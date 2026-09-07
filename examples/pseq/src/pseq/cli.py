"""Entrada da CLI.

Comandos planos sobre um unico objeto: FASTA de proteinas. A camada visual vive
em theme.py e no ui.py vendorizado, e desaparece por completo quando a saida nao e um
terminal, quando NO_COLOR esta definido ou quando --color never e passado.
"""

from __future__ import annotations

import re
import signal
import sys
from typing import Annotated, Optional

import typer
from typer import rich_utils

# O painel de ajuda do typer usa a largura do terminal quando MAX_WIDTH e None.
rich_utils.MAX_WIDTH = min(rich_utils.MAX_WIDTH or 80, 80)

try:  # typer >= 0.27 embute o click
    from typer._click.exceptions import UsageError
except ImportError:  # pragma: no cover
    from click.exceptions import UsageError

from . import __version__, fasta, props, theme, ui
from .errors import EXIT_DATA, EXIT_INTERRUPT, EXIT_OK, EXIT_RUNTIME, EXIT_USAGE, PseqError
from .output import Column, open_output, resolve_mode, status, warn, write_panel, write_table

app = typer.Typer(
    name="pseq",
    help="""Protein FASTA analysis.

    \b
    Examples:
      pseq stats examples/sample.fa
      pseq filter --min-length 50 in.fa > out.fa
      zcat big.fa.gz | pseq validate -
    """,
    epilog="Exit codes: 0 success, 1 runtime error, 2 usage error, 3 data problems found.",
    add_completion=False,
    no_args_is_help=False,
    rich_markup_mode="rich",
    # A ajuda para em 80 colunas mesmo numa janela larga: uma linha de ajuda com
    # 120 caracteres e ilegivel e nao sobrevive a uma colagem em outro lugar.
    context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 80},
)

Files = Annotated[Optional[list[str]], typer.Argument(metavar="[FILE]...", help="FASTA file(s); - for stdin.", show_default=False)]
Output = Annotated[Optional[str], typer.Option("-o", "--output", metavar="PATH", help="Write to PATH instead of stdout.", show_default=False)]
Json = Annotated[bool, typer.Option("--json", help="Emit JSON.")]
Tsv = Annotated[bool, typer.Option("--tsv", help="Emit plain TSV (automatic when piped).")]
Quiet = Annotated[bool, typer.Option("-q", "--quiet", help="Suppress status, warnings and animation.")]
Verbose = Annotated[int, typer.Option("-v", "--verbose", count=True, help="More detail; -vv shows tracebacks.")]
Color = Annotated[str, typer.Option("--color", metavar="WHEN", help="auto, always or never.")]
NoColor = Annotated[bool, typer.Option("--no-color", help="Same as --color never.")]
NoArt = Annotated[bool, typer.Option("--no-art", help="Drop bars and banner, keep color.")]


SLOGAN = f"protein FASTA analysis  v{__version__}"
BANNER_OPTIONS = (
    ("--json / --tsv", "machine readable output"),
    ("--color WHEN", "auto, always or never"),
    ("-q / -v", "quieter, or more detail"),
    ("--help", "examples and every flag"),
)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"pseq {__version__}")
        raise typer.Exit(EXIT_OK)


@app.callback(invoke_without_command=True)
def root(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True, help="Show version.")] = False,
) -> None:
    if ctx.invoked_subcommand is None:
        ui.banner("pseq", SLOGAN, BANNER_OPTIONS)  # stderr; nunca contamina um pipe
        typer.echo(ctx.get_help())
        raise typer.Exit(EXIT_OK)


def _inputs(files: Optional[list[str]], cmd: str) -> list[str]:
    """Sem FILE: le stdin se houver pipe; em TTY mostra uso curto e sai com 2."""
    if files:
        return files
    if not sys.stdin.isatty():
        return ["-"]
    lvl = theme.level(sys.stderr, "auto")
    sys.stderr.write(
        f"{theme.fg('pseq ' + cmd, 'err', lvl, bold=True)}: no input given.\n"
        f"  {theme.dim('usage', lvl)}  pseq {cmd} [FILE]...   or   cat file.fa | pseq {cmd}\n"
        f"  {theme.dim('help ', lvl)}  pseq {cmd} --help\n"
    )
    raise typer.Exit(EXIT_USAGE)


def _mode(json_: bool, tsv: bool, color: str, no_color: bool, quiet: bool, verbose: int, output: Optional[str], art: bool = True):
    if json_ and tsv:
        raise UsageError("--json and --tsv are mutually exclusive.")
    if color not in ("auto", "always", "never"):
        raise UsageError(f"--color takes auto, always or never, not {color!r}.")
    if no_color:
        color = "never"
    ui.apply_color_flag(color)
    out = open_output(output)
    return resolve_mode(json_, tsv, color, quiet, verbose, out, art), out


def _compile(pattern: str, prosite: bool) -> re.Pattern:
    rx = props.prosite_to_regex(pattern) if prosite else pattern
    try:
        return re.compile(rx)
    except re.error as e:
        raise UsageError(f"invalid pattern {pattern!r}: {e}.")


def _load(paths: list[str], mode, label: str = "reading") -> list[fasta.Record]:
    """Le tudo com o spinner de gradiente do template; silencioso com --quiet."""
    if mode.quiet:
        return list(fasta.read_all(paths))
    with ui.status(label):
        return list(fasta.read_all(paths))


def _tracked(items, label: str, mode):
    """Barra de progresso do template; sem TTY o Progress se desliga sozinho."""
    if mode.quiet:
        yield from items
        return
    with ui.progress() as bar:
        task = bar.add_task(label, total=len(items))
        for item in items:
            yield item
            bar.advance(task)


def _close(out, output: Optional[str]) -> None:
    out.flush()
    if output and output != "-":
        out.close()


# ---------------------------------------------------------------- stats

def _pi_color(v, row):
    return "acidic" if v < 6.0 else "basic" if v > 8.0 else None


def _charge_color(v, row):
    return "acidic" if v < -0.5 else "basic" if v > 0.5 else None


def _gravy_color(v, row):
    return "hydrophobic" if v > 0 else "hydrophilic"


@app.command()
def stats(
    files: Files = None,
    output: Output = None,
    json_: Json = False,
    tsv: Tsv = False,
    ph: Annotated[float, typer.Option("--ph", help="pH for net charge.")] = 7.0,
    summary: Annotated[bool, typer.Option("--summary", help="Aggregate instead of one row per sequence.")] = False,
    color: Color = "auto",
    no_color: NoColor = False,
    no_art: NoArt = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Length, molecular weight, pI, GRAVY and net charge per sequence.

    \b
    Examples:
      pseq stats examples/sample.fa
      pseq stats --json in.fa | jq '.[] | select(.pi > 9)'
      zcat big.fa.gz | pseq stats --summary
    """
    paths = _inputs(files, "stats")
    mode, out = _mode(json_, tsv, color, no_color, quiet, verbose, output, art=not no_art)
    records = _load(paths, mode)
    rows = []
    pending: list[str] = []
    for r in _tracked(records, "computing", mode):
        amb = props.ambiguous_positions(r.seq)
        if amb:
            pending.append(f"{r.id}: {len(amb)} ambiguous residue(s); excluded from MW, pI and GRAVY.")
        rows.append(
            {
                "id": r.id,
                "length": len(props.clean(r.seq)),
                "mw": props.molecular_weight(r.seq),
                "pi": props.isoelectric_point(r.seq),
                "gravy": props.gravy(r.seq),
                "charge": props.charge_at(r.seq, ph),
            }
        )
    for msg in pending:  # depois da barra, para nao cortar a linha animada
        warn(msg, mode)
    ambiguous = len(pending)
    if summary:
        n = len(rows)
        lengths = [r["length"] for r in rows] or [0]
        agg = {
            "sequences": n,
            "residues": sum(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "mean_length": sum(lengths) / n if n else 0.0,
            "mean_mw": sum(r["mw"] for r in rows) / n if n else 0.0,
            "mean_pi": sum(r["pi"] for r in rows) / n if n else 0.0,
            "mean_gravy": sum(r["gravy"] for r in rows) / n if n else 0.0,
        }
        if mode.rich:
            write_panel([(k.replace("_", " "), f"{v:.2f}" if isinstance(v, float) else str(v)) for k, v in agg.items()], mode, out, title="summary")
        else:
            write_table([agg], list(agg.keys()), mode, out)
        _close(out, output)
        return

    maxlen = max((r["length"] for r in rows), default=1)
    cols = [
        Column("id"),
        Column("length", align="right", bar_width=12,
               bar=lambda r, l, w: theme.bar(r["length"], maxlen, w, l, "accent")),
        Column("mw", align="right"),
        Column("pi", align="right", color=_pi_color),
        Column("gravy", align="right", color=_gravy_color, bar_width=11,
               bar=lambda r, l, w: theme.diverging_bar(r["gravy"], 4.5, w, l)),
        Column("charge", align="right", color=_charge_color),
    ]
    write_table(rows, cols, mode, out, title="stats")
    if mode.rich:
        note = f"{len(rows)} sequences"
        if ambiguous:
            note += f", {ambiguous} with ambiguous residues"
        status(note, mode)
    _close(out, output)


# ---------------------------------------------------------------- composition

@app.command()
def composition(
    files: Files = None,
    output: Output = None,
    json_: Json = False,
    tsv: Tsv = False,
    per_sequence: Annotated[bool, typer.Option("--per-sequence", help="One row per sequence instead of a global total.")] = False,
    color: Color = "auto",
    no_color: NoColor = False,
    no_art: NoArt = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Amino acid counts and frequencies.

    \b
    Examples:
      pseq composition examples/sample.fa
      pseq composition --per-sequence --tsv in.fa | cut -f1,2
    """
    paths = _inputs(files, "composition")
    mode, out = _mode(json_, tsv, color, no_color, quiet, verbose, output, art=not no_art)
    records = _load(paths, mode)
    if per_sequence:
        rows = []
        for r in records:
            c = props.composition(r.seq)
            rows.append({"id": r.id, "length": sum(c.values()), **c})
        write_table(rows, ["id", "length", *props.STANDARD], mode, out, title="composition")
        _close(out, output)
        return

    total: dict[str, int] = {}
    for r in records:
        for a, n in props.composition(r.seq).items():
            total[a] = total.get(a, 0) + n
    residues = sum(total.values())
    rows = [
        {"residue": a, "count": total.get(a, 0), "frequency": (total.get(a, 0) / residues if residues else 0.0)}
        for a in sorted(total, key=lambda k: (k not in props.STANDARD, k))
    ]
    top = max((r["frequency"] for r in rows), default=1.0)
    cols = [
        Column("residue"),
        Column("count", align="right"),
        Column("frequency", align="right", fmt="{:.4f}", bar_width=24,
               bar=lambda r, l, w: theme.bar(r["frequency"], top, w, l, _residue_color(r["residue"]))),
    ]
    write_table(rows, cols, mode, out, title="composition")
    if mode.rich:
        status(f"{residues} residues over {len(records)} sequences", mode)
    _close(out, output)


_HYDROPHOBIC = set("AVLIMFWYC")
_CHARGED_POS = set("KRH")
_CHARGED_NEG = set("DE")


def _residue_color(a: str) -> str:
    if a in _CHARGED_POS:
        return "basic"
    if a in _CHARGED_NEG:
        return "acidic"
    if a in _HYDROPHOBIC:
        return "hydrophobic"
    return "hydrophilic"


# ---------------------------------------------------------------- filter

@app.command()
def filter(
    files: Files = None,
    output: Output = None,
    min_length: Annotated[Optional[int], typer.Option("--min-length", metavar="N", show_default=False)] = None,
    max_length: Annotated[Optional[int], typer.Option("--max-length", metavar="N", show_default=False)] = None,
    pattern: Annotated[Optional[str], typer.Option("--pattern", metavar="REGEX", help="Keep sequences matching REGEX.", show_default=False)] = None,
    prosite: Annotated[bool, typer.Option("--prosite", help="Interpret --pattern as PROSITE notation.")] = False,
    id_pattern: Annotated[Optional[str], typer.Option("--id", metavar="REGEX", help="Keep ids matching REGEX.", show_default=False)] = None,
    ids_file: Annotated[Optional[str], typer.Option("--ids-file", metavar="PATH", help="Keep ids listed in PATH, one per line.", show_default=False)] = None,
    no_ambiguous: Annotated[bool, typer.Option("--no-ambiguous", help="Drop sequences with B, J, O, U, X or Z.")] = False,
    invert: Annotated[bool, typer.Option("--invert", help="Keep sequences that do NOT match.")] = False,
    line_width: Annotated[int, typer.Option("--line-width", metavar="N", help="Wrap at N columns; 0 for one line.")] = 60,
    color: Color = "auto",
    no_color: NoColor = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Select sequences by length, id, pattern or ambiguity; writes FASTA.

    \b
    Examples:
      pseq filter --min-length 50 in.fa > out.fa
      pseq filter --pattern "C.{2,4}C" --invert in.fa
      pseq filter --ids-file keep.txt in.fa | pseq stats
    """
    paths = _inputs(files, "filter")
    mode, out = _mode(False, False, color, no_color, quiet, verbose, output)
    if min_length is not None and max_length is not None and min_length > max_length:
        raise UsageError(f"--min-length ({min_length}) is greater than --max-length ({max_length}).")
    seq_rx = _compile(pattern, prosite) if pattern else None
    id_rx = _compile(id_pattern, False) if id_pattern else None
    keep_ids: set[str] | None = None
    if ids_file:
        try:
            with open(ids_file, encoding="utf-8") as fh:
                keep_ids = {ln.strip().split()[0] for ln in fh if ln.strip()}
        except OSError as e:
            raise PseqError(f"cannot read --ids-file {ids_file}: {e.strerror}.", code=EXIT_RUNTIME)

    def match(r: fasta.Record) -> bool:
        n = len(props.clean(r.seq))
        if min_length is not None and n < min_length:
            return False
        if max_length is not None and n > max_length:
            return False
        if seq_rx and not seq_rx.search(r.seq):
            return False
        if id_rx and not id_rx.search(r.id):
            return False
        if keep_ids is not None and r.id not in keep_ids:
            return False
        if no_ambiguous and props.ambiguous_positions(r.seq):
            return False
        return True

    seen = kept = 0

    def gen():
        nonlocal seen, kept
        for r in fasta.read_all(paths):
            seen += 1
            if match(r) != invert:
                kept += 1
                yield r

    if mode.quiet:
        fasta.write_fasta(gen(), out, line_width=line_width)
    else:
        with ui.status("filtering"):
            fasta.write_fasta(gen(), out, line_width=line_width)
    if not quiet and (out.isatty() or output):
        pct = (kept / seen * 100) if seen else 0.0
        status(f"kept {kept} of {seen} sequences ({pct:.0f}%)", mode)
    _close(out, output)


# ---------------------------------------------------------------- validate

def _level_color(v, row):
    return "err" if v == "error" else "warn"


@app.command()
def validate(
    files: Files = None,
    output: Output = None,
    json_: Json = False,
    tsv: Tsv = False,
    allow_ambiguous: Annotated[bool, typer.Option("--allow-ambiguous", help="Do not report B, J, O, U, X, Z as problems.")] = False,
    color: Color = "auto",
    no_color: NoColor = False,
    no_art: NoArt = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Check alphabet, duplicate ids and empty sequences. Exit 3 if problems are found.

    \b
    Examples:
      pseq validate in.fa && echo clean
      pseq validate --json in.fa
    """
    paths = _inputs(files, "validate")
    mode, out = _mode(json_, tsv, color, no_color, quiet, verbose, output, art=not no_art)
    records = _load(paths, mode, "checking")
    issues: list[dict] = []
    seen: dict[str, str] = {}
    for r in records:
        where = f"{r.source}:{r.line}"
        if not r.id:
            issues.append({"level": "error", "id": "", "where": where, "problem": "empty header"})
        if not props.clean(r.seq):
            issues.append({"level": "error", "id": r.id, "where": where, "problem": "empty sequence"})
        if r.id in seen:
            issues.append({"level": "error", "id": r.id, "where": where, "problem": f"duplicate id (first at {seen[r.id]})"})
        else:
            seen[r.id] = where
        for pos, a in props.invalid_positions(r.seq):
            issues.append({"level": "error", "id": r.id, "where": where, "problem": f"invalid character {a!r} at position {pos}"})
        if not allow_ambiguous:
            amb = props.ambiguous_positions(r.seq)
            if amb:
                issues.append({"level": "warning", "id": r.id, "where": where, "problem": f"{len(amb)} ambiguous residue(s), first {amb[0][1]!r} at {amb[0][0]}"})

    errors = sum(1 for i in issues if i["level"] == "error")
    warnings = len(issues) - errors
    if mode.fmt in ("json", "tsv"):
        write_table(issues, ["level", "id", "where", "problem"], mode, out)
    else:
        mark = {"error": theme.g("err"), "warning": theme.g("warn")}
        shown = [{**i, "level": f"{mark[i['level']]} {i['level']}"} for i in issues]
        write_table(
            shown,
            [Column("level", color=lambda v, r: "err" if "error" in v else "warn"),
             Column("id"), Column("where"), Column("problem")],
            mode, out, title="validate",
        )
        if not issues:
            verdict, token = "clean", "ok"
        elif errors:
            verdict, token = f"{errors} error(s), {warnings} warning(s)", "err"
        else:
            verdict, token = f"{warnings} warning(s)", "warn"
        status(f"{len(records)} sequences checked: " + theme.fg(verdict, token, mode.lvl, bold=True), mode)
    if mode.fmt != "rich":
        status(f"{len(records)} sequences, {errors} error(s), {warnings} warning(s).", mode)
    _close(out, output)
    if errors:
        raise typer.Exit(EXIT_DATA)


# ---------------------------------------------------------------- motif

@app.command()
def motif(
    files: Files = None,
    output: Output = None,
    json_: Json = False,
    tsv: Tsv = False,
    pattern: Annotated[str, typer.Option("--pattern", metavar="PATTERN", help="Regex, or PROSITE with --prosite.", show_default=False)] = ...,
    prosite: Annotated[bool, typer.Option("--prosite", help="Interpret PATTERN as PROSITE notation.")] = False,
    context: Annotated[int, typer.Option("--context", metavar="N", help="Residues of flanking context to show.")] = 6,
    color: Color = "auto",
    no_color: NoColor = False,
    no_art: NoArt = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Find pattern occurrences with 1-based positions.

    \b
    Examples:
      pseq motif --pattern "N[^P][ST][^P]" in.fa
      pseq motif --prosite --pattern "N-{P}-[ST]" examples/sample.fa
    """
    paths = _inputs(files, "motif")
    mode, out = _mode(json_, tsv, color, no_color, quiet, verbose, output, art=not no_art)
    rx = _compile(pattern, prosite)
    records = _load(paths, mode, "scanning")
    rows = []
    for r in records:
        for m in rx.finditer(r.seq):
            left = r.seq[max(0, m.start() - context) : m.start()]
            right = r.seq[m.end() : m.end() + context]
            rows.append({"id": r.id, "start": m.start() + 1, "end": m.end(), "match": m.group(0),
                         "_left": left, "_right": right})
    if mode.fmt in ("json", "tsv"):
        for row in rows:
            row.pop("_left", None)
            row.pop("_right", None)
        write_table(rows, ["id", "start", "end", "match"], mode, out)
    else:
        cols = [
            Column("id"), Column("start", align="right"), Column("end", align="right"),
            Column("match", color=lambda v, r: "accent"),
            Column("context", value=False, bar_width=0,
                   bar=lambda r, l, w: theme.dim(r["_left"], l)
                   + theme.fg(r["match"], "accent", l, bold=True)
                   + theme.dim(r["_right"], l)),
        ]
        write_table(rows, cols, mode, out, title=f"motif  {pattern}")
        status(f"{len(rows)} match(es) in {len(records)} sequences", mode)
    _close(out, output)


# ---------------------------------------------------------------- convert

@app.command()
def convert(
    files: Files = None,
    output: Output = None,
    json_: Json = False,
    tsv: Tsv = False,
    line_width: Annotated[int, typer.Option("--line-width", metavar="N", help="Wrap at N columns; 0 for one line.")] = 60,
    lower: Annotated[bool, typer.Option("--lower", help="Lowercase residues.")] = False,
    color: Color = "auto",
    no_color: NoColor = False,
    quiet: Quiet = False,
    verbose: Verbose = 0,
) -> None:
    """Rewrap, change case, or export to TSV/JSON.

    \b
    Examples:
      pseq convert --line-width 0 in.fa > oneline.fa
      pseq convert --tsv in.fa | cut -f1
    """
    paths = _inputs(files, "convert")
    mode, out = _mode(json_, tsv, color, no_color, quiet, verbose, output)
    if json_ or tsv:
        rows = [{"id": r.id, "description": r.description, "seq": r.seq} for r in fasta.read_all(paths)]
        write_table(rows, ["id", "description", "seq"], mode, out)
    else:
        fasta.write_fasta(fasta.read_all(paths), out, line_width=line_width, case="lower" if lower else None)
    _close(out, output)


# ---------------------------------------------------------------- completion

@app.command()
def completion(
    shell: Annotated[str, typer.Argument(metavar="SHELL", help="bash, zsh, fish or powershell.")],
) -> None:
    """Print the shell completion script.

    \b
    Examples:
      mkdir -p ~/.zfunc && pseq completion zsh > ~/.zfunc/_pseq
      eval "$(pseq completion bash)"
    """
    from typer._completion_shared import get_completion_script

    if shell not in ("bash", "zsh", "fish", "powershell"):
        raise UsageError(f"unknown shell {shell!r}; use bash, zsh, fish or powershell.")
    typer.echo(get_completion_script(prog_name="pseq", complete_var="_PSEQ_COMPLETE", shell=shell))


# ---------------------------------------------------------------- entrada

def main() -> None:
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (AttributeError, ValueError):
        pass
    ui.install_signal_handlers()
    argv = sys.argv[1:]
    verbose = sum(1 for a in argv if a in ("-v", "--verbose")) + sum(a.count("v") for a in argv if re.fullmatch(r"-v+", a))
    lvl = theme.level(sys.stderr, "auto")
    try:
        rc = app(standalone_mode=False)
    except typer.Exit as e:
        sys.exit(e.exit_code)
    except UsageError as e:
        sys.stderr.write(f"{theme.fg('Error', 'err', lvl, bold=True)}: {e.format_message()}\n")
        if e.ctx is not None:
            sys.stderr.write(theme.dim(f"Run `{e.ctx.command_path} --help` for usage.\n", lvl))
        sys.exit(EXIT_USAGE)
    except PseqError as e:
        sys.stderr.write(f"{theme.fg('Error', 'err', lvl, bold=True)}: {e.message}\n")
        if e.hint:
            sys.stderr.write(f"{theme.fg('Try', 'info', lvl, bold=True)}: {e.hint}\n")
        sys.exit(e.code)
    except KeyboardInterrupt:
        sys.stderr.write("\x1b[?25h\n" + theme.dim("Interrupted.", lvl) + "\n")
        sys.exit(EXIT_INTERRUPT)
    except BrokenPipeError:
        sys.exit(EXIT_OK)
    except Exception as e:
        if verbose >= 2:
            raise
        sys.stderr.write(
            f"{theme.fg('Error', 'err', lvl, bold=True)}: unexpected failure: {e}\n"
            + theme.dim("Run again with -vv for a traceback.\n", lvl)
        )
        sys.exit(EXIT_RUNTIME)
    sys.exit(rc if isinstance(rc, int) else EXIT_OK)


if __name__ == "__main__":
    main()

"""Saida de dados.

Contrato: stdout carrega dados, stderr carrega mensagens. Em TTY a tabela ganha
gradiente, cor semantica e barras; em pipe ela vira TSV puro, byte a byte igual
ao que os testes verificam. JSON e identico nos dois casos.
"""

from __future__ import annotations

import json
import sys
import textwrap
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence, TextIO

from . import theme

Colorizer = Callable[[Any, dict], "str | tuple[int, int, int] | None"]

MIN_BAR = 7  # abaixo disso a barra nao ordena mais nada e vira ruido


@dataclass
class OutputMode:
    fmt: str  # "rich" | "tsv" | "json"
    lvl: int
    quiet: bool
    verbose: int
    width: int = 80
    art: bool = True

    @property
    def rich(self) -> bool:
        return self.fmt == "rich"


@dataclass
class Column:
    key: str
    label: str | None = None
    align: str = "left"      # left | right
    fmt: str = "{}"
    color: Colorizer | None = None
    bar: Callable[[dict, int, int], str] | None = None  # (row, lvl, width) -> arte
    bar_width: int = 0
    value: bool = True   # False: a coluna e apenas a arte

    def head(self) -> str:
        return self.label if self.label is not None else self.key


def resolve_mode(
    json_: bool, tsv: bool, color: str, quiet: bool, verbose: int, out: TextIO, art: bool = True
) -> OutputMode:
    lvl = theme.level(out, color)
    if json_:
        fmt = "json"
    elif tsv:
        fmt = "tsv"
    else:
        is_tty = hasattr(out, "isatty") and out.isatty()
        # --color always e uma escolha explicita por saida humana (pipe para `less -R`).
        fmt = "rich" if (is_tty or color == "always") else "tsv"
    return OutputMode(fmt=fmt, lvl=lvl, quiet=quiet, verbose=verbose, width=theme.term_width(), art=art)


def open_output(path: str | None) -> TextIO:
    if path is None or path == "-":
        return sys.stdout
    return open(path, "w", encoding="utf-8", newline="\n")


def fmt_value(v: Any, spec: str = "{}") -> str:
    if isinstance(v, float):
        out = spec.format(v) if spec != "{}" else f"{v:.2f}"
        return "0.00" if out in ("-0.00", "-0.0", "-0") else out
    return spec.format(v) if spec != "{}" else str(v)


def write_table(
    rows: Iterable[dict[str, Any]],
    columns: Sequence[Column] | Sequence[str],
    mode: OutputMode,
    out: TextIO,
    title: str = "",
) -> int:
    cols = [Column(c) if isinstance(c, str) else c for c in columns]
    rows = list(rows)

    if mode.fmt == "json":
        json.dump(rows, out, indent=2)
        out.write("\n")
        return len(rows)

    cols_data = [c for c in cols if c.value]
    keys = [c.key for c in cols_data]
    if mode.fmt == "tsv":
        out.write("\t".join(keys) + "\n")
        for r in rows:
            out.write("\t".join(fmt_value(r.get(c.key, ""), c.fmt) for c in cols_data) + "\n")
        return len(rows)

    # --- caminho TTY -------------------------------------------------------
    lvl = mode.lvl
    body = [[fmt_value(r.get(c.key, ""), c.fmt) if c.value else "" for c in cols] for r in rows]
    widths = []
    for i, c in enumerate(cols):
        w = max([len(c.head())] + [len(b[i]) for b in body]) if body else len(c.head())
        widths.append(w)

    # Largura antes de beleza, mas a arte encolhe antes de sumir: em 80 colunas
    # uma barra curta ainda ordena a coluna, e uma coluna ausente nao.
    gap = 2
    show_art = mode.art
    art_cols = [c for c in cols if c.bar]
    bar_w = {id(c): c.bar_width for c in art_cols}

    def _total(with_art: bool) -> int:
        n = sum(widths[i] for i, c in enumerate(cols) if c.value)
        cells = sum(1 for c in cols if c.value)
        if with_art:
            n += sum(bar_w[id(c)] for c in art_cols)
            cells += len(art_cols)
        return n + gap * max(0, cells - 1)

    if show_art and art_cols:
        while _total(True) > mode.width and any(bar_w[id(c)] > MIN_BAR for c in art_cols):
            for c in art_cols:
                if bar_w[id(c)] > MIN_BAR:
                    bar_w[id(c)] -= 1
        if _total(True) > mode.width:
            show_art = False
    if _total(False) > mode.width:
        room = mode.width - (_total(False) - max(widths))
        widest = widths.index(max(widths))
        widths[widest] = max(8, room)
        ell = "\u2026" if theme.unicode_ok() else "..."
        for line in body:
            if len(line[widest]) > widths[widest]:
                line[widest] = line[widest][: widths[widest] - len(ell)] + ell

    if title:
        out.write(theme.rule(mode.width, lvl, title) + "\n")

    head_cells = []
    for i, c in enumerate(cols):
        if c.value:
            h = c.head().upper()
            head_cells.append(h.rjust(widths[i]) if c.align == "right" else h.ljust(widths[i]))
        if c.bar and show_art:
            label = "" if c.value else c.head().upper()
            head_cells.append(label.ljust(bar_w[id(c)]) if bar_w[id(c)] else label)
    out.write(theme.gradient("  ".join(head_cells).rstrip(), lvl, bold=True) + "\n")

    if not rows:
        out.write(theme.dim("  (no rows)", lvl) + "\n")
        return 0

    for r, line in zip(rows, body):
        cells = []
        for i, c in enumerate(cols):
            if c.value:
                text = line[i]
                pad = text.rjust(widths[i]) if c.align == "right" else text.ljust(widths[i])
                if c.color:
                    tok = c.color(r.get(c.key), r)
                    pad = theme.fg(pad, tok, lvl) if tok else pad
                cells.append(pad)
            if c.bar and show_art:
                cells.append(c.bar(r, lvl, bar_w[id(c)]))
        out.write("  ".join(cells).rstrip() + "\n")
    return len(rows)


def write_panel(pairs: Sequence[tuple[str, str]], mode: OutputMode, out: TextIO, title: str = "") -> None:
    """Caixa com borda em gradiente para um resumo de poucos campos."""
    if not mode.rich:
        return
    b = theme.box()
    tl, tr, bl, br, h, v = b["tl"], b["tr"], b["bl"], b["br"], b["h"], b["v"]
    label_w = max(len(k) for k, _ in pairs)
    value_w = max(len(v2) for _, v2 in pairs)
    inner = max(label_w + value_w + 3, len(title) + 2, 24)
    lvl = mode.lvl
    head = f"{tl}{h} {title} " + h * max(0, inner - len(title) - 3) + tr if title else tl + h * inner + tr
    out.write(theme.gradient(head, lvl) + "\n")
    for k, val in pairs:
        pad = " " * (inner - label_w - len(val) - 3)
        out.write(
            theme.dim(v, lvl) + " " + theme.dim(k.ljust(label_w), lvl) + pad
            + theme.fg(val, "accent", lvl, bold=True) + " " + theme.dim(v, lvl) + "\n"
        )
    out.write(theme.gradient(bl + h * inner + br, lvl) + "\n")


def _wrapped(prefix_len: int, msg: str, mode: OutputMode) -> list[str]:
    """Quebra na largura do terminal: uma linha mais longa vira duas e desalinha
    tudo que vier depois."""
    width = max(24, mode.width - prefix_len)
    return textwrap.wrap(msg, width=width) or [""]


def status(msg: str, mode: OutputMode) -> None:
    if mode.quiet:
        return
    mark = theme.g("pointer")
    head = theme.fg(mark, "accent", mode.lvl) if mode.lvl else mark
    lines = _wrapped(len(mark) + 1, msg, mode)
    sys.stderr.write(f"{head} {lines[0]}\n")
    for extra in lines[1:]:
        sys.stderr.write(f"{' ' * (len(mark) + 1)}{extra}\n")


def warn(msg: str, mode: OutputMode) -> None:
    if mode.quiet:
        return
    mark = theme.g("warn")
    label = f"{mark} warning"
    prefix = theme.fg(label, "warn", mode.lvl, bold=True) if mode.lvl else "Warning:"
    plain_len = len(label) + 1 if mode.lvl else len("Warning: ")
    lines = _wrapped(plain_len, msg, mode)
    sys.stderr.write(f"{prefix} {lines[0]}\n")
    for extra in lines[1:]:
        sys.stderr.write(f"{' ' * plain_len}{extra}\n")

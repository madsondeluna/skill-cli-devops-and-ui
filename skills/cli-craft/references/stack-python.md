# Python

Default stack for this user. Requires Python 3.10+.

| Shape | Libraries |
|---|---|
| 1, 2 | Typer (on Click) for arguments, Rich for output, `rich-gradient` for banners |
| 3 | Typer for entry, Rich `Live` and `Console` for the transcript, `prompt_toolkit` for the input box |
| 4 | Textual |

Alternatives worth knowing: `click` alone when Typer's type driven API gets in the way (complex option groups, plugin CLIs); `argparse` for zero dependency tools; `cyclopts` as a Typer replacement with better help; `questionary` for prompts in shapes 1 and 2; `tqdm` only when the project already uses it (Rich progress is better looking and integrates with the console); `alive-progress` for animated bars when Rich is not present.

Packaging: `pyproject.toml` with a `[project.scripts]` entry point, install with `uv tool install` or `pipx`. Never make the user run `python tool.py`.

## Start from the template

`assets/templates/python/ui.py` is the finished output module: copy it into
the package, set `CLI_CRAFT_TOOL_NAME` to the tool name (or edit the `TOOL`
constant) and import it everywhere output happens. `test_ui.py` next to it is
the matching unittest module. `scripts/demo_gallery.py` shows the template
used by a complete shape 1 tool. The section below explains what the template
does and why, for when it needs to be extended.

## Output module (`ui.py`)

The single place that knows about terminals. Every command imports `out` and `err` from here.

```python
"""Terminal output for the tool. All decoration goes to stderr."""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.theme import Theme

# Semantic roles (see palette.md). Rich picks the nearest color on 256 and 16 color terminals
# when given truecolor hex, so a single table serves all levels. The 16 color fallback is
# explicit for roles where the nearest match is poor.
THEME = Theme({
    "muted": "#8B95A9",
    "accent": "#6FA3FF",
    "accent2": "#B49CFF",
    "ok": "#6EE39C",
    "warn": "#F2C56B",
    "err": "#FF7B8E",
    "info": "#7CD5FF",
    "border": "#3A4258",
    "key": "bold #B49CFF",
    "cmd": "bold #6FA3FF",
    "path": "underline",
})


def _color_system(when: str) -> str | None:
    # Returns the Rich color_system argument or None to disable color.
    if when == "never" or "NO_COLOR" in os.environ:
        return None
    if when == "always" or os.environ.get("FORCE_COLOR"):
        return {"2": "256", "3": "truecolor"}.get(os.environ.get("FORCE_COLOR", ""), "standard")
    return "auto"  # Rich then checks isatty, TERM, COLORTERM itself


def make_consoles(color: str = "auto", quiet: bool = False) -> tuple[Console, Console]:
    cs = _color_system(color)
    common = dict(theme=THEME, color_system=cs, no_color=cs is None, emoji=False,
                  highlight=False, soft_wrap=False)
    out = Console(file=sys.stdout, **common)
    err = Console(file=sys.stderr, quiet=quiet, **common)
    return out, err


out, err = make_consoles()

# Unicode fallback: Rich handles box characters, but glyphs are ours.
UTF8 = (err.encoding or "").lower().replace("-", "") == "utf8" and not os.environ.get("TOOL_ASCII")
G = {
    "ok": "\u2713" if UTF8 else "ok",
    "err": "\u2717" if UTF8 else "x",
    "warn": "\u25b2" if UTF8 else "!",
    "info": "\u25cf" if UTF8 else "*",
    "ptr": "\u276f" if UTF8 else ">",
}

ANIMATE = err.is_terminal and not os.environ.get("CI") and not os.environ.get("TOOL_NO_ANIMATION")
INTERACTIVE = sys.stdin.isatty() and err.is_terminal and not os.environ.get("CI")


def ok(msg: str) -> None:
    err.print(f"[ok]{G['ok']}[/] {msg}")


def info(msg: str) -> None:
    err.print(f"[info]{G['info']}[/] {msg}")


def warn(msg: str) -> None:
    err.print(f"[warn]warning:[/] {msg}")


def error(msg: str, hint: str | None = None) -> None:
    err.print(f"[err]error:[/] {msg}")
    if hint:
        err.print(f"  [muted]hint:[/] {hint}")


@contextmanager
def status(msg: str) -> Iterator[None]:
    """Spinner on a TTY, a plain line otherwise. Replaces itself with the final state."""
    import time
    t0 = time.monotonic()
    if not ANIMATE:
        info(msg)
        yield
        ok(f"{msg} [muted]({time.monotonic() - t0:.1f}s)[/]")
        return
    with err.status(msg, spinner="dots", spinner_style="info"):
        try:
            yield
        except BaseException:
            error(msg)
            raise
    ok(f"{msg} [muted]({time.monotonic() - t0:.1f}s)[/]")
```

Notes on Rich behavior that matter here:

- `Console(file=sys.stderr)` is what keeps stdout clean. Never use the global `rich.print` for status.
- `emoji=False` and `highlight=False` stop Rich from turning `:x:` into pictures and from coloring numbers in your data.
- `err.status(...)` uses `Live`, which already stops animating when not a terminal, but printing the plain `info` line first gives log files a timestamped start.
- Wrap `Live` regions in synchronized output: Rich 13.8+ does this on supporting terminals; on older Rich, set `Console(force_terminal=...)` and accept minor flicker in tmux.

## Commands (`cli.py`)

```python
import typer
from typing_extensions import Annotated

from . import ui

app = typer.Typer(
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Run and inspect AMP pipelines.\n\n"
         "[bold]Examples[/]\n"
         "  tool run samples.tsv --profile docker\n"
         "  tool status --json | jq .state",
)


@app.callback()
def main(
    color: Annotated[str, typer.Option(help="auto, always, never", envvar="TOOL_COLOR")] = "auto",
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Errors only")] = False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0,
):
    ui.out, ui.err = ui.make_consoles(color, quiet)


@app.command()
def run(
    samples: Annotated[typer.FileText, typer.Argument(help="TSV of samples, or - for stdin")],
    profile: Annotated[str, typer.Option("--profile", "-p", envvar="TOOL_PROFILE")] = "docker",
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
):
    """Execute the pipeline on a sample sheet."""
    rows = list(read_samples(samples))
    if not yes and not dry_run:
        if not ui.INTERACTIVE:
            ui.error("cannot prompt: stdin is not a terminal", "pass --yes")
            raise typer.Exit(2)
        if not typer.confirm(f"Run {len(rows)} samples with profile {profile}?", default=False, err=True):
            raise typer.Exit(130)
    with ui.status(f"aligning {len(rows)} samples"):
        align_all(rows, profile)
    ui.ok(f"{len(rows)} samples done, report at [path]results/report.html[/]")


@app.command()
def status(json_: Annotated[bool, typer.Option("--json")] = False):
    """Show the last run."""
    state = load_state()
    if json_:
        import json
        ui.out.print_json(json.dumps(state))  # stdout, no color when piped
        return
    from rich.table import Table
    t = Table(box=None, header_style="bold muted", pad_edge=False, show_edge=False)
    t.add_column("NAME"); t.add_column("STATUS"); t.add_column("DURATION", justify="right")
    for r in state["runs"]:
        style = {"ok": "ok", "failed": "err", "running": "info"}[r["status"]]
        t.add_row(r["name"], f"[{style}]{r['status']}[/]", r["duration"])
    ui.out.print(t)
```

Behaviors to keep: `typer.Exit(code)` for exit codes, `raise typer.BadParameter` for usage errors (exit 2), `err=True` on prompts so they use stderr, `print_json` on the stdout console for `--json`. Catch `KeyboardInterrupt` at the entry point and exit 130 after restoring the cursor (Rich `Live` does this in its `__exit__`; a bare `sys.exit(130)` inside `with err.status` is safe).

## Progress

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn, TransferSpeedColumn

with Progress(
    SpinnerColumn(style="info"), "[bold]{task.description}", BarColumn(bar_width=None, style="border", complete_style="accent"),
    "{task.percentage:>3.0f}%", MofNCompleteColumn(), TimeElapsedColumn(), TimeRemainingColumn(),
    console=ui.err, transient=False, disable=not ui.ANIMATE,
) as progress:
    task = progress.add_task("aligning", total=len(rows))
    for row in rows:
        align(row)
        progress.advance(task)
```

`disable=not ANIMATE` gives clean logs in CI; print a summary line after the block so non TTY runs still see completion. For parallel work, one task per worker plus an overall task; workers report through a queue, the main thread advances (Rich is not thread safe for concurrent `print`; a single writer is).

## Streaming and REPL (shape 3)

- Transcript: `ui.err.print(...)` for frozen content, `Live(renderable, console=ui.err, refresh_per_second=12, transient=False)` for the current message; update the renderable with the accumulated text and let Rich re wrap. For long messages, freeze completed paragraphs by printing them above the Live region (`live.console.print`) and keep only the current paragraph live.
- Markdown: `rich.markdown.Markdown(text, code_theme="monokai")` on the final message; while streaming, render plain text with inline bold and code only.
- Input: `prompt_toolkit.PromptSession` with history (`FileHistory`), multi line via `Shift+Enter` (needs kitty protocol; fall back to `Meta+Enter`), completer for `/commands` and `@files`, bracketed paste is on by default.
- Permission prompt: `questionary.select` with the dangerous option not first, or a Rich panel plus `Prompt.ask` with choices.
- `--print` mode: no `Live`, no prompts, text to stdout, events as JSON lines with `--json`.

## Full screen (shape 4): Textual

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import DataTable, Footer, Header, Log, Static


class Monitor(App):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    DataTable { width: 2fr; border: round $primary; }
    Log { width: 1fr; border: round $secondary; }
    DataTable:focus, Log:focus { border: round $accent; }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("slash", "filter", "Filter", key_display="/"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            yield DataTable(cursor_type="row", zebra_stripes=True)
            yield Log(highlight=True)
        yield Footer()

    def on_mount(self) -> None:
        self.theme = "tokyo-night"
        table = self.query_one(DataTable)
        table.add_columns("NAME", "STATUS", "DURATION")
        self.set_interval(2.0, self.action_refresh)

    async def action_refresh(self) -> None:
        # Off thread work: use run_worker or @work(thread=True) so the UI never blocks
        rows = await self.run_worker(load_runs, thread=True).wait()
        table = self.query_one(DataTable)
        table.clear()
        for r in rows:
            table.add_row(r["name"], r["status"], r["duration"], key=r["name"])
```

Textual provides: CSS layout with docking and grid, mouse and keyboard with hit testing, focus management, `Screen` and `ModalScreen` for overlays, built in themes with `App.theme`, `@work` for background tasks, `textual run --dev` with the devtools console, `snap_compare` for snapshot tests, `textual serve` to run the same app in a browser. Do not hand roll any of this in a Textual app. Keep the `App` thin: business logic in plain modules, widgets call into them via workers.

## Gradients and banners

```python
from rich_gradient import Gradient
ui.err.print(Gradient("tool 1.4.0", colors=["#3DDBC7", "#38BDF8", "#5B9CFF", "#8B7BFF", "#C084FC"]), justify="left")
```

Only on `ui.err.is_terminal and ui.err.color_system == "truecolor"`; otherwise print the name in `[accent]`.

## Testing

- `typer.testing.CliRunner` for commands; assert on `result.stdout` (clean) and `result.stderr` separately (`mix_stderr=False`).
- Set `COLUMNS=80` and `NO_COLOR=1` in tests for stable snapshots; add one test with `FORCE_COLOR=3` asserting escape sequences are present.
- Textual: `async with app.run_test(size=(80, 24)) as pilot: await pilot.press("j", "enter")` and `snap_compare`.
- `scripts/check_cli.py -- tool status` in CI for TTY and pipe behavior.

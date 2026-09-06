#!/usr/bin/env python3
"""Render every component of the Python template so the identity can be seen.

Usage:
  python scripts/demo_gallery.py            # full gallery, animated on a TTY
  python scripts/demo_gallery.py --json     # data path only (what a pipe gets)
  python scripts/demo_gallery.py --fast     # no sleeps (for check_cli.py)
  python scripts/demo_gallery.py --version

Also serves as the reference implementation of a "script" archetype CLI:
banner on stderr, progress on stderr, result table on stdout, --json.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "assets", "templates", "python"))
os.environ.setdefault("CLI_CRAFT_TOOL_NAME", "gallery")

import ui  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.tree import Tree  # noqa: E402

EXAMPLES = """examples:
  gallery                 render the full gallery
  gallery --json          machine readable summary
  gallery --fast | cat    what a pipe receives (no ANSI)
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gallery", description="cli-craft component gallery.",
        epilog=EXAMPLES, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="emit a JSON summary on stdout")
    parser.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                        help="color output (default auto: TTY and NO_COLOR decide)")
    parser.add_argument("--fast", action="store_true", help="skip sleeps and animation")
    parser.add_argument("--version", action="version", version="gallery 1.0.0")
    args = ui.parse_args(parser, argv)  # exit 2 with a hint on usage errors
    ui.apply_color_flag(args.color)
    ui.install_signal_handlers()
    if args.fast:
        os.environ["GALLERY_NO_ANIMATION"] = "1"

    delay = 0.0 if args.fast else 0.05
    items = [("AMPidentifier", 1240, "ok"), ("decryptAMP", 388, "ok"),
             ("LAMELLA", 97, "warn"), ("ELROND", 0, "err")]
    data = {"tool": "gallery", "items": [dict(name=n, count=c, status=s) for n, c, s in items]}

    if args.json:
        ui.emit(data, as_json=True)
        return 0

    # 1. banner: ASCII art title, animated slogan, general options
    ui.banner(
        "cli-craft",
        "terminal tools that read well and pipe cleanly",
        options=[("gallery", "render every component"),
                 ("--json", "machine readable summary"),
                 ("--color", "auto, always or never"),
                 ("--help", "usage and examples")],
        reveal_ms=0 if args.fast else 1200,
    )

    # 2. status spinner
    with ui.status("Scanning peptide libraries"):
        time.sleep(delay * 6)

    # 3. progress with gradient tinted fill
    with ui.progress() as prog:
        task = prog.add_task("Scoring sequences", total=40)
        for _ in range(40):
            time.sleep(delay)
            prog.advance(task)

    # 4. messages
    ui.ok("4 libraries processed")
    ui.warn("LAMELLA returned fewer hits than expected")
    ui.info("results cached in ~/.cache/gallery")

    # 5. data on stdout: table on a TTY, JSON when piped
    table = Table(title=None, border_style="border", header_style="accent2",
                  show_edge=False, pad_edge=False, expand=False)
    table.add_column("library", style="fg")
    table.add_column("hits", justify="right", style="fg")
    table.add_column("status")
    for name, count, st in items:
        glyph = ui.G["ok" if st == "ok" else "warn" if st == "warn" else "err"]
        table.add_row(name, str(count), f"[{st}]{glyph} {st}[/]")
    ui.emit(data, renderable=table)

    # 6. tree and panel (stderr chrome, shown only on a TTY)
    if ui.env.stdout_tty:
        tree = Tree("[accent]results/[/]", guide_style="dim")
        run = tree.add("[fg]run_2026-09-06/[/]")
        run.add("[muted]scores.tsv[/]")
        run.add("[muted]summary.json[/]")
        ui.console.print(tree)
        ui.console.print(ui.panel("Next: [accent]gallery --json | jq '.items[]'[/]",
                                  title="next step"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

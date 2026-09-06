#!/usr/bin/env python3
"""Show the cli-craft palette or emit it for a stack.

Usage:
  python scripts/palette.py                # swatches in the current terminal
  python scripts/palette.py --contrast     # WCAG table for dark and light sets
  python scripts/palette.py --rich         # Python dict for rich.theme.Theme
  python scripts/palette.py --ink          # TypeScript object for Ink / chalk
  python scripts/palette.py --gradient N   # N interpolated stops (OKLCH), dark set

Stdlib only, reads assets/theme.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "..", "assets", "theme.json")
sys.path.insert(0, os.path.join(HERE, "..", "assets", "templates", "python"))


def load() -> dict:
    with open(THEME, encoding="utf-8") as fh:
        return json.load(fh)


def lum(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def swatches(t: dict) -> None:
    truecolor = os.environ.get("COLORTERM") in ("truecolor", "24bit") and "NO_COLOR" not in os.environ
    for mode in ("dark", "light"):
        print(f"{mode}:")
        for role, h in t[mode].items():
            r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
            block = f"\x1b[48;2;{r};{g};{b}m      \x1b[0m" if truecolor else "      "
            print(f"  {block} {role:10} {h}")
    print("gradient (dark):", " ".join(t["gradient"]["aurora_dark"]))
    print("gradient (light):", " ".join(t["gradient"]["aurora_light"]))


def contrast_table(t: dict) -> None:
    print(f"{'role':10} {'dark/#000':>10} {'dark/panel':>11} {'light/#FFF':>11} {'light/panel':>12}")
    for role in t["dark"]:
        if role.startswith("bg") or role == "border":
            continue
        d, l = t["dark"][role], t["light"][role]
        print(f"{role:10} {contrast(d, '#000000'):10.2f} {contrast(d, t['dark']['bg_panel']):11.2f} "
              f"{contrast(l, '#FFFFFF'):11.2f} {contrast(l, t['light']['bg_panel']):12.2f}")


def emit_rich(t: dict) -> None:
    print("from rich.theme import Theme\n")
    for mode in ("dark", "light"):
        print(f"{mode.upper()} = Theme({{")
        for role, h in t[mode].items():
            if role.startswith("bg"):
                continue
            style = f"bold {h}" if role in ("ok", "err", "warn", "accent") else h
            print(f'    "{role}": "{style}",')
        print("})\n")


def emit_ink(t: dict) -> None:
    print("// Theme roles for Ink <Text color=...> and chalk.hex(...)")
    print("export const theme = {")
    for mode in ("dark", "light"):
        print(f"  {mode}: {{")
        for role, h in t[mode].items():
            print(f'    {role}: "{h}",')
        print("  },")
    print(f'  gradient: {json.dumps(t["gradient"]["aurora_dark"])},')
    print("} as const;")


def emit_gradient(t: dict, n: int) -> None:
    import ui  # type: ignore  # template module, OKLCH sampler
    stops = t["gradient"]["aurora_dark"]
    for i in range(n):
        print(ui._sample(i / n * 0.6, stops))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contrast", action="store_true")
    ap.add_argument("--rich", action="store_true")
    ap.add_argument("--ink", action="store_true")
    ap.add_argument("--gradient", type=int, metavar="N")
    a = ap.parse_args()
    t = load()
    if a.contrast:
        contrast_table(t)
    elif a.rich:
        emit_rich(t)
    elif a.ink:
        emit_ink(t)
    elif a.gradient:
        emit_gradient(t, a.gradient)
    else:
        swatches(t)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Downstream closed early (head, less): exit quietly like a Unix tool.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)

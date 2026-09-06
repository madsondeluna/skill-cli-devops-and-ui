#!/usr/bin/env python3
"""Fail if any file in the skill contains an emoji or an em dash.

Both are house rules: emojis break column alignment, fonts and screen readers
in a terminal, and em dashes are not used in this documentation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "skills"
BAD_DASHES = {"\u2014", "\u2013"}


def is_emoji(ch: str) -> bool:
    o = ord(ch)
    return 0x1F300 <= o <= 0x1FAFF or 0x2600 <= o <= 0x26FF or o in (0x2705, 0x274C, 0x2728, 0x2B50)


def main() -> int:
    findings = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append((path, 0, "not valid UTF-8"))
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if BAD_DASHES & set(line):
                findings.append((path, n, "em or en dash"))
            if any(is_emoji(c) for c in line):
                findings.append((path, n, "emoji"))
    for path, n, what in findings:
        print(f"{path.relative_to(ROOT.parent)}:{n}: {what}", file=sys.stderr)
    print(f"{len(findings)} finding(s)", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

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


# macOS writes an AppleDouble sidecar (._name) next to every file edited on a
# non native volume, and those are not UTF-8. They are already in .gitignore;
# the walk has to skip them too, or the check fails on files git never sees.
SKIP_DIRS = {"__pycache__", ".git", "dist", "build", ".venv", ".pytest_cache", ".ruff_cache"}
SKIP_SUFFIXES = {".skill", ".zip", ".png", ".jpg", ".gif", ".pdf", ".woff", ".woff2"}


def skipped(path: Path) -> bool:
    if SKIP_DIRS & set(path.parts):
        return True
    if path.name.startswith("._") or path.name == ".DS_Store":
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def main() -> int:
    findings = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or skipped(path):
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

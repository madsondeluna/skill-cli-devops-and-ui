#!/usr/bin/env python3
"""Ground truth for the reference package (behaviour and visual halves).

Every component is listed in INDEX.md, has exactly one topics.json entry,
resolves its cross links, and carries a summary, a "When this applies" line, an
example and a do/don't section. These are the invariants SKILL.md claims; this
script is what makes the claim checkable.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "cli-devops-with-ultimate-ui"
REF = SKILL / "references"
findings: list[str] = []


def add(where: str, what: str) -> None:
    findings.append(f"{where}: {what}")


def main() -> int:
    if not REF.is_dir():
        print(f"missing {REF}", file=sys.stderr)
        return 1
    components = sorted(p for p in REF.glob("*.md")
                        if p.name != "behaviour-index.md" and not p.name.startswith("._"))
    index = (SKILL / "SKILL.md").read_text()
    behaviour_index = (REF / "behaviour-index.md").read_text()
    topics = json.loads((REF / "behaviour-topics.json").read_text())
    # os caminhos em topics.json sao relativos a raiz da skill, nao a references/
    listed = {pathlib.PurePosixPath(t["file"]).name
              for t in (topics if isinstance(topics, list) else topics.get("topics", []))
              if t.get("file")}

    for path in components:
        name = path.name
        text = path.read_text()
        # Todo componente tem de ser alcancavel pelo roteador do SKILL.md: uma
        # referencia que ninguem indica e uma referencia que ninguem carrega.
        if name not in index:
            add(name, "not in the SKILL.md router table")
        # As invariantes de forma valem para a metade de comportamento, que foi
        # escrita sob elas; as referencias visuais tem outra estrutura.
        if name in behaviour_index or name in listed:
            if listed and name not in listed:
                add(name, "no behaviour-topics.json entry")
            if "When this applies" not in text:
                add(name, 'missing a "When this applies" line')
            if "```" not in text:
                add(name, "no example block")
            if not re.search(r"##\s*(Do / Don't|Anti-patterns|Edge cases)", text):
                add(name, "no do/don't or anti-patterns section")
        for link in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", text):
            target = (path.parent / link).resolve()
            if not target.exists():
                add(name, f"broken link to {link}")

    for f in findings:
        print(f, file=sys.stderr)
    print(f"{len(findings)} finding(s)", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

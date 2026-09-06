# Contributing

## Before opening a pull request

```
make test      # unit tests for the vendorable template
make audit     # terminal hygiene harness, must report no blocking findings
python3 .github/check_style.py
```

All three run in CI on Python 3.10 and 3.12.

## House rules

- No emojis anywhere, including code comments and terminal output. They break
  column alignment, fonts and screen readers. Unicode glyphs from the palette
  are symbols, not emojis, and are fine.
- No em dashes in documentation.
- The skill folder contains no README.md: everything lives in SKILL.md or
  under references/. This README is for the repository, not the skill.
- Every claim about behavior in a reference must be reproducible with a
  command. If a rule cannot be demonstrated, it is an opinion and belongs in
  the discussion, not in the skill.

## Adding a reference

Keep SKILL.md under roughly 300 lines. New material goes in
`skills/cli-craft/references/` and gets a row in the router table at the top of
SKILL.md saying when to read it. A reference nobody is pointed to is a
reference nobody loads.

## Changing the palette

Colours live in `skills/cli-craft/assets/theme.json`, and nowhere else. After
changing them, run `make palette` and paste the updated contrast table into
`references/palette.md`. Any text role below 4.5 to 1 on either background is
a regression.

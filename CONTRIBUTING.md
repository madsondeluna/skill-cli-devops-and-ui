# Contributing

## Before opening a pull request

```
make test      # unit tests for the vendorable template
make audit     # terminal hygiene harness, must report no blocking findings
python3 .github/check_style.py
```

After changing anything under `skills/`, reinstall before testing the skill in
Claude Code, otherwise the loaded copy is the old one:

```
make install
make verify-install
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

## Renaming the skill

The skill name appears in the folder name, the `name` field of SKILL.md, the
`SKILL` variable in the Makefile, the packaged file name and the README. It must
not appear in a public identifier such as an environment variable: those name
the tool being built, not the skill, and a rename leaves them pointing at a
brand that no longer exists. `CLI_TOOL_NAME` is deliberately unbranded.

After a rename, run `make install` and `make verify-install`; a stale installed
copy under `~/.claude/skills` keeps the old name alive and the model will list a
skill it cannot load.

## Adding a reference

Keep SKILL.md under roughly 300 lines. New material goes in
`skills/cli-devops-with-ultimate-ui/references/` and gets a row in the router table at the top of
SKILL.md saying when to read it. A reference nobody is pointed to is a
reference nobody loads.

## Changing the palette

Colours live in `skills/cli-devops-with-ultimate-ui/assets/theme.json`, and nowhere else. After
changing them, run `make palette` and paste the updated contrast table into
`references/palette.md`. Any text role below 4.5 to 1 on either background is
a regression.

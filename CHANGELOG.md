# Changelog

Notable changes are documented here. The format follows Keep a Changelog and
versions follow semantic versioning.

## [1.0.0] - 2026-09-06

First release.

### Added

- Two operating modes with opposite defaults: build mode for new tools, and
  audit mode for tools that already exist and work, where the skill reports
  and proposes without rewriting what is validated.
- Visual identity `aurora` (teal to blue to violet), with the WCAG contrast of
  every text role documented and recomputable from `assets/theme.json`.
- Banner in the ANSI Shadow font with a wipe in and a highlight sweep, with
  three levels of degradation down to a single line.
- Cycling gradient spinner and progress bar with sub cell precision.
- Agent style thinking indicator: pulsing glyph, rotating verb, elapsed time,
  counter and interrupt hint.
- Launcher: filterable select list with a permanent keybinding footer.
- Vendorable templates for Python (Rich) and TypeScript (Ink), plus a README
  template carrying a complexity and memory table.
- `check_cli.py`, a pseudo terminal harness covering pipe, NO_COLOR, CI, help,
  version, JSON, usage errors and Ctrl-C.
- Twelve reference documents: principles, palette, anatomy, motion, launcher,
  interactive TUIs, agent UIs, engineering, MCP workflow, review checklist and
  five language stacks.

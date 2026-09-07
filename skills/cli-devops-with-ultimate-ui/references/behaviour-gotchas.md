# Behaviour gotchas

Recurring failure modes when relying on the behaviour references, and what to do
instead. Read alongside `../SKILL.md`.

**When this applies:** before turning any recommendation in the behaviour half
into code, and whenever a rule here meets a convention the target project or
platform already has.

- This skill is design GUIDANCE, not a spec to copy verbatim; adapt each recommendation to the target platform (Unix vs Windows/PowerShell) and the program's existing conventions.
- It is not an argument-parser API reference; verify framework-specific behavior (argparse, click, typer, cobra, clap, commander, oclif) against that framework's own docs.
- When a recommendation conflicts with an established project or platform convention, surface the tradeoff rather than silently overriding it.
- Distinguish interactive/TTY behavior from non-interactive/CI behavior; a UX choice that helps at a terminal can break pipes and scripts.

## Do / Don't

- **Do** state the tradeoff out loud when this skill and an existing convention
  disagree, and let the user decide.
- **Do** verify parser specific behaviour against the framework's own
  documentation before promising it.
- **Don't** copy a recommendation verbatim into a platform it was not written
  for; Unix and Windows differ, and the references say where.
- **Don't** invent a convention to fill a gap. Say the gap exists.

```
# The shape of an honest gap
Matched the existing raw JSON output for consistency with `list-projects`.
Noticed: no --help on any command, so nothing is discoverable.
Recommendation: add --help across all commands in a follow up?
```

## Related

`behaviour-index.md` - `behaviour-review.md` - `../SKILL.md`

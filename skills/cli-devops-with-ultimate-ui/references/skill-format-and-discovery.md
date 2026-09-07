# Skill Format and Discovery (Codex & Claude)

How this skill is structured so both Codex and Claude discover and load it, following the Agent Skills
open standard. Useful when creating, moving, or debugging discovery of any skill in this repo: and
the reason the package is mirrored to two locations.

**When this applies:** authoring or relocating a skill, fixing a skill that won't trigger, or
adapting a skill for both Codex and Claude.

## The Agent Skills standard

- A skill is a folder with a required `SKILL.md`
 (YAML frontmatter: at minimum `name` and `description`, plus instructions), optionally bundling
 `scripts/`, `references/`, and `assets/`. The Agent Skills format is an open standard adopted across
 many agents.
- **Progressive disclosure** in three stages: (1) **Discovery**, only `name` + `description` are
 loaded at startup; (2) **Activation**: when a task matches the description, the full `SKILL.md`
 loads; (3) **Execution**: referenced files/scripts load on demand. Keep `SKILL.md` lean and route
 detail into `references/`.

## Discovery locations

- Codex searches, by scope: `$CWD/.agents/skills`, `$CWD/../.agents/skills`,
 `$REPO_ROOT/.agents/skills`, `$HOME/.agents/skills`, `/etc/codex/skills`, then bundled.
- Claude uses `.claude/skills/<name>/SKILL.md` (and can be invoked
 directly with `/<name>`).
- This is why the package lives at `.agents/skills/cli-design/` (Codex-native, the source of truth)
 and is mirrored to `.claude/skills/cli-design/` (Claude-native). The identical `SKILL.md` works for
 both because they share the open standard.

## Frontmatter rules

- `name`: short, lowercase, matches the folder (`cli-design`).
- `description`: **this is the trigger.** Both agents match a task against it for implicit invocation,
 so make it deliberately trigger-rich (name the task and the concrete phrases/contexts/file types
 that should invoke it, including when the user doesn't say the skill's name).
- The `description` is truncated if large: capped at roughly 2% of the
 context window or about 8,000 characters; stay well under.

```yaml
---
name: cli-design
description: >-
  Use when designing/reviewing terminal UX ... (trigger-rich; see this skill's SKILL.md)
---
```

## Decision rules

- One job per skill, with imperative step-by-step instructions (Codex). Put bulky reference material
 in `references/` so it loads only when needed (progressive disclosure).
- Keep `name` unique within a scope: if two skills share a `name`, both
 appear (no merge).
- Symlinks are supported (Codex); restart the agent if changes don't appear.

## Keeping the two copies in sync

- `.agents/skills/cli-design/` is authoritative. After changing it, re-mirror to
 `.claude/skills/cli-design/` so SKILL.md, all `references/`, and the JSON metadata match. The
 package's verifier checks the two trees are identical (see `behaviour-review.md`,
 `testing-cli-ux.md`).

## Edge cases / anti-patterns

- A skill that won't trigger usually has a weak `description`: enrich the triggers, don't rely on the
 user naming it.
- Don't put task artifacts/logs inside the skill folder; keep the folder to SKILL.md + bundled
 resources.

## Do / Don't

- **Do** keep SKILL.md lean and route detail through `references/behaviour-index.md`.
- **Do** write a pushy, trigger-rich `description` under the size cap.
- **Don't** duplicate the skill name within a scope.
- **Don't** let the two location copies drift.

## Related

`../SKILL.md` · `behaviour-index.md` · `behaviour-review.md` · `testing-cli-ux.md`

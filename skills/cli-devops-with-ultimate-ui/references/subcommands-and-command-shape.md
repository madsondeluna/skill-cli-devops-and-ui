# Subcommands and Command Shape

How to structure a multi-command tool: grouping commands into areas, naming them consistently, and
choosing word order. The reconciled default is **noun-verb / area-grouping**, with verb-noun noted as a common alternative. Consistency across subcommands matters
more than the specific scheme.

**When this applies:** designing or reviewing a tool with more than one command: command groups,
naming, word order, aliases, or whether to add subcommands at all.

## Principles

- **Use subcommands to tame a large tool** or to combine related tools under one name. A grouping command (area) should identify a group, not perform an action by itself:
 `tool container` lists/identifies; `tool container create` acts.
- **Be consistent across subcommands:** same flag names for the same concepts, same
 output shape, same error style. Consistency is the single biggest usability lever here.

## Decision rules

### Word order: recommended default: noun-verb / area-grouping
- **Recommended:** group by the object (noun/area), then the action (verb):
 `tool <area> <verb>` e.g. `docker container create`, `git remote add`, `dotnet tool install`. This organizes help, scales as the tool grows, and matches most large multi-command CLIs.
- **Alternative: verb-noun:** `tool create project` reads like natural
 task phrasing and is used by some tools. If you choose it, apply it everywhere.
- **Rule:** pick one order and never mix. Mixed order is the most common consistency bug.

```
# Noun-verb / area-grouping (recommended default)
$ tool app create myapp
$ tool app scale myapp --replicas 3
$ tool db backup myapp
```

### Implicit area
- Many tools have an implicit area (dotnet→project, docker→image), so
 `tool build` works without naming it. If you allow both `tool build` and `tool image build`, define
 two commands that do the same thing: the explicit form gives you help and tab-completion for the
 group.

### Naming
- Lowercase, single words; kebab-case only when a multi-word name is unavoidable
 (`pg:credentials:repair-default`). Colons are one valid nesting separator;
 spaces (`git remote add`) are the more common one.
- The root of an area should list its members, e.g. `tool config` lists config vars: **don't** add a
 redundant `*:list` command.
- Avoid near-synonym commands ("update" vs "upgrade"); disambiguate or pick one.

## Windows / PowerShell callouts

- Think of the command line like a REST API: consistent rules make it
 learnable; once shipped it's hard to change because users script it. PowerShell's own convention is
 `Verb-Noun` cmdlets (`Get-Item`) from an approved verb list: if you also ship cmdlets, follow that;
 for a cross-platform argv CLI, keep the noun-verb subcommand scheme identical on both OSes.

## Edge cases / anti-patterns

- **Don't add a catch-all subcommand** (assume `run` when the first arg is unrecognized): you can
 never later add a command with that name without breaking scripts.
- **Don't allow arbitrary prefix abbreviation** (`tool ins` → `install`): it traps you from adding
 any command starting with those letters. Use explicit, stable aliases instead.
- Deep nesting (4+ levels) hurts discoverability; flatten or group.

## Do / Don't

- **Do** keep flag names and output identical across subcommands.
- **Do** organize help by area and frequency (see `help-and-usage.md`).
- **Don't** mix verb-noun and noun-verb in the same tool.
- **Don't** create `*:list`/`*:show` when the area root can list.

## Related

`arguments-and-flags.md` · `help-and-usage.md` · `output-and-formatting.md` ·
`config-env-and-precedence.md`

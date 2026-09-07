# Help and Usage Text

Designing `-h`/`--help`, the usage synopsis, examples, and discovery aids ("did you mean"). Help is
the primary discovery surface: lead with examples, show concise help by default when input is
missing, print help to stdout, and support per-subcommand help.

**When this applies:** designing or reviewing help output, usage synopsis notation, man pages,
no-argument behavior, or typo/suggestion handling.

## Principles

- **Help is discovery.** Assume the user knows nothing about the tool; answer three
 questions fast: what it does, how to start, where to learn more.
- **Lead with examples.** Users reach for examples before prose; show real invocations
 and, when short, real output.
- **Print help to stdout** (not stderr) and exit 0 when help was explicitly requested. When help is shown because of a *usage error*, print to stderr and exit non-zero
 (see `errors-and-exit-codes.md`).

## Decision rules

### Trigger surfaces
- Show full help for `tool`, `tool --help`, `tool -h`. For multi-command tools also support
 `tool help`, `tool help <cmd>`, `tool <cmd> --help`, `tool <cmd> -h`.
- **Concise help by default** when a command needs arguments but got none: except
 genuinely interactive tools like `npm init`. Concise = one-line description, 1-2 example
 invocations, the most common flags, and "pass --help for more."
- **Don't overload `-h`**; when help is requested, render help and ignore other flags.

### What full help contains (template)
```
$ tool --help
tool v1.2.0: synchronize files between repositories

USAGE
  tool <command> [options]
  tool <source> <target>... [options]

EXAMPLES
  tool sync ./a ./b            # one-shot sync
  tool sync ./a ./b --watch    # keep syncing

COMMANDS
  sync        copy changes between paths
  config      manage settings
  help        show help for any command

FLAGS
  -h, --help        show help
  -q, --quiet       suppress non-essential output
      --json        machine-readable output
```
- Synopsis notation (POSIX-style): `tool [-adho] [-t | -w] [-M path] operand...`: `[ ]` optional,
 `|` mutually exclusive, `...` repeatable.
- Organize by frequency: most common commands/flags first. Use terminal-independent
 formatting (bold headings), not walls of escape codes.

### Discovery aids
- **Suggest corrections** on typos/unknown commands ("Did you mean…"), and point to the
 command list, but suggest, don't auto-run, especially for state-changing actions:
```
$ tool buld
Error: unknown command "buld".
Did you mean "build"?  Run `tool help` to list commands.
```
- Provide a support/website link in top-level help; link to web docs from subcommand help.

### Shell completion (UX)
Tab-completion is a discovery aid; design for it even though the generator internals are out of scope.
- Prefer flags over bare positionals partly because they enable better autocomplete:
 e.g. `tool --app <tab><tab>` can complete app names because the parser knows the next value's type. See `arguments-and-flags.md`.
- Defining the explicit grouping/area command (not just an implicit
 area) gives you help *and* tab-completion for that group for free. See
 `subcommands-and-command-shape.md`.
- Ship a `completion` command that generates the shell completion
 script (as in the help template: `completion Generate autocompletion script`), so users can opt in
 per shell.

### Documentation beyond `--help`
- Offer both auto-generated **reference** (generated from the parser, so it can't drift) and human
 **documentation**; web docs (searchable/linkable) plus terminal docs/man pages (offline, version-
 matched). Make man pages reachable from the tool (`tool help <cmd>` ≈
 `man tool-cmd`).

## Standards baseline

- Always support `--help` and `--version`. Keep long-option names consistent across tools (e.g.,
 verbose is always `--verbose`), reusing conventional names where they exist (see
 `arguments-and-flags.md`).

## Windows / PowerShell callout

- PowerShell cmdlets surface help via comment-based help and `Get-Help`/`-?`; an argv-style CLI on
 Windows should still implement `--help`/`-h` identically to Unix. Keep one help system as the
 source of truth across OSes.

## Edge cases / anti-patterns

- **Don't page help by default**: users may not know how to scroll/search/quit; let them pipe to a
 pager themselves. See `output-and-formatting.md` for when paging *is* appropriate.
- If the tool expects piped stdin but stdin is a TTY, show help or exit instead of hanging silently. See `interactivity-tty-and-ci.md`.

## Do / Don't

- **Do** lead with examples and show the most common path first.
- **Do** print explicit-help to stdout/exit 0; usage-error help to stderr/exit non-zero.
- **Don't** dump every flag in concise/default help.
- **Don't** auto-execute a guessed command.

## Related

`arguments-and-flags.md` · `subcommands-and-command-shape.md` · `errors-and-exit-codes.md` ·
`output-and-formatting.md` · `accessibility-and-i18n.md`

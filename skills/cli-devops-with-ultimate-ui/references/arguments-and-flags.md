# Arguments and Flags

Designing the inputs a command accepts: positional **arguments** (order-sensitive) and named
**flags/options** (order-independent, optionally valued). Prefer flags for clarity, follow the
POSIX-style syntax baseline, reserve short flags for common uses, and never accept secrets on the
command line. Equal-weight notes cover where Windows/.NET diverges from POSIX.

**When this applies:** designing or reviewing how a command takes input: positional args vs flags,
short vs long options, defaults, required vs optional, parsing libraries, or passing secrets.

## Principles

- **Use an argument-parsing library** rather than hand-rolling. You get help, error
 messages, and suggestions for free.
- **Prefer flags to positional arguments.** Flags are explicit, self-documenting, order-
 independent, and easier to evolve without breaking scripts.
 Positional args are fine for one obvious operand or simple multi-file actions.
- **Provide a long form for every flag**, and a short form only for the common ones. Long forms make scripts readable; short forms speed interactive use.

## Decision rules

### Argument vs flag
- One obvious operand, or a list of like things → positional is fine: `rm a.txt b.txt`, `rm *.txt`.
- Two operands with a fixed, well-known order → positional acceptable: `cp <source> <dest>`.
- Anything else (two+ unlike values, optional inputs, future growth) → **use flags**.

```
# Unclear which app is source vs target:
$ tool fork destapp -a sourceapp
# Clear and order-independent:
$ tool fork --from sourceapp --to destapp
```

### Short-flag namespace
- Reserve single letters for frequent options; keep a stable short↔long mapping. Standard names:
 `-a/--all`, `-d/--debug`, `-f/--force`, `-h/--help` (help only, never overload it),
 `-o/--output`, `-q/--quiet`, `-u/--user`, `-v` (pick verbose **or** version), `-n/--dry-run`,
 `--json`, `--no-input`, `--version`.
- In .NET CLI, reserve `-i`=`--interactive`, `-o`=`--output`,
 `-v`=`--verbosity`; minimize short aliases overall.

### Defaults
- **Make the default right for the majority.** Most users never discover flags, so a bad
 default harms most people. Booleans get sensible defaults and need no explicit value
 (`--dry-run`, `--force`).

### Naming the flags
- Lowercase, kebab-case for multi-word (`--additional-probing-path`); be consistent about
 pluralization for multi-valued options; nouns for options, verbs for action commands.

### Reuse standard long-option names
- When an option matches a conventional meaning, use the standard long name
 so user expectations transfer across tools. Common
 ones to reuse rather than reinvent:

 | Option | Conventional meaning |
 | --- | --- |
 | `--help` / `--version` | usage info / version number |
 | `--verbose` / `--quiet` (`--silent`) | more progress output / suppress usual output |
 | `--output` | output file name |
 | `--force` | override/force the operation |
 | `--interactive` | prompt before acting |
 | `--recursive` | operate on directories recursively |
 | `--all` | include all items |
 | `--dry-run` | describe changes without doing them |
 | `--no-color` / honor `NO_COLOR` | disable color (see `color-and-styling.md`) |

 Pick the standard name when the meaning fits; only coin a new name for genuinely new behavior.

## POSIX-style option syntax (the Unix contract)

- Options are a `-` plus a single alphanumeric; `-W` is reserved for vendors.
- Options without arguments may be grouped: `-abc` == `-a -b -c`.
- `--` ends options; everything after is operands even if it starts with `-`.
- Options should precede operands; option order shouldn't matter unless documented mutually exclusive.
- **Optional option-arguments:** by convention, option-arguments should *not* be
 optional, yet real tools ship `--color[=when]`. If you must, attach the value (`--color=auto`) and
 document it; do not rely on a following token. For optional-value flags, accept an explicit word
 like `none` rather than a blank (`ssh -F none`).
- **Support `-`** to mean stdin/stdout in file operands: see
 `streams-and-piping.md`.

## Windows / PowerShell callouts

- .NET CLI does **not** support omitting the delimiter for a single-
 char alias (no `-pVALUE`; use `-p VALUE`), does **not** accept multiple args for one option without
 repeating it, and some boolean options ignore the passed value (`--no-restore false` acts like
 `--no-restore`). Native PowerShell cmdlets use `-Name value` (single dash, PascalCase): when
 designing a cross-platform CLI, pick POSIX `--long`/`-x` and keep it identical on both OSes rather
 than mixing styles.
- Windows tools historically used `/flag`; for portable modern CLIs prefer `--long` everywhere and,
 at most, also accept `/flag` on Windows.

## Edge cases

- A flag that can repeat (`-v -v -v` or `-vvv` for verbosity): define whether repetition stacks.
- Negatable booleans: offer `--feature`/`--no-feature` for clarity.
- Globbing is expanded by the shell on Unix but **not** by `cmd.exe`/PowerShell the same way: if you
 accept patterns, document whether the program expands them.

## Do / Don't

- **Do** make args/flags/subcommands order-independent where possible (users append options on re-run).
- **Do** validate input early and fail with a clear message (see `errors-and-exit-codes.md`).
- **Don't** read secrets from flags: they leak into `ps` output and shell history. Use a
 `--password-file`, stdin, or a secret store. See `config-env-and-precedence.md`.
- **Don't** overload `-h`; when help is requested, show help and ignore other flags.
- **Don't** require a value-flag's argument as a loose following token if it can be confused with an
 operand.

## Related

`subcommands-and-command-shape.md` · `help-and-usage.md` · `config-env-and-precedence.md` ·
`streams-and-piping.md` · `errors-and-exit-codes.md`

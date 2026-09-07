# Principles

Distilled from clig.dev, the 12 factor CLI app guidelines, the Heroku and GitHub CLI style guides, and the patterns visible in Claude Code, Gemini CLI, Crush and lazygit. Apply all of them to every shape of tool.

## 1. Streams

| Stream | Carries |
|---|---|
| stdout | The result. Data, JSON, the thing the user asked for. |
| stderr | Everything about the process: progress, spinners, status, logs, prompts, warnings, errors, hints. |

Consequence: `tool | jq .` and `tool > file` always work, and the user still sees progress on screen because stderr is still the terminal.

Never print a spinner or a banner to stdout. Never print the result to stderr.

## 2. Capability detection

Compute once at startup, per stream:

```
is_tty(stream)        isatty(fd)
color_level(stream)   none | basic16 | ansi256 | truecolor
unicode               locale is UTF-8 (LANG, LC_ALL, LC_CTYPE contain "UTF-8")
width                 ioctl TIOCGWINSZ, fallback COLUMNS env, fallback 80
interactive           is_tty(stdin) and is_tty(stderr) and not CI and not --no-input
```

Color level resolution, in order:

1. `--color=never` or `NO_COLOR` set (any value, even empty): none
2. `--color=always` or `FORCE_COLOR` set: at least basic16 (FORCE_COLOR=2 ansi256, 3 truecolor)
3. not a TTY: none
4. `TERM=dumb`: none
5. `COLORTERM` in (truecolor, 24bit): truecolor
6. `TERM` contains 256color: ansi256
7. otherwise basic16

CI systems (GitHub Actions, GitLab) set `CI=true` and often support color but not cursor movement. Treat CI as: color allowed if FORCE_COLOR, no live regions, print the final state of a progress bar once.

## 3. Structured output

Any command whose output someone might parse gets `--json`. Rules:

- One JSON document on stdout, nothing else on stdout.
- Stable keys, snake_case, documented.
- Errors in JSON mode are also JSON on stdout with a non zero exit: `{"error": {"code": "not_found", "message": "..."}}`.
- Lists as arrays, never as newline separated objects, unless the flag is explicitly `--jsonl`.
- `--plain` (or `--terse`) is the human readable but decoration free form: tab separated, no color, no box drawing. Useful for `cut` and `awk`.

## 4. Arguments and configuration

Precedence, highest first: command line flags, environment variables (`TOOL_*` prefix), project local config (`./.toolrc` or `./tool.toml`, found by walking up from the working directory), user config (XDG: `$XDG_CONFIG_HOME/tool/config.toml`), system config (`/etc/tool/config.toml`), built in defaults. Each layer overrides the one below it, key by key, not file by file: a project file that sets one option does not discard the user file.

Provenance is part of the contract. Under `--verbose` print which files were found, in which order, and the effective value of each option with the layer it came from. Configuration that cannot be traced is configuration that gets debugged by deletion.

- Flags have long names always, short names for the five most common.
- Boolean flags accept `--no-` prefix negation.
- Positional arguments only for the obvious primary input. Everything else is a flag.
- Read from stdin when the input argument is `-` or missing and stdin is not a TTY.
- `--dry-run` for anything destructive. `--yes` / `-y` to skip confirmations. `--quiet` / `-q` suppresses non essential stderr. `--verbose` / `-v` adds detail, `-vv` adds debug.
- Secrets are never flags (they leak into shell history and `ps`). Use env vars or files.

## 5. Help

`--help` is the most read screen of the tool. Structure:

```
tool - one line purpose

Usage:
  tool <command> [options]

Examples:
  tool run pipeline.nf --profile docker
  tool status --json | jq .state
  cat ids.txt | tool fetch -

Commands:
  run       Execute a pipeline
  status    Show the last run
  init      Create a config file

Options:
  -c, --config <path>   Config file (default: ~/.config/tool/config.toml)
  -q, --quiet           Only print errors
      --json            Machine readable output
      --color <when>    auto, always, never (default: auto)
  -h, --help            Show help
  -V, --version         Show version
```

Examples come first because they are what people copy. Group options by purpose when there are more than eight. Color the help on a TTY (command names in accent, flags in muted) and keep it aligned when piped.

`tool` with no arguments on a TTY prints the help. With piped stdin it processes stdin.

## 6. Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Runtime failure (the operation could not complete) |
| 2 | Usage error (bad flags, missing argument) |
| 3 to 125 | Tool specific, documented in `--help` and README |
| 126 | Command found but not executable |
| 127 | Command not found |
| 130 | Interrupted by Ctrl+C (128 + SIGINT) |

Usage errors print the one line error and a hint to run `--help`, not the full help.

## 7. Errors

Format on stderr:

```
error: <what failed, in one line, lowercase after the prefix>
  <context line: path, value, expected vs got>
  hint: <the single most likely fix>
```

- Prefix with the tool name only when the tool is likely to run inside other tools: `tool: error: ...`.
- Never dump a stack trace by default. `--verbose` or `TOOL_DEBUG=1` shows it.
- Unknown input gets a suggestion, not just a rejection. On an unknown
  subcommand or flag, compute the edit distance against the known names and
  offer the closest one when it is within two edits: `unknown command 'statsu'`
  then `did you mean 'status'?`. When the value comes from a closed set, list
  the valid values instead of guessing. This turns a dead end into one
  keystroke of recovery, and it is the single cheapest UX improvement in a CLI.
- A confirmation states the blast radius before asking: the count, the names
  when few, and what is irreversible. `delete 47 runs from project amp (cannot
  be undone)` then the prompt. A confirmation that only says "are you sure"
  teaches the user to type y without reading. `--force` or `--yes` skips it and
  is what non interactive callers must use; never auto confirm on their behalf.
- Errors from external commands are relayed with their exit code and the command that was run.
- Warnings use `warning:` in the warn color and never stop execution.

## 8. Interactivity

Prompts are a convenience, never a requirement. Before prompting check `interactive`. If false, exit 2 with:

```
error: missing --name (stdin is not a terminal, cannot prompt)
  hint: pass --name <value> or set TOOL_NAME
```

Confirmations for destructive actions default to No. `--yes` bypasses. Pressing Ctrl+C in a prompt exits 130 cleanly.

## 9. Performance and feel

- Startup under 100 ms feels instant; lazy import heavy modules (Python: import inside the command function; Node: dynamic import).
- Show a spinner if an operation exceeds about 200 ms. Show a progress bar when the total is known. Show elapsed time when it exceeds 2 s.
- Print results incrementally when possible instead of buffering until the end.
- Long operations are cancellable and leave the system in a consistent state.

## 10. Do not

- Do not clear the screen in shapes 1 to 3. The user's scrollback is theirs.
- Do not print banners or logos on every invocation. A banner is acceptable once on an interactive REPL start, and only on a TTY.
- Do not use color as the only carrier of meaning: pair it with a glyph or a word (`ok`, `warn`, `error`).
- Never use emojis in output, help text, code comments or docs. They break alignment, fonts and screen readers. Unicode glyphs from the palette are fine.
- Do not write to the terminal from multiple threads without a single writer or a lock.
- Do not exceed the terminal width. Truncate with an ellipsis or wrap.

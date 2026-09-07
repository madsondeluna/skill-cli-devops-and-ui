# Review checklist

Use for auditing an existing CLI or TUI, and as the final pass on anything built with this skill. Order findings by severity: blocking (breaks scripting or leaves the terminal broken), major (wrong behavior in a common environment), minor (polish). For each finding give the evidence (the command run and what appeared), the rule it violates, and the fix.

Run `python scripts/check_cli.py -- <command...>` first when the tool is executable; it covers the mechanical items in sections A and B and prints a report to build on. Findings marked `info` are notes, not defects: they record something the tool does correctly under a different name, and the right response is to leave it alone. The exit code counts blocking findings only.

The harness is a first pass, not a verdict. It matches on text, so it can miss a capability that exists under a name it does not recognise. Before reporting anything as missing, confirm in the tool's own help and code that it is genuinely absent. Telling the author of a working tool to add something it already has is how an audit loses its credibility.

## Scenarios to run first

Before reading any code, drive the tool through these six invocations and keep
the output. Most findings in the sections below surface here, and a tool that
handles all six well is already above average.

| Invocation | What to look for |
|---|---|
| no arguments | does it teach, launch, or just error out |
| missing required argument | does it name the argument and how to pass it |
| invalid value | does it list the valid values or suggest the near match |
| `--help` | examples first, all flags documented, exit 0, fits 80 columns |
| unknown subcommand or flag | did you mean, and exit 2 |
| a valid run | is the result on stdout alone, and the chrome on stderr |

## A. Streams and scripting (blocking)

- [ ] Primary output on stdout only; status, progress, prompts, errors on stderr.
- [ ] `tool ... | cat` produces no ANSI escapes and no cursor movement.
- [ ] `tool ... 2>/dev/null` still yields the result.
- [ ] `NO_COLOR=1` disables color on both streams; `--color=never` too; `--color=always` and `FORCE_COLOR` enable it when piped.
- [ ] `--json` prints one valid JSON document, nothing else, on stdout; errors in JSON mode are JSON with a non zero exit.
- [ ] Exit codes: 0 success, 1 failure, 2 usage error, 130 on Ctrl+C.
- [ ] No prompt when stdin is not a TTY; a clear error names the flag to pass.
- [ ] `CI=true` produces no live redraws (no `\r` overwrites, no cursor up).
- [ ] `tool ... | head -1` exits quietly (BrokenPipe handled, no traceback).

## B. Terminal hygiene (blocking)

- [ ] Cursor visible after every exit path, including Ctrl+C during a spinner and an unhandled error.
- [ ] Alternate screen left, raw mode disabled, mouse tracking disabled, bracketed paste disabled, SGR reset, on every exit path including panic.
- [ ] Ctrl+Z suspends and resumes cleanly (shape 4).
- [ ] No output exceeds terminal width at 80 and at 40 columns; resize does not corrupt the layout; a reported width of 0 falls back to 80.
- [ ] `TERM=dumb` and `LANG=C` runs are readable (ASCII glyphs, no box drawing).

## C. Help and arguments (major)

- [ ] `--help` and `-h` on every command; leads with examples; options grouped; fits 80 columns.
- [ ] `--version` / `-V` prints name and version, nothing else, exit 0.
- [ ] Usage errors print one line plus a hint, not the full help, exit 2.
- [ ] Every prompt has a flag equivalent; every destructive action has `--dry-run` and `--yes`.
- [ ] Config precedence flags > env > file > defaults is documented and implemented; env vars are prefixed.
- [ ] Secrets never accepted as flags.
- [ ] Reads stdin on `-` or when stdin is piped and the input argument is omitted.

## D. Visual quality (major to minor)

- [ ] Semantic roles only; no raw colors scattered in code; theme overridable.
- [ ] Color never the only carrier: glyph or word accompanies it.
- [ ] Contrast reaches 4.5:1 on dark and light backgrounds (check the muted role, the usual failure).
- [ ] One accent per screen state; at most one gradient surface; no gradient on body text, tables, help or errors.
- [ ] Gradient stops and roles come from `assets/theme.json` (aurora); no ad hoc hex values in code.
- [ ] Status colors are always paired with a glyph or word (color is never the only channel).
- [ ] Alignment: columns padded, numbers right aligned, headers uppercase muted.
- [ ] Vertical rhythm: blank line between components, none inside.
- [ ] Errors follow `error: ... / hint: ...`; success is quiet; no exclamation marks, no emojis.
- [ ] Unknown commands and flags suggest the nearest valid name; closed sets list their values.
- [ ] Destructive confirmations state the count and what is irreversible before asking.
- [ ] Truncation with an ellipsis, paths truncated from the left.
- [ ] Hyperlinks via OSC 8 on TTY, plain URL when piped.

## E. Motion (major to minor)

- [ ] Spinner appears only after about 200 ms; frames at 80 to 100 ms; stops on non TTY.
- [ ] Progress bar redraws at most 20 times per second, shows ETA only when stable, never 100 percent before done.
- [ ] Live region replaced by a final static state; never a leftover spinner frame in scrollback.
- [ ] Frames wrapped in synchronized output or written in one syscall; no flicker in tmux.
- [ ] Animation pauses on focus loss or SIGTSTP when the framework supports it; `--no-animation` exists.
- [ ] Streaming text appends; does not re render the whole message per chunk.

## F. Interactive (shape 3 and 4)

- [ ] Keyboard reaches every action; `?` shows the binding table; footer shows context bindings.
- [ ] Esc cancels or closes, never quits from the root; `q` and Ctrl+C quit.
- [ ] Mouse: click focuses, wheel scrolls the pane under the pointer, text selection still possible (Shift drag or a toggle).
- [ ] Text inputs: word movement, Home and End, history, bracketed paste, multi line.
- [ ] Minimum size handled with a message, not a broken layout.
- [ ] Long lists virtualized; no visible lag at 10k rows.
- [ ] Off thread I/O; UI never freezes.
- [ ] Permission or confirmation prompts show the exact action verbatim and default to the safe choice.
- [ ] Non interactive `--print` mode exists for agent front ends.

## G. Engineering

- [ ] One output module is the only place that inspects TTY, color level and width (the template, or equivalent).
- [ ] Tests cover environment detection, `--json` output and one rendered frame snapshot.
- [ ] Engine and rendering are separate modules; the engine has no terminal imports.
- [ ] Heavy imports are lazy; startup under 100 ms (Python under 200 ms is acceptable).
- [ ] Tests: piped and TTY snapshots at 80 and 40 columns, NO_COLOR and FORCE_COLOR cases, Ctrl+C cleanup.
- [ ] README without emojis and without em dashes: install, usage with examples, flags, env vars, exit codes, theme file.
- [ ] Shell completions shipped (Typer, Commander via `omelette` or `tabtab`, Cobra, clap_complete).

## Before running anything

The tool under review may be in production. Run the audit against `--help`, a
read only subcommand, or `--dry-run`. If none exists, report that the dynamic
checks could not be run safely and audit statically instead. An audit that
deploys something is not an audit.

Nothing in this checklist authorises editing the tool. Findings are proposed;
the user decides. Behavior that works and is depended upon is a specification,
even where this skill would have chosen otherwise, and it appears in the report
as a note rather than as a defect.

## Report format

```
# Review: <tool> <version>

## Blocking
1. stdout polluted by spinner
   evidence: `tool status | cat` shows `\x1b[?25l` and `\r` sequences
   rule: principles.md section 1
   fix: route the spinner to stderr (patch attached)

## Major
...

## Minor
...

## Missing (capabilities that do not exist yet, none of them defects)
- no --json on `list`, so the output cannot be consumed by a script
- no test covering an input larger than memory

## Verified OK (exercised and correct, leave as is)
- NO_COLOR honored, --json valid on `status`, exit codes correct, cursor
  restored after Ctrl-C during the spinner

## Deliberate differences (this skill would differ; the existing choice stands)
- symbols instead of color for status, consistent across all commands
```

Each finding carries: the command run, what appeared, the rule it violates,
the fix, and the regression risk of applying that fix. A fix whose risk is not
stated is not a fix, it is a suggestion wearing a patch.

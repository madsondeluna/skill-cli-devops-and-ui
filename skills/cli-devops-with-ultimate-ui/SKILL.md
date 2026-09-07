---
name: cli-devops-with-ultimate-ui
description: Builds, reviews and polishes command line tools and terminal UIs that are robust (pipe safe, CI safe, scriptable, typed, tested) and visually excellent (animated teal to blue to violet gradients, spinners, progress, live panels, tables, trees, diffs, streaming output, keyboard driven TUIs) in the style of Claude Code, Gemini CLI, Crush and lazygit. Carries the behaviour layer too: subcommand shape and naming, POSIX option syntax, defaults, prompts and confirmation, help and usage text, error messages and exit codes, stdout versus stderr, piping and structured output, TTY detection, non interactive and CI behaviour, configuration precedence across flags, environment and files, shell completion, accessibility and i18n. Covers Bash, Python (Typer, Rich, Textual), TypeScript (Commander, Ink), Go (Cobra, Bubble Tea) and Rust (clap, Ratatui). Use whenever the user asks to create, scaffold, refactor, review or improve a CLI, command, script, terminal app, TUI, REPL, agent console, pipeline wrapper, progress bar, spinner, banner, colored output, --json flag, help text or exit codes, wires up an argument parser (argparse, click, typer, cobra, clap, commander, oclif) or a setup script prompt, mentions ANSI, TTY or NO_COLOR, or says a tool looks plain, flickers, breaks when piped, or should look like Claude Code. Also use for shell scripts that print to a terminal, even when the user does not say CLI. On an existing, working tool it audits and reports without rewriting what already works.
license: MIT
metadata:
  author: Madson A. de Luna Aragao
  version: 1.0.0
  category: developer-tools
  tags: [cli, tui, terminal, python, typescript, rich, textual, ink, typer, go, rust]
---

# cli-devops-with-ultimate-ui

Build command line tools that a systems engineer trusts and a designer
admires. The two goals are not in tension: the discipline that makes output
pipe safe (streams, TTY detection, structured output) is what lets visual
polish be applied without breaking anything. Visual layer over a correct
core, never instead of it.

## Two modes, and the one that must not break anything

Decide which mode applies before doing anything else, because they have
opposite defaults.

**Build mode** applies to a new tool, or a new command inside one. Everything
in this skill is a default to apply.

**Audit mode** applies to a tool that already exists, especially one that is
working and validated. Here the skill is a lens, not a rewrite. The contract:

- Read and run; do not modify. Produce a report of what could improve and what
  is missing, with the evidence for each finding. Code changes are proposed as
  patches the user chooses to apply, not applied because they were obvious.
- Working behavior is a specification. If a tool prints a format, uses a flag
  name or returns an exit code that this skill would have chosen differently,
  that is a note in the report, not a defect. Users, scripts and pipelines
  depend on it, and consistency beats correctness in style matters.
- Never touch what is validated to make it match the aesthetics here. The
  identity in this skill is for tools it builds. An existing tool with its own
  visual language keeps it, and the report speaks to that language.
- Findings are ranked by what they cost the user, not by how far they sit from
  this skill's preferences: broken scripting first, wrong behavior in a common
  environment second, polish last, and polish is explicitly optional.
- Separate what is missing from what is wrong. Missing means a capability that
  does not exist yet (`--json`, a `--dry-run`, tests for the streaming path).
  Wrong means present behavior that breaks in a real environment. A tool can be
  entirely correct and still be missing things, and saying so is the point of
  the audit.
- State plainly what was verified and found correct. A report that lists only
  problems misrepresents a good tool and hides which parts were actually
  exercised.

When the user asks to improve rather than to audit, the mode changes only for
the part they named. Everything else stays as it is, and the report still says
what was left alone and why.

Running the audit safely: `scripts/check_cli.py` executes the command several
times. Point it at a read only subcommand, at `--help`, or at a `--dry-run`
invocation. Never audit a command that writes, deploys or deletes against real
data, and say so if no safe invocation exists rather than running it anyway.

## Read first

Read `references/principles.md` for every task: the non negotiable rules on
streams, TTY, NO_COLOR, exit codes, --json and help. Then load by need:

| Need | Read |
|---|---|
| Colors, contrast, gradient stops, glyphs, box drawing | `references/palette.md` |
| What a screen is made of: banner, status, steps, progress, table, tree, diff, panel, prompt, footer | `references/anatomy.md` |
| Spinners, progress, animated gradient, streaming, flicker free rendering | `references/motion.md` |
| Launcher screens, single choice menus, keybinding footers | `references/launcher.md` |
| Full screen apps: alt screen, keyboard, mouse, focus, resize, modals | `references/interactive-tui.md` |
| Agent front ends: transcript, tool call cards, diffs, approval prompts, token footer | `references/agent-ui.md` |
| Bash / POSIX sh | `references/stack-bash.md` |
| Python (default for this user) | `references/stack-python.md` |
| TypeScript / Node / Bun | `references/stack-typescript.md` |
| Go | `references/stack-go.md` |
| Rust | `references/stack-rust.md` |
| Auditing an existing tool | `references/review-checklist.md` and `scripts/check_cli.py` |
| Positional args, flags, options, defaults, secrets on the command line | `references/arguments-and-flags.md` |
| Command and subcommand structure, naming, word order | `references/subcommands-and-command-shape.md` |
| Prompting, confirmation, destructive action safety | `references/prompts-and-confirmation.md` |
| `--help`, usage synopsis, man pages, "did you mean" | `references/help-and-usage.md` |
| What to print, success output, tables, `--json`, paging | `references/output-and-formatting.md` |
| ANSI colour rules, `NO_COLOR`, Windows VT | `references/color-and-styling.md` |
| Error messages, exit codes, `sysexits.h` | `references/errors-and-exit-codes.md` |
| stdout vs stderr, pipes, `-` for a stream | `references/streams-and-piping.md` |
| When to show a spinner or a bar at all | `references/progress-and-feedback.md` |
| TTY detection, `--no-input`, CI, signals | `references/interactivity-tty-and-ci.md` |
| Flags vs env vars vs config files, precedence, XDG | `references/config-env-and-precedence.md` |
| Screen readers, colour vision, locale, plain output | `references/accessibility-and-i18n.md` |
| Testing CLI behaviour and UX | `references/testing-cli-ux.md` |
| Auditing behaviour against a written checklist | `references/behaviour-review.md` |
| Authoring and discovery of a skill package | `references/skill-format-and-discovery.md` |
| Index and keyword map of the behaviour half | `references/behaviour-index.md`, `references/behaviour-topics.json` |
| Failure modes of the behaviour guidance itself | `references/behaviour-gotchas.md` |
| Complexity, streaming, concurrency, security of the core | `references/engineering.md` |
| Drawing the command tree, verifying a library API, recording decisions | `references/mcp-workflow.md` |

## One skill, two halves

Behaviour and appearance ship together here. `references/principles.md` states
the non negotiable rules and is enough for most tools; the behaviour references
above go deeper when the question is which commands exist, how a flag should be
named, where a setting comes from, or how a failure should exit.

Two review checklists, with different scope: `references/review-checklist.md`
audits what the terminal shows, `references/behaviour-review.md` audits what the
tool does. A tool passes both or the review is not finished.

Load only what the task needs. The table above is the router; reading every
reference is never the plan. For the behaviour half the procedure is:

1. Open `references/behaviour-index.md`, or `references/behaviour-topics.json`
   for the keyword map.
2. Load only the components the concern touches.
3. Apply their principles, decision rules and do/don't guidance.
4. Where established practices conflict, each component states the
   reconciliation inline. Follow it.
5. To audit an existing tool, run `references/behaviour-review.md` as a
   checklist and report findings with severity.
6. If a needed point is not covered, say so and mark it `TODO`. Never invent a
   convention.

## Language and formatting

Code, comments, help text and documentation in English; reply in the user's
language. Never emojis, anywhere (Unicode glyphs from the palette are
symbols, not emojis). Never em dashes in documentation. One README.md per
project, no other stray .md files.

## Workflow

### 1. Classify the tool

Every CLI is one of four shapes. Decide before writing code; the shape
dictates the rendering strategy.

1. Script (one shot, prints and exits): semantic color on a TTY, no live
   regions. A converter, a validator, a pipeline step.
2. Command tool (subcommands, long running steps): status lines, spinners,
   progress on stderr; result on stdout. A pipeline runner, a deploy tool.
3. REPL / streaming (conversational, appends to a scrolling log): inline
   rendering that never clears the screen, streamed text, tool call cards.
   An agent front end like Claude Code.
4. Full screen TUI (owns the terminal): alternate screen, layout engine,
   mouse and keyboard, resize handling. lazygit, a monitor, a file browser.

Shapes 1 and 2 are the default. A full screen TUI for a task that runs once
is a design error.

### 2. Pick the stack

Prefer what the user already uses. If open:

- Bash when the tool wraps other commands, has no state and fits one file.
- Python when the tool processes data or the ecosystem is Python (this
  user's default): Typer + Rich for shapes 1 to 3, Textual for shape 4.
- TypeScript when the tool ships to npm or needs an Ink component tree for
  shape 3.
- Go when a single static binary with fast startup matters.
- Rust when performance and correctness are the product.

Read only the matching `stack-*.md`.

### 3. Start from the template

`assets/templates/python/ui.py` and `assets/templates/typescript/theme.ts`
are vendorable modules: copy one into the project as the single place that
knows about TTYs, color depth, animation and the theme. They ship the
environment detection, the tiered palette, the OKLCH gradient sampler with
depth fallback, synchronized output, Ctrl-C handling, the `--color` flag and
JSON emission. `assets/templates/python/test_ui.py` is the matching test.
`scripts/demo_gallery.py` is a complete shape 1 reference tool built on the
template; run it to show the identity before writing code.

### 3.5 When the tool already exists

Audit mode applies (see the top of this file). Match before improving. Inconsistent UX confuses more than uniformly mediocre
UX, so on an existing codebase keep the output format, error style, command
naming and visual language already in use, unless the user has asked for a
redesign of all commands together.

Safe to add without breaking consistency, because they are additive rather
than a change of behavior: `--help` where there was none, correct exit codes,
better messages for errors that are new, progress for operations that are new.

When matching something that is itself a problem, say so once, in this shape,
and let the user decide:

```
Matched raw JSON output for consistency with `list-projects`.
Noticed: no --help on any command, so nothing is discoverable.
Recommendation: add --help across all commands in a follow up?
```

### 3.6 Triage when there is no time

If only a few minutes exist, this order buys the most user experience per
minute, and each item is independent of the rest:

1. `--help` with two examples at the top.
2. Exit codes: 0, 1, 2, 130. This is what makes the tool usable in a script.
3. Errors that name what is invalid, what is valid, and how to fix it.
4. Any feedback at all for operations over 500 ms.

Defer without guilt: color schemes, tables, gradients, `--json`, themes. They
are the polish this skill exists for, but a tool that scripts correctly and
explains itself is already useful, and one that looks beautiful while
returning exit 0 on failure is not.

### 3.7 Draw the surface before writing it

When connectors are available, draw the command tree and, for shapes 3 and 4,
the state machine, before implementing. A diagram of states is what reveals
the paths nobody planned: no way back from a confirmation, no exit code on
interrupt. `references/mcp-workflow.md` has the shapes and the boundaries,
including what never leaves the machine. Without connectors, a Mermaid block
in the reply does the same job.

### 4. Design the output before the logic

Write a short text mock of what the terminal shows in three conditions:
interactive success, interactive error, and piped (`| cat`). Put it in the
response before generating code. Use `anatomy.md` for the vocabulary and
`palette.md` for the roles.

### 5. Build in layers

1. Argument parsing, config precedence (flag, env, config file, default),
   exit codes.
2. The ui module (template). Every print goes through it.
3. Plain output path (the piped path). Make it correct first.
4. Visual layer: color, then spinners and progress, then live panels, then
   the gradient. Each layer degrades to the one below.
5. Interactivity (shapes 3 and 4 only).
6. Tests: environment detection, `--json`, one snapshot of a rendered frame,
   plus the four core cases in `engineering.md` (empty input, oversized input,
   malformed input, interruption partway).

The core is written under `references/engineering.md`, not by instinct: state
the time and memory complexity before the loop is written, stream rather than
load, bound every buffer and every fan out, and never interpolate user input
into a shell command. Polish on top of a core that dies at scale is worse than
no polish, because it promised competence.

### 6. Verify

Run `python scripts/check_cli.py -- <command>` whenever the tool runs in the
sandbox. It exercises pipe, NO_COLOR, CI, pty, --help, --version, --json, a
usage error and Ctrl-C, and reports ANSI leaks, exit codes, stdout pollution
and help quality. Fix every finding before presenting. When the tool cannot
run here, walk `review-checklist.md` and say which items were verified.

## Rules that apply to every stack

- Result to stdout. Progress, spinners, logs, prompts, warnings, errors,
  banners to stderr. This is what makes `tool | jq` work.
- Detect a TTY per stream, once, at startup. stdout can be piped while
  stderr is a terminal.
- Honor `NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, `CI`, and a
  `--color=auto|always|never` flag. Auto is the default.
- Never require interactivity. Every prompt has a flag or env var
  equivalent; when stdin is not a TTY, fail fast naming the flag.
- `--json` on any command someone might script against: stdout, one
  document or NDJSON, stable sorted keys, no decoration.
- Exit codes: 0 success, 1 failure, 2 usage error, 130 on SIGINT. Handle
  `BrokenPipe` quietly (`tool | head` is normal use).
- Help leads with examples, then usage, then options grouped by purpose.
- Width aware: read the width, wrap, truncate with an ellipsis, never
  assume 80 or exceed it. Guard a reported width of 0.
- Unicode aware: glyphs only when the locale is UTF-8, ASCII fallback.
- Animation stops when not on a TTY, in CI, or when backgrounded. Never
  animate into a log file. Frames are written in one syscall inside
  synchronized output (DEC 2026).
- Ctrl-C always honored; cursor restored, alternate screen left, even on
  exceptions.

## Visual identity

Cool multi-hue: teal to blue to violet (`aurora` in `assets/theme.json`).
Three fixed decisions shape every tool built here:

1. Banner: the tool name in the shadow font, one continuous gradient across
   the block, wiped in from the left and then crossed twice by a highlight
   sweep before freezing, followed by the slogan and a two column list of
   general options, closed by a gradient rule. See `anatomy.md` for the shape
   and `motion.md` for why the sweep is a soft band rather than a hard edge.
2. Motion: spinners and progress bars carry the gradient and cycle it
   continuously while the live region is visible, then freeze at completion.
   One moving gradient at a time; nothing static ever shimmers.
3. Grouping: rounded panels with a visible border (`ui.panel`) are the default
   way to group a block of output. ASCII box when the locale is not UTF-8. A
   choice is presented as a launcher inside one panel, with a permanent
   keybinding footer. See `launcher.md`.

Body text in the terminal foreground, secondary text in `muted`, interactive
elements in `accent` (blue), second highlight in `accent2` (violet). Status
colors reserved for meaning and always paired with a glyph or a word. One cell
padding, prose and panels capped at 100 columns. Success is quiet.

## Voice of the output

Terse, present tense, no exclamation marks. Messages say what happened and
what to do next:

```
error: config file not found: ./tool.toml
  hint: run `tool init` to create one, or pass --config <path>
```

## Deliverables

New tool: runnable files (not snippets), the ui module, tests, a README.md
built from `assets/templates/README-template.md`, and the three text mocks.

The README is part of the deliverable, not an afterthought. It carries: the
one line purpose, install, three real invocations with their output, a
pipeline diagram, the complexity and memory table, the flag table with env
vars and precedence, the exit code table, the stdout and stderr contract, the
theme overrides, and three lines on what the tool executes, writes and sends.

The diagram is generated with the draw.io connector (see `mcp-workflow.md`)
and exported into `docs/`, with the Mermaid source kept in a collapsed block
in the README so it stays diffable and editable without the connector. The
performance table is filled with measured numbers, never estimated ones; if
nothing was measured, say so rather than inventing a figure. Review: findings ordered blocking, major, minor, each
with its fix, plus a patched file when the fix is mechanical.

## Troubleshooting

- Flicker in tmux or Windows Terminal: frames not wrapped in synchronized
  output, or several writes per frame. Use the template render path. In
  tmux set `set -as terminal-features ',xterm*:sync'`.
- Colors wrong over SSH: `COLORTERM` unset, so the 256 tier is chosen. Test
  with `FORCE_COLOR=3`.
- Progress bar duplicates lines in CI: animation not disabled; `animate`
  must read `CI`.
- Nothing renders under `script` or some runners: the pty reports 0
  columns. The template guards this; hand rolled code must too.
- Rich still colors a piped stream: `force_terminal=False` means auto
  detect. Pass `no_color=True, color_system=None` for non TTY streams.
- Garbled glyphs: locale not UTF-8. Check `sys.stdout.encoding` and `LANG`;
  offer `TOOL_ASCII=1`.

## Sources

Original content, informed by the GNU Coding Standards, the POSIX utility
conventions, Microsoft's .NET command line guidance, the Agent Skills format,
and the terminal work of Charm, Textual and Rich.

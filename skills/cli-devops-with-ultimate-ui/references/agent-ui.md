# Agent front ends

Patterns for shape 3 tools that wrap a model or an autonomous process: Claude Code, Gemini CLI, Crush, OpenCode, Aider. These tools are REPLs that stream, call tools, ask for permission and keep a transcript. The transcript is the product; everything else exists to keep it readable.

## Screen layout (inline, not alternate screen)

```
[transcript: immutable, scrolls with the terminal]
[live region: current assistant message or tool activity]
[input box]
[footer: status, keys, cost]
```

The transcript uses the terminal's own scrollback, which is why these tools do not use the alternate screen: the user can scroll up with the terminal, select text, and keep the history after quitting. Ink's `<Static>`, Bubble Tea's `tea.Println`, Rich `Live` with `console.print` are the mechanisms for appending frozen content above the live region.

## Message blocks

User message: a prefix glyph in accent, text in fg, indented by 2. Assistant message: a different glyph (or none), rendered markdown, indented by 2. Both separated by one blank line. Do not draw boxes around every message; boxes are for tool results and diffs.

```
> summarize the failed samples

  Three samples failed alignment. sample_07 and sample_11 had
  adapter contamination; sample_03 was truncated during upload.
```

Markdown rendering: headers in bold accent, inline code in accent2 on a subtle background, code fences in a panel with language label and syntax highlighting, lists with the bullet glyph, links as OSC 8 hyperlinks with the URL visible in muted when not supported. Tables render as the table component from `anatomy.md`.

## Tool call cards

Each tool call is a compact card with three states.

Pending or running:

```
  - Read src/pipeline.py
```

Done, collapsed by default with a one line result summary:

```
  ok Read src/pipeline.py (212 lines)
  ok Grep "def align" (3 matches)
```

Done, expanded (user pressed the expand key or the tool asked for expansion):

```
  ok Bash pytest tests/ -q
     +- output ------------------------------------------+
     | 41 passed, 2 skipped in 3.12s                     |
     +---------------------------------------------------+
```

Failed:

```
  x Bash npm test
    exit code 1
    hint: press ctrl+o to expand output
```

Rules: tool name in bold, primary argument after it in fg, truncated to one line; result summary in muted; expanded output in a panel capped at 20 lines with a "... 130 more lines" line and a key to open fully; consecutive similar calls (three Reads) may collapse into one line `ok Read 3 files`.

## Diff and edit proposals

An edit tool shows a unified diff (see `anatomy.md`) with the file path as the panel title and line numbers in muted. Word level highlighting on changed lines is worth the effort here: it is the difference between skimming and reading.

## Permission prompts

The most important UI in an agent tool. It interrupts the stream, so it must be unmissable, fast to answer and safe by default.

```
  +- permission -------------------------------------------+
  | Bash wants to run:                                     |
  |   rm -rf results/tmp                                   |
  |                                                        |
  |   > Yes, once                                          |
  |     Yes, for this session                              |
  |     No, and tell Claude what to do instead             |
  +--------------------------------------------------------+
   arrows select  enter confirm  esc deny
```

Rules: the exact command or file path is shown verbatim, in a monospace panel, never paraphrased; the default is the safest option; Esc denies; "always allow" options are scoped and visible in a settings command; a denial returns focus to the input with the denial recorded in the transcript. Never auto approve silently, never time out into approval.

## Thinking and waiting states

While the model works, show a live line that gives three facts: something is happening, how long it has been, how to stop it.

```
  * Reasoning (12s, 2.1k tokens)  esc to interrupt
```

Rotate the verb from a small list to avoid a static feel, use the `pulse` spinner, keep the elapsed time. When streaming starts the line is replaced by the message. Show the extended reasoning text only in a collapsible block, dim, when the user enabled it.

## Input box

```
  +---------------------------------------------------------+
  | > write the README|                                     |
  +---------------------------------------------------------+
```

Multi line with Shift+Enter (kitty protocol) or backslash newline fallback, history with Up and Down, `/` opens the slash command palette with fuzzy filter, `@` opens a file picker with fuzzy filter, `!` prefix runs a shell command, bracketed paste inserts without triggering commands, a paste over 10 lines is collapsed to `[pasted 42 lines]` in the transcript. The box border turns accent on focus and warn while a permission prompt is open.

## Footer

```
  claude-sonnet-4-6  main*  ctx 34%  $0.12  ? help
```

Model, git branch with dirty marker, context usage as a percentage with warn color above 70 and err above 90, cost when known, one help hint. Right aligned state, left aligned identity. Shrinks to model and context percentage on narrow terminals.

## Slash commands and palettes

A fuzzy palette (like fzf): list of commands with descriptions, filter as you type, Up and Down, Enter selects, Esc closes. Show at most 8 items, scroll beyond. Commands come from one registry with name, description, handler, so `--help`, the palette and the documentation stay in sync.

## Non interactive mode

Every agent tool needs a `-p` / `--print` mode: read the prompt from an argument or stdin, stream the answer as plain text (or `--json` events, one per line) to stdout, tool call summaries to stderr, exit with the model's completion status. This is what makes the tool composable in scripts and CI. Gemini CLI and Claude Code both ship it; design it from day one, because it forces the separation between engine and rendering.

## Architecture

Separate three packages or modules: engine (API calls, tool execution, permission policy, session state), rendering (components, theme, terminal I/O), and the entry point (argument parsing, mode selection). The engine emits typed events (`message_delta`, `tool_call_start`, `tool_call_result`, `permission_request`, `usage`); the renderer consumes them. This is the structure of both Gemini CLI (packages/core and packages/cli) and Claude Code, and it is what makes `--print` mode, tests, and a future web or IDE front end cheap.

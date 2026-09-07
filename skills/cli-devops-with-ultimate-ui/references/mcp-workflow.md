# MCP in the CLI workflow

Connectors help at three moments: designing the command surface before code,
verifying that a library still works the way you remember, and recording the
decisions so the next session does not relitigate them. Everything else in
this skill works with zero connectors, and nothing here is a prerequisite.

## The rule that comes first

Never send source code, unpublished research, credentials or client data to a
third party connector. A command tree and a state machine are safe to draw
because they are structure, not content. The tool itself, its data and its
keys stay local.

Connectors marked as consumer partners (Figma among them) need the user to
opt in before they are called. Offer, do not assume. When a connector is not
available, the fallback is always a fenced Mermaid block or an ASCII sketch in
the reply, which loses nothing that matters for the design.

## 1. Before code: draw the surface

The cheapest bug to fix is a command tree that nobody could have guessed.
Draw it before implementing, and the argument design reviews itself.

`draw.io:create_diagram` with a Mermaid flowchart, for the command tree:

```
flowchart LR
  root["mytool"] --> run["run <input>"]
  root --> ls["list"]
  root --> cfg["config"]
  run --> flags["--out --threads --json --dry-run"]
  cfg --> get["get <key>"]
  cfg --> set["set <key> <value>"]
```

Same tool with `stateDiagram-v2`, for a TUI or a REPL, where the value is
higher because states are what get forgotten:

```
stateDiagram-v2
  [*] --> Launcher
  Launcher --> Running : enter
  Launcher --> [*] : esc
  Running --> Confirm : destructive step
  Confirm --> Running : yes
  Confirm --> Launcher : no
  Running --> Interrupted : ctrl-c
  Interrupted --> [*] : exit 130
```

Reading that diagram is what surfaces the missing paths: no way back from a
confirmation, no exit code on interrupt, a state the keybar never mentions.
Use `sequenceDiagram` instead when the tool talks to a server or an agent and
the question is who waits for whom.

`Figma:generate_diagram` does the same in FigJam when the diagram belongs in a
design file the team already uses. It needs opt in, and it is the only reason
to reach for Figma here: this skill has its own visual identity and takes no
tokens from a design file.

## 2. During: verify, do not remember

Terminal libraries moved fast and training data goes stale. Before writing
against an API, confirm it with `web_search` and `web_fetch` rather than
recalling it. The ones that changed recently and break silently:

- Bubble Tea v2: `View()` returns `tea.View`, not a string; `KeyMsg` became
  `KeyPressMsg`; alt screen and cursor are set on the view.
- Lip Gloss v2, Huh v2, Glamour v2 moved import paths.
- Ink: synchronized output arrived in 6.7; older versions flicker in tmux.
- Textual: major version jumps have changed widget APIs.

A version guess that compiles but behaves differently is worse than an
admitted gap. When the answer is not found, say so and use the older API with
a note, rather than inventing the new one.

## 3. After: record the decisions, not the code

`Notion:notion-create-pages` is worth one page per tool, holding what a future
session would otherwise ask again: the shape (script, command, REPL, TUI), the
stack and why, the flag surface, the exit code table, the theme overrides, and
the findings from `check_cli.py` that were accepted rather than fixed. Keep the
code in git; the page holds the reasoning that git does not.

Do this when the user asks for it or when the tool is theirs to maintain, not
on every scaffold. A decision page nobody asked for is one more stale document.

## What not to use

Most connected servers have nothing to do with CLI work. Reaching for a
literature or media connector during a build is noise, and calling a connector
to produce something the reply could have contained directly (a diagram nobody
will edit, a page nobody will read) costs the user time for no gain. The test
is whether the artifact outlives the conversation. If it does not, write it in
the reply.

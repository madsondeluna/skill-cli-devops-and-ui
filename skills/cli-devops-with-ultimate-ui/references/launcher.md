# Launcher

The screen a tool shows when it is invoked with no arguments, and the shape of
any single choice it asks for. This is the pattern behind Charm based
launchers (Daytona, Crush, gum choose) and it is the only interactive
primitive a command tool needs. Anything richer belongs in a full screen app;
see `interactive-tui.md`.

## Anatomy

Inside one rounded panel, in this order:

1. Brand line: the tool or screen name with the identity gradient.
2. Prompt: one line in `muted` saying what the choice is. When a filter query
   is active it is appended in `accent` after a pointer glyph.
3. Rows: label in `fg` (bold `accent` when selected), two spaces, description
   in `muted`. Labels are padded to a common width so the descriptions form a
   column. The selected row is marked with a pointer in the left gutter; the
   others get three spaces, never a different glyph.
4. Overflow line: when the list is longer than `max_rows`, one `dim` line
   saying how many remain and that typing filters. Never a scrollbar.
5. Keybar: the footer, always present, listing every key that does something
   on this screen. Key in `accent`, action in `muted`, separated by a bullet.

The panel is the only frame. There is no separate header box, no shadow, no
double border. The gradient appears once, on the brand line.

## Behavior

- Arrows and `j` and `k` move; typing filters; enter chooses; escape cancels
  and returns nothing.
- Filtering matches the label and the description, and label matches sort
  first: typing the start of a name puts that name at the top.
- The cursor resets to the first row on every filter change, so enter after
  typing always takes the obvious row.
- The live region is transient: on exit the panel disappears and only the
  consequence of the choice remains in the scrollback. A launcher that leaves
  its own menu behind makes the transcript unreadable.
- A stray terminal report (an escape sequence that is not an arrow) is
  ignored, never treated as escape. Keys are read from the file descriptor so
  a multi byte sequence arrives whole; reading the buffered text stream
  splits it and turns arrows into accidental cancels.

## The rule that outranks the aesthetics

A launcher must never be the only way to reach a capability. Every choice it
offers is also a flag or an argument, and when stderr or stdin is not a
terminal the tool fails fast (exit 2) naming that flag instead of prompting.
This is what keeps a beautiful launcher compatible with cron, CI and pipes.

## Implementation

Python: `ui.select(items, title, prompt)` and `ui.keybar(*pairs)` in the
template. Go: `huh.NewSelect` with a Lip Gloss theme, or `bubbles/list` when
the list needs pagination. TypeScript: `ink-select-input` inside a bordered
`Box`, or `@clack/prompts` outside Ink.

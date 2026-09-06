# Interactive TUIs

Shape 4 tools own the terminal. They are judged on input feel (keyboard and mouse), layout stability under resize, and how cleanly they hand the terminal back. This file is framework agnostic; the stack files map each rule to a library.

## Terminal modes

| Mode | Escape | When |
|---|---|---|
| Alternate screen | `ESC[?1049h` / `ESC[?1049l` | Full screen apps only. Restores the user's scrollback on exit. Never for REPLs. |
| Raw mode | termios (no ICANON, no ECHO) | Any app that reads single keys. Restore on exit, including panic. |
| Hide cursor | `ESC[?25l` / `ESC[?25h` | While rendering; show it inside text inputs. |
| Mouse tracking | `ESC[?1000h` (clicks), `ESC[?1002h` (drag), `ESC[?1003h` (all motion), `ESC[?1006h` (SGR encoding, always pair with one of the above) | Only when the app has clickable regions. Mouse tracking steals the terminal's native text selection; provide Shift-drag passthrough or a key to toggle it. |
| Bracketed paste | `ESC[?2004h` / `ESC[?2004l` | Any text input. Pasted text arrives wrapped in `ESC[200~ ... ESC[201~` and must not trigger key bindings. |
| Focus reporting | `ESC[?1004h` / `ESC[?1004l` | Pause animations and polling when the terminal loses focus. |
| Synchronized output | `ESC[?2026h` / `ESC[?2026l` | Every frame. See `motion.md`. |
| Kitty keyboard protocol | `ESC[>1u` ... `ESC[<u` | Distinguishes Shift+Enter, Ctrl+Enter, key release. Supported by kitty, WezTerm, Ghostty, foot, iTerm2 3.5+, Alacritty. Enable when available; keep legacy bindings as fallback. |

Exit sequence (always, in a finally or defer): disable mouse, disable bracketed paste, disable focus reporting, show cursor, leave raw mode, leave alternate screen, reset SGR (`ESC[0m`). Install this for SIGINT, SIGTERM and for uncaught exceptions; a crashed TUI that leaves the terminal in raw mode is the single most hated bug in this category.

Suspend: Ctrl+Z should run the exit sequence, send SIGTSTP to self, and re enter all modes on SIGCONT. Bubble Tea v2 and Textual implement this; Ink does not by default.

## Keyboard

Conventions users expect, from vim, less, fzf, lazygit and GitHub CLI:

| Key | Action |
|---|---|
| `q` or Ctrl+C | quit (Ctrl+C always works even when `q` is captured by an input) |
| `?` | help overlay listing every binding |
| `j` `k` and arrows | move down and up |
| `h` `l` and arrows | move left and right, collapse and expand |
| `g` `G` | top and bottom |
| Ctrl+d Ctrl+u | half page down and up |
| Tab and Shift+Tab | next and previous pane or field |
| Enter | confirm, open, select |
| Esc | cancel, close overlay, clear filter; a second Esc from the root does nothing (never quits) |
| `/` | filter or search in the current list |
| Space | toggle selection in multi select |
| `1` to `9` | jump to pane N |
| Ctrl+r | refresh or reload |

Rules:

- Every action reachable by mouse is reachable by keyboard.
- Bindings are declared in one table (key, action, description, context) so the help overlay and the footer are generated from it and never drift.
- Text inputs capture printable keys; navigation keys work only when no input has focus, except Esc (blur) and Ctrl+C.
- Show the active bindings in the footer, context sensitive: a list shows `j/k move  enter open  / filter`; an input shows `enter submit  esc cancel`.
- Multi key sequences (like `g g`) need a visible pending state and a 1 s timeout.
- Key repeat must not queue: coalesce repeated navigation events per frame.

Input widget essentials: cursor movement by word (Alt+arrows, Ctrl+arrows), Home and End, Ctrl+a Ctrl+e, Ctrl+w delete word, Ctrl+u clear line, Up and Down history in a REPL, multi line with Shift+Enter (kitty protocol) or a trailing backslash fallback, and bracketed paste handling.

## Mouse

Support it as an accelerator, never as the only path:

- Click selects an item or focuses a pane. Double click opens. Right click is unreliable across terminals; do not depend on it.
- Wheel scrolls the pane under the pointer by 3 lines, not the focused pane.
- Drag on a splitter resizes panes; drag elsewhere does nothing (leave selection to the terminal when possible).
- Hover highlights are cheap in the framework but cost a redraw per motion event; enable motion tracking only when the app uses hover.
- Hit testing: every rendered element knows its screen rectangle. Frameworks with a layout tree (Textual, Ink with Yoga, Bubble Tea v2 zones via `bubblezone`, Ratatui `Rect` bookkeeping) give this for free; hand rolled apps must keep a list of rectangles per frame.

## Layout

- Layout is a tree of boxes with constraints (fixed, percent, fill, min and max), computed from the terminal size on every resize. Flexbox (Ink, Yoga), CSS grid and docking (Textual), constraint splits (Ratatui, Lip Gloss v2 layouts).
- Minimum size: declare it (for example 60x16). Below it, render a single centered message "terminal too small (need 60x16)" rather than a broken layout.
- Panes have a title, a focus indicator (border color changes to accent), and a scroll position indicator when content overflows.
- A modal overlay dims or leaves the background as is, centers a panel, traps focus, closes on Esc and on its own confirm and cancel buttons.
- Long lists are virtualized: render only visible rows. Ten thousand rows must not cost ten thousand string builds per frame.
- Text areas wrap at pane width and recompute on resize.
- Keep a status bar (top or bottom) with mode, context, and a message area for transient notifications that expire after 3 to 5 s.

## Rendering

- One render per event batch, not per event. Collect all input and data events that arrived, update state, render once.
- Render is a pure function of state. Side effects (network, subprocess, file I/O) run in commands, workers or tasks that emit messages back to the state loop. This is the Elm architecture (Bubble Tea), Textual messages, Ink hooks with effects, Ratatui with a channel.
- Off thread work reports progress by message; the UI never blocks. A frozen TUI during a 5 s fetch is a design failure.
- Double buffering with line diffing, wrapped in synchronized output.
- Color the background of the selected row, not just the text, so selection is visible on any content.
- Frame budget: under 16 ms for the typical frame. Profile with the framework's devtools (Textual devtools, Ink React devtools, Bubble Tea `tea.LogToFile`).

## Accessibility

- Every state change that matters is also announced in text (status bar), not only by color.
- Support a high contrast theme and a monochrome theme (`--theme mono`).
- Screen reader mode: Ink has `INK_SCREEN_READER`, Textual has a plain mode; provide a linear text view of the current pane on request.
- Never rely on Unicode glyphs alone; the ASCII fallback set must produce a usable app.

## Testing

- Snapshot tests of rendered frames at fixed sizes (80x24, 120x40, 40x12). Textual `snap_compare`, Ink `ink-testing-library`, Bubble Tea `teatest`, Ratatui `TestBackend`.
- Input scripts: feed key sequences, assert state. Test the exit sequence restores the terminal (check emitted escapes in a fake TTY).
- Run the app in a pseudo terminal in CI to exercise the TTY paths; the sandbox script `scripts/check_cli.py --tui` does this for startup, resize and quit.

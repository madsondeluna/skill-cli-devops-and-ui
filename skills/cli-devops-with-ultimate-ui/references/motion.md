# Motion

Animation in a terminal is a sequence of rewrites. Every rule here exists to make rewrites invisible (no flicker), cheap (no CPU burn), and absent when nobody is watching (pipes, CI, logs).

## When feedback is owed

Decide by how long the user waits, before deciding what to draw:

| Duration | What the tool owes the user |
|---|---|
| under 200 ms | nothing; an indicator that flashes is worse than silence |
| 200 ms to 500 ms | nothing, unless the command is known to be slow sometimes |
| over 500 ms | an indicator: a spinner with a message naming the current step |
| over 3 s, determinate | a progress bar with counts, plus an ETA once it is stable |
| over 5 s, indeterminate | elapsed time and per item throughput, so the user can tell live from stuck |
| over 30 s | the same, plus a line on how to interrupt, and `--bell` if offered |

The failure this prevents is a tool that runs half a minute in silence: the
user cannot distinguish work from a hang, and reaches for Ctrl-C. Silence is
correct only when the wait is shorter than the eye notices.

## When to animate

| Condition | Behavior |
|---|---|
| stderr is a TTY, not CI, not `TERM=dumb` | animate |
| stderr not a TTY | print state changes as plain lines |
| `CI=true` | print start line and final line of each animated region |
| process backgrounded (SIGTSTP) or terminal lost focus (when detectable) | pause animation, resume on SIGCONT or focus |
| `--quiet` | no animation, no status, errors only |
| `TOOL_NO_ANIMATION=1` or `--no-animation` | static glyphs, still colored |

Also respect reduced motion as a user setting in the theme file. Some users find spinners distracting; make static indicators a one line config change.

## Frame rate

- Spinners: 80 to 100 ms per frame (10 to 12 fps). Faster looks nervous, slower looks stuck.
- Progress bars: redraw at most every 50 ms and only when a visible digit changes.
- Gradients and text effects: 30 fps cap, and only for a bounded duration (a banner reveal under 1.5 s), never continuously.
- Streaming text: render as chunks arrive, but coalesce chunks that arrive within 16 ms into one write.

A hidden cost: each redraw is a syscall and a terminal parse. Over SSH, a 60 fps spinner is a visible bandwidth hog. Cap rates and skip frames when the previous write has not flushed.

## Flicker free rendering

Flicker is the terminal painting an intermediate state: cursor moved up, lines cleared, new content not yet written. Three defenses, in order of preference:

1. **Synchronized output (DEC mode 2026).** Wrap each frame in `ESC[?2026h` ... `ESC[?2026l`. The terminal buffers everything in between and paints once. Supported by iTerm2, kitty, WezTerm, Ghostty, foot, Windows Terminal, Alacritty, and by tmux 3.4+ with `set -as terminal-features ',xterm*:sync'`. Ink 6.7+ and Bubble Tea v2 emit it; Rich Live and Textual do since 2025; Ratatui exposes it through crossterm `BeginSynchronizedUpdate`. When writing raw escapes, emit it yourself; terminals that do not support it ignore it harmlessly.
2. **Overwrite, do not clear.** Move the cursor to the start of the live region and write the full new frame, padding each line to the previous width with spaces. Only clear to end of line (`ESC[K`) after writing the new content, never before. Avoid `ESC[2J`.
3. **Write one frame in one syscall.** Build the frame as a string and write it once. Interleaved small writes are what tmux and slow links turn into visible tearing.

Diffing: for live regions taller than about 10 lines, diff the new frame against the previous one and rewrite only changed lines. Textual, Ink, Bubble Tea and Ratatui all do this internally; when hand rolling, keep the previous frame as a list of lines and compare.

## Live region discipline

- Exactly one live region at a time, always at the bottom of the output.
- Everything printed while the region is live goes above it: the library must support "print above the live region" (Rich `Live` with `console.print`, Ink `<Static>`, Bubble Tea `tea.Println`). Do not print into the middle of a live region.
- On finish, the region is replaced by its final static state and the cursor moves below it. On error or Ctrl+C the same happens, then the error prints. Never leave a spinner frame as the last line.
- Hide the cursor (`ESC[?25l`) while a region is live; show it (`ESC[?25h`) on exit, including abnormal exit. Register an atexit or defer handler for this.

## Spinners

Curated set in `assets/spinners.json`. Choose by context:

The identity spinner is `dots` with a gradient tinted glyph (`_GradientSpinner`
in the Python template): the frame advances at 12 fps and the color samples the
gradient at 0.35 turns per second, so the glyph cycles hue while it spins.

| Name | Frames | Use |
|---|---|---|
| dots | braille rotation, 10 frames | default, all purpose |
| line | `- \ | /` | ASCII fallback |
| arc | 6 arc glyphs | compact, next to text |
| bounce | bar moving in a track | long indeterminate waits |
| pulse | dim to bright of one glyph | agent "thinking" state |

Rules: one spinner per screen; glyph in info or accent color; message after it in fg; elapsed in muted after 2 s. When the operation completes the spinner glyph becomes ok or err, never disappears.

The Claude Code "thinking" indicator alternates a verb word with a spinner and keeps the elapsed time and token count; that is the pattern for agent waits: `pulse` spinner, a rotating verb from a small list, elapsed time, and a way out ("esc to interrupt").

## Progress

Determinate progress needs: total, current, rate (exponential moving average over the last 2 s), ETA (remaining / rate, shown only after 3 s and when stable). Bar width is what remains after the other columns; minimum 10 cells.

Smooth bars use the eighth block characters (U+258F to U+2588) for sub cell precision; ASCII fallback uses `#` and `-`.

Never show 100 percent before the work is actually finished, and never show an ETA that goes up more than once; if the estimate jumps, hide it for a second rather than flash a wrong number.

## Streaming text

For model output and long command output:

- Append text as it arrives; do not re render the whole message on every chunk. Only the last line needs rewriting for word wrap.
- Wrap on word boundaries at terminal width minus indent, recomputing on resize for the current message only. Older messages are frozen.
- Markdown rendering on the fly is expensive and produces jumpy output; render code fences and headers when their closing marker arrives, render inline styles (bold, code) immediately.
- A blinking or moving cursor glyph at the end of the stream signals "still writing"; remove it on completion.

## Gradients and effects

The identity gradient (teal to blue to violet, `assets/theme.json`) is the
brand moment of every tool built with this skill. It is animated, multi-hue and
confined to decorative surfaces.

Allowed surfaces, one per screen: the banner or logo on start, the rule under
an input box, the filled part of a progress bar, the spinner glyph, a one time
completion line. Never on body text, tables, help output or error messages.

Animation model:

- Frame rate 15 fps (`fps` in theme.json). 30 is the hard ceiling.
- Each frame shifts the hue phase by 6 degrees (`phase_step_deg`). Because the
  stop list wraps, the loop is seamless.
- Banner: 1200 ms at 30 fps, in three beats. The art wipes in from the left
  over the first third, a highlight band then sweeps across it twice, and the
  last frame is the clean static gradient so scrollback stays readable. The
  30 fps here is the ceiling and it is spent on a bounded reveal, not on a
  loop.
- Progress and spinner: the gradient cycles continuously while the live region
  is visible, driven by wall clock time so every redraw advances the phase.
  It freezes at completion and the glyph recolors to `ok` or `err`. The cycle
  ends with the region: there is no shimmer on static text, which is what
  would actually cost battery and SSH bandwidth.
- Interpolate in OKLCH (or linear RGB at minimum), never in sRGB, or the
  midpoints between blue and violet turn grey. The templates ship the sampler.
- Every frame is one write wrapped in synchronized output; the cursor is hidden
  during the reveal and restored on exit, including on Ctrl-C.
- Depth fallback: 256 colors get a static 4 stop version; 16 colors get the
  `accent` color; no color gets plain text. Callers never branch on depth, the
  `gradient_text` / `gradientColors` helpers do.
- Off switch: `TOOL_NO_ANIMATION=1`, `--no-animation`, `CI`, non TTY stderr.
  In all of them the banner prints one static frame or nothing.

Typewriter reveal is not part of the identity. Shimmer on finished, static
output is: once a region stops being live it stops moving, permanently.

One live gradient region at a time. The banner animates, freezes, and only
then does a spinner or bar start cycling. Two moving gradients on screen at
once is the failure mode this rule exists to prevent.

Libraries when a dependency is acceptable: Python `rich-gradient` (Gradient,
Rule, AnimatedText, AnimatedRule); TypeScript `ink-gradient` plus
`ink-big-text`, or `gradient-string` without Ink; Go Lip Gloss v2 blend
helpers; Rust `colorgrad` with Ratatui spans. Configure them with the stops from
`theme.json` rather than their presets so every tool shares one identity.

## Sound and bell

Never emit the terminal bell by default. Offer `--bell` for long running commands that the user might walk away from; it fires once on completion or failure.

## Resize

Handle SIGWINCH (or the equivalent event in the framework). On resize: recompute width, re render only the live region, keep completed output as is. Textual, Ink, Bubble Tea and Ratatui handle this; Rich `Live` needs `console.size` re-read; hand rolled Bash needs `trap ... WINCH` and a `COLUMNS` re-read via `tput cols`.

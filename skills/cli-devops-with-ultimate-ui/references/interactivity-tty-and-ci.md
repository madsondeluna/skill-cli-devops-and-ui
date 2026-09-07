# Interactivity, TTY, and CI

Making one tool behave well both for a human at a terminal and for scripts/CI: driven by TTY
detection, a `--no-input` escape hatch, and clean signal handling. The same command should adapt, not
require two different invocations.

**When this applies:** deciding interactive vs non-interactive behavior, detecting TTY/CI, handling
Ctrl-C and signals, or making a tool safe to run unattended.

## Principles

- **Detect the TTY and adapt.** stdin-TTY decides whether to prompt; stdout-TTY decides
 whether to color/animate. Pipes and CI are non-TTY: the same checks cover both. See
 `streams-and-piping.md`, `color-and-styling.md`, `progress-and-feedback.md`.
- **Always offer an explicit non-interactive mode** so behavior is predictable in automation.

## Decision rules

### Interactive vs non-interactive
```
# Human (stdin is a TTY): may prompt, color, animate
$ tool deploy
# CI / piped (non-TTY): no prompts, no color, no spinner; needs flags
$ echo "" | tool deploy --no-input --yes
```
- If interactive input is needed but unavailable (non-TTY and no flag), **fail fast** with a message
 naming the flag: don't hang. See `prompts-and-confirmation.md`.
- If the tool reads piped stdin but stdin is a TTY (nothing piped), show help or exit rather than
 blocking. See `help-and-usage.md`.

### Signals and escape
- **Ctrl-C (SIGINT) must work**, even during network I/O; say something, then exit
 promptly. Add timeouts to cleanup so it can't hang; a second Ctrl-C during cleanup should skip the
 long cleanup and tell the user what happens next time.
- Expect unclean exits: design so a resumed run tolerates incomplete prior cleanup (crash-only). See `progress-and-feedback.md`.
- For wrappers (ssh/tmux-like), document the escape sequence.

### Unattended safety
- Defaults must be safe for automation: no surprise prompts, no animations, deterministic output,
 non-zero exit on failure (see `errors-and-exit-codes.md`).
- Honor proxy/`NO_COLOR`/`CI` and similar environment signals. See
 `config-env-and-precedence.md`.

## Windows / PowerShell callouts

- Use an `-i`/`--interactive` flag to signal possible prompting; if
 `--verbosity Quiet` and interactive could collide, either still prompt under `--interactive` or
 forbid the pairing, so the tool never silently waits.
- TTY/console detection and Ctrl-C handling differ on Windows (no SIGINT in the Unix
 sense; the console sends CTRL_C_EVENT). Detect "is a console attached" via the platform API and
 still exit non-zero on interruption. Detect CI the same way (env vars / non-TTY) on both OSes.

## Edge cases / anti-patterns

- **Don't** assume interactive: the most common automation bug is a prompt that hangs CI.
- **Don't** ignore Ctrl-C during long network calls.
- Auto-detecting "am I in CI?" via env vars is a useful *hint*, but the TTY check is the reliable
 signal; combine them.

## Do / Don't

- **Do** gate prompts/color/animation on TTY and provide `--no-input`/`--yes`.
- **Do** make Ctrl-C immediate and cleanup bounded.
- **Don't** hang waiting for input that can't come.
- **Don't** emit interactive-only UI into pipes or CI.

## Related

`prompts-and-confirmation.md` · `streams-and-piping.md` · `progress-and-feedback.md` ·
`color-and-styling.md` · `config-env-and-precedence.md` · `errors-and-exit-codes.md`

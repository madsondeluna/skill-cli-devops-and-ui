# Color and Styling

Using ANSI color and text styling to aid scanning without breaking machines or excluding users.
Color must be an enhancement, never the only signal: disable it off-TTY and on `NO_COLOR`, keep
palettes small and theme-safe, and handle Windows virtual-terminal mode.

**When this applies:** adding color/bold to output, choosing a palette, or deciding when to turn
color off.

## Principles

- **Color is a redundant enhancement.** Overusing it means nothing stands out; meaning
 must survive with color stripped. See `accessibility-and-i18n.md`.
- **Reserve red/yellow for errors/warnings**; use one or two accent colors plus dim/bold
 for everything else.

## Decision rules

### When to DISABLE color (all of these)
- stdout **or** stderr is not a TTY (piping breaks tools: `printf '\e[1mhi\e[0m' | grep hi` can miss).
- `NO_COLOR` is set and non-empty.
- `TERM=dumb`.
- User passed `--no-color` (or set `COLOR=false` / a `MYAPP_NO_COLOR` var).
- Consider honoring `FORCE_COLOR` to re-enable when piping intentionally.

```
if stdout_is_tty and not NO_COLOR and TERM != "dumb" and not --no-color:
    enable_color()
```

### How to emit it
- ANSI sequence = ESC `[` + code + `m`: `\e[31m` red, `\e[1m` bold, `\e[0m` reset; combine bold+red
 for errors.
- Prefer the basic 16 or the fixed 8-bit palette (`\e[38;5;<0-255>m`) for consistent rendering across
 terminals; user themes make exact colors unpredictable, so keep styling simple.
- When you set a background, also set the foreground (light/dark theme safety).

### Don't convey meaning by color alone
- Pair color with a text label or symbol so colorblind users and screen readers get the signal: `OK build passed` / `ERROR build failed`, not green/red dots only.

## Windows / PowerShell callouts

- Modern Windows Terminal and PowerShell render ANSI, but legacy `conhost` needs
 virtual-terminal processing enabled (`ENABLE_VIRTUAL_TERMINAL_PROCESSING`) or ANSI shows as raw
 escapes. Detect capability and fall back to no-color rather than printing garbage.
- PowerShell has its own styling (`$PSStyle`, `Write-Host -ForegroundColor`); for a cross-platform
 argv CLI, emit ANSI and gate it on capability detection so the same binary behaves on both OSes.
- `NO_COLOR` is honored cross-platform: respect it on Windows too.

## Edge cases / anti-patterns

- **Don't** use backspace/overstrike "bold" (garbles in editors as `bboolldd`).
- **Don't** emit color into CI logs. CI is non-TTY, so the disable rules already cover it; verify.
- Hyperlinks (OSC 8) and 24-bit color aren't universal: feature-detect, degrade gracefully.

## Do / Don't

- **Do** make output meaningful in monochrome; add color on top.
- **Do** honor `NO_COLOR`, `--no-color`, and TTY detection consistently across stdout/stderr.
- **Don't** hardcode a background without a foreground.
- **Don't** rely on color as the sole status indicator.

## Related

`output-and-formatting.md` · `accessibility-and-i18n.md` · `progress-and-feedback.md` ·
`interactivity-tty-and-ci.md`

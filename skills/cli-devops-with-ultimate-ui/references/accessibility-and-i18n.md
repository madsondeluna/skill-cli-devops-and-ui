# Accessibility and Internationalization

Making CLI output usable by people with screen readers or color vision deficiency, and by users in
other locales. The core rule: never carry meaning in color or layout alone, write plain descriptive
text, and keep output parseable by assistive tech.

**When this applies:** any user-facing output, prompts, color usage, tables/ASCII art, or
locale-sensitive formatting.

## Principles

- **Meaning must survive without color or styling.** Pair every color/symbol cue with a
 text label so colorblind users and screen readers get the same signal. See
 `color-and-styling.md`.
- **Plain, structured output is accessible output.** Prefer clean labeled
 lines with headings/bullets/separators over heavy ASCII tables, long walls of text, or animations
 that screen readers can't follow.

## Decision rules

### Don't rely on color/visuals alone
```
# Inaccessible: only a colored dot distinguishes states
● myapp     ● otherapp
# Accessible: text label carries the meaning
OK    myapp
DOWN  otherapp
```

### Write descriptive content
- Avoid vague text ("it failed"); say what failed and the next step. See
 `errors-and-exit-codes.md`.
- Give prompts and feedback descriptive labels; don't assume the user infers from context or visual
 scanning. See `prompts-and-confirmation.md`.

### Keep output screen-reader friendly
- Favor plain text with clear separators over dense box-drawing tables and overly styled ASCII art;
 offer a `--plain`/`--json` mode for assistive tooling and scripts. See
 `output-and-formatting.md`.
- Don't emit animations/spinners that thrash a screen reader; they're TTY-only anyway and should be
 suppressed in non-interactive contexts. See `progress-and-feedback.md`.
- A short, accessible success line:
```
OK Deployment successful.
Run `tool status` to check environment health.
```

### Keyboard and non-interactive safety
- Ensure flows are keyboard-accessible and scriptable; include a `--non-interactive`/`--no-input`
 path so nothing depends on visual, mouse, or timing cues. See
 `interactivity-tty-and-ci.md`.

### Internationalization
- Don't hardcode assumptions about width or encoding: terminals are UTF-8 capable but width varies;
 read `COLUMNS` and degrade. Be careful with emoji and wide/CJK glyphs in aligned tables (they break
 column math). Respect locale where you format numbers/dates, and keep machine output
 (`--json`) locale-independent so scripts are stable.
 *(Consensus on plain/parseable output across sources; specific locale mechanics are a reasoned
 extension, not pulled verbatim from a single source.)*

### Testing
- Test with a screen reader and a colorblindness simulator to catch
 contrast, clarity, and verbosity problems. See `testing-cli-ux.md`.

## Windows / PowerShell callouts

- Screen readers exist on all platforms (NVDA/JAWS/Narrator on Windows, VoiceOver on macOS, Orca on
 Linux); plain labeled text helps all of them. `NO_COLOR` is honored cross-platform: respect it.
 On legacy Windows consoles, ANSI may not render (see `color-and-styling.md`), so never make ANSI the
 only way meaning is conveyed.

## Edge cases / anti-patterns

- **Don't** use red/green dots, spinners, or box art as the sole signal.
- **Don't** assume 80 columns or that emoji render/measure consistently.
- **Don't** ship prompt flows that require visually scanning an unlabeled menu.

## Do / Don't

- **Do** pair visual cues with text; offer `--plain`/`--json`.
- **Do** test with a screen reader and colorblind simulator.
- **Don't** convey state by color/layout alone.
- **Don't** block assistive/scripted use behind interactive-only UI.

## Related

`color-and-styling.md` · `output-and-formatting.md` · `errors-and-exit-codes.md` ·
`prompts-and-confirmation.md` · `interactivity-tty-and-ci.md` · `testing-cli-ux.md`

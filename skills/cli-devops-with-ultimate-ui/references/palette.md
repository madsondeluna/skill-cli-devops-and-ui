# Palette and glyphs

Source of truth: `assets/theme.json` (theme name `aurora`). Code refers to
roles, never to raw colors. The same code renders on 16, 256 and truecolor
terminals and the theme can be swapped by editing one file. Run
`python scripts/palette.py` to see the swatches in the current terminal and
`python scripts/palette.py --rich` or `--ink` to emit the theme object for
each stack.

## Identity

Cool multi-hue: teal into blue into violet. The gradient is the brand moment
and lives on large decorative surfaces (banner, rule under the input, progress
fill, spinner glyph). Text never sits on a gradient. Interactive elements use
`accent` (blue); secondary highlights use `accent2` (violet); `teal` is the
third voice, for tags and small marks. Status colors keep their conventional
hues (green, amber, red, cyan) so meaning stays universal.

## Semantic roles

| Role | Use | dark bg | light bg | 256 | 16 |
|---|---|---|---|---|---|
| fg | body text | #E6E9F0 | #1B2030 | default | default |
| muted | secondary text, hints, timestamps | #8B95A9 | #5B6472 | 245 | bright black |
| dim | decoration only (rules, guides); never text | #5C6577 | #8A93A3 | 240 | bright black |
| accent | command names, selection, links, focus | #6FA3FF | #2358D6 | 75 | blue |
| accent2 | keys in key value pairs, tags, second highlight | #B49CFF | #6B33D6 | 141 | magenta |
| teal | tertiary marks, tag borders | #3DDBC7 | #0F7A6E | 80 | cyan |
| ok | success, completed, added lines | #6EE39C | #1B7A3E | 114 | green |
| warn | warning, pending, modified | #F2C56B | #8A5A00 | 221 | yellow |
| err | error, failed, removed lines | #FF7B8E | #C4283A | 210 | red |
| info | informational, in progress | #7CD5FF | #0B6FA8 | 117 | cyan |
| border | box edges, table rules | #3A4258 | #CDD3DE | 238 | bright black |
| bg_panel | panel background when supported | #161A26 | #F4F6FA | 234 | none |
| bg_select | selected row background | #243052 | #DDE6FF | 237 | blue bg |

## Contrast (WCAG 2.1, computed from theme.json)

| Role | dark on #000 | dark on bg_panel | light on #FFF | light on bg_panel |
|---|---|---|---|---|
| fg | 17.3 | 14.3 | 16.2 | 15.0 |
| muted | 7.0 | 5.8 | 6.0 | 5.5 |
| dim | 3.6 | 3.0 | 3.1 | 2.9 |
| accent | 8.4 | 6.9 | 6.1 | 5.6 |
| accent2 | 9.1 | 7.6 | 6.8 | 6.3 |
| teal | 12.2 | 10.1 | 5.2 | 4.8 |
| ok | 13.1 | 10.9 | 5.4 | 5.0 |
| warn | 13.0 | 10.7 | 5.9 | 5.5 |
| err | 8.5 | 7.0 | 5.7 | 5.2 |
| info | 12.8 | 10.6 | 5.5 | 5.0 |

Rule: 4.5 or above for any text; 3 to 4.5 for large glyphs and UI marks;
below 3 is decoration. Every text role clears 4.5 on both backgrounds and on
the panel surface. `dim` is the only role in the 3 band, which is why it never
carries text. Status colors are always paired with a glyph or a word so color
is never the only channel.

Background detection: the terminal background is unknown. Default to the dark
set (it degrades more gracefully on mid tone themes). When the stack supports
it (Textual, Bubble Tea v2, crossterm) query OSC 11 with a 100 ms timeout and
switch to the light set when luminance is above 0.5. Always honor an explicit
override: `--theme dark|light` or `TOOL_THEME`.

## Gradient

| Name | Stops (truecolor) | Use |
|---|---|---|
| aurora_dark | #3DDBC7, #38BDF8, #5B9CFF, #8B7BFF, #C084FC | dark backgrounds |
| aurora_light | #0F766E, #0284C7, #2358D6, #5B3FD1, #8A3FC4 | light backgrounds |
| c256 | 80, 75, 111, 141 | 256 color approximation, 4 stops, static |
| c16 | accent only | no gradient |

Where the gradient may appear: the ASCII art banner title, the rule under it
or under an input box, the filled part of a progress bar, the spinner glyph.
Body text, tables, help output and error messages never use it. One moving
gradient at a time: the banner animates and freezes before any spinner or bar
begins cycling.

Animation: shift the hue phase by `phase_step_deg` (6) per frame at `fps`
(15). Reveal for `reveal_ms` (1200) then freeze on the banner; on a spinner or
progress bar keep cycling while the operation runs and freeze at completion.
Interpolate in OKLCH (or linear RGB at minimum), never in sRGB, so the
midpoints between blue and violet do not go grey. The templates in
`assets/templates/` implement this; `rich-gradient` on Python and
`ink-gradient` or `gradient-string` on TypeScript are acceptable when a
dependency is fine.

## Conventional assignments

Beyond the role table, three assignments are worth keeping constant across
tools because users learn them: file paths and URLs in `info` (cyan),
identifiers the user typed or can retype (command names, flags, keys) in
`accent`, and counts, durations and timestamps in `muted`. A path in the same
ink as prose is a path the eye has to search for.

## Glyphs

| Meaning | Unicode | ASCII fallback |
|---|---|---|
| ok | U+2713 | ok |
| error | U+2717 | x |
| warning | U+25B2 | ! |
| info | U+25CF | * |
| pending | U+25CB | o |
| running | spinner frames | - \ / |
| pointer | U+276F | > |
| bullet | U+2022 | * |
| ellipsis | U+2026 | ... |
| tree branch | U+251C U+2500 | |- |
| tree last | U+2514 U+2500 | `- |
| tree line | U+2502 | | |
| progress filled | U+2588 (eighth blocks U+258F to U+2588 for sub cell) | # |
| progress empty | U+2591 | - |
| rule | U+2500 | - |

Box sets: `rounded` (U+256D U+256E U+2570 U+256F with light sides) for panels
and the input frame, `light` for tables, `ascii` (`+ - |`) as fallback. Heavy
and double are not part of the identity.

Emit Unicode only when the locale reports UTF-8, `TERM` is not `dumb` and the
platform is not the Windows legacy console. Provide a `TOOL_ASCII=1` escape
hatch. Emojis are never used: they break column alignment, fonts and screen
readers, and this user does not want them.

## Typography in the terminal

One font, so hierarchy comes from color, bold, dim and spacing.

- Bold for the primary noun on a line (a file name, a command).
- Dim (SGR 2) paired with `muted` for metadata (durations, counts, paths).
- Underline only for OSC 8 hyperlinks. Italic is unreliable across fonts.
- Blink and reverse video are never used, except reverse video for the
  selection in a full screen TUI when background colors are unavailable.
- One blank line between sections, none between rows of one list. Nested
  content indents by two spaces. Columns align with spaces, never tabs.
- Width capped at 100 columns for prose and panels even on wide terminals;
  tables may use the full width.

## Hyperlinks

OSC 8 (`ESC ] 8 ; ; url ESC \ text ESC ] 8 ; ; ESC \`) on a TTY only; piped
output gets the plain URL. Style the link text with `accent` and underline.

## Theme file

Expose the palette in a user theme file (TOML or JSON in the XDG config dir)
keyed by the role names above, with `dark` and `light` built in. This is how
lazygit, Crush and Textual apps let people match their terminal theme.

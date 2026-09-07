# Progress and Feedback

Keeping the user informed during long work so the tool feels responsive and never looks frozen:
spinners, progress bars, and the rules for when to show them (TTY only) and how they interact with
logs and pipes.

**When this applies:** any operation that can take more than a moment (network, large files, many
items), or deciding whether/how to show progress.

## Principles

- **Responsive beats fast.** Print something within ~100 ms; if a network call is coming,
 print before it so the tool doesn't appear hung.
- **Silence looks broken.** For long operations show a spinner or progress bar; if you're
 stuck in one place, show an animation or an ETA.

## Decision rules

### Show progress only on a TTY
- Render spinners/bars/animations only when stdout is a TTY; in non-TTY/CI, suppress them (otherwise
 CI logs fill with redraw spam: "Christmas-tree" output). See
 `color-and-styling.md`, `streams-and-piping.md`.
- Progress is out-of-band → write it to **stderr** so redirected stdout stays clean data.
```
$ tool import big.csv
Importing  [############------]  62%  (12s left)   <- stderr, TTY only
$ tool import big.csv | wc -l                       <- no bar; data only
```

### Progress vs logs
- On success, keep verbose logs hidden behind the progress UI; **on failure, dump the captured logs**
 so the user can debug.
- For parallel work, use a library that renders multiple progress lines coherently; don't interleave
 raw output from concurrent tasks. (`docker pull`'s per-layer progress is the model.)

### Long-running etiquette
- Add timeouts to network/long steps with sensible defaults so the tool can't hang forever.
- Make operations recoverable/resumable where possible so an interrupted run can continue.
- Confirm completion appropriately for the channel (TTY confirmation vs quiet when piped): see
 `output-and-formatting.md`.

## Windows / PowerShell callouts

- PowerShell has `Write-Progress` (a native progress bar) for cmdlets; a cross-platform argv CLI
 should render its own stderr/TTY progress and gate it on capability detection so it degrades on
 legacy consoles. Carriage-return redraws (`\r`) need a VT-capable terminal: feature-detect (see
 `color-and-styling.md`).
- CI detection: treat common CI env vars / non-TTY as "no animation," same as Unix.

## Edge cases / anti-patterns

- **Don't** animate or use `\r` redraws when stdout isn't a TTY.
- **Don't** let a progress bar's frames end up in captured/final output.
- **Don't** block with no feedback during cleanup; if Ctrl-C is pressed during cleanup, allow a
 second Ctrl-C to skip it (see `interactivity-tty-and-ci.md`).

## Do / Don't

- **Do** print within ~100 ms and before network calls.
- **Do** put progress on stderr, TTY-gated, and show ETAs for stalls.
- **Don't** spam progress into pipes/CI.
- **Don't** hide failure logs: surface them on error.

## Related

`output-and-formatting.md` · `streams-and-piping.md` · `interactivity-tty-and-ci.md` ·
`color-and-styling.md`

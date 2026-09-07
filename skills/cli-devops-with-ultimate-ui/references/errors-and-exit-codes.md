# Errors and Exit Codes

Writing errors humans can act on, and choosing exit codes scripts can rely on. Rewrite errors
conversationally with a fix, manage signal-to-noise, and use a **layered exit-code model**: always
correct binary semantics, a small documented set for usability, reserved codes respected, and
optional richer codes where a tool genuinely needs them.

**When this applies:** designing error messages, choosing/duplicating exit codes, mapping failures
for scripts, or handling partial failures.

## Error messages

### Principles
- **Rewrite expected errors for humans** and point at the fix: not
 `EACCES: permission denied`, but:
```
Error: can't write to config.toml: it isn't writable.
Try: chmod +w config.toml
```
- **Manage signal-to-noise:** group many similar errors under one header; put the most
 important line last (eye lands there); use red sparingly.
- **Be specific, not vague:** "it failed" is useless; name what failed and why.
- **For unexpected/internal errors,** show debug detail + how to report a bug (pre-fill an issue URL
 with context); don't dump a raw stack trace by default: gate it behind `--verbose`.

### Where errors go
- Error/warning text → **stderr**; exit non-zero. See `streams-and-piping.md`.
- A usage error may print short help to stderr (see `help-and-usage.md`).

## Exit codes: layered, all-encompassing model

Apply the layers in order; adopt only as much granularity as the tool needs, and **document whatever
set you choose**.

1. **Binary baseline (always true):** `0` = success, non-zero = failure. Scripts and
 `&&`/`||` depend on this; never exit 0 on failure.
2. **Small documented set (recommended default for usability):**
 - `0` success
 - `1` general/runtime error
 - `2` usage/misuse (bad flags or arguments): common convention
 Provide rich stderr messages alongside; this keeps simple tools simple while
 staying script-friendly.
3. **Respect reserved codes** (don't reuse them for your own meanings): shell/Unix convention:
 - `126` command found but not executable; `127` command not found;
 - `128+N` terminated by signal N (e.g., `130` = Ctrl-C/SIGINT); avoid codes above 255.
4. **Optional richer codes** when a tool benefits: map specific, stable codes to distinct failure classes a caller will branch on. A common
 ready-made scheme is BSD `sysexits.h` (`64` usage, `65` data err, `66` no input, `69` unavailable,
 `70` software, `73` can't create, `77` no permission, `78` config). Use it only if callers need to
 distinguish causes, and keep codes stable forever once published.

```
$ tool deploy && echo OK || echo "failed ($?)"
# exit 0 -> OK ; exit 2 -> usage ; exit 1 -> runtime failure
```

### Decision rules
- Before adding granularity, ask: is the failure recoverable on retry? are there partial successes?
 do callers actually branch on the cause? If not, stay at layer 2.
- **Partial failure:** decide and document: non-zero if any item failed (fail-closed) is the common,
 safe default; offer `--keep-going` style behavior explicitly if you continue past errors.
- HTTP/proxy-style tools legitimately map richer codes: that's the layer-4 case.

## Windows / PowerShell callouts

- PowerShell exposes a native command's exit code as `$LASTEXITCODE`, while `$?` is a
 separate boolean: design so the integer code is meaningful, since scripts check `$LASTEXITCODE`.
 Note: PowerShell 5.1 can set `$?` to `$false` on stderr output even when exit code is 0; keep exit
 code authoritative and don't rely on stderr-as-failure.
- The `128+N` signal convention is Unix; on Windows, Ctrl-C handling differs: still return non-zero
 on interruption. Keep the same documented codes cross-platform where you can.

## Edge cases / anti-patterns

- **Don't** encode error detail only in the exit code: humans can't read it; pair codes with stderr
 messages.
- **Don't** renumber published codes; that breaks scripts silently.
- **Don't** treat all stderr output as failure: many tools log progress to stderr while exiting 0.

## Do / Don't

- **Do** make every error state non-zero and every message actionable.
- **Do** document your exit-code table in `--help`/docs.
- **Don't** print stack traces by default.
- **Don't** reuse 126/127/128+N for custom meanings.

## Related

`output-and-formatting.md` · `streams-and-piping.md` · `arguments-and-flags.md` ·
`interactivity-tty-and-ci.md` · `testing-cli-ux.md`

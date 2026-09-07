# Testing CLI UX

How to verify that a CLI's user experience actually holds: using observable, binary checks and real
command output as ground truth rather than opinion. Test the contract (exit codes, stdout/stderr,
TTY vs non-TTY, prompts, help) the same way you'd test any interface.

**When this applies:** writing tests for a CLI's behavior, setting up CI checks, or verifying a UX
change before shipping.

## Principle

- Prefer ground truth over self-assessment: assert against real exit
 codes and captured stdout/stderr, not "looks right." Define the checks before building, and report
 pass/fail honestly (Spec → Verifier → Environment).
- Because non-zero exit codes and the stdout/stderr split are the machine contract, they are exactly what tests should pin down. See `errors-and-exit-codes.md`,
 `streams-and-piping.md`.

## What to test (observable, binary)

### The machine contract
- Exit code is `0` on success and the documented non-zero on each failure class; `--help`/`--version`
 exit `0` (see `errors-and-exit-codes.md`, `help-and-usage.md`).
- Data goes to stdout, messages to stderr: assert each stream separately.
```
out=$(tool export); rc=$?
test "$rc" -eq 0
echo "$out" | head -1 | grep -q '^id,'      # stdout is the CSV
err=$(tool export 2>&1 1>/dev/null)         # capture stderr only
```

### TTY vs non-TTY behavior
- Piped/redirected (non-TTY): no color, no spinner, no prompt; prompts either use flags or fail fast.
- Drive non-interactive paths in tests by piping/`--no-input`; never let a test hang on a prompt.
```
printf '' | tool deploy --no-input --yes   # must not block; must exit deterministically
tool regions | grep -q Common              # human table stays grep-parseable
NO_COLOR=1 tool status | grep -q OK         # meaning present without color
```

### Help, errors, suggestions
- `--help` prints to stdout/exit 0; usage error prints to stderr/exit non-zero; unknown command emits
 a "did you mean" suggestion (see `help-and-usage.md`).

### Stability and idempotence
- Released stdout/`--json` shape stays backward-compatible (add-only); snapshot-test `--json`
 (see `output-and-formatting.md`). Re-running a command is safe/idempotent where promised.

## Decision rules

- Test the **non-interactive** surface in CI (it's deterministic); reserve manual/recorded checks for
 interactive prompts and animations.
- Snapshot machine output (`--json`, `--plain`); assert on *fields*, not exact human-formatted lines
 (which are allowed to change: see `output-and-formatting.md`).
- Include an accessibility pass: `NO_COLOR` output still conveys state; a screen-reader/colorblind
 spot check for human output. See `accessibility-and-i18n.md`.

## Windows / PowerShell callouts

- Assert `$LASTEXITCODE` (the native exit code), not `$?`, in PowerShell tests; on
 PowerShell 5.1 stderr output can flip `$?` to `$false` even on exit 0, so keep the exit code
 authoritative (see `errors-and-exit-codes.md`). Capture native stdout/stderr with care (5.1 wraps
 native stderr as error records). Run the same behavioral suite on both OSes.

## Edge cases / anti-patterns

- **Don't** write tests that depend on a TTY being present (CI has none): drive the non-TTY path.
- **Don't** assert on exact colored/animated output; strip ANSI or set `NO_COLOR`.
- **Don't** let a missing-input case prompt in CI: it will hang.

## Do / Don't

- **Do** assert exit code + stdout + stderr separately, against documented behavior.
- **Do** snapshot `--json` and test `NO_COLOR`/non-TTY paths.
- **Don't** test interactive prompts in a way that can block.
- **Don't** pin human-formatted lines that are allowed to evolve.

## Related

`errors-and-exit-codes.md` · `streams-and-piping.md` · `output-and-formatting.md` ·
`interactivity-tty-and-ci.md` · `accessibility-and-i18n.md` · `behaviour-review.md`

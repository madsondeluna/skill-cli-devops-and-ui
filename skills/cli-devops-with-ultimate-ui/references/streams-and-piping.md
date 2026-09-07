# Streams and Piping

Using stdin/stdout/stderr so a command composes with others. Data goes to stdout, diagnostics to
stderr, and `-` means "use a stream." Designing for pipes is what makes a CLI a building block.

**When this applies:** deciding what goes to stdout vs stderr, supporting pipelines, reading piped
input, or the `-` operand.

## Principles

- **stdout = the program's data; stderr = messages about the program** (logs, progress,
 warnings, errors). This lets `tool | other` pass clean data while the human
 still sees status.
- **Design output as input to the next program**. Line-oriented text composes
 with `grep`/`awk`/`sort`; offer `--json` for structure. See `output-and-formatting.md`.

## Decision rules

### What goes where
```
$ tool export > data.csv      # data on stdout is redirected cleanly
Exporting... done             # this status line is on stderr, still visible
```
- Out-of-band info (spinners, "action" progress, prompts) → stderr, so redirecting stdout keeps data
 pure. See `progress-and-feedback.md`.

### Reading and writing streams
- **Support `-` as an operand** meaning stdin (for reading) or stdout (for writing): `curl … | tar xzf -`, `tool fmt -` reads stdin.
- If the tool needs piped input but stdin is a TTY (nothing piped), show help or exit: don't hang
 waiting on input. See `interactivity-tty-and-ci.md`.
- Detect whether stdin/stdout is a TTY to switch between human and machine modes.

### Pipe-friendly behavior
- Don't colorize or animate when stdout isn't a TTY: see `color-and-styling.md`,
 `progress-and-feedback.md`.
- Flush output promptly so downstream consumers aren't starved; beware full buffering when stdout is
 a pipe.
- Handle `SIGPIPE`/`EPIPE` gracefully: when a downstream reader (e.g., `head`) closes the pipe, exit
 quietly instead of erroring.

## Windows / PowerShell callouts

- Classic Unix pipes pass bytes/text; **PowerShell pipes pass .NET objects**. A
 cross-platform CLI can't assume object pipelines: emit text/JSON on stdout so it works in `cmd`,
 `bash`, and PowerShell alike. PowerShell users then `... | ConvertFrom-Json`.
- On Windows PowerShell 5.1, redirecting a native program's stderr can wrap lines as error records;
 don't rely on stderr semantics for control flow (keep the exit code authoritative: see
 `errors-and-exit-codes.md`). Default redirection encoding is UTF-16; document `-Encoding utf8` if
 users pipe your machine output to a file.

## Edge cases / anti-patterns

- **Don't** send primary data to stderr or status to stdout: it corrupts pipelines.
- **Don't** assume a TTY; check, because CI and pipes are non-TTY.
- Mixing ordered stdout and stderr in a terminal can interleave; keep machine data on stdout only.

## Do / Don't

- **Do** keep stdout pure data; put everything else on stderr.
- **Do** accept `-` for stdin/stdout and detect TTY.
- **Don't** hang waiting for stdin that isn't piped.
- **Don't** crash on a closed downstream pipe.

## Related

`output-and-formatting.md` · `interactivity-tty-and-ci.md` · `progress-and-feedback.md` ·
`errors-and-exit-codes.md`

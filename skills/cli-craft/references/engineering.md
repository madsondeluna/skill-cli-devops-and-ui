# Engineering behind the interface

A CLI that looks excellent and falls over on a real input is worse than a
plain one, because the polish promised competence. This file is the contract
the visual layer rests on: complexity, memory, concurrency, security. Apply it
to any tool that touches files, networks or user supplied data, which is
nearly all of them.

## Complexity, stated not assumed

Before writing the core loop, state the complexity in time and memory as a
function of the input, and put it in the README. Not as decoration: the act of
writing it is what catches the accidental quadratic.

The failures that actually happen in command line tools:

| Pattern | Cost | Fix |
|---|---|---|
| membership test against a list inside a loop | O(n*m) | build a set or dict once, O(n+m) |
| string concatenation in a loop | O(n squared) copies | collect in a list, join once |
| re-reading or re-parsing a file per item | O(n) file reads | parse once into an index |
| sorting inside a loop | O(n squared log n) | sort once outside |
| regex compiled per iteration | constant factor, often 10x | compile at module level |
| nested loop over two datasets | O(n*m) | join on a hash index |
| pairwise comparison of all records | O(n squared) | block or bucket first, compare within buckets |

For a bioinformatics or data tool the input is rarely small: assume the file
is larger than memory until proven otherwise. A tool that is O(n) in time but
O(n) in memory still dies on a 40 GB FASTQ.

## Streaming by default

Read line by line or in chunks; materialise the whole input only when the
algorithm truly needs random access, and say so in the help text when it does.

- Iterate the file handle rather than calling read or readlines.
- Yield from generators through the pipeline instead of building lists between
  stages. Memory then depends on the stage, not the input.
- When random access is unavoidable, use an index, a memory map, or a
  temporary on disk store (sqlite, a sorted spill file), not a dict of
  everything.
- Bound every buffer. An unbounded queue between a fast producer and a slow
  consumer is an out of memory error waiting for a large input.
- Write output as it is produced so a long run is useful when interrupted, and
  flush on a schedule rather than every record.

Report memory the same way as progress: peak resident size under `--verbose`
is what turns a vague report of a crash into a bug you can fix.

## Concurrency worth its complexity

Parallelism is a last resort, after the algorithm is right. When it is
warranted:

- CPU bound work: a process pool sized to the core count, with the input in
  chunks large enough that the serialisation cost is amortised. Default the
  worker count to the CPU count, expose `--threads` or `--jobs`, and accept 0
  or auto to mean the default.
- IO bound work: async or a thread pool with a bounded semaphore. Bound the
  concurrency, always: an unbounded fan out of network calls is a self
  inflicted denial of service on whatever you are calling.
- Determinism: results must not depend on completion order. Collect with an
  index and sort before writing, or write to per worker files and merge.
- Progress across workers goes through one live region, never one bar per
  worker fighting for the same lines.
- Retry with exponential backoff and jitter, a cap on attempts, and only on
  errors that are actually transient. Retrying a 400 forever is a loop.
- Cancellation must reach the workers. Ctrl-C that kills the parent and leaves
  a pool running is the worst of both worlds.

## Security for tools that run on someone else's machine

Every one of these has been a real CVE class in real CLI tools.

- Never build a shell command by string interpolation. Pass an argument list
  and keep `shell=False`. If a shell is genuinely required, quote with the
  language's own quoting function, never with your own.
- Validate paths that come from input or archives. Resolve to an absolute path
  and confirm it stays inside the intended directory before writing, or an
  entry named `../../etc/passwd` in a tarball becomes an arbitrary write.
- Secrets never go in flags: the whole command line is visible in the process
  table and lands in shell history. Accept them from an environment variable,
  a file with checked permissions, or stdin, and never echo or log them.
- Files created with secrets get mode 600, and temporary files are created
  with `mkstemp` in a private directory, not with a predictable name in
  `/tmp`, which is a symlink attack.
- Parse untrusted input with a real parser and a size limit. Never `eval`,
  never `pickle`, never YAML's unsafe loader. Cap the decompressed size of any
  archive you expand, or a small file expands into a full disk.
- Verify TLS certificates. Disabling verification to make a demo work is how
  it ships.
- Pin dependencies with a lock file, and keep the dependency count low: every
  package is code running with the user's privileges.
- The tool should refuse to do something destructive that was not asked for.
  Anything that deletes or overwrites needs `--dry-run` to exist, needs the
  confirmation to state the blast radius, and needs the non interactive path
  to require an explicit `--force`.

## What the tests must cover

The visual layer already has its harness (`scripts/check_cli.py`). The core
needs its own, and these four cases catch most of what ships broken:

1. The empty input and the single record input.
2. An input larger than a comfortable buffer, to prove streaming (generate it
   in the test rather than committing it).
3. Malformed input, confirming the error names the line or record and exits 1.
4. Interruption partway, confirming partial output is either valid or removed,
   never a truncated file that looks complete.

Property based testing (Hypothesis) earns its place for parsers and format
converters, where the invariant is easy to state and the edge cases are
endless.

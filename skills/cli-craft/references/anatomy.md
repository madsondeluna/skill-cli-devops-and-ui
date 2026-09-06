# Anatomy of a terminal screen

A vocabulary of components, each with its purpose, a text mock, and the rules that keep it robust. Compose screens from these; do not invent new shapes unless a component here does not fit.

All mocks use the ASCII fallback so they render anywhere; on a UTF-8 TTY substitute the glyphs from `palette.md`.

## Banner

Shown once, on interactive start (bare invocation, a REPL, a TUI, or
`--help`). Never on every subcommand, never when stderr is not a TTY, never in
`--quiet`. Four parts, in order:

1. The tool name in the shadow font (`ui.ascii_art`), coloured by one
   continuous gradient across the whole block, wiped in over the first third
   of 1200 ms, then crossed twice by a highlight sweep, then frozen:

```
 ██████╗██╗     ██╗       ██████╗██████╗  █████╗ ███████╗████████╗
██╔════╝██║     ██║      ██╔════╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
██║     ██║     ██║█████╗██║     ██████╔╝███████║█████╗     ██║
██║     ██║     ██║╚════╝██║     ██╔══██╗██╔══██║██╔══╝     ██║
╚██████╗███████╗██║      ╚██████╗██║  ██║██║  ██║██║        ██║
 ╚═════╝╚══════╝╚═╝       ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝
```

   The glyph table (`font-shadow.json`, generated once from the public figlet
   font `ansi_shadow` and shipped beside `ui.py`) means no runtime dependency.
   Three levels of degradation, none of which the caller handles: too wide for
   the shadow font falls back to the 5x5 block font, too wide for that falls
   back to one upper case line, and a non UTF-8 locale goes straight to the
   line.
2. The slogan on the next line in `muted`: one short sentence, lower case, no
   period, saying what the tool is for.
3. The general options: label in `accent`, description in `muted`, aligned in
   two columns, four to six entries. These are the commands or flags a new
   user reaches for first, not the full option list, which lives in `--help`.
4. A gradient rule closing the block.

Everything goes to stderr. Titles longer than the terminal width degrade to a
single upper case line, as does a non UTF-8 locale.

A compact variant replaces the art with one line when the tool starts a
session rather than a menu, carrying the context the user would otherwise have
to ask for:

```
  tool v1.4.0                                  ~/projects/amp-pipeline
  model: claude-sonnet-4-6   session: 3f9a   type /help for commands
```

At most three lines, name and version carrying the gradient, everything else
muted.


## Status line

One line, overwritten in place on a TTY, appended as separate lines when piped.

```
- resolving dependencies (3.2s)
```

Glyph then verb phrase in present tense then elapsed in muted parentheses after 2 s. On completion the line is replaced by a final state, never left as the last spinner frame:

```
ok resolved 142 packages (3.4s)
```

## Step list

For commands with sequential phases. Each step is a status line; completed steps keep their final state, the current step animates, future steps are muted.

```
ok  read config                 config.toml
ok  validate inputs             12 samples
-   align reads                 sample 7/12  ###########---------  58%
o   call variants
o   write report
```

Rules: align the three columns (glyph, step name, detail). The detail column truncates from the left for paths (`.../data/sample_07.fq.gz`) and from the right for text. Total width never exceeds terminal width.

### Three shapes for multi step work

Pick by how much the user needs to see at once:

- Checklist: the whole plan is visible from the start, each line changing
  state in place. Use when the user should know what is coming, for example a
  deployment or a migration.
- Phase: a heading per stage, the work under it, a closing line with the
  elapsed time. Use when stages are long enough that the user reads them
  separately, and when scrollback will be pasted into an issue.
- Narrative: one line per step, appended as it completes, no live region. Use
  when the tool runs inside CI or a log, where nothing may overwrite.

The checklist and phase shapes need a live region and degrade to the narrative
shape automatically when animation is off. Do not mix two shapes in one
command: the user reads the first one they see and expects it to continue.

## Progress bar

Known total. Lives on stderr, one line, updated at most 20 times per second.

```
aligning  [##########----------]  50%  6/12  00:41 < 00:39  1.2 MB/s
```

Components in order: label, bar, percent, count, elapsed and ETA, rate. Drop components from the right as width shrinks. Below 40 columns show only label and percent. When piped, print one line per 10 percent or every 5 s, whichever is less frequent, and a final 100 percent line.

Multi bar (parallel tasks): one line per task plus an overall line at the bottom; complete tasks collapse to a single `ok` line.

## Table

```
NAME            STATUS    DURATION   SAMPLES
pipeline-a      ok        4m12s      120
pipeline-b      failed    0m03s      0
pipeline-c      running   1m40s      48
```

Rules: header in bold muted, uppercase, no color; body values colored by semantic role only in the status column; numbers right aligned; text left aligned; columns padded with two spaces; no vertical borders in shapes 1 to 3 (borders are for TUIs and for tables that need visual grouping). Above 8 columns offer `--columns` to select. When piped, output tab separated with the same header, which is what `cut -f` expects. Wrap long cells only in the last column.

## Key value block

For `info`, `status`, `config show`.

```
Name        amp-pipeline
Profile     docker
Work dir    /scratch/run-2026-09-06
Last run    2 hours ago (ok)
```

Keys in accent2 or muted, values in fg, aligned on the longest key plus two spaces. When piped, `key\tvalue` per line.

## Tree

```
results/
|- alignments/
|  |- sample_01.bam
|  `- sample_02.bam
|- variants.vcf.gz
`- report.html
```

Guide lines in border color, directory names in accent, files in fg, sizes or counts in muted at the right edge. Collapse beyond a depth (`--depth`) and beyond 200 entries with a `... and 38 more` line.

## Panel

A bordered block used for a quotable unit: a diff, a code excerpt, a message from another party (the model, a remote), a final summary.

```
+- report ----------------------------------------------+
| 12 samples processed, 11 ok, 1 failed                 |
| failed: sample_07 (alignment rate below 60%)          |
| output: results/report.html                           |
+-------------------------------------------------------+
```

Rules: rounded border on UTF-8, title in the top edge, padding of one space, width fits content up to terminal width minus 2, never nested more than one level. When piped, drop the border and indent the content by two spaces under the title.

## Diff

```
  src/pipeline.py
  @@ -12,4 +12,5 @@
   def align(sample):
  -    return run("bwa", sample)
  +    threads = os.cpu_count()
  +    return run("bwa", "-t", str(threads), sample)
```

Removed lines in err color, added in ok color, context in fg, hunk header in muted, file name in bold. Prefix with the marker character so color is not the only carrier. Offer word level highlighting inside changed lines when the stack supports it (rich, diff-match-patch, Lip Gloss). When piped, output unified diff exactly as `diff -u` would.

## Prompt

```
? Delete 3 runs from /scratch? (y/N)
? Profile:  > docker
             singularity
             conda
```

Question glyph in accent, question in bold, default in parentheses. Select lists show the pointer on the current item, 7 visible items with scroll indicators beyond that, type to filter. Multi select uses `[x]` and `[ ]`. Prompts render on stderr and read from stdin; the answer is echoed once on confirm.

## Log line

For `--verbose` output and long running daemons.

```
11:42:03  info   started worker 3
11:42:07  warn   retrying fetch (attempt 2/3)
11:42:09  error  fetch failed: timeout after 30s
```

Timestamp muted, level in its role color padded to 5, message in fg. No level glyphs; the word is the carrier. In JSON mode each line is a JSON object (`--jsonl`).

## Footer

Only in shapes 3 and 4. One line at the bottom with the most useful keys or state.

```
 ctrl+c quit   tab switch   ? help                    tokens 12.4k  $0.03
```

Keys in accent, labels in muted, state right aligned. Shrinks to the first two items on narrow terminals.

## Summary

The last thing a command prints on success. Short, factual, points to the output.

```
ok  12 samples in 4m12s, report at results/report.html
```

One line preferred. Up to a key value block for complex commands. Never a panel with a large title, never "Done!", never emojis.

## Composition rules

- One primary component per screen state. A step list with a progress bar inside the current step is one component; a step list next to a table is two and needs a blank line between them.
- Vertical rhythm: blank line between components, none inside.
- Left edge aligned at column 0 for shapes 1 and 2, at column 1 (one space indent) for shapes 3 and 4 where the terminal edge touches the border.
- Everything that animates lives at the bottom of the current output. Completed content above it is immutable so scrollback stays readable.

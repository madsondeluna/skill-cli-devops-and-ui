# pseq

Protein FASTA analysis from the command line.

Reference example for this skill: a real tool, not a snippet. It applies both
halves at once, the behaviour rules and the aurora identity, and it is the
thing to read when the question is what a finished tool built from here looks
like. `src/pseq/ui.py` is the vendored template, copied unchanged;
`make example` in the repository root fails if the two drift apart.

Run it:

```
cd examples/pseq
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pseq                                  # banner and the command list
pseq stats examples/sample.fa         # the table, with colour and bars
pseq stats examples/sample.fa | head  # the same data as plain TSV
pytest -q
```

## Install

```
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.10 or later. Runtime dependency: Typer.

## Quick start

`examples/sample.fa` ships with the repository and every command below runs against it.

```
pseq stats examples/sample.fa
pseq composition examples/sample.fa
pseq filter --min-length 30 examples/sample.fa > long.fa
pseq motif --prosite --pattern "N-{P}-[ST]" examples/sample.fa
pseq validate examples/sample.fa; echo "exit $?"
pseq filter --no-ambiguous examples/sample.fa | pseq stats --json | jq '.[] | select(.pi > 9)'
```

## Commands

| Command | Output | Options |
| --- | --- | --- |
| `pseq stats [FILE]...` | id, length, mw, pi, gravy, charge | `--ph 7.0`, `--summary` |
| `pseq composition [FILE]...` | residue, count, frequency | `--per-sequence` |
| `pseq filter [FILE]...` | FASTA | `--min-length N`, `--max-length N`, `--pattern REGEX`, `--prosite`, `--id REGEX`, `--ids-file PATH`, `--no-ambiguous`, `--invert`, `--line-width N` |
| `pseq validate [FILE]...` | level, id, where, problem | `--allow-ambiguous` |
| `pseq motif [FILE]...` | id, start, end, match | `--pattern PATTERN` (required), `--prosite` |
| `pseq convert [FILE]...` | FASTA, or id/description/seq with `--tsv`/`--json` | `--line-width N`, `--lower` |
| `pseq completion SHELL` | completion script | bash, zsh, fish, powershell |

## Shell completion

`completion` writes the script to stdout; the destination directory must already exist.

```
# zsh
mkdir -p ~/.zfunc && pseq completion zsh > ~/.zfunc/_pseq
# then in ~/.zshrc, before compinit:
#   fpath=(~/.zfunc $fpath)

# bash
mkdir -p ~/.local/share/bash-completion/completions
pseq completion bash > ~/.local/share/bash-completion/completions/pseq

# current shell only
eval "$(pseq completion zsh)"
```

## Common options

| Option | Effect |
| --- | --- |
| `-o, --output PATH` | write to PATH; `-` is stdout |
| `--json` | JSON array of objects |
| `--tsv` | tab-separated, header row; default when stdout is not a TTY |
| `-q, --quiet` | suppress status, warnings and animation |
| `-v, --verbose` | repeatable; `-vv` prints tracebacks |
| `--color WHEN` | `auto`, `always` or `never` |
| `--no-color` | same as `--color never` |
| `--no-art` | keep color, drop bars and banner |
| `-h, --help`, `--version` | |

## Look

The visual layer is the `aurora` theme from the `cli-devops-with-ultimate-ui`
skill, vendored as `src/pseq/ui.py` next to the code that uses it. Colour is
addressed by role, never by hex, and the same code renders on truecolor, 256
and 16 colour terminals.

On a terminal, `stats`, `composition`, `validate` and `motif` render a titled
gradient rule, a gradient header, semantic colour and inline bars: sequence
length, a diverging Kyte-Doolittle axis, residue frequency, and the flanking
context of every motif hit. `--summary` renders a bordered panel. Reading and
computing show a gradient spinner and progress bar on stderr. `pseq` with no
command wipes in the block-letter banner and freezes it.

None of that reaches a pipe. When stdout is not a terminal the same commands
emit plain TSV. The banner, the spinner, the progress bar, warnings and the
closing count all live on stderr, so `pseq stats in.fa | jq` sees data only.

| Signal | Role | Meaning |
| --- | --- | --- |
| cyan | info | acidic residue, pI below 6, negative net charge |
| teal | teal | hydrophilic GRAVY |
| violet | accent2 | basic residue, pI above 8, positive net charge |
| amber | warn | hydrophobic residue, positive GRAVY, validation warning |
| red | err | validation error |

Colour is never the only channel: every value is printed as a number, every
validation issue names its level as a word, and both carry a glyph.

### Width

The table measures the terminal. Bars shrink before they are dropped, and the
widest text column is truncated with an ellipsis only after the bars are gone.
No line ever exceeds the reported width, which is capped at 100 columns.

### Colour precedence

`--color never` beats `--no-color`, which beats `--color always`, which beats
`NO_COLOR`, which beats `FORCE_COLOR`, which beats terminal detection.
`TERM=dumb`, `CI` and a non-TTY stdout each disable colour or animation.
`--color always` also selects the terminal renderer, so
`pseq stats in.fa --color always | less -R` keeps the bars.

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | any non-empty value disables colour |
| `FORCE_COLOR` | `1` for 16 colours, `2` for 256, anything else for truecolor |
| `PSEQ_THEME` | `light` switches to the light-background palette |
| `PSEQ_ASCII` | any value forces ASCII glyphs and box drawing |
| `PSEQ_NO_ANIMATION` | any value keeps colour and drops live redraws |
| `CI` | disables animation, keeps colour |

Truecolor needs `COLORTERM=truecolor`; otherwise the palette degrades to 256
and then to the 16 ANSI colours, which follow the user's own theme. Box
drawing and block characters fall back to ASCII when stdout is not UTF-8.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | runtime error (missing file, I/O) |
| 2 | usage error (unknown flag, invalid value, conflicting options) |
| 3 | `validate` or the parser found data problems |
| 130 | interrupted |

## Properties

| Value | Method |
| --- | --- |
| mw | average residue masses plus water, Da |
| pi | bisection on net charge, pKa: N-term 9.69, C-term 2.34, K 10.53, R 12.48, H 6.00, D 3.65, E 4.25, C 8.18, Y 10.07 |
| gravy | Kyte-Doolittle mean hydropathy |
| charge | net charge at `--ph` |

Ambiguous residues (B, J, O, U, X, Z) are excluded from mw, pi and gravy; `stats` warns on stderr.

The pI comes from the Lehninger pKa set listed above. ExPASy ProtParam uses a different scale, so values differ by a few tenths of a pH unit; ubiquitin gives 7.68 here and 6.56 there. Compare pI values only within this tool.

## Tests

```
pytest
```

`tests/test_cli.py` covers exit codes, stream separation and parsing.
`tests/test_visual.py` runs the tool inside a pseudo-terminal, with stderr on a
separate pipe, to prove that colour and animation appear on a terminal and
never in a pipe.

The terminal hygiene harness that ships with the skill reports no findings:

```
python3 ~/.claude/skills/cli-devops-with-ultimate-ui/scripts/check_cli.py \
  --timeout 30 -- pseq stats examples/sample.fa
```

It exercises the piped path, `NO_COLOR`, `CI`, a pty, `--help`, `--version`,
`--json`, a usage error and Ctrl-C, and checks for ANSI leaking into a pipe,
stdout pollution, over-wide lines and exit codes.

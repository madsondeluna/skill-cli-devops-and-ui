# CLI Design Review Checklist

A binary, severity-labeled checklist for auditing an existing CLI against this skill's guidance. Run
it top to bottom, mark each item pass/fail/n-a with evidence (real command output), and report
findings by severity. Built on the three-layer method: define the checks first, use ground truth, and
report honestly.

**When this applies:** reviewing or critiquing an existing CLI, gating a release, or self-auditing a
CLI you just built.

## How to run it

1. For each item, run the command and capture exit code + stdout + stderr (ground truth, not opinion).
2. Mark **pass / fail / n-a** and paste the evidence.
3. Report findings grouped by severity. Suggested severities:
 - **blocker**: breaks scripting/automation or is unsafe (e.g., prompt hangs CI, exit 0 on failure,
 secret on the command line, destructive action with no guard).
 - **major**: real usability/consistency problem (inconsistent flags, color-only meaning, no
 `--json`, unhelpful errors).
 - **minor**: polish (wording, ordering, density).

## Checklist

### Arguments & flags: see `arguments-and-flags.md`
- [ ] Every flag has a long form; common ones have stable short forms; `-h` is help-only. (major)
- [ ] No secrets accepted via flags or env vars. (blocker)
- [ ] Sensible defaults for the majority; booleans need no value. (major)
- [ ] POSIX baseline honored where applicable (`--` ends options; `-` = stdin/stdout). (major)

### Command shape: see `subcommands-and-command-shape.md`
- [ ] One consistent word order (noun-verb or verb-noun), never mixed. (major)
- [ ] Flag names/output consistent across subcommands. (major)
- [ ] No catch-all subcommand; no arbitrary prefix abbreviation. (major)

### Help & usage: see `help-and-usage.md`
- [ ] `--help`/`-h` and (for multi-command tools) `tool help <cmd>` work; help → stdout, exit 0. (major)
- [ ] Concise help on missing args; full help leads with examples. (major)
- [ ] Unknown command/typo yields a "did you mean" suggestion. (minor)

### Output: see `output-and-formatting.md` / `streams-and-piping.md`
- [ ] Data → stdout, messages → stderr. (blocker)
- [ ] Success output is context-dependent (confirm on TTY, quiet/data when piped). (major)
- [ ] `--json` (or `--plain`) available; human tables are grep-parseable. (major)
- [ ] Released output is backward-compatible (add-only). (major)
- [ ] Pager/animation only on a TTY. (minor)

### Color: see `color-and-styling.md`
- [ ] Color disabled off-TTY, on `NO_COLOR`, on `--no-color`, on `TERM=dumb`. (major)
- [ ] Meaning never conveyed by color alone. (major)
- [ ] Windows VT handled or color disabled gracefully on legacy consoles. (minor)

### Errors & exit codes: see `errors-and-exit-codes.md`
- [ ] Exit `0` only on success; documented non-zero on failure; reserved 126/127/128+N respected. (blocker)
- [ ] Error messages are specific and actionable; no default stack traces. (major)
- [ ] Exit-code table documented. (minor)

### Prompts & interactivity: see `prompts-and-confirmation.md` / `interactivity-tty-and-ci.md`
- [ ] Every prompt has a flag/arg bypass and a `--no-input`/`--yes` path. (blocker)
- [ ] Prompts only when stdin is a TTY; non-TTY fails fast naming the flag. (blocker)
- [ ] Destructive actions guarded; severity scales with blast radius; secrets not echoed. (blocker)
- [ ] Ctrl-C works mid-network; cleanup is bounded. (major)

### Config: see `config-env-and-precedence.md`
- [ ] Documented precedence (flags > env > project > user > system). (major)
- [ ] Standard locations (XDG / `%APPDATA%`); config validated as untrusted input. (minor)
- [ ] No consent-free edits to files the tool doesn't own. (major)

### Progress: see `progress-and-feedback.md`
- [ ] Feedback within ~100 ms / before network calls; progress on stderr, TTY-only. (major)
- [ ] Failure logs surfaced on error. (major)

### Accessibility & i18n: see `accessibility-and-i18n.md`
- [ ] Output meaningful with `NO_COLOR`; plain/`--json` mode exists. (major)
- [ ] Descriptive text (no "it failed"); not dependent on visual scanning. (major)
- [ ] No assumption of 80 columns; emoji/CJK width handled in tables. (minor)

### Testing: see `testing-cli-ux.md`
- [ ] Non-interactive paths covered in CI; exit/stdout/stderr asserted separately. (major)
- [ ] `--json` snapshotted; `NO_COLOR`/non-TTY tested; PowerShell uses `$LASTEXITCODE`. (minor)

## Worked example

Each item is checked by running the tool and keeping the evidence. Exit code,
stdout and stderr are captured separately, because a finding that mixes them
proves nothing:

```
$ mytool export --format csv > out.csv; echo "exit=$?"
Exporting 1200 rows... done
exit=0
$ head -2 out.csv
Exporting 1200 rows... done
id,name
```

The progress line landed on stdout, so it is now the first row of the CSV.
That is a blocker: every pipeline reading this tool is corrupted. The report
states it once, with the evidence and the fix.

```
blocker  streams   progress written to stdout corrupts piped data
  evidence: head -2 out.csv shows "Exporting 1200 rows... done" as row 1
  fix:      write progress to stderr; see streams-and-piping.md
major    exit      --format bogus exits 0 with an empty file
  evidence: mytool export --format bogus; echo $? -> 0, out.csv is 0 bytes
  fix:      validate the value, print what is valid, exit 2
minor    help      no examples in --help
  fix:      lead with two real invocations; see help-and-usage.md
```

Findings are ordered by what they cost the user, not by how far the tool sits
from a preference. A tool can pass every item here and still be unpleasant to
look at: the visual layer is a separate review, in
`cli-devops-with-ultimate-ui`.

## Do / Don't (for the reviewer)

- **Do** capture real exit code + stdout + stderr as evidence for each item; opinion is not a finding.
- **Do** sort findings by severity (blocker → major → minor) and lead with blockers.
- **Do** test the non-interactive path (pipe / `--no-input`) so the review itself can't hang.
- **Don't** mark an item pass without running it; **don't** file style nits as blockers.
- **Don't** penalize human-output wording changes that are explicitly allowed to evolve (see
 `output-and-formatting.md`).

## Three-layer framing (why this checklist exists)

- Spec: state what "good CLI UX" means up front (this checklist).
 Verifier: each item is observable and binary, checked against real command output. Environment:
 apply the platform's conventions (Unix and Windows) and don't break users' existing scripts.

## Related

`../SKILL.md` · `behaviour-index.md` · every component file referenced above.

# Behaviour references: index

Start here. Each component is a self-contained, original guide. Load only what the task
needs (progressive disclosure). Metadata: `topics.json` (topic → file + keywords). Guidance gives
equal weight to Unix/POSIX and Windows/PowerShell and flags divergences.

| Component | One-line summary | Read this when… |
| --- | --- | --- |
| [arguments-and-flags.md](arguments-and-flags.md) | Positional args vs named flags; POSIX-style syntax; defaults; no secrets on the CLI | designing how a command takes input |
| [subcommands-and-command-shape.md](subcommands-and-command-shape.md) | Grouping, naming, and word order (noun-verb default) | a tool has more than one command |
| [prompts-and-confirmation.md](prompts-and-confirmation.md) | Prompts with non-interactive escape hatches; danger-scaled confirmation | adding prompts or destructive-action guards |
| [help-and-usage.md](help-and-usage.md) | `-h`/`--help`, usage synopsis, examples-first, "did you mean" | designing help/usage output |
| [output-and-formatting.md](output-and-formatting.md) | What to print, `--json`/`--plain`, tables, context-dependent success output | deciding what a command prints |
| [color-and-styling.md](color-and-styling.md) | ANSI color as enhancement; `NO_COLOR`/TTY rules; Windows VT | adding or gating color |
| [errors-and-exit-codes.md](errors-and-exit-codes.md) | Actionable errors; layered exit-code model; reserved codes | designing errors and exit codes |
| [streams-and-piping.md](streams-and-piping.md) | stdout=data, stderr=messages; `-` for streams; pipe-friendliness | making a command compose in pipelines |
| [progress-and-feedback.md](progress-and-feedback.md) | Responsiveness, spinners/progress bars, TTY-only animation | long-running operations |
| [interactivity-tty-and-ci.md](interactivity-tty-and-ci.md) | TTY detection, `--no-input`, signals, unattended/CI safety | interactive vs non-interactive behavior |
| [config-env-and-precedence.md](config-env-and-precedence.md) | Flags vs env vs files; precedence; XDG/`%APPDATA%`; no secrets in env | designing configuration |
| [accessibility-and-i18n.md](accessibility-and-i18n.md) | Meaning without color; screen-reader-safe output; locale/width | any user-facing output |
| [testing-cli-ux.md](testing-cli-ux.md) | Verify exit/stdout/stderr, TTY paths, `--json` snapshots as ground truth | testing CLI behavior/UX |
| [skill-format-and-discovery.md](skill-format-and-discovery.md) | Agent Skills standard; Codex/Claude discovery; trigger-rich description | authoring/relocating this or any skill |
| [behaviour-review.md](behaviour-review.md) | Binary, severity-labeled audit checklist | reviewing or gating an existing CLI |

## Reading paths

- **New CLI from scratch:** subcommands-and-command-shape → arguments-and-flags → help-and-usage →
  output-and-formatting → errors-and-exit-codes, then the rest as needed.
- **Reviewing an existing CLI:** start at behaviour-review.md and follow its links.
- **Output/automation focus:** streams-and-piping → output-and-formatting → color-and-styling →
  progress-and-feedback.
- **Safety/automation focus:** prompts-and-confirmation → interactivity-tty-and-ci →
  config-env-and-precedence.

## Source disagreements (reconciled in the components)

- **Command word order:** noun-verb/area-grouping recommended; verb-noun is a noted alternative.
- **Exit codes:** layered model: binary baseline, small documented set, reserved codes, optional
  richer codes (reconciles the minimal and granular approaches).
- **Success output:** context-dependent: confirm on a TTY, quiet when piped (reconciles the
  confirm-for-humans and silent-for-scripts approaches).

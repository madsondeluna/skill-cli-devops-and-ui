# Bash and POSIX shell

Use for wrappers, glue, install scripts and pipeline launchers. Bash gives no framework; the discipline is a small output library at the top of the script that every message goes through. The library below is the reference implementation; paste it into scripts (or source it from a shared `lib/ui.sh`).

Target Bash 4+ (`#!/usr/bin/env bash`, `set -euo pipefail`). When POSIX sh is required, drop arrays and `[[`, keep everything else; `printf` and `tput` are POSIX.

## Output library

```bash
#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------
# ui: capability detection, colors, glyphs, messages, spinner
# All decoration goes to stderr. Results go to stdout via plain echo.
# ---------------------------------------------------------------

ui_init() {
  # Color level: 0 none, 1 basic16, 2 ansi256, 3 truecolor
  UI_COLOR=0
  if [[ "${TOOL_COLOR:-auto}" == "never" || -n "${NO_COLOR+x}" ]]; then
    UI_COLOR=0
  elif [[ "${TOOL_COLOR:-auto}" == "always" || -n "${FORCE_COLOR:-}" ]]; then
    UI_COLOR=1
    [[ "${FORCE_COLOR:-}" == "2" ]] && UI_COLOR=2
    [[ "${FORCE_COLOR:-}" == "3" ]] && UI_COLOR=3
  elif [[ -t 2 && "${TERM:-dumb}" != "dumb" ]]; then
    case "${COLORTERM:-}" in truecolor|24bit) UI_COLOR=3 ;; *)
      case "${TERM:-}" in *256color*) UI_COLOR=2 ;; *) UI_COLOR=1 ;; esac ;;
    esac
  fi

  # Unicode: only on a UTF-8 locale and not explicitly disabled
  UI_UTF8=0
  if [[ -z "${TOOL_ASCII:-}" ]] && locale 2>/dev/null | grep -qi 'utf-\?8'; then UI_UTF8=1; fi
  [[ "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" == *[Uu][Tt][Ff]-8* ]] && [[ -z "${TOOL_ASCII:-}" ]] && UI_UTF8=1

  # Interactive: stdin and stderr are terminals, not CI, not --no-input
  UI_INTERACTIVE=0
  [[ -t 0 && -t 2 && -z "${CI:-}" && -z "${TOOL_NO_INPUT:-}" ]] && UI_INTERACTIVE=1

  # Animate: stderr is a TTY, not CI, not disabled
  UI_ANIMATE=0
  [[ -t 2 && -z "${CI:-}" && -z "${TOOL_NO_ANIMATION:-}" && "${TERM:-dumb}" != "dumb" ]] && UI_ANIMATE=1

  UI_WIDTH=$(tput cols 2>/dev/null || echo "${COLUMNS:-80}")

  # Semantic roles. Truecolor uses 24 bit SGR, lower levels use 16 color SGR.
  if (( UI_COLOR >= 3 )); then
    C_FG=$'\e[38;2;230;230;230m'; C_MUTED=$'\e[38;2;138;143;152m'
    C_ACCENT=$'\e[38;2;122;162;247m'; C_ACCENT2=$'\e[38;2;187;154;247m'
    C_OK=$'\e[38;2;158;206;106m'; C_WARN=$'\e[38;2;224;175;104m'
    C_ERR=$'\e[38;2;247;118;142m'; C_INFO=$'\e[38;2;125;207;255m'
  elif (( UI_COLOR >= 1 )); then
    C_FG=$'\e[39m'; C_MUTED=$'\e[90m'; C_ACCENT=$'\e[34m'; C_ACCENT2=$'\e[35m'
    C_OK=$'\e[32m'; C_WARN=$'\e[33m'; C_ERR=$'\e[31m'; C_INFO=$'\e[36m'
  else
    C_FG=''; C_MUTED=''; C_ACCENT=''; C_ACCENT2=''; C_OK=''; C_WARN=''; C_ERR=''; C_INFO=''
  fi
  if (( UI_COLOR >= 1 )); then C_BOLD=$'\e[1m'; C_DIM=$'\e[2m'; C_RESET=$'\e[0m'
  else C_BOLD=''; C_DIM=''; C_RESET=''; fi

  if (( UI_UTF8 )); then G_OK=$'\u2713'; G_ERR=$'\u2717'; G_WARN=$'\u25b2'; G_INFO=$'\u25cf'; G_PTR=$'\u276f'; G_DOT=$'\u2022'
  else G_OK='ok'; G_ERR='x'; G_WARN='!'; G_INFO='*'; G_PTR='>'; G_DOT='*'; fi
}

# Messages: all to stderr, all with a glyph or a word so color is never the only signal
ui_ok()    { printf '%s%s%s %s\n' "$C_OK" "$G_OK" "$C_RESET" "$*" >&2; }
ui_info()  { printf '%s%s%s %s\n' "$C_INFO" "$G_INFO" "$C_RESET" "$*" >&2; }
ui_warn()  { printf '%swarning:%s %s\n' "$C_WARN" "$C_RESET" "$*" >&2; }
ui_error() { printf '%serror:%s %s\n' "$C_ERR" "$C_RESET" "$*" >&2; }
ui_hint()  { printf '  %shint:%s %s\n' "$C_MUTED" "$C_RESET" "$*" >&2; }
ui_step()  { printf '%s%s%s %s%s%s\n' "$C_ACCENT" "$G_PTR" "$C_RESET" "$C_BOLD" "$*" "$C_RESET" >&2; }
ui_kv()    { printf '%s%-14s%s %s\n' "$C_MUTED" "$1" "$C_RESET" "$2" >&2; }
ui_rule()  { local w=${1:-$UI_WIDTH} ch='-'; (( UI_UTF8 )) && ch=$'\u2500'; printf '%s%s%s\n' "$C_MUTED" "$(printf "%${w}s" '' | sed "s/ /$ch/g")" "$C_RESET" >&2; }

# die <exit_code> <message> [hint]
die() { local code=$1; shift; ui_error "$1"; [[ -n "${2:-}" ]] && ui_hint "$2"; exit "$code"; }

# Spinner: runs a command in the foreground, animates on stderr, prints the final state.
# Usage: ui_spin "aligning reads" bwa mem ... > out.sam
ui_spin() {
  local msg=$1; shift
  if (( ! UI_ANIMATE )); then
    ui_info "$msg"; "$@"; local rc=$?
    (( rc == 0 )) && ui_ok "$msg" || ui_error "$msg (exit $rc)"; return $rc
  fi
  local frames='-\|/' i=0 start=$SECONDS
  (( UI_UTF8 )) && frames=$'\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f'
  printf '\e[?25l' >&2
  "$@" & local pid=$!
  trap 'kill "$pid" 2>/dev/null; printf "\e[?25h\n" >&2; exit 130' INT TERM
  while kill -0 "$pid" 2>/dev/null; do
    local f=${frames:i%${#frames}:1} el=''
    (( SECONDS - start >= 2 )) && el=" ${C_MUTED}($((SECONDS - start))s)${C_RESET}"
    printf '\r\e[K%s%s%s %s%s' "$C_INFO" "$f" "$C_RESET" "$msg" "$el" >&2
    i=$((i+1)); sleep 0.09
  done
  wait "$pid"; local rc=$?
  trap - INT TERM
  printf '\r\e[K\e[?25h' >&2
  (( rc == 0 )) && ui_ok "$msg ${C_MUTED}($((SECONDS - start))s)${C_RESET}" || ui_error "$msg (exit $rc)"
  return $rc
}

# Progress: ui_progress <current> <total> <label>; call in a loop, ends with a newline when done
ui_progress() {
  local cur=$1 tot=$2 label=${3:-}
  local pct=$(( tot ? cur * 100 / tot : 0 ))
  if (( ! UI_ANIMATE )); then (( cur == tot || pct % 10 == 0 )) && printf '%s %d%% (%d/%d)\n' "$label" "$pct" "$cur" "$tot" >&2; return 0; fi
  local barw=$(( UI_WIDTH - ${#label} - 24 )); (( barw < 10 )) && barw=10
  local filled=$(( barw * cur / tot )) fc='#' ec='-'
  (( UI_UTF8 )) && { fc=$'\u2588'; ec=$'\u2591'; }
  printf '\r\e[K%s  %s[%s%s%s%s]%s %3d%%  %d/%d' "$label" "$C_ACCENT" \
    "$(printf "%${filled}s" '' | tr ' ' "$fc")" "$C_MUTED" "$(printf "%$((barw-filled))s" '' | tr ' ' "$ec")" "$C_ACCENT" "$C_RESET" "$pct" "$cur" "$tot" >&2
  (( cur == tot )) && printf '\n' >&2
  return 0
}

# Confirm: ui_confirm "Delete 3 runs?" ; defaults to No; honors --yes via TOOL_YES=1
ui_confirm() {
  [[ -n "${TOOL_YES:-}" ]] && return 0
  (( UI_INTERACTIVE )) || die 2 "cannot prompt: stdin is not a terminal" "pass --yes to confirm non interactively"
  printf '%s?%s %s (y/N) ' "$C_ACCENT" "$C_RESET" "$1" >&2
  local a; read -r a </dev/tty; [[ "$a" == [yY]* ]]
}

# Select: ui_select "Profile" docker singularity conda ; prints the choice to stdout
ui_select() {
  local title=$1; shift; local opts=("$@") idx=0 key
  (( UI_INTERACTIVE )) || die 2 "cannot prompt for $title: stdin is not a terminal" "pass the value as a flag"
  printf '\e[?25l' >&2
  while :; do
    printf '%s?%s %s\n' "$C_ACCENT" "$C_RESET" "$title" >&2
    for i in "${!opts[@]}"; do
      if (( i == idx )); then printf '  %s%s %s%s\n' "$C_ACCENT" "$G_PTR" "${opts[i]}" "$C_RESET" >&2
      else printf '    %s\n' "${opts[i]}" >&2; fi
    done
    IFS= read -rsn1 key </dev/tty
    [[ $key == $'\e' ]] && { read -rsn2 -t 0.05 key </dev/tty || key=esc; }
    case $key in
      '[A'|k) (( idx > 0 )) && idx=$((idx-1)) ;;
      '[B'|j) (( idx < ${#opts[@]} - 1 )) && idx=$((idx+1)) ;;
      '') printf '\e[?25h' >&2; printf '%s\n' "${opts[idx]}"; return 0 ;;
      esc|q) printf '\e[?25h' >&2; return 130 ;;
    esac
    printf '\e[%dA' $(( ${#opts[@]} + 1 )) >&2
  done
}

# Always restore the terminal
ui_cleanup() { if [[ -t 2 ]]; then printf '\e[?25h\e[0m' >&2; fi; }
trap ui_cleanup EXIT

ui_init
```

## Argument parsing

Hand rolled `while` loop with `case`; `getopts` cannot do long options. Pattern:

```bash
usage() {
  cat <<EOF
$C_BOLD${0##*/}$C_RESET - run the AMP pipeline

${C_BOLD}Usage:$C_RESET
  ${0##*/} run <samples.tsv> [--profile <name>] [--dry-run]
  ${0##*/} status [--json]

${C_BOLD}Examples:$C_RESET
  ${0##*/} run samples.tsv --profile docker
  ${0##*/} status --json | jq .state

${C_BOLD}Options:$C_RESET
  -p, --profile <name>   Execution profile (default: docker)
  -y, --yes              Skip confirmations
  -q, --quiet            Errors only
      --json             Machine readable output
      --color <when>     auto, always, never
  -h, --help             Show this help
  -V, --version          Show version
EOF
}

PROFILE=${TOOL_PROFILE:-docker}; JSON=0; DRY=0
while (( $# )); do
  case $1 in
    -p|--profile) [[ $# -ge 2 ]] || die 2 "--profile needs a value"; PROFILE=$2; shift 2 ;;
    --profile=*) PROFILE=${1#*=}; shift ;;
    -y|--yes) TOOL_YES=1; shift ;;
    -q|--quiet) exec 2>/dev/null; shift ;;
    --json) JSON=1; shift ;;
    --dry-run) DRY=1; shift ;;
    --color) TOOL_COLOR=$2; shift 2; ui_init ;;
    -h|--help) usage; exit 0 ;;
    -V|--version) echo "${0##*/} 1.4.0"; exit 0 ;;
    --) shift; break ;;
    -*) die 2 "unknown option: $1" "run ${0##*/} --help" ;;
    *) break ;;
  esac
done
```

Note that `--quiet` redirecting stderr to `/dev/null` is the simplest correct implementation: errors should then go through `die`, which must write to the original stderr. Save it first with `exec 3>&2` and have `ui_error` write to fd 3.

## JSON output

Without `jq`, emit JSON by hand only for flat objects, escaping strings with a helper. For anything nested, require `jq` and build with `jq -n --arg`:

```bash
jq -n --arg state "$STATE" --argjson n "$COUNT" '{state: $state, samples: $n}'
```

## Tables

`column -t -s $'\t'` on a TTY; raw tab separated when piped:

```bash
emit_rows | if [[ -t 1 ]]; then column -t -s $'\t'; else cat; fi
```

Header in bold: print it separately before piping the rows.

## Full screen and interactive

Bash is the wrong tool for shape 4. For a quick interactive pick, shell out to `fzf` (fuzzy select), `gum` (Charm's prompt, spin, choose, confirm, style commands) or `dialog`/`whiptail`. Detect availability and fall back to `ui_select` above. Example with gum, with fallback:

```bash
pick() { if command -v gum >/dev/null; then gum choose "$@"; else ui_select "Choose" "$@"; fi; }
```

## Robustness checklist for shell

- `set -euo pipefail`, `IFS=$'\n\t'` when iterating over lines.
- Quote every expansion. Use arrays for argument lists.
- `mktemp -d` with a cleanup trap for temporary files.
- `command -v` to check dependencies at start; report all missing ones in one error.
- `shellcheck` clean. Run it before delivering.
- Exit codes propagated from the last real command; use `die` for the tool's own errors.
- Read from `/dev/tty` for prompts so `tool < input.txt` still prompts on the terminal when interactive.
- Long lines through `fold -s -w "$UI_WIDTH"` for help and messages when the width is known.

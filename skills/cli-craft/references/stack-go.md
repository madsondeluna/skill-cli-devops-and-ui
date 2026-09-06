# Go (1.22+)

Choose for single static binaries, fast startup, and the Charm ecosystem, which is the most complete terminal UI toolkit in any language. Crush (Charm's agent) and lazygit are the references.

| Shape | Libraries |
|---|---|
| 1, 2 | `spf13/cobra` (commands, help, completions), `charmbracelet/lipgloss` v2 (styles, tables, trees, layout), `charmbracelet/huh` (forms and prompts), `charmbracelet/log` (leveled logging), `muesli/termenv` (detection), `mattn/go-isatty`, `schollz/progressbar/v3` or a Bubbles progress model driven outside Bubble Tea |
| 3, 4 | `charmbracelet/bubbletea` v2 (Elm architecture runtime), `charmbracelet/bubbles` v2 (text input, text area, list, table, viewport, spinner, progress, paginator, help, key), `charmbracelet/glamour` (markdown), `charmbracelet/bubblezone` (mouse hit zones), `alecthomas/chroma` (syntax highlighting) |

Alternatives: `urfave/cli` v3 instead of Cobra when a lighter dependency is wanted; `rivo/tview` on `tcell` for a widget toolkit closer to curses; `gum` as a shell facing binary that exposes huh and lipgloss to scripts.

Charm v2 (2025 to 2026) matters: Bubble Tea v2 returns `tea.View` from `View()` with fields for alt screen, window title and mouse mode, emits synchronized output, supports focus reporting and native progress reporting, and Lip Gloss v2 removed the global renderer in favor of explicit output detection (`lipgloss.Writer`, `colorprofile`). Read the v2 docs for the exact API; do not mix v1 and v2 imports.

## Output package (`internal/ui`)

```go
package ui

import (
	"fmt"
	"io"
	"os"
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/colorprofile"
	"github.com/mattn/go-isatty"
)

// Stream wraps a writer with a resolved color profile so every write degrades correctly.
type Stream struct {
	W       io.Writer
	Profile colorprofile.Profile
	TTY     bool
	Width   int
}

var Err, Out *Stream

func Init(colorFlag string) {
	Err = newStream(os.Stderr, colorFlag)
	Out = newStream(os.Stdout, colorFlag)
}

func newStream(f *os.File, colorFlag string) *Stream {
	tty := isatty.IsTerminal(f.Fd()) || isatty.IsCygwinTerminal(f.Fd())
	p := colorprofile.Detect(f, os.Environ()) // honors NO_COLOR, FORCE_COLOR, TERM, COLORTERM, CI
	switch colorFlag {
	case "never":
		p = colorprofile.NoTTY
	case "always":
		if p < colorprofile.ANSI {
			p = colorprofile.ANSI
		}
	}
	w := 80
	if tty {
		if cw, _, err := term.GetSize(int(f.Fd())); err == nil && cw > 0 {
			w = cw
		}
	}
	return &Stream{W: &colorprofile.Writer{Forward: f, Profile: p}, Profile: p, TTY: tty, Width: w}
}

var (
	// Semantic roles. Lip Gloss downsamples truecolor to the stream profile automatically.
	Muted   = lipgloss.NewStyle().Foreground(lipgloss.Color("#8B95A9"))
	Accent  = lipgloss.NewStyle().Foreground(lipgloss.Color("#6FA3FF"))
	Accent2 = lipgloss.NewStyle().Foreground(lipgloss.Color("#B49CFF"))
	Ok      = lipgloss.NewStyle().Foreground(lipgloss.Color("#6EE39C"))
	Warn    = lipgloss.NewStyle().Foreground(lipgloss.Color("#F2C56B"))
	ErrS    = lipgloss.NewStyle().Foreground(lipgloss.Color("#FF7B8E"))
	Info    = lipgloss.NewStyle().Foreground(lipgloss.Color("#7CD5FF"))
	Border  = lipgloss.Color("#3A4258")
	Panel   = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(Border).Padding(0, 1)
)

var utf8 = os.Getenv("TOOL_ASCII") == "" && strings.Contains(strings.ToLower(os.Getenv("LANG")+os.Getenv("LC_ALL")+os.Getenv("LC_CTYPE")), "utf-8")

func glyph(u, a string) string {
	if utf8 {
		return u
	}
	return a
}

var (
	GOk   = glyph("\u2713", "ok")
	GErr  = glyph("\u2717", "x")
	GInfo = glyph("\u25cf", "*")
	GPtr  = glyph("\u276f", ">")
)

func Okf(format string, a ...any)   { fmt.Fprintln(Err.W, Ok.Render(GOk)+" "+fmt.Sprintf(format, a...)) }
func Infof(format string, a ...any) { fmt.Fprintln(Err.W, Info.Render(GInfo)+" "+fmt.Sprintf(format, a...)) }
func Warnf(format string, a ...any) { fmt.Fprintln(Err.W, Warn.Render("warning:")+" "+fmt.Sprintf(format, a...)) }
func Errorf(hint string, format string, a ...any) {
	fmt.Fprintln(Err.W, ErrS.Render("error:")+" "+fmt.Sprintf(format, a...))
	if hint != "" {
		fmt.Fprintln(Err.W, "  "+Muted.Render("hint:")+" "+hint)
	}
}

func Animate() bool {
	return Err.TTY && os.Getenv("CI") == "" && os.Getenv("TOOL_NO_ANIMATION") == "" && os.Getenv("TERM") != "dumb"
}

func Interactive() bool {
	return isatty.IsTerminal(os.Stdin.Fd()) && Err.TTY && os.Getenv("CI") == ""
}
```

## Cobra commands

```go
var rootCmd = &cobra.Command{
	Use:   "tool",
	Short: "Run and inspect AMP pipelines",
	Example: `  tool run samples.tsv --profile docker
  tool status --json | jq .state`,
	SilenceUsage:  true, // usage errors print one line plus a hint, not the full help
	SilenceErrors: true, // we print errors ourselves through ui
	PersistentPreRun: func(cmd *cobra.Command, _ []string) {
		c, _ := cmd.Flags().GetString("color")
		ui.Init(c)
	},
}

func init() {
	rootCmd.PersistentFlags().String("color", "auto", "auto, always, never")
	rootCmd.PersistentFlags().BoolP("quiet", "q", false, "errors only")
	rootCmd.PersistentFlags().CountP("verbose", "v", "more output")
	rootCmd.SetErr(os.Stderr)
	rootCmd.SetOut(os.Stdout)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		var ue *UsageError
		if errors.As(err, &ue) {
			ui.Errorf("run tool --help", "%s", err)
			os.Exit(2)
		}
		ui.Errorf("", "%s", err)
		os.Exit(1)
	}
}
```

Flags before env before config: bind with `viper` or a small loader that applies `TOOL_*` env when the flag was not `Changed()`. Shell completions come free with `cobra` (`tool completion zsh`).

## Spinner and progress outside Bubble Tea (shape 2)

Bubbles' spinner and progress are Bubble Tea models; for a plain command, drive them with a small `tea.Program` in inline mode (no alt screen) that quits when the work is done, or use `schollz/progressbar/v3` with `progressbar.OptionSetWriter(os.Stderr)` and `OptionSetVisibility(ui.Animate())`. Print a final summary line after either so logs have the completion.

Huh gives forms and confirmations that degrade properly:

```go
if !yes {
	if !ui.Interactive() {
		ui.Errorf("pass --yes", "cannot prompt: stdin is not a terminal")
		os.Exit(2)
	}
	var ok bool
	huh.NewConfirm().Title(fmt.Sprintf("Run %d samples with %s?", n, profile)).Affirmative("Yes").Negative("No").Value(&ok).Run()
	if !ok {
		os.Exit(130)
	}
}
```

## Bubble Tea v2 for shapes 3 and 4

The Elm architecture: `Init() tea.Cmd`, `Update(msg tea.Msg) (tea.Model, tea.Cmd)`, `View() tea.View`. State lives in the model, side effects are `tea.Cmd` functions that return messages, rendering is pure.

```go
type model struct {
	width, height int
	list      list.Model
	logs      viewport.Model
	spinner   spinner.Model
	keys      keymap
	help      help.Model
	focused   pane
	loading   bool
}

type keymap struct {
	Up, Down, Tab, Filter, Refresh, Help, Quit key.Binding
}

func newKeymap() keymap {
	return keymap{
		Up:      key.NewBinding(key.WithKeys("k", "up"), key.WithHelp("k/up", "up")),
		Down:    key.NewBinding(key.WithKeys("j", "down"), key.WithHelp("j/down", "down")),
		Tab:     key.NewBinding(key.WithKeys("tab"), key.WithHelp("tab", "switch pane")),
		Filter:  key.NewBinding(key.WithKeys("/"), key.WithHelp("/", "filter")),
		Refresh: key.NewBinding(key.WithKeys("r", "ctrl+r"), key.WithHelp("r", "refresh")),
		Help:    key.NewBinding(key.WithKeys("?"), key.WithHelp("?", "help")),
		Quit:    key.NewBinding(key.WithKeys("q", "ctrl+c"), key.WithHelp("q", "quit")),
	}
}

func (m model) Init() tea.Cmd { return tea.Batch(m.spinner.Tick, loadRuns) }

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width, m.height = msg.Width, msg.Height
		m.list.SetSize(m.width*2/3, m.height-3)
		m.logs.Width, m.logs.Height = m.width-m.width*2/3-2, m.height-3
	case tea.KeyPressMsg:
		if m.list.FilterState() == list.Filtering { break } // inputs capture keys
		switch {
		case key.Matches(msg, m.keys.Quit):
			return m, tea.Quit
		case key.Matches(msg, m.keys.Tab):
			m.focused = (m.focused + 1) % 2
		case key.Matches(msg, m.keys.Refresh):
			m.loading = true
			return m, loadRuns
		}
	case tea.MouseWheelMsg:
		// scroll the pane under the pointer, not the focused one
		if zone.Get("logs").InBounds(msg) { m.logs, _ = m.logs.Update(msg) }
	case runsLoadedMsg:
		m.loading = false
		m.list.SetItems(msg.items)
	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	}
	var cmd tea.Cmd
	if m.focused == paneList { m.list, cmd = m.list.Update(msg) } else { m.logs, cmd = m.logs.Update(msg) }
	return m, cmd
}

func (m model) View() tea.View {
	if m.width < 60 || m.height < 16 {
		return tea.NewView("terminal too small (need 60x16)")
	}
	left := paneStyle(m.focused == paneList).Render(m.list.View())
	right := paneStyle(m.focused == paneLogs).Render(zone.Mark("logs", m.logs.View()))
	status := ""
	if m.loading { status = m.spinner.View() + " refreshing" }
	body := lipgloss.JoinHorizontal(lipgloss.Top, left, right)
	footer := m.help.ShortHelpView([]key.Binding{m.keys.Up, m.keys.Down, m.keys.Tab, m.keys.Filter, m.keys.Quit}) + "  " + ui.Muted.Render(status)
	v := tea.NewView(lipgloss.JoinVertical(lipgloss.Left, body, footer))
	v.AltScreen = true
	v.MouseMode = tea.MouseModeCellMotion
	v.WindowTitle = "tool"
	return zone.Scan(v)
}

func main() {
	zone.NewGlobal()
	p := tea.NewProgram(newModel(), tea.WithReportFocus())
	if _, err := p.Run(); err != nil {
		ui.Errorf("", "%s", err)
		os.Exit(1)
	}
}
```

Rules specific to Bubble Tea:

- Never block in `Update`. Network and subprocess work go in a `tea.Cmd`; long streams use a channel and a command that waits for the next item (`func() tea.Msg { return <-ch }`), re issued after each message.
- `tea.Println` and `tea.Printf` write above the live view in inline mode; this is how a shape 3 transcript is frozen. Use `tea.WithoutSignalHandler` only if you install your own Ctrl+C handling.
- Focus reporting (`tea.WithReportFocus`) plus `tea.FocusMsg` and `tea.BlurMsg`: stop the spinner tick on blur.
- Bracketed paste arrives as `tea.PasteMsg`; route it to the focused text input untouched.
- `bubblezone` for mouse hit testing; wrap regions with `zone.Mark` and check `InBounds` in `Update`.
- Snapshot tests with `charmbracelet/x/exp/teatest`: send `tea.WindowSizeMsg{Width: 80, Height: 24}`, then keys, then compare `FinalOutput`.
- Rendering markdown: `glamour.NewTermRenderer(glamour.WithAutoStyle(), glamour.WithWordWrap(width))`. Note the OSC 11 background query in `WithAutoStyle` can hang a few seconds on terminals that do not answer; prefer an explicit style from the theme file and only query with a timeout.

## Packaging

`go build -ldflags "-s -w -X main.version=1.4.0"`, `goreleaser` for multi platform releases, Homebrew tap and `go install` instructions in the README. Startup is under 10 ms; do not add init time work.

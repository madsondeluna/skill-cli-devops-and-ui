# Rust (stable, edition 2021 or 2024)

Choose when the tool processes large data, must be fast and correct, or ships as a dependency free binary. Ripgrep, bat, delta, eza, starship and yazi are the references for shapes 1 and 2; yazi, gitui and bottom for shape 4.

| Shape | Crates |
|---|---|
| 1, 2 | `clap` v4 with `derive` (arguments, help, `clap_complete`), `anstream` + `anstyle` or `owo-colors` (color with detection), `indicatif` (spinners, progress, multi progress), `console` (terminal features, `Term::stderr`), `comfy-table` or `tabled` (tables), `dialoguer` or `inquire` (prompts), `unicode-width` (width math), `supports-color`, `supports-hyperlinks`, `colorgrad` (gradients) |
| 3 | `clap` for entry, `ratatui` inline viewport (`Viewport::Inline(n)`) plus `insert_before` for the transcript, `tui-textarea` for input, `tui-markdown` or `termimad` for markdown |
| 4 | `ratatui` with `crossterm` backend, `tui-widgets` ecosystem (`tui-input`, `tui-tree-widget`, `tui-logger`, `throbber-widgets-tui`), `tokio` for async I/O |

Rust specifics worth exploiting: `clap` generates help, completions and man pages from one derive; `anstream::println!` strips ANSI automatically when the stream is not a TTY, which makes the stdout and stderr rule almost free; `indicatif` hides bars on non TTY by default and supports `MultiProgress` with a single writer; `ratatui` 0.30 supports synchronized output through crossterm's `BeginSynchronizedUpdate`.

## Output module (`ui.rs`)

```rust
//! Terminal output. Decoration to stderr, results to stdout.
use anstream::{eprintln, AutoStream, ColorChoice};
use anstyle::{AnsiColor, Color, RgbColor, Style};
use std::io::IsTerminal;
use std::sync::OnceLock;

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level { None, Basic, Ansi256, TrueColor }

pub struct Caps { pub err_level: Level, pub out_level: Level, pub utf8: bool, pub animate: bool, pub interactive: bool, pub width: usize }

static CAPS: OnceLock<Caps> = OnceLock::new();

pub fn init(color: &str) -> &'static Caps {
    CAPS.get_or_init(|| {
        let choice = match color { "never" => ColorChoice::Never, "always" => ColorChoice::Always, _ => ColorChoice::Auto };
        anstream::ColorChoice::write_global(choice); // anstream then honors NO_COLOR, FORCE_COLOR, TERM, CI
        let lvl = |stream: bool| -> Level {
            if choice == ColorChoice::Never || std::env::var_os("NO_COLOR").is_some() { return Level::None; }
            if choice == ColorChoice::Always { return Level::Basic.max(env_force()); }
            if !stream { return Level::None; }
            match supports_color::on_cached(supports_color::Stream::Stderr) {
                Some(s) if s.has_16m => Level::TrueColor,
                Some(s) if s.has_256 => Level::Ansi256,
                Some(_) => Level::Basic,
                None => Level::None,
            }
        };
        let err_tty = std::io::stderr().is_terminal();
        let lang = std::env::var("LC_ALL").or_else(|_| std::env::var("LC_CTYPE")).or_else(|_| std::env::var("LANG")).unwrap_or_default();
        Caps {
            err_level: lvl(err_tty),
            out_level: lvl(std::io::stdout().is_terminal()),
            utf8: std::env::var_os("TOOL_ASCII").is_none() && lang.to_ascii_lowercase().replace('-', "").contains("utf8"),
            animate: err_tty && std::env::var_os("CI").is_none() && std::env::var_os("TOOL_NO_ANIMATION").is_none() && std::env::var("TERM").as_deref() != Ok("dumb"),
            interactive: std::io::stdin().is_terminal() && err_tty && std::env::var_os("CI").is_none(),
            width: console::Term::stderr().size().1 as usize,
        }
    })
}

fn env_force() -> Level {
    match std::env::var("FORCE_COLOR").as_deref() { Ok("3") => Level::TrueColor, Ok("2") => Level::Ansi256, _ => Level::Basic }
}

// Semantic roles. anstyle downsampling: on Basic terminals use the AnsiColor variant.
pub fn role(name: &str) -> Style {
    let caps = CAPS.get().expect("ui::init first");
    let tc = caps.err_level >= Level::Ansi256;
    let pick = |rgb: (u8, u8, u8), basic: AnsiColor| -> Color {
        if tc { Color::Rgb(RgbColor(rgb.0, rgb.1, rgb.2)) } else { Color::Ansi(basic) }
    };
    let fg = match name {
        "muted" => pick((138, 143, 152), AnsiColor::BrightBlack),
        "accent" => pick((122, 162, 247), AnsiColor::Blue),
        "accent2" => pick((187, 154, 247), AnsiColor::Magenta),
        "ok" => pick((158, 206, 106), AnsiColor::Green),
        "warn" => pick((224, 175, 104), AnsiColor::Yellow),
        "err" => pick((247, 118, 142), AnsiColor::Red),
        "info" => pick((125, 207, 255), AnsiColor::Cyan),
        _ => return Style::new(),
    };
    Style::new().fg_color(Some(fg))
}

pub fn glyph(u: &'static str, a: &'static str) -> &'static str { if CAPS.get().map_or(false, |c| c.utf8) { u } else { a } }

pub fn ok(msg: &str)   { let s = role("ok");   eprintln!("{s}{}{s:#} {msg}", glyph("\u{2713}", "ok")); }
pub fn info(msg: &str) { let s = role("info"); eprintln!("{s}{}{s:#} {msg}", glyph("\u{25cf}", "*")); }
pub fn warn(msg: &str) { let s = role("warn"); eprintln!("{s}warning:{s:#} {msg}"); }
pub fn error(msg: &str, hint: Option<&str>) {
    let s = role("err"); let m = role("muted");
    eprintln!("{s}error:{s:#} {msg}");
    if let Some(h) = hint { eprintln!("  {m}hint:{m:#} {h}"); }
}
```

`anstyle` styles print their reset with the `{s:#}` alternate form, which is why the format strings look that way.

## clap commands

```rust
use clap::{Parser, Subcommand, ValueEnum};

#[derive(Parser)]
#[command(name = "tool", version, about = "Run and inspect AMP pipelines",
          after_help = "Examples:\n  tool run samples.tsv --profile docker\n  tool status --json | jq .state")]
struct Cli {
    /// auto, always, never
    #[arg(long, global = true, default_value = "auto", env = "TOOL_COLOR")]
    color: String,
    /// Errors only
    #[arg(short, long, global = true)]
    quiet: bool,
    /// More output (repeatable)
    #[arg(short, long, global = true, action = clap::ArgAction::Count)]
    verbose: u8,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Execute the pipeline on a sample sheet
    Run {
        /// TSV of samples, or - for stdin
        samples: String,
        #[arg(short, long, default_value = "docker", env = "TOOL_PROFILE")]
        profile: String,
        #[arg(long)]
        dry_run: bool,
        #[arg(short, long)]
        yes: bool,
    },
    /// Show the last run
    Status {
        #[arg(long)]
        json: bool,
    },
}

fn main() {
    let cli = Cli::parse(); // usage errors exit 2 with a one line message on stderr
    let caps = ui::init(&cli.color);
    let code = match run(cli, caps) {
        Ok(()) => 0,
        Err(e) => { ui::error(&e.to_string(), e.hint()); e.exit_code() }
    };
    std::process::exit(code);
}
```

Ctrl+C: install `ctrlc::set_handler` (or tokio `signal::ctrl_c`) that restores the terminal (`console::Term::stderr().show_cursor()`, `crossterm::terminal::disable_raw_mode`, `LeaveAlternateScreen`) and exits 130. Wrap the main body so panics also run the restore (`std::panic::set_hook` that restores, then delegates to the default hook).

## Spinner and progress with indicatif

```rust
use indicatif::{ProgressBar, ProgressStyle, ProgressDrawTarget};

let target = if caps.animate { ProgressDrawTarget::stderr_with_hz(20) } else { ProgressDrawTarget::hidden() };
let pb = ProgressBar::with_draw_target(Some(rows.len() as u64), target);
pb.set_style(ProgressStyle::with_template("{spinner:.cyan} {msg:<16} [{bar:30.blue/240}] {percent:>3}%  {pos}/{len}  {elapsed_precise} < {eta_precise}")
    .unwrap().progress_chars(if caps.utf8 { "\u{2588}\u{2588}\u{2591}" } else { "##-" }));
pb.set_message("aligning");
for row in &rows { align(row)?; pb.inc(1); }
pb.finish_and_clear();
ui::ok(&format!("{} samples aligned ({:.1}s)", rows.len(), t0.elapsed().as_secs_f32()));
```

When hidden (non TTY) print a line every 10 percent yourself; `MultiProgress` for parallel tasks with `rayon` or threads, all bars owned by one `MultiProgress` so writes never interleave.

## Ratatui for shape 4

Immediate mode: each frame you build widgets from state and draw them into a `Frame`. State lives in your struct, input comes from `crossterm::event`, I/O runs on tokio tasks or threads that send messages over a channel.

```rust
use ratatui::{prelude::*, widgets::*};
use crossterm::{event::{self, Event, KeyCode, KeyModifiers, MouseEventKind, EnableMouseCapture, DisableMouseCapture, EnableBracketedPaste, DisableBracketedPaste, EnableFocusChange, DisableFocusChange}, execute, terminal::{enable_raw_mode, disable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen}};

struct App { runs: Vec<Run>, table: TableState, logs: Vec<String>, log_scroll: u16, focus: Pane, show_help: bool, areas: Areas }

fn main() -> anyhow::Result<()> {
    let mut terminal = ratatui::init(); // raw mode, alternate screen, panic hook that restores
    execute!(std::io::stdout(), EnableMouseCapture, EnableBracketedPaste, EnableFocusChange)?;
    let res = run_app(&mut terminal);
    execute!(std::io::stdout(), DisableFocusChange, DisableBracketedPaste, DisableMouseCapture)?;
    ratatui::restore();
    res
}

fn run_app(terminal: &mut DefaultTerminal) -> anyhow::Result<()> {
    let mut app = App::new();
    let (tx, rx) = std::sync::mpsc::channel();
    spawn_loader(tx.clone());
    loop {
        terminal.draw(|f| draw(f, &mut app))?;
        // Batch: drain all pending events, then one redraw
        while event::poll(std::time::Duration::from_millis(50))? {
            match event::read()? {
                Event::Key(k) if k.kind == event::KeyEventKind::Press => {
                    if k.code == KeyCode::Char('c') && k.modifiers.contains(KeyModifiers::CONTROL) { return Ok(()); }
                    match k.code {
                        KeyCode::Char('q') => return Ok(()),
                        KeyCode::Char('?') => app.show_help = !app.show_help,
                        KeyCode::Esc => app.show_help = false,
                        KeyCode::Tab => app.focus = app.focus.next(),
                        KeyCode::Char('j') | KeyCode::Down => app.down(),
                        KeyCode::Char('k') | KeyCode::Up => app.up(),
                        _ => {}
                    }
                }
                Event::Mouse(m) => match m.kind {
                    MouseEventKind::ScrollDown if app.areas.logs.contains((m.column, m.row).into()) => app.log_scroll = app.log_scroll.saturating_add(3),
                    MouseEventKind::ScrollUp if app.areas.logs.contains((m.column, m.row).into()) => app.log_scroll = app.log_scroll.saturating_sub(3),
                    MouseEventKind::Down(_) => app.click(m.column, m.row),
                    _ => {}
                },
                Event::Resize(_, _) => {}
                Event::FocusLost => app.paused = true,
                Event::FocusGained => app.paused = false,
                Event::Paste(s) => app.paste(s),
                _ => {}
            }
        }
        while let Ok(msg) = rx.try_recv() { app.apply(msg); }
    }
}

fn draw(f: &mut Frame, app: &mut App) {
    let area = f.area();
    if area.width < 60 || area.height < 16 {
        f.render_widget(Paragraph::new("terminal too small (need 60x16)").centered(), area);
        return;
    }
    let [body, footer] = Layout::vertical([Constraint::Min(1), Constraint::Length(1)]).areas(area);
    let [left, right] = Layout::horizontal([Constraint::Percentage(66), Constraint::Fill(1)]).areas(body);
    app.areas = Areas { table: left, logs: right }; // keep rects for hit testing

    let border = |focused: bool| if focused { Style::new().fg(Color::Rgb(122, 162, 247)) } else { Style::new().fg(Color::Rgb(59, 66, 97)) };
    let rows = app.runs.iter().map(|r| Row::new([r.name.clone(), r.status.clone(), r.duration.clone()])
        .style(match r.status.as_str() { "failed" => Style::new().fg(Color::Rgb(247, 118, 142)), "ok" => Style::new().fg(Color::Rgb(158, 206, 106)), _ => Style::default() }));
    let table = Table::new(rows, [Constraint::Fill(2), Constraint::Length(8), Constraint::Length(9)])
        .header(Row::new(["NAME", "STATUS", "DURATION"]).style(Style::new().bold().fg(Color::Rgb(138, 143, 152))))
        .row_highlight_style(Style::new().bg(Color::Rgb(40, 52, 87)))
        .block(Block::bordered().border_type(BorderType::Rounded).border_style(border(app.focus == Pane::Table)).title(" runs "));
    f.render_stateful_widget(table, left, &mut app.table);

    let logs = Paragraph::new(app.logs.join("\n")).wrap(Wrap { trim: false }).scroll((app.log_scroll, 0))
        .block(Block::bordered().border_type(BorderType::Rounded).border_style(border(app.focus == Pane::Logs)).title(" logs "));
    f.render_widget(logs, right);

    f.render_widget(Line::from(vec![
        Span::styled(" j/k ", Style::new().fg(Color::Rgb(122, 162, 247))), Span::raw("move  "),
        Span::styled("tab ", Style::new().fg(Color::Rgb(122, 162, 247))), Span::raw("pane  "),
        Span::styled("? ", Style::new().fg(Color::Rgb(122, 162, 247))), Span::raw("help  "),
        Span::styled("q ", Style::new().fg(Color::Rgb(122, 162, 247))), Span::raw("quit"),
    ]), footer);

    if app.show_help {
        let popup = centered_rect(50, 40, area);
        f.render_widget(Clear, popup);
        f.render_widget(Paragraph::new(HELP).block(Block::bordered().border_type(BorderType::Rounded).title(" keys ")), popup);
    }
}
```

Ratatui rules: keep `Rect`s from the last frame for mouse hit testing; never block in the event loop (loaders on threads or tokio, results over a channel); use `ratatui::init` and `ratatui::restore` (they install the panic hook); `Clear` before drawing a popup; `Layout::areas` with destructuring for readable splits; colors through a `Theme` struct so 16 color fallback is a single swap (`Color::Blue` instead of `Color::Rgb`); test with `TestBackend` and `assert_snapshot!` from `insta`.

## Packaging

`cargo build --release` with `lto = true`, `codegen-units = 1`, `strip = true` in the release profile; `cargo-dist` for releases; `clap_complete` and `clap_mangen` in `build.rs` for completions and man pages.

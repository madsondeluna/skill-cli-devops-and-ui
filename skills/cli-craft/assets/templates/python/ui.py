"""Terminal UI layer for CLIs built with cli-craft.

Copy this file into your package (for example `mytool/ui.py`). It is the only
module that knows about TTYs, colors and animation. Everything else in the
tool hands it plain data. Dependencies: Rich (required), nothing else.

Public surface:
    env            -> Env       detected once at import, never re-detected
    console, err   -> Console   stdout console (data) and stderr console (chrome)
    theme          -> dict      role name -> Rich style string
    gradient_text  -> Text      static multi-hue gradient over a string
    banner()                    ASCII art title, animated slogan, options list
    ascii_art()                 render a string in the built in 5x5 block font
    status()                    spinner with a cycling gradient glyph
    thinking()                  agent wait: pulsing glyph, rotating verb, elapsed, escape hint
    progress()                  progress bar with a cycling gradient fill
    panel()                     rounded panel, the default block grouping
    select()                    launcher: filterable list, arrows, keybinding footer
    keybar()                    persistent footer of key hints
    ok / warn / fail / info     one line status messages on stderr
    emit(data)                  data to stdout, JSON when --json or piped
    parse_args(parser)          argparse wrapper: usage errors exit 2 with a hint
    did_you_mean(word, options) nearest valid name, for unknown input
    apply_color_flag(value)     honor --color auto|always|never after parsing
    install_signal_handlers()   Ctrl-C -> restore cursor, exit 130
"""
from __future__ import annotations

import json
import locale
import math
import math
import os
import re
import signal
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, Sequence

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (MofNCompleteColumn, Progress, ProgressColumn, Task,
                           TextColumn, TimeElapsedColumn, TimeRemainingColumn)
from rich.text import Text
from rich.theme import Theme

TOOL = os.environ.get("CLI_CRAFT_TOOL_NAME", "tool").upper()

# ---------------------------------------------------------------------------
# Environment detection: one pass, one source of truth.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Env:
    stdout_tty: bool
    stderr_tty: bool
    color: bool           # any SGR at all
    depth: int            # 0, 16, 256 or 16_777_216
    animate: bool         # live redraws allowed on stderr
    interactive: bool     # prompts allowed (stdin and stderr are TTYs, not CI)
    unicode: bool         # box drawing and glyphs allowed
    width: int
    light_bg: bool        # explicit override only; default is dark


def _detect() -> Env:
    stdout_tty = sys.stdout.isatty()
    stderr_tty = sys.stderr.isatty()
    stdin_tty = sys.stdin.isatty()
    ci = bool(os.environ.get("CI"))
    term = os.environ.get("TERM", "")
    dumb = term == "dumb"
    force = os.environ.get("FORCE_COLOR")
    no_color = "NO_COLOR" in os.environ

    # Color depth: FORCE_COLOR wins, then NO_COLOR, then terminal capability.
    if force not in (None, "", "0"):
        depth = {"1": 16, "2": 256}.get(force, 16_777_216)
    elif no_color or dumb:
        depth = 0
    elif os.environ.get("COLORTERM") in ("truecolor", "24bit"):
        depth = 16_777_216
    elif "256" in term:
        depth = 256
    elif term:
        depth = 16
    else:
        depth = 0

    enc = (sys.stdout.encoding or locale.getpreferredencoding(False) or "").lower()
    unicode = ("utf" in enc) and not dumb and not os.environ.get(f"{TOOL}_ASCII")
    animate = stderr_tty and not ci and not dumb and not os.environ.get(f"{TOOL}_NO_ANIMATION")
    try:
        width = os.get_terminal_size(sys.stderr.fileno()).columns
    except OSError:
        width = int(os.environ.get("COLUMNS", "80") or 80)
    if width <= 0:
        width = 80  # a pty with no window size reports 0 columns
    return Env(
        stdout_tty=stdout_tty,
        stderr_tty=stderr_tty,
        color=depth > 0 and (stdout_tty or stderr_tty),  # capability and somewhere to show it
        depth=depth,
        animate=animate,
        interactive=stdin_tty and stderr_tty and not ci,
        unicode=unicode,
        width=min(width, 100),
        light_bg=os.environ.get(f"{TOOL}_THEME") == "light",
    )


env = _detect()

# ---------------------------------------------------------------------------
# Theme: roles -> Rich styles, tiered by color depth (see references/palette.md)
# ---------------------------------------------------------------------------

_DARK = dict(fg="#E6E9F0", muted="#8B95A9", dim="#5C6577", accent="#6FA3FF",
             accent2="#B49CFF", teal="#3DDBC7", ok="#6EE39C", warn="#F2C56B",
             err="#FF7B8E", info="#7CD5FF", border="#3A4258")
_LIGHT = dict(fg="#1B2030", muted="#5B6472", dim="#8A93A3", accent="#2358D6",
              accent2="#6B33D6", teal="#0F7A6E", ok="#1B7A3E", warn="#8A5A00",
              err="#C4283A", info="#0B6FA8", border="#CDD3DE")
_C256 = dict(fg="default", muted="color(245)", dim="color(240)", accent="color(75)",
             accent2="color(141)", teal="color(80)", ok="color(114)", warn="color(221)",
             err="color(210)", info="color(117)", border="color(238)")
_C16 = dict(fg="default", muted="bright_black", dim="bright_black", accent="blue",
            accent2="magenta", teal="cyan", ok="green", warn="yellow", err="red",
            info="cyan", border="bright_black")

GRADIENT_DARK = ["#3DDBC7", "#38BDF8", "#5B9CFF", "#8B7BFF", "#C084FC"]
GRADIENT_LIGHT = ["#0F766E", "#0284C7", "#2358D6", "#5B3FD1", "#8A3FC4"]
GRADIENT_256 = ["color(80)", "color(75)", "color(111)", "color(141)"]


def _roles() -> dict[str, str]:
    if env.depth >= 16_777_216:
        return _LIGHT if env.light_bg else _DARK
    if env.depth >= 256:
        return _C256
    return _C16


theme = _roles()
_rich_theme = Theme({k: v for k, v in theme.items()} | {
    "ok": f"bold {theme['ok']}", "err": f"bold {theme['err']}",
    "warn": f"bold {theme['warn']}", "accent": f"bold {theme['accent']}",
    "progress.percentage": theme["muted"], "progress.remaining": theme["muted"],
    "bar.complete": theme["accent"], "bar.finished": theme["ok"], "bar.pulse": theme["accent2"],
})

_common = dict(theme=_rich_theme, emoji=False, highlight=False, width=env.width,
               legacy_windows=False)


def _console(stream: Any, is_tty: bool) -> Console:
    # Rich treats force_terminal=False as "auto detect", so a non TTY stream must
    # be told explicitly that it has no color system at all.
    if is_tty and env.color:
        cs = {16: "standard", 256: "256"}.get(env.depth, "truecolor")
        return Console(file=stream, force_terminal=True, color_system=cs, **_common)
    return Console(file=stream, force_terminal=False, no_color=True, color_system=None, **_common)


console = _console(sys.stdout, env.stdout_tty)
err = _console(sys.stderr, env.stderr_tty)

# Glyphs with ASCII fallback.
G = {
    "ok": "\u2713" if env.unicode else "ok",
    "err": "\u2717" if env.unicode else "x",
    "warn": "\u25b2" if env.unicode else "!",
    "info": "\u25cf" if env.unicode else "*",
    "pointer": "\u276f" if env.unicode else ">",
    "rule": "\u2500" if env.unicode else "-",
}

# ---------------------------------------------------------------------------
# Gradient: OKLCH interpolation so blue to violet does not go grey.
# ---------------------------------------------------------------------------


def _hex_to_oklab(h: str) -> tuple[float, float, float]:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    l = 0.4122214708 * lin[0] + 0.5363325363 * lin[1] + 0.0514459929 * lin[2]
    m = 0.2119034982 * lin[0] + 0.6806995451 * lin[1] + 0.1073969566 * lin[2]
    s = 0.0883024619 * lin[0] + 0.2817188376 * lin[1] + 0.6299787005 * lin[2]
    l, m, s = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _oklab_to_hex(L: float, a: float, b: float) -> str:
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
           -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
           -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)
    out = []
    for c in lin:
        c = max(0.0, min(1.0, c))
        c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        out.append(int(round(c * 255)))
    return "#{:02X}{:02X}{:02X}".format(*out)


def _stops() -> list[str]:
    return GRADIENT_LIGHT if env.light_bg else GRADIENT_DARK


def _sample(t: float, stops: Sequence[str]) -> str:
    # t in [0, 1); wraps so an animated phase loops seamlessly.
    t = t % 1.0
    n = len(stops)
    pos = t * n
    i = int(pos) % n
    f = pos - int(pos)
    a, b = _hex_to_oklab(stops[i]), _hex_to_oklab(stops[(i + 1) % n])
    return _oklab_to_hex(*(x + (y - x) * f for x, y in zip(a, b)))


def _lighten(hex_colour: str, amount: float) -> str:
    """Raise lightness in OKLCH, easing chroma down so the core reads as a
    highlight rather than a different hue. `amount` is 0 to 1."""
    if amount <= 0:
        return hex_colour
    L, a, b = _hex_to_oklab(hex_colour)
    L = min(1.0, L + 0.42 * amount)
    fade = 1 - 0.45 * amount
    return _oklab_to_hex(L, a * fade, b * fade)


def _shimmer_at(x: float, centre: float, width: float = 0.16) -> float:
    """Intensity of the sweeping highlight at position x, both in 0 to 1.

    A gaussian band: a hard edge reads as a rectangle sliding over the text,
    while a soft one reads as light moving across a surface, which is the
    difference between an animation that looks cheap and one that does not.
    """
    d = abs(x - centre)
    d = min(d, 1 - d)  # wrap, so the sweep can loop without a seam
    return math.exp(-(d * d) / (2 * width * width))


def gradient_text(s: str, phase: float = 0.0, style: str = "bold") -> Text:
    """Return `s` with a horizontal gradient; falls back per color depth."""
    if env.depth < 256:
        return Text(s, style=f"{style} {theme['accent']}")
    text = Text()
    if env.depth < 16_777_216:
        stops = GRADIENT_256
        for i, ch in enumerate(s):
            text.append(ch, style=f"{style} {stops[(i * len(stops) // max(1, len(s))) % len(stops)]}")
        return text
    for i, ch in enumerate(s):
        text.append(ch, style=f"{style} {_sample(i / max(1, len(s)) * 0.6 + phase, _stops())}")
    return text


def gradient_rule(width: int | None = None, phase: float = 0.0) -> Text:
    return gradient_text(G["rule"] * (width or env.width), phase=phase, style="")


# ---------------------------------------------------------------------------
# Chrome: banner, status, progress, messages (all on stderr)
# ---------------------------------------------------------------------------

_SYNC_ON, _SYNC_OFF = "\x1b[?2026h", "\x1b[?2026l"


_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font-shadow.json")
_FALLBACK_HEIGHT = 5
_FALLBACK: dict[str, list[str]] = {
    "A": ["01110", "10001", "11111", "10001", "10001"], "B": ["11110", "10001", "11110", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "01111"], "D": ["11110", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "11110", "10000", "11111"], "F": ["11111", "10000", "11110", "10000", "10000"],
    "G": ["01111", "10000", "10011", "10001", "01111"], "H": ["10001", "10001", "11111", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "11111"], "J": ["00111", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "11100", "10010", "10001"], "L": ["10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001"], "N": ["10001", "11001", "10101", "10011", "10001"],
    "O": ["01110", "10001", "10001", "10001", "01110"], "P": ["11110", "10001", "11110", "10000", "10000"],
    "Q": ["01110", "10001", "10101", "10010", "01101"], "R": ["11110", "10001", "11110", "10010", "10001"],
    "S": ["01111", "10000", "01110", "00001", "11110"], "T": ["11111", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "01110"], "V": ["10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10101", "11011", "10001"], "X": ["10001", "01010", "00100", "01010", "10001"],
    "Y": ["10001", "01010", "00100", "00100", "00100"], "Z": ["11111", "00010", "00100", "01000", "11111"],
    "0": ["01110", "10011", "10101", "11001", "01110"], "1": ["00100", "01100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00110", "01000", "11111"], "3": ["11110", "00001", "01110", "00001", "11110"],
    "4": ["00010", "00110", "01010", "11111", "00010"], "5": ["11111", "10000", "11110", "00001", "11110"],
    "6": ["01110", "10000", "11110", "10001", "01110"], "7": ["11111", "00010", "00100", "01000", "01000"],
    "8": ["01110", "10001", "01110", "10001", "01110"], "9": ["01110", "10001", "01111", "00001", "01110"],
    "-": ["00000", "00000", "01110", "00000", "00000"], " ": ["00000", "00000", "00000", "00000", "00000"],
}
_shadow_font: dict[str, Any] | None = None


def _load_font() -> dict[str, Any] | None:
    """Load the ANSI Shadow glyph table shipped next to this module.

    The table was generated once from the public figlet font, so there is no
    runtime dependency. When the file is missing (someone vendored ui.py alone)
    the blocky 5x5 fallback keeps the banner working rather than failing.
    """
    global _shadow_font
    if _shadow_font is None:
        try:
            with open(_FONT_PATH, encoding="utf-8") as fh:
                _shadow_font = json.load(fh)
        except OSError:
            _shadow_font = {}
    return _shadow_font or None


def ascii_art(word: str) -> list[str]:
    """Render `word` as terminal art, one string per row.

    Prefers the shadow font; falls back to the 5x5 block font when the shadow
    art would not fit the width, and to a single upper case line when even that
    would not, or when the locale is not UTF-8. Callers never branch.
    """
    word = word.upper()
    if not env.unicode:
        return [word]

    font = _load_font()
    if font:
        glyphs = font["glyphs"]
        width = sum(len(glyphs.get(ch, glyphs[" "])[0]) for ch in word)
        if width <= env.width:
            rows = [""] * font["height"]
            for ch in word:
                g = glyphs.get(ch, glyphs[" "])
                for i in range(font["height"]):
                    rows[i] += g[i]
            return [r.rstrip() for r in rows]

    if len(word) * 6 <= env.width:
        rows = [""] * _FALLBACK_HEIGHT
        for ch in word:
            g = _FALLBACK.get(ch, _FALLBACK[" "])
            for i in range(_FALLBACK_HEIGHT):
                rows[i] += "".join("\u2588" if b == "1" else " " for b in g[i]) + " "
        return [r.rstrip() for r in rows]
    return [word]


def _gradient_block(lines: Sequence[str], phase: float, sweep: float | None = None,
                    reveal: float = 1.0) -> Text:
    """Colour a block with one gradient across its width.

    `sweep` is the position of the highlight band, 0 to 1, or None for none.
    `reveal` wipes the block in from the left: columns beyond it stay blank, so
    the art materialises rather than appearing all at once.
    """
    width = max((len(l) for l in lines), default=1)
    cut = int(width * reveal)
    out = Text()
    for i, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch == " " or x >= cut:
                out.append(" ")
                continue
            if env.depth < 16_777_216:
                out.append(ch, style=theme["accent"])
                continue
            base = _sample(x / width * 0.6 + phase, _stops())
            if sweep is not None:
                base = _lighten(base, _shimmer_at(x / width, sweep))
            out.append(ch, style=base)
        if i < len(lines) - 1:
            out.append("\n")
    return out


def banner(title: str, slogan: str = "", options: Sequence[tuple[str, str]] = (),
           reveal_ms: int = 1200, fps: int = 30) -> None:
    """Animated banner: the title wipes in, a highlight sweeps across it twice,
    then it settles into the static gradient. Slogan and options follow.

    Everything goes to stderr, so a banner never contaminates piped data. With
    animation off a single static frame is printed; with no TTY, nothing.
    """
    if not env.stderr_tty:
        return
    art = ascii_art(title)
    animate = env.animate and env.depth >= 16_777_216
    step = 6 / 360

    if not animate:
        err.print(_gradient_block(art, 0.0))
    else:
        frames = max(6, int(reveal_ms / 1000 * fps))
        sys.stderr.write("\x1b[?25l")
        try:
            for k in range(frames):
                t = k / (frames - 1)
                # First third wipes the art in; the sweep then crosses twice and
                # leaves at the right edge, so the last frame is the clean one.
                reveal = min(1.0, t / 0.35)
                sweep = None if t < 0.3 else ((t - 0.3) / 0.7) * 2.0 % 1.0
                sys.stderr.write(_SYNC_ON)
                if k:
                    sys.stderr.write(f"\x1b[{len(art)}A")
                err.print(_gradient_block(art, k * step, sweep=sweep, reveal=reveal))
                sys.stderr.write(_SYNC_OFF)
                sys.stderr.flush()
                time.sleep(1 / fps)
            sys.stderr.write(f"\x1b[{len(art)}A")
            err.print(_gradient_block(art, frames * step))
        finally:
            sys.stderr.write("\x1b[?25h")
            sys.stderr.flush()

    if slogan:
        err.print(Text(slogan, style="muted"))
    if options:
        err.print()
        pad = max(len(label) for label, _ in options)
        for label, description in options:
            err.print(f"  [accent]{label:<{pad}}[/]  [muted]{description}[/]")
    err.print(gradient_rule())


class _GradientSpinner(ProgressColumn):
    """Spinner glyph whose color cycles through the identity gradient.

    The phase is derived from wall clock time, so every redraw advances it and
    the cycle is continuous while the region is live. It stops when the task
    finishes because Rich stops refreshing.
    """

    FRAMES = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f" if env.unicode else "-\\|/"

    def render(self, task: Task) -> Text:
        if task.finished:
            return Text(G["ok"], style="ok")
        t = time.monotonic()
        frame = self.FRAMES[int(t * 12) % len(self.FRAMES)]
        if env.depth < 16_777_216:
            return Text(frame, style=theme["accent"])
        return Text(frame, style=_sample(t * 0.35, _stops()))


class _GradientBar(ProgressColumn):
    """Progress bar whose filled part carries the gradient, cycling in place.

    Sub cell precision: the eighth block characters let the bar advance in
    eighths of a column instead of jumping a whole cell, which is what makes a
    slow bar look continuous rather than stuttering. On a non UTF-8 terminal
    the partial cell is dropped and the bar quantises to whole cells.
    """

    EIGHTHS = "\u258f\u258e\u258d\u258c\u258b\u258a\u2589"  # 1/8 through 7/8

    def __init__(self, width: int | None = None) -> None:
        super().__init__()
        self.width = width

    def render(self, task: Task) -> Text:
        width = self.width or max(10, min(40, env.width - 45))
        fill_glyph = "\u2588" if env.unicode else "#"
        empty_glyph = "\u2591" if env.unicode else "-"
        exact = width * (task.percentage or 0) / 100
        full = int(exact)
        frac = exact - full
        phase = time.monotonic() * 0.25

        def tint(x: int) -> str:
            return (_sample(x / width * 0.6 + phase, _stops())
                    if env.depth >= 16_777_216 else theme["accent"])

        bar = Text()
        for x in range(full):
            bar.append(fill_glyph, style=tint(x))
        remaining = width - full
        if env.unicode and remaining > 0 and frac > 0.125 and not task.finished:
            bar.append(self.EIGHTHS[min(6, int(frac * 8) - 1)], style=tint(full))
            remaining -= 1
        if remaining > 0:
            bar.append(empty_glyph * remaining, style=theme["border"])
        return bar


@contextmanager
def status(message: str) -> Iterator[None]:
    """Cycling gradient spinner while a block runs; a plain line when off."""
    if not env.animate:
        err.print(f"{G['pointer']} {message}", style="muted")
        yield
        return
    prog = Progress(_GradientSpinner(), TextColumn("[fg]{task.description}"),
                    console=err, transient=True, refresh_per_second=15)
    with prog:
        prog.add_task(message, total=None)
        yield
    err.print(f"[ok]{G['ok']}[/] {message}")


AGENT_VERBS = ("Thinking", "Reasoning", "Reading", "Planning", "Checking",
               "Composing", "Considering", "Working")


class _ThinkingLine:
    """The agent wait indicator: pulsing glyph, verb, elapsed, escape hint.

    Every part answers a question the user is actually asking while they wait.
    The glyph says the process is alive, the verb says what kind of work is
    happening, the elapsed time says whether it is stuck, the counter says
    whether it is producing anything, and the hint says how to get out. Drop
    any one of them and the wait becomes anxious.
    """

    PULSE = "\u25cb\u25d4\u25d1\u25d5\u25cf\u25d5\u25d1\u25d4" if env.unicode else ".oOo"

    def __init__(self, verbs: Sequence[str] = AGENT_VERBS, verb_seconds: float = 4.0,
                 counter: Any = None, interrupt_hint: str = "esc to interrupt") -> None:
        self.start = time.monotonic()
        self.verbs = list(verbs) or list(AGENT_VERBS)
        self.verb_seconds = verb_seconds
        self.counter = counter  # callable returning a short string, e.g. "1.2k tokens"
        self.interrupt_hint = interrupt_hint

    def render(self) -> Text:
        now = time.monotonic()
        elapsed = now - self.start
        glyph = self.PULSE[int(now * 8) % len(self.PULSE)]
        verb = self.verbs[int(elapsed / self.verb_seconds) % len(self.verbs)]

        line = Text()
        if env.depth >= 16_777_216:
            line.append(glyph + " ", style=_sample(now * 0.35, _stops()))
            # The verb carries the gradient too, sampled per character with a
            # moving phase: that is the shimmer, and it stops with the region.
            for i, ch in enumerate(verb):
                line.append(ch, style="bold " + _sample(i / max(1, len(verb)) * 0.4 + now * 0.35, _stops()))
        else:
            line.append(glyph + " ", style=theme["accent"])
            line.append(verb, style="bold " + theme["accent"])

        meta = [f"{elapsed:.0f}s"]
        if self.counter:
            try:
                extra = self.counter()
            except Exception:
                extra = None
            if extra:
                meta.append(str(extra))
        if self.interrupt_hint:
            meta.append(self.interrupt_hint)
        line.append("  (" + "  ".join(meta) + ")", style=theme["muted"])
        return line


@contextmanager
def thinking(verbs: Sequence[str] = AGENT_VERBS, counter: Any = None,
             done: str | None = None, interrupt_hint: str = "esc to interrupt") -> Iterator[None]:
    """Agent style wait indicator, for work with no measurable progress.

    Use when the tool is waiting on a model, a network call or anything whose
    completion cannot be counted; use `progress` whenever a total exists. On a
    non interactive stderr it prints one line at the start and one at the end,
    so logs and CI stay readable.
    """
    if not env.animate:
        err.print(f"{G['pointer']} {verbs[0].lower()}", style="muted")
        yield
        if done:
            err.print(f"[ok]{G['ok']}[/] {done}")
        return

    from rich.live import Live

    line = _ThinkingLine(verbs, counter=counter, interrupt_hint=interrupt_hint)
    import threading

    stop = threading.Event()

    # The interrupted message must be printed after the live region has closed.
    # Printing it from inside the region (as a signal handler does) means Rich
    # erases it along with the last frame, leaving a stale spinner as the final
    # line of the scrollback.
    try:
        with Live(line.render(), console=err, refresh_per_second=15, transient=True) as live:
            def tick() -> None:
                while not stop.wait(1 / 15):
                    live.update(line.render())

            worker = threading.Thread(target=tick, daemon=True)
            worker.start()
            try:
                yield
            finally:
                stop.set()
                worker.join(timeout=0.2)
    except BaseException:
        err.print("[muted]interrupted[/]")
        raise
    elapsed = time.monotonic() - line.start
    err.print(f"[ok]{G['ok']}[/] {done or 'done'} [muted]({elapsed:.0f}s)[/]")


def progress(description: str = "") -> Progress:
    """Progress bar on stderr with a cycling gradient fill.

    Disabled (no live region, no output) when animation is off; callers still
    advance tasks, so the calling code never branches.
    """
    return Progress(
        _GradientSpinner(),
        TextColumn("[fg]{task.description}"),
        _GradientBar(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=err, transient=False, disable=not env.animate, refresh_per_second=15,
    )


def panel(content: Any, title: str | None = None, style: str = "border") -> Panel:
    """Rounded panel, the default grouping for a block of output.

    Rounded box on Unicode terminals, ASCII box otherwise. Title in `accent`.
    Use for blocks that belong together; a screen with more than two panels is
    usually a screen that should be split.
    """
    from rich.box import ASCII, ROUNDED
    return Panel(content, title=Text(title, style="accent") if title else None,
                 title_align="left", border_style=style, padding=(0, 1),
                 box=ROUNDED if env.unicode else ASCII, width=min(env.width, 100))


def panel_group(*panels: Panel) -> Group:
    """Stack panels with the vertical rhythm the identity expects."""
    return Group(*panels)


def _line(glyph: str, style: str, msg: str) -> None:
    err.print(f"[{style}]{glyph}[/] {msg}")


def ok(msg: str) -> None:
    _line(G["ok"], "ok", msg)


def warn(msg: str) -> None:
    _line(G["warn"], "warn", msg)


def info(msg: str) -> None:
    _line(G["info"], "info", msg)


def fail(msg: str, hint: str | None = None, code: int = 1) -> None:
    """Print `error: msg` and an optional hint on stderr, then exit."""
    err.print(f"[err]error:[/] {msg}")
    if hint:
        err.print(f"  [muted]hint:[/] {hint}")
    raise SystemExit(code)


# ---------------------------------------------------------------------------
# Data output: stdout only, JSON when asked or when piped
# ---------------------------------------------------------------------------


def emit(data: Any, as_json: bool = False, renderable: Any = None) -> None:
    """Send the primary result to stdout.

    as_json or a non-TTY stdout -> compact JSON (stable keys).
    otherwise -> `renderable` (a Rich table, tree, panel) or str(data).
    """
    if as_json or (not env.stdout_tty and renderable is not None):
        sys.stdout.write(json.dumps(data, ensure_ascii=False, separators=(",", ":"),
                                    sort_keys=True) + "\n")
        sys.stdout.flush()
        return
    console.print(renderable if renderable is not None else data)


# ---------------------------------------------------------------------------
# Signals: Ctrl-C leaves the terminal clean and exits 130
# ---------------------------------------------------------------------------


def install_signal_handlers() -> None:
    def _sigint(_sig: int, _frame: Any) -> None:
        # Restore the terminal, then let the exception unwind so any live region
        # closes before anything is printed. Callers that own a live region print
        # their own interrupted line; see `thinking`.
        sys.stderr.write("\x1b[?25h\x1b[?2026l\r\x1b[K")
        raise SystemExit(130)

    signal.signal(signal.SIGINT, _sigint)


# ---------------------------------------------------------------------------
# Argument handling helpers
# ---------------------------------------------------------------------------


def parse_args(parser: Any, argv: Sequence[str] | None = None) -> Any:
    """argparse.parse_args that follows the exit code and error format rules.

    Usage errors print `error: <msg>` plus a hint pointing at --help and exit
    with 2 instead of argparse's default multi line usage dump.
    """
    import argparse

    class _Parser(argparse.ArgumentParser):
        def error(self, message: str) -> None:  # type: ignore[override]
            err.print(f"[err]error:[/] {message}")
            # Turn an unknown flag into a suggestion when one is close enough.
            unknown = re.search(r"unrecognized arguments?: (\S+)", message)
            hint = None
            if unknown:
                known = [o for a in self._actions for o in a.option_strings]
                near = did_you_mean(unknown.group(1), known)
                if near:
                    hint = f"did you mean `{near}`?"
            err.print(f"  [muted]hint:[/] {hint or f'run `{self.prog} --help` for usage and examples'}")
            raise SystemExit(2)

    parser.__class__ = _Parser
    return parser.parse_args(argv)


def did_you_mean(word: str, options: Sequence[str], max_distance: int = 2) -> str | None:
    """Closest option to `word` within `max_distance` edits, or None.

    Used to turn a rejection into a recovery: an unknown subcommand or flag
    should suggest the near match rather than only stating that it is unknown.
    Uses difflib so there is no dependency; the cutoff is expressed as a ratio
    because difflib does not take an edit budget.
    """
    import difflib

    if not word or not options:
        return None
    # Convert an edit budget into a similarity ratio for the length at hand.
    cutoff = max(0.4, 1 - max_distance / max(len(word), 1))
    matches = difflib.get_close_matches(word, list(options), n=1, cutoff=cutoff)
    return matches[0] if matches else None


def apply_color_flag(value: str) -> None:
    """Honor --color=auto|always|never. Auto keeps the detected environment."""
    global env, theme, console, err
    if value == "auto":
        return
    depth = 0 if value == "never" else (env.depth or 16_777_216)
    env = Env(**{**env.__dict__, "color": depth > 0, "depth": depth,
                 "animate": env.animate and depth > 0})
    theme = _roles()
    console = _console(sys.stdout, env.stdout_tty or value == "always")
    err = _console(sys.stderr, env.stderr_tty or value == "always")


# ---------------------------------------------------------------------------
# Launcher: a filterable select list with a keybinding footer
#
# The pattern behind Charm based launchers (Daytona, Crush, gum choose): a
# brand header, a list of rows carrying a label and a description, live
# filtering, and a footer that always states which keys do what. It is the
# only interactive primitive most command tools need; anything richer belongs
# in Textual (see references/interactive-tui.md).
# ---------------------------------------------------------------------------


def keybar(*pairs: tuple[str, str]) -> Text:
    """Footer of key hints: key in accent, action in muted, separated by dots."""
    out = Text()
    for i, (key, action) in enumerate(pairs):
        if i:
            out.append("  \u2022  " if env.unicode else "  |  ", style=theme["dim"])
        out.append(key, style=theme["accent"])
        out.append(" " + action, style=theme["muted"])
    return out


def _read_key() -> str:
    """Read one key press in raw mode. Returns a name for special keys.

    Reads through the file descriptor rather than the buffered text stream, so
    a multi byte escape sequence (an arrow key) arrives whole. An unrecognised
    sequence is ignored rather than treated as escape, which is what turns a
    stray terminal report into an accidental cancel.
    """
    import select as _select
    import termios
    import tty

    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode("utf-8", "replace")
        if ch == "\x1b":
            if not _select.select([fd], [], [], 0.05)[0]:
                return "esc"  # a bare escape, pressed by the user
            seq = os.read(fd, 8).decode("utf-8", "replace")
            return {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}.get(seq, "ignore")
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x7f":
            return "backspace"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def select(items: Sequence[tuple[str, str]], title: str = "", prompt: str = "Select an option",
           max_rows: int = 10) -> str | None:
    """Interactive single select. Returns the chosen label, or None on escape.

    `items` is a sequence of (label, description) pairs. Typing filters the
    list, arrows or j and k move, enter chooses, escape cancels. Raises
    SystemExit(2) when the terminal is not interactive, naming the flag the
    caller should offer instead, because a tool must never require a TTY.
    """
    if not env.interactive:
        fail("this command needs an interactive terminal",
             "pass the value as a flag instead, or run without a pipe", code=2)
    if not items:
        return None

    from rich.live import Live

    query, cursor = "", 0

    def visible() -> list[tuple[str, str]]:
        if not query:
            return list(items)
        q = query.lower()
        # Label matches rank above description matches: typing the start of a
        # name should put that name first, not whatever mentions it in prose.
        by_label = [it for it in items if q in it[0].lower()]
        by_desc = [it for it in items if q not in it[0].lower() and q in it[1].lower()]
        return by_label + by_desc

    def frame() -> Panel:
        rows = visible()
        body = Text()
        if title:
            body.append_text(gradient_text(title))
            body.append("\n")
        body.append(prompt, style=theme["muted"])
        if query:
            body.append(f"  {G['pointer']} {query}", style=theme["accent"])
        body.append("\n\n")
        if not rows:
            body.append("  no match", style=theme["muted"])
        pad = max((len(label) for label, _ in rows), default=0)
        for i, (label, description) in enumerate(rows[:max_rows]):
            selected = i == cursor
            body.append(f" {G['pointer']} " if selected else "   ",
                        style=theme["accent"] if selected else theme["dim"])
            body.append(f"{label:<{pad}}", style=("bold " + theme["accent"]) if selected else theme["fg"])
            body.append(f"  {description}\n", style=theme["muted"])
        if len(rows) > max_rows:
            body.append(f"   {len(rows) - max_rows} more, keep typing to filter\n", style=theme["dim"])
        body.append("\n")
        body.append_text(keybar(("up/down", "move"), ("type", "filter"),
                                ("enter", "select"), ("esc", "cancel")))
        return panel(body)

    with Live(frame(), console=err, refresh_per_second=15, transient=True,
              screen=False) as live:
        while True:
            key = _read_key()
            rows = visible()
            if key == "ignore":
                continue
            if key == "esc":
                return None
            if key == "enter":
                return rows[cursor][0] if rows else None
            if key in ("up", "k"):
                cursor = max(0, cursor - 1)
            elif key in ("down", "j"):
                cursor = min(max(0, min(len(rows), max_rows) - 1), cursor + 1)
            elif key == "backspace":
                query, cursor = query[:-1], 0
            elif len(key) == 1 and key.isprintable():
                query, cursor = query + key, 0
            live.update(frame())

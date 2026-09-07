"""Camada visual do stdout.

O ui.py vendorizado (template da skill cli-devops-with-ultimate-ui) e a unica
fonte de deteccao de ambiente e de cor: papeis, profundidade, largura, unicode.
Este modulo escreve ANSI cru porque a tabela de dados vai para o stdout e
precisa sair byte a byte igual ao que os testes fixam; o Rich fica com a
decoracao no stderr, dentro do ui.

Politica de cor, em ordem de precedencia:
  1. --color never | always
  2. --no-color
  3. NO_COLOR nao vazio
  4. FORCE_COLOR
  5. TTY, TERM, COLORTERM
"""

from __future__ import annotations

import os
import re
from typing import Sequence, TextIO

from . import ui

RGB = tuple[int, int, int]

NONE, ANSI_16, ANSI_256, TRUECOLOR = 0, 1, 2, 3

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Papeis do tema aurora, na variante que o ui escolheu para este terminal.
# Sao tabelas do modulo vendorizado: uma copia aqui sairia do compasso na
# proxima atualizacao do template.
_ROLES: dict[str, str] = ui._LIGHT if ui.env.light_bg else ui._DARK
_GRADIENT: list[str] = ui.GRADIENT_LIGHT if ui.env.light_bg else ui.GRADIENT_DARK

# Papeis de dominio, apontando para os papeis do tema. A quimica nao entra na
# paleta: acido e basico sao leituras de um numero, nao estados do programa.
DOMAIN = {
    "acidic": "info",
    "basic": "accent2",
    "hydrophobic": "warn",
    "hydrophilic": "teal",
}

ANSI16 = {
    "fg": "39", "muted": "90", "dim": "90", "accent": "34", "accent2": "35",
    "teal": "36", "ok": "32", "warn": "33", "err": "31", "info": "36", "border": "90",
}
C256 = {
    "fg": "", "muted": "245", "dim": "240", "accent": "75", "accent2": "141",
    "teal": "80", "ok": "114", "warn": "221", "err": "210", "info": "117", "border": "238",
}

GLYPHS = {
    True: {"ok": "✓", "err": "✗", "warn": "▲", "info": "●",
           "pointer": "❯", "rule": "─", "bar_fill": "█",
           "bar_empty": "░", "axis": "│"},
    False: {"ok": "ok", "err": "x", "warn": "!", "info": "*", "pointer": ">",
            "rule": "-", "bar_fill": "#", "bar_empty": "-", "axis": "|"},
}
BOX = {
    True: {"tl": "╭", "tr": "╮", "bl": "╰", "br": "╯",
           "h": "─", "v": "│"},
    False: {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|"},
}

_PARTIAL = "▏▎▍▌▋▊▉█"


def unicode_ok() -> bool:
    return ui.env.unicode


def g(name: str) -> str:
    return GLYPHS[ui.env.unicode][name]


def box() -> dict[str, str]:
    return BOX[ui.env.unicode]


def term_width(default: int = 80) -> int:
    return ui.env.width or default


def _tier() -> int:
    d = ui.env.depth
    if d >= 16_777_216:
        return TRUECOLOR
    if d >= 256:
        return ANSI_256
    return ANSI_16 if d >= 16 else NONE


def level(stream: TextIO, mode: str = "auto") -> int:
    """Profundidade de cor a usar neste stream."""
    if mode == "never":
        return NONE
    tier = _tier()
    if mode == "always":
        return tier or TRUECOLOR
    if not (hasattr(stream, "isatty") and stream.isatty()):
        return NONE
    return tier


def _hex_to_rgb(h: str) -> RGB:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _resolve(color: RGB | str) -> tuple[RGB | None, str]:
    """Devolve o RGB e o nome do papel, aceitando papel, papel de dominio ou RGB."""
    if isinstance(color, tuple):
        return color, "accent"
    role = DOMAIN.get(color, color)
    value = _ROLES.get(role)
    return (_hex_to_rgb(value) if value else None), role


def fg(text: str, color: RGB | str, lvl: int, bold: bool = False) -> str:
    if lvl == NONE or not text:
        return text
    rgb, role = _resolve(color)
    if lvl == TRUECOLOR and rgb:
        code = f"\x1b[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m"
    elif lvl == ANSI_256:
        idx = C256.get(role) or (_to_256(rgb) if rgb else "")
        code = f"\x1b[38;5;{idx}m" if idx != "" else ""
    else:
        code = f"\x1b[{ANSI16.get(role, '39')}m"
    return f"{BOLD if bold else ''}{code}{text}{RESET}"


def dim(text: str, lvl: int) -> str:
    return f"{DIM}{text}{RESET}" if lvl else text


def _to_256(c: RGB) -> int:
    r, gr, b = c
    if abs(r - gr) < 12 and abs(gr - b) < 12:
        return 232 + min(23, (r * 3 + gr * 4 + b * 3) // 10 // 11)
    return 16 + 36 * (r * 5 // 255) + 6 * (gr * 5 // 255) + (b * 5 // 255)


def _lerp(a: RGB, b: RGB, t: float) -> RGB:
    return (round(a[0] + (b[0] - a[0]) * t),
            round(a[1] + (b[1] - a[1]) * t),
            round(a[2] + (b[2] - a[2]) * t))


def ramp(stops: Sequence[RGB], n: int) -> list[RGB]:
    if n <= 1:
        return [stops[0]]
    out, segs = [], len(stops) - 1
    for i in range(n):
        pos = i / (n - 1) * segs
        k = min(int(pos), segs - 1)
        out.append(_lerp(stops[k], stops[k + 1], pos - k))
    return out


def stops() -> list[RGB]:
    return [_hex_to_rgb(s) for s in _GRADIENT]


def gradient(text: str, lvl: int, bold: bool = False) -> str:
    """Gradiente da identidade, caractere a caractere. Nunca sob texto de dados."""
    if lvl == NONE:
        return text
    if lvl == ANSI_16:
        return fg(text, "accent", lvl, bold)
    colors = ramp(stops(), max(len(text), 2))
    parts = [BOLD] if bold else []
    for ch, c in zip(text, colors):
        if ch == " ":
            parts.append(ch)
            continue
        parts.append(
            f"\x1b[38;2;{c[0]};{c[1]};{c[2]}m{ch}" if lvl == TRUECOLOR
            else f"\x1b[38;5;{_to_256(c)}m{ch}"
        )
    parts.append(RESET)
    return "".join(parts)


def visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))


def rule(width: int, lvl: int, label: str = "") -> str:
    ch = g("rule")
    if label:
        head = f"{ch}{ch} {label} "
        return gradient(head, lvl, bold=True) + dim(ch * max(0, width - visible_len(head)), lvl)
    return gradient(ch * width, lvl)


def bar(value: float, vmax: float, width: int, lvl: int, color: RGB | str = "accent") -> str:
    if vmax <= 0:
        return " " * width
    frac = max(0.0, min(1.0, value / vmax))
    fill, empty = g("bar_fill"), g("bar_empty")
    if not ui.env.unicode:
        n = round(frac * width)
        return fg(fill * n, color, lvl) + dim(empty * (width - n), lvl)
    total = frac * width
    full = int(total)
    rest = total - full
    s = fill * full
    if full < width and rest > 0.06:
        s += _PARTIAL[min(len(_PARTIAL) - 1, int(rest * 8))]
    pad = width - visible_len(s)
    return fg(s, color, lvl) + dim(empty * pad, lvl)


def diverging_bar(value: float, vmax: float, width: int, lvl: int) -> str:
    """Barra centrada: negativo a esquerda, positivo a direita.

    Devolve exatamente `width` colunas visiveis. Um eixo central exige largura
    impar; quando ela e par, a coluna que sobra vira preenchimento a direita, em
    vez de sair uma celula mais estreita que o cabecalho.
    """
    block, axis = g("bar_fill"), g("axis")
    half = max(1, (width - 1) // 2)
    n = min(half, round(abs(value) / vmax * half)) if vmax else 0
    if value < 0:
        body = " " * (half - n) + fg(block * n, "hydrophilic", lvl) + dim(axis, lvl) + " " * half
    else:
        body = " " * half + dim(axis, lvl) + fg(block * n, "hydrophobic", lvl) + " " * (half - n)
    return body + " " * (width - (2 * half + 1))

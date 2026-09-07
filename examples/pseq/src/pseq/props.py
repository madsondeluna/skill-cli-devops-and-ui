"""Propriedades fisico-quimicas de sequencias proteicas."""

from __future__ import annotations

STANDARD = "ACDEFGHIKLMNPQRSTVWY"
AMBIGUOUS = "BJOUXZ"
ALPHABET = set(STANDARD + AMBIGUOUS + "*-")

# Massas medias dos residuos (Da), sem agua.
RESIDUE_MASS = {
    "A": 71.0788, "R": 156.1875, "N": 114.1038, "D": 115.0886, "C": 103.1388,
    "E": 129.1155, "Q": 128.1307, "G": 57.0519, "H": 137.1411, "I": 113.1594,
    "L": 113.1594, "K": 128.1741, "M": 131.1926, "F": 147.1766, "P": 97.1167,
    "S": 87.0782, "T": 101.1051, "W": 186.2132, "Y": 163.1760, "V": 99.1326,
    "U": 150.0388, "O": 237.3018,
}
WATER = 18.01528

# Kyte-Doolittle.
HYDROPATHY = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# pKa (Lehninger); positivos e negativos tratados separadamente.
PKA_POS = {"NTERM": 9.69, "K": 10.53, "R": 12.48, "H": 6.00}
PKA_NEG = {"CTERM": 2.34, "D": 3.65, "E": 4.25, "C": 8.18, "Y": 10.07}


def clean(seq: str) -> str:
    return seq.replace("*", "").replace("-", "")


def molecular_weight(seq: str) -> float:
    s = clean(seq)
    if not s:
        return 0.0
    return sum(RESIDUE_MASS.get(a, 0.0) for a in s) + WATER


def gravy(seq: str) -> float:
    s = [a for a in clean(seq) if a in HYDROPATHY]
    return sum(HYDROPATHY[a] for a in s) / len(s) if s else 0.0


def charge_at(seq: str, ph: float) -> float:
    s = clean(seq)
    if not s:
        return 0.0
    counts = {a: s.count(a) for a in "KRHDECY"}
    pos = 1.0 / (1.0 + 10 ** (ph - PKA_POS["NTERM"]))
    for a in "KRH":
        pos += counts[a] / (1.0 + 10 ** (ph - PKA_POS[a]))
    neg = 1.0 / (1.0 + 10 ** (PKA_NEG["CTERM"] - ph))
    for a in "DECY":
        neg += counts[a] / (1.0 + 10 ** (PKA_NEG[a] - ph))
    return pos - neg


def isoelectric_point(seq: str) -> float:
    """Bisseccao no intervalo 0..14 ate a carga liquida cruzar zero."""
    if not clean(seq):
        return 0.0
    lo, hi = 0.0, 14.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if charge_at(seq, mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def composition(seq: str) -> dict[str, int]:
    s = clean(seq)
    counts = {a: 0 for a in STANDARD}
    for a in s:
        counts[a] = counts.get(a, 0) + 1
    return counts


def ambiguous_positions(seq: str) -> list[tuple[int, str]]:
    return [(i + 1, a) for i, a in enumerate(seq) if a in AMBIGUOUS]


def invalid_positions(seq: str) -> list[tuple[int, str]]:
    return [(i + 1, a) for i, a in enumerate(seq) if a not in ALPHABET]


def prosite_to_regex(pattern: str) -> str:
    """Converte notacao PROSITE (P-x(2)-[ST]-{P}) em regex Python."""
    p = pattern.strip().rstrip(".")
    out = []
    anchored_start = p.startswith("<")
    anchored_end = p.endswith(">")
    p = p.strip("<>")
    for token in p.split("-"):
        if not token:
            continue
        rep = ""
        if "(" in token:
            token, rep = token[: token.index("(")], token[token.index("(") :]
            rep = "{" + rep[1:-1] + "}"
        if token == "x":
            out.append("." + rep)
        elif token.startswith("{"):
            out.append("[^" + token[1:-1] + "]" + rep)
        elif token.startswith("["):
            out.append(token + rep)
        else:
            out.append(token + rep)
    body = "".join(out)
    return ("^" if anchored_start else "") + body + ("$" if anchored_end else "")

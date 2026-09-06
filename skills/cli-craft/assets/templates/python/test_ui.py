"""Tests for the ui module. Copy next to ui.py and run with `pytest` or
`python -m unittest`. They exercise the three things that break in the wild:
environment detection, the data path, and the gradient fallback.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

PROBE = (
    "import ui, json; e = ui.env; "
    "print(json.dumps(dict(color=e.color, depth=e.depth, animate=e.animate, unicode=e.unicode)))"
)


def probe(**env: str) -> dict:
    """Import ui in a subprocess (detection happens at import) and return Env."""
    clean = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR", "CI", "COLORTERM")}
    clean.update(env)
    out = subprocess.run([sys.executable, "-c", PROBE], cwd=HERE, env=clean,
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class EnvDetection(unittest.TestCase):
    def test_piped_has_no_color_and_no_animation(self) -> None:
        e = probe(TERM="xterm-256color")
        self.assertFalse(e["color"])      # stdout is a pipe in subprocess.run
        self.assertFalse(e["animate"])

    def test_no_color_wins_over_colorterm(self) -> None:
        e = probe(NO_COLOR="1", COLORTERM="truecolor", FORCE_COLOR="")
        self.assertEqual(e["depth"], 0)

    def test_force_color_sets_depth(self) -> None:
        e = probe(FORCE_COLOR="3")
        self.assertEqual(e["depth"], 16_777_216)
        e = probe(FORCE_COLOR="2")
        self.assertEqual(e["depth"], 256)

    def test_ascii_escape_hatch(self) -> None:
        e = probe(TOOL_ASCII="1", LANG="C.UTF-8")
        self.assertFalse(e["unicode"])


class DataPath(unittest.TestCase):
    def test_emit_json_is_compact_and_sorted(self) -> None:
        code = "import ui; ui.emit({'b': 1, 'a': [1, 2]}, as_json=True)"
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout, '{"a":[1,2],"b":1}\n')
        self.assertEqual(out.stderr, "")

    def test_gradient_falls_back_to_plain_when_no_color(self) -> None:
        code = ("import ui; t = ui.gradient_text('banner'); "
                "print(len(t.plain), sum(1 for s in t.spans if s.style))")
        clean = {k: v for k, v in os.environ.items() if k != "FORCE_COLOR"}
        clean["NO_COLOR"] = "1"
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=clean, capture_output=True, text=True, check=True)
        length, spans = out.stdout.split()
        self.assertEqual(length, "6")
        self.assertLessEqual(int(spans), 1)  # one style for the whole word, no per char spans


class Suggestions(unittest.TestCase):
    def test_near_miss_is_suggested(self) -> None:
        code = ("import ui; print(ui.did_you_mean('--colour', "
                "['--color', '--json', '--help']))")
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True,
                             text=True, check=True)
        self.assertEqual(out.stdout.strip(), "--color")

    def test_far_miss_returns_none(self) -> None:
        code = "import ui; print(ui.did_you_mean('--zzzz', ['--color', '--json']))"
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True,
                             text=True, check=True)
        self.assertEqual(out.stdout.strip(), "None")


class ThinkingIndicator(unittest.TestCase):
    def test_line_has_all_five_parts(self) -> None:
        code = ("import ui; l = ui._ThinkingLine(counter=lambda: '7k tokens'); "
                "print(l.render().plain)")
        clean = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        clean["FORCE_COLOR"] = "3"
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=clean,
                             capture_output=True, text=True, check=True)
        line = out.stdout.strip()
        self.assertIn("Thinking", line)          # verb
        self.assertIn("0s", line)                # elapsed
        self.assertIn("7k tokens", line)         # counter
        self.assertIn("esc to interrupt", line)  # way out

    def test_non_animated_path_prints_two_lines(self) -> None:
        code = ("import ui\n"
                "with ui.thinking(done='finished'):\n"
                "    pass\n")
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True,
                             text=True, check=True)
        self.assertEqual(len(out.stderr.strip().splitlines()), 2)
        self.assertEqual(out.stdout, "")  # chrome never touches stdout


class BannerArt(unittest.TestCase):
    def test_shadow_font_is_used_when_it_fits(self) -> None:
        code = "import ui; a = ui.ascii_art('cli'); print(len(a), max(len(r) for r in a))"
        clean = dict(os.environ, LANG="C.UTF-8", COLUMNS="120", FORCE_COLOR="3")
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=clean,
                             capture_output=True, text=True, check=True)
        rows, width = out.stdout.split()
        self.assertEqual(rows, "6")      # shadow font height
        self.assertGreater(int(width), 12)

    def test_degrades_to_one_line_on_narrow_terminal(self) -> None:
        code = "import ui; print(ui.ascii_art('averylongtoolname'))"
        clean = dict(os.environ, LANG="C.UTF-8", COLUMNS="40", FORCE_COLOR="3")
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=clean,
                             capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), "['AVERYLONGTOOLNAME']")

    def test_sweep_has_a_soft_peak_that_wraps(self) -> None:
        code = ("import ui; print(round(ui._shimmer_at(0.5, 0.5), 3), "
                "round(ui._shimmer_at(0.0, 0.99), 3), round(ui._shimmer_at(0.0, 0.5), 3))")
        out = subprocess.run([sys.executable, "-c", code], cwd=HERE, capture_output=True,
                             text=True, check=True)
        peak, wrapped, far = (float(v) for v in out.stdout.split())
        self.assertEqual(peak, 1.0)          # centre is full intensity
        self.assertGreater(wrapped, 0.9)     # wraps across the seam
        self.assertLess(far, 0.01)           # falls off to nothing


if __name__ == "__main__":
    unittest.main()

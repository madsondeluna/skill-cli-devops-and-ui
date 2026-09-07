import gzip
import os
import subprocess
import sys
from pathlib import Path

import pytest

FA = """>sp|P1 first protein
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ
>P2 second
ACDEFGHIKLMNPQRSTVWY
>P3
MXXK
"""


@pytest.fixture
def fa(tmp_path: Path) -> Path:
    p = tmp_path / "in.fa"
    p.write_text(FA)
    return p


def run(*args, stdin: str | None = None, env: dict | None = None):
    e = {**os.environ, "NO_COLOR": "1", **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "pseq.cli", *args],
        input=stdin, capture_output=True, text=True, env=e,
    )


def test_help_to_stdout_exit_0():
    r = run("--help")
    assert r.returncode == 0
    assert "stats" in r.stdout and r.stderr == ""
    assert run("stats", "-h").returncode == 0
    assert run("--version").stdout.strip().startswith("pseq ")


def test_no_input_and_tty_stdin_is_usage_error():
    # stdin nao e TTY dentro do subprocess; simula ausencia de arquivo com stdin fechado vazio
    r = run("stats", stdin="")
    assert r.returncode == 0 and r.stdout.strip() == "id\tlength\tmw\tpi\tgravy\tcharge"


def test_unknown_command_exit_2():
    r = run("stat")
    assert r.returncode == 2
    assert r.stdout == "" and "Error" in r.stderr


def test_stats_piped_is_tsv_data_only(fa):
    r = run("stats", str(fa))
    assert r.returncode == 0
    lines = r.stdout.splitlines()
    assert lines[0] == "id\tlength\tmw\tpi\tgravy\tcharge"
    assert lines[1].split("\t")[:2] == ["sp|P1", "33"]
    assert "Warning: P3" in r.stderr  # aviso vai para stderr, nao contamina dados


def test_no_negative_zero(tmp_path):
    p = tmp_path / "n.fa"
    p.write_text(">H\nMLLIVVGAILFAVLGLIVGAVLIAGFLLVAGIILVA\n")
    r = run("stats", str(p))
    assert "-0.00" not in r.stdout


def test_sample_file_runs():
    r = run("stats", "examples/sample.fa")
    assert r.returncode == 0 and "UBIQ" in r.stdout


def test_stats_json(fa):
    import json
    r = run("stats", "--json", str(fa))
    data = json.loads(r.stdout)
    p2 = next(d for d in data if d["id"] == "P2")
    assert p2["length"] == 20
    assert 2300 < p2["mw"] < 2400
    assert 5.5 < p2["pi"] < 7.5


def test_json_and_tsv_exclusive(fa):
    r = run("stats", "--json", "--tsv", str(fa))
    assert r.returncode == 2 and "mutually exclusive" in r.stderr


def test_missing_file_is_actionable():
    r = run("stats", "nope.fa")
    assert r.returncode == 1
    assert "does not exist" in r.stderr and "Try:" in r.stderr


def test_stdin_dash_and_gzip(fa, tmp_path):
    r = run("stats", "-", stdin=FA)
    assert r.returncode == 0 and "sp|P1" in r.stdout
    gz = tmp_path / "in.fa.gzipped"  # extensao nao importa, magic bytes sim
    gz.write_bytes(gzip.compress(FA.encode()))
    r = run("stats", str(gz))
    assert r.returncode == 0 and "P2" in r.stdout


def test_filter_writes_fasta_and_pipes(fa):
    r = run("filter", "--min-length", "21", str(fa))
    assert r.stdout.startswith(">sp|P1 first protein\n")
    assert ">P2" not in r.stdout
    # Sem TTY o indicador vira uma linha estatica no stderr, sem controle nenhum.
    assert "\x1b" not in r.stderr and "\r" not in r.stderr
    r = run("filter", "--no-ambiguous", "--invert", str(fa))
    assert r.stdout.splitlines()[0] == ">P3"
    r = run("filter", "--min-length", "9", "--max-length", "3", str(fa))
    assert r.returncode == 2


def test_validate_exit_3_on_errors(tmp_path):
    bad = tmp_path / "bad.fa"
    bad.write_text(">A\nMKT\n>A\nMK1\n>B\n\n")
    r = run("validate", bad.as_posix())
    assert r.returncode == 3
    assert "duplicate id" in r.stdout and "invalid character '1'" in r.stdout
    assert "error(s)" in r.stderr
    ok = tmp_path / "ok.fa"
    ok.write_text(">A\nMKT\n")
    assert run("validate", str(ok)).returncode == 0


def test_motif_prosite(fa):
    r = run("motif", "--prosite", "--pattern", "K-x-[AS]", str(fa))
    rows = [l.split("\t") for l in r.stdout.splitlines()[1:]]
    assert ["sp|P1", "2", "4", "KTA"] in rows
    r = run("motif", "--pattern", "[", str(fa))
    assert r.returncode == 2 and "invalid pattern" in r.stderr


def test_output_flag_and_convert(fa, tmp_path):
    out = tmp_path / "out.tsv"
    r = run("convert", "--tsv", "-o", str(out), str(fa))
    assert r.returncode == 0 and r.stdout == ""
    assert out.read_text().splitlines()[0] == "id\tdescription\tseq"
    r = run("convert", "--line-width", "10", str(fa))
    assert r.stdout.splitlines()[1] == "MKTAYIAKQR"


def test_sigpipe_is_quiet(fa):
    big = "".join(f">S{i}\nMKTAYIAKQR\n" for i in range(20000))
    p = subprocess.run(
        f"{sys.executable} -m pseq.cli stats - | head -n 2",
        input=big, shell=True, capture_output=True, text=True,
        env={**os.environ, "NO_COLOR": "1"},
    )
    assert "Traceback" not in p.stderr and "BrokenPipe" not in p.stderr

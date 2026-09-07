"""A camada visual aparece so em terminal e some por completo em pipe."""

import fcntl
import os
import pty
import re
import struct
import subprocess
import sys
import termios

import pytest

ANSI = re.compile(r"\x1b\[[0-9;]*m")
SAMPLE = "examples/sample.fa"


def run(*args, env=None):
    e = {**os.environ, "NO_COLOR": "1", **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "pseq.cli", *args], capture_output=True, text=True, env=e
    )


def run_tty(*args, cols=100, env=None, split_err=True, animate=False):
    """Executa num pseudo-terminal, com stderr em um pipe a parte.

    Sem separar os fluxos, o pty entrega mensagens e dados na mesma sequencia de
    bytes e nenhuma afirmacao sobre a pureza do stdout faria sentido.
    """
    err_r, err_w = (os.pipe() if split_err else (None, None))
    pid, fd = pty.fork()
    if pid == 0:
        if split_err:
            os.close(err_r)
            os.dup2(err_w, 2)
        os.environ.pop("NO_COLOR", None)
        # A animacao custa segundos por execucao; so os testes que a medem a ligam.
        if not animate:
            os.environ["PSEQ_NO_ANIMATION"] = "1"
        else:
            os.environ.pop("PSEQ_NO_ANIMATION", None)
        os.environ.update(
            COLORTERM="truecolor", TERM="xterm-256color", COLUMNS=str(cols), **(env or {})
        )
        os.execv(sys.executable, [sys.executable, "-m", "pseq.cli", *args])
    if split_err:
        os.close(err_w)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, cols, 0, 0))
    out = b""
    while True:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    err = b""
    if split_err:
        while True:
            chunk = os.read(err_r, 65536)
            if not chunk:
                break
            err += chunk
        os.close(err_r)
    _, status = os.waitpid(pid, 0)
    return out.decode(errors="replace"), err.decode(errors="replace"), os.waitstatus_to_exitcode(status)


def test_pipe_has_no_escape_sequences():
    for cmd in (["stats", SAMPLE], ["composition", SAMPLE], ["validate", SAMPLE]):
        r = run(*cmd)
        assert "\x1b" not in r.stdout, cmd


def test_tty_paints_gradient_and_bars():
    out, _, rc = run_tty("stats", SAMPLE)
    assert rc == 0
    assert "\x1b[38;2;" in out          # truecolor
    assert "█" in out                    # barras
    assert "─" in out                    # regra do titulo
    assert "UBIQ" in ANSI.sub("", out)


def test_no_color_wins_over_tty():
    out, err, rc = run_tty("stats", SAMPLE, env={"NO_COLOR": "1"})
    assert rc == 0 and "\x1b[" not in out and "\x1b[" not in err


def test_color_always_forces_ansi_into_a_pipe():
    r = run("stats", "--color", "always", SAMPLE, env={"NO_COLOR": ""})
    assert "\x1b[38;2;" in r.stdout
    # o layout continua sendo o de terminal, nao o TSV
    assert "\t" not in r.stdout


def test_color_never_and_bad_value():
    out, err, _ = run_tty("stats", "--color", "never", SAMPLE)
    assert "\x1b[" not in out and "\x1b[" not in err
    r = run("stats", "--color", "sometimes", SAMPLE)
    assert r.returncode == 2 and "auto, always or never" in r.stderr


def test_no_art_keeps_color_but_drops_bars():
    out, _, rc = run_tty("stats", "--no-art", SAMPLE)
    assert rc == 0 and "\x1b[38;2;" in out and "█" not in out


def test_tsv_flag_beats_the_terminal():
    out, _, rc = run_tty("stats", "--tsv", SAMPLE)
    assert rc == 0 and "\x1b[" not in out
    assert "id\tlength\tmw\tpi\tgravy\tcharge" in out


def test_json_is_identical_in_both_worlds():
    piped = run("stats", "--json", SAMPLE).stdout
    tty, _, _ = run_tty("stats", "--json", SAMPLE)
    assert "\x1b[" not in tty
    assert piped.replace("\n", "") == tty.replace("\r\n", "").replace("\n", "")


def test_animation_never_reaches_a_pipe():
    r = run("stats", SAMPLE)
    assert "\x1b[?25l" not in r.stderr and "\r" not in r.stderr


def test_warning_verdict_is_not_reported_as_clean():
    out, err, rc = run_tty("validate", SAMPLE)
    plain = ANSI.sub("", out + err)
    assert rc == 0
    assert "1 warning(s)" in plain and "clean" not in plain


def test_banner_only_without_a_subcommand():
    # O banner e decoracao: sai no stderr, por isso os fluxos ficam juntos aqui.
    out, _, rc = run_tty(split_err=False)
    plain = ANSI.sub("", out)
    assert rc == 0 and "█" in out and "protein FASTA analysis" in plain
    out, err, _ = run_tty("stats", SAMPLE)
    assert "protein FASTA analysis" not in ANSI.sub("", out + err)


CURSOR_UP = re.compile(r"\x1b\[\d*A")


def test_animation_redraws_in_place_and_returns_the_cursor():
    out, _, rc = run_tty(split_err=False, animate=True)
    assert rc == 0
    assert "\x1b[?25l" in out and "\x1b[?25h" in out      # cursor escondido e devolvido
    assert CURSOR_UP.search(out)                          # quadros redesenhados no lugar
    assert "\x1b[?2026h" in out and "\x1b[?2026l" in out  # cada quadro em uma pintura so


def test_no_animation_env_var_is_honored():
    """Sem animacao nao ha redesenho: o banner sai em um quadro estatico.

    A saida sincronizada nao serve de prova aqui, porque todo quadro do Rich
    passa a ser emitido dentro dela, animado ou nao.
    """
    out, _, rc = run_tty(split_err=False, animate=False)
    assert rc == 0 and not CURSOR_UP.search(out)


@pytest.mark.parametrize("cols", [60, 80, 100, 120])
def test_no_rendered_line_exceeds_the_window(cols):
    """Uma linha mais larga que a janela quebra em duas e desalinha a tabela."""
    for cmd in (["stats", SAMPLE], ["composition", SAMPLE], ["validate", SAMPLE],
                ["motif", "--pattern", "N[^P][ST]", SAMPLE]):
        out, err, _ = run_tty(*cmd, cols=cols)
        for stream in (out, err):
            for line in stream.splitlines():
                for seg in line.split("\r"):
                    assert len(ANSI.sub("", seg)) <= cols, (cmd, cols, ANSI.sub("", seg))


def test_banner_never_reaches_stdout():
    """Um banner no stdout quebraria `pseq | cat`; ele pertence ao stderr."""
    out, err, rc = run_tty(split_err=True)
    assert rc == 0
    assert "█" not in out
    assert "\x1b[" not in ANSI.sub("", out)


def test_quiet_silences_status_and_warnings():
    out, err, rc = run_tty("stats", "--quiet", SAMPLE)
    assert rc == 0 and err == ""
    assert "UBIQ" in ANSI.sub("", out)

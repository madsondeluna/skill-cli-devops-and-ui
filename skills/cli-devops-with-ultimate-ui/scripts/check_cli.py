#!/usr/bin/env python3
"""Audit a command line tool for terminal hygiene.

Runs the given command under several environments and reports violations
of the rules in references/principles.md and review-checklist.md:

  pipe        stdout and stderr piped (no TTY): no ANSI, no cursor movement
  no_color    pseudo TTY with NO_COLOR=1: no SGR sequences
  ci          pseudo TTY with CI=true: no live redraws
  tty         pseudo TTY, truecolor: cursor restored, alt screen left, width respected
  help        --help: examples present, fits 80 columns, exit 0
  version     --version: one line, exit 0
  json        --json (if the tool accepts it): stdout is one valid JSON document
  usage       an unknown flag: exit 2, one line error, hint present
  sigint      Ctrl+C after a short delay in a TTY: exit 130 and cursor restored

Usage:
  python check_cli.py [--tui] [--timeout SECONDS] [--width N] -- <command> [args...]

--tui   treats the command as a full screen app: sends q after startup, expects
        alternate screen enter and leave, checks resize handling by sending SIGWINCH.

Exit code is the number of blocking findings (0 when clean). Stdlib only; Unix only
(uses pty). Nothing here is tool specific: it is a generic harness.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time

ANSI = re.compile(rb"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][AB012]")
SGR = re.compile(rb"\x1b\[[0-9;]*m")
CURSOR_MOVE = re.compile(rb"\x1b\[[0-9]*[ABCDEFGHJKf]|\r(?!\n)")
HIDE_CURSOR = b"\x1b[?25l"
SHOW_CURSOR = b"\x1b[?25h"
ALT_ENTER = re.compile(rb"\x1b\[\?1049h|\x1b\[\?47h")
ALT_LEAVE = re.compile(rb"\x1b\[\?1049l|\x1b\[\?47l")
MOUSE_ON = re.compile(rb"\x1b\[\?100[0236]h")
MOUSE_OFF = re.compile(rb"\x1b\[\?100[0236]l")
SYNC = re.compile(rb"\x1b\[\?2026h")

findings: list[tuple[str, str, str]] = []  # (severity, check, message)


def add(sev: str, check: str, msg: str) -> None:
    findings.append((sev, check, msg))


def base_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR", "CI", "CLICOLOR_FORCE")}
    env.update(extra)
    return env


def run_pipe(cmd: list[str], env: dict[str, str], timeout: float, stdin: bytes | None = None) -> tuple[int, bytes, bytes]:
    try:
        p = subprocess.run(cmd, env=env, input=stdin, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        return -1, e.stdout or b"", e.stderr or b""
    except FileNotFoundError:
        add("blocking", "run", f"command not found: {cmd[0]}")
        return 127, b"", b""


def run_pty(cmd: list[str], env: dict[str, str], timeout: float, width: int = 80, height: int = 24,
            send: list[tuple[float, bytes]] | None = None, sigint_after: float | None = None,
            winch_after: float | None = None) -> tuple[int, bytes]:
    """Run under a pseudo terminal. Returns (exit code, combined output)."""
    pid, fd = pty.fork()
    if pid == 0:  # child
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        os.execvpe(cmd[0], cmd, env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
    out = bytearray()
    t0 = time.monotonic()
    send = sorted(send or [], key=lambda x: x[0])
    sent_int = False
    sent_winch = False
    status = None
    while True:
        el = time.monotonic() - t0
        if send and el >= send[0][0]:
            try:
                os.write(fd, send.pop(0)[1])
            except OSError:
                pass
        if sigint_after is not None and not sent_int and el >= sigint_after:
            os.kill(pid, signal.SIGINT)
            sent_int = True
        if winch_after is not None and not sent_winch and el >= winch_after:
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", height, width - 20, 0, 0))
            os.kill(pid, signal.SIGWINCH)
            sent_winch = True
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                chunk = b""
            if not chunk:
                break
            out += chunk
        wpid, st = os.waitpid(pid, os.WNOHANG)
        if wpid == pid:
            status = st
            # drain
            while True:
                r, _, _ = select.select([fd], [], [], 0.05)
                if not r:
                    break
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
            break
        if el > timeout:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
            add("major", "timeout", f"did not exit within {timeout}s under a TTY")
            status = None
            break
    os.close(fd)
    if status is None:
        return -1, bytes(out)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status), bytes(out)
    return os.WEXITSTATUS(status), bytes(out)


def visible_width(line: bytes) -> int:
    return len(ANSI.sub(b"", line).decode("utf-8", "replace"))


def check_pipe(cmd, timeout):
    rc, out, err = run_pipe(cmd, base_env(), timeout)
    if ANSI.search(out):
        add("blocking", "pipe", "stdout contains ANSI escapes when piped (color or cursor control leaks into scripts)")
    if ANSI.search(err):
        add("blocking", "pipe", "stderr contains ANSI escapes when piped")
    if CURSOR_MOVE.search(out) or CURSOR_MOVE.search(err):
        add("blocking", "pipe", "cursor movement or carriage return redraws when piped (spinner or progress not disabled)")
    if HIDE_CURSOR in out + err:
        add("blocking", "pipe", "cursor hidden while piped")
    if rc == -1:
        add("major", "pipe", f"did not exit within {timeout}s when piped (waiting for a prompt?)")
    return rc, out, err


def check_no_color(cmd, timeout):
    rc, out = run_pty(cmd, base_env(NO_COLOR="1", TERM="xterm-256color"), timeout)
    if SGR.search(out):
        add("blocking", "no_color", "SGR color sequences emitted with NO_COLOR=1")
    return rc, out


def check_ci(cmd, timeout):
    rc, out = run_pty(cmd, base_env(CI="true", TERM="xterm-256color"), timeout)
    redraws = len(re.findall(rb"\r(?!\n)", out)) + len(re.findall(rb"\x1b\[[0-9]*A", out))
    if redraws > 3:
        add("major", "ci", f"{redraws} in place redraws with CI=true (progress and spinners should print static lines in CI)")
    return rc, out


def check_tty(cmd, timeout, width, tui):
    env = base_env(TERM="xterm-256color", COLORTERM="truecolor", LANG="en_US.UTF-8")
    send = [(0.8, b"q")] if tui else None
    rc, out = run_pty(cmd, env, timeout, width=width, send=send, winch_after=0.4 if tui else None)
    if HIDE_CURSOR in out and out.rfind(SHOW_CURSOR) < out.rfind(HIDE_CURSOR):
        add("blocking", "tty", "cursor hidden and not restored on exit")
    if ALT_ENTER.search(out):
        if not tui:
            add("major", "tty", "alternate screen used by a non full screen command (scrollback is lost)")
        if not ALT_LEAVE.search(out):
            add("blocking", "tty", "alternate screen entered and not left on exit")
    elif tui:
        add("minor", "tty", "full screen app did not use the alternate screen (scrollback will be polluted)")
    if MOUSE_ON.search(out) and not MOUSE_OFF.search(out):
        add("blocking", "tty", "mouse tracking enabled and not disabled on exit")
    sgrs = SGR.findall(out)
    if sgrs and sgrs[-1] not in (b"\x1b[0m", b"\x1b[m") and not re.fullmatch(rb"\x1b\[(?:0;)*0?m", sgrs[-1]):
        add("minor", "tty", "last SGR sequence is not a reset (terminal may keep the last color)")
    # width: any visible line longer than width
    # A carriage return overwrites the line, so measure each \r segment on its own.
    long_lines = [l for l in out.split(b"\n")
                  if max((visible_width(seg) for seg in l.split(b"\r")), default=0) > width]
    if long_lines:
        add("major", "tty", f"{len(long_lines)} line(s) exceed the terminal width of {width}")
    if not SYNC.search(out) and (tui or CURSOR_MOVE.search(out)):
        add("minor", "tty", "live redraws without DEC 2026 synchronized output (may flicker in tmux and over SSH)")
    if b"\x1b[5m" in out or b"\x1b[7m" in out and not tui:
        add("minor", "tty", "blink or reverse video used")
    # emoji detection (astral plane and common symbol ranges)
    if re.search(r"[\U0001F300-\U0001FAFF\u2600-\u26FF]", out.decode("utf-8", "replace")):
        add("minor", "tty", "emoji or pictographic symbols in output")
    if not SGR.search(out) and not tui:
        add("minor", "tty", "no color at all on a truecolor TTY (fine for pure data tools, otherwise add semantic color)")
    return rc, out


def check_help(cmd, timeout):
    rc, out, err = run_pipe(cmd + ["--help"], base_env(), timeout)
    text = (out + err).decode("utf-8", "replace")
    if rc != 0:
        add("major", "help", f"--help exited {rc} (expected 0)")
    if not text.strip():
        add("major", "help", "--help printed nothing")
        return
    if out.strip() == b"" and err.strip():
        add("minor", "help", "--help printed to stderr (stdout is conventional so it can be paged and grepped)")
    if "example" not in text.lower():
        add("major", "help", "--help has no Examples section (examples are what users copy)")
    wide = [l for l in text.splitlines() if len(l) > 80]
    if wide:
        add("minor", "help", f"{len(wide)} help line(s) exceed 80 columns")
    # A machine readable mode may already exist under another name. Reporting a
    # missing --json when the tool offers --format json would push a redundant
    # flag onto a working interface, which is the opposite of the job here.
    machine_readable = re.search(
        r"--json|--format[= ]|--output[= ]|--out(?:put)?-format|-o\s+\{?json|ndjson|--porcelain",
        text, re.IGNORECASE)
    if not machine_readable:
        add("minor", "help", "no machine readable output advertised (--json, --format json or equivalent)")
    elif "--json" not in text:
        add("info", "help", f"machine readable output exists under another name ({machine_readable.group(0).strip()}); keep it, do not add a second spelling")
    if "--color" not in text and "no-color" not in text:
        add("minor", "help", "no --color flag (NO_COLOR alone is acceptable, but a flag is expected by clig.dev)")
    return text


def check_version(cmd, timeout):
    # A version flag belongs to the program, not to the subcommand the audit was
    # pointed at, so `tool sub file --version` failing proves nothing. Probe the
    # given argv first, then the bare executable.
    targets = [cmd]
    if len(cmd) > 1:
        targets.append(cmd[:1])
    for target in targets:
        for flag in ("--version", "-V"):
            rc, out, err = run_pipe(target + [flag], base_env(), timeout)
            if rc == 0 and (out + err).strip():
                lines = (out + err).strip().splitlines()
                if len(lines) > 2:
                    add("minor", "version", f"{flag} printed {len(lines)} lines (one is conventional)")
                return
    add("minor", "version", "no --version or -V")


def check_json(cmd, timeout, help_text):
    if not help_text or "--json" not in help_text:
        return
    rc, out, err = run_pipe(cmd + ["--json"], base_env(), timeout)
    if rc == -1:
        return
    try:
        json.loads(out.decode("utf-8"))
    except Exception:
        # accept JSON lines
        try:
            for line in out.decode("utf-8").splitlines():
                if line.strip():
                    json.loads(line)
        except Exception:
            add("blocking", "json", "--json stdout is not valid JSON (decoration or logs mixed into stdout?)")
    if ANSI.search(out):
        add("blocking", "json", "--json stdout contains ANSI escapes")


def check_usage(cmd, timeout):
    rc, out, err = run_pipe(cmd + ["--this-flag-does-not-exist-xyz"], base_env(), timeout)
    if rc == -1:
        return
    if rc != 2:
        add("major", "usage", f"unknown flag exited {rc} (expected 2 for usage errors)")
    text = (out + err).decode("utf-8", "replace")
    if len(text.strip().splitlines()) > 6:
        add("minor", "usage", "unknown flag printed the full help (print one line and a hint instead)")
    if "help" not in text.lower():
        add("minor", "usage", "usage error does not point to --help")


def check_sigint(cmd, timeout, tui):
    env = base_env(TERM="xterm-256color", COLORTERM="truecolor")
    rc, out = run_pty(cmd, env, timeout, sigint_after=0.5)
    if rc == 0 and len(out) < 10:
        return  # exited before the signal, nothing to check
    if rc not in (130, 2, -1) and rc != 0:
        add("minor", "sigint", f"Ctrl+C exit code {rc} (130 is conventional)")
    if HIDE_CURSOR in out and out.rfind(SHOW_CURSOR) < out.rfind(HIDE_CURSOR):
        add("blocking", "sigint", "cursor not restored after Ctrl+C")
    if ALT_ENTER.search(out) and not ALT_LEAVE.search(out):
        add("blocking", "sigint", "alternate screen not left after Ctrl+C")
    if MOUSE_ON.search(out) and not MOUSE_OFF.search(out):
        add("blocking", "sigint", "mouse tracking not disabled after Ctrl+C")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tui", action="store_true", help="treat as a full screen app")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--width", type=int, default=80)
    ap.add_argument("--skip", default="", help="comma separated checks to skip (help,version,json,usage,sigint,ci)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="command after --")
    a = ap.parse_args()
    cmd = [c for c in a.cmd if c != "--"]
    if not cmd:
        ap.error("give the command after --")
    skip = set(a.skip.split(",")) if a.skip else set()

    print(f"check_cli: {' '.join(cmd)}", file=sys.stderr)
    if not a.tui:
        check_pipe(cmd, a.timeout)
    check_no_color(cmd, a.timeout)
    if "ci" not in skip and not a.tui:
        check_ci(cmd, a.timeout)
    check_tty(cmd, a.timeout, a.width, a.tui)
    help_text = None if "help" in skip else check_help(cmd, a.timeout)
    if "version" not in skip:
        check_version(cmd, a.timeout)
    if "json" not in skip and not a.tui:
        check_json(cmd, a.timeout, help_text)
    if "usage" not in skip:
        check_usage(cmd, a.timeout)
    if "sigint" not in skip:
        check_sigint(cmd, a.timeout, a.tui)

    # "info" is not a finding: it records something the tool does differently
    # and correctly, so an audit does not read as if it were a defect.
    order = {"blocking": 0, "major": 1, "minor": 2, "info": 3}
    findings.sort(key=lambda f: order[f[0]])
    if not findings:
        print("clean: no findings", file=sys.stderr)
        return 0
    for sev, check, msg in findings:
        print(f"{sev:9s} {check:9s} {msg}", file=sys.stderr)
    blocking = sum(1 for f in findings if f[0] == "blocking")
    real = sum(1 for f in findings if f[0] != "info")
    notes = len(findings) - real
    tail = f", {notes} note(s)" if notes else ""
    print(f"\n{real} finding(s), {blocking} blocking{tail}", file=sys.stderr)
    return blocking


if __name__ == "__main__":
    sys.exit(main())

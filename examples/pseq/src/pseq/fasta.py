"""Leitura de FASTA a partir de arquivos, gzip ou stdin."""

from __future__ import annotations

import gzip
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Iterable

from .errors import EXIT_RUNTIME, PseqError

GZIP_MAGIC = b"\x1f\x8b"


@dataclass
class Record:
    id: str
    description: str
    seq: str
    source: str
    line: int


def _open_source(path: str) -> tuple[io.TextIOBase, str]:
    """Abre arquivo ou stdin; detecta gzip por magic bytes, nao por extensao."""
    if path == "-":
        raw = sys.stdin.buffer
        name = "<stdin>"
    else:
        p = Path(path)
        if not p.exists():
            raise PseqError(
                f"{path} does not exist.",
                "check the path, or pass - to read from stdin.",
                EXIT_RUNTIME,
            )
        if p.is_dir():
            raise PseqError(f"{path} is a directory, not a FASTA file.", code=EXIT_RUNTIME)
        try:
            raw = p.open("rb")
        except PermissionError:
            raise PseqError(f"{path} is not readable.", f"chmod +r {path}", EXIT_RUNTIME)
        name = path
    head = raw.peek(2)[:2] if hasattr(raw, "peek") else b""
    if head == GZIP_MAGIC:
        raw = gzip.open(raw, "rb")
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace"), name


def parse(handle: Iterable[str], source: str) -> Iterator[Record]:
    header: str | None = None
    header_line = 0
    chunks: list[str] = []
    for n, line in enumerate(handle, 1):
        line = line.rstrip("\r\n")
        if line.startswith(">"):
            if header is not None:
                yield _make(header, chunks, source, header_line)
            header = line[1:]
            header_line = n
            chunks = []
        elif header is None:
            if line.strip():
                raise PseqError(
                    f"{source}:{n}: sequence data before the first '>' header.",
                    "make sure the file is FASTA; use `pseq validate` for a full report.",
                    EXIT_DATA_FROM_PARSE,
                )
        else:
            chunks.append(line.strip())
    if header is not None:
        yield _make(header, chunks, source, header_line)


EXIT_DATA_FROM_PARSE = 3


def _make(header: str, chunks: list[str], source: str, line: int) -> Record:
    parts = header.split(None, 1)
    rid = parts[0] if parts else ""
    desc = parts[1] if len(parts) > 1 else ""
    return Record(id=rid, description=desc, seq="".join(chunks).upper(), source=source, line=line)


def read_all(paths: list[str]) -> Iterator[Record]:
    for path in paths:
        handle, name = _open_source(path)
        try:
            yield from parse(handle, name)
        finally:
            if path != "-":
                handle.close()


def write_fasta(records: Iterable[Record], out, line_width: int = 60, case: str | None = None) -> int:
    n = 0
    for r in records:
        seq = r.seq
        if case == "lower":
            seq = seq.lower()
        header = f">{r.id} {r.description}".rstrip()
        out.write(header + "\n")
        if line_width <= 0:
            out.write(seq + "\n")
        else:
            for i in range(0, len(seq), line_width):
                out.write(seq[i : i + line_width] + "\n")
        n += 1
    return n

"""Portable, conservative filesystem boundaries and atomic writes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path, PureWindowsPath


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def confined(root: Path, relative: str) -> Path:
    if not relative or "\x00" in relative or ":" in relative or "\\" in relative:
        raise ValueError("Expected a safe relative path inside the bank")
    part = Path(relative)
    if part.is_absolute() or PureWindowsPath(relative).is_absolute() or ".." in part.parts:
        raise ValueError("Path escapes the memory bank")
    current = root
    for segment in part.parts:
        current = current / segment
        if linked(current):
            raise ValueError(f"Symbolic links and junctions are not followed: {relative}")
    target = current.resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError("Path escapes the memory bank")
    return current


def atomic_bytes(path: Path, data: bytes) -> None:
    if linked(path) or linked(path.parent):
        raise ValueError("Refusing to write through a symbolic link or junction")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def atomic_text(path: Path, text: str) -> None:
    atomic_bytes(path, text.encode("utf-8"))

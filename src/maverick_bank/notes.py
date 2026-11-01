"""Read Markdown evidence without interpreting it as executable instructions."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import yaml

from .config import Config
from .paths import confined, linked

KINDS = {"preference", "decision", "lesson", "fact", "hypothesis"}
STATUSES = {"unverified", "user-confirmed", "observed"}


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_id(value: str) -> bool:
    if re.fullmatch(r"import-[0-9a-f]{24}", value):
        return True
    try:
        return str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


@dataclass
class Note:
    id: str
    relative: str
    path: Path
    raw: bytes
    text: str
    body: str
    body_start: int
    metadata: dict
    modified_at: str
    revision: str
    superseded_by: list[str] = field(default_factory=list)

    @property
    def scope(self) -> str:
        return self.metadata.get("scope", "global")

    def summary(self) -> dict:
        return {
            "id": self.id,
            "revision": self.revision,
            "path": str(self.path),
            "relative_path": self.relative,
            "title": self.metadata.get("title", self.path.stem),
            "source": self.metadata.get("source", ""),
            "scope": self.scope,
            "kind": self.metadata.get("kind", "fact"),
            "status": self.metadata.get("status", "unverified"),
            "created_at": self.metadata.get("created_at"),
            "checked_at": self.metadata.get("checked_at"),
            "modified_at": self.modified_at,
            "date_warning": "modified_at is file text time; declared dates are assertions, not proof of validity",
            "supersedes": self.metadata.get("supersedes"),
            "superseded_by": self.superseded_by,
        }


def parse_note(root: Path, path: Path, raw: bytes) -> Note:
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    metadata = {}
    body_start = 1
    if lines and lines[0] == "---":
        try:
            closing = lines.index("---", 1)
        except ValueError as exc:
            raise ValueError("Unclosed Markdown frontmatter") from exc
        metadata = yaml.safe_load("\n".join(lines[1:closing])) or {}
        if not isinstance(metadata, dict):
            raise ValueError("Frontmatter must be an object")
        body_start = closing + 2
    while body_start <= len(lines) and not lines[body_start - 1].strip():
        body_start += 1
    relative = path.relative_to(root).as_posix()
    memory_id = metadata.get("id", "import-" + digest(relative.encode())[:24])
    if not isinstance(memory_id, str) or not valid_id(memory_id):
        raise ValueError("Invalid memory id")
    for key in (
        "scope",
        "source",
        "title",
        "kind",
        "status",
        "supersedes",
        "created_at",
        "checked_at",
    ):
        if (
            key in {"scope", "source", "title", "kind", "status"}
            and key in metadata
            and metadata[key] is None
        ):
            raise ValueError(f"Metadata {key} must not be null")
        if key in metadata and metadata[key] is not None and not isinstance(metadata[key], str):
            if key in {"created_at", "checked_at"} and hasattr(metadata[key], "isoformat"):
                metadata[key] = metadata[key].isoformat()
            else:
                raise ValueError(f"Metadata {key} must be a string")
    if (
        metadata.get("kind", "fact") not in KINDS
        or metadata.get("status", "unverified") not in STATUSES
    ):
        raise ValueError("Unknown memory kind or status")
    if not metadata.get("scope", "global").strip():
        raise ValueError("Memory scope must not be empty")
    body = "\n".join(lines[body_start - 1 :]).strip()
    modified = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    return Note(
        memory_id, relative, path, raw, text, body, body_start, metadata, modified, digest(raw)
    )


def scan(root: Path, config: Config) -> tuple[dict[str, Note], list[dict], set[str]]:
    notes_root = confined(root, config.notes_dir)
    notes: dict[str, Note] = {}
    issues: list[dict] = []
    ambiguous: set[str] = set()
    count = 0
    for folder, dirs, files in os.walk(notes_root, followlinks=False):
        base = Path(folder)
        for name in list(dirs):
            candidate = base / name
            if name.startswith("."):
                dirs.remove(name)
            elif linked(candidate):
                dirs.remove(name)
                issues.append({"code": "unsafe_path", "path": str(candidate)})
        for name in sorted(files):
            if not name.lower().endswith(".md"):
                continue
            path = base / name
            count += 1
            if count > config.max_files:
                if count == config.max_files + 1:
                    issues.append(
                        {
                            "code": "file_limit",
                            "reason": "Bank exceeds max_files; extra files are not indexed until the configured limit is raised",
                        }
                    )
                continue
            try:
                confined(root, path.relative_to(root).as_posix())
                if path.stat().st_size > config.max_note_bytes:
                    raise ValueError("Note exceeds max_note_bytes")
                note = parse_note(root, path, path.read_bytes())
                if note.id in ambiguous:
                    issues.append({"code": "duplicate_id", "id": note.id, "path": str(path)})
                elif note.id in notes:
                    previous = notes.pop(note.id)
                    ambiguous.add(note.id)
                    issues.append(
                        {
                            "code": "duplicate_id",
                            "id": note.id,
                            "paths": [str(previous.path), str(path)],
                        }
                    )
                else:
                    notes[note.id] = note
            except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
                issues.append(
                    {
                        "code": "unsafe_path" if linked(path) else "invalid_note",
                        "path": str(path),
                        "reason": str(exc),
                    }
                )
    for note in notes.values():
        old = note.metadata.get("supersedes")
        if old:
            if old in notes and notes[old].scope == note.scope and old != note.id:
                notes[old].superseded_by.append(note.id)
            else:
                issues.append({"code": "invalid_supersedes", "id": note.id, "target": old})
    return notes, issues, ambiguous

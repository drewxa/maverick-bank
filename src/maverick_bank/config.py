"""Explicit bank settings; no environment scanning or remote providers."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import tomlkit

from .paths import atomic_text, confined


@dataclass(frozen=True)
class Config:
    schema_version: int = 1
    notes_dir: str = "notes"
    default_scope: str = "global"
    git_enabled: bool = True
    review_after_days: int = 90
    maintenance_interval_days: int = 7
    max_note_bytes: int = 262144
    max_response_chars: int = 12000
    max_files: int = 10000
    lock_timeout: int = 15
    event_retention_days: int = 90
    event_max_count: int = 50000
    semantic_enabled: bool = False
    semantic_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    semantic_cache_dir: str = ""
    capture_policy: str = "Save explicit requests and clear corrections; exclude secrets, raw transcripts, temporary tasks and unconfirmed inferred preferences."

    def validate(self, root: Path) -> Config:
        defaults = Config()
        for field in fields(self):
            if type(getattr(self, field.name)) is not type(getattr(defaults, field.name)):
                raise ValueError(f"Configuration {field.name} has an invalid type")
        if self.schema_version != 1:
            raise ValueError(
                "Unsupported configuration schema; upgrade Maverick Bank before opening"
            )
        if self.notes_dir == "." or self.notes_dir.split("/")[0] in {".git", ".maverick"}:
            raise ValueError("notes_dir must be a dedicated relative directory")
        confined(root, self.notes_dir)
        for key in (
            "review_after_days",
            "maintenance_interval_days",
            "lock_timeout",
            "event_retention_days",
            "event_max_count",
        ):
            if not 1 <= getattr(self, key) <= 1000000:
                raise ValueError(f"Configuration {key} must be positive and bounded")
        if not 1024 <= self.max_note_bytes <= 8 * 1024 * 1024:
            raise ValueError("max_note_bytes must be between 1024 and 8388608")
        if not 256 <= self.max_response_chars <= 100000 or not 1 <= self.max_files <= 100000:
            raise ValueError("Response/file limits are out of range")
        if not self.default_scope.strip() or len(self.default_scope) > 200:
            raise ValueError("Invalid default_scope")
        return self

    @classmethod
    def load(cls, path: Path, root: Path) -> Config:
        try:
            values = tomllib.loads(path.read_text(encoding="utf-8"))
            return cls(**values).validate(root)
        except (tomllib.TOMLDecodeError, TypeError) as exc:
            raise ValueError(f"Invalid bank configuration: {exc}") from exc

    def save(self, path: Path) -> None:
        atomic_text(path, tomlkit.dumps(asdict(self)))


def default_root() -> Path:
    return Path(
        os.environ.get("MAVERICK_BANK_HOME", str(Path.home() / ".maverick-bank"))
    ).expanduser()

"""Durable local observations, intentionally independent of the search index."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from .notes import utcnow
from .paths import atomic_text, linked


def append(path: Path, event: str, **metadata) -> dict:
    if linked(path):
        raise ValueError("Refusing a linked journal")
    record = {
        "event_id": str(uuid4()),
        "at": utcnow(),
        "event": event,
        "observer": "bank-server",
        **metadata,
    }
    separator = b""
    if path.exists() and path.stat().st_size:
        with path.open("rb") as previous:
            previous.seek(-1, os.SEEK_END)
            if previous.read(1) != b"\n":
                separator = b"\n"
    with path.open("ab") as stream:
        stream.write(separator + (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    return record


def read_events(path: Path) -> tuple[list[dict], int]:
    if not path.exists():
        return [], 0
    if linked(path):
        raise ValueError("Refusing a linked journal")
    events, invalid = [], 0
    with path.open("rb") as stream:
        for line in stream:
            try:
                event = json.loads(line.decode("utf-8"))
                if not isinstance(event, dict) or not isinstance(event.get("event"), str):
                    raise ValueError("Invalid event")
                events.append(event)
            except (ValueError, TypeError, UnicodeError):
                invalid += 1
    return events, invalid


def report(path: Path) -> dict:
    events, invalid = read_events(path)
    return {
        "events": dict(Counter(item["event"] for item in events)),
        "invalid_journal_lines": invalid,
        "interpretation": "offered=server response prepared; read=bank served text; declared_used=agent self-report. None proves attention, causal benefit, or correctness. Direct filesystem reads are unobserved.",
    }


def prune(path: Path, days: int, max_count: int) -> dict:
    events, invalid = read_events(path)
    if invalid:
        raise ValueError("Journal contains malformed lines; preserve and repair it before pruning")
    cutoff = datetime.now(UTC) - timedelta(days=days)
    retained = [e for e in events if datetime.fromisoformat(e["at"]) >= cutoff][-max_count:]
    atomic_text(path, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in retained))
    return {"retained": len(retained), "removed": len(events) - len(retained)}

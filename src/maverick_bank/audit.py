"""Checkable maintenance findings; semantic judgments are explicitly delegated."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from .config import Config
from .notes import Note, digest, utcnow


def audit_notes(
    notes: dict[str, Note], issues: list[dict], config: Config, offset: int = 0, limit: int = 20
) -> dict:
    findings = list(issues)
    content: dict[str, list[str]] = {}
    cutoff = datetime.now(UTC) - timedelta(days=config.review_after_days)
    for note in notes.values():
        if not note.metadata.get("source"):
            findings.append(
                {
                    "code": "missing_source",
                    "id": note.id,
                    "revision": note.revision,
                    "path": str(note.path),
                }
            )
        normalized = re.sub(r"\s+", " ", note.body).strip().casefold()
        if normalized:
            content.setdefault(digest(normalized.encode()), []).append(note.id)
        date = note.metadata.get("checked_at") or note.metadata.get("created_at")
        if date:
            try:
                parsed = datetime.fromisoformat(date.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                if parsed < cutoff and not note.superseded_by:
                    findings.append(
                        {
                            "code": "review_due",
                            "id": note.id,
                            "revision": note.revision,
                            "reason": "Age is a review trigger, not evidence of invalidity",
                        }
                    )
            except ValueError:
                findings.append(
                    {"code": "invalid_date", "id": note.id, "field": "checked_at/created_at"}
                )
        if note.metadata.get("checked_at") and not note.metadata.get("checked_source"):
            findings.append({"code": "check_without_evidence", "id": note.id})
        chain, cursor = set(), note
        while cursor.metadata.get("supersedes") in notes:
            if cursor.id in chain:
                findings.append({"code": "supersession_cycle", "id": note.id})
                break
            chain.add(cursor.id)
            cursor = notes[cursor.metadata["supersedes"]]
    for ids in content.values():
        if len(ids) > 1:
            findings.append(
                {
                    "code": "duplicate_content",
                    "ids": ids[:50],
                    "count": len(ids),
                    "action": "review; similar content may have different scopes or independent sources",
                }
            )
    candidates = [notes[key].summary() for key in sorted(notes) if not notes[key].superseded_by]
    return {
        "at": utcnow(),
        "notes": len(notes),
        "issues": findings[:50],
        "issue_count": len(findings),
        "issues_truncated": len(findings) > 50,
        "semantic_review": "host_agent_required",
        "writes_applied": 0,
        "review_instructions": "Read cited revisions before judging. Separate explicit user statements, observations and inferences. Compare scope and validity time; newest text does not automatically win. Repetition is not independent evidence. Propose corrections as new superseding notes; never delete or promote truth solely from age or usage.",
        "review_candidates": candidates[offset : offset + limit],
        "candidates_truncated": offset + limit < len(candidates),
        "candidate_count": len(candidates),
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(candidates) else None,
        "dataset_revision": digest(
            "\n".join(f"{key}:{notes[key].revision}" for key in sorted(notes)).encode()
        ),
    }

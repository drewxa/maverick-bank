"""One application service for CLI and MCP: files remain authoritative."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import yaml
from filelock import FileLock, Timeout

from . import events
from .audit import audit_notes
from .config import Config
from .history import History
from .index import Index
from .notes import KINDS, STATUSES, Note, digest, scan, utcnow, valid_id
from .paths import atomic_bytes, confined


class Bank:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.state = confined(self.root, ".maverick")
        config_path = confined(self.state, "config.toml")
        if not config_path.is_file():
            raise ValueError(
                f"Bank is not initialized: {self.root}. Run maverick-bank init --bank PATH."
            )
        self.config = Config.load(config_path, self.root)
        self.index_path = confined(self.state, "index.sqlite3")
        self.events_path = confined(self.state, "events.jsonl")
        self.operations_path = confined(self.state, "operations.jsonl")
        self.history = History(self.state, self.config.git_enabled)

    @classmethod
    def initialize(cls, root: Path, **settings) -> Bank:
        root = Path(root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        state = confined(root, ".maverick")
        state.mkdir(exist_ok=True)
        lock_path = confined(state, "bank.lock")
        with FileLock(lock_path, timeout=15):
            path = confined(state, "config.toml")
            if not path.exists():
                config = Config(**settings).validate(root)
                confined(root, config.notes_dir).mkdir(parents=True, exist_ok=True)
                config.save(path)
            elif settings:
                current = Config.load(path, root)
                if any(getattr(current, key, None) != value for key, value in settings.items()):
                    raise ValueError(
                        "Existing configuration differs; edit .maverick/config.toml explicitly"
                    )
        return cls(root)

    @contextmanager
    def locked(self):
        # Validate state paths again; users may edit bank contents between calls.
        for relative in (
            "bank.lock",
            "config.toml",
            "index.sqlite3",
            "events.jsonl",
            "operations.jsonl",
            "history",
        ):
            confined(self.state, relative)
        try:
            with FileLock(confined(self.state, "bank.lock"), timeout=self.config.lock_timeout):
                yield
        except Timeout as exc:
            raise ValueError(
                "Memory bank is busy. Retry after the other operation finishes."
            ) from exc

    def _scan(self):
        return scan(self.root, self.config)

    def _snapshot(self, notes: dict[str, Note]) -> dict:
        if not self.config.git_enabled:
            return {"state": "disabled", "commit": None}
        try:
            commit = self.history.snapshot(notes)
            operations, _ = events.read_events(self.operations_path)
            finished = {o.get("operation_id") for o in operations if o["event"] == "complete"}
            for operation in operations:
                note = notes.get(operation.get("id"))
                if (
                    operation["event"] == "pending"
                    and operation["operation_id"] not in finished
                    and note
                    and note.revision == operation.get("revision")
                ):
                    events.append(
                        self.operations_path,
                        "complete",
                        operation_id=operation["operation_id"],
                        commit=commit,
                    )
            return {"state": "saved", "commit": commit}
        except ValueError as exc:
            return {"state": "history_pending", "commit": None, "reason": str(exc)}

    def _sync_index(self, notes: dict[str, Note]) -> dict:
        try:
            return Index(self.index_path).sync(notes)
        except sqlite3.DatabaseError as exc:
            # Preserve a broken derived database for diagnosis; all authority is elsewhere.
            backup = self.state / f"index.corrupt-{uuid4().hex}.sqlite3"
            self.index_path.replace(backup)
            result = Index(self.index_path).sync(notes)
            return {**result, "recovered_index": str(backup), "reason": str(exc)}

    def _get(self, notes: dict[str, Note], ambiguous: set[str], memory_id: str) -> Note:
        if not valid_id(memory_id):
            raise ValueError("Invalid memory id; use an ID returned by memory_search")
        if memory_id in ambiguous:
            raise ValueError(
                "Memory id is ambiguous; resolve the duplicate files reported by audit"
            )
        if memory_id not in notes:
            raise ValueError("Memory not found; search again or run audit")
        return notes[memory_id]

    def remember(
        self,
        title: str,
        body: str,
        source: str,
        scope: str | None = None,
        kind: str = "fact",
        status: str = "unverified",
        supersedes: str | None = None,
    ) -> dict:
        scope = self.config.default_scope if scope is None else scope
        for name, value, limit in (
            ("title", title, 200),
            ("body", body, self.config.max_note_bytes),
            ("source", source, 2000),
            ("scope", scope, 200),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > limit
                or "\x00" in value
            ):
                raise ValueError(f"{name} must be nonempty and within {limit} characters")
        if kind not in KINDS or status not in STATUSES:
            raise ValueError("Invalid kind or status")
        if kind == "hypothesis" and status != "unverified":
            raise ValueError("A hypothesis cannot be promoted to a confirmed observation")
        if self.config.git_enabled and not self.history.available():
            raise ValueError(
                "Git is required before capture. Install Git or explicitly configure git_enabled=false."
            )
        with self.locked():
            notes, _, ambiguous = self._scan()
            count = sum(
                1
                for p in confined(self.root, self.config.notes_dir).rglob("*")
                if p.suffix.lower() == ".md"
            )
            if count >= self.config.max_files:
                raise ValueError(
                    "Bank has reached max_files; raise the configured limit before capturing more notes"
                )
            if supersedes:
                previous = self._get(notes, ambiguous, supersedes)
                if previous.scope != scope:
                    raise ValueError("A correction must have the same scope as its superseded note")
            before = self._snapshot(notes)
            if before["state"] == "history_pending":
                raise ValueError(before["reason"])
            memory_id, operation_id = str(uuid4()), str(uuid4())
            metadata = {
                "schema_version": 1,
                "id": memory_id,
                "title": title.strip(),
                "created_at": utcnow(),
                "source": source.strip(),
                "scope": scope.strip(),
                "kind": kind,
                "status": status,
            }
            if supersedes:
                metadata["supersedes"] = supersedes
            raw = (
                "---\n"
                + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)
                + "---\n\n"
                + body.strip()
                + "\n"
            ).encode("utf-8")
            if len(raw) > self.config.max_note_bytes:
                raise ValueError("Note exceeds max_note_bytes after UTF-8 encoding")
            path = confined(self.root, f"{self.config.notes_dir}/{memory_id}.md")
            events.append(
                self.operations_path,
                "pending",
                operation_id=operation_id,
                id=memory_id,
                revision=digest(raw),
            )
            atomic_bytes(path, raw)
            notes, _, _ = self._scan()
            history = self._snapshot(notes)
            self._sync_index(notes)
            events.append(
                self.events_path, "captured", id=memory_id, revision=notes[memory_id].revision
            )
            return {**notes[memory_id].summary(), "history": history}

    def read(
        self, memory_id: str, start_line: int | None = None, end_line: int | None = None
    ) -> dict:
        with self.locked():
            notes, _, ambiguous = self._scan()
            note = self._get(notes, ambiguous, memory_id)
            lines = note.text.splitlines()
            start = note.body_start if start_line is None else start_line
            end = min(len(lines), start + 199) if end_line is None else end_line
            if (
                type(start) is not int
                or type(end) is not int
                or start < 1
                or end < start
                or end > len(lines)
                or end - start > 399
            ):
                raise ValueError("Invalid line range; request 1–400 existing lines")
            selected = []
            for line in lines[start - 1 : end]:
                if (
                    sum(len(item) + 1 for item in selected) + len(line)
                    > self.config.max_response_chars
                ):
                    if not selected:
                        raise ValueError(
                            "Source line is too long; split the Markdown line before reading"
                        )
                    break
                selected.append(line)
            end = start + len(selected) - 1
            self._snapshot(notes)
            excerpt = "\n".join(selected)
            if digest(note.path.read_bytes()) != note.revision:
                raise ValueError("Memory changed during read; retry against its current revision")
            events.append(
                self.events_path,
                "read",
                id=note.id,
                revision=note.revision,
                line_start=start,
                line_end=end,
            )
            return {
                **note.summary(),
                "body": excerpt,
                "excerpt": excerpt,
                "line_start": start,
                "line_end": end,
                "truncated": end < len(lines),
                "history": self.history.attribution(note, start, end),
            }

    def search(
        self,
        query: str,
        limit: int = 5,
        scope: str | None = None,
        include_superseded: bool = False,
        all_scopes: bool = False,
    ) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError("query must contain 1–2000 characters")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        scope = scope or self.config.default_scope
        with self.locked():
            notes, issues, _ = self._scan()
            index_state = self._sync_index(notes)
            history = self._snapshot(notes)
            allowed = {
                key
                for key, note in notes.items()
                if (all_scopes or note.scope in {scope, "global"})
                and (include_superseded or not note.superseded_by)
            }
            provider, semantic_status, reason = self._semantic_provider()
            try:
                candidates = Index(self.index_path).retrieve(query, allowed, limit, provider)
            except (ValueError, RuntimeError, OSError) as exc:
                if provider is None:
                    raise
                provider, semantic_status, reason = None, "unavailable", str(exc)
                candidates = Index(self.index_path).retrieve(query, allowed, limit)
            results, consumed = [], 0
            for candidate in candidates:
                note = notes[candidate["memory_id"]]
                if digest(note.path.read_bytes()) != note.revision:
                    issues.append({"code": "changed_during_search", "id": note.id})
                    continue
                excerpt = candidate["body"]
                if consumed + len(excerpt) > self.config.max_response_chars:
                    break
                consumed += len(excerpt)
                results.append(
                    {
                        **note.summary(),
                        "excerpt": excerpt,
                        "line_start": candidate["line_start"],
                        "line_end": candidate["line_end"],
                        "rank_score": candidate["rank_score"],
                        "history": self.history.attribution(
                            note, candidate["line_start"], candidate["line_end"]
                        ),
                    }
                )
                events.append(
                    self.events_path,
                    "offered",
                    id=note.id,
                    revision=note.revision,
                    line_start=candidate["line_start"],
                    line_end=candidate["line_end"],
                    rank=len(results),
                    query_hash=digest(query.encode()),
                )
            return {
                "mode": "hybrid" if provider else "lexical",
                "semantic_status": semantic_status,
                "semantic_reason": reason,
                "scope": scope,
                "results": results,
                "scan_issues": issues[:20],
                "index": index_state,
                "history_state": history["state"],
            }

    def _semantic_provider(self):
        if not self.config.semantic_enabled:
            return (
                None,
                "not_configured",
                "Run semantic install to explicitly provision a local model",
            )
        from .embeddings import load_provider

        try:
            return (
                load_provider(
                    self.state, self.config.semantic_model, self.config.semantic_cache_dir
                ),
                "ready",
                None,
            )
        except (ImportError, OSError, ValueError, RuntimeError) as exc:
            return None, "unavailable", str(exc)

    def record_use(
        self,
        memory_id: str,
        revision: str,
        task_id: str = "",
        agent: str = "unknown",
        outcome: str = "unknown",
    ) -> dict:
        if not valid_id(memory_id) or not re.fullmatch(r"[0-9a-f]{64}", revision):
            raise ValueError("Expected a valid memory id and SHA-256 revision")
        for value in (task_id, agent, outcome):
            if not isinstance(value, str) or len(value) > 500:
                raise ValueError("Attribution fields must be strings up to 500 characters")
        with self.locked():
            observed, _ = events.read_events(self.events_path)
            if not any(
                e.get("id") == memory_id
                and e.get("revision") == revision
                and e["event"] in {"offered", "read", "captured"}
                for e in observed
            ):
                raise ValueError(
                    "Unknown revision; reference a revision actually returned by the bank"
                )
            return events.append(
                self.events_path,
                "declared_used",
                id=memory_id,
                revision=revision,
                task_id=task_id,
                agent=agent,
                outcome=outcome,
                evidence_level="self_report",
            )

    def reindex(self) -> dict:
        with self.locked():
            notes, issues, _ = self._scan()
            if self.index_path.exists():
                self.index_path.unlink()
            result = self._sync_index(notes)
            return {**result, "issues": issues, "history": self._snapshot(notes)}

    def audit(self) -> dict:
        with self.locked():
            notes, issues, _ = self._scan()
            return audit_notes(notes, issues, self.config)

    def stats(self) -> dict:
        with self.locked():
            notes, issues, _ = self._scan()
            return {"notes": len(notes), "issues": len(issues), **events.report(self.events_path)}

    def status(self) -> dict:
        with self.locked():
            notes, issues, _ = self._scan()
            operations, invalid = events.read_events(self.operations_path)
            completed = {
                event.get("operation_id") for event in operations if event["event"] == "complete"
            }
            pending = [
                e["operation_id"]
                for e in operations
                if e["event"] == "pending" and e["operation_id"] not in completed
            ]
            return {
                "root": str(self.root),
                "notes": len(notes),
                "issues": issues[:20],
                "git_enabled": self.config.git_enabled,
                "git_available": self.history.available(),
                "pending_operations": pending,
                "invalid_operation_lines": invalid,
                "semantic_enabled": self.config.semantic_enabled,
                "semantic_model": self.config.semantic_model,
                "capture_policy": self.config.capture_policy,
                "privacy": "No application telemetry, sync or remote inference. Host agents may send offered text to their model providers.",
            }

    def prune_events(self) -> dict:
        with self.locked():
            return events.prune(
                self.events_path, self.config.event_retention_days, self.config.event_max_count
            )

    def provision_semantic(self, model: str | None = None) -> dict:
        from .embeddings import provision

        selected = model or self.config.semantic_model
        result = provision(self.state, selected, self.config.semantic_cache_dir)
        with self.locked():
            self.config = replace(self.config, semantic_enabled=True, semantic_model=selected)
            self.config.save(confined(self.state, "config.toml"))
        return result

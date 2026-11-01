"""Disposable lexical index and local-vector rank fusion."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from .notes import Note, digest


def chunks(note: Note) -> list[dict]:
    lines = note.text.splitlines()
    result, start, pending, size = [], note.body_start, [], 0
    for number in range(note.body_start, len(lines) + 1):
        line = lines[number - 1]
        if pending and (size + len(line) > 1800 or len(pending) >= 40):
            text = "\n".join(pending)
            result.append(
                {
                    "key": digest(f"{note.id}:{start}:{text}".encode()),
                    "id": note.id,
                    "start": start,
                    "end": number - 1,
                    "text": text,
                    "title": note.metadata.get("title", note.path.stem),
                }
            )
            start, pending, size = number, [], 0
        pending.append(line)
        size += len(line) + 1
    if pending:
        text = "\n".join(pending)
        result.append(
            {
                "key": digest(f"{note.id}:{start}:{text}".encode()),
                "id": note.id,
                "start": start,
                "end": len(lines),
                "text": text,
                "title": note.metadata.get("title", note.path.stem),
            }
        )
    return result


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimension mismatch; rebuild the semantic index")
    denominator = math.sqrt(sum(x * x for x in left) * sum(y * y for y in right))
    return (
        sum(x * y for x, y in zip(left, right, strict=True)) / denominator if denominator else 0.0
    )


class Index:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, revision TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS chunks(key TEXT PRIMARY KEY, memory_id TEXT, line_start INTEGER, line_end INTEGER, body TEXT, title TEXT)"
            )
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(key UNINDEXED, title, body, tokenize='unicode61')"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS vectors(key TEXT PRIMARY KEY, model TEXT NOT NULL, vector TEXT NOT NULL)"
            )
        except Exception:
            connection.close()
            raise
        return connection

    def sync(self, notes: dict[str, Note]) -> dict:
        with closing(self.connect()) as db, db:
            existing = {row["id"]: row["revision"] for row in db.execute("SELECT * FROM documents")}
            changed = [note for key, note in notes.items() if existing.get(key) != note.revision]
            removed = set(existing) - set(notes)
            for memory_id in removed | {note.id for note in changed}:
                keys = [
                    row[0]
                    for row in db.execute("SELECT key FROM chunks WHERE memory_id=?", (memory_id,))
                ]
                db.executemany("DELETE FROM search WHERE key=?", [(key,) for key in keys])
                db.execute("DELETE FROM chunks WHERE memory_id=?", (memory_id,))
                db.execute("DELETE FROM documents WHERE id=?", (memory_id,))
            for note in changed:
                db.execute("INSERT INTO documents VALUES (?,?)", (note.id, note.revision))
                for chunk in chunks(note):
                    db.execute(
                        "INSERT INTO chunks VALUES (?,?,?,?,?,?)",
                        (
                            chunk["key"],
                            note.id,
                            chunk["start"],
                            chunk["end"],
                            chunk["text"],
                            chunk["title"],
                        ),
                    )
                    db.execute(
                        "INSERT INTO search VALUES (?,?,?)",
                        (chunk["key"], chunk["title"], chunk["text"]),
                    )
            db.execute("DELETE FROM vectors WHERE key NOT IN (SELECT key FROM chunks)")
        return {"documents": len(notes), "changed": len(changed), "removed": len(removed)}

    def retrieve(self, query: str, allowed: set[str], limit: int, provider=None) -> list[dict]:
        tokens = re.findall(r"[^\W_]+", query, re.UNICODE)[:64]
        if not tokens:
            return []
        expression = " OR ".join('"' + token + '"' for token in tokens)
        with closing(self.connect()) as db, db:
            all_chunks = [
                dict(row)
                for row in db.execute("SELECT * FROM chunks")
                if row["memory_id"] in allowed
            ]
            by_key = {chunk["key"]: chunk for chunk in all_chunks}
            # Filter before top-k: other projects must not crowd out this project's evidence.
            lexical = [
                row["key"]
                for row in db.execute(
                    "SELECT key FROM search WHERE search MATCH ? ORDER BY bm25(search,0,2,1)",
                    (expression,),
                )
                if row["key"] in by_key
            ]
            ranks = {key: 1 / (60 + rank) for rank, key in enumerate(lexical, 1)}
            if provider is not None and all_chunks:
                cached = {
                    row["key"]: json.loads(row["vector"])
                    for row in db.execute(
                        "SELECT * FROM vectors WHERE model=?", (provider.identity,)
                    )
                }
                missing = [chunk for chunk in all_chunks if chunk["key"] not in cached]
                if missing:
                    embeddings = provider.embed_documents([chunk["body"] for chunk in missing])
                    for chunk, vector in zip(missing, embeddings, strict=True):
                        cached[chunk["key"]] = vector
                        db.execute(
                            "INSERT OR REPLACE INTO vectors VALUES (?,?,?)",
                            (chunk["key"], provider.identity, json.dumps(vector)),
                        )
                question = provider.embed_query(query)
                semantic = sorted(
                    ((key, cosine(question, cached[key])) for key in by_key),
                    key=lambda pair: pair[1],
                    reverse=True,
                )
                for rank, (key, similarity) in enumerate(semantic, 1):
                    if similarity >= 0.20:
                        ranks[key] = ranks.get(key, 0) + 1 / (60 + rank)
            ranked = sorted(ranks, key=lambda key: (-ranks[key], key))
            result, seen = [], set()
            for key in ranked:
                chunk = by_key[key]
                if chunk["memory_id"] not in seen:
                    result.append({**chunk, "rank_score": round(ranks[key], 6)})
                    seen.add(chunk["memory_id"])
                if len(result) >= limit:
                    break
        return result

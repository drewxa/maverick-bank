from pathlib import Path
from uuid import uuid4

import pytest
from test_bank import bank_class

from maverick_bank import events


def test_malformed_metadata_is_quarantined_not_a_bank_wide_crash(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    (bank.root / "notes" / "bad.md").write_text("---\nscope: null\n---\nBad note", encoding="utf-8")
    assert any(i["code"] == "invalid_note" for i in bank.audit()["issues"])
    assert bank.search("Bad")["results"] == []
    assert bank.remember("Good", "Working note", source="user:1")


def test_capture_uses_configured_default_scope(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", default_scope="project:private")
    saved = bank.remember("Private", "Private project evidence", source="user:1")
    assert saved["scope"] == "project:private"
    assert bank.search("Private", scope="project:other")["results"] == []


def test_capacity_error_precedes_note_mutation_and_audit_remains_usable(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", max_files=1)
    bank.remember("First", "Existing note", source="user:1")
    with pytest.raises(ValueError, match="max_files"):
        bank.remember("Second", "Must not be written", source="user:2")
    assert len(list((bank.root / "notes").glob("*.md"))) == 1
    assert bank.audit()["notes"] == 1
    assert bank.search("Existing")["results"]


def test_corrupt_derived_index_can_be_rebuilt_on_windows(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Recovery", "Evidence survives index corruption", source="user:1")
    bank.index_path.write_bytes(b"not a sqlite database")
    result = bank.search("corruption")
    assert result["results"][0]["id"] == saved["id"]
    assert "recovered_index" in result["index"]


def test_pending_unwritten_capture_is_never_falsely_completed(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    missing = str(uuid4())
    events.append(
        bank.operations_path, "pending", operation_id=missing, id=str(uuid4()), revision="0" * 64
    )
    bank.search("nothing")
    assert missing in bank.status()["pending_operations"]


def test_read_detects_manual_edit_during_history_snapshot(tmp_path, monkeypatch):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Rule", "Old bytes", source="user:1")
    original = bank._snapshot

    def edit_during_snapshot(notes):
        result = original(notes)
        path = Path(saved["path"])
        path.write_text(
            path.read_text(encoding="utf-8").replace("Old bytes", "New bytes"), encoding="utf-8"
        )
        return result

    monkeypatch.setattr(bank, "_snapshot", edit_during_snapshot)
    with pytest.raises(ValueError, match="changed"):
        bank.read(saved["id"])


def test_small_valid_note_limit_accepts_small_note(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", max_note_bytes=1024)
    assert bank.remember("Tiny", "Small body", source="user:1")


def test_torn_utf8_journal_tail_preserves_previous_events_and_next_append(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Rule", "Keep journal history", source="user:1")
    with bank.events_path.open("ab") as stream:
        stream.write(b'{"event":"read","agent":"\xf0')
    report = bank.stats()
    assert report["events"]["captured"] == 1
    assert report["invalid_journal_lines"] == 1
    bank.read(saved["id"])
    assert bank.stats()["events"]["read"] == 1
    assert bank.stats()["invalid_journal_lines"] == 1

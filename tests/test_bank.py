from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def bank_class():
    try:
        from maverick_bank.bank import Bank
    except ImportError:
        pytest.fail("Bank service is not implemented")
    return Bank


def test_capture_read_preserves_source_and_revision(tmp_path):
    bank = bank_class().initialize(tmp_path / "Моя память with spaces")
    saved = bank.remember("Decisions", "Use SQLite for this project.", source="user:session-7")
    read = bank.read(saved["id"])
    assert read["body"] == "Use SQLite for this project."
    assert read["source"] == "user:session-7"
    assert read["status"] == "unverified"
    assert len(read["revision"]) == 64
    assert Path(read["path"]).is_file()
    assert read["history"]["commit"]


def test_capture_requires_source_and_does_not_promote_inference(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    with pytest.raises(ValueError, match="source"):
        bank.remember("guess", "Maybe the user likes blue", source="")
    with pytest.raises(ValueError, match="hypothesis"):
        bank.remember("guess", "Maybe blue", source="agent:guess", kind="hypothesis", status="user-confirmed")
    assert list((bank.root / "notes").glob("*.md")) == []


def test_reinitialize_preserves_notes_and_configuration(tmp_path):
    Bank = bank_class()
    bank = Bank.initialize(tmp_path / "bank", review_after_days=12)
    saved = bank.remember("Preference", "Short answers", source="user:1")
    again = Bank.initialize(bank.root)
    assert again.config.review_after_days == 12
    assert again.read(saved["id"])["body"] == "Short answers"


def test_two_cooperating_writers_do_not_lose_records(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda n: bank.remember(f"Note {n}", f"Payload {n}", source=f"test:{n}"), range(6)))
    assert len({r["id"] for r in results}) == 6
    assert len(list((bank.root / "notes").glob("*.md"))) == 6


def test_use_event_requires_observed_revision_and_survives_index_rebuild(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Rule", "Keep source links", source="user:1")
    bank.read(saved["id"])
    bank.record_use(saved["id"], saved["revision"], task_id="task-1", agent="codex")
    with pytest.raises(ValueError, match="revision"):
        bank.record_use(saved["id"], "0" * 64)
    bank.reindex()
    assert bank.stats()["events"]["declared_used"] == 1
    assert bank.stats()["events"]["read"] >= 1


def test_manual_changes_are_read_from_authority(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Rule", "Old contents", source="user:1")
    path = Path(saved["path"])
    path.write_text(path.read_text(encoding="utf-8").replace("Old contents", "New contents"), encoding="utf-8")
    current = bank.read(saved["id"])
    assert current["body"] == "New contents"
    assert current["revision"] != saved["revision"]

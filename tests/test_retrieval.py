from pathlib import Path

import pytest
from test_bank import bank_class


def test_search_returns_evidence_lines_and_honest_lexical_mode(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember(
        "Database", "We selected SQLite because it runs locally.", source="user:1"
    )
    found = bank.search("SQLite")
    assert found["mode"] == "lexical"
    assert found["semantic_status"] == "not_configured"
    result = found["results"][0]
    assert result["id"] == saved["id"]
    assert "SQLite" in result["excerpt"]
    assert result["line_start"] > 1
    lines = Path(result["path"]).read_text(encoding="utf-8").splitlines()
    assert result["excerpt"] == "\n".join(lines[result["line_start"] - 1 : result["line_end"]])
    assert bank.stats()["events"]["offered"] == 1
    assert bank.stats()["events"].get("read", 0) == 0


def test_named_scope_includes_global_but_never_other_projects(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    global_note = bank.remember("Global", "Keep evidence", source="user:1")
    own = bank.remember("Project", "Keep evidence", source="user:2", scope="project:one")
    bank.remember("Other", "Keep evidence", source="user:3", scope="project:two")
    assert {r["id"] for r in bank.search("evidence", scope="project:one")["results"]} == {
        global_note["id"],
        own["id"],
    }
    assert [r["id"] for r in bank.search("evidence")["results"]] == [global_note["id"]]


def test_manual_edit_deletion_and_index_deletion_never_return_stale_text(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Rule", "Prefer PostgreSQL", source="user:1")
    assert bank.search("PostgreSQL")["results"]
    path = Path(saved["path"])
    path.write_text(
        path.read_text(encoding="utf-8").replace("PostgreSQL", "SQLite"), encoding="utf-8"
    )
    assert bank.search("PostgreSQL")["results"] == []
    assert bank.search("SQLite")["results"]
    bank.index_path.unlink()
    assert bank.search("SQLite")["results"]
    path.unlink()
    assert bank.search("SQLite")["results"] == []
    assert bank.stats()["events"]["offered"] >= 3


def test_supersession_keeps_history_but_excludes_old_fact(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    old = bank.remember("Database", "Use PostgreSQL", source="user:1")
    new = bank.remember("Database", "Use SQLite", source="user:2", supersedes=old["id"])
    assert bank.search("PostgreSQL")["results"] == []
    assert bank.search("PostgreSQL", include_superseded=True)["results"][0]["id"] == old["id"]
    assert bank.read(old["id"])["superseded_by"] == [new["id"]]
    with pytest.raises(ValueError, match="scope"):
        bank.remember(
            "Wrong", "Use X", source="user:3", scope="project:other", supersedes=new["id"]
        )


def test_unicode_queries_and_fts_syntax_are_safe(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Память", "Пользователь предпочитает короткие ответы.", source="user:1")
    assert bank.search("короткие ответы")["results"][0]["id"] == saved["id"]
    assert bank.search('" OR * : (')["results"] == []
    with pytest.raises(ValueError):
        bank.search("x" * 5000)


def test_imports_are_unverified_and_duplicate_ids_are_quarantined(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    (bank.root / "notes" / "manual.md").write_text(
        "# Manual\n\nRemember walruses", encoding="utf-8"
    )
    assert bank.search("walruses")["results"][0]["status"] == "unverified"
    saved = bank.remember("Decision", "Use unique identity", source="user:1")
    duplicate = bank.root / "notes" / "copy.md"
    duplicate.write_bytes(Path(saved["path"]).read_bytes())
    assert bank.search("unique")["results"] == []
    with pytest.raises(ValueError, match="ambiguous"):
        bank.read(saved["id"])
    assert any(i["code"] == "duplicate_id" for i in bank.audit()["issues"])


def test_matching_long_line_returns_honestly_bounded_evidence(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", max_response_chars=256)
    saved = bank.remember("Long line", "needle " + "x" * 300, source="user:1")
    result = bank.search("needle")["results"][0]
    assert result["id"] == saved["id"]
    assert "needle" in result["excerpt"]
    assert len(result["excerpt"]) <= 256
    assert result["partial_line"] is True
    assert result["column_end"] - result["column_start"] + 1 == len(result["excerpt"])

from datetime import UTC, datetime, timedelta

from test_bank import bank_class


def test_audit_reports_duplicates_missing_sources_and_age_without_editing(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", review_after_days=1)
    bank.remember("One", "Repeat this claim", source="user:1")
    bank.remember("Two", "Repeat this claim", source="user:2")
    old = (datetime.now(UTC) - timedelta(days=10)).isoformat()
    path = bank.root / "notes" / "legacy.md"
    path.write_text(f"---\ncreated_at: '{old}'\n---\nLegacy claim", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in (bank.root / "notes").glob("*.md")}
    report = bank.audit()
    assert {i["code"] for i in report["issues"]} >= {
        "duplicate_content",
        "missing_source",
        "review_due",
    }
    assert report["semantic_review"] == "host_agent_required"
    assert {p.name: p.read_bytes() for p in (bank.root / "notes").glob("*.md")} == before

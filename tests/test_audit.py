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


def test_audit_pages_can_reach_every_record(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", git_enabled=False)
    for number in range(55):
        (bank.root / "notes" / f"manual-{number}.md").write_text(
            f"Review evidence {number}", encoding="utf-8"
        )
    ids = set()
    offset = 0
    while offset is not None:
        page = bank.audit(offset=offset, limit=10)
        ids.update(item["id"] for item in page["review_candidates"])
        offset = page["next_offset"]
    assert len(ids) == 55


def test_normal_search_surfaces_scoped_maintenance_without_manual_scheduler(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank", git_enabled=False)
    own = bank.remember("Current", "Keep useful evidence", source="user:1", scope="project:one")
    other = bank.remember(
        "Other", "Other project secret fixture", source="user:2", scope="project:two"
    )
    result = bank.search("evidence", scope="project:one")
    assert result["maintenance"]["structural_scan_performed"] is True
    assert other["id"] not in str(result["maintenance"])
    assert (
        bank.search("evidence", scope="project:one")["maintenance"]["structural_scan_performed"]
        is False
    )
    page = bank.audit(scope="project:one")
    assert [item["id"] for item in page["review_candidates"]] == [own["id"]]

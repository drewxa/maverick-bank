import subprocess

from test_bank import bank_class


def git(path, *args):
    return subprocess.run(
        ["git", "-c", f"safe.directory={path.as_posix()}", "-C", str(path), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_snapshots_do_not_touch_parent_repository_index(tmp_path):
    git(tmp_path, "init", "--quiet")
    foreign = tmp_path / "foreign.txt"
    foreign.write_text("staged user work", encoding="utf-8")
    git(tmp_path, "add", "foreign.txt")
    before = git(tmp_path, "diff", "--cached", "--binary")
    bank = bank_class().initialize(tmp_path / "bank")
    bank.remember("Decision", "Keep history separate", source="user:1")
    assert git(tmp_path, "diff", "--cached", "--binary") == before
    assert git(bank.root / ".maverick" / "history", "log", "--format=%s").strip()


def test_mixed_source_span_has_consistent_per_line_attributions(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    saved = bank.remember("Mixed", "old first line\nold last line", source="user:1")
    original_commit = saved["history"]["commit"]
    path = __import__("pathlib").Path(saved["path"])
    path.write_bytes(path.read_bytes().replace(b"old first line", b"new first line"))
    result = bank.read(saved["id"])
    history = result["history"]
    current_commit = bank.history.command("rev-parse", "HEAD").stdout.strip()
    assert history["commit"] == current_commit
    assert {item["commit"] for item in history["attributions"]} == {original_commit, current_commit}
    assert history["text_changed_at"] == history["attributions"][0]["text_changed_at"]

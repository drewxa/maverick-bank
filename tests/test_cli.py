import json
import os
import subprocess
import sys


def command(*arguments, env=None):
    return subprocess.run(
        [sys.executable, "-m", "maverick_bank", *map(str, arguments)],
        capture_output=True,
        encoding="utf-8",
        env=env,
        timeout=45,
    )


def test_cli_onboarding_capture_recall_and_diagnosis(tmp_path):
    root = tmp_path / "Моя память with spaces"
    initialized = command("init", "--bank", root)
    assert initialized.returncode == 0, initialized.stderr
    captured = command(
        "remember",
        "--bank",
        root,
        "--title",
        "Database",
        "--body",
        "Use SQLite locally",
        "--source",
        "user:acceptance",
    )
    assert captured.returncode == 0, captured.stderr
    note = json.loads(captured.stdout)
    recalled = command("search", "--bank", root, "SQLite")
    assert recalled.returncode == 0, recalled.stderr
    assert json.loads(recalled.stdout)["results"][0]["id"] == note["id"]
    read = command("read", "--bank", root, note["id"])
    assert json.loads(read.stdout)["body"] == "Use SQLite locally"
    diagnosed = command("doctor", "--bank", root)
    assert diagnosed.returncode == 0, diagnosed.stderr
    assert json.loads(diagnosed.stdout)["checks"]["fts5"] is True


def test_cli_reports_uninitialized_bank_and_does_not_traceback(tmp_path):
    result = command("search", "--bank", tmp_path / "missing", "x")
    assert result.returncode == 2
    assert "init" in result.stderr
    assert "Traceback" not in result.stderr


def test_environment_selects_bank_without_modifying_other_banks(tmp_path):
    root = tmp_path / "selected"
    env = {**os.environ, "MAVERICK_BANK_HOME": str(root)}
    assert command("init", env=env).returncode == 0
    assert json.loads(command("status", env=env).stdout)["root"] == str(root.resolve())

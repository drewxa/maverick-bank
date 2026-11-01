import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]


def test_platform_installer_help_does_not_install_or_require_prerequisites(tmp_path):
    if sys.platform == "win32":
        shell = shutil.which("powershell")
        command = [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT / "scripts/install.ps1"),
            "-Help",
        ]
    else:
        command = ["sh", str(PROJECT / "scripts/install.sh"), "--help"]
    result = subprocess.run(
        command, capture_output=True, encoding="utf-8", timeout=30, cwd=tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert "source" in result.stdout.lower()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.installer
def test_real_installer_is_idempotent_and_uses_isolated_profiles(tmp_path):
    if not os.environ.get("MAVERICK_TEST_INSTALLERS"):
        pytest.skip("Explicit opt-in: installer provisions an isolated uv tool environment")
    uv = shutil.which("uv")
    if not uv:
        pytest.skip("uv required for this opt-in installer trial")
    home = tmp_path / "Colleague profile with spaces"
    home.mkdir()
    bank = home / "Моя память"
    bin_dir = home / "tools-bin"
    env = {
        **os.environ,
        "HOME": str(home),
        "USERPROFILE": str(home),
        "CODEX_HOME": str(home / ".codex"),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "UV_TOOL_DIR": str(home / "tools"),
        "UV_TOOL_BIN_DIR": str(bin_dir),
        "MAVERICK_BANK_HOME": str(bank),
        "PYTHONUTF8": "1",
    }
    if sys.platform == "win32":
        shell = shutil.which("powershell")
        command = [
            shell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT / "scripts/install.ps1"),
            "-Source",
            str(PROJECT),
            "-Clients",
            "codex,claude",
            "-Bank",
            str(bank),
            "-Python",
            sys.executable,
        ]
        executable = bin_dir / "maverick-bank.exe"
    else:
        command = [
            "sh",
            str(PROJECT / "scripts/install.sh"),
            "--source",
            str(PROJECT),
            "--clients",
            "codex",
            "claude",
            "--bank",
            str(bank),
            "--python",
            sys.executable,
        ]
        executable = bin_dir / "maverick-bank"
    first = subprocess.run(command, env=env, capture_output=True, encoding="utf-8", timeout=300)
    assert first.returncode == 0, first.stdout + first.stderr
    assert executable.is_file()
    second = subprocess.run(command, env=env, capture_output=True, encoding="utf-8", timeout=300)
    assert second.returncode == 0, second.stdout + second.stderr
    saved = subprocess.run(
        [
            str(executable),
            "remember",
            "--title",
            "Onboarding",
            "--body",
            "Put the next action first",
            "--source",
            "user:acceptance",
        ],
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert saved.returncode == 0, saved.stderr
    result = subprocess.run(
        [str(executable), "search", "next action"],
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert json.loads(result.stdout)["results"][0]["id"] == json.loads(saved.stdout)["id"]
    removed = subprocess.run(
        [str(executable), "uninstall", "--clients", "codex", "claude"],
        env=env,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert removed.returncode == 0, removed.stderr
    assert list((bank / "notes").glob("*.md"))

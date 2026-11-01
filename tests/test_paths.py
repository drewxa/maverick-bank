import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest
from test_bank import bank_class


@pytest.mark.parametrize(
    "bad", ["../outside", "/etc/passwd", "C:\\private", "a:b", "..\\outside", "\\\\server\\share"]
)
def test_memory_identifier_cannot_be_a_filesystem_escape(tmp_path, bad):
    bank = bank_class().initialize(tmp_path / "bank")
    with pytest.raises(ValueError):
        bank.read(bad)


def test_symlink_note_is_never_followed(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    outside = tmp_path / "private.md"
    outside.write_text("Private outside content", encoding="utf-8")
    link = bank.root / "notes" / "escape.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("OS denies symlink creation for this account")
    assert bank.search("Private")["results"] == []
    assert any(i["code"] == "unsafe_path" for i in bank.audit()["issues"])


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior")
def test_windows_junction_is_skipped_before_descending_into_external_tree(tmp_path):
    bank = bank_class().initialize(tmp_path / "bank")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "private.md").write_text("External private fixture", encoding="utf-8")
    junction = bank.root / "notes" / "linked-folder"
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(junction), str(outside)], capture_output=True
    )
    if result.returncode:
        pytest.skip("This Windows account cannot create test junctions")
    assert bank.search("private")["results"] == []
    assert any(
        i["code"] == "unsafe_path" and i.get("path") == str(junction)
        for i in bank.audit()["issues"]
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission semantics")
def test_new_bank_directory_is_private_without_chmod_existing_directory():
    # WSL workspaces may be on NTFS; test POSIX permissions on the native temp filesystem.
    with tempfile.TemporaryDirectory(prefix="maverick-permissions-") as temporary:
        root = Path(temporary)
        bank = bank_class().initialize(root / "private-bank")
        assert stat.S_IMODE(bank.root.stat().st_mode) & 0o077 == 0
        existing = root / "existing-bank"
        existing.mkdir(mode=0o755)
        existing.chmod(0o755)
        bank_class().initialize(existing)
        assert stat.S_IMODE(existing.stat().st_mode) == 0o755

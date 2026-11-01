import importlib.util
import zipfile
from pathlib import Path

import pytest


def test_release_archive_contains_installable_source_not_private_state(tmp_path):
    source = Path(__file__).resolve().parents[1] / "scripts/package_release.py"
    if not source.exists():
        pytest.fail("Release packager is not implemented")
    spec = importlib.util.spec_from_file_location("release_packager", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "project"
    (project / "src/maverick_bank").mkdir(parents=True)
    (project / "src/maverick_bank/__init__.py").write_text("", encoding="utf-8")
    (project / "scripts").mkdir()
    (project / "scripts/install.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname="maverick-bank"\nversion="0.1.0"\n', encoding="utf-8"
    )
    (project / "README.md").write_text("Fixture readme", encoding="utf-8")
    (project / ".model-cache").mkdir()
    (project / ".model-cache/private.md").write_text("private fixture", encoding="utf-8")
    first = module.package(project)
    before = first.read_bytes()
    assert module.package(project).read_bytes() == before
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert "maverick-bank-0.1.0/pyproject.toml" in names
        assert "maverick-bank-0.1.0/scripts/install.sh" in names
        assert not any("private" in name or ".model-cache" in name for name in names)

"""Build a reproducible source ZIP from a positive allowlist, never a home directory."""

from __future__ import annotations

import hashlib
import tomllib
import zipfile
from pathlib import Path

TOP_FILES = {
    "README.md",
    "README.ru.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
}
DIRECTORIES = {"src", "tests", "scripts", "docs", ".github"}
EXTENSIONS = {".py", ".md", ".toml", ".yml", ".yaml", ".sh", ".ps1", ".json"}


def package(root: Path) -> Path:
    root = root.resolve()
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    destination = root / "dist"
    destination.mkdir(exist_ok=True)
    archive_path = destination / f"maverick-bank-{version}.zip"
    files = [
        path
        for path in root.iterdir()
        if path.name in TOP_FILES and path.is_file() and not path.is_symlink()
    ]
    for name in sorted(DIRECTORIES):
        directory = root / name
        if not directory.is_dir() or directory.is_symlink():
            continue
        for path in directory.rglob("*"):
            if (
                path.is_file()
                and path.suffix in EXTENSIONS
                and not path.is_symlink()
                and "__pycache__" not in path.parts
            ):
                if not any(parent.is_symlink() for parent in path.parents if parent != root):
                    files.append(path)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(files):
            name = f"maverick-bank-{version}/{path.relative_to(root).as_posix()}"
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if path.suffix == ".sh" else 0o100644) << 16
            archive.writestr(info, path.read_bytes())
    artifacts = sorted(
        path
        for path in destination.iterdir()
        if path.suffix in {".whl", ".gz", ".zip"} and path.is_file()
    )
    checksums = "".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n"
        for path in artifacts
    )
    (destination / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    return archive_path


if __name__ == "__main__":
    print(package(Path(__file__).resolve().parents[1]))

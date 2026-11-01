"""Snapshots in an isolated, hook-free Git repository; never the user's index."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import UTC
from pathlib import Path

from .notes import Note, digest
from .paths import atomic_bytes, atomic_text, confined, linked


class History:
    def __init__(self, state: Path, enabled: bool):
        self.state = state
        self.root = confined(state, "history")
        self.enabled = enabled

    def available(self) -> bool:
        return shutil.which("git") is not None

    def command(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        if not self.available():
            raise ValueError(
                "Git is required for versioned capture. Install Git or explicitly set git_enabled=false."
            )
        empty_config = confined(self.state, "empty-git-config")
        if not empty_config.exists():
            atomic_text(empty_config, "")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": str(empty_config),
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_LITERAL_PATHSPECS": "1",
            }
        )
        command = [
            "git",
            "-c",
            f"safe.directory={self.root.as_posix()}",
            "-c",
            "user.name=Maverick Bank",
            "-c",
            "user.email=memory@localhost",
            "-c",
            "commit.gpgSign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.quotePath=false",
            "-C",
            str(self.root),
            *args,
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f"Local Git failed; memory is preserved: {exc}") from exc
        if check and result.returncode:
            raise ValueError(
                f"Local Git failed; memory is preserved: {result.stderr.strip()[:800]}"
            )
        return result

    def snapshot(self, notes: dict[str, Note]) -> str | None:
        if not self.enabled:
            return None
        if not self.available():
            raise ValueError(
                "Git is required for versioned capture. Install Git or set git_enabled=false."
            )
        self.root.mkdir(exist_ok=True)
        if linked(self.root / ".git"):
            raise ValueError("Linked Git metadata is not supported")
        if not (self.root / ".git").exists():
            self.command("init", "--quiet", "--template=", "--initial-branch=main")
        wanted = set()
        for note in notes.values():
            target = confined(self.root, note.relative)
            wanted.add(target)
            if not target.exists() or digest(target.read_bytes()) != note.revision:
                atomic_bytes(target, note.raw)
        for folder, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if d != ".git" and not linked(Path(folder) / d)]
            for filename in files:
                candidate = Path(folder) / filename
                if candidate not in wanted:
                    confined(self.root, candidate.relative_to(self.root).as_posix()).unlink()
        self.command("add", "--all", "--", ".")
        changed = self.command("diff", "--cached", "--quiet", check=False)
        if changed.returncode == 1:
            self.command("commit", "--quiet", "-m", "Snapshot memory changes")
        elif changed.returncode:
            raise ValueError("Unable to inspect pending local history")
        head = self.command("rev-parse", "HEAD", check=False)
        return head.stdout.strip() if head.returncode == 0 else None

    def attribution(self, note: Note, start: int, end: int) -> dict:
        result = {
            "commit": None,
            "text_changed_at": None,
            "meaning": "Git text attribution, not last verification or real-world validity",
        }
        if not self.enabled or not self.available() or not (self.root / ".git").exists():
            return result
        snapshot = confined(self.root, note.relative)
        if not snapshot.exists() or digest(snapshot.read_bytes()) != note.revision:
            return {**result, "state": "snapshot_pending"}
        output = self.command(
            "blame", "--line-porcelain", "-L", f"{start},{end}", "--", note.relative, check=False
        )
        if output.returncode:
            return result
        attributions = []
        current = None
        for line in output.stdout.splitlines():
            parts = line.split()
            if (
                not line.startswith("\t")
                and len(parts) in {3, 4}
                and len(parts[0]) == 40
                and all(c in "0123456789abcdef" for c in parts[0])
            ):
                current = {
                    "commit": parts[0],
                    "line_start": int(parts[2]),
                    "line_end": int(parts[2]),
                }
            elif line.startswith("committer-time ") and current is not None:
                from datetime import datetime

                current["text_changed_at"] = datetime.fromtimestamp(int(parts[1]), UTC).isoformat()
            elif line.startswith("\t") and current is not None:
                if (
                    attributions
                    and attributions[-1]["commit"] == current["commit"]
                    and attributions[-1]["line_end"] + 1 == current["line_start"]
                ):
                    attributions[-1]["line_end"] = current["line_end"]
                else:
                    attributions.append(current)
                current = None
        if attributions:
            result.update(
                {
                    "commit": attributions[0]["commit"],
                    "text_changed_at": attributions[0]["text_changed_at"],
                    "attributions": attributions,
                    "meaning": "Primary attribution is the first source line; attributions lists the other line groups. Text history is not verification or validity.",
                }
            )
        return result

    def log(self, limit: int = 20) -> dict:
        if not self.enabled or not (self.root / ".git").exists():
            return {"commits": [], "enabled": self.enabled}
        result = self.command(
            "log", f"-{min(max(limit, 1), 100)}", "--format=%H%x09%cI%x09%s", check=False
        )
        commits = (
            [
                dict(zip(("commit", "at", "message"), line.split("\t", 2), strict=True))
                for line in result.stdout.splitlines()
            ]
            if result.returncode == 0
            else []
        )
        return {"commits": commits, "enabled": True, "repository": str(self.root)}

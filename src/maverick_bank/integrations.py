"""Owned, reversible local client configuration. Never starts an agent process."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import tomlkit
from filelock import FileLock, Timeout

SERVER = "maverick-bank"
START = "<!-- maverick-bank:start -->"
END = "<!-- maverick-bank:end -->"


class IntegrationError(ValueError):
    """An unsafe or ambiguous client configuration was left untouched."""


@dataclass
class _Change:
    path: Path
    before: bytes | None
    after: bytes | None
    backup: Path | None = None


def _read(path: Path) -> bytes | None:
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        raise IntegrationError(f"Refusing linked integration file: {path}")
    if path.exists():
        if not path.is_file():
            raise IntegrationError(f"Invalid integration file: {path}")
        return path.read_bytes()
    return None


def _hash(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def _text(data: bytes | None, path: Path) -> str:
    try:
        return data.decode("utf-8") if data is not None else ""
    except UnicodeDecodeError as exc:
        raise IntegrationError(f"Invalid UTF-8 integration file: {path}") from exc


def _json(text: str, path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key {key}")
            result[key] = value
        return result

    try:
        data = json.loads(text, object_pairs_hook=unique) if text else {}
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        return data
    except ValueError as exc:
        raise IntegrationError(f"Malformed JSON configuration: {path}: {exc}") from exc


def _config(data: bytes | None, path: Path, kind: str):
    text = _text(data, path)
    if kind == "json":
        document = _json(text, path)
        name = "mcpServers"
    else:
        try:
            document = tomlkit.parse(text)
        except ValueError as exc:
            raise IntegrationError(f"Malformed TOML configuration: {path}: {exc}") from exc
        name = "mcp_servers"
    servers = document.get(name, {})
    if not isinstance(servers, Mapping):
        raise IntegrationError(f"Invalid {name} object: {path}")
    return document, name, servers


def _dump(document, kind: str) -> bytes:
    if kind == "json":
        return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return tomlkit.dumps(document).encode("utf-8")


def _atomic(path: Path, data: bytes | None) -> None:
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".mb-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(name, path.stat().st_mode & 0o777)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def _commit(changes: list[_Change]) -> list[str]:
    """Preflight every target; roll back ordinary write failures, preserving later edits."""
    for change in changes:
        if _read(change.path) != change.before:
            raise IntegrationError(f"Integration file changed during installation: {change.path}")
    applied = []
    backups = []
    try:
        for change in changes:
            if change.before == change.after:
                continue
            if change.before is not None:
                backup = change.backup or change.path.with_name(f".mb-{uuid.uuid4().hex}.bak")
                _atomic(backup, change.before)
                backups.append(str(backup))
            _atomic(change.path, change.after)
            applied.append(change)
    except OSError:
        for change in reversed(applied):
            if _read(change.path) == change.after:
                _atomic(change.path, change.before)
        raise
    return backups


def _options(bank_root, clients, scope, project, home, codex_home, python):
    if not clients or any(client not in {"codex", "claude"} for client in clients):
        raise IntegrationError("Select one or both clients: codex, claude")
    if scope not in {"user", "project"} or (scope == "project" and project is None):
        raise IntegrationError(
            "Scope must be user or project; project scope requires a project path"
        )
    executable = python or sys.executable
    if not Path(executable).is_absolute() or "\x00" in executable or "\n" in executable:
        raise IntegrationError("Python executable must be an absolute executable path")
    bank = Path(bank_root).expanduser().resolve()
    user_home = Path(home).expanduser().resolve() if home is not None else Path.home().resolve()
    codex_dir = (
        Path(codex_home or os.environ.get("CODEX_HOME") or user_home / ".codex")
        .expanduser()
        .resolve()
    )
    project_dir = Path(project).expanduser().resolve() if project is not None else None
    state = bank / ".maverick"
    if state.is_symlink() or getattr(state, "is_junction", lambda: False)():
        raise IntegrationError(f"Refusing linked integration state: {state}")
    return bank, list(dict.fromkeys(clients)), user_home, codex_dir, project_dir, executable


def _destinations(client, scope, home, codex_home, project):
    base = home if scope == "user" else project
    if client == "codex":
        config = (codex_home if scope == "user" else base / ".codex") / "config.toml"
        instruction_dir = codex_home if scope == "user" else base
        override = instruction_dir / "AGENTS.override.md"
        # Codex reads only the first nonempty global/project guidance file.
        instructions = override if _read(override) else instruction_dir / "AGENTS.md"
        skill = base / ".agents/skills/maverick-bank/SKILL.md"
        return config, "toml", instructions, skill
    custom_claude_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    claude_dir = (
        Path(custom_claude_dir).expanduser().resolve()
        if scope == "user" and custom_claude_dir
        else base / ".claude"
    )
    config = (
        (claude_dir / ".claude.json" if custom_claude_dir else home / ".claude.json")
        if scope == "user"
        else base / ".mcp.json"
    )
    # Unconditional rules auto-load, without creating CLAUDE.md and thereby
    # suppressing a project's existing AGENTS.md discovery in current Claude.
    instructions = claude_dir / "rules/maverick-bank.md"
    return config, "json", instructions, claude_dir / "skills/maverick-bank/SKILL.md"


def _key(client, scope, config):
    return f"{client}:{scope}:{_hash(str(config).encode('utf-8'))}"


def _manifest(path: Path):
    data = _read(path)
    if data is None:
        return {"version": 1, "installations": {}}, None
    document = _json(_text(data, path), path)
    if document.get("version") != 1 or not isinstance(document.get("installations"), dict):
        raise IntegrationError(f"Invalid integrations manifest: {path}")
    for key, installation in document["installations"].items():
        if (
            not isinstance(installation, dict)
            or installation.get("client") not in {"codex", "claude"}
            or installation.get("scope") not in {"user", "project"}
        ):
            raise IntegrationError(f"Invalid installation in integrations manifest: {path}")
        artifacts = installation.get("artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 3:
            raise IntegrationError(f"Invalid artifacts in integrations manifest: {path}")
        for artifact in artifacts:
            if not isinstance(artifact, dict) or not {
                "path",
                "kind",
                "before_hash",
                "after_hash",
                "backup",
            }.issubset(artifact):
                raise IntegrationError(f"Invalid artifact in integrations manifest: {path}")
            if (
                not isinstance(artifact["path"], str)
                or not Path(artifact["path"]).is_absolute()
                or artifact["kind"] not in {"json", "toml", "block", "skill"}
            ):
                raise IntegrationError(
                    f"Invalid artifact path or kind in integrations manifest: {path}"
                )
            if artifact["kind"] in {"json", "toml"} and not isinstance(artifact.get("entry"), dict):
                raise IntegrationError(f"Invalid server entry in integrations manifest: {path}")
            if artifact["kind"] == "block" and not isinstance(artifact.get("block"), str):
                raise IntegrationError(
                    f"Invalid instruction block in integrations manifest: {path}"
                )
        if key != _key(installation["client"], installation["scope"], Path(artifacts[0]["path"])):
            raise IntegrationError(f"Invalid installation key in integrations manifest: {path}")
    return document, data


def _block(bank: Path) -> bytes:
    return (
        f"{START}\n"
        "Maverick Bank is available through the maverick-bank MCP server.\n"
        f"Bank directory: {json.dumps(str(bank), ensure_ascii=False)}.\n"
        "Once per session, call memory_status and apply its capture_policy before saving. "
        "At the start of a task, search relevant prior preferences, decisions and lessons; "
        "read matching evidence before applying it. Use the maverick-bank skill for capture and recall. "
        "Current user instructions take precedence. Record durable explicit requests and clear corrections "
        "with their source; keep guesses unverified. Exclude secrets and temporary task lists. "
        "Report used memory IDs and revisions only when they affected the answer; "
        "offered/read/declared_used events do not prove model influence.\n"
        "When normal search reports a new maintenance scan, review relevant findings at a convenient pause; "
        "use memory_audit pagination and never automatically adjudicate truth.\n"
        f"{END}\n"
    ).encode()


def _artifact(path, kind, before, after, **extra):
    backup = path.with_name(f".mb-{uuid.uuid4().hex}.bak") if before is not None else None
    entry = {
        "path": str(path),
        "kind": kind,
        "before_hash": _hash(before),
        "after_hash": _hash(after),
        "backup": str(backup) if backup else None,
        **extra,
    }
    return entry, _Change(path, before, after, backup)


def _check_owned(artifact, data):
    path = Path(artifact["path"])
    kind = artifact["kind"]
    if kind in {"toml", "json"}:
        _, _, servers = _config(data, path, kind)
        if servers.get(SERVER) != artifact["entry"]:
            raise IntegrationError(f"Owned server configuration modified or missing: {path}")
    elif kind == "block":
        block = artifact["block"].encode("utf-8")
        if (
            data is None
            or data.count(block) != 1
            or data.count(START.encode()) != 1
            or data.count(END.encode()) != 1
        ):
            raise IntegrationError(f"Owned instruction block modified or missing: {path}")
    elif kind == "skill":
        if _hash(data) != artifact["after_hash"]:
            raise IntegrationError(f"Owned skill modified or missing: {path}")
    else:
        raise IntegrationError(f"Invalid artifact kind in integrations manifest: {kind}")


def install_clients(
    bank_root: Path,
    clients: list[str],
    scope: str = "user",
    project: Path | None = None,
    home: Path | None = None,
    codex_home: Path | None = None,
    python: str | None = None,
) -> dict:
    """Install only unclaimed entries, or verify an exact owned reinstall."""
    bank, clients, home, codex_home, project, executable = _options(
        bank_root, clients, scope, project, home, codex_home, python
    )
    state = bank / ".maverick"
    state.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(state / "integrations.lock"), timeout=10):
            manifest_path = state / "integrations.json"
            manifest, manifest_before = _manifest(manifest_path)
            changes = []
            results = []
            skill_data = (
                files("maverick_bank")
                .joinpath("resources/skills/maverick-bank/SKILL.md")
                .read_bytes()
            )
            for client in clients:
                config, kind, instructions, skill = _destinations(
                    client, scope, home, codex_home, project
                )
                key = _key(client, scope, config)
                expected = {
                    "command": executable,
                    "args": ["-m", "maverick_bank", "serve", "--bank", str(bank)],
                }
                if client == "claude":
                    expected = {"type": "stdio", **expected}
                owned = manifest["installations"].get(key)
                if owned is not None:
                    if owned["artifacts"][1]["path"] != str(instructions):
                        raise IntegrationError(
                            "An instruction override shadows installed guidance; uninstall before reinstalling"
                        )
                    for artifact in owned["artifacts"]:
                        _check_owned(artifact, _read(Path(artifact["path"])))
                    if owned["artifacts"][0]["entry"] != expected:
                        raise IntegrationError(
                            "Owned interpreter or bank changed; uninstall before reinstalling"
                        )
                    results.append(
                        {
                            "client": client,
                            "scope": scope,
                            "status": "already-installed",
                            "config": str(config),
                        }
                    )
                    continue
                before = _read(config)
                document, name, servers = _config(before, config, kind)
                if SERVER in servers:
                    raise IntegrationError(
                        f"Server name conflict: {SERVER} already exists and is not owned: {config}"
                    )
                if name not in document:
                    document[name] = tomlkit.table() if kind == "toml" else {}
                document[name][SERVER] = expected
                artifact, change = _artifact(
                    config, kind, before, _dump(document, kind), entry=expected
                )
                artifacts = [artifact]
                changes.append(change)
                instruction_before = _read(instructions)
                instruction_text = _text(instruction_before, instructions)
                if START in instruction_text or END in instruction_text:
                    raise IntegrationError(
                        f"Instruction block conflict; existing block is not owned: {instructions}"
                    )
                block = _block(bank)
                separator = (
                    b"\n\n"
                    if instruction_before and not instruction_before.endswith(b"\n")
                    else b"\n"
                    if instruction_before
                    else b""
                )
                owned_block = separator + block
                artifact, change = _artifact(
                    instructions,
                    "block",
                    instruction_before,
                    (instruction_before or b"") + owned_block,
                    block=owned_block.decode("utf-8"),
                )
                artifacts.append(artifact)
                changes.append(change)
                if _read(skill) is not None:
                    raise IntegrationError(f"Skill conflict: existing file is not owned: {skill}")
                artifact, change = _artifact(skill, "skill", None, skill_data)
                artifacts.append(artifact)
                changes.append(change)
                manifest["installations"][key] = {
                    "client": client,
                    "scope": scope,
                    "artifacts": artifacts,
                }
                results.append(
                    {"client": client, "scope": scope, "status": "installed", "config": str(config)}
                )
            if changes:
                changes.append(_Change(manifest_path, manifest_before, _dump(manifest, "json")))
            backups = _commit(changes)
            return {
                "changed": bool(changes),
                "clients": results,
                "backups": backups,
                "restart_required": bool(changes),
                "manifest": str(manifest_path),
            }
    except Timeout as exc:
        raise IntegrationError(
            "Client integration is busy; retry when the other installer finishes"
        ) from exc


def _remove_artifact(artifact):
    path = Path(artifact["path"])
    data = _read(path)
    _check_owned(artifact, data)
    # Byte-exact roundtrip if nobody changed the containing file. Backups keep
    # credentials alongside their original config, never in the bank manifest.
    if _hash(data) == artifact["after_hash"]:
        if artifact["before_hash"] is None:
            return _Change(path, data, None)
        backup_path = Path(artifact["backup"])
        backup = _read(backup_path)
        if _hash(backup) != artifact["before_hash"]:
            raise IntegrationError(f"Original integration backup changed or missing: {backup_path}")
        return _Change(path, data, backup)
    if artifact["kind"] == "block":
        remaining = data.replace(artifact["block"].encode("utf-8"), b"", 1)
        return _Change(path, data, remaining)
    document, name, _ = _config(data, path, artifact["kind"])
    del document[name][SERVER]
    if not document[name]:
        del document[name]
    return _Change(path, data, _dump(document, artifact["kind"]))


def uninstall_clients(
    bank_root: Path,
    clients: list[str],
    scope: str = "user",
    project: Path | None = None,
    home: Path | None = None,
    codex_home: Path | None = None,
    python: str | None = None,
) -> dict:
    """Remove matching owned artifacts; keep bank data and all backups."""
    bank, clients, home, codex_home, project, _ = _options(
        bank_root, clients, scope, project, home, codex_home, python
    )
    manifest_path = bank / ".maverick/integrations.json"
    if not manifest_path.exists():
        return {"changed": False, "clients": [], "backups": [], "restart_required": False}
    try:
        with FileLock(str(manifest_path.parent / "integrations.lock"), timeout=10):
            manifest, manifest_before = _manifest(manifest_path)
            changes = []
            results = []
            for client in clients:
                config, _, _, _ = _destinations(client, scope, home, codex_home, project)
                key = _key(client, scope, config)
                owned = manifest["installations"].get(key)
                if owned is None:
                    results.append({"client": client, "scope": scope, "status": "not-installed"})
                    continue
                changes.extend(_remove_artifact(artifact) for artifact in owned["artifacts"])
                del manifest["installations"][key]
                results.append({"client": client, "scope": scope, "status": "uninstalled"})
            if changes:
                changes.append(_Change(manifest_path, manifest_before, _dump(manifest, "json")))
            backups = _commit(changes)
            return {
                "changed": bool(changes),
                "clients": results,
                "backups": backups,
                "restart_required": bool(changes),
            }
    except Timeout as exc:
        raise IntegrationError(
            "Client integration is busy; retry when the other installer finishes"
        ) from exc


def inspect_clients(bank_root: Path) -> dict:
    """Read owned registration health without exposing foreign settings or starting hosts.

    ``registered`` means that the manifest records installations. ``status`` says
    whether their actual files and runtime are still valid; it is not host recall.
    """
    empty = {"status": "not_installed", "registered": False, "clients": [], "issues": []}
    state = Path(bank_root).expanduser().resolve() / ".maverick"
    try:
        if state.is_symlink() or getattr(state, "is_junction", lambda: False)():
            raise IntegrationError("Linked integration state")
        manifest, _ = _manifest(state / "integrations.json")
    except (ValueError, OSError):
        return {
            **empty,
            "status": "attention",
            "issues": [
                "Integration ownership manifest is invalid or unreadable; reconcile it before reinstalling."
            ],
        }
    installations = manifest["installations"]
    if not installations:
        return empty
    clients = []
    issues = []
    descriptions = {
        "json": "Owned MCP configuration is missing, modified or invalid.",
        "toml": "Owned MCP configuration is missing, modified or invalid.",
        "block": "Owned startup guidance is missing, modified or invalid.",
        "skill": "Owned skill is missing, modified or invalid.",
    }
    for key in sorted(installations):
        installation = installations[key]
        client_issues = []
        for artifact in installation["artifacts"]:
            try:
                _check_owned(artifact, _read(Path(artifact["path"])))
            except (ValueError, OSError):
                # Parser diagnostics can contain unrelated user keys. Return only
                # our own artifact category, never the foreign document or error.
                client_issues.append(descriptions[artifact["kind"]])
        executable = installation["artifacts"][0].get("entry", {}).get("command")
        try:
            valid_runtime = (
                isinstance(executable, str)
                and Path(executable).is_absolute()
                and Path(executable).is_file()
            )
        except (ValueError, OSError):
            valid_runtime = False
        if not valid_runtime:
            client_issues.append(
                "Registered runtime executable is missing or invalid; reinstall the runtime."
            )
        client = installation["client"]
        scope = installation["scope"]
        clients.append(
            {
                "client": client,
                "scope": scope,
                "status": "attention" if client_issues else "ready",
                "issues": client_issues,
            }
        )
        issues.extend(f"{client} ({scope}): {issue}" for issue in client_issues)
    return {
        "status": "attention" if issues else "ready",
        "registered": True,
        "clients": clients,
        "issues": issues,
    }

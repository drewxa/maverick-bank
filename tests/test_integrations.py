"""Client configuration tests use temporary homes; no authenticated host is invoked."""

import importlib
import json
import sys
import tomllib
from pathlib import Path

import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    home = tmp_path / "Пользователь with spaces"
    home.mkdir()
    bank = tmp_path / "Память bank"
    bank.mkdir()
    return bank, home


def api():
    return importlib.import_module("maverick_bank.integrations")


def test_install_preserves_foreign_configuration_and_reinstalls_without_writes(env):
    bank, home = env
    codex = home / ".codex"
    codex.mkdir()
    original = '# retained comment\nmodel = "test"\n[mcp_servers.other]\ncommand = "other"\n'
    (codex / "config.toml").write_text(original, encoding="utf-8")
    claude = {"theme": "dark", "mcpServers": {"other": {"command": "other"}}}
    (home / ".claude.json").write_text(json.dumps(claude), encoding="utf-8")
    args = dict(bank_root=bank, clients=["codex", "claude"], home=home)
    first = api().install_clients(**args)
    config = tomllib.loads((codex / "config.toml").read_text(encoding="utf-8"))
    assert config["model"] == "test"
    assert config["mcp_servers"]["other"] == {"command": "other"}
    assert config["mcp_servers"]["maverick-bank"] == {
        "command": sys.executable,
        "args": ["-m", "maverick_bank", "serve", "--bank", str(bank.resolve())],
    }
    assert "# retained comment" in (codex / "config.toml").read_text(encoding="utf-8")
    registered = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert registered["theme"] == "dark"
    assert registered["mcpServers"]["other"] == {"command": "other"}
    assert registered["mcpServers"]["maverick-bank"]["type"] == "stdio"
    assert first["changed"]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in home.rglob("*") if p.is_file()}
    assert api().install_clients(**args)["changed"] is False
    assert before == {
        p: (p.read_bytes(), p.stat().st_mtime_ns) for p in home.rglob("*") if p.is_file()
    }


def test_uninstall_restores_original_bytes_and_keeps_memory(env):
    bank, home = env
    (bank / "notes").mkdir()
    note = bank / "notes" / "keep.md"
    note.write_text("durable memory")
    (home / ".codex").mkdir()
    instruction = home / ".codex" / "AGENTS.md"
    instruction.write_bytes(b"User guidance\r\n")
    config = home / ".codex" / "config.toml"
    config.write_bytes(b'# original\r\nmodel = "test"\r\n')
    original = config.read_bytes()
    args = dict(bank_root=bank, clients=["codex", "claude"], home=home)
    api().install_clients(**args)
    assert (home / ".agents/skills/maverick-bank/SKILL.md").exists()
    assert (home / ".claude/skills/maverick-bank/SKILL.md").exists()
    assert api().uninstall_clients(**args)["changed"]
    assert config.read_bytes() == original
    assert instruction.read_bytes() == b"User guidance\r\n"
    assert not (home / ".claude.json").exists()
    assert not (home / ".agents/skills/maverick-bank/SKILL.md").exists()
    assert note.read_text(encoding="utf-8") == "durable memory"
    assert api().uninstall_clients(**args)["changed"] is False


@pytest.mark.parametrize(
    "client,relative,text",
    [
        ("codex", ".codex/config.toml", '[mcp_servers.maverick-bank]\ncommand="foreign"\n'),
        ("claude", ".claude.json", '{"mcpServers":{"maverick-bank":{"command":"foreign"}}}'),
    ],
)
def test_foreign_server_name_is_not_claimed_or_overwritten(env, client, relative, text):
    bank, home = env
    path = home / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    with pytest.raises(ValueError, match="conflict|already|owned"):
        api().install_clients(bank, [client], home=home)
    assert path.read_text(encoding="utf-8") == text
    assert not (bank / ".maverick/integrations.json").exists()


@pytest.mark.parametrize(
    "relative,text",
    [
        (".codex/config.toml", "[broken"),
        (".claude.json", "{bad"),
        (".claude.json", '{"mcpServers":[]}'),
    ],
)
def test_preflight_refuses_malformed_config_without_partial_client_install(env, relative, text):
    bank, home = env
    target = home / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    with pytest.raises(ValueError, match="[Mm]alformed|[Ii]nvalid"):
        api().install_clients(bank, ["codex", "claude"], home=home)
    assert target.read_text(encoding="utf-8") == text
    assert not (home / ".agents/skills/maverick-bank/SKILL.md").exists()


def test_uninstall_keeps_unrelated_edits_and_refuses_modified_owned_blocks(env):
    bank, home = env
    args = dict(bank_root=bank, clients=["codex", "claude"], home=home)
    api().install_clients(**args)
    config = home / ".codex/config.toml"
    with config.open("a", encoding="utf-8") as stream:
        stream.write('\n[project]\nname = "new"\n')
    instruction = home / ".codex/AGENTS.md"
    original_instruction = instruction.read_text(encoding="utf-8")
    instruction.write_text(
        original_instruction.replace("Maverick Bank", "Changed Bank"), encoding="utf-8", newline=""
    )
    before = config.read_bytes()
    with pytest.raises(ValueError, match="modified|changed"):
        api().uninstall_clients(**args)
    assert config.read_bytes() == before
    instruction.write_text(original_instruction + "\nUser addition\n", encoding="utf-8", newline="")
    api().uninstall_clients(**args)
    remaining = tomllib.loads(config.read_text(encoding="utf-8"))
    assert remaining["project"]["name"] == "new"
    assert "maverick-bank" not in remaining.get("mcp_servers", {})
    assert instruction.read_text(encoding="utf-8") == "\nUser addition\n"


def test_modified_owned_server_and_skill_are_not_removed(env):
    bank, home = env
    args = dict(bank_root=bank, clients=["claude"], home=home)
    api().install_clients(**args)
    skill = home / ".claude/skills/maverick-bank/SKILL.md"
    original = skill.read_bytes()
    skill.write_text("human revision")
    with pytest.raises(ValueError, match="modified|changed"):
        api().uninstall_clients(**args)
    skill.write_bytes(original)
    path = home / ".claude.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["mcpServers"]["maverick-bank"]["args"].append("--human-change")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="modified|changed"):
        api().install_clients(**args)
    with pytest.raises(ValueError, match="modified|changed"):
        api().uninstall_clients(**args)
    assert skill.exists()


def test_project_scope_stays_in_project_and_respects_codex_override(env):
    bank, home = env
    project = home / "repo с пробелами"
    (project / ".codex").mkdir(parents=True)
    override = project / "AGENTS.override.md"
    override.write_text("Higher priority guidance\n")
    args = dict(
        bank_root=bank, clients=["codex", "claude"], scope="project", project=project, home=home
    )
    api().install_clients(**args)
    assert (project / ".codex/config.toml").exists()
    assert (project / ".mcp.json").exists()
    assert (project / ".agents/skills/maverick-bank/SKILL.md").exists()
    assert (project / ".claude/skills/maverick-bank/SKILL.md").exists()
    assert "Maverick Bank" in override.read_text(encoding="utf-8")
    assert not (project / "AGENTS.md").exists()
    assert not (home / ".codex").exists()
    api().uninstall_clients(**args)
    assert override.read_text(encoding="utf-8") == "Higher priority guidance\n"


def test_codex_home_environment_and_explicit_override(env, monkeypatch):
    bank, home = env
    custom = home / "custom codex"
    monkeypatch.setenv("CODEX_HOME", str(custom))
    api().install_clients(bank, ["codex"], home=home)
    assert (custom / "config.toml").exists()
    assert (custom / "AGENTS.md").exists()
    assert (home / ".agents/skills/maverick-bank/SKILL.md").exists()
    api().uninstall_clients(bank, ["codex"], home=home)
    explicit = home / "explicit codex"
    api().install_clients(bank, ["codex"], home=home, codex_home=explicit)
    assert (explicit / "config.toml").exists()


def test_foreign_identical_entry_still_requires_ownership(env):
    bank, home = env
    api().install_clients(bank, ["claude"], home=home)
    (bank / ".maverick/integrations.json").unlink()
    with pytest.raises(ValueError, match="conflict|already|owned"):
        api().install_clients(bank, ["claude"], home=home)


def test_options_and_relative_python_are_rejected_without_mutations(env):
    bank, home = env
    for kwargs in [
        {"clients": ["unknown"]},
        {"clients": []},
        {"clients": ["codex"], "scope": "bad"},
        {"clients": ["codex"], "scope": "project"},
        {"clients": ["codex"], "python": "python"},
    ]:
        with pytest.raises(ValueError):
            api().install_clients(bank, home=home, **kwargs)
    assert list(home.iterdir()) == []


def test_other_bank_cannot_take_over_same_client(env):
    bank, home = env
    api().install_clients(bank, ["codex"], home=home)
    other_bank = bank.parent / "another bank"
    other_bank.mkdir()
    with pytest.raises(ValueError, match="conflict|already|owned"):
        api().install_clients(other_bank, ["codex"], home=home)


def test_explicit_unicode_interpreter_is_one_config_value(env):
    bank, home = env
    executable = str((home / "venv с пробелами" / "python.exe").resolve())
    api().install_clients(bank, ["claude"], home=home, python=executable)
    data = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
    assert data["mcpServers"]["maverick-bank"]["command"] == executable
    assert data["mcpServers"]["maverick-bank"]["args"][-1] == str(bank.resolve())


def test_python_311_path_api_is_supported(env, monkeypatch):
    bank, home = env
    # pathlib.Path.is_junction was introduced in 3.12.
    monkeypatch.delattr(Path, "is_junction", raising=False)
    api().install_clients(bank, ["codex"], home=home)
    assert (home / ".codex/config.toml").exists()


def test_claude_guidance_keeps_existing_instruction_discovery(env):
    bank, home = env
    project = home / "repo"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("Existing shared instruction chain\n")
    api().install_clients(bank, ["claude"], scope="project", project=project, home=home)
    assert agents.read_text(encoding="utf-8") == "Existing shared instruction chain\n"
    assert not (project / "CLAUDE.md").exists()
    assert (project / ".claude/rules/maverick-bank.md").exists()
    api().uninstall_clients(bank, ["claude"], scope="project", project=project, home=home)
    assert not (project / ".claude/rules/maverick-bank.md").exists()
    assert agents.exists()


def test_reinstall_detects_new_override_that_shadows_installed_instructions(env):
    bank, home = env
    api().install_clients(bank, ["codex"], home=home)
    override = home / ".codex/AGENTS.override.md"
    override.write_text("New overriding guidance")
    with pytest.raises(ValueError, match="shadow|override|instruction"):
        api().install_clients(bank, ["codex"], home=home)
    api().uninstall_clients(bank, ["codex"], home=home)
    assert override.read_text(encoding="utf-8") == "New overriding guidance"


def test_failed_write_rolls_back_all_client_files(env, monkeypatch):
    bank, home = env
    module = api()
    real_atomic = module._atomic

    def deny_skill(path, data):
        if path.name == "SKILL.md" and data is not None:
            raise PermissionError("simulated read-only skill destination")
        real_atomic(path, data)

    monkeypatch.setattr(module, "_atomic", deny_skill)
    with pytest.raises(PermissionError):
        module.install_clients(bank, ["codex", "claude"], home=home)
    assert not (home / ".codex/config.toml").exists()
    assert not (home / ".codex/AGENTS.md").exists()
    assert not (bank / ".maverick/integrations.json").exists()


@pytest.mark.parametrize(
    "manifest",
    [
        {"version": 2, "installations": {}},
        {"version": 1, "installations": {"bad": {}}},
    ],
)
def test_malformed_manifest_is_actionable_and_does_not_mutate_clients(env, manifest):
    bank, home = env
    (bank / ".maverick").mkdir()
    (bank / ".maverick/integrations.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest"):
        api().install_clients(bank, ["codex"], home=home)
    assert list(home.iterdir()) == []


def test_config_backup_preserves_original_bytes_and_manifest_omits_credentials(env):
    bank, home = env
    config = home / ".claude.json"
    original = b'{"secretMarker":"private-test-value"}'
    config.write_bytes(original)
    result = api().install_clients(bank, ["claude"], home=home)
    assert any(Path(path).read_bytes() == original for path in result["backups"])
    manifest = (bank / ".maverick/integrations.json").read_text(encoding="utf-8")
    assert "private-test-value" not in manifest


def test_claude_custom_config_directory_is_used_for_all_user_artifacts(env, monkeypatch):
    bank, home = env
    custom = home / "Claude work config"
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(custom))
    api().install_clients(bank, ["claude"], home=home)
    assert (custom / ".claude.json").exists()
    assert (custom / "skills/maverick-bank/SKILL.md").exists()
    assert (custom / "rules/maverick-bank.md").exists()
    assert not (home / ".claude.json").exists()
    assert not (home / ".claude").exists()
    api().uninstall_clients(bank, ["claude"], home=home)
    assert not (custom / ".claude.json").exists()


def test_inspect_clients_distinguishes_healthy_and_cli_only_banks(env):
    bank, home = env
    module = api()
    assert module.inspect_clients(bank) == {
        "status": "not_installed",
        "registered": False,
        "clients": [],
        "issues": [],
    }
    module.install_clients(bank, ["codex", "claude"], home=home)
    result = module.inspect_clients(bank)
    assert result["status"] == "ready"
    assert result["registered"] is True
    assert {entry["client"] for entry in result["clients"]} == {"codex", "claude"}
    assert result["issues"] == []
    module.uninstall_clients(bank, ["codex", "claude"], home=home)
    assert module.inspect_clients(bank)["status"] == "not_installed"


def test_inspect_clients_detects_deleted_config_without_leaking_foreign_settings(env):
    bank, home = env
    module = api()
    module.install_clients(bank, ["codex", "claude"], home=home)
    (home / ".codex/config.toml").unlink()
    claude_config = home / ".claude.json"
    data = json.loads(claude_config.read_text(encoding="utf-8"))
    data["credentials"] = "unrelated-private-test-value"
    claude_config.write_text(json.dumps(data), encoding="utf-8")
    result = module.inspect_clients(bank)
    assert result["status"] == "attention"
    assert any(
        entry["client"] == "codex" and entry["status"] == "attention" for entry in result["clients"]
    )
    assert any(
        entry["client"] == "claude" and entry["status"] == "ready" for entry in result["clients"]
    )
    assert result["issues"]
    assert "unrelated-private-test-value" not in json.dumps(result)


def test_inspect_clients_reports_missing_runtime_without_starting_it(env):
    bank, home = env
    module = api()
    nonexistent = str((home / "deleted runtime/python.exe").resolve())
    module.install_clients(bank, ["codex"], home=home, python=nonexistent)
    result = module.inspect_clients(bank)
    assert result["status"] == "attention"
    assert result["registered"] is True
    assert any(
        "runtime" in issue.lower() or "executable" in issue.lower() for issue in result["issues"]
    )


def test_inspect_clients_reports_modified_owned_guidance_and_skill(env):
    bank, home = env
    module = api()
    module.install_clients(bank, ["claude"], home=home)
    (home / ".claude/rules/maverick-bank.md").write_text("changed instruction")
    (home / ".claude/skills/maverick-bank/SKILL.md").write_text("changed skill")
    result = module.inspect_clients(bank)
    assert result["status"] == "attention"
    assert len(result["issues"]) == 2


def test_inspect_clients_reports_invalid_manifest_without_traceback(env):
    bank, _ = env
    (bank / ".maverick").mkdir()
    (bank / ".maverick/integrations.json").write_text('{"version":99}')
    result = api().inspect_clients(bank)
    assert result["status"] == "attention"
    assert result["registered"] is False
    assert result["issues"]

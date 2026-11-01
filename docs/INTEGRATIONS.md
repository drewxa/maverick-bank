# Claude Code and Codex integrations

Maverick Bank runs a local MCP stdio process. This connection needs no MCP API key, OAuth flow or open port. Your agent client still needs its normal authenticated account. Install the package into a persistent environment before registering it; deleting or moving that environment breaks the registered interpreter path.

The installer registers an absolute executable path and separate arguments:

```json
{
  "command": "/absolute/path/to/venv/bin/python",
  "args": ["-m", "maverick_bank", "serve", "--bank", "/absolute/path/to/bank"]
}
```

On Windows, `command` points to the environment's `Scripts/python.exe`. Spaces and Unicode remain part of each JSON/TOML string. No shell, executable wrapper, PATH lookup or query-time package download is involved. The installer writes configuration directly; neither client CLI needs to be installed to prepare the files. Preparing files alone does not establish a working host connection.

## Files and scopes

| Client and scope | MCP configuration | Skill | Startup guidance |
| --- | --- | --- | --- |
| Codex user | `$CODEX_HOME/config.toml`, default `~/.codex/config.toml` | `~/.agents/skills/maverick-bank/SKILL.md` | `$CODEX_HOME/AGENTS.md` |
| Codex project | `<project>/.codex/config.toml` | `<project>/.agents/skills/maverick-bank/SKILL.md` | `<project>/AGENTS.md` |
| Claude Code user | `~/.claude.json`, top-level `mcpServers` | `~/.claude/skills/maverick-bank/SKILL.md` | `~/.claude/rules/maverick-bank.md` |
| Claude Code project | `<project>/.mcp.json` | `<project>/.claude/skills/maverick-bank/SKILL.md` | `<project>/.claude/rules/maverick-bank.md` |

Codex's nonempty `AGENTS.override.md` takes precedence at the same location. The adapter appends its marked block there when present, instead of adding ineffective guidance to `AGENTS.md`. If a new override later shadows an installed block, reinstall refuses and explains that uninstall/reinstall is needed. An explicit `codex_home` Python API argument overrides `CODEX_HOME`. User skills still belong to the user's `.agents/skills`, independently of `CODEX_HOME`. [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills).

Claude's dedicated rule file has no `paths` restriction and is loaded at startup. This preserves existing `CLAUDE.md` files and avoids creating a `CLAUDE.md` that could suppress automatic discovery of an existing `AGENTS.md`. Claude's `local` MCP scope is a separate private per-project configuration in `~/.claude.json`; Maverick Bank exposes only explicit `user` and `project` scopes. Existing higher-priority client settings and managed policies can still shadow or block the server. [Claude rule loading and instruction discovery](https://code.claude.com/docs/en/memory), [Claude MCP scopes](https://code.claude.com/docs/en/mcp).

When `CLAUDE_CONFIG_DIR` is set, user-level rules and skills live beneath that directory, and the user MCP file becomes `$CLAUDE_CONFIG_DIR/.claude.json`. Project paths remain project-relative. Use the same environment when uninstalling. [Claude configuration directory](https://code.claude.com/docs/en/claude-directory).

Start a fresh agent session after installation or removal so startup guidance and MCP configuration reload. Codex's desktop, CLI and IDE share MCP configuration for the same Codex host; the desktop MCP settings offer a Restart action. Codex project MCP configuration requires a trusted project. Claude may show workspace trust and project MCP approval prompts on first interactive use. The adapter does not disable these host controls. Local skills and stdio servers are not automatically available to cloud sessions. [Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [Claude MCP](https://code.claude.com/docs/en/mcp), [Claude skills](https://code.claude.com/docs/en/skills).

## Preservation and recovery

The adapter preflights every requested client before changing client files. It refuses malformed configuration, duplicate JSON keys, foreign same-name servers or skills, unowned instruction markers, and changed owned entries. Even an identical foreign server is not silently claimed. Exact reinstall makes no configuration writes. Use the same bank, scope and client paths for removal.

Every changed existing file gets an atomic sibling backup named `.mb-<unique-id>.bak`. The per-bank `.maverick/integrations.json` records owned entries, block text, content fingerprints and backup paths; it does not copy unrelated client secrets into the bank. Backups can contain the same sensitive data as their source files: keep them private with the client configuration. Backups are retained after uninstall for manual recovery.

Uninstall restores original bytes when the containing file is unchanged. When unrelated edits were made, it removes the matching owned server entry or exact marked block while keeping those edits. JSON formatting can change; TOML comments and unrelated values are preserved through tomlkit. A changed owned block, server entry or skill is a conflict: reconcile it manually before retrying. Notes and other bank data are never removed. Empty created directories may remain.

Writes use fsync, atomic replacement and a per-bank installer lock. Ordinary write errors roll back earlier file changes when they still match what this operation wrote. A multi-file install is not one filesystem transaction: abrupt process termination, disk failure or simultaneous edits by another application can require manual recovery from the sibling backups. Do not delete the ownership manifest while registrations remain. The manifest and client files are trusted local configuration, not a security boundary against another process running as your user.

## Verify the actual host

After registration, inspect configuration with `codex mcp get maverick-bank` or `claude mcp get maverick-bank`, then start a new session and inspect `/mcp`. A configuration listing is not proof of model use. Ask the agent to save a harmless project-scoped test preference, search it, read its ID and revision, and report which evidence informed its answer. Remove the test note manually if no longer useful.

The provider-neutral skill documents the six MCP memory tools, explicit capture, scoped evidence, corrections through supersession, and the limits of offered/read/declared-use events. Installing a skill does not prove compliance. Automated adapter tests exercise temporary homes and file behavior; a real SDK handshake and authenticated agent trials are separate acceptance checks.

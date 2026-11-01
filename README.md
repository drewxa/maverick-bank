# Maverick Bank

Local, editable long-term memory shared by **Claude Code and Codex**. Save durable preferences, decisions and lessons as Markdown; retrieve excerpts with their source, lines, revision and dates. The bank runs on your computer through a CLI and a local MCP connection.

**Release candidate · 0.1.0.** Intended for Windows, macOS and Ubuntu. [Download the release ZIP](https://github.com/drewxa/maverick-bank/releases/download/v0.1.0-rc.3/maverick-bank-0.1.0.zip) or [browse releases](https://github.com/drewxa/maverick-bank/releases). See [validation evidence](docs/VALIDATION.md) and the [release checklist](docs/RELEASE-CHECKLIST.md) for executed checks and pending host/platform trials. No PyPI publication is required.

[Русский](README.ru.md) · [Configuration](docs/CONFIGURATION.md) · [Privacy](docs/PRIVACY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

## Install

Start with an installed, authenticated Claude Code or Codex client, Git available on PATH, and internet for dependencies. Download and extract the supplied release ZIP, open a terminal in that directory, and run **one** command:

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Source . -Clients codex,claude
```

macOS / Ubuntu:

```sh
sh scripts/install.sh --source . --clients codex claude
```

The scripts provision uv when needed, install the package and configure selected clients. Choose only `codex` or `claude` if you use one. The default bank is `~/.maverick-bank`; choose another with `-Bank "path"` on Windows or `--bank "path"` on macOS/Ubuntu. A downloaded wheel can be supplied as the source instead. Git history stays local.

For CLI commands below, copy the installer's final `PATH command:` line into your terminal, without that label. It makes both `uv` and `maverick-bank` available by name, including after a fresh installation. Save the displayed directories in your user PATH/shell profile for future terminals; reopening a terminal alone does not add them. Agent connections use absolute paths and work independently of this CLI setup.

For a custom bank, subsequent CLI commands must use the same `--bank PATH` or set `MAVERICK_BANK_HOME` to that directory.

From a source checkout with [uv](https://docs.astral.sh/uv/) already installed:

```sh
uv tool install .
maverick-bank init
maverick-bank install --clients codex claude --scope user
maverick-bank doctor
```

Restart your agent client. Approve its normal workspace/MCP permissions if prompted. Startup guidance asks the agent to read `memory_status` once per session and apply your configured recording policy. Client configuration alone does not prove a live connection; [integration details](docs/INTEGRATIONS.md) explain files and verification.

## First useful memory

In your agent, send a harmless, specific request:

> Remember in Maverick Bank, scope `project:onboarding-demo`: for this demo project's status reports, put the next action first. Save this as a user-confirmed preference with this message as its source. Tell me the saved ID and revision.

Start a **new session**, then ask:

> Search Maverick Bank in scope `project:onboarding-demo` for the status-report preference. Read the matching record before answering. What should the first line contain? Cite its path and lines, and say whether memory informed your answer.

Success means the agent retrieves the saved record and applies the preference. An answer without tool calls does not pass the recall check. The 5–7 minute onboarding target is a goal to measure, not a universal timing guarantee.

## Search that works immediately

Base installation uses SQLite full-text search. No API key, Docker or model download is needed. A selected project scope sees that scope plus `global`; unrelated projects are excluded by default.

```sh
maverick-bank search "status reports" --scope project:onboarding-demo
maverick-bank status
maverick-bank audit
```

For local multilingual semantic retrieval, install optional dependencies **from the downloaded source directory**, then explicitly provision the model:

```sh
uv tool install --force '.[semantic]'
maverick-bank semantic install
```

A fresh installation can use `uv tool install '.[semantic]'`. The default multilingual model is approximately **220 MB**; dependencies and cache need additional space. Size and time vary. Search never downloads a model; missing/unavailable models are reported with lexical fallback. See [semantic configuration](docs/CONFIGURATION.md#local-semantic-search).

## Keep memory useful

Normal search/status performs a per-scope structural check on first use and when due (every seven days by default), then hints to the agent to review relevant findings. This does not verify claims or change notes. You can also ask:

> Audit Maverick Bank. Read the cited revisions and review candidates for duplicates, conflicting scope/time, missing evidence and claims needing a fresh check. Separate user statements from inference. Propose corrections with sources; do not delete, merge or mark claims confirmed automatically.

`audit` supplies scoped, paginated candidates for agent review; it does not determine truth. Follow `next_offset`, restarting if `dataset_revision` changes. Corrections create new records linked through `supersedes`. Usage counts distinguish offered text, served reads and agent-declared use; they do not prove model influence.

Edit notes directly under `notes/`. Search refreshes changed files; `maverick-bank reindex` rebuilds the disposable index. Local Git snapshots live separately under `.maverick/history`, including prior note content. After an interrupted capture, `maverick-bank recover` restores missing pending writes without overwriting human edits and retries history/index updates. [Configuration and backup](docs/CONFIGURATION.md) cover maintenance and recovery.

## Privacy and removal

The application sends no telemetry, notes or queries to a hosted service. Your agent may send retrieved text to its cloud model provider. Explicit package/model installation uses the network. Memory is not encrypted; use a private directory and keep secrets out. Read the [privacy and threat boundary](docs/PRIVACY.md).

```sh
maverick-bank uninstall --clients codex claude --scope user
uv tool uninstall maverick-bank
```

Uninstall removes owned integration entries, preserves unrelated settings, and **never deletes your bank**. Use the same bank and scope as installation. Restart clients afterward. See [troubleshooting](docs/TROUBLESHOOTING.md) for changed-entry conflicts and manual recovery.

MIT licensed. [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

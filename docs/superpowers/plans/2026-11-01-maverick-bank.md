# Maverick Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. The owner explicitly delegates decisions and asks for continuous autonomous execution without questions.

**Goal:** Ship a useful, installable, configurable local Markdown memory bank for Codex and Claude Code.

**Architecture:** Python service shared by CLI and MCP; human-readable authority, separate derived SQLite index, durable operational journals and isolated local Git snapshots. One install with optional explicitly provisioned local semantic model.

**Tech Stack:** Python >=3.11, uv, official MCP SDK, SQLite FTS5, PyYAML, filelock, tomlkit; optional FastEmbed; pytest, Ruff, build.

**Spec:** `docs/superpowers/specs/2026-11-01-maverick-bank-design.md`

## Global Constraints

- Windows, macOS, Ubuntu; Claude Code and Codex. First useful base setup target 5–7 minutes, measured conditions recorded.
- No remote notes/telemetry, no paid-model requirement, no query-time model download, no changes to unrelated existing files.
- Markdown authority; append-only UUID captures; events/history survive disposable-index rebuild.
- Bounded inputs and locks, confined paths, explicit uncertainty/status, no automatic semantic deletion or truth promotion.
- Public runtime errors explain remediation; no stdout diagnostics in MCP mode.
- Production-readiness claims match actual platform/host/model evidence.

## Review Focus

- Foreign Git indexes/hooks/global filters must not be touched by memory versioning: exercise a pre-staged user repository and sidecar snapshot.
- Unicode/spaces, symlink/junction paths and interrupted writes: core integration tests and installed-wheel smoke.
- Same server names and pre-existing instruction content: reversible/idempotent adapters with changed-owned-content conflicts.
- Rebuild/manual edits/corrections cannot silently retain stale visible evidence or erase journals: retrieval and durability scenarios.
- Missing Git/model/network/agent CLI must be an explicit usable or actionable state, never a fake green diagnosis.

## Task 1: Durable bank and capture

Files: package scaffold; `config.py`, `paths.py`, `notes.py`, `history.py`, `events.py`, `bank.py`; `tests/test_bank.py`, `tests/test_history.py`, `tests/test_paths.py`.

Interfaces: `Bank(root: Path)`; `Bank.initialize(root, **settings)`; `remember(title, body, source, scope='global', kind='fact', status='unverified', supersedes=None) -> dict`; `read(memory_id, start_line=None, end_line=None) -> dict`; `record_use(memory_id, revision, task_id='', agent='unknown', outcome='unknown') -> dict`. Structured results use JSON-compatible values, stable `id`, `revision`, `path` and UTC timestamps.

- [x] Add real filesystem/Git tests for capture/read, external edits, concurrent writers, confined paths, preserving unrelated staged changes and event durability; observe missing feature failures.
- [x] Implement strict config, locking, atomic notes, durable journals, isolated snapshots and bounded reads; run targeted tests then complete suite.
- [x] Commit coherent durable core and record evidence.

## Task 2: Retrieval, temporal evidence and audits

Files: `index.py`, `embeddings.py`, `audit.py`; tests for retrieval, model lifecycle and audit.

Interfaces: `Bank.search(query, limit=5, scope=None, include_superseded=False) -> dict` with `mode`, `semantic_status`, `results`; `Bank.reindex() -> dict`; `Bank.audit() -> dict`; `Bank.stats() -> dict`; `Bank.provision_semantic(model=None) -> dict`. Index stores chunk line spans/hashes. Semantic provider supports document and query embeddings and explicit provisioning.

- [x] Test exact/Unicode/paraphrase lookup, scope, deleted/changed authority, stale index recovery, supersession, deterministic audit candidates and honest missing-model state.
- [x] Implement SQLite FTS5 + cosine reciprocal-rank fusion, cached model metadata, explicit offline load; run suite.
- [x] Provision actual local multilingual model, run nonlexical retrieval and offline smoke; record measured limitations.
- [x] Commit retrieval/audit.

## Task 3: CLI, MCP and client installation

Files: `cli.py`, `server.py`, `integrations.py`, packaged skill; `tests/test_cli.py`, `tests/test_mcp.py`, `tests/test_integrations.py`.

Interfaces: CLI `init`, `remember`, `search`, `read`, `reindex`, `audit`, `stats`, `history`, `doctor`, `semantic install`, `install`, `uninstall`. Common `--bank PATH`, machine-readable JSON for tests/agents. MCP tools `memory_search`, `memory_read`, `memory_remember`, `memory_record_use`, `memory_audit`, `memory_status` call Bank; server uses `serve --bank PATH`.

- [x] Write failing subprocess CLI and real SDK stdio tests, plus realistic config roundtrip/conflict tests.
- [x] Implement wrappers, error handling and safe owned client configuration; do not install into the owner's actual host settings during tests.
- [x] Test real installed Codex configuration in an isolated temporary CODEX_HOME, clearly distinguishing it from authenticated model recall.
- [x] Commit integration.

## Task 4: Distribution and onboarding

Files: `scripts/install.ps1`, `scripts/install.sh`, `scripts/smoke.py`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, docs, license/security/changelog.

- [x] Write installer behavior tests against temporary destinations and existing install state; preserve data on uninstall.
- [x] Package wheel/source distribution; install clean wheel with runtime absolute paths; measure init-to-first-recall and full installation separately.
- [x] Add Windows/macOS/Ubuntu CI tests, package checks, offline base smoke and opt-in semantic test. Release artifact workflow emits versioned archives/checksums without private data.
- [x] Publish truthful quickstarts and configuration reference; commit distribution.

## Task 5: Independent review and release candidate

- [x] Fresh-context reviewers examine product acceptance, architecture/data safety and integrations; report concrete findings with evidence.
- [x] Reproduce material defects with failing tests, fix them, rerun affected and complete suite.
- [x] Build final artifacts, record checksums and test matrix in `docs/VALIDATION.md`; distinguish executed, simulated and pending checks.
- [x] Finish in a clean committed release branch; provide concise result and real limitations, without claiming unexecuted platform trials passed.

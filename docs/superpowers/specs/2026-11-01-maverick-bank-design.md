# Maverick Bank: release design

## Intent

Build a publishable local memory bank for Claude Code and Codex on Windows, macOS, and Ubuntu. A colleague with an authenticated agent and basic IT knowledge should install the base product and reach a useful first recall in 5–7 minutes. The user delegates product and implementation decisions and explicitly opts out of questions and approval checkpoints.

## Decisions and alternatives

Choose a Python package, CLI, official MCP stdio server, and small client adapters. Python 3.11+ is provisioned by uv; SQLite and Markdown need no database server. A Node-only implementation would impose a runtime without improving this file/SQLite workload. A skill alone cannot enforce versioning, event semantics, consistency or path boundaries. A hosted service would violate the local storage goal and add accounts and credentials.

Working product name: Maverick Bank. Treat dictated “Cloud” as Claude Code. English product documentation and a short Russian quickstart. MIT source license. No public deployment, registry publish or remote repository creation is authorized by “publishable”; prepare release artifacts instead.

## Product contract

- Authoritative UTF-8 Markdown is human editable. New durable notes are append-only, one UUID per file. Corrections create a new note with `supersedes`; existing human text is never overwritten by automated capture.
- Record source, scope, kind (preference/decision/lesson/fact/hypothesis), status (unverified/user-confirmed/observed), created time and optional evidence links. Model guesses must not become user-confirmed by default. Imported Markdown without metadata stays searchable as unverified.
- Default capture policy: explicit requests and clear corrections; exclude secrets, transcripts and temporary task lists. This policy is agent guidance, not a claim of perfect automatic secret detection.
- Dedicated configurable bank directory, selected clients, global/project integration, recording guidance, search limits, review age, event retention, Git requirement, semantic model and offline cache.
- Automatic local Git snapshots live in an application-owned sidecar repository; never stage or change an existing user repository. No remote, push, application telemetry, implicit cloud inference, model download at query time, or automatic semantic adjudication.
- SQLite FTS5 lexical retrieval works immediately. A real local FastEmbed multilingual backend is shipped as an optional extra; an explicit provision command downloads the model. Hybrid search uses lexical+cosine ranks. Missing/unprovisioned models return an honest lexical mode and diagnostic.
- Return stable ID, exact content revision, path, line span, excerpt, declared metadata dates, filesystem date, and available Git attribution labelled as text-history information. Recheck current content; never present an index snapshot as a guaranteed current file.
- Durable local events distinguish `offered` (server prepared response), `read` (bank tool served a span), and `declared_used` (agent self-report). They prove neither client receipt nor true influence. No raw search queries or bodies in events; bank access outside the tools is unobserved.
- Audits identify malformed records, missing sources, duplicate IDs/content, supersession errors, review-age candidates and possible semantic conflicts for host-agent review. No automatic deletion, rewriting or truth promotion. Review inputs reference record IDs and revisions; changed inputs invalidate review proposals.

## Architecture

Bank root contains `notes/` and `.maverick/`. The latter holds versioned configuration, durable event journal, operation journal, lock, disposable SQLite index, model cache and an isolated `history/` Git repository containing snapshots of selected note bytes. Index rebuilding never destroys events/history/configuration.

Modules: `config`, `paths`, `notes`, `history`, `events`, `index`, `embeddings`, `bank`, `audit`, `integrations`, `server`, `cli`. CLI and MCP call the same Bank service. Public Python API is small; no arbitrary command execution or arbitrary-path file editing through MCP.

Acquire a bounded per-bank file lock for cooperating writes and snapshot/index transactions. Write captures atomically and fsync durable journals. A pending operation is visible and recoverable if Git fails after file creation; do not roll back over later manual edits. Clear actionable errors for invalid future schemas, busy banks, malformed configuration and missing Git. Search/read/audit remain usable when Git is unavailable; capture requires Git unless explicitly configured otherwise.

Path policy confines note paths to the bank, rejects traversal, absolute/device/UNC inputs, alternate data streams and descendant symlinks/junctions. State and history paths must not be symlinks. Skip malformed or oversized imports with visible audit findings. This is not a security boundary against a malicious process running as the same user.

## Integration and onboarding

One install command per platform using uv and the released wheel/source checkout; bundle bootstrap scripts which provision uv when absent. Register an absolute interpreter path and `-m maverick_bank serve --bank ABSOLUTE_ROOT` as stdio MCP. Offer registration for either or both clients. Preserve unrelated JSON/TOML/instruction content, atomically back up edits, use owned markers/manifests, reject conflicting same-name servers, and make reinstall/uninstall idempotent. Never remove memory data on uninstall.

Provider-neutral skill plus a concise owned startup instruction block explain lookup, scoped evidence, safe capture and reported-use semantics. User/project scope are explicit. Installing artifacts does not prove model compliance. `doctor` checks configuration, FTS5, Git, semantic state, registrations and real MCP protocol smoke test. Host restart and host permission prompts are documented.

## Acceptance and release evidence

1. Fresh wheel installs in a clean venv into a Unicode path with spaces; CLI init/capture/search/read/history/audit/event report work without project cwd assumptions.
2. Real MCP process lists tools and performs capture/search/read via the official SDK. Stdout is protocol-only and tool errors are actionable.
3. Two processes capture without losing records; traversal/symlink attempts fail; Unicode and large/error inputs are bounded; manual edits and deletion refresh retrieval; index deletion preserves durable state; superseded records are excluded from normal current recall.
4. Actual local embedding model retrieves an English paraphrase and a Russian paraphrase, runs without network after provisioning, and does not invent semantic success when unavailable.
5. Client installation/removal preserve realistic existing configs/instructions; repeat install is safe; path quoting and project/global options are exercised. Where available, validate with installed Codex CLI. Keep simulated adapter tests distinct from actual authenticated agent tests.
6. CI matrix runs tests, package build and wheel/MCP smoke tests on Windows, macOS and Ubuntu, Python 3.11/3.12. Record executed versus pending environments honestly. Six real OS × host onboarding trials remain an external release gate if those hosts are unavailable locally.
7. Include quickstart, configuration, privacy/threat boundary, migration/backup/restore, troubleshooting, release checklist, changelog, license, security policy, CI and reproducible artifacts/checksums. Do not put owner-specific paths, notes, credentials or generated test banks in artifacts.

## Deliberately excluded

Hosted sync, accounts, GUI, automatic transcript mining, a graph DB, an autonomous paid model, silently applied semantic merges, and claims of perfect truth or perfect usage observation. These are not required for a coherent first release.

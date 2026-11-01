# Configuration and maintenance

## Choose a bank and clients

The default bank is `~/.maverick-bank`. A command's `--bank PATH` overrides `MAVERICK_BANK_HOME`, which overrides that default. Use an absolute path when registering a client; the adapter stores the resolved path and installed Python executable. Do not move or delete the runtime environment while it is registered.

```sh
maverick-bank init --bank "/path/to/memory"
maverick-bank install --bank "/path/to/memory" --clients codex claude --scope user
```

The path above is an example: replace it with a private directory on your machine. For an existing knowledge base, choose a dedicated subdirectory, or configure `notes_dir` to a dedicated relative folder. Maverick Bank scans Markdown under that folder, not your entire home directory. Do not point it at unrelated sensitive documents.

For project-local registration:

```sh
maverick-bank install --clients codex --scope project --project "/path/to/project"
```

Registration scope controls where the client connection/guidance is installed. A note's memory `scope` controls retrieval. These are separate settings: installing in a project does not automatically move notes into that project's scope. Use the same bank, client paths, registration scope and project when uninstalling. See [exact files and ownership behavior](INTEGRATIONS.md).

## Settings

Edit `<bank>/.maverick/config.toml` while the bank is idle, then restart connected clients. Use valid TOML types; unknown fields, unsupported schema versions and invalid bounds are rejected. Re-running `init` preserves existing configuration.

| Setting | Default | Meaning |
| --- | --- | --- |
| `schema_version` | `1` | File format version; do not change manually. |
| `notes_dir` | `"notes"` | Dedicated relative Markdown folder inside the bank; no linked descendant paths. |
| `default_scope` | `"global"` | Scope used when search does not supply one. |
| `git_enabled` | `true` | Local sidecar snapshots; capture requires Git when enabled. |
| `review_after_days` | `90` | Age that triggers review, not an expiry or truth judgment. |
| `max_note_bytes` | `262144` | Maximum UTF-8 record size, including metadata. |
| `max_response_chars` | `12000` | Bound on returned content. |
| `max_files` | `10000` | Maximum Markdown files scanned. |
| `lock_timeout` | `15` | Seconds to wait for cooperating bank operations. |
| `event_retention_days` | `90` | Age limit applied by explicit event pruning. |
| `event_max_count` | `50000` | Count limit applied by explicit event pruning. |
| `semantic_enabled` | `false` | Enables the provisioned local semantic provider. |
| `semantic_model` | `"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"` | Local embedding model identifier. |
| `semantic_cache_dir` | `""` | Empty uses `<bank>/.maverick/models`; an absolute path selects another cache. |
| `capture_policy` | Explicit requests and clear corrections; exclude secrets, raw transcripts, temporary tasks and unconfirmed inferred preferences. | Guidance exposed to agents; not an automatic secret filter. |

Positive day/count/timeout settings are bounded at 1–1,000,000. Note sizes allow 1,024–8,388,608 bytes; response size allows 256–100,000 characters; file count allows 1–100,000. Raising limits increases work and memory use. Search accepts 1–20 results, default 5.

## Records, scopes and corrections

Captured records contain a UUID, title, creation date, source, scope, kind and status in YAML frontmatter. Kinds: `preference`, `decision`, `lesson`, `fact`, `hypothesis`. Statuses: `unverified`, `user-confirmed`, `observed`. A hypothesis stays unverified. A model must not infer user confirmation.

Use a stable label such as `project:reporting-tool` for project memory and `global` only for a rule intended across projects. Search with that project scope returns its records plus global ones. Explicit all-scopes retrieval can expose other scopes; scope is not a permission boundary. Read a result by its returned ID before relying on it.

A correction creates a new record with `supersedes` referencing the earlier ID in the same scope. Superseded records remain in files/history and are omitted from ordinary search. Repetition, recency and usage counts do not independently confirm a claim. `created_at`, `checked_at` and `checked_source` are declarations; filesystem and Git dates describe text history.

Human-edited UTF-8 Markdown in `notes_dir` is searchable. Without frontmatter it receives an imported ID derived from its relative path and defaults to unverified/global. Renaming such a file changes its imported ID. Keep stable explicit IDs when cross-referencing records; duplicate IDs are rejected from normal retrieval and reported by audit. Invalid or oversized records produce visible scan findings rather than silent import.

## Local semantic search

Base search is lexical. Install optional dependencies from the source directory with `uv tool install '.[semantic]'`, or add `--force` when replacing an existing tool installation. The installation scripts also support `-Semantic` (PowerShell) or `--semantic` (shell). Then run:

```sh
maverick-bank semantic install
maverick-bank doctor
```

Provisioning is an explicit network operation. The default multilingual model download is approximately 220 MB; dependencies and cache require additional space. Consult the command's `--help` for selecting a supported model. Model-specific downloads/licenses are separate from this project's MIT source license.

Search loads provisioned files locally and combines lexical/semantic ranks. It never downloads on demand. Check returned `mode`, `semantic_status` and reason: a missing dependency/cache or model error means lexical fallback, not successful semantic retrieval. To verify meaning-based retrieval, save harmless text and search using a paraphrase without its keywords; inspect the result and returned mode. [Validation](VALIDATION.md) records which real model trials ran.

An external absolute cache can share model files across banks. Keep it private and stable; moving it requires updating configuration and restarting clients. Changing model or cache settings does not provision the new model. Restart clients after replacing the installed runtime, and reinstall integrations if the executable path changed.

## Maintenance

```sh
maverick-bank audit
maverick-bank stats
maverick-bank history
maverick-bank reindex
maverick-bank events prune
```

Audit reports malformed notes, missing sources, duplicate content/IDs, supersession errors and review-age findings. Meaningful conflicts need host-agent review of the actual revisions; audit applies no corrections. Candidate lists are bounded, so a single audit is not proof that every pair of notes was compared. `stats` reports local observations, not proven model benefit.

Search refreshes external edits/deletions. `reindex` recreates the disposable SQLite index and preserves notes, events, configuration and history. `events prune` applies retention limits explicitly; it is not a scheduled background purge and does not prune notes, operation history, Git or external backups. Export a journal first if long-term usage evidence matters.

## Local history, backup and restore

Snapshots live in `<bank>/.maverick/history`, an isolated Git repository containing note snapshots. The bank does not stage your project's repository, use its hooks/filters or push. Supported bank operations capture observed note changes; this is not a continuous filesystem watcher and cannot preserve an edit made and reverted between observations. Git dates do not establish when a real-world fact was last checked.

For a complete backup, close agent sessions and other bank writers, then copy the **entire bank directory**, including hidden `.maverick`, to a private backup destination. Include an external model cache separately if you need offline restore. Models/indexes can be regenerated; notes, configuration, journals and Git history cannot be reconstructed from an index. Client configuration backups live beside client files, not inside the bank.

Restore a complete copy to the same path with writers stopped, run `doctor`, and restart clients. To restore one record, inspect the sidecar Git history and copy the selected prior note version back into its original notes location, then run `reindex` and inspect the result. Back up current files first; avoid restoring older state over newer notes without review.

Moving a bank changes registered paths. Uninstall its old registrations before moving, then install against the new path. Do not hand-edit or delete the integration ownership manifest while registrations remain. A restored manifest can contain old absolute client paths; review it and [integration recovery](INTEGRATIONS.md) before changing installations on another computer. No automatic migration from another memory product is implied; copy only selected Markdown into `notes_dir`, then audit sources, scopes and IDs.

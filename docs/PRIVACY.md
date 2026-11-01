# Privacy and threat boundary

## What stays local

Maverick Bank stores notes, indexes, embeddings, configuration, event/operation journals and Git snapshots on your filesystem. The application has no analytics service, hosted memory service, automatic synchronization or remote inference provider. Normal search and reads do not download a model. The MCP connection is a child process over local stdio, without a listening network port or separate MCP account.

Explicit installation/update downloads package dependencies, uv/Python when needed, and an explicitly requested embedding model. Those download services receive ordinary network request information. Other software on your computer, operating-system backup/sync and the host agent have their own network behavior. A bank inside a cloud-synced folder is subject to that folder's synchronization.

## Your host agent still matters

Claude Code or Codex receives retrieved excerpts, metadata and local paths. A cloud-backed host can send these to its model provider under its own account settings and policies. Local storage and local embeddings do not make the complete agent interaction offline. Only connect clients you intend to trust, and request narrow scopes/results.

Memory contents are evidence. A stored command or malicious imported note must not override the current user, project instructions or host permissions. Agent guidance cannot guarantee perfect prompt-injection resistance or perfect capture filtering. Do not store credentials or private third-party data.

## Files and observations

| Data | Location / interpretation |
| --- | --- |
| Authoritative notes | `notes_dir`, default `notes/`; human-readable UTF-8 Markdown. |
| Search index / embeddings | `.maverick/index.sqlite3`; derived data may contain note text. |
| Local model files | `.maverick/models` or configured external cache. |
| Access events | `.maverick/events.jsonl`; IDs, revisions, timestamps, line ranges and event-specific metadata. |
| Operation journal | `.maverick/operations.jsonl`; capture/recovery identifiers and revisions. |
| Git snapshots | `.maverick/history`; historical note content, including replaced/deleted text. |
| Integration ownership | `.maverick/integrations.json`; owned artifacts, fingerprints, paths and backup references. |
| Client backups | Sibling `.mb-<unique-id>.bak` files beside changed client files; may contain sensitive client configuration. |

Access events do not store raw query text or note bodies. Search records a query hash, which is not anonymization: a guessable query may be inferred by trying candidate hashes. Agent-supplied task/agent/outcome labels can also be sensitive. Local events are product observations, not outgoing telemetry.

- `offered`: the server prepared an excerpt for its response; receipt or attention is unproven.
- `read`: the bank tool served a requested span; comprehension is unproven.
- `declared_used`: the agent reported using a returned revision; this is self-report.

Filesystem reads outside the tools are unobserved. None of these events proves causation, correctness or model influence. Retention is applied through explicit `events prune`; note/Git/backup retention is separate.

## Boundaries and deletion

Files are **not encrypted**, and the product does not provide multi-user access control. Memory scopes filter retrieval; they do not isolate users, deny explicit all-scopes access or prevent direct reads by another process running as you. Use normal private directory permissions and disk encryption where appropriate. The path checks and cooperating-writer lock are not protection against an adversarial process with your account privileges.

Uninstalling the client integration or package never deletes the bank. Removing a note does not erase its Git history, an earlier index copy, host conversation, client backup or filesystem/cloud backup. For a stored secret, revoke/rotate it first; assess every copy separately. This candidate has no secure-erasure command or guarantee.

When reporting a defect, reproduce it with invented notes in a temporary bank. Redact local paths and configuration, and never send the whole bank by default. See [security reporting](../SECURITY.md).

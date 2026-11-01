# Troubleshooting

Start with `maverick-bank doctor --bank "path/to/bank"` and `maverick-bank status --bank "path/to/bank"`, using your actual path. Keep diagnostic output private until redacted. `doctor` checks product/runtime state; it is not proof that an authenticated model used memory.

| Symptom | Next action |
| --- | --- |
| `maverick-bank` is not found | Open a new terminal after installation. With uv, run `uv tool update-shell`, then reopen it. A script can use the installed executable directly even before PATH refresh. |
| Bank is not initialized | Check `--bank` and `MAVERICK_BANK_HOME`; run `maverick-bank init --bank "actual/path"`. A different root is a different bank. |
| Capture says Git is required | Install Git on PATH, restart the client and retry. Alternatively explicitly set `git_enabled = false`; this disables versioned capture. Search/read/audit remain available without Git. |
| Bank is busy | Let the other operation finish and retry. Close stale agent processes before investigation. Do not delete live lock/state files. |
| No search result | Check scope, spelling and search mode. Lexical search needs matching terms; try terms from the note. Check `audit` for malformed/oversized records or duplicate IDs. |
| Semantic search remains lexical | Install the semantic extra and run `semantic install` explicitly. Check `semantic_enabled`, cache/model settings and returned reason; restart clients. A fallback is usable but is not semantic success. |
| A changed/deleted note appears wrong | Search again, then run `reindex`; inspect scan findings. Use a returned current ID/revision rather than an old cached result. |
| Record ID is ambiguous | Audit duplicate IDs. Review both files and preserve a backup before assigning distinct IDs or correcting the content. Do not arbitrarily discard a source. |
| Invalid configuration / future schema | Fix TOML types/bounds or use a compatible newer product. Back up configuration; do not lower the schema number to bypass validation. |
| `history_pending` or pending capture | The note may already exist. Preserve it, resolve the Git/disk error, then search/read or reindex to retry snapshots. Inspect status before reissuing capture and creating a duplicate. |
| Journal contains malformed lines | Back up the whole bank and inspect the named journal. Reindex cannot repair durable journal evidence. Do not prune or remove it to manufacture clean statistics. |

## Client cannot see the tools

Restart the client after registration. Inspect `/mcp` and, where the client CLI is available, `codex mcp get maverick-bank` or `claude mcp get maverick-bank`. Check that the registered absolute Python path still exists and the bank path is correct. A removed/moved uv environment breaks the registration; reinstall it from the intended persistent environment.

Use the same environment variables (`CODEX_HOME`, `CLAUDE_CONFIG_DIR`) and user/project scope as installation. Project configuration can require trust or host MCP approval, and managed policies can override it. A local stdio registration is not automatically available in a hosted cloud session. See [integration files and precedence](INTEGRATIONS.md).

The CLI can work even when the host connection is unavailable. Conversely, seeing the server in a configuration listing proves only registration. Use the README's new-session scoped recall check to verify live search, read and application of evidence. If the agent omits tool calls, ask it explicitly to use `memory_search` and `memory_read`; do not count an answer from current conversation context as recall.

## Install/uninstall refuses a conflict

The adapters will not overwrite a foreign `maverick-bank` server/skill or changed owned instruction block. They also refuse malformed configs, duplicate JSON keys and unsafe ownership changes. Back up the client file, compare the reported entry with your intended settings, and resolve that specific conflict. Do not delete the entire client configuration.

Existing changed files have sibling `.mb-<unique-id>.bak` backups; the bank manifest records their paths. Backups may contain sensitive client settings. Uninstall normally removes only exact owned artifacts and preserves unrelated later edits. A changed owned artifact requires manual reconciliation before retrying. Do not delete `.maverick/integrations.json` while registrations remain.

If an abrupt failure interrupted a multi-file install, preserve current files and backups, inspect which owned entries were written, and restore the relevant original files only after comparing later edits. Ordinary write failures attempt rollback; abrupt termination is not an atomic multi-file transaction. [Integration recovery details](INTEGRATIONS.md) explain ownership and restoration.

## Offline or restricted networks

Base retrieval runs locally once packages are installed. Bootstrap/package installation and explicit semantic provisioning need their download sources unless you supply an appropriate pre-downloaded environment/cache. A wheel alone does not bundle every dependency or an embedding model. No query-time download is attempted to hide a missing model.

For offline semantic use, provision the chosen model beforehand, retain its complete configured cache and verify retrieval with networking unavailable. A failed download is not a successful provisioning check. Model-specific failures and unsupported identifiers should be resolved with the supported model list and command diagnostics, not a hosted API key.

## Report a reproducible problem

Include the product version (`maverick-bank --version`), OS, install method, command, expected result and redacted actual error. Reproduce using a temporary bank and invented notes. State whether the failure concerns a CLI command, real MCP handshake, configuration preparation or an authenticated host session. For a security issue, use the [private reporting guidance](../SECURITY.md).

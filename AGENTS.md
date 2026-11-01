# Maverick Bank contributor instructions

Read the design and current plan under docs/superpowers before changing behavior. The owner delegates routine decisions and requests autonomous execution. Keep user-facing explanations short; put detailed evidence in docs/VALIDATION.md.

This is a standalone product, not part of Game Lab. Only modify this repository. Never read or copy the owner's personal memory into fixtures or artifacts. Use temporary HOME/CODEX_HOME/config destinations when testing integrations.

Write meaningful failing behavior tests before implementation. Run targeted tests and the complete suite after changes; use uv with a workspace-local cache. Core code must run on Python 3.11+, Windows, macOS and Ubuntu. Distinguish real platform and host trials from simulated path tests.

No hidden network requests or query-time downloads. Markdown is authority, events and Git history are durable, SQLite index is rebuildable. Do not conflate server-offered, bank-read and agent-declared-use events with actual model influence. No automatic semantic merges or truth promotion. Isolate Git versioning from all user repositories and global hooks/filters.

Do not publish, push, or modify the owner's actual agent configuration as a side effect of development. Produce local release artifacts and instructions. Reviews must identify concrete behavior and reproduction; docs claims must match tested behavior.

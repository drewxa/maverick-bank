# Release acceptance checklist

This is a gate, not evidence of completion. Record results, versions, dates, conditions and artifact hashes in [VALIDATION.md](VALIDATION.md). An unchecked item is pending; configuration simulation, a protocol handshake and authenticated agent recall are distinct forms of evidence.

## Candidate artifacts and local behavior

- [ ] Build wheel, source distribution and downloadable archive from the final source revision; record checksums.
- [ ] Inspect distributions for personal paths, actual memory, credentials, generated test banks and unwanted caches.
- [ ] Install the built wheel in a clean environment under a Unicode path containing spaces; do not rely on the checkout's import path.
- [ ] Run CLI init/capture/search/read/audit/stats/history/reindex/recover and a real SDK MCP handshake with capture/search/read.
- [ ] Demonstrate concurrent captures without lost notes and confinement of traversal/linked paths.
- [ ] Verify manual edits/deletions refresh retrieval, superseded records leave normal recall, and index rebuild preserves notes, journals and history.
- [ ] Verify snapshots leave unrelated staged changes, user Git configuration/hooks and repositories untouched.
- [ ] Exercise interrupted operations, missing Git, malformed records/configuration and changed integration ownership; report actionable recovery.
- [ ] Interrupt capture/history, preserve a later human edit and recover both original and edited versions; restore absent pending writes without overwriting existing files.
- [ ] Verify automatic structural checks are per scope and interval, expose a host hint without truth claims, and allow complete candidate traversal with `next_offset`/`dataset_revision`.
- [ ] Verify startup guidance loads configured capture policy through `memory_status`; doctor detects changed owned registrations without confusing that check with model recall.
- [ ] Install/uninstall twice in temporary client profiles with existing settings; preserve unrelated content and all memory data.
- [ ] Provision the real default embedding model explicitly; demonstrate English and Russian paraphrase retrieval with `mode=hybrid` and no network after provisioning.
- [ ] Show honest lexical fallback with the extra/model missing; no query-time model download or hidden application telemetry.
- [ ] Run the final automated suite, package checks and configured Windows/macOS/Ubuntu CI jobs; link actual runs separately from planned CI.

## Six authenticated onboarding trials

Run each row on the actual target OS with a real, authenticated client. Start with no product installation or developer runtime and an empty test bank. Installed/authenticated host, Git and working internet are stated prerequisites. A basic IT colleague follows only the shipped quickstart. Time installation and first successful fresh-session recall separately; the target is 5–7 minutes for the base path. A slower result needs its conditions and remediation recorded, not a universal success claim.

Real Windows installer and Ubuntu-under-WSL bootstrap/suite evidence is recorded separately in VALIDATION. Those trials do not replace an authenticated host trial or a native macOS trial; preserve the exact environment labels and final rerun results.

| Actual environment | Host | Evidence to record | Status |
| --- | --- | --- | --- |
| Windows 11 / PowerShell | Codex | Install, tool calls, new-session scoped read/application, removal | Authenticated capture/fresh-session application passed with isolated guidance; native guidance/cold colleague trial pending |
| Windows 11 / PowerShell | Claude Code | Same, independently authenticated | Pending external trial |
| Supported macOS / record architecture | Codex | Same; paths with spaces | Pending external trial |
| Supported macOS / record architecture | Claude Code | Same; preserve existing guidance | Pending external trial |
| Ubuntu LTS / record release | Codex | Same; no desktop dependency | Pending external trial |
| Ubuntu LTS / record release | Claude Code | Same; concurrent-bank use | Pending external trial |

For every trial, record host/runtime/package versions, prerequisites, downloaded source/artifact, elapsed time, permission prompts, tool evidence and any failure. Use harmless project-scoped notes. A server listing, six parametrized tests or a model repeating current-prompt content does not satisfy these trials. Update statuses only with matching evidence.

## Documentation and release claims

- [ ] Verify every quickstart command against the shipped CLI/scripts and clean artifacts.
- [ ] Check README remains concise, both languages match, relative links resolve and no nonexistent registry/repository URL is presented as working.
- [ ] Confirm config defaults, optional model/cache behavior, uninstall, privacy, retention and backup guidance match code.
- [ ] Keep offered/read/declared-use semantics distinct and state host-cloud disclosure, unencrypted storage and scope limitations.
- [ ] Include MIT license, changelog, security reporting policy and third-party model-license information.
- [ ] Label remaining unsupported/unexecuted platforms, semantic checks and host trials prominently; do not claim production readiness for unverified combinations.
- [ ] Ensure a public release has a usable private security-reporting channel before advertising one.

Preparing release artifacts does not authorize publishing a package, creating a remote repository or pushing source. Those actions remain separate from this checklist.

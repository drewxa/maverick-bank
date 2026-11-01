# Validation and release status

Checked **2026-11-01**. Product version **0.1.0**, release candidate. Code revision `4771b41` (subsequent commits may update evidence and packaging). The application is implemented and packaged; the complete six-environment authenticated-host acceptance is **not yet certified**.

## Executed checks

| Environment | Actual result | What this establishes |
| --- | --- | --- |
| Windows x64, CPython 3.12.14, semantic extra | **75 passed, 4 skipped** | Full suite including real stdio MCP in modern/legacy modes, local multilingual inference with socket connections blocked, installer repeat/uninstall, recovery and client configuration |
| Windows x64, CPython 3.11.17, base install | **74 passed, 5 skipped** | Declared minimum Python version, lexical-only base behavior and actionable missing semantic dependency |
| Ubuntu 26.04 LTS x64, WSL2, CPython 3.12.15 | **77 passed, 2 skipped** | Actual Linux execution, real bootstrap/reinstallation, symlink confinement, local semantic inference and MCP |
| Ubuntu native temporary filesystem | POSIX private-directory regression passed | New banks use private creation permissions; existing directory permissions are preserved. WSL NTFS mounts may ignore POSIX mode bits |
| Installed Codex CLI | Accepted generated MCP configuration and confirmed removal in an isolated profile | Configuration compatibility only; no authenticated model/session recall was performed |
| Built wheel in a new Windows venv | Capture → search → read → real MCP status passed | Installation is usable independently of the development environment |
| Distribution build | Wheel and source distribution built; `twine check` passed | Structurally valid Python distributions using Core Metadata 2.4 |
| Source ZIP | Allowlist, required installer/source contents and reproducibility test passed | Runtime profiles, model caches, operational journals, credentials and repository metadata are excluded |
| Ruff and Git | Lint/format and whitespace checks passed | Static hygiene, not a claim of correctness by itself |

Windows semantic-suite skips: two symbolic-link creation tests denied by the account; one POSIX-only permissions test; the missing-extra case because FastEmbed is installed. The separate Windows 3.11 run also skips explicit model and installer opt-ins, while actually testing the missing semantic dependency. Ubuntu skips the Windows-only junction case and the missing-extra case. Windows junction protection was tested successfully on Python 3.11 and 3.12.

## Measured automated onboarding

Both trials used empty, separate uv, managed-Python, dependency and tool caches, a new bank and isolated client profiles. They started with Git, a terminal and internet. Neither used Docker or an inference API key.

| Platform | Installer complete, including real MCP diagnostic | First CLI capture and matching recall |
| --- | ---: | ---: |
| Windows | 17.44 seconds | 18.36 seconds |
| Ubuntu | 66.49 seconds | 69.71 seconds |

These measure an **automated base-install/MCP/CLI path on this connection**, not a colleague's completion time and not an authenticated Claude/Codex model applying memory. They support the feasibility of the 5–7 minute target; they do not certify it universally. Agent authentication, host permission prompts, client restart and semantic-model provisioning are separate. The optional multilingual model downloaded in approximately 38 seconds in the development run; this is not a download-time guarantee.

The restricted Windows development account initially could not acquire SChannel TLS credentials. The cold trial was rerun outside that restricted account with all writable runtime/profile/cache data still confined to the project test area. A real PowerShell 7 → Windows PowerShell 5 module-inheritance problem was reproduced and fixed before the successful cold trial.

## Meaningful behavior covered

- Exact and Unicode lexical retrieval; English and Russian nonlexical paraphrases using actual ONNX weights.
- No query-time model download or remote fallback; semantic readiness and lexical fallback are explicit.
- Scoped project recall plus global notes, exclusion of unrelated projects, configured capture scope and policy visibility.
- Current file edits/deletions, index loss/corruption, duplicate-ID quarantine, source spans and bounded partial-line excerpts.
- Local Git isolation from a pre-staged parent repository, matched per-line commit/date provenance, and no inherited hooks/signing/filter configuration.
- Two cooperating writers, bounded locking, path traversal, symlinks and Windows junctions.
- Torn UTF-8 journal tails; post-write Git failure followed by manual editing; preservation of the original returned revision; interrupted absent-note recovery.
- Events survive index rebuilding; offered/read/declared-use labels remain distinct; unknown revision references are rejected.
- Audit pagination, structural maintenance hints, duplicate/source/age findings without semantic deletion or truth promotion.
- Idempotent, owned user/project integrations, existing instruction/config preservation, malformed/conflicting config refusal and registration diagnostics.

Independent architecture review found and reproduced defects before release-candidate packaging. Each material finding received a failing regression and a fix; the final four architecture findings were independently rechecked with **4/4 passing targeted tests**. Integration review's registration-diagnostic finding and product review's policy/pagination/maintenance findings were addressed. These reviews are additional engineering evidence, not proof of all possible behavior.

## Reproduce

From the source directory, with uv and Git available:

```sh
uv sync --locked --extra semantic --group dev --python 3.12
uv run --no-sync pytest -q
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
uv build
uv run --no-sync twine check dist/*.whl dist/*.tar.gz
uv run --no-sync python scripts/package_release.py
```

Semantic tests require explicit provisioning and `MAVERICK_TEST_MODEL_CACHE` pointing to that model cache. Installer trials require `MAVERICK_TEST_INSTALLERS=1` and use temporary profiles. See test skip messages for the exact unmet prerequisite. No test requires the owner's real bank or live client configuration.

`.github/workflows/ci.yml` prepares a Windows/macOS/Ubuntu × Python 3.11/3.12 matrix and a separate actual-model job. `.github/workflows/release.yml` builds artifacts; it does not publish to a registry. The hosted workflows have **not been executed** from this local repository.

## Remaining release gates

1. Execute the macOS core, installer and semantic checks on a real macOS host or hosted runner. This machine has no macOS environment.
2. Execute all six OS × authenticated host trials: Windows, macOS, Ubuntu with Claude Code and Codex. In a fresh session, the agent must retrieve the saved source and apply its scoped preference. CLI config parsing and a direct MCP client are insufficient substitutes.
3. Have a colleague follow only the quickstart and record time, permission prompts and confusion. Keep the existing-authenticated-agent and Git prerequisites explicit.
4. Choose a public repository/registry destination and run the prepared CI before making a general production-ready claim. No remote, public repository or registry release was created during development.

Until these gates pass, distribute as a **release candidate** with this report, not as a certified production release on all six combinations.

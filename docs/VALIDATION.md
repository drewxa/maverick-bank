# Validation and release status

Checked **2026-11-01**. Product version **0.1.0**, release candidate. The application is implemented and packaged, including MCP argument-schema hardening found during actual Codex use; the complete six-environment authenticated-host acceptance is **not yet certified**.

## Executed checks

| Environment | Actual result | What this establishes |
| --- | --- | --- |
| Windows x64, CPython 3.12.14, semantic extra | **75 passed, 4 skipped** | Full suite including real stdio MCP in modern/legacy modes, local multilingual inference with socket connections blocked, installer repeat/uninstall, recovery and client configuration |
| Windows x64, CPython 3.11.17, base install | **74 passed, 5 skipped** | Declared minimum Python version, lexical-only base behavior and actionable missing semantic dependency |
| Ubuntu 26.04 LTS x64, WSL2, CPython 3.12.15 | **77 passed, 2 skipped** | Actual Linux execution, real bootstrap/reinstallation, symlink confinement, local semantic inference and MCP |
| Ubuntu native temporary filesystem | POSIX private-directory regression passed | New banks use private creation permissions; existing directory permissions are preserved. WSL NTFS mounts may ignore POSIX mode bits |
| Installed Codex CLI | Accepted generated MCP configuration and confirmed removal in an isolated profile | Configuration compatibility only; no authenticated model/session recall was performed |
| Windows, authenticated Codex CLI 0.164.0-alpha.11.1 | Two separate-session capture/recall trials passed; final trial saved on its first attempt | Actual model-driven MCP capture and fresh-session application, with synthetic data and isolated guidance; see boundaries below |
| Final MCP schema/error change | Windows 3.12 full base suite: **73 passed, 6 skipped**; targeted MCP tests: **2 passed** on each of Windows 3.11 and Ubuntu 3.12 | Both modern/legacy protocols advertise valid enums, reject invalid status without writing, and return actionable domain-validation errors |
| Final handoff, Windows 3.12 | **75 passed, 4 skipped**, including actual model and installer opt-ins | Complete suite after the final PATH onboarding fix; separate installer tests passed **2/2** on Windows and **2/2** on Ubuntu |
| GitHub Actions, Windows/macOS/Ubuntu × Python 3.11/3.12 | **All six core jobs and the separate semantic job passed** on commit `6ac25c6` ([run](https://github.com/drewxa/maverick-bank/actions/runs/41324808984)) | Actual hosted platform suites, package checks, isolated built-wheel/MCP smoke and real installer trials; actual multilingual-model inference in the Ubuntu semantic job |
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

Final independent handoff review found that an unmanaged uv bootstrap leaves executable directories outside PATH, so a successful absolute-path installation did not guarantee the README's subsequent commands worked by name. Both installers now print a shell-specific activation command containing the exact uv/application directories. Regression tests first failed for missing activation, then executed the printed command with both directories removed from PATH and verified that both executable names resolve. Windows and Ubuntu tests include spaces and an apostrophe in custom profile paths, repeated install, capture/recall and removal without deleting notes. Quickstarts explain current-session activation and persistent PATH setup; the installers do not silently modify shell profiles or the Windows user registry. Product review found no remaining implementation gaps; integration re-review confirmed this finding closed.

## Authenticated Codex behavior

Actual Windows Codex sessions used the existing native login without the test driver reading or copying credentials. Each trial started with an empty synthetic bank. Session one saved a scoped, user-confirmed formatting preference containing an unusual marker. A new session received an ordinary status-update request without the marker or an instruction to recall it; it searched the bank and applied the saved preference. Distinct thread IDs and completed MCP calls were checked. The first trial also read the source explicitly; both reported use against its revision.

The first trial exposed a real integration defect: `memory_remember` accepted unrestricted string arguments in its advertised schema, so the model guessed `confirmed`, and the SDK masked the core validation message. Public kind/status enums and expected `ToolError` responses now make the contract explicit. Modern/legacy regression tests first reproduced the missing enum and then passed. A second authenticated trial completed `memory_remember` on its first attempt, followed by successful fresh-session recall/application; its sessions took 13.89 and 13.72 seconds respectively.

These trials used real authenticated Codex and genuine stdio MCP, with user configuration/AGENTS discovery disabled and an explicit synthetic-bank MCP registration. They establish host behavior, **not** native skill auto-discovery, a cold colleague onboarding time, or any Claude/macOS result. Private runtime logs and authentication material are excluded from distributions. The final base-suite skips above comprise the existing platform/missing-extra cases plus two explicit optional-model/installer opt-ins; the earlier full opt-in suite results remain separate evidence.

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

`.github/workflows/ci.yml` executed the Windows/macOS/Ubuntu × Python 3.11/3.12 matrix and separate actual-model job successfully in [GitHub Actions run 41324808984](https://github.com/drewxa/maverick-bank/actions/runs/41324808984), against commit `6ac25c6`. Publication/report-only commits may follow that tested source revision. `.github/workflows/release.yml` is an optional artifact-build workflow; no PyPI registry publication is included.

The initial hosted Windows runs exposed two test-harness assumptions hidden by the local environment: implicit system-codepage reads of generated UTF-8 configuration, and treating all `Get-Command` matches as a single resolved executable when the development CLI also appeared in PATH. Tests now read UTF-8 explicitly and assert the first executable that would run. The latter failure was reproduced locally with two CLI installations in PATH before fixing it. The final hosted run passed every job; no production encoding workaround or forced CI UTF-8 mode was needed.

## Final acceptance deferred by the owner

On **2026-11-01**, the owner explicitly deferred unavailable platform/client and colleague trials until final acceptance and asked development to continue. They do not block handing over the implemented candidate. The missing evidence below remains visible; this decision does not turn unexecuted checks into passing results. Implementation, local review and packaging are complete; no additional features are required merely to compensate for unavailable test environments.

1. macOS core, installer and built-wheel/MCP checks are now complete on hosted runners. Optional-model inference on macOS remains unexecuted; actual-model inference has been tested on Windows and Ubuntu.
2. Execute the complete six OS × authenticated onboarding trials: Windows, macOS, Ubuntu with Claude Code and Codex. Windows Codex capture/fresh-session application is now demonstrated under the isolated-guidance boundary above; its native guidance/cold colleague trial and the remaining combinations are pending. CLI config parsing and a direct MCP client are insufficient substitutes.
3. Have a colleague follow only the quickstart and record time, permission prompts and confusion. Keep the existing-authenticated-agent and Git prerequisites explicit.
4. Hosted CI passed as linked above. Publication was subsequently authorized by the owner; the public repository is [drewxa/maverick-bank](https://github.com/drewxa/maverick-bank), with candidate assets under [releases](https://github.com/drewxa/maverick-bank/releases). No PyPI registry publication is included.

Distribute the completed implementation as a **release candidate** with this report for the owner's final acceptance. A certified production claim across all six combinations still requires the corresponding results.

# Session 58 Summary (2026-08-21)

**Duration:** Full-day session. Single primary thread (NIST-user diagnostic follow-through) that grew into landing a full provenance-stamping infrastructure and fixing two ship-blocker UI regressions along the way.

**Commits landed:**
- Submodule `0d2013b` — Initial provenance stamp for every backend output.
- Submodule `2da613a` — Early-crash coverage + compiler/flags identity (schema v2).
- Super-repo `868e9cba` — Provenance sidecar + CSV headers + UI plumbing.
- Super-repo `ab706fad` — F1 + F2 fixes + microstructure-restoration ship-blocker.

**Not committed / not yet applied:**
- `scratchpad/thames-cc-portability.patch` (Bug B — portable `cp`/`mv`/`mkdir`) — drafted, awaits Jeff's re-examination.
- Windows UI glass-phase auto-inject investigation — logged as POST_ALPHA, likely Bug A's root cause.
- Nothing pushed to origin (Jeff drives push).

---

## Chronology

### 1. NIST diagnostic thread opens

Jeff received an operations folder from a NIST user testing THAMES alpha on a managed Windows machine. Copied to `~/tmp/NIST-thames-operations/operations/`. Set up `docs/NIST-diagnostic.md` as the tracking doc (per Jeff's "light formality — this is user-support triage, belongs inside THAMES").

Four bugs identified from log inspection alone:
- **Bug A (fatal):** `Hydration-sphere` and `Hydration-test-2` die at `ChemicalSystem::parseMicroPhases` with "Microstructure phase C2AS is not Void but has no GEM pahse data?". Both failed configs list glass phases (`C2AS(am)`, `CAS(am)`, `CA2S(am)`, `CAS2(am)`, `K6A2S(am)`) in their `hydration_products` array. The passing config (`Hydration-test-1`) has no glass phases.
- **Bug B (Windows-only, present in every run):** stderr shows repeated `'cp' is not recognized as an internal or external command` and same for `'mv'`. `backend/thames-hydration/src/thames.cc` shells out to POSIX `cp`/`mv`/`mkdir -p` in 9 sites (7 `cp -f`, 2 `mv -f`, 1 `mkdir -p`). Fails silently on Windows cmd.exe.
- **Bug C (all runs):** no `exit_status.json` in any Result folder — even the successful one. Session 23-30 introduced that file; probably coupled to Bug B (file `mv`'d into place via shell).
- **Bug D (low severity):** failing configs list both `Hydrotalc-pyr` AND `hydrotalcite` — looks like the Materials Panel is letting the user select two aliases for the same phase.

Cross-platform verification: `bin` files, 9 shell-out sites, and UI split — established that Bug B is entirely in C++ backend; UI is a single cross-platform Python codebase (single `thames-windows.spec` since Session 45).

### 2. Bug B drafted (not applied)

Jeff wanted to inspect before applying. Draft at `scratchpad/thames-cc-portability.patch`. Uses C++17 `std::filesystem` (already enabled via `-std=c++17` in CMakeLists.txt); three helper functions (`copyFileInto`, `moveFileInto`, `ensureDir`) preserve the existing `FileException` error path but replace `system()` calls with portable API. Also identified as a bonus fix: closing the ifstream BEFORE the rename in `deleteDynAllocMem` — necessary on Windows where open read handles block renames. Test plan drafted for macOS regression + Windows positive test. **Bug B stays in scratchpad awaiting Jeff's one-more-look.**

### 3. Missing provenance became the second big thread

Jeff asked whether every output file records THAMES version + platform. Answer: essentially no. `version.h` exists (unused for stamping), `APP_VERSION` in `app_info.py` is only shown in the About dialog. Every CSV, log, and image landed with no identity stamp. The concrete harm: NIST user's operations folder and Jeff's own can't be trivially compared to know if they came from the same build. The whole NIST diagnostic is bitten by this.

Recommended two-layer stamp: sidecar `run_metadata.json` in every Result folder + one-line `#` comment header on every CSV. Full UI-implication audit surfaced 17 CSV-consumer sites (3 pandas, 14 `csv.reader`/`DictReader`), Load Operation opportunity, hostname privacy concern, `exit_status.json` coexist-vs-replace decision.

**Eight design decisions** discussed, with Jeff pushing back and revising item 6 to "replace" (I had softly recommended "coexist" and reversed on the merits):

| # | Choice | Rationale |
|---|---|---|
| 1 | Vendor `picosha2.h` (MIT single header) | Small, permissive, one file |
| 2 | Bake git hash into `VERSION` at `git tag` time | Handles release tarballs without .git |
| 3 | Ship CSV `#` header unconditionally | Cleanest; all consumers updated in same patch |
| 4 | Sidecar filename `run_metadata.json` | Most self-explanatory |
| 5 | Land before electrolyte-fixed fix | Every day of uninstrumented output makes future forensics harder |
| 6 | Replace `exit_status.json` with `run_metadata.json` (revised from "coexist") | One canonical source of truth; two-file coexistence guarantees drift |
| 7 | Hostname toggle in Preferences, default include | Diagnostic-first alpha posture |
| 8 | Load Operation version-mismatch banner as follow-on | Initial patch has no operations with sidecar to test against |

### 4. Full patch applied

New files (backend): `RunMetadata.h`, `RunMetadata.cc`, `picosha2.h`, `version.h.in`.

Modified (backend): `CMakeLists.txt` (git-hash `execute_process` + `configure_file`), `.gitignore` (generated `version.h`), `thames.h` + `thames.cc` (initialize + finalize hooks on both hydration and elastic paths), `Controller.{h,cc}` (removed `writeExitStatus`; 15 CSV writers get `runmeta::csvCommentLine()`).

Modified (UI): `hydration_input_service.py` (ui_context injection into simparams), `user_config.py` (new `include_hostname_in_metadata` field), `preferences_dialog.py` (checkbox for it), `operations_monitoring_panel.py` (`run_metadata.json` reader replaced the `exit_status.json` reader).

CSV consumer defense: 12 files, 17 sites — 3 pandas gain `comment='#'`, 14 `csv.reader`/`DictReader` gain a skip-`#` generator idiom.

Docs: `docs/NIST-diagnostic.md` first pickup log entry.

Landed as super-repo `868e9cba` + submodule `0d2013b`.

### 5. Phase 1-3 backend testing — passed

- **Phase 1 (macOS build):** clean rebuild. `version.h` correctly stamped with real git hash (`1bdf5d5c`) and UTC build date.
- **Phase 2 (sidecar smoke):** Ca11mM fixture, 1.2 h simulation, 27 s wall. Full schema populated; `exit_status.json` correctly absent; CSV `#` headers on every inspected file; backend log shows `RunMetadata initialized` and `RunMetadata finalized: Simulation completed successfully`.
- **Phase 3 (regression byte-diff):** **29/29 CSVs byte-identical** to Session 57 baseline (accounting for the new `#` header). 15 CSVs with headers verified identical after strip; 14 CSVs untouched (PSDs + Colors — written outside `Controller.cc`) byte-identical as-is. Zero simulation-output regressions. DCH SHA-256 (`553987f3…`) exactly matched `shasum -a 256`.

### 6. Jeff asked about compiler + flags metadata — added (schema v2)

Bumped `schema_version` from 1 to 2. New `"build"` block in `run_metadata.json`:
- `compiler_id` (e.g. `"AppleClang"`)
- `compiler_version` (e.g. `"21.0.0.21000101"`)
- `cxx_flags` (verbatim `CMAKE_CXX_FLAGS`)
- `cmake_version` (e.g. `"4.4.2"`)
- `build_type` (Debug/Release/RelWithDebInfo/unset)

Required moving `configure_file` in `CMakeLists.txt` to run AFTER the compiler-specific branches, and mirroring `add_compile_options` into `CMAKE_CXX_FLAGS` on Clang so the flag string gets captured correctly. Purpose: instant "identical build?" check during cross-host divergence investigations.

### 7. Phase 4 UI integration — 5 tests

- **Test 1 (fresh op, happy path):** PASS.
- **Test 2 (failure banner):** Deferred first — Bug A crashes before `runmeta::initialize` could fire, so no sidecar existed to trigger the reader. Also Jeff observed the F2 regression (Running → Pending on backend crash) which blocked banner testing entirely. Re-tested LATER after F1 + F2 fixes landed.
- **Test 3 (hostname toggle):** Initially FAILED. Root cause: my `_build_ui_context` called `get_config_manager()` which doesn't exist in `config_manager.py`; the ImportError was caught by a bare `except Exception` and silently swallowed. Fixed to use `get_service_container().config_manager` (canonical singleton accessor). Also added info-level log for future preference-plumbing issues. Both directions verified after fix.
- **Test 4 (legacy op compatibility):** READ-VERIFIED. Jeff tried to copy the NIST Hydration-test-1 folder into the operations dir; Sync-with-Filesystem flagged it as an "Orphaned Folder" and offered to delete it. Confirms the UI has no "Import operation from folder" workflow. Missing-metadata guard in `_check_hydration_exit_status` is provably correct from code inspection.
- **Test 5 (CSV consumers):** PASS. All viewers render cleanly with `#` header present. During exercise, Jeff noticed pH and DOR aren't plottable in the UI despite being in the CSV output — logged.

### 8. F2 — Running → Pending on backend crash (SHIP-BLOCKER, fixed)

Investigation traced through `operations_monitoring_panel.py` polling → DB refresh → `_convert_db_status_to_ui_status`. **Root cause: two `status_mapping` dicts (lines 5623 and 5853) were missing `'ERROR'`**. Chain of events:

1. Op launches. DB status = `"RUNNING"`. UI shows "Running 5%" (default reconciler-assigned progress).
2. Backend crashes at 12ms.
3. Hydration executor's monitor thread (`hydration_executor_service.py:399-419`) polls the child every 15s. On seeing dead process + no output files, calls `_update_operation_status(name, OperationStatus.ERROR)` → DB status = `"ERROR"`.
4. UI's polling loop does `_convert_db_status_to_ui_status("ERROR")`. That key is absent from the mapping dict; falls back to `OperationStatus.PENDING`.
5. Line 5688-5689 overwrites in-memory RUNNING → PENDING.
6. `_validate_operations_data` zeroes the progress (line 6054) because "PENDING with non-zero progress" is treated as anomaly.
7. Result: "Pending 0%" indefinitely, with Duration continuing to tick.

`models/operation.py:25` explicitly documents `"ERROR"` as an alias for `"FAILED"` for backward compatibility — but the UI reader was never updated to honor that alias.

**Fix:** added `'ERROR': OperationStatus.FAILED` to both mapping dicts. Swapped the silent fallback for a logged warning so future missing statuses surface immediately.

**Verified by Jeff:** Bug A op now goes RUNNING → FAILED cleanly, no red icon (cosmetic follow-up) but the status column correctly reads "Failed".

### 9. F1 — runmeta::initialize fires too late

`runmeta::initialize` was called AFTER `prepOutputFolder` at line 613. But `ChemicalSystem` construction (where Bug A throws) happens at line 192, before either. Bug-A-class crashes left zero provenance.

**Fix:**
- Moved `runmeta::initialize` to fire right after `simParamName` capture (line 193), BEFORE `ChemicalSystem` construction.
- Added specific `runmeta::finalize` calls in each ChemicalSystem catch block with reasons like `"ChemicalSystem constructor: DataException"`.
- Made `runmeta::finalize` idempotent (first-call-wins) so specific catch-block reasons don't get overwritten by a generic fallback.
- Added generic fallback `runmeta::finalize(1, "Backend died before completion", ...)` at top of `deleteDynAllocMem` — covers any error path that didn't stamp its own reason.
- **CRLF-line-ending bug fix in `extractDchName`:** while testing on NIST's Windows-authored `input.in`, `getline(cin, ...)` on POSIX keeps the trailing `\r`, so paths like `"thames-dat.lst\r"` don't exist. Added `rstrip()` helper applied to all three `initialize()` arguments.

**Verified by Jeff:** Bug A op now produces a complete `run_metadata.json` with `exit_reason: "ChemicalSystem constructor: DataException"`, DCH sha256 populated, build identity captured.

### 10. Load Operation microstructure-swap ship-blocker (fixed)

Jeff noticed while exploring the Hydration Panel that Load Operation restores everything EXCEPT the microstructure — silently uses whatever's in the (now-disabled) picker. Elevated to ship-blocker per Jeff: scientific-reproducibility bugs beat status-display bugs.

Investigation revealed `_load_from_operation` at `thames_hydration_panel.py:1849` explicitly logs `"Note: Select the desired input microstructure before running."` — a prior developer knew and left a text-only warning that's trivially ignored. Also confirmed `_hydration_config.json` doesn't store the microstructure filename at all; only lives in `input.in` line 4.

**Fix:**
- `HydrationInputConfig` gained a `microstructure_file` field (basename only). Populated from `self.selected_microstructure_path.name` at config-build time. Legacy configs decode as empty string.
- New `_restore_microstructure_for_loaded_op` helper: reads `config.microstructure_file` first; falls back to parsing line 4 of `<operation_dir>/input.in` for legacy configs; looks up basename in the combo model, then in the operation folder itself. Programmatically fires the combo's `changed` signal so all downstream state (phase mapping, product selector, refs label) updates.
- Strong warning ONLY on restoration failure; confirmation of which microstructure was restored on success.

**Verified by Jeff:** create fresh op with X → switch picker to Y → Load Operation on the first → picker correctly reverts to X, log confirms.

### 11. Late-session Bug A root-cause candidate

Jeff's Zoom with the NIST user surfaced that the **Windows UI is silently auto-including glass phases (CAS2 and others) as hydration products even when they are NOT in the initial microstructure**. The macOS UI does not do this. Jeff has not yet verified on his own Windows box.

**Almost certainly Bug A's root cause.** Session 37 added `(am)` suffix to five glass phases (`C2AS`, `CA2S`, `CAS`, `CAS2`, `K6A2S`). If the Windows UI injects one WITHOUT the suffix, OR injects one that isn't in the microstructure, the backend receives an unmatchable phase name → `parseMicroPhases` throws DataException with exactly the Bug A message.

Logged in both `docs/NIST-diagnostic.md` and `docs/POST_ALPHA_TODOS.md` with concrete investigation plan (diff `_hydration_config.json` `hydration_products` arrays across platforms). If confirmed, Bug A collapses from a scary backend crash to a simple UI-side default fix.

### 12. venv rot side quest (not code work but blocked Phase 4)

`thames-env` was created against Python 3.11 originally, then someone/something ran `python -m venv` against 3.14 later, upgrading interpreter symlinks but leaving 3.11's site-packages tree. Homebrew's Python 3.11 Cellar path shifted between patch versions, breaking the 3.11 symlink. Result: prompt showed `thames-env` active but no `python` found, no `gi` module, no `psutil`. Nuked and rebuilt against `/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv`, reinstalled from `requirements.txt`, added missing `psutil` (was declared only in `thames-windows.spec:93` hidden imports, not in `requirements.txt`).

---

## POST_ALPHA_TODOS added this session

- **Windows UI auto-includes glass phases** — likely Bug A root cause (candidate for elevation to ship-blocker once confirmed)
- **Preferences Apply/OK/Cancel semantics** — post-Apply, Cancel doesn't undo (mild UX inconsistency; Jeff OK'd as-is)
- **No "Import operation from folder" workflow** — Sync only offers destructive path for orphans
- **Results Viewer can't plot pH or DOR** — despite both being in CSV output
- **Load Operation microstructure restoration** — filed as ship-blocker, then marked LANDED same session

---

## Ship-blockers open before NIST alpha-3 distribution

1. **Bug B** (portable `cp`/`mv`/`mkdir`) — draft ready in scratchpad, awaits Jeff's one-more-look.
2. **Windows UI glass-phase auto-inject** — investigate first; if this is Bug A's root cause, a UI fix collapses the whole class.

Both fixable in a single follow-on session.

---

## Session 59 pickup list

1. **Bug B application** — inspect the drafted patch, apply, submodule push + super-repo pointer bump, then Windows integration test.
2. **Bug A investigation** — diff `hydration_products` arrays across platforms for a fresh op; identify the platform-conditional injection site; fix and verify on both Mac and Windows.
3. **Windows access** — pending; a lot of alpha-3 validation blocks on it.
4. **Push** — nothing has been pushed this session; Session 58's four commits (two submodule + two super-repo) are local-only.
5. **Physics work backlog** (still open from Session 57):
   - JMAK-CSHQ implementation (natural next step to fix [Si] decay in Garrault validation)
   - `electrolyte_conditions "fixed"` bias fix
   - Priority-2 Portland cement rerun (~27 h wall)
   - C2S / C4AF calibration papers audit if any come to light

# Session 61 Windows Preparation

**Purpose.** Reduce OS-switch friction. The C++ backend has drifted substantially since the last Windows session (S45, alpha-2 in May 2026). Realistically the first 45-60 min of Session 61 will be environment reconcile + rebuild before any actual debugging.

**Written.** Session 60 (2026-08-23), macOS side, before switching to Windows.

**Session 61 scope (agreed with Jeff):**
1. Windows validation of S59 Bug A + Bug B fixes.
2. Windows glass-phase auto-inject investigation.
3. Package a patch for the NIST colleague.
4. Only then physics work per `docs/CNT_DIAGNOSTIC_PLAN.md`.

---

## What has changed since alpha-2 (S45, May 2026)

### New C++ files that must compile on MSYS2 toolchain for the first time

- `backend/thames-hydration/src/thameslib/NucleationRate.{h,cc}` (S51)
- `backend/thames-hydration/src/thameslib/NucleationParameters.h` (S51)
- `backend/thames-hydration/src/thameslib/SaturatingRate.h` + `SaturatingRateModel.{h,cc}` (S52)
- `backend/thames-hydration/src/thameslib/JMAKGrowth.{h,cc}` + `JMAKParameters.h` (S54)
- `backend/thames-hydration/src/thameslib/TransportStats.{h,cc}` + `TransportParameters.h` + `TransportCorrection.{h,cc}` (S55)
- `backend/thames-hydration/src/thameslib/RunMetadata.{h,cc}` + `version.h.in` + vendored `picosha2.h` (S58)

### CMakeLists.txt changes needing Windows verification

- `configure_file(version.h.in ...)` moved to run **after** compiler branches (S58) — needs verification the CMake generator on MSYS2 handles the reordering.
- `add_compile_options` mirrored into `CMAKE_CXX_FLAGS` on Clang so the flag string is captured (S58) — tested on macOS clang; MSYS2 clang or gcc may behave differently.

### S59 Bug B is the critical Windows test

Nine shell-out sites (`cp` / `mv` / `mkdir`) in `backend/thames-hydration/src/thames.cc` were replaced with `std::filesystem` in S59. C++17 already enabled but whether MSYS2's `<filesystem>` header links without extra flags is untested. If it fails, add `-lstdc++fs` to the link line — though modern MinGW-clang usually doesn't need this.

### Python environment drift

- `thames-env` on macOS was nuked and rebuilt against **Python 3.14** in S58. Windows `thames-env` is probably still Python 3.12 — needs rebuild.
- `requirements.txt` gained `psutil` in S58. Windows PyInstaller spec had it in hidden imports already but the venv needs a fresh `pip install`.
- New UI code from S58: `operations_monitoring_panel.py` reads `run_metadata.json` (not the deprecated `exit_status.json`); `HydrationInputConfig.microstructure_file` field added; hostname preference toggle added. All Python — should be cross-platform, but untested on Windows.

### Data-file drift

- DCH shifted for C3S (S56) and C3A (S57) — constant G° offsets. Windows will pull these; no local backup files exist on Windows (they're gitignored per-machine artifacts).
- S59 glass-phase `(am)` rename touched DCH + DBR + `src/data/database/thames.db` + `simparams_service.py::_get_thamesname` + `ChemicalSystem.cc` hardcoded `colorN_` initializers.
- **Windows user data dir (`%LOCALAPPDATA%\THAMES\operations\`) may contain pre-S59 operations with bare `C2AS` / `CAS2` / etc. in their `_phase_mapping.json`.** These will silently break on re-hydration. Scan for them before running anything (see below).

---

## Concrete command order — Session 61 opening sequence

Copy-paste these in order on Windows. Timing estimate: 45-60 min end-to-end assuming no errors.

```bash
# 1. Confirm working dir (must be the Desktop path per CLAUDE.md, not ~/THAMES)
cd /c/Users/jwbullard/Desktop/foo/THAMES

# 2. Sync repo + submodule
./pre-session-sync.sh
git submodule update --init --recursive
cd backend/thames-hydration
git log -1 --oneline    # confirm 808a5c0 or later (S59 submodule tip)
cd ../..

# 3. Toolchain audit — record what's on PATH
which clang && clang --version
which gcc   && gcc --version
which cmake && cmake --version
which python && python --version
ls thames-env/pyvenv.cfg 2>/dev/null      # what Python version was venv built with

# 4. Rebuild Python venv (only if Python < 3.14 or the pyvenv.cfg is stale)
rm -rf thames-env
python -m venv thames-env
source thames-env/Scripts/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. C++ backend rebuild — capture full log
./build-windows.sh 2>&1 | tee build.log

# 6. Sanity: binaries present
ls -la bin/thames.exe bin/micgen.exe 2>/dev/null

# 7. Pre-run defensive scan for pre-rename microstructures
find "$LOCALAPPDATA/THAMES/operations" -name "*_phase_mapping.json" \
  -exec grep -l -E '"(C2AS|CA2S|CAS|CAS2|K6A2S)"[^(]' {} \; 2>/dev/null
# Anything that matches → move to a scratch folder or regenerate before use.

# 8. Smoke test — launch UI, run a small Portland-only hydration
# (Any small microstructure, no fly ash for the first pass; add fly ash for auto-inject investigation.)
```

Only after Step 8 passes do you touch the Windows Bug A auto-inject debugging.

---

## Mac reference simparams.json — for the glass-phase diff

Two mac reference files are committed under `docs/reference_data/`. Use the **primary** one for the diagnostic; the secondary is retained as a pre-S59 corroboration point.

### Primary reference: `docs/reference_data/mac_reference_today.json`

**Provenance.** Generated 2026-08-23 (session 60) by Jeff on macOS with current post-S59 code, via UI operation `S61-ref-mac-today`. Portland-only mix, 22 microstructure phases, 79 entries in `suppressed_phases`, `hydration_products: null`, full `ui_context` block populated (Python 3.14.7, Darwin arm64, THAMES 1.0.0-alpha.2).

**Glass phases in this reference** — all appear in `suppressed_phases` with the post-S59 `(am)` suffix: `C2AS(am)`, `CA2S(am)`, `CAS(am)`, `CAS2(am)`, `K6A2S(am)` (plus `C2ASH55`, which is a hydrated glass-related phase, not one of the S37/S59 renamed set). **None appear in `hydration_products`, `microstructure.phases`, or elsewhere.** This is the correct clean state — the auto-inject bug puts glass phases into `hydration_products` or `microstructure.phases`.

**How to use for the Windows diff:**

1. On Windows, launch the current UI and set up a Portland-only hydration with the same defaults. Use operation name `S61-ref-win-today` to keep them straight. The specific microstructure doesn't have to match `S61-ref-mac-today`'s; what matters is that no fly-ash / SCM materials are selected and default Hydration Panel settings are accepted.
2. Locate the Windows-generated `simparams.json` under `%LOCALAPPDATA%\THAMES\operations\S61-ref-win-today\` and diff against `mac_reference_today.json`.
3. **Expected deltas** (not bugs, filter these out mentally):
   - `ui_context.platform_system`: `Darwin` → `Windows`
   - `ui_context.platform_release`, `.platform_machine`, `.hostname`, `.python_version`: differ
   - `ui_context.operation_name`: `S61-ref-mac-today` → `S61-ref-win-today`
   - Minor phase-count differences if the two microstructures chose different resolutions or clinker fractions
4. **Bug signals** (any of these = the auto-inject bug reproduced):
   - `hydration_products` is non-null in the Windows version. `mac_reference_today.json` shows `hydration_products: null` — the UI's Hydration Panel default did NOT put anything there on macOS. If Windows does, that's the smoking gun.
   - Extra glass-phase entries in `microstructure.phases` on Windows that aren't on mac.
   - A glass-phase name appears WITHOUT the `(am)` suffix anywhere in the Windows output. This would mean the Windows UI is injecting bare glass names — a distinct, worse variant of the bug that would re-open Bug A (parseMicroPhases crash) with a different trigger path.
5. If Windows shows NO auto-inject in the Portland-only flow, repeat with a fly-ash mix (`ClassF-FlyAsh` material). The auto-inject may only fire when fly ash IS in the mix.

### Secondary reference: `docs/reference_data/mac_simparams_reference.json`

**Provenance.** Older `Hydration-test-1/simparams.json` from Jeff's macOS `%LOCALAPPDATA%`. Portland-only (27 phases, 75 suppressed), captured **before S58 provenance and before S59 rename**. Bare glass names (`C2AS`, `CA2S`, `CAS`, `CAS2`, `K6A2S`) in `suppressed_phases`; no `ui_context` block; `hydration_products: null`.

**Use for.** Corroboration if the primary diff is ambiguous — comparing three-way (pre-S59 mac / current mac / Windows today) can help localize when a delta was introduced. Do not use as the primary diff target; the primary is a like-for-like current-code comparison.

---

## Highest-risk failure modes — mentally prepare for these

1. **`<filesystem>` link fails on MSYS2.** Symptom: build.log shows unresolved `std::__fs::filesystem::...`. Fix: add `-lstdc++fs` to the link line. Modern MinGW-clang usually doesn't need this; older gcc does.
2. **`configure_file(version.h.in)` runs before the compiler branch is resolved on the MSYS2 generator.** Symptom: `CXX_FLAGS_STRING` comes out empty in `version.h`. Fix: reorder the CMakeLists directives the same way S58 did for macOS.
3. **PyGObject reinstall fails without `PATH=/c/msys64/mingw64/bin:$PATH`** (S42 gotcha). Fix: prepend that path before `pip install`.
4. **UI can't find `%LOCALAPPDATA%\THAMES\` correctly** on a Windows box where it was created by a different Python version. Symptom: stale `.pyc` bytecode. Fix: `find . -name __pycache__ -exec rm -rf {} +` in the repo.
5. **The new `operations_monitoring_panel.py` `run_metadata.json` reader silently fails on old operations without a sidecar.** Symptom: empty or wrong status columns in the operations list for pre-S58 operations. This was surfaced as "no import workflow" in POST_ALPHA and is not blocking.
6. **`build-windows.sh` may need a refresh** based on what breaks. Don't touch it proactively — fix in the moment when a specific failure surfaces.

---

## Windows-specific gotchas to remember

- **Working dir MUST be `C:\Users\jwbullard\Desktop\foo\THAMES`**, not `C:\Users\jwbullard\THAMES`. Micgen stack overflows if run from the shorter path (S33).
- **Interactive flags disabled by harness** — no `git rebase -i` etc.
- **Subprocess spawn on Windows** needs `creationflags=subprocess.CREATE_NO_WINDOW` to avoid a flash console. Already in the codebase; don't undo it.

---

## Handoff to Session 61

Read this doc first. Then execute the command order above. Report back the toolchain audit output (Step 3) and the build.log tail (Step 5) so we know what environment we're actually in. Only then start on the Windows Bug A / Bug B validation.

The mac reference for the glass-phase diff is at `docs/reference_data/mac_simparams_reference.json`.

The CNT physics diagnostic plan at `docs/CNT_DIAGNOSTIC_PLAN.md` is deferred until Windows is validated and the NIST patch is out.

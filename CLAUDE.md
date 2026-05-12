# THAMES Project - Claude Context

## Project Overview

THAMES is a GTK-based application for advanced cement hydration simulation, using the THAMES-Hydration C++ simulator. This project is based on the VCCTL architecture but adapted for the upgraded hydration simulation engine.

**Based on:** VCCTL v10.0.0
**Hydration Engine:** THAMES-Hydration (C++)
**Started:** November 2025

## Key Differences from VCCTL

- **Hydration Simulator**: VCCTL uses disrealnew.c (C); THAMES uses THAMES-Hydration (C++)
- **Materials**: VCCTL uses per-type tables (cement, fly_ash, slag, etc.); THAMES uses a unified `material` table with tag-based classification and GEMS phase composition
- **Thermodynamics**: THAMES integrates GEMS3K (100 phases, 198 DCs, 277-353K temperature range)

## Development Sessions

### Sessions 1-10 (November 2025): Foundation
- **Session 1-2**: Repository setup, GEMS3K integration, tag-based materials architecture
- **Session 3-5**: Material database schema, migrated 36 cements + 1 limestone from VCCTL, PSD system (5 distribution types), clinker fraction editor
- **Session 6-7**: Phase ID mapping service (0=VOID, 1=ELECTROLYTE, 2-7=Clinker, 8=AGGREGATE, 9+=Other), MicgenInputService implementation
- **Session 8**: Phase color service (~90 GEMS phase colors), Results Viewer with THAMES support
- **Session 9-10**: Hydration Panel UI (electrolyte editor, product tree, kinetic model editing for all 4 model types)

### Sessions 11-18 (December 2025): Visualization & Elastic Moduli
- **Session 11-12**: Hydration progress tracking, kinetic preferences system, data plots (multi-select, log axes, export)
- **Session 13-14**: Elastic moduli UI, executable path standardization to `bin/`, GEMS database file handling
- **Session 15**: Unified voxel ordering (X-fastest) across micgen, THAMES C++, and Python/VTK
- **Session 16**: Multi-temperature GEMS database (277-353K), expanded to 82 hydration products
- **Session 17-18**: Elastic/strain energy visualization, 3D orientation axes, Homebrew safety (pinned pygobject3, py3cairo, gobject-introspection)

### Sessions 19-22 (Dec 2025 - Jan 2026): Windows Platform
- **Session 19**: Windows dev environment (MSYS2 Python 3.12.12, PyGObject 3.54.3), Unicode arrow fix, GTK CSS platform check
- **Session 20**: Windows C++ backend build, ImageMagick removal (replaced with PngWriter.h using libpng), particle shape sets copied from VCCTL
- **Session 21**: Switched to Clang on Windows, fixed `long int` → `long long int` (32-bit on Windows vs 64-bit on macOS), Git LFS for `*.tar.gz`
- **Session 22**: W/B ratio limits removed (up to 10000 for dilute suspensions), adaptive time units for progress display

### Sessions 23-30 (Jan-Feb 2026): Adaptive Time Stepping
- **Session 23**: Deep analysis of THAMES C++ time stepping and GEMS3K solver; created implementation plan (`docs/adaptive_timestepping_implementation_plan.md`)
- **Session 24**: Implemented AdaptiveTimeController class + GEMS convergence accessors (getPCI, getDXM, getConvergenceRatio); removed random guessing from calculateState()
- **Session 25**: Testing — raised ICTHRESH to 1e-8, checkICMoles() every cycle; kinetics-based initial timestep (estimateInitialDissolutionRate for PK, Standard, Pozzolanic models)
- **Session 26**: User Manual created (`docs/USER_MANUAL.md`, ~1,100 lines); Result-Adaptive-04 baseline performance
- **Session 27**: Sub-minute output filenames (added seconds: `00h00m18s`), smaller minimum timestep (1e-5 hours)
- **Session 28**: Model-aware adaptive parameters (SI-driven vs DOR-driven); fast-dissolving phase exclusions (Bassanite, Gypsum, Arcanite, Thenardite); electrolyte duplicate DC detection in UI
- **Session 29**: Fixed GEMS phase name vs DC name confusion (hydrotalcite→OH-hydrotalc, zeoliteP_Ca→ZeoliteP); added Anhydrite to fast-dissolving exclusions; multi-simulation comparison plotting
- **Session 30**: Simplified to unified adaptive parameters (dt_initial=0.001h, dt_max=4h, growth_factor=1.5); IC depletion recovery with charge compensation; exit_status.json + UI alerts

### Sessions 31-32 (Feb 2026): Documentation & UI Config
- **Session 31**: Integrated 26 screenshots into User Manual, restructured sections (merged Microstructure into Mix Design)
- **Session 32**: Configurable adaptive time stepping UI (7 SpinButtons in Hydration panel → simparams.json); IC_FLOOR=1e-5 proactive depletion prevention; runtime electrolyte concentration safety (minConc = IC_FLOOR / waterMass); concentration_overrides.json + UI notification

### Session 33: Micgen Windows Crash Debugging
March 19, 2026 — Windows 10

- Stack-allocated arrays (`struct lineitem line[MAXLINES]` = 1.7 MB) exceeded Windows 1 MB stack; fixed with `static`
- Bbox array bounds mismatch (0.75 vs 0.8 of systemsize) caused buffer overflow; fixed allocation
- Added `-Wl,--stack,8388608` linker flag for Windows as defense-in-depth
- Segfault during `freemicgen()` exit cleanup persists (after output written, low priority)

**IMPORTANT — Windows Working Directory:** Always work from `C:\Users\jwbullard\Desktop\foo\THAMES` on Windows, NOT `C:\Users\jwbullard\THAMES`.

### Session 34: Suppressed Phases, Time Unit Seconds & Submodule Merge
March 20, 2026 — macOS

- **Suppressed phases feature**: UI unchecked phases → `suppressed_phases` list in simparams.json → Controller reads list → maps phase→DC via nDCinPH → `addSuppressedDC()` → `initDCUpperLimit()` skips suppressed DCs (keeps at 0.0)
- Added "seconds" to all time unit dropdowns; unit combos for dt_initial/dt_max
- Empty category row fix in hydration product selector
- Merged adaptive-timestepping branch (12 commits, +2236 lines) into main

### Session 35: Early Termination Bug Fix, UI Decimal Places & macOS Signing
March 27, 2026 — macOS

- **Critical**: `time_[]` vector entries overwritten with cycle times; fixed by using `initialLastTime` (3 locations)
- 4 decimal places for all floating-point SpinButtons in adaptive stepping and kinetic editor
- macOS code signing: added `codesign --force --sign -` as POST_BUILD step in CMakeLists.txt

### Session 36: Time Vector Bounds Fix, Kinetics Floor & False Termination Fix
March 28, 2026 — macOS

- `time_[lastGoodI]` out-of-bounds write when cycles exceeded vector size; added bounds check
- `computeKineticsBasedMaxTimestep()` could return ~1e-13; enforced `stepTimeTHR_` (1e-5 hours) as minimum
- False "FINAL TIME REACHED" termination: now also requires `initialLastTime - lastGoodTime_ < 1e-6`

### Session 37: Lattice Retry Limit, UI Race Condition & Glass Phase Names
March 29-31, 2026 — macOS

- `while (changeLattice == 0)` infinite loop: added MAX_LATTICE_RETRIES=50 with voxel_mismatch.log
- Progress polling race condition: moved polling start into `_on_simulation_started()` callback
- 5 glass phases needed `(am)` suffix (C2AS, CA2S, CAS, CAS2, K6A2S) to prevent crystalline behavior

### Session 38: Post-Failure Kinetics Constraint Fix
March 31 - April 1, 2026 — macOS

- **Critical**: GEMS failure recovery path bypassed kinetics timestep constraint; after failure, `recordFailure()` returned ~1.0h (1000x too large); caused IC overshoot → IC recovery injection → SI explosion
- Fix: Apply `computeKineticsBasedMaxTimestep()` on failure path same as success path

### Session 39: Windows Sync, Micgen Fix, 3D Layout & Load Operation Feature
April 4, 2026 — Windows 10

- Pre-session sync of Sessions 34-38; clean C++ rebuild
- Created `build-windows.sh` and `build-macos.sh`
- Micgen divide-by-zero fix: `numchunk = total/100` produced 0 for <100 particles; fix: `if (numchunk < 1) numchunk = 1`
- 3D viewer control panel reorganized into two rows
- **Load Operation feature**: radio buttons for "New simulation" vs "Load from previous operation"; combo dropdown populates from `*_hydration_config.json` files; loads all UI widgets (temperature, electrolyte, products, kinetics, time params, adaptive stepping, runtime options)

### Session 40: Material Migration, VCCTL Cleanup & Aggregate Shapes
April 14, 2026 — macOS

- **Material migration**: Migrated 5 materials from VCCTL legacy tables to THAMES unified material table (undensifiedSF, Quartz-Fine, periclase, quartz-inert, psdFiller); 2 corundum entries not migrated (no GEMS Al2O3 phase)
- **VCCTL removal from Materials Panel**: Removed all 6 VCCTL legacy material loading blocks from `material_table.py`; removed VCCTL type dispatch from selection, deletion, duplication, export handlers; simplified `_get_material_type()`, `_duplicate_material()`, `_delete_material()`, `_generate_unique_material_name()` in `materials_panel.py`; removed 7 dead VCCTL copy methods (~290 lines)
- **Aggregate decision**: Aggregates kept in separate pipeline (own UI in Mix Design with fine/coarse selection, grading curves, mechanical properties); they don't use GEMS phases
- **Aggregate shape data**: Copied `aggregate.tar.gz` (185 MB) from VCCTL; extracted to app support directory; Git LFS tracks via existing `*.tar.gz` rule; extraction logic in `directories_service.py` already handles first-launch extraction
- **Build script fix**: Fixed kva2json linker race condition in `build-macos.sh`
- **Hydration panel**: dt_max lower bound reduced to 0.001 seconds; "timestep" → "time step" rename; Load Operation UI restructured with radio buttons + combo box

### Session 41: Concelas Integration — Concrete-Scale Elastic Moduli
April 20-21, 2026 — macOS

- **Python concelas port**: Ported multi-scale concrete moduli algorithm from VCCTL `backend/src/elastic.c:2942-3559` to `src/app/services/concelas_service.py` (pure algorithms) and `concelas_runner.py` (CSV I/O + orchestration); no C++ backend changes; 37 unit tests passing
- **Completion hook wiring**: Post-completion hook in `operations_monitoring_panel.py` reads `concelas_inputs.json` and calls `run_and_append()` after `thames -s 5` completes; appends 13 Concrete/ITZ/Mortar rows to `EffectiveModuli.csv` plus `ConcelasLog.txt`
- **UI unblock**: Removed four `thames_mode` gating points in `elastic_moduli_panel.py` (warning banner, ITZ checkbox hide, disable-aggregate-settings, lineage fallback text); ITZ checkbox now auto-enabled when lineage returns aggregate
- **Effective Moduli Viewer**: Added ITZ property bucket, renamed EFFECTIVE MODULI → BINDER EFFECTIVE MODULI, ordered sections Binder / Concrete / ITZ
- **UX polish**: Source label shows red VF=0 warning when microstructure has no aggregate slab; Mix Design pops pre-generation dialog for orphan aggregate metadata (name set, mass=0)
- **Post-alpha TODO system**: Created `docs/POST_ALPHA_TODOS.md` with format template; seeded with 5 entries (headline: adaptive-timestep near-depletion stall)
- **Stop/cancel persistence bug fix**: `_stop_operation` and `cancel_operation` in `operations_monitoring_panel.py` never persisted `CANCELLED` to the database — stopped ops kept showing as `RUNNING` and resurrected on every app launch (phantom "restart" dialog). Added DB write on both paths plus a startup reconciliation in `_load_operations_from_database` that flips any orphaned `RUNNING` record (no live process) to `CANCELLED`. Reconciled existing DB state once via direct SQL.
- **Help menu overhaul**: Help → User Guide / Getting Started / Troubleshooting previously either errored ("Documentation Not Found" from defunct MkDocs paths) or handed the .md to whatever external viewer macOS/Windows/Linux had registered. Rewrote `documentation_viewer.py` to render `docs/USER_MANUAL.md` to a single-file HTML on demand using Python-Markdown (new dep: `markdown>=3.4.0`; added to both PyInstaller specs). Target section is baked into the HTML as `window.__THAMES_TARGET_SECTION` rather than passed via URL fragment (fragments are unreliable through macOS `osascript → open location → browser` pipeline). Internal TOC links use fragment-only `href="#..."` that work natively once on the page. Image paths pre-absolutized to avoid `<base href>` which would break fragment navigation.
- **About dialog**: Credits pane previously showed literal `<span size="small">Texas A&M University</span>` for the first author — GTK's Credits pane runs each line through Pango markup parser; `&` in "A&M" looked like an HTML entity start and failed. Fixed by pre-escaping `&` → `&amp;` in the authors list. Also consolidated all About-dialog strings to read from `app_info.py` (single source of truth).
- **Version bump**: `APP_VERSION` 10.0.0 → **`1.0.0-alpha.1`** (SemVer 2.0.0 pre-release). New `APP_VERSION_STAGE` constant shows an "ALPHA pre-release" banner in the About dialog. Annotated tag `v1.0.0-alpha.1` created and pushed.
- **Windows alpha prep**: new `docs/ALPHA_RELEASE_PREPARATION.md` is a 10-step Windows packaging recipe (sync → deps → smoke test → PyInstaller → Inno Setup → README → GitHub pre-release).
- End-to-end validated on 7-day ccr152-concrete: paste K=19.5 G=10.2, concrete K=22.9 G=12.7, ITZ K=16.8 G=8.5, concrete cube strength 20.2 MPa (reasonable for 7-day mortar)

### Session 42: Windows Alpha Smoke Test, UI Fixes & Release Packaging
April 23-24, 2026 — Windows 10

- **Smoke test (Step 4 of `docs/ALPHA_RELEASE_PREPARATION.md`)**: 4.1 Help menu, 4.2 Stop/cancel persistence, 4.3 Concelas pipeline all PASSED. Step 4.4 (orphan-aggregate dialog) revealed UX gaps that drove the next several fixes.
- **Mix Design — orphan prevention at source**: New `_apply_aggregate_gating()` in `mix_design_panel.py` disables aggregate combo, grading button + template label, shape combo, and air content spin until that side's mass spin > 0. Re-entering mass = 0 resets and clears the side. Wired from `_on_mass_changed` (skipping during `_loading_in_progress`) plus a final reconciliation call at end of `_populate_ui_from_mix_design`. Eliminates the ability to save aggregate metadata for a microstructure that has no aggregate slab.
- **Elastic Moduli — defensive lock when no real aggregate**: In `_populate_from_resolved_lineage`, compute `fine_has_real_aggregate = bool(fine_agg and VF > 0)` (similarly coarse). If neither is real, both Include-aggregate checkboxes AND the ITZ checkbox are unchecked AND made insensitive — user cannot opt into concelas post-processing for a microstructure that has no slab. Same treatment added to `_update_ui_from_operation` for saved-elastic-op loads. Backend was already safe (`_write_concelas_inputs_json` short-circuits on no aggregate).
- **Elastic Moduli — reset disabled inputs**: New `_reset_aggregate_inputs(agg_type)` helper resets one side's volume/bulk/shear/grading entry/grading status to creation defaults (0.0, 37.0, 44.0, blank, blank) so disabled controls don't display stale values from a prior selection. Called in both no-aggregate branches of both populate paths.
- **Elastic Moduli — informational warnings**: Switched four `foreground="#D32F2F"` (red) markups to `foreground="#B8860B"` (DarkGoldenRod) so users read "no aggregate slab" as informational rather than as an error.
- **Hydration Product Selector — clickable pencil icon**: The pencil icon in column 5 of the phase tree was a `Gtk.CellRendererPixbuf` rendered for selected rows but had no click handler — it looked clickable but only `row-activated` (double-click) opened the config dialog. Added `_on_treeview_button_press` that uses `get_path_at_pos` to detect single-clicks landing in the config column on selected non-category rows, and emits `configure-phase` (same payload as the double-click path). Returns False on other columns so default tree handling (checkbox toggle, selection) is preserved.
- **Aggregate shape sets missing on Windows**: Mix Design shape combos showed only "sphere" because `%LOCALAPPDATA%\THAMES\aggregate\` was empty. Root cause: `directories_service.py:58-59` returns early in dev mode (`return # Don't extract in development mode`), so `aggregate.tar.gz` only auto-extracts inside a PyInstaller bundle. macOS happened to work because the user data dir was already populated from a prior bundle run. Manually extracted `tar -xzf aggregate.tar.gz -C "$LOCALAPPDATA/THAMES/"` (36 shape directories). Logged the dev-mode auto-extract gap as a `POST_ALPHA_TODOS.md` candidate.
- **Operations reconciler — live-process incident**: User left two `micgen.exe` operations running. I killed `python.exe` to relaunch the UI (between fix iterations); UI restart flagged the running operations as `CANCELLED` because the reconciliation in `_load_operations_from_database` only checks the original UI-tracked PID, not the spawned children. User deleted the "cancelled" operations from the UI; DB rows removed but on-disk operation folders survived AND the still-live `micgen.exe` processes continued writing to them. Killed two stale `micgen.exe`, removed `ccr140-FlyAsh-orphan_01` and `_02` operation folders. Logged a new `POST_ALPHA_TODOS.md` entry: persist child PID/image/cwd at launch and reattach via `psutil` on UI restart instead of trusting only the parent PID. Also saved a feedback memory: do not restart the THAMES UI without explicit user permission.
- **VCCTL release process investigation**: Spawned Explore agent to compare VCCTL packaging (`docs/PACKAGING.md`, `scripts/build_windows.bat`, `vcctl-windows.spec`, `.github/workflows/build.yml`) to the THAMES alpha plan. Findings: tarball bundling and PyInstaller GTK DLL collection patterns are essentially identical; main gap was no Inno Setup template (VCCTL auto-generates NSIS at build time). Recommended Inno Setup over NSIS for maintainability.
- **Spec file fixes (`thames-windows.spec`)**: Replaced 27 stale VCCTL legacy executable references in the Windows binaries block (`backend/bin-windows/genmic.exe`, `disrealnew.exe`, `elastic.exe`, etc.) with the three actual THAMES backend artifacts (`bin/thames.exe`, `bin/micgen.exe`, `bin/libpng16-16.dll`); the legacy paths never existed in THAMES so PyInstaller aborted at the first binary. Dropped missing `vcctl-docs/site` data reference (no longer ship prebuilt MkDocs site) and optional `colors/colors.csv` (runtime falls back to default phase mapping). Also added `scipy` hidden imports earlier in session for `micgen_input_service` log-normal PSD usage. **Note: `thames-macos.spec` has the same VCCTL-legacy executable problem latent — separate fix needed.**
- **Inno Setup script**: New `installer/thames-windows.iss` produces user-local install at `%LOCALAPPDATA%\Programs\THAMES\` (no admin / no UAC), Start Menu + optional desktop shortcut, Add/Remove Programs entry, LZMA2/ultra compression. Critically, uninstaller removes only the program tree — user data at `%LOCALAPPDATA%\THAMES\` (operations, database, aggregate cache) is intentionally untouched so testers don't lose work on uninstall + reinstall. ISCC found at `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` (per-user install).
- **PyInstaller GI hook PATH fix**: Build aborted with `ValueError: Could not resolve any shared library of Gio 2.0: ['libgio-2.0-0.dll']`. Workaround: prepend `C:\msys64\mingw64\bin` to PATH at PyInstaller invocation (`PATH="/c/msys64/mingw64/bin:$PATH" pyinstaller thames-windows.spec --noconfirm`). The DLL is found by Python's import machinery without it but PyInstaller's hook does a separate `ctypes.util.find_library`-style lookup that needs the Windows-format PATH.
- **ZIP wrapping**: Windows `tar -a -cf foo.zip` does NOT compress when the extension is `.zip` — produces an uncompressed-tar file with `.zip` extension (verified by checking magic bytes: "THAM" instead of "PK\x03\x04"). Switched to Python `zipfile.ZipFile(..., ZIP_DEFLATED, compresslevel=6, allowZip64=True)`. 1.43 GB raw → 760 MB compressed in 48 seconds.
- **LICENSE → LICENSE.md**: Renamed via `git mv` to preserve history. Content unchanged (MIT, copyright 2025 jwbullard). Updated `installer/thames-windows.iss` `LicenseFile=..\LICENSE.md` reference.
- **README.md rewrite**: 96-byte placeholder rewritten as a proper landing page: status/license/version badges, hero screenshot (`docs/images/01-main-window.png`), download section linking to GitHub releases, quick-start walkthrough, architecture table acknowledging VCCTL/GEMS3K/THAMES-Hydration lineage, user-data layout note, build-from-source recipe with the MSYS2 PATH trick, **Contributors section** (Bullard PI; Nita TAMU for performance/accuracy of C++ hydration model), and Acknowledgements (NIST + PSI).
- **Version bump and tag move**: `APP_VERSION` 1.0.0-alpha.1 → 1.0.0-alpha.2. Two commits: 5ae9c31e (UI fixes) and 3b84512a (Windows packaging + LICENSE rename + README). Tag `v1.0.0-alpha.2` force-moved from cb895724 → ed6f90fa to include the packaging commit (only one developer with the tag pulled, force-push safe). `main` and tag both pushed to origin.
- **Distribution artifacts produced in `dist/`**:
  - `THAMES-1.0.0-alpha.2-setup.exe` (~105 MB Inno Setup installer, LZMA2/ultra)
  - `THAMES-1.0.0-alpha.2-win64.zip` (~760 MB portable ZIP, DEFLATE)
  - `THAMES-1.0.0-alpha.2-README.txt` (alpha tester README with install instructions for both formats, known limitations, getting started)
- **Pending when session resumes**: Smoke-test bundled `dist\THAMES\THAMES.exe` on this machine; install `setup.exe` in Windows Sandbox (built into Win10 Enterprise, disposable VM) to validate fresh-install + first-launch extraction; `gh release create v1.0.0-alpha.2 --prerelease` to publish. Steps 8-10 of `docs/ALPHA_RELEASE_PREPARATION.md`.

### Session 43: Second Alpha Pass — DB Cleanup, UI Polish, v1.0.0-alpha.2 Re-Released
April 27, 2026 — Windows 10

User returned with the conclusion that alpha.2 was not actually ready: too many small bugs surfaced during testing. Deleted the `v1.0.0-alpha.2` tag (local + origin) — tag-only force-push was safe since user is sole consumer. Then a second cleanup-and-fix pass:

- **Materials database cleanup**: Five partially-migrated VCCTL cements deleted (`ma160`, `ma165`, `ma178`, `rossi`, `sacci-425` — `has_clinker=0` with only 2-3 phases out of 7); user-created `Clinker152` deleted via direct SQL because the Materials Panel UI delete was silently no-op'ing for it; `cement16{130,131,132,133,134,148,149,150,155,594}` renamed to `clinker16XXX` (these are clinker raw materials, not finished cements; `cement168` left alone because it has only 1 trailing digit, distinct pattern); `cementhoc/otc/rci` renamed to `clinkerhoc/otc/rci`. 19 ops in one transaction; material count 43 → 37.
- **Specific gravity recalc from GEMS**: Wrote a parser for `src/data/gems/thames-dch.dat` that extracts DC names, molar masses (kg/mol), and standard molar volumes (m³/mol) at T=297.15K (the closest grid point to 298.15K), derives `density = mm/V0` for every single-DC phase (skipping multi-DC solid solutions like CSHQ-* and zero-V0 phases), then for each material with a `material_phase` composition computes `SG = 1/Σ(mf_i/SG_i)` and updates the DB if the recalculated value differs from the stored one. 32 of 37 materials updated; the 5 unchanged were already correct (Portlandite 2.24, Gypsum 2.31, ClassF-FlyAsh 2.63, LS-RealShape 2.71, ma157-real 3.14). Most cements moved from the cement-model default of 3.15 to ~3.10-3.20 (typical Portland range). `NormalLimestone` corrected 2.65 → 2.71.
- **VCCTL migration root cause analysis**: User asked why ma157 was still broken after deletion of the obvious-broken five. Investigation: ma157 is **faithfully migrated** — VCCTL's own DB has 5 of 7 correlation BLOBs (`sil`, `c3s`, `alu`, `c3a`, `n2o` at 713 bytes each; `c4f`, `k2o` are NULL in VCCTL too) and **all 6 surface fractions are NULL in VCCTL**. So the migration didn't fail; the source was incomplete. The 27 other "NULL_CORR" materials are likewise faithful copies of partial VCCTL data. Recoverable from VCCTL: nothing more than what's already there. Recoverable from the description text: ma157's 6 surface fractions (the description includes a "PHASE / AREA / PERIMETER (SURFACE)" table). Backfilled ma157 with C3S=0.5611, C2S=0.2396, C3A=0.1200, C4AF=0.0672, K2SO4=0.0120, Na2SO4=0.0 (sums to 0.9999).
- **`_copy_clinker_extension_data` rewrite (Bug B)**: User-created `ma157-real` (a duplicate of ma157 made through the UI for testing) had `has_clinker=1` but no `clinker_extension` row at all, causing the input generator to raise "ClinkerExtension not found for material ID 49" and SmokeIt to fail silently before micgen launched. Root cause: `_copy_clinker_extension_data` in `materials_panel.py` called `service.get_clinker_surface_fractions(source)` which returns `{c3s: 0.0, c2s: 0.0, ...}` for NULL fractions (the model's `or 0.0` default in `get_surface_fractions_dict`), then `service.set_clinker_surface_fractions(target, ...)` called `validate_surface_fractions()` which rejected the all-zero composition (sum 0 != 1.0), raising `ServiceError`. The outer `try/except` swallowed it and exited before the correlation-copy loop, so the duplicate ended up with no row. Rewrote `_copy_clinker_extension_data` to do a direct `INSERT INTO clinker_extension (...) SELECT ... FROM clinker_extension WHERE material_id=?` via raw SQL — bypasses the validators entirely. Idempotent (DELETEs target row first). Verified scan: 31 clinker materials, every one now has a row, every one has 6/6 surface fractions.
- **Materials Panel — three small fixes**: (a) Row checkboxes now actually toggle: added `_on_checkbox_toggled` handler + `_checkbox_cell_data_func` that drives display state from `self.selected_materials` (previously the `Gtk.CellRendererToggle` was decoration with no signal connection or data binding). (b) Cursor preserved across `refresh_data()` so duplicate/delete no longer scrolls to top: capture highlighted material id before `_load_materials()`, then re-cursor + `scroll_to_cell(...)` after. (c) Hidden the panel-level "Export" button (handler did `pass`); the table widget's "Export Selected" button works and is the canonical export. Added `.csv` extension fallback in `_export_selected_materials` so a filename without extension defaults to CSV instead of erroring "Unsupported file format".
- **Operations Panel — gear button removed, sync semantics flipped**: The Settings (gear) toolbar button was a TODO stub showing only "Monitoring settings not yet implemented" — removed widget, sensitivity logic, and click handler entirely. Sync-with-Filesystem previously RE-IMPORTED orphan folders as new "completed" operations (opposite of user expectation). Rewrote to DELETE orphan folders matching the user mental model "sync = clean up trash". Tooltip + confirmation dialog text updated. The persistent reconciler-vs-live-children bug remains in POST_ALPHA_TODOS.
- **Per-panel info icon section anchors**: The "i in a circle" icons on each panel header (`panel_help_button.py:create_panel_help_button`) all jumped to the manual top regardless of which panel. Root cause: `PANEL_DOCUMENTATION_MAP` held defunct MkDocs URLs like `'user-guide/materials-management/index.html'`, and the click handler routed through `DocumentationViewer.open_documentation()`, the legacy alias that **silently dropped its `page` argument** and routed to the manual top. Replaced with anchor slugs (`'4-materials-management'`, `'5-mix-design'`, `'6-hydration-simulation'`, ...) and switched the click handler to `open_section(anchor)`. Also added `'THAMESHydrationPanel'` alias because the actual panel class on the Hydration page is `ThamesHydrationPanel` (uppercase THAMES prefix), not the legacy `HydrationPanel` — was the only post-fix straggler.
- **Aggregate kinetic default + Preferences pseudo-phase**: The `Aggregate` row in the Hydration phase list used to show kinetic model "Thermodynamic" because no built-in default existed, requiring the user to manually set Pozzolanic kinetics with low rate constants on every microstructure. Aggregate is a UI alias for the structural slab (underlying GEMS phase is Quartz) and shouldn't be in the GEMS-phase Preferences list. Two-pronged fix: (a) added `'Aggregate'` to `POZZOLANIC_DEFAULTS` in `kinetic_defaults_service.py` with all three rate constants pinned to `1e-12 mol/m²/s` (= `0.000001 µmol/m²/s`, the spin-button minimum non-zero — user's empirically-found floor; literal zero risks divide-by-zero in the kinetic solver). (b) Injected `'Aggregate'` as a pseudo-phase into `preferences_dialog._load_phases()` after the GEMS phases are loaded, so users can override the built-in default the same way as any GEMS phase. Refactored row insertion into a small `_append_phase_row()` helper so the loop and the special-case insertion share code.
- **App icon swapped**: Replaced the inherited VCCTL `icon.ico` with a multi-resolution ICO (16/24/32/48/64/128/256) converted from `icons/thames-icon.png` (the in-app home image) using Pillow. PyInstaller bundles this as the `THAMES.exe` icon on Windows.
- **Saved memory feedback**: After the user explicitly asked me to stop killing the UI to apply code changes mid-session, saved a `feedback_ui_lifecycle.md` memory: never restart the THAMES UI without explicit permission. The risk is that killing `python.exe` (parent UI) does NOT kill child `micgen.exe`/`thames.exe`, which then orphan their DB rows when the UI relaunches and the reconciler flips them to CANCELLED. Caused real folder/DB damage on 4/23.
- **Operations wipe before release**: Per user request, deleted all rows from `operations`, `microstructure_operations`, `hydration_operations`, `elastic_moduli_operations` and removed 17 operation folders from `%LOCALAPPDATA%\THAMES\operations\` (preserving 5 `.gdg` grading files and `microstructure_metadata`). Note: testers' installs already get a clean state because `%LOCALAPPDATA%\THAMES\` is per-user and not bundled — the wipe is for the user's own clean smoke-test of the alpha.
- **v1.0.0-alpha.2 re-tagged and released**: Bundled today's session into commit `375e2b49` ("Alpha 2 polish: UI fixes from second testing pass"). Re-tagged `v1.0.0-alpha.2` at HEAD (the previously-deleted tag was published anew). Re-built distribution artifacts:
  - `dist/THAMES-1.0.0-alpha.2-setup.exe` (~105 MB Inno Setup installer)
  - `dist/THAMES-1.0.0-alpha.2-win64.zip` (~760 MB portable ZIP)
  - `dist/THAMES-1.0.0-alpha.2-README.txt` (refreshed to mention the second-pass fixes)
- **DB backups created during the session** (in `%LOCALAPPDATA%\THAMES\database\`):
  - `thames.db.pre-cleanup-20260427-101735.bak` — before the materials cleanup
  - `thames.db.pre-ma157-fix-20260427-133441.bak` — before the ma157 backfill + ma157-real delete
  - `thames.db.pre-ops-wipe-20260427-155044.bak` — before the operations wipe
- **Pending when session resumes**:
  1. User to test the bundled `dist\THAMES\THAMES.exe` and the `setup.exe` installer (ideally in Windows Sandbox for a fresh-install scenario).
  2. `gh release create v1.0.0-alpha.2 --prerelease ...` to publish the GitHub pre-release with the three artifacts attached and the README body. Step 9 of `docs/ALPHA_RELEASE_PREPARATION.md`.
  3. Address `POST_ALPHA_TODOS.md` items between alpha and beta — notably the UI-restart reconciler bug (live-but-untracked child operations get flipped to CANCELLED) and the Materials Panel silent-delete bug.

### Session 44: Sandbox Validation — Three Crash Bugs Found & Fixed, Diagnostics Permanent
April 29-30, 2026 — Windows 10 (Sandbox testing)

User installed the Session-43 alpha.2 setup.exe in a fresh Windows Sandbox VM and immediately found that fresh-install testing exposes a different class of bugs than dev-machine testing. Three distinct crash bugs surfaced in succession; each required a separate fix and a fresh artifact.

- **Bug 1 — Empty Materials and Mix Design panels on fresh install.** Root cause: `app_info.py:58-63` copies a seed DB from `src/data/database/thames.db` to `%LOCALAPPDATA%\THAMES\database\thames.db` on first launch, but **the seed file never existed in the source tree**. PyInstaller's spec already bundles `('src/data', 'data')` (which would have picked it up), but with nothing at the source path the bundle had nothing to ship. SQLAlchemy silently created an empty SQLite at the user-data path on first launch. Fix: created `src/data/database/thames.db` (2.8 MB) from a wiped copy of the dev DB — kept 37 materials + 7 reference aggregates + 8 grading templates + 196 material_phase rows + 124 psd_data + 32 clinker_extension + 5 migrations + 12 particle_shape_set rows; cleared all user-state tables (mix_design 102→0, operations 6→0, microstructure_operations 2→0, elastic_moduli_operations 1→0, results, db_file, plus their `sqlite_sequence` rows) and `VACUUM`ed it. Added `!src/data/database/thames.db` exception to `.gitignore` so the seed is now tracked. Note: **`thames-macos.spec:67` still bundles a stale `src/data/database/vcctl.db` path that does not exist** — same fix needed there before any macOS packaging attempt.

- **Bug 2 — Silent crash with no error message after Mix completion.** Initial user report was "selecting a Mix in Results crashes the app." Investigation required adding diagnostic infrastructure (see below) before the actual cause became visible. Real story: the app died WHILE the Mix was running (at ~65% progress, 14 minutes into the run). The user only noticed the crash on next launch when they tried to interact with the Results page. With diagnostics in place, the second test run wrote `thames-crash.log` showing `Windows fatal exception: code 0xc0000374` (`STATUS_HEAP_CORRUPTION`) with the current thread in the Gio main loop and two background threads in `operations_monitoring_panel._monitoring_loop` and `performance_monitor._monitoring_loop`. Root cause: `_update_operation_in_database` at line 5827-5837 had **four orphan statements after its try/except block** that called GTK widget methods directly — `_sync_with_active_hydration_simulations`, `_update_operations_list`, `_update_performance_metrics`, `_refresh_results_analysis`. `_update_operation_in_database` is called from the BG monitoring thread (in `_update_microstructure_progress`) every time micgen's progress file changes. GTK widget mutation from a non-main thread on Windows ⇒ silent heap corruption ⇒ Windows GUI process Heap Terminate-on-Corruption fires (`__fastfail()`) ⇒ process dies with no exception. The orphan code looked like the tail of `_load_operations_from_database` that was duplicated into the wrong function during a refactor — `_load_operations_from_database` already has its own correctly-`GLib.idle_add`-wrapped UI refresh tail at lines 5585-5593. Fix: deleted the four orphan lines from `_update_operation_in_database`. Why dev machine never crashed: heap corruption from a single bad write usually lands on slack space or benign bytes; only when the bad write hits live free-list metadata does the heap manager terminate. Sandbox has a tighter heap (small process working set, dense allocations) and slower I/O (longer overlap window between BG and main thread GTK calls), making the corruption more likely to hit a critical structure.

- **Permanent guardrail for Bug 2's class.** Added `src/app/utils/thread_safety.py` with `assert_main_thread()` — raises `RuntimeError` with a clear message if called from any thread other than the main thread. Wired into the entry-point widget-touching methods of `operations_monitoring_panel.py`: `_update_ui`, `_update_operations_list`, `_update_performance_metrics`, `_update_operation_details`, `_refresh_results_analysis`, `_set_error_analysis`. Verified that the two existing direct call sites are still safe: line 5598 is wrapped in a try/except with comment "expected if not on main thread" (the assert is now caught and logged at DEBUG, no behavior change), and line 5777 is reached only via `_simple_progress_update` which is registered with `GLib.timeout_add_seconds` (callbacks run on main thread, assert won't fire). Future cross-thread calls — anywhere in the panel — now fail loudly with a clean Python traceback instead of silent heap corruption.

- **Bug 3 — Aggregate shape dropdowns empty in Mix Design.** Discovered while user's third test was running. `MixDesignPanel.refresh_shape_sets()` was being called by `DirectoriesService` after the first-launch tarball extraction, but it only refreshed `cement_shape_combo` — not `fine_agg_shape_combo` or `coarse_agg_shape_combo`. The aggregate combos were populated at panel-creation time (before extraction completed), so they captured zero entries and stuck on the default "sphere" until the next app launch. Particle/cement shapes appeared correctly because they're refreshed; aggregates weren't. Fix: extended `refresh_shape_sets` with a small `_repopulate(combo, shape_sets)` helper that's called for all three combos (cement / fine aggregate / coarse aggregate); each preserves the current selection if still valid, falls back to index 0 otherwise.

- **Diagnostic infrastructure now permanent.** `console=False` PyInstaller builds discard stdout, so the only way to debug a packaged crash was to add file-based diagnostics:
  - `src/main.py` — opens `%LOCALAPPDATA%\THAMES\logs\thames-crash.log` BEFORE any heavyweight imports run; calls `faulthandler.enable(file=...)` so native crashes (segfaults, heap corruption) get a stack trace; installs `sys.excepthook` so uncaught Python exceptions also write to the same file. Long-lived file reference held module-level so the FD survives the program lifetime.
  - `src/app/application.py::_setup_logging` — added a `FileHandler` writing to `%LOCALAPPDATA%\THAMES\logs\thames.log` alongside the existing `StreamHandler(sys.stdout)`. `force=True` on `basicConfig` ensures it overrides any earlier basicConfig call from third-party imports. Logs path resolved the same way as `app_info.py` to avoid circular imports.
  - `src/app/windows/panels/results_panel.py` — wrapped `_on_operation_selection_changed` in try/except so a Python exception during selection gets logged with traceback (rather than swallowed by GTK's signal handler) and the user sees an error dialog.

- **Sandbox 3D viewer crash — environment limitation, not a code bug.** After Bug 2 was fixed, user's next test was clicking the 3D microstructure viewer in Results. App crashed with `STATUS_ACCESS_VIOLATION (0xC0000005)` at `pyvista_3d_viewer.py:1055` — `self.render_window.Render()`. Sandbox has no GPU acceleration (basic display via RemoteFX, no working OpenGL); VTK's first GL call NULL-derefs in native code. Python try/except cannot catch native faults. Decision: **document the GPU requirement, do not ship Mesa software fallback for alpha**. Real testers on real machines won't hit it. Documented in: README.md (new "System requirements" section between status and Download), `dist/THAMES-1.0.0-alpha.2-README.txt` (new System Requirements section + #1 in Known Limitations + new Crash Diagnostics section pointing testers at the log files), and `docs/USER_MANUAL.md` section 8.1 (new alpha-warning callout right after the state table).

- **User manual section 8.1 also got the operation-shutdown warning.** Independent of the Sandbox bugs, in conversation about reattach-on-restart behavior I noted that closing THAMES while a Mix or Hydration is running leaves the simulator process alive (`micgen.exe` / `thames.exe`) — but the next UI launch flips the operation row to CANCELLED because the reconciler only checks the previous UI's PID, not the spawned child's PID. This is logged in `POST_ALPHA_TODOS.md` ("Reconciler marks live operations CANCELLED when UI is restarted"). For alpha, added an explicit warning callout in section 8.1 that explains: what happens, what to do (Task Manager check before deleting "Cancelled" ops; let the simulator finish; Results panel scans the folder so finished runs are visible there even if Operations still labels them Cancelled), and what to avoid (use Stop button, or just leave THAMES open). Reattach is on the post-alpha roadmap.

- **Sandbox testing pass result.** With all three bugs fixed and the manual updated, the user did a final full Sandbox pass: duplicating/editing/deleting materials, making a mixture, hydrating it, calculating elastic moduli, browsing the user manual via Help menu and tooltips, and verifying that completed operations persist across an app shutdown. Everything passed cleanly. The 3D viewer is still unavailable in Sandbox (documented limitation) but verified working on the host machine.

- **One useful design conversation.** User asked why Sandbox surfaced bugs the dev machine didn't (timing + heap density + Heap Terminate-on-Corruption is unconditional on Windows GUI processes since Win8) and how to prevent the orphan-statements class systematically. Recommended three options in increasing cost: (1) `assert_main_thread()` runtime guards — implemented this session; (2) funnel pattern (mark widget methods unsafe-private, BG threads must go through a single `_post_to_ui` helper); (3) full architectural separation (BG thread emits signals to a queue; main thread consumes via `GLib.timeout_add` — strongest invariant but a sizable refactor of `operations_monitoring_panel.py`). (1) is in for alpha; (2) and (3) deferred to post-alpha.

- **Artifacts produced** (in `dist/`):
  - `THAMES-1.0.0-alpha.2-setup.exe` (~624 MB Inno Setup installer; bigger than Session 42's ~105 MB because MSYS2 has updated, the spec's broad `lib*.dll` glob now picks up libLLVM-21 / libclang-cpp / libgccjit / libclang ~265 MB raw — Post-Alpha TODO candidate to tighten the glob)
  - `THAMES-1.0.0-alpha.2-README.txt` (refreshed with System requirements + GPU limitation + Crash Diagnostics section)

- **Pending when session resumes**: tag move + commit + push + `gh release create`. The `v1.0.0-alpha.2` tag from Session 43 is now stale by all the Session 44 fixes; user authorized moving it (force-tag in place is safe — it has not been published to testers yet, this whole session was the validation).

### Session 45: macOS Alpha-2 Build, Public Cross-Platform Release
May 2, 2026 — macOS

First public cross-platform release. Brought macOS packaging up to parity with the Windows alpha-2 (which the user had published manually via the GitHub web UI between Session 44 and this one). No runtime code changed; all work was build infrastructure plus the artifact upload. End-to-end validated on macOS 15.4 arm64. Full narrative: `docs/session45_summary.md`.

- **Cross-platform spec fix**: `thames-windows.spec` (the canonical cross-platform spec, despite the misleading name) IS_MACOS branch was bundling seven nonexistent VCCTL-legacy `backend/bin/*` paths. Replaced with the actual three artifacts (`bin/thames`, `bin/micgen`, `bin/libpng16.16.dylib`). Bumped macOS BUNDLE version 10.0.0 → 1.0.0-alpha.2 and added `LSMinimumSystemVersion='10.14'` and `LSApplicationCategoryType='public.app-category.education'`.
- **Libpng bundling for macOS**: `bin/thames` and `bin/micgen` linked `/opt/homebrew/opt/libpng/lib/libpng16.16.dylib` directly, so testers without Homebrew would see "dylib not loaded" at first launch (mirror of the Windows libpng16-16.dll bundling). Added a permanent Step 5 to `build-macos.sh` that copies Homebrew's libpng next to the binaries, runs `install_name_tool -id @rpath/libpng16.16.dylib` on the dylib and `install_name_tool -change ... @rpath/...` on each binary, adds `@loader_path` to LC_RPATH (idempotent — skipped if already present), and re-codesigns ad-hoc. Mirrored as a spec-bundled binary in `thames-windows.spec`.
- **PIL libharfbuzz collision (the harfbuzz crisis)**: bundled .app silently exited at startup with no error dialog. Direct invocation from Terminal showed `dlopen(...): Symbol not found: _hb_coretext_font_create — Expected in: PIL/__dot__dylibs/libharfbuzz.0.dylib`. Root cause: PyInstaller's PIL hook bundles a minimal libharfbuzz built without CoreText support, and Pillow's hook ran after the GI hook so PIL's harfbuzz won the canonical `Contents/Frameworks/libharfbuzz.0.dylib` slot via a symlink chain. Homebrew's `libpangocairo` (collected by the GI hook for GTK) was built against Homebrew's harfbuzz which DOES have `_hb_coretext_font_create`, so dyld returned PIL's harfbuzz and the symbol lookup failed → typelib load failed → app exit before any UI. Fix: replace the single physical PIL harfbuzz file (everything else in the bundle resolves to it via symlinks) with Homebrew's, rewrite install_names from `/opt/homebrew/...` to `@rpath/...` for `libfreetype.6.dylib`, `libglib-2.0.0.dylib`, and `libgraphite2.3.dylib` (all three already in `Contents/Frameworks/` from the GI hook). Re-codesign the dylib and the parent bundle (deep, ad-hoc). Added permanent post-BUNDLE block inside `if IS_MACOS:` in `thames-windows.spec` that runs the install_name_tool + codesign sequence at the end of every macOS build, with explicit `RuntimeError` raises if Homebrew harfbuzz is missing or if PyInstaller's bundle layout shifts. Comment block in the spec explains the dyld resolution chain so the next person to look at it (or me, in a future session) doesn't have to re-derive it.
- **App icon**: created `src/app/resources/icon.icns` from existing `icons/thames-icon.png` (1036×1036 RGBA) using `sips` at the 10 standard iconset sizes (16/32/64/128/256/512/1024 plus @2x retina) and `iconutil -c icns`. Lands at the path the spec's existing `os.path.exists` check looks at. Mirrors Session 43's Windows ICO swap.
- **Legacy thames-macos.spec deletion**: separate spec file existed full of VCCTL legacy (executable name `vcctl`, `vcctl.db` references, MkDocs paths, wrong icon). Hadn't been used since the project pivoted off VCCTL — `build-macos.sh` only handles C++ side; PyInstaller is invoked manually with `thames-windows.spec`. Deleted to remove a future-confusion source.
- **The 271-hour orphan**: pre-Step-1 inspection caught a `bin/thames` process running for 11 days, 7 hours, 23 minutes — `HydrationOf-ccr152-concrete`, the same near-depletion-stall hydration logged in `POST_ALPHA_TODOS.md` since Session 41. Session 41's stop/cancel fix had reconciled the DB to `CANCELLED`, but the spawned simulator never received the message and kept running for 11 days, eating CPU and growing a `thames.log` to 251 MB. This is the orphan pattern in `POST_ALPHA_TODOS.md` ("Reconciler marks live operations CANCELLED when UI is restarted"). Killed cleanly with `kill` (SIGTERM, no SIGKILL needed).
- **Distribution wrap**: `ditto -c -k --keepParent --rsrc` (preserves resource forks and codesign metadata; `zip` and Python `zipfile` would invalidate signatures). Output: `dist/THAMES-1.0.0-alpha.2-macOS.zip` (621 MB; 44% compression on the 1.1 GB binary-heavy bundle). Verified `codesign --verify` passes after `ditto -x -k` round-trip.
- **Tester README**: `dist/THAMES-1.0.0-alpha.2-macOS-README.txt` modeled on the Windows alpha-2 README. Differs in install instructions (drag-to-Applications, Gatekeeper bypass via right-click → Open or `xattr -dr com.apple.quarantine`), log paths (`~/Library/Application Support/THAMES/logs/`), and system requirements (macOS 10.14+ Apple Silicon).
- **Public release upload**: user had manually published Windows alpha-2 via the GitHub web UI between Session 44 and this one. With a published tag, force-moving was off the table. Plan revised to **Option A**: commit the macOS build infrastructure as a new commit on `main`, leave the tag where it is (every change this session was build-tooling only — zero Python/C++ runtime change, so the macOS .app behavior matches what the v1.0.0-alpha.2 tag represents). Installed `gh` CLI (Homebrew, 2.92.0); user did `gh auth login` browser flow. Commit `bbe62bb3` ("macOS alpha-2 build infrastructure") staged the four real changes (icon.icns, deletion of thames-macos.spec, build-macos.sh, thames-windows.spec) and excluded local-prefs noise. `gh release upload v1.0.0-alpha.2 --clobber` for both macOS files. Final state: 5 assets on the release (3 Windows + 2 macOS), notes rewritten for both platforms.
- **Release URL**: https://github.com/jwbullard/THAMES/releases/tag/v1.0.0-alpha.2 — first public cross-platform THAMES release.

### Session 46: Color-Button GSettings, Silica-Fume Stall Diagnosis, Kinetic Save-Bug Fix
May 11–12, 2026 — macOS

Two unrelated alpha-2-era issues debugged in the same long session. Full narrative: `docs/session46_summary.md`.

- **3D viewer color-button silent crash (dev mode only)**: clicking a phase color in the Results-page 3D viewer's Phase Controls panel killed `python src/main.py` instantly with no Python traceback. macOS crash report (`~/Library/Logs/DiagnosticReports/Python-2026-05-11-111030.ips`) showed `EXC_BREAKPOINT/SIGTRAP` via `g_log_abort` in `gtk_color_chooser_dialog_init` → `g_settings_new('org.gtk.Settings.ColorChooser')` — GLib's intentional fatal abort when the compiled schema cache is unreachable. Root cause: Ghostty terminal's `XDG_DATA_DIRS` doesn't include `/opt/homebrew/share`, so `gsettings list-schemas` returns nothing. `faulthandler` cannot intercept SIGTRAP from glib's abort path, hence no entry in `thames-crash.log`. Bundled `.app` is unaffected (PyInstaller's `pyi_rth_glib.py` runtime hook sets `GSETTINGS_SCHEMA_DIR` to the bundle's own copy). Fixed in `src/main.py` before any GI import: in dev mode on macOS, point `GSETTINGS_SCHEMA_DIR` at Homebrew's compiled cache if it exists. Alpha-2 testers cannot hit this, so the release was NOT reissued. Committed as `94d9b89d`.
- **Cement + silica-fume hydration stuck at cycle 11**: `HY-ccr152-sf15-ws45-01` ran for 5 minutes, then locked up with 100% CPU and no log progress. `thames.log` frozen mid-cycle-11, `currTime` advancing by 1e-5 h per cycle (a 99.9% rollback), 20 `checkICMoles: IC Ca depleted to -0.5 mol` events in 4 minutes (vs 9 over all 1031 cycles of the user's sf-free `HY-ccr152-ws45` companion run). The damning signal: GEMS asking the lattice to GROW Portlandite by 1,786,978 voxels (17× current mass) in ONE step while simultaneously DISSOLVING ettringite and CSHQ entirely. Unphysical chemistry flip-flop. Root cause: adding silica fume to a Portland chemistry creates two near-degenerate solid distributions in the GEMS landscape, and GEMS oscillates between them on each `recall GEM`. Portlandite-as-Standard puts Portlandite into the `maxRelativeChange=5%` kinetics constraint, which correctly refuses the impossible step but doesn't fix the oscillation — dt clips to ~1e-5 h forever. The fix, found after eliminating two false leads:
  - **Try 1 (slower silica fume kinetics 3.3e-9 vs 4e-8)**: partial improvement (Ca depletion 20→4) but still stalled at cycle 11
  - **Try 2 (unsuppress straetlingite + syngenite as alternative Ca-Al sinks)**: no effect — GEMS doesn't pick these phases at this composition; they showed zero activity in the lattice log
  - **Try 3 (Portlandite → Thermodynamic, no kinetic_data block)**: **cleared the stall**. Cycle 19 reached in 7 min 35 s, dt growing 0.0072 → 0.012 h geometrically, zero Ca depletion events, smooth monotonic Portlandite growth (3095 → 12838 voxels over the unstuck cycles). Removing Portlandite from the kinetics-constraint denominator lets GEMS settle into its equilibrium solid budget in one big lattice update, after which the system stays in a stable basin.
- **The same-cement-no-silica-fume comparison was decisive**: `HY-ccr152-ws45` reached cycle 1031, dt grew to 0.616 h, only 9 IC-recovery events total, smooth gradual CSHQ + Portlandite growth. That data ruled out a generic Portland-cement bug and pinpointed silica fume as the trigger.
- **Kinetic-editor save bug discovered during the above**: the user reported the kinetic editor dialog showed Portlandite as "Thermodynamic" but the run's `hydration_config.json` recorded Standard with full rate constants. Investigation revealed an architectural asymmetry between two parallel kinetic-editor entry points. The **Preferences dialog** calls `prefs_service.set_user_default(phase_name, {'type': 'Thermodynamic'})` and persists to `~/Library/Application Support/THAMES/preferences/kinetic_defaults.json`. The **Hydration panel's kinetic dialog** (`_on_configure_kinetics`) only updates the in-session `kinetic_configurations` widget dict; it never persists. A UI restart (we did two during yesterday's suppression-toggle and harfbuzz debugging) reset the dict from built-in defaults, and the next Run launched with Standard despite the user's earlier Thermodynamic selection. Fixed in `thames_hydration_panel.py::_on_configure_kinetics`: both OK branches now call `set_user_default` so the two editors have identical persistence semantics. Second small fix in `microstructure_phases_editor.py::_edit_phase_kinetics` corrects an `if new_params:` check that silently dropped `None` (Thermodynamic) returns. Working tree only — NOT YET VALIDATED end-to-end; user will exercise the fix in the next session.
- **UI patches made and reverted mid-session**: while still misdiagnosing the stall as Arcanite-related, two patches went into `src/app/widgets/hydration_product_selector.py` (`_checkbox_cell_data_func` and `_on_product_toggled`) to allow toggling of microstructure-resident phases for suppression. Subsequently discovered that (a) the toggle didn't actually propagate to `simparams_service`'s suppressed_phases list because `microstructure_phases` is a separate set from `selected_products`, and (b) the actual fix was Portlandite=Thermodynamic, not suppression. Both patches reverted via `git checkout`. The architectural gap is logged in POST_ALPHA_TODOS for proper future fix (the recommended path is a confirmation dialog plus actual data-flow plumbing).
- **POST_ALPHA_TODOS gained five new entries**: Load-from-Previous tree population, Load-from-Previous microstructure-path population, suppression toggle confirmation dialog (replacing the reverted patches), kinetic editor Thermodynamic save bug (FIXED in working tree), and the comprehensive GEMS-Portlandite stall pattern entry recommending Portlandite default to Thermodynamic in materials DB and exploring a backend oscillation-detector.
- **Overnight SIGABRT**: the cycle-19 run was left running and at some point aborted with `exit 134`. The user cleaned up the operation directory before the next-day check, so no logs survive for post-mortem. The Portlandite=Thermodynamic fix is **validated for breaking the cycle-11 cliff**; whether the simulation can run to its 28-day target with this fix alone is **unknown and on the next-session list**.

---

## PRIORITY TASKS

### 1. Adaptive Time Stepping (COMPLETE)
Fully implemented: AdaptiveTimeController class, GEMS convergence accessors, kinetics-based timestep, UI configuration (7 SpinButtons), simparams.json integration. See `docs/adaptive_timestepping_implementation_plan.md`.

Default parameters: dt_initial=0.001h, dt_max=4h, growth_factor=1.5, successes_for_growth=2. Disable via UI checkbox or `useAdaptiveTimeStepping_ = false` in Controller constructor.

### 2. GEMS Error Recovery (COMPLETE)
IC depletion recovery with charge compensation, IC_FLOOR=1e-5 (must NOT exceed this), runtime electrolyte concentration safety, exit_status.json + UI alerts, concentration_overrides.json + UI notification.

### 3. Documentation (MOSTLY COMPLETE)
User Manual at `docs/USER_MANUAL.md` (~1,200 lines) with 26 screenshots. 2 screenshots still missing (elastic results, workflow1 results).

### 4. Known Issues
- UI memory bloat: Loading 200^3 microstructures causes ~5.9 GB RAM usage
- Windows process termination: UI "stop and delete" may not fully kill thames.exe
- micgen exit segfault during `freemicgen()` cleanup (after output written, low priority)
- Near-depletion phases can collapse adaptive timestep at late ages (see post-alpha list)

### 5. Post-Alpha TODO List
Deferred improvements are tracked in `docs/POST_ALPHA_TODOS.md`. Append there whenever a "later" / "post-alpha" / "not blocking alpha" item comes up in conversation; do NOT add post-alpha items directly to this file.

---

## Immutable Materials

38 materials are immutable (read-only, migrated from VCCTL): all materials beginning with "cement", csatype10, csatype50, danwhite, dh, frcement, ma157, ma160, ma165, ma178, rossi, sacci-425, sacement, ustype1, NormalLimestone.

---

## MANDATORY: Cross-Platform Safety Protocol

**CRITICAL: Before making ANY change to these files, ALWAYS check both platforms:**
- `.spec` files (thames-macos.spec, thames-windows.spec)
- Path-related code (directories_service.py, config_manager.py, app_info.py)
- Build scripts (build_macos.sh, any Windows build scripts)
- Hooks directory

**Required checks for EVERY change:**

1. **Read BOTH platform spec files:**
   ```bash
   grep -n "relevant_pattern" thames-macos.spec
   grep -n "relevant_pattern" thames-windows.spec
   ```

2. **State explicitly BEFORE making the change:**
   - "This change affects: [macOS / Windows / both]"
   - "Windows currently does: [X]"
   - "macOS currently does: [Y]"
   - "After this change: [Z]"
   - "This will/won't break Windows because: [reason]"

3. **For path changes specifically:**
   - Check where files are bundled in BOTH specs
   - Check where code looks for them in the Python files
   - Verify the paths match on BOTH platforms after the change

**Failure to follow this protocol causes platform regressions and wastes user time.**

## Git commands
- Do not run a git command unless you are requested to do so
- Use "git add -A" to stage changes before committing to the git repository
- ALWAYS include both co-authors in commit messages:
  - Co-Authored-By: Jeffrey W. Bullard <jwbullard@tamu.edu>
  - Co-Authored-By: Claude <noreply@anthropic.com>

## Responses
- Do not use the phrase "You're absolutely right!". Instead, use the phrase
"Good point.", or "I see what you are saying."

## OS Switching Procedures (CRITICAL - READ FIRST)

### **Cross-Platform Development Workflow**

When working on THAMES across multiple operating systems (Mac, Windows, Linux), use these scripts to keep git repositories synchronized:

#### **Starting Work on Different OS:**

```bash
./pre-session-sync.sh
```

**What it does:**
- Fetches latest changes from remote
- Shows what commits will be pulled
- Creates automatic backup branch
- Pulls changes with rebase strategy
- Verifies sync completed successfully

**When to use:**
- ALWAYS at start of session on different OS
- After long break between sessions
- When you suspect changes on remote

#### **Ending Work Session:**

```bash
./post-session-sync.sh
```

**What it does:**
- Shows all uncommitted changes
- Prompts for commit message (or auto-generates)
- Stages all changes with `git add -A`
- Creates commit with standard format
- Pushes to remote repository

**When to use:**
- ALWAYS at end of work session
- Before switching to different OS
- Before long breaks

---

## Key Technical Patterns

### PyInstaller Path Resolution:
```python
# WRONG - breaks in PyInstaller:
project_root = Path(__file__).parent.parent.parent

# RIGHT - use service abstraction:
operations_dir = self.service_container.directories_service.get_operations_path()
```

### Platform-Specific subprocess:
```python
popen_kwargs = {'stdout': ..., 'stderr': ...}
if sys.platform == 'win32':
    popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
process = subprocess.Popen(cmd, **popen_kwargs)
```

### Cross-Platform User Data Directories:
- **macOS:** `~/Library/Application Support/THAMES/`
- **Windows:** `%LOCALAPPDATA%\THAMES\`
- **Linux:** `~/.local/share/THAMES/`

---

# Important Instructions
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.

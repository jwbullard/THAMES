# Session 41: Concelas Integration — Concrete-Scale Elastic Moduli

**Date:** April 20–21, 2026
**Platform:** macOS (Darwin 25.4.0)

## Overview

Integrated the multi-scale concrete elastic-moduli post-processor ("concelas") into THAMES so that elastic runs with aggregate now produce paste + ITZ + concrete moduli plus empirical strength fits. Previously the Elastic panel showed an orange banner warning that "Aggregate support not yet available in THAMES mode." The banner and the gating behind it are gone. Alpha release is now feasible for the full elastic-moduli pipeline.

The concelas algorithm was ported from the VCCTL `backend/src/elastic.c` (lines 2942–3559) to Python. No C++ changes were needed in the THAMES-Hydration submodule — the existing `thames -s 5` FEM binary already writes `EffectiveModuli.csv` and `ITZModuli.csv` when an aggregate slab is present; the Python post-processor reads those and appends concrete-scale rows.

## Planning

The session opened in plan mode. Three parallel Explore agents investigated (a) the aggregate-geometry wiring between micgen, the THAMES-Hydration C++ simulator, and the legacy `elastic.c`, (b) the UI gating that blocked concelas in THAMES mode, and (c) the differences between VCCTL's and THAMES's elastic execution paths. The agents' findings showed that the standalone `backend/src/elastic.c` was legacy VCCTL code (uses undefined `INERTAGG`, `C3S`, `vcctl.h`) and is commented out of the backend CMakeLists, while the C++ `thames -s 5` ELASTIC_CALC mode already produces `EffectiveModuli.csv` + `ITZModuli.csv` and auto-detects `hasAggregateSlab_` from the microstructure. That meant the cleanest path was a **Python post-processor** reading those CSVs — no backend C++ changes, no porting of the defunct `elastic.c` header dependencies.

Plan written to `/Users/jwbullard/.claude/plans/toasty-booping-moon.md`; approved with seven milestones M0–M6.

## Milestones

### M0 — Aggregate plumbing verified (no code changes)

Traced `mix_design_panel.py:2029–2032`, which already detects `has_aggregate` from fine/coarse mass fields and passes `add_aggregate_slab=True` to `MicgenInputService.generate_input_file()`. `Lattice.cc:764` auto-detects `hasAggregateSlab_` from `getVolumeFraction(AggregateId) > 0`. End-to-end wiring was already in place.

### M1 — Python concelas service

**New:** `src/app/services/concelas_service.py` (~480 lines) — pure-algorithm module.

Public API:
- `run_concelas(paste_K, paste_G, layer_K, layer_G, agg_x, resolution_um, cement_psd, fine, coarse, air_vf) → ConcelasResult`
- Dataclasses: `AggregateSource`, `ConcelasResult`

Ported functions (all from `backend/src/elastic.c`):
- `median_cement_psd()` — linear interpolation of cumulative PSD for d₅₀
- `compute_itz_and_paste_moduli()` — ITZ vs bulk-paste K, G averaging from per-layer arrays
- `_effective()` — Hashin composite-sphere ITZ correction per aggregate size class
- `_slope()` — differential Mori–Tanaka rate of change wrt matrix volume
- Inline 4th-order Runge–Kutta driver (799 steps, matches C code)
- Power-law compressive-strength fits (SCG mortar + Pichet concrete cube/cylinder)

**New:** `tests/test_concelas_service.py` — 21 unit tests covering median-PSD interpolation, young/poisson helpers, strength fits, ITZ vs bulk averaging, degenerate paste-only, realistic fine+coarse stiffening, only-fine, only-coarse, and air-softening. All pass.

### M2 — CSV I/O adapter

**New:** `src/app/services/concelas_runner.py` (~260 lines). Parses `EffectiveModuli.csv` (paste moduli), `ITZModuli.csv` (per-layer K, G), cement PSD, and grading files. Calls `run_concelas`. Appends 13 concrete-scale rows to `EffectiveModuli.csv`. Writes `ConcelasLog.txt`.

Public API: `run_and_append(elastic_output_dir, fine=None, coarse=None, cement_psd_path=None, air_volume_fraction=0.0, write_log=True) → ConcelasResult`

Notable design choices:
- **Idempotent**: `append_concrete_rows` no-ops if any `Concrete_*` key already exists.
- **Layer ordering**: ITZModuli.csv labels layers as `Layer_<N>` where N can be zero or negative; the parser sorts by the `distance` field rather than the label to guarantee slab-outward ordering.
- **Graceful degradation**: Missing ITZ file with aggregate supplied → warns and uses paste moduli as ITZ proxy, pipeline continues.
- **Resolution quirk tolerance**: C++ writes `"Resolution, "` (trailing space) in EffectiveModuli.csv vs `"Resolution,"` in ITZModuli.csv; parser strips whitespace.

**New:** `tests/test_concelas_runner.py` — 16 tests covering CSV parsing, idempotency of row appending, degraded modes, and error handling.

### M3 — Remove UI gating

Four `thames_mode` gate points removed from `src/app/windows/panels/elastic_moduli_panel.py`:
- Warning banner "⚠ Aggregate support not yet available in THAMES mode..." deleted entirely.
- `_disable_aggregate_settings()` call removed and the dead method deleted.
- `has_itz_check` `set_visible(False)/set_sensitive(False)` removed — checkbox now works in THAMES mode.
- Lineage fallback text rephrased to drop the "lineage not available for aggregate properties" implication.
- Backend info banner updated to advertise multi-scale capability.

No changes to `elastic_input_generator.py` or `elastic_lineage_service.py`; they were already mode-agnostic.

### M4 — Wire concelas invocation

`_launch_thames_elastic` now accepts the `ElasticModuliOperation` object. New helper `_write_concelas_inputs_json` writes `concelas_inputs.json` to the elastic output directory at launch time, embedding resolved fine/coarse volume fraction, K, G, and grading points (read from file rather than deferred) plus the cement PSD path and air volume fraction.

`operations_monitoring_panel.py` gained `_on_elastic_moduli_calculation_completed(operation)`, wired alongside the existing microstructure completion hook. After a successful elastic operation, the hook reads `concelas_inputs.json` (no-op if absent, i.e. paste-only run), builds `AggregateSource` objects, and calls `run_and_append()` on the `Result/` subdirectory.

Failure path: concelas exceptions are caught, logged, and swallowed — a concelas failure does not downgrade an otherwise-valid paste elastic result.

### M5 — Display concrete moduli

`src/app/windows/dialogs/effective_moduli_viewer.py` already had keyword-based auto-grouping of rows from EffectiveModuli.csv. One rule added: an `itz` property bucket, tested **before** the generic `modulus`/`ratio` rule so that `ITZ_bulk_modulus`, `ITZ_shear_modulus`, and `ITZ_width` land in an ITZ group rather than being split across BINDER MODULI and OTHER PROPERTIES.

Section ordering (user-specified):
1. MICROSTRUCTURE INFO
2. BINDER EFFECTIVE MODULI (renamed from "EFFECTIVE MODULI" — clearer that it's the paste-scale homogenization, not the concrete-scale one)
3. PASTE PROPERTIES (VCCTL-legacy section, usually empty for THAMES)
4. CONCRETE PROPERTIES
5. ITZ PROPERTIES (moved last on user request — natural reading order is binder → concrete → interface)
6. OTHER PROPERTIES

### M6 — Documentation

- `docs/USER_MANUAL.md` Section 7 expanded: new lead-in describing three-scale computation (binder / ITZ / concrete), rewritten Section 7.1 noting auto-populate from lineage and the VF=0 warning, rewritten 7.2 describing concelas invocation and log files, and rewritten 7.3 with a clear four-subsection breakdown (Binder / Concrete / ITZ / Strain Energy) including the strength-fit caveat and references to two new screenshots.
- Section 10.1 (Workflow 1) now references both `25-workflow1-results-3d.png` and `25-workflow1-results-plot.png`.
- New screenshots added to `docs/images/`:
  - `18-elastic-results-tabular.png` — Effective Moduli Viewer with all four populated sections
  - `18-elastic-results-itzplot.png` — ITZ K, G vs distance from aggregate surface
  - `25-workflow1-results-3d.png` — 3D view of Workflow 1 final microstructure
  - `25-workflow1-results-plot.png` — Phase-volume plots for Workflow 1
  - `28-hydration-input-mode.png` — New/Load radio buttons
  - `29-adaptive-time-stepping.png` — Adaptive parameters expander
- Session 41 entry added to CLAUDE.md.

## Stop/cancel persistence bug fix

Late in the session the user reported that the stopped 9.22-day ccr152-concrete hydration kept appearing to "restart" on every app launch, and could not be deleted because the elastic results lived inside its folder. Root cause: `_stop_operation` (and the sibling `cancel_operation`) in `operations_monitoring_panel.py` updated only in-memory status to `CANCELLED`, never persisting the change to the database. The misleading comment *"Database automatically updated through operation monitoring"* was false — the monitoring loop writes status changes only on COMPLETED/FAILED transitions it detects itself, not on externally-driven cancels. Consequence: the DB kept the op as `RUNNING` forever, and each `_load_operations_from_database` call resurrected it as a live-running operation at 5% progress, triggering the hydration-sync code path that produced the phantom dialog.

Three fixes:

1. **`_stop_operation`** — now calls `self._update_operation_in_database(operation)` after setting CANCELLED. Future stop-button clicks persist correctly.
2. **`cancel_operation`** — same fix plus removal of the misleading comment.
3. **Startup reconciliation in `_load_operations_from_database`** — after loading, iterate all ops; any marked `RUNNING` without a preserved process handle and whose `is_process_running()` returns false is a leftover from a previous session. Reclassify as `CANCELLED` and write back. Self-heals the current DB *and* any future zombie records from crashes or force-quits.

Applied a one-shot SQL update to reconcile the user's existing DB (id=76 ccr152-concrete hydration: `RUNNING` → `CANCELLED`). The Elastic results inside its folder are untouched.

## Two UX polish items added mid-session

In response to a user test that exposed an empty concrete-scale result for a mix with `fine_aggregate_mass = 0`:

1. **Elastic panel warning**: In `_populate_from_resolved_lineage`, the Source label now displays a red warning when lineage returns `volume_fraction = 0` with an aggregate name present: "⚠ Volume fraction is 0 — microstructure likely has no aggregate slab (set Fine/Coarse Aggregate Mass > 0 in Mix Design and regenerate)." Applied symmetrically to fine and coarse.
2. **Mix Design pre-generation dialog**: Before launching micgen, the panel now detects orphan aggregate metadata (aggregate name set, mass = 0) and pops an OK/Cancel warning dialog explaining that the aggregate will not be placed and concelas will be skipped. User can proceed or cancel to fix.

## Post-alpha TODO infrastructure

Created `docs/POST_ALPHA_TODOS.md` to track deferred improvements. Seeded with five entries — the headline item is the **adaptive-timestep near-depletion stall** observed during a 28-day hydration of ccr152-concrete: when a phase drops to < 10 voxels, the kinetics constraint (5% max mole change per step) collapses the timestep to ~0.2 s per cycle. Proposed fix: add a volume-fraction threshold inside `computeKineticsBasedMaxTimestep` to ignore near-exhausted phases.

CLAUDE.md gains a one-line pointer under PRIORITY TASKS #5. Convention logged to auto-memory: any "post-alpha / later / not blocking" item goes into the TODOs file, not into CLAUDE.md directly.

## Files Modified

- `src/app/services/concelas_service.py` — **new** (~480 lines)
- `src/app/services/concelas_runner.py` — **new** (~260 lines)
- `tests/test_concelas_service.py` — **new** (21 tests)
- `tests/test_concelas_runner.py` — **new** (16 tests)
- `src/app/windows/panels/elastic_moduli_panel.py` — removed thames_mode gates, added `_write_concelas_inputs_json`, passed `elastic_operation` through to THAMES launch path, added VF=0 Source-label warning
- `src/app/windows/panels/operations_monitoring_panel.py` — added `_on_elastic_moduli_calculation_completed` completion hook
- `src/app/windows/panels/mix_design_panel.py` — added orphan-aggregate pre-generation warning dialog
- `src/app/windows/dialogs/effective_moduli_viewer.py` — added ITZ property bucket, renamed section to BINDER EFFECTIVE MODULI, reordered ITZ last
- `docs/USER_MANUAL.md` — Section 7 and 10.1 rewritten
- `docs/POST_ALPHA_TODOS.md` — **new**
- `CLAUDE.md` — Session 41 entry, pointer to POST_ALPHA_TODOS.md
- `operations_monitoring_panel.py` — stop/cancel persistence fix + orphan-RUNNING reconciliation on DB load
- `thames.db` — one-shot reconciliation of id=76 `HydrationOf-ccr152-concrete` from `RUNNING` to `CANCELLED` (app-driven reconciliation will handle this automatically next launch for any future zombies)
- `docs/images/18-elastic-results-tabular.png`, `18-elastic-results-itzplot.png`, `25-workflow1-results-3d.png`, `25-workflow1-results-plot.png`, `28-hydration-input-mode.png`, `29-adaptive-time-stepping.png` — **new**

## Verification

- Python unit tests: 37 passing (21 concelas_service + 16 concelas_runner).
- Syntax check on every modified Python file: OK.
- End-to-end manual test: HydrationOf-ccr152-concrete 7-day microstructure produced `EffectiveModuli.csv` with paste + concrete + ITZ rows, `ConcelasLog.txt`, `ITZModuli.csv`, and `ipmlog.txt`. Numerical sanity check:
  - Paste K = 19.55, G = 10.19 GPa
  - Concrete K = 22.88, G = 12.65 GPa (stiffer than paste ✓)
  - ITZ K = 16.82, G = 8.50 GPa (softer than paste ✓)
  - Mortar cube = 31.3 MPa, concrete cube = 20.2 MPa, cylinder = 12.6 MPa (reasonable 7-day values)

## Known Issue Surfaced (deferred to post-alpha)

During a 28-day hydration of a 100³ ccr152-concrete microstructure, the adaptive timestep collapsed to ~0.06 ms per cycle at ~9 days due to near-depletion of Arcanite (K₂SO₄) at 2 voxels. The kinetics constraint's denominator becomes the pathology. Paste-scale results through 7 days were captured and are valid. Full entry logged in `docs/POST_ALPHA_TODOS.md`.

## Help menu fixes (late-session trilogy)

Three Help-menu bugs surfaced during alpha smoke testing, all fixed in a sequence of iterations:

1. **Help → Getting Started / Troubleshooting → "Documentation Not Found"** — handlers still pointed at defunct MkDocs paths (`workflows/troubleshooting/index.html`, `getting-started/index.html`). Rewrote `documentation_viewer.py` to convert `docs/USER_MANUAL.md` to a single-file HTML document on demand using Python-Markdown (new dependency: `markdown>=3.4.0`) with the `toc`, `tables`, and `fenced_code` extensions. Opens in the user's default browser. Troubleshooting handler in `main_window.py` now calls `open_section("11-troubleshooting")`.

2. **Help → User Guide opened whatever external markdown viewer was installed** — users without a native markdown viewer saw nothing useful, and anchor handling varied wildly by viewer. The Python-Markdown + browser approach replaces the external-viewer handoff with an in-process render that the app fully controls.

3. **Internal TOC links were dead** — solved by Python-Markdown's `toc` extension, which generates heading IDs matching the GitHub-convention slugs the manual's TOC already uses.

Two follow-on iterations were needed after the initial rewrite:

- The first render added `<base href="file:///.../docs/">` so `<img src="images/...">` would resolve. That broke all fragment-only TOC links, because the browser resolved `href="#1-introduction"` against the base and sent it to the `docs/` directory listing. Dropped the `<base>` tag; rewrite `src="images/..."` to absolute `file://` URIs at render time.
- Direct-anchor navigation (Help → Getting Started) still landed on the TOC. Diagnosed as URL-fragment loss somewhere in the macOS `webbrowser → osascript open location → browser` pipeline, or scroll-restoration overriding on initial load. Fix: don't pass the target as a URL fragment. Render one HTML per target section with the target baked in as `window.__THAMES_TARGET_SECTION`; an in-page script reads that constant and scrolls. Internal TOC links still work because same-page hash changes never leave the page.

## About dialog / version bump

- Credits pane rendered `<span size="small">Texas A&M University</span>` literally for the first author. Root cause: GTK's Credits pane runs each author line through the Pango markup parser, which interprets `&` as the start of an entity. `"A&M University"` fails to parse, so Pango wraps the broken source in `<span>` and displays it verbatim. Fix: pre-escape `&` → `&amp;` in the authors list.
- Cleaned up the About dialog to read every field (`APP_VERSION`, `APP_TITLE`, `APP_WEBSITE`, `ORG_NAME`, `AUTHORS`, `LICENSE_TEXT`) from `src/app/resources/app_info.py`. Eliminates duplicated hard-coded copies in `main_window.py`.
- **`APP_VERSION` bumped from `10.0.0` to `1.0.0-alpha.1`** (SemVer 2.0.0 pre-release identifier). THAMES forks off the VCCTL v10 architecture but ships a different hydration engine, so it starts its own 1.x line rather than continuing 10.x.
- New `APP_VERSION_STAGE = "alpha"` constant drives a visible "ALPHA pre-release, not for production use" banner next to the tagline in the About dialog.
- `USER_MANUAL.md` gains a version/status line under the title so the rendered HTML immediately shows the alpha status.
- Annotated git tag `v1.0.0-alpha.1` created on `main` and pushed to origin.

## Windows alpha prep document

New `docs/ALPHA_RELEASE_PREPARATION.md` captures the end-to-end Windows packaging recipe: pre-session sync, dependency refresh, C++ verification, smoke tests, PyInstaller build, Inno Setup wrap, README template, GitHub pre-release marking, and feedback triage. Designed so the next session can follow the steps in order without having to reconstruct context.

## Cumulative file changes for Session 41

New services/tests: `concelas_service.py`, `concelas_runner.py`, `test_concelas_service.py`, `test_concelas_runner.py`.
New docs: `POST_ALPHA_TODOS.md`, `session41_summary.md`, `ALPHA_RELEASE_PREPARATION.md`, six screenshot PNGs.
Modified: `documentation_viewer.py`, `effective_moduli_viewer.py`, `elastic_moduli_panel.py`, `mix_design_panel.py`, `operations_monitoring_panel.py`, `main_window.py`, `app_info.py`, `USER_MANUAL.md`, `requirements.txt`, both PyInstaller specs, `CLAUDE.md`. DB direct-reconciled for orphan RUNNING op.
Tag: `v1.0.0-alpha.1`.

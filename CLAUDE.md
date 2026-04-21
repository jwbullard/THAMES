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

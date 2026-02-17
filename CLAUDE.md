# THAMES Project - Claude Context

## Project Overview

THAMES is a GTK-based application for advanced cement hydration simulation, using the THAMES-Hydration C++ simulator. This project is based on the VCCTL architecture but adapted for the upgraded hydration simulation engine.

**Based on:** VCCTL v10.0.0
**Hydration Engine:** THAMES-Hydration (C++)
**Started:** November 2025

## Key Differences from VCCTL

### Hydration Simulator
- **VCCTL:** Uses disrealnew.c (C implementation)
- **THAMES:** Uses THAMES-Hydration (C++ implementation)

### Input Generation
[To be documented during migration]

### Output Format
[To be documented during migration]

### Microstructure Generation
[To be documented during migration]

## Development Sessions

### Session 1: Repository Setup
November 15, 2025 (Morning)
- Created THAMES repository
- Copied VCCTL infrastructure
- Added THAMES-Hydration as git submodule
- Initial project documentation
- THAMES C++ code analysis

### Session 2: GEMS Integration & Materials Architecture
November 15, 2025 (Afternoon)

**Key Accomplishments**:
- Integrated GEMS3K thermodynamic database (100 phases, 198 DCs)
- Created GEMSParserService to parse thames-dch.dat and build phase-to-DC mappings
- Designed tag-based materials architecture (phases + flexible tags, no kinetics)
- Created phase mappings between VCCTL and GEMS naming conventions
- Set up virtual environment with PyGObject 3.52.3

**Files Created**: `src/data/gems/`, `src/app/services/gems_parser_service.py`, `src/app/config/phase_mappings.py`

---

### Session 3: Material System + UI Phase 1
November 16, 2025

**Key Accomplishments**:
- Created material database schema (material, tag, material_tags, material_phase tables)
- Implemented automatic density calculation from GEMS molar volumes
- Migrated 36 cements + 1 limestone from VCCTL (183 phase entries, 100% success)
- Created MaterialService with full CRUD operations (~800 lines)
- Built Materials UI Phase 1: MaterialsPanel, TagChipInput widget, MaterialDialog

**Testing**: 16/16 tests passed (MaterialService, density calculation, migration, UI)

---

### Session 4: Clinker/Cement Material System
November 18, 2025

**Key Accomplishments**:
- Added ClinkerExtension model with 6 surface area fractions and 7 correlation function BLOBs
- Implemented "Add from Material" feature in PhaseCompositionEditor
- Automatic clinker tracking when phases from clinker materials are added to cements
- Materials created by adding clinker phases (scaled by fraction) plus additional phases (sulfates, etc.)

**Files Created**: `src/app/models/clinker_extension.py`, `src/app/models/material_component.py`

---

### Session 5: Clinker Re-migration + PSD UI + Clinker Fraction Editor
November 20, 2025

**Key Accomplishments**:
- Re-migrated 36 VCCTL cements with clinker data (surface fractions + 161 correlation BLOBs)
- Integrated VCCTL's UnifiedPSDWidget (5 distribution types: Rosin-Rammler, Log-Normal, Fuller-Thompson, Custom, Discrete)
- Implemented editable clinker fraction editor with proportional scaling
- Made MaterialDialog scrollable to prevent overflow

**User Feedback**: "That is definitely working now. I like it a lot. I don't immediately see anything else that needs to be done with the Materials page."

---

### Session 6: Mix Design Validation + Phase ID Mapping System
November 21, 2025

**Key Accomplishments**:
- Fixed Mix Design validation for THAMES mode (MaterialSelector vs VCCTL type_combo)
- Suppressed concrete-specific warnings for THAMES materials
- Created PhaseIdMappingService with dynamic phase ID assignment (~385 lines)
- THAMES Phase ID Rules: 0=VOID, 1=ELECTROLYTE, 2-7=Clinker phases, 8+=Other phases
- Comprehensive test suite: 10/10 tests passing

**Files Created**: `src/app/services/phase_id_mapping_service.py`, `tests/test_phase_id_mapping_service.py`

---

### Session 7: MicgenInputService Implementation & Testing
November 26, 2025

**Key Accomplishments**:
- Debugged micgen.c (fixed stack overflow, unallocated pointer)
- Implemented complete PSD system with discretization for all 5 modes
- Weighted PSD combination for multiple materials contributing to same phase
- Comprehensive unit tests: 15/15 passing
- UI integration in mix_design_panel.py
- Fixed executable name: genmic → micgen

**Files Created**: `src/app/services/micgen_input_service.py` (~1,100 lines), `tests/test_micgen_input_service.py` (~414 lines)

**Dependencies**: `pip install scipy` (for log-normal PSD)

---

### Session 8: Results Page Adaptation & Phase Color System
November 27, 2025

**Key Accomplishments**:
- Created PhaseColorService with ~90 GEMS phase colors (~400 lines)
- Updated Results Viewer to support THAMES phase mappings (loads from JSON)
- Added support for THAMES microstructure header format (`#THAMES:` prefix)
- Phase name standardization: `aq_gen` → `Electrolyte`, `arcanite` → `Arcanite`, `thenardite` → `Thenardite`
- Fixed operations page progress tracking (micgen_progress.json)

**THAMES Phase ID Convention**: 0=VOID (black), 1=Electrolyte (dark blue), 2-7=Clinker phases, 8=AGGREGATE, 9+=Dynamic

**Files Created**: `src/app/services/phase_color_service.py`

---

### Session 9: THAMES Hydration Panel UI Implementation
November 28, 2025

**Key Accomplishments**:
- Complete THAMES Hydration Panel replacement (~850 lines)
- Created ElectrolyteCompositionEditor with real-time charge balance validation (~420 lines)
- Hydration product tree with category checkboxes for bulk selection
- Simulation parameters: Resolution, temperature, moisture conditions (Saturated/Sealed), time parameters
- Fixed GEMS parser path issues

**Testing**: All 31 unit tests pass

**Files Created**: `src/app/widgets/electrolyte_composition_editor.py`

---

### Session 10: THAMES Hydration Panel Refinements
November 29, 2025

**Key Accomplishments**:
- Unified microstructure phases and hydration products into single tree view
- Full kinetic model editing for ANY phase (Thermodynamic, ParrotKilloh, Standard, Pozzolanic)
- UI improvements: Carbon edit icon, limestone cement type auto-selection
- Kinetic configuration management (add/remove/edit)

**User Feedback**: "Looks nice! I like the Carbon icon you chose." / "It looks great now and I think it is working pretty well."

---

### Session 11: Hydration Progress Tracking & Bug Fixes
December 5, 2025

**Key Accomplishments**:
- Fixed Arcanite/Thenardite case mismatch bug (lowercase vs capitalized)
- Fixed phase_colors.json remapping bug (nested JSON structure)
- THAMES C++ progress.json format fix (user corrected Controller.cc to write proper JSON with commas)
- Hydration progress tracking on Operations page (cycle, time_hours, target_time_hours)
- Fixed premature "Simulation completed successfully!" message
- Fixed progress callback signature mismatch
- UI improvements: Always-visible scrollbars, keyboard navigation

**THAMES C++ Changes**: Fixed Controller.cc progress.json format, added target_time_hours

---

### Session 12: Hydration Results Visualization & Preferences UI
December 6, 2025

**Key Accomplishments**:
- Fixed kinetic model attachment bug (phases without built-in defaults)
- Fixed 3D visualization time sequence bug (THAMES file pattern `JobRoot.YYYyDDDdHHhMMm.TTTK.img`)
- Implemented kinetic preferences system (user defaults stored in JSON)
- Added Kinetic Defaults tab to preferences dialog (search, edit, reset, import/export)
- Implemented hydration output visualization with tabbed interface (3D + Data Plots)
- Data plots: Multi-select variables, log axes, custom ranges, line width, color schemes, export to PNG/PDF/SVG

**CSV Output Files**: Phase Volumes, Solution Chemistry, Saturation Indices, Surface Areas, Enthalpy

**Files Created**: `src/app/services/kinetic_preferences_service.py` (~273 lines)

---

### Session 13: Elastic Moduli UI Integration for THAMES
December 10, 2025

**Key Accomplishments**:
- THAMES backend detection and support (`thames -s 5` for elastic calculations)
- Fixed THAMES hydration operations discovery (Result/ subdirectory, simparams.json)
- Fixed THAMES microstructure discovery (pattern: `*.YYYyDDDdHHhMMm.TTTK.img`)
- Auto-population of UI fields when microstructure selected
- Collapsible microstructure settings (Expander, collapsed by default)
- Pimg file handling and copy during hydration setup

**Files Created**: `src/app/services/elastic_defaults_service.py`

---

### Session 14: Executable Paths & Elastic Moduli Input Fix
December 16, 2025

**Key Accomplishments**:
- Fixed hydration operation lineage tracking (parent_operation_id now set in database)
- Standardized executable paths to top-level `bin/` folder (not `backend/bin/`)
- Fixed THAMES elastic calculation input format (stdin, not command-line args)
- THAMES elastic input: Line 1=5 (ELASTIC_CALC), Line 2=thames-dat.lst, Line 3=simparams.json, Line 4=microstructure.img
- Copy GEMS database files to elastic operation directory
- Updated 6 files to use `bin/` with fallbacks

**Files Created**: `bin/.gitkeep`

---

### Session 15: Unified Voxel Ordering Convention (X-Fastest)
December 18, 2025

**Context**: Unified micgen.c (Z-fastest) and THAMES C++ (X-fastest) voxel ordering. Changed all code to use X-fastest for consistency with VTK/PyVista.

**Key Changes**:
- **memutil.c** `getInt3dindex()`: Changed to `x + (xsize * y) + (xsize * ysize * z)`
- **micgen.c** file loop: Changed to Z-outer, Y-middle, X-inner
- **Python**: Reshape to `(z_size, y_size, x_size)`, VTK dims to `(shape[2], shape[1], shape[0])`

**Testing**: All test combinations passed (with/without slab × long dimension in x/z)

**Git Commits**: `ad6bf72` (baseline), `267a771` (X-fastest)

---

### Session 16: Multi-Temperature GEMS Database & Hydration Products Expansion
December 20, 2025

**Key Accomplishments**:
- Debugged GEMS database for multi-temperature support (277-353K, 39 temperature points)
- Added 11 new phases: Mullite, C2AS, CA2S, CAS, CAS2, K6A2S, Diopside, Albite, Anorthite, Fayalite, Forsterite
- Final database: **100 phases, 198 DCs**
- Expanded hydration products from ~32 to **82 phases** (chloride AFm, zeolites, silicates, pozzolanic, carbonates, ferrite/aluminate hydrates, Fe oxides, etc.)
- Successful multi-temperature testing at 10°C, 25°C, and 40°C

**Name Fixing Script** (for new GEMS exports):
```bash
sed -i '' -e "s/'aq_gen'/'Electrolyte'/g" -e "s/'arcanite'/'Arcanite'/g" -e "s/'thenardite'/'Thenardite'/g" thames-dch.dat thames-dbr.dat
```

---

### Session 17: Elastic Results Visualization & Homebrew Safety
December 23, 2025

**Key Accomplishments**:
- Fixed EffectiveModuli and ITZModuli viewers for THAMES 3-column CSV format (`Property,Value,Units`)
- Strain energy viewer code preserved (THAMES C++ doesn't output energy.img yet)
- Homebrew safety analysis: Pinned high-risk packages (pygobject3 3.52.3, py3cairo 1.28.0, gobject-introspection 1.84.0)

**Homebrew Commands**:
```bash
brew pin pygobject3 py3cairo gobject-introspection
```

---

### Session 18: Strain Energy Visualization & 3D Orientation Axes
December 26, 2025

**Key Accomplishments**:
- 3D orientation axes indicator in corner viewport (vtkAxesActor, real-time camera sync)
- Strain energy visualization using VTK (vtkThreshold, vtkGlyph3D, vtkLookupTable)
- Support for THAMES `Result/energy.img` files and `#THAMES:` header prefix

**Key Methods**:
- `_create_orientation_axes_renderer()`: Axes with enlarged arrowheads, RGB colors, labels at 1.3× distance
- `_sync_axes_camera()`: Synchronizes orientation with main camera (fixed distance 8.0)

**User Feedback**: "That is as close to perfect as I think we are going to get."

---

### Session 19: Windows Migration - Initial Setup & UI Launch
December 29, 2025

**Platform:** Windows 10 (19045.6691)

**Key Accomplishments**:

1. **Windows Development Environment Setup**
   - Created `thames-env-windows` using MSYS2 Python 3.12.12
   - Enabled system site-packages for PyGObject 3.54.3, PyVista 0.36.0, SQLAlchemy 2.0.43
   - Location: `C:\msys64\mingw64\bin\python.exe`

2. **Scipy Import Fix (Cross-Platform)**
   - Made scipy import lazy (moved to method level in `micgen_input_service.py`)
   - Benefit: Application launches without scipy, only needed for log-normal PSD mode

3. **Database Migration from macOS**
   - Copied 2.8 MB database: 45 materials, 6 tags, 16 operations
   - From: `~/Library/Application Support/THAMES/database/thames.db` (macOS)
   - To: `C:\Users\jwbullard\AppData\Local\THAMES\database\thames.db` (Windows)

4. **Platform-Specific Compatibility Fixes**

   **Fix 1: Unicode Arrow Encoding**
   - Problem: Windows console cp1252 encoding, Unicode arrow `→` caused `UnicodeEncodeError`
   - Fix: Replaced all `→` with `->` in 5 files (operations_monitoring_panel.py, elastic_lineage_service.py, pyvista_3d_viewer.py, material_dialog.py, mix_design_panel.py)
   - Impact: Works on both platforms, ASCII arrows less decorative but cross-platform safe

   **Fix 2: GTK CSS Platform-Specific Properties**
   - Problem: Windows GTK doesn't support `-gtk-overlay-scrolling` property
   - Fix: Added platform check in `theme_manager.py`: `overlay_scrolling_css = "" if sys.platform == "win32" else "\n            -gtk-overlay-scrolling: false;"`
   - Impact: Windows skips property, macOS/Linux apply as before

5. **Successful GUI Launch**
   - Command: `thames-env-windows/bin/python src/main.py`
   - All 6 tabs display correctly, 94 materials (45 THAMES + 49 VCCTL), 6 tags, 16 operations
   - No encoding errors, no crashes

**Testing Status**: ✓ Launch, ✓ Materials, ✓ Tags, ✓ Database, ✓ All tabs, ✓ Operations, ✓ Logging

**Known Limitations**:
1. Scipy not installed - use Rosin-Rammler, Fuller-Thompson, Custom, or Discrete PSD modes
2. Backend executables not built - need `bin/thames.exe`, `bin/micgen.exe`
3. Minor CSS warning (cosmetic only)

**Next Steps**: Compile C++ backend with MSYS2 MinGW, test workflow, VTK visualization

**Platform Safety**: All changes use `sys.platform == "win32"` checks, macOS unchanged, cross-platform compatible

---

### Session 20: Windows Backend Build & ImageMagick Removal
December 30, 2025

**Platform:** Windows 10 with MSYS2 MinGW-w64

**Key Accomplishments**:

1. **Built Complete C++ Backend on Windows**
   - GEMS3K-standalone library (libGEMS3K-static.a)
   - THAMES-Hydration (thames.exe)
   - Micgen microstructure generator (micgen.exe)
   - Created comprehensive `docs/WINDOWS_BUILD_GUIDE.md`

2. **GCC 15 Compatibility Fix**
   - Added `#include <cstdint>` to `GEMS3K-standalone/GEMS3K/io_simdjson.h`
   - Required for `int64_t` type declaration

3. **Removed ImageMagick Dependency**
   - Created `PngWriter.h` utility using native libpng
   - Modified `Lattice.cc` and `ElasticModel.cc` to use `PngWriter::convertPpmToPng()`
   - Added `find_package(PNG REQUIRED)` to CMakeLists.txt
   - Movie frames now saved as PNG (animation can be done in post-processing)

4. **Fixed Uninitialized Pointer Variables**
   - `Lattice.cc:2605`: `Site *ste = nullptr; Site *stenb = nullptr;`
   - `Lattice.cc:6125`: `Site *ste = nullptr;`
   - These caused "may be used uninitialized" warnings on GCC but not Clang

5. **Added Particle Shape Sets**
   - Copied `particle_shape_set/` directory from VCCTL (12 shape sets)
   - Copied `particle_shape_set.tar.gz` (254 MB) for PyInstaller builds

**Files Created/Modified**:
- `backend/thames-hydration/src/thameslib/PngWriter.h` (new)
- `backend/thames-hydration/src/thameslib/Lattice.cc` (ImageMagick removal + nullptr fixes)
- `backend/thames-hydration/src/thameslib/ElasticModel.cc` (ImageMagick removal)
- `backend/thames-hydration/CMakeLists.txt` (added PNG library)
- `backend/thames-hydration/src/GEMS3K-standalone/GEMS3K/io_simdjson.h` (cstdint fix)
- `docs/WINDOWS_BUILD_GUIDE.md` (new)
- `particle_shape_set/` and `particle_shape_set.tar.gz` (copied from VCCTL)

**Issue Under Investigation**: Windows thames.exe crashes during first cycle while Mac version works. User is comparing input files between platforms.

**Issue Resolved in Session 21**: Windows crash was caused by compiler differences (GCC vs Clang) and `long int` size differences (32-bit on Windows, 64-bit on macOS).

---

### Session 21: Windows Clang Build & Platform Compatibility Fixes
December 31, 2025

**Platform:** Windows 10 with MSYS2 MinGW-w64 + Clang 21.1.1

**Key Accomplishments**:

1. **Installed Clang Compiler on Windows**
   - `pacman -S mingw-w64-x86_64-clang` (Clang 21.1.1)
   - Rebuilt both GEMS3K and THAMES with Clang
   - Build command: `/c/msys64/mingw64/bin/cmake -G "MinGW Makefiles" -DCMAKE_C_COMPILER=/c/msys64/mingw64/bin/clang.exe -DCMAKE_CXX_COMPILER=/c/msys64/mingw64/bin/clang++.exe -DCMAKE_MAKE_PROGRAM=/c/msys64/mingw64/bin/mingw32-make.exe ..`

2. **Fixed Missing libpng DLL**
   - Copied `libpng16-16.dll` from `/c/msys64/mingw64/bin/` to `bin/`
   - Required because PngWriter.h uses libpng

3. **Fixed Uninitialized Variables in Site.cc**
   - Added `wmc_ = 0;` and `wmc0_ = 0;` to both constructors (default and overloaded)
   - These were causing garbage values in wmc calculations

4. **Fixed Integer Overflow (Windows vs macOS Platform Difference)**
   - **Root Cause**: `long int` is 64-bit on macOS but only 32-bit on Windows
   - Changed `long int` to `long long int` in Lattice.cc (4 places):
     - `sumWmcInt` (lines 2642, 6168)
     - `affSumInt` (line 1245)
     - `wAffSumInt, vAffSumInt` (line 2197)
     - `sumWmcT` (line 6297)
   - These values accumulate over 60,000+ sites with values ~1-2 million each, easily exceeding 32-bit int max

5. **Fixed Git LFS for Large File**
   - Migrated `particle_shape_set.tar.gz` (266 MB) to Git LFS
   - Command: `git lfs migrate import --include="*.tar.gz" --everything`
   - Force pushed to remote after history rewrite

6. **Git Authentication Setup on Windows**
   - Deleted cached credentials: `cmdkey /delete:git:https://github.com`
   - Installed git-lfs: `pacman -S mingw-w64-x86_64-git-lfs`
   - Used GitHub classic token with `repo` scope

7. **Homebrew Fix on macOS (Side Issue)**
   - Fixed `libsimdjson.26.dylib` not found error with `brew reinstall node`

**Files Modified**:
- `backend/thames-hydration/src/thameslib/Site.cc` (wmc initialization)
- `backend/thames-hydration/src/thameslib/Lattice.cc` (long int → long long int)
- `bin/libpng16-16.dll` (copied from MSYS2)

**Test Results**: Hydration simulation ran successfully through 110+ cycles (400+ hours simulated)

**Platform Compatibility Notes**:
- `long int`: 64-bit on macOS, 32-bit on Windows → use `long long int` for cross-platform 64-bit
- `long long int`: 64-bit on both platforms
- All fixes are compatible with both macOS (Clang) and Windows (Clang)

---

### Session 22: Git Sync Fix, W/B Ratio Limits & Progress Time Units
January 5, 2026

**Platform:** macOS (Darwin 25.2.0)

**Key Accomplishments**:

1. **Fixed Git Repository Sync After LFS Migration**
   - pre-session-sync.sh failed due to rebase conflicts from Session 21's Git LFS force push
   - Local and remote histories had diverged (28 vs 31 commits, no common ancestor)
   - Resolved by resetting local to remote, then merging submodule changes
   - Merged divergent thames-hydration submodule commits:
     - `f251cb2` (Windows fixes) + `92e7efc` (linear time scaling)

2. **Removed W/B Ratio and Water Content Limits**
   - User needed W/B ratio up to 10000 for dilute suspension simulations
   - Updated 8 locations with hard-coded limits:
     - `mix_design_panel.py`: SpinButton ranges (W/B: 2.0→10000, Water: 10000→100000)
     - `mix_design.py`: Pydantic models (W/B: 2.0→10000, total_water_content: 1000→100000)
     - `mix_service.py`: Dataclass validation (W/B: 2.0→10000)
     - `microstructure_service.py`: Config validation (W/B: 2.0→10000)

3. **Adaptive Time Units for Hydration Progress Display**
   - Problem: Short simulations (2 min) showed "Time: 0.00d of 0.0d"
   - Created `format_simulation_time()` helper function
   - Auto-selects units based on target simulation time:
     - Minutes (`m`) if target < 1 hour
     - Hours (`h`) if target < 24 hours
     - Days (`d`) if target >= 24 hours
   - Updated 3 locations in `operations_monitoring_panel.py`

**Files Modified**:
- `src/app/windows/panels/mix_design_panel.py` (SpinButton ranges)
- `src/app/models/mix_design.py` (Pydantic validation limits)
- `src/app/services/mix_service.py` (dataclass validation)
- `src/app/services/microstructure_service.py` (config validation)
- `src/app/windows/panels/operations_monitoring_panel.py` (time formatting)
- `backend/thames-hydration` (submodule merge)

**Example Progress Display**:
- 2-minute sim: `"Cycle 50, Time: 1.50m of 2.0m, DOH: 0.012"`
- 12-hour sim: `"Cycle 500, Time: 6.25h of 12.0h, DOH: 0.234"`
- 30-day sim: `"Cycle 2000, Time: 15.50d of 30.0d, DOH: 0.678"`

---

### Session 23: Adaptive Time Stepping Analysis & Planning
January 6, 2026

**Platform:** macOS (Darwin 25.2.0)

**Key Accomplishments**:

1. **Fixed GEMS3K Standalone Build Issues**
   - Removed thameslib references from GEMS3K CMakeLists.txt (was pulling in PngWriter.h → libpng dependency)
   - Added platform auto-detection to `install.sh` (macOS/Windows/Linux)
   - Created `strainenergy_standalone.cpp` to provide missing extern symbol for standalone builds

2. **Fixed Output Time Preview Bug**
   - Problem: Hydration Tab showed "1 ms" instead of ~100 time points for 1-minute simulation
   - Root cause: `merge_times()` deduplication used 0.001 days (1.44 min) absolute tolerance
   - Fix: Use 1-second absolute tolerance when comparing small times
   - Also added unit sync: spacing unit now follows final time unit automatically

3. **Deep Analysis of THAMES C++ Time Stepping Architecture**
   - Analyzed all time-related code in `thameslib/`
   - Found time steps are pre-generated with fixed linear increment (0.00006 hours)
   - Identified "GODZILLA" comments flagging need for adaptive stepping
   - Documented current failure recovery: halve timestep + random sampling (up to 1000 tries)

4. **Deep Analysis of GEMS3K Solver**
   - Analyzed Interior Point Method (IPM-3) algorithm
   - Identified failure modes: max iterations (7000), dual divergence, singular R matrix
   - Found accessible convergence data: `GEM_Iterations()`, `NodeStatusCH`, `pm.PCI`, `pm.DXM`
   - Key insight: GEMS has NO built-in step rejection - failures must be handled by THAMES

5. **Created Comprehensive Adaptive Time Stepping Implementation Plan**
   - 5-phase implementation plan with detailed code specifications
   - New `AdaptiveTimeController` class design (~400 lines)
   - PI-like control based on GEMS iteration counts and convergence metrics
   - Optional kinetic-based prediction module
   - Full testing strategy and configuration options

**Files Created**:
- `docs/adaptive_timestepping_implementation_plan.md` (~700 lines)
- `backend/thames-hydration/src/GEMS3K-standalone/GEMS3K/strainenergy_standalone.cpp`

**Files Modified**:
- `backend/thames-hydration/src/GEMS3K-standalone/GEMS3K/CMakeLists.txt`
- `backend/thames-hydration/src/GEMS3K-standalone/install.sh`
- `src/app/services/time_generator_service.py` (deduplication fix)
- `src/app/windows/panels/thames_hydration_panel.py` (unit sync)

**Key Technical Findings**:

| GEMS Data | Access Method | Use for Adaptive Stepping |
|-----------|---------------|---------------------------|
| IPM iterations | `GEM_Iterations(&prec, &fia, &ipm)` | Convergence difficulty metric |
| Convergence status | `NodeStatusCH` enum | Success/failure classification |
| Dikin criterion | `pm.PCI` | How close to convergence |
| Error codes | 2=max iter, 5=divergence | Failure type classification |

**Next Steps (Priority)**:
1. Implement Phase 1: Add GEMS convergence accessors to ChemicalSystem
2. Implement Phase 2: Create AdaptiveTimeController class
3. Implement Phase 3: Integrate into Controller::doCycle()

---

### Session 24: Adaptive Time Stepping Implementation
January 7, 2026

**Platform:** macOS (Darwin 25.2.0)

**Key Accomplishments**:

1. **Phase 1: GEMS Convergence Accessors (ChemicalSystem)**
   - Added `getPCI()` - Returns Dikin's criterion from GEMS solver
   - Added `getDXM()` - Returns convergence threshold
   - Added `getDetailedIterations()` - Returns breakdown of IPM iteration counts
   - Added `getConvergenceRatio()` - Returns PCI/DXM ratio for quality assessment

2. **Phase 2: AdaptiveTimeController Class (New Files)**
   - Created `AdaptiveTimeController.h` (~347 lines) with:
     - `GEMSResultType` enum (SUCCESS_EASY/NORMAL/HARD, FAILURE_STIFFNESS/STRUCTURAL/TERMINAL)
     - `AdaptiveTimeConfig` struct with configurable parameters
     - Full class documentation
   - Created `AdaptiveTimeController.cc` (~275 lines) with:
     - PI-like control algorithm based on GEMS iteration counts
     - History tracking with moving averages
     - Configurable growth/shrink factors (default: grow 1.2×, shrink 0.5×)
     - Max consecutive failures limit (default: 50)

3. **Phase 3: Controller Integration**
   - Added `adaptiveTimeController_` unique_ptr member to Controller
   - Added `useAdaptiveTimeStepping_` flag (enabled by default)
   - On GEMS success: Records iteration count, PCI, DXM to adaptive controller
   - On GEMS failure: Gets new smaller timestep from adaptive controller
   - Timestep selection respects output times and final simulation time
   - Legacy mode preserved when adaptive disabled

4. **Removed Random Guessing from calculateState()**
   - Deleted ~90 lines of random time sampling code (up to 1000 tries)
   - Retry logic now handled entirely by doCycle() with AdaptiveTimeController
   - Cleaner, more predictable failure recovery

**Branch:** `adaptive-timestepping` (local, not pushed)

**Commits on Branch:**
| Commit | Description |
|--------|-------------|
| `d6ed993` | Phase 1-2: GEMS accessors + AdaptiveTimeController class |
| `e8dfa0b` | Phase 3: Integration into Controller |
| `b3a6b84` | Remove random guessing from calculateState() |

**Files Created:**
- `backend/thames-hydration/src/thameslib/AdaptiveTimeController.h` (~347 lines)
- `backend/thames-hydration/src/thameslib/AdaptiveTimeController.cc` (~275 lines)

**Files Modified:**
- `backend/thames-hydration/src/thameslib/ChemicalSystem.h` (+50 lines)
- `backend/thames-hydration/src/thameslib/ChemicalSystem.cc` (+35 lines)
- `backend/thames-hydration/src/thameslib/Controller.h` (+48 lines)
- `backend/thames-hydration/src/thameslib/Controller.cc` (+125/-143 lines)

**Total Changes:** +880 lines added, -143 lines removed

**Testing Status:** Compiles successfully, not yet tested with simulation

**Next Session:**
1. Test adaptive time stepping with a simulation
2. Push branch to remote: `git push -u origin adaptive-timestepping`
3. If tests pass, merge to main

**Technical Details - Dikin's Criterion:**
- Named after I.I. Dikin (Russian mathematician, 1967)
- Part of Interior Point Method (affine scaling algorithm)
- PCI measures duality gap (primal vs dual solution agreement)
- When PCI < DXM, solver has converged
- PCI/DXM ratio indicates convergence quality (< 1.0 = good, > 100 = near failure)

---

### Session 25: Adaptive Time Stepping Testing & Kinetics-Based Initial Timestep
January 13, 2026

**Platform:** macOS (Darwin 25.2.0)

**Key Accomplishments:**

1. **Adaptive Time Stepping Testing**
   - **Result-Adaptive-01**: Failed at ~12.9 hours with GEMS MBR (Mass Balance Refinement) errors
   - Root cause: E04IPM errors due to near-zero IC (Independent Component) moles
   - **Fix applied**: Raised ICTHRESH from 1.0e-9 to 1.0e-8 in `global.h`
   - **Fix applied**: Call `checkICMoles()` every cycle (not just first cycle)

2. **SIA Mode Experiment (Failed)**
   - **Result-Adaptive-02**: Tried using SIA (Smart Initial Approximation) for non-first cycles
   - Failed earlier at ~0.031 hours with E06IPM (IPM Main Descent) errors
   - Root cause: Large IC changes between cycles made previous solution a poor starting point
   - **Reverted**: Back to always using AIA mode with `GEM_run(true)`

3. **Successful Test Run**
   - **Result-Adaptive-03**: Running successfully past the 12.9 hour failure point
   - At time of session end: ~47.6 hours simulated, 248 cycles, DOH 34.7%, no GEMS errors
   - Full 30-day simulation still in progress

4. **Kinetics-Based Initial Timestep Implementation**
   - Problem: Hard-coded 0.001h initial timestep not physics-based
   - Solution: Set initial timestep to limit DC mole changes to 5% per timestep
   - Formula: `dt = maxRelativeChange / maxRate` (clamped to [dt_min, dt_max])

   **New Methods Added:**
   | Class | Method | Purpose |
   |-------|--------|---------|
   | `KineticModel` | `estimateInitialDissolutionRate()` | Virtual base (returns 0.0) |
   | `ParrotKillohModel` | `estimateInitialDissolutionRate()` | Uses PK rate equations at DOR=0.001 |
   | `StandardKineticModel` | `estimateInitialDissolutionRate()` | Uses rate constant k with conservative assumptions |
   | `PozzolanicModel` | `estimateInitialDissolutionRate()` | Similar to Standard with OH- effects |
   | `KineticController` | `getMaxInitialDissolutionRate()` | Scans all kinetic models, returns max rate |
   | `AdaptiveTimeController` | `setInitialTimestepFromKinetics()` | Computes physics-based initial dt |

5. **Verified Microstructure Consistency Check**
   - Confirmed existing behavior in `Controller.cc` lines 1015-1290
   - When `lattice_->changeMicrostructure()` returns 0 (can't implement GEMS result):
     - System resets to initial state
     - Lower limits set on DCs based on sites that couldn't dissolve
     - GEMS re-runs with constraints
   - This is separate from adaptive time stepping (constrains GEMS vs reduces timestep)

**Files Modified:**
- `backend/thames-hydration/src/thameslib/KineticModel.h` (+5 lines)
- `backend/thames-hydration/src/thameslib/ParrotKillohModel.h` (+1 line)
- `backend/thames-hydration/src/thameslib/ParrotKillohModel.cc` (+45 lines)
- `backend/thames-hydration/src/thameslib/StandardKineticModel.h` (+1 line)
- `backend/thames-hydration/src/thameslib/StandardKineticModel.cc` (+30 lines)
- `backend/thames-hydration/src/thameslib/PozzolanicModel.h` (+1 line)
- `backend/thames-hydration/src/thameslib/PozzolanicModel.cc` (+35 lines)
- `backend/thames-hydration/src/thameslib/KineticController.h` (+1 line)
- `backend/thames-hydration/src/thameslib/KineticController.cc` (+15 lines)
- `backend/thames-hydration/src/thameslib/AdaptiveTimeController.h` (+5 lines)
- `backend/thames-hydration/src/thameslib/AdaptiveTimeController.cc` (+30 lines)
- `backend/thames-hydration/src/thameslib/Controller.cc` (+10 lines)
- `backend/thames-hydration/src/thameslib/global.h` (ICTHRESH: 1.0e-9 → 1.0e-8)
- `backend/thames-hydration/src/thameslib/ChemicalSystem.cc` (checkICMoles every cycle)

**Performance Note:**
- Adaptive time stepping is more conservative than random sampling approach
- Current growth_factor=1.2 may be too slow; future tuning suggested
- Potential optimizations: increase growth_factor to 1.5-2.0, reduce successes_for_growth

**Test Results Summary:**
| Test | Result | Issue |
|------|--------|-------|
| Result-Adaptive-01 | Failed at 12.9h | E04IPM (MBR errors) |
| Result-Adaptive-02 | Failed at 0.031h | E06IPM (SIA mode) |
| Result-Adaptive-03 | Running (47.6h+) | No errors |

---

### Session 26: User Manual Documentation & Simulation Analysis
January 20, 2026

**Platform:** macOS (Darwin 25.2.0)

**Key Accomplishments:**

1. **Created Comprehensive THAMES User Manual**
   - Created `docs/USER_MANUAL.md` (~1,100 lines) following VCCTL documentation style
   - 15 main sections covering all aspects of THAMES
   - 3 detailed workflows with step-by-step instructions
   - Troubleshooting section including GEMS solver error explanations
   - 4 appendices: Phase reference, kinetic parameters, file formats, keyboard shortcuts
   - Glossary with cement chemistry terminology

2. **Added Screenshot Placeholders**
   - Created `docs/images/` folder for screenshots
   - Added 27 image placeholders throughout the User Manual
   - Organized by section with descriptive filenames (01-main-window.png through 27-workflow3-elastic.png)

3. **Result-Adaptive-04 Test Run**
   - Created `run_adaptive_04.sh` script with proper stdin redirection and output capture
   - Ran 10-hour simulation (345.73 simulated hours, 1,092 cycles)
   - Exit code 0 (normal termination)
   - Documented performance baseline for future comparison

4. **Simulation Early Exit Analysis**
   - **Issue**: Simulation stopped at 14.4 days instead of target 30 days
   - **Root Cause**: High CO2 concentration (0.5 mol/kg) in electrolyte settings
   - **Effect**: Portlandite never precipitated (SI ~10⁻¹³), system filled with carbonates
   - **Termination**: Ran out of nucleation sites (45,789 requested, 45,597 available)

5. **Performance Metrics Documentation**
   - Created `Result-Adaptive-04/PERFORMANCE_SUMMARY.md` with baseline metrics
   - Key metrics for future comparison:
     - 33.5 seconds per cycle
     - 34.0 simulated hours per wall hour
     - Average timestep: 19 minutes
     - 0 GEMS failures

**Files Created:**
- `docs/USER_MANUAL.md` (~1,100 lines)
- `docs/images/` (folder for screenshots)
- `Result-Adaptive-04/run_adaptive_04.sh`
- `Result-Adaptive-04/PERFORMANCE_SUMMARY.md`

**User Manual Sections:**
1. Introduction
2. Getting Started
3. User Interface Overview
4. Materials Management
5. Mix Design
6. Microstructure Generation
7. Hydration Simulation
8. Elastic Properties
9. Operations Monitoring
10. Results Analysis
11. Workflows (3 examples)
12. Troubleshooting
13. Appendices (A-D)
14. Glossary
15. References

**Screenshot Placeholders (27 total):**
- Section 3: Main window, Preferences dialogs (3)
- Section 4: Materials panel, dialog, phase editor, tags (4)
- Section 5: Mix design, PSD configuration (2)
- Section 6: Microstructure config, 3D view (2)
- Section 7: Hydration panel, kinetics, electrolyte, products, time (5)
- Section 8: Elastic panel, results (2)
- Section 9: Operations panel, progress (2)
- Section 10: 3D viewer (axes, slice), data plots (4)
- Section 11: Workflow results (3)

**Performance Baseline (Result-Adaptive-04):**
| Metric | Value |
|--------|-------|
| Microstructure | 110 × 100 × 100 (1.1M voxels) |
| Simulated time | 345.73 hours (14.4 days) |
| Wall clock time | 10.16 hours |
| Cycles | 1,092 |
| Final DOH | 65.2% |
| Seconds/cycle | 33.5 |
| Avg timestep | 19 minutes |
| GEMS failures | 0 |

**CO2 Issue Analysis:**
- Configured CO2@: 0.5 mol/kg (should be ~10⁻⁶ for normal hydration)
- Portlandite SI: ~10⁻¹³ (extremely undersaturated)
- pH dropped from 13.2 to 5.2 in first cycle
- Portlandite never formed; all Ca went to carbonates and C-S-H

**Next Steps:**
1. User to capture 27 screenshots for User Manual
2. Run more challenging adaptive time stepping test
3. Analyze and optimize adaptive time stepping performance (growth_factor tuning)
4. Add adaptive time stepping config to simparams.json

---

### Session 27: Carbonation Testing, Timestep Tuning & Sub-Minute Output Files
January 22, 2026

**Platform:** macOS (Darwin 25.2.0)

**Context:** User testing carbonation simulations (CalThermoHet series) with Portlandite dissolving and Calcite precipitating in CO2-rich environment.

**Key Accomplishments:**

1. **Carbonation Simulation Debugging (CalThermoHet-10)**
   - User tested with 10× higher Portlandite dissolution rate constant (4e-5 → 4e-4)
   - Caused numerical instability: Portlandite SI overshot equilibrium (reached 5.5, then 8)
   - GEMS failed 50+ consecutive times; simulation terminated at 130 seconds instead of 600
   - **Root cause**: High rate constant made system too "stiff" for the timestep

2. **Saturation Index Interpretation Correction**
   - Clarified SI semantics: SI = 1 at equilibrium, SI < 1 undersaturated, SI > 1 supersaturated
   - SI = 0 means infinitely undersaturated (pure water), NOT equilibrium

3. **Smaller Minimum Timestep Implementation**
   - Modified `Controller.cc` to use smaller timesteps for stiff systems:
     - `stepTimeTHR_`: 1e-3 → 1e-5 hours (minimum timestep now 0.036 seconds)
     - `dt_initial` default: 0.001 → 0.0001 hours (~0.36 seconds)
     - `maxRelativeChange`: 5% → 2% (more conservative for high driving forces)

4. **Sub-Minute Output Filename Bug Fix**
   - **Problem**: User set 0.3-minute (18-second) output spacing, expected ~35 images, got only 11
   - **Root cause**: `getTimeString()` only used minutes in filename, rounding to nearest minute
   - Multiple output times (0.0, 0.3, 0.6 min) all mapped to same filename `00h00m`, overwriting each other
   - **Solution**: Added seconds to filename when non-zero
   - New filename format: `000y000d00h00m18s.298K.img` (seconds appended only when > 0)
   - Backward compatible: files without seconds still work

5. **Python Regex Updates for New Filename Format**
   - Updated `elastic_lineage_service.py`: Pattern now handles optional `(?:(\d{2})s)?` suffix
   - Updated `hydration_results_viewer.py`: Pattern and time calculation include seconds

**Files Modified:**

*C++ (thames-hydration submodule):*
- `src/thameslib/Controller.cc`:
  - `getTimeString()`: Added seconds to filename when > 0
  - Removed unused variables from old rounding logic
  - Timestep parameters: smaller minimum and initial timesteps

*Python (main repo):*
- `src/app/services/elastic_lineage_service.py`: Updated THAMES filename regex and time parsing
- `src/app/windows/dialogs/hydration_results_viewer.py`: Updated THAMES filename regex and time parsing

**Technical Details - Filename Format:**

| Time (minutes) | Old Filename | New Filename |
|----------------|--------------|--------------|
| 0.0 | `00h00m` | `00h00m` |
| 0.3 (18 sec) | `00h00m` (collision!) | `00h00m18s` |
| 0.6 (36 sec) | `00h01m` (rounded) | `00h00m36s` |
| 0.9 (54 sec) | `00h01m` (collision!) | `00h00m54s` |
| 1.2 (72 sec) | `00h01m` (collision!) | `00h01m12s` |

**Test Simulations:**
| Test | Config | Result |
|------|--------|--------|
| CalThermoHet-10 | 10× rate constant | Failed - SI overshoot, 50+ GEMS failures |
| CalThermoHet-11 | 3× rate constant | Ran 17,790 cycles, only 11 images (filename collision bug) |
| CalThermoHet-11 (after fix) | Pending | User to test with sub-minute output intervals |

**Next Steps:**
1. User to test CalThermoHet with sub-minute output intervals
2. Verify all 35 output images are created with unique filenames
3. Continue carbonation kinetics tuning

---

### Session 28: Model-Aware Adaptive Time Stepping & UI Charge Balance Validation
January 25, 2026

**Platform:** macOS (Darwin 25.2.0)

**Context:** User reported ParrotKilloh-only cement hydration simulations were 5-10x slower than before due to overly conservative adaptive time stepping parameters.

**Key Accomplishments:**

1. **Model-Aware Adaptive Time Stepping**
   - **Problem**: Conservative adaptive parameters designed for SI-driven models were slowing down PK-only simulations
   - **Solution**: Implemented automatic model type detection via `hasSignificantSIDrivenMass()` method
   - **Behavior**: Detects kinetic model types at simulation start and applies appropriate parameters

   **Parameter Selection by Model Type:**
   | Model Type | dt_initial | dt_max | growth_factor | successes_for_growth | maxRelChange |
   |------------|------------|--------|---------------|---------------------|--------------|
   | SI-driven (Standard, Pozzolanic) | 0.0001h | 1.0h | 1.2 | 3 | 2% |
   | DOR-driven (ParrotKilloh only) | 0.01h | 12.0h | 2.0 | 1 | 5% |

2. **Fast-Dissolving Phase Exclusions**
   - **Problem**: Bassanite and Gypsum use StandardKineticModel but dissolve quickly, triggering conservative mode unnecessarily
   - **Solution**: Added exclusion list for fast-dissolving sulfate phases
   - **Excluded Phases**: Bassanite, Gypsum, Arcanite, Thenardite (case-insensitive)
   - These phases are skipped when determining if SI-driven models are present

3. **GEMS E05IPM Failure Analysis (PKTest-03)**
   - **Issue**: Simulation failed at 209.27 hours with E05IPM (Mass Balance Refinement) errors
   - **Root Cause**: Carbon IC dropped from ~8.9e-08 to ~4.9e-08 mol, approaching ICTHRESH
   - **User's Solution**: Increased initial DC concentrations by 10x
   - **Result**: Simulation completed in ~5 minutes (matching original performance)

4. **Electrolyte Charge Balance UI Fix (CalciteTestAfter)**
   - **Problem**: Carbonation test failed with "Electrolyte charge imbalance" error
   - **Root Cause**: `std::map::insert()` in C++ ignores duplicate keys - only first K+ entry was used
   - **UI had K+ listed twice**: First entry (2e-05 mol) kept, second entry (0.004 mol) ignored
   - **Net charge seen by backend**: +0.00002 - 0.00402 = -0.004 (not balanced)
   - **UI Fix**: Added duplicate detection to `ElectrolyteCompositionEditor`:
     - `_update_charge_balance()` now detects and warns about duplicate DC entries
     - Shows red ERROR message: "Duplicate entries for [DC]. Only first value will be used!"
     - Calculates charge using first-occurrence-only logic (matching C++ backend)
     - `is_charge_balanced()` returns False if duplicates exist

**Files Modified:**

*C++ (thames-hydration submodule):*
- `src/thameslib/KineticController.h`: Added `hasSignificantSIDrivenMass()` declaration
- `src/thameslib/KineticController.cc`: Implemented model detection with fast-dissolving exclusions (~40 lines)
- `src/thameslib/Controller.cc`: Model-aware adaptive parameter selection (~30 lines)

*Python (main repo):*
- `src/app/widgets/electrolyte_composition_editor.py`:
  - `_update_charge_balance()`: Added duplicate detection and first-occurrence-only charge calculation
  - `is_charge_balanced()`: Returns False if duplicates exist

**Technical Details - Model Detection Logic:**
```cpp
bool KineticController::hasSignificantSIDrivenMass() const {
  static const std::vector<std::string> fastDissolvingPhases = {
      "Bassanite", "Gypsum", "Arcanite", "Thenardite",
      "bassanite", "gypsum", "arcanite", "thenardite"
  };

  for (int i = 0; i < pKMsize_; ++i) {
    if (phaseKineticModel_[i] != nullptr) {
      std::string modelType = phaseKineticModel_[i]->getType();
      if (modelType == StandardType || modelType == PozzolanicType) {
        std::string phaseName = phaseKineticModel_[i]->getName();
        // Skip fast-dissolving phases
        if (isFastDissolving(phaseName)) continue;
        return true;  // Found SI-driven model requiring conservative settings
      }
    }
  }
  return false;  // Only PK models - use aggressive settings
}
```

**Test Results:**
| Test | Configuration | Result |
|------|---------------|--------|
| PKTest-03 (initial) | Default adaptive params | Slow (~10x slower than expected) |
| PKTest-03 (after exclusions) | Model-aware params | Still triggered conservative (Bassanite/Gypsum) |
| PKTest-03 (with 10x DCs) | Model-aware + exclusions | Completed in ~5 minutes |
| CalciteTestAfter | Duplicate K+ entries | Failed: charge imbalance |
| CalciteTestAfter (fixed) | Single Na+ entry | Working |

**Key Insight - std::map::insert() Behavior:**
```cpp
// C++ backend code (parseSolutionComp):
initialSolutionComposition_.insert(make_pair(testDCId, testConc));
// If testDCId already exists, the NEW value is IGNORED (not summed or replaced)
```

**Next Steps:**
1. Consider implementing more sophisticated GEMS error recovery (IC adjustment strategies)
2. Monitor adaptive time stepping performance on various simulation types
3. Potential future work: Anticipatory IC monitoring before problems occur

---

### Session 29: GEMS Phase Name Fixes & Data Plot Enhancements
January 28, 2026

**Platform:** macOS (Darwin 25.2.0)

**Context:** User reported HydrationOf-Cem152-w45 (Portland cement with ParrotKilloh model) failing around cycle 60. Also requested data plotting enhancements for the Results tab.

**Key Accomplishments:**

1. **Fixed GEMS Phase Name vs DC Name Confusion**
   - **Problem**: Simulation failed with "No GEM phase data for a microstructure phase" for hydrotalcite
   - **Root Cause**: `hydration_products_service.py` had `gems_name="hydrotalcite"` which is a DC name, not a GEMS phase name
   - **GEMS Terminology**: A *phase* (e.g., `OH-hydrotalc`) contains one or more *DCs* (e.g., `hydrotalcite`)
   - **Fixes Applied in Three Locations**:

   | File | Fix |
   |------|-----|
   | `hydration_products_service.py` | Changed `gems_name="hydrotalcite"` to `"OH-hydrotalc"`, `gems_name="zeoliteP_Ca"` to `"ZeoliteP"` |
   | `simparams_service.py` | Added `_get_gems_phase_name()` helper to look up correct GEMS phase name from product data |
   | `hydration_input_service.py` | Fixed `_create_phase_mapping()` and `create_default_config()` to use `product_data.gems_name` |

2. **Added Anhydrite to Fast-Dissolving Exclusion List**
   - **Problem**: Portland cement simulations still running slowly despite model-aware adaptive time stepping
   - **Root Cause**: Anhydrite uses StandardKineticModel but wasn't in the fast-dissolving exclusion list
   - **Fix**: Added "Anhydrite" and "anhydrite" to `fastDissolvingPhases` in `KineticController.cc`
   - **Note**: Requires C++ rebuild to take effect

3. **Data Plot Time Unit Selection (Feature 1)**
   - Added "Time Units" dropdown to Plot Options with choices: Days, Hours, Minutes
   - X-axis label updates automatically based on selection
   - Useful for fast simulations where days would show "0.00d"

4. **Multi-Simulation Comparison Plotting (Feature 2)**
   - Added "Compare with Simulations" section in Data Plots tab
   - **Add...** button shows dialog listing available hydration operations
   - **Remove** button removes selected comparison simulation
   - Plotting behavior:
     - Primary simulation uses solid lines (`-`)
     - Comparison simulations use different line styles (`--`, `-.`, `:`, etc.)
     - Same color used for same variable across simulations
     - Legend entries include simulation name in parentheses

**Files Modified:**

*C++ (thames-hydration submodule):*
- `src/thameslib/KineticController.cc`: Added "Anhydrite" to fast-dissolving phases exclusion list

*Python (main repo):*
- `src/app/services/hydration_products_service.py`: Fixed gems_name for hydrotalcite and zeoliteP_Ca
- `src/app/services/simparams_service.py`: Added `_get_gems_phase_name()` helper method
- `src/app/services/hydration_input_service.py`: Fixed phase mapping to use GEMS phase names
- `src/app/windows/dialogs/hydration_results_viewer.py`:
  - Added `comparison_data` and `comparison_liststore` instance variables
  - Added time unit ComboBox (`time_unit_combo`)
  - Added comparison simulations UI section
  - Updated `_on_create_data_plot_clicked()` to handle time units and multi-simulation comparison
  - Added `_on_add_comparison_simulation()`, `_load_comparison_operation()`, `_on_remove_comparison_simulation()` methods

**Technical Details - GEMS Phase vs DC Names:**
```
GEMS Phase Name    DC Names (components within phase)
---------------    ----------------------------------
OH-hydrotalc       hydrotalcite
ZeoliteP           zeoliteP_Ca, zeoliteP_K, zeoliteP_Na
CSHQ               CSHQ_TobH, CSHQ_TobD, CSHQ_JenH, CSHQ_JenD
```

**Test Status:**
- HydrationOf-Cem152-w45 simulation running (cycle 20+ at session end)
- Performance fix (Anhydrite exclusion) requires C++ rebuild
- Data plotting features not yet tested (simulation in progress)

**Next Steps:**
1. Rebuild C++ backend with Anhydrite exclusion fix
2. Test data plotting time unit selection
3. Test multi-simulation comparison plotting

---

### Session 30: Unified Adaptive Stepping, IC Depletion Recovery & Exit Status Messaging
February 3, 2026

**Platform:** macOS (Darwin 25.2.0)

**Context:** Testing adaptive time stepping with various simulation types. E05IPM GEMS failure occurred at ~556 hours in HydrationOf-AllThree-03 due to IC depletion.

**Key Accomplishments:**

1. **Simplified Adaptive Time Stepping (Unified Parameters)**
   - Removed model-type detection (`hasSignificantSIDrivenMass()`)
   - Now uses unified parameters for all simulation types:
     - `dt_initial = 0.001h` (~3.6 seconds)
     - `dt_max = 4.0h`
     - `growth_factor = 1.5`
     - `successes_for_growth = 2`
   - Kinetics-based timestep constraint provides dynamic adaptation
   - Fast-dissolving exclusion list no longer needed

2. **IC Depletion Recovery with Charge Compensation**
   - **Problem**: ICs dropping below ICTHRESH caused E05IPM (Mass Balance Refinement) failures
   - **Solution**: When IC depleted, add corresponding aqueous DC mass to maintain stoichiometry
   - **IC-to-DC Mapping**: Ca→Ca+2, Fe→Fe+2, Al→Al+3, K→K+, Na→Na+, etc.
   - **Charge Compensation**: Track charge from added DCs, balance with H+ or OH-
   - **Maintainer Documentation**: Added comments explaining how to extend mapping for new ICs

3. **UI Exit Status Messaging**
   - **C++ Backend**: Added `writeExitStatus()` method to write `exit_status.json`
   - **Exit Points**: Called at normal completion and MAX FAILURES EXCEEDED
   - **Python UI**: Added `_check_hydration_exit_status()` to read exit status
   - **User Alert**: Shows error dialog with reason and diagnostics when simulation fails

4. **Test Results**
   - CarbPort-02: ✅ Completed normally (0.5h target)
   - HydrationOf-AllThree-04: ✅ Completed normally (672h/28d target)
   - HydrationOf-AllThree-EarlyAge-01: ✅ Completed normally (72h/3d target)

5. **Hydration Tab UI Improvements**
   - **Validation time units**: Fixed "Final time" in validation output to use selected unit (was hardcoded "days")
   - **Microstructure reference label**: Added small text below Operation Name showing selected microstructure name for easy reference when naming operations

6. **GEMS Documentation**
   - Created `docs/GEMS_DC_STOICHIOMETRY_GUIDE.md` - comprehensive guide explaining how to extract DC stoichiometry from GEMS
   - Covers TNode direct access and ChemicalSystem wrapper functions
   - Includes examples for solid solutions and phase composition

**Files Modified:**

*C++ (thames-hydration submodule):*
- `src/thameslib/ChemicalSystem.h`: IC depletion recovery with charge compensation (~120 lines added)
- `src/thameslib/Controller.cc`: Unified adaptive params, writeExitStatus calls (+61 lines)
- `src/thameslib/Controller.h`: Added writeExitStatus declaration (+14 lines)
- `src/thameslib/KineticController.cc`: Removed hasSignificantSIDrivenMass() (-57 lines)
- `src/thameslib/KineticController.h`: Removed hasSignificantSIDrivenMass() declaration (-21 lines)

*Python (main repo):*
- `src/app/windows/panels/operations_monitoring_panel.py`: Added `_check_hydration_exit_status()` method and integration (+76 lines)
- `src/app/windows/panels/thames_hydration_panel.py`: Validation time units fix, microstructure reference label (+20 lines)

*Documentation:*
- `docs/GEMS_DC_STOICHIOMETRY_GUIDE.md`: New guide for extracting DC stoichiometry from GEMS (~280 lines)

**Commits:**
- `96065c5` (submodule): Add IC depletion recovery with charge compensation & exit status reporting
- `c4ebfe26` (main): Session 30: IC depletion recovery & UI exit status messaging
- Additional commit pending: UI fixes and GEMS documentation

---

### Session 31: User Manual Documentation Updates
February 4, 2026

**Platform:** macOS (Darwin 25.2.0)

**Context:** User captured 27 screenshots for the User Manual and needed to integrate them, plus fix several documentation issues.

**Key Accomplishments:**

1. **Screenshot Integration**
   - Moved 26 screenshots from `tmp/UserManualImages/` to `docs/images/`
   - Renamed files from `Figure_XX.YY.png` to descriptive names (e.g., `01-main-window.png`)
   - Updated all image references in USER_MANUAL.md
   - Removed references to 2 missing screenshots (18-elastic-results.png, 25-workflow1-results.png)

2. **Section 3.2 Tab Navigation Fix**
   - Removed incorrect "Microstructure" tab from table (it's part of Mix Design)
   - Added missing "Operations" tab between Elastic and Results
   - Updated table to show 6 correct tabs

3. **Section 3.3 Preferences Fix**
   - Updated General Tab to match actual UI (Auto-save, Confirm destructive actions)
   - Added Performance Tab section (Worker threads, Memory limit, Caching)
   - Added Affinity Defaults Tab section
   - Removed non-existent Paths Tab

4. **Section 4.2 Creating Materials Enhancement**
   - Added missing fields: Specific Gravity, Specific Surface Area, Particle Shape, Material Type
   - Reordered steps to match actual dialog layout

5. **Section 4.5 Import/Export Materials**
   - Marked as future feature (not yet implemented)

6. **Major Restructuring: Merged Microstructure into Mix Design**
   - Removed old Section 5.3 "Saving Mix Designs" (doesn't exist)
   - Added new Section 5.3 "Aggregates" with types, configuration, and grading
   - Merged old Section 6 (Microstructure Generation) into Section 5:
     - 5.4 Microstructure Configuration
     - 5.5 Resolution and Dimensions
     - 5.6 Running Microstructure Generation
     - 5.7 Viewing Generated Microstructures
   - Renumbered all subsequent sections (7→6, 8→7, etc.)
   - Updated Table of Contents to match new structure
   - Updated all figure numbers throughout

7. **Section 9.2 Data Plots Enhancement**
   - Added Time Units option (Days, Hours, Minutes)
   - Added Multi-Simulation Comparison subsection with step-by-step instructions
   - Fixed figure number 10.4 → 9.4

**Files Modified:**
- `docs/USER_MANUAL.md`: Major restructuring and content updates (~200 lines changed)
- `docs/images/`: 26 screenshots added with descriptive names

**New Section Structure:**
| Old # | New # | Section |
|-------|-------|---------|
| 5 | 5 | Mix Design (now includes microstructure) |
| 6 | - | Microstructure Generation (merged into 5) |
| 7 | 6 | Hydration Simulation |
| 8 | 7 | Elastic Properties |
| 9 | 8 | Operations Monitoring |
| 10 | 9 | Results Analysis |
| 11 | 10 | Workflows |
| 12 | 11 | Troubleshooting |
| 13 | 12 | Appendices |
| 14 | 13 | Glossary |
| 15 | 14 | References |

### Session 32: Configurable Adaptive Time Stepping UI & Runtime Concentration Safety
February 11, 2026

**Platform:** macOS (Darwin 25.3.0)

**Context:** Continuation of previous session implementing configurable adaptive time stepping parameters exposed through the UI + simparams.json, plus runtime electrolyte concentration safety in the C++ backend.

**Key Accomplishments:**

1. **Configurable Adaptive Time Stepping (Tasks 1-4 Complete)**
   - **Task 1 (simparams_service.py)**: Added `AdaptiveSteppingConfig` dataclass, optional `adaptive_stepping` field on `TimeConfig`, updated `_build_time_parameters()` to include the config in JSON output
   - **Task 2 (hydration_input_service.py)**: Added `adaptive_stepping` field to `HydrationInputConfig`, wired through `to_dict()`/`from_dict()`/`_generate_simparams()`
   - **Task 3 (thames_hydration_panel.py)**: Added "Adaptive Time Stepping" UI section with enable checkbox + Expander containing 7 SpinButtons (dt_initial, dt_max, growth_factor, shrink_factor, successes_for_growth, max_consecutive_failures, max_relative_change), updated `_build_config()` to collect values
   - **Task 4 (Controller.cc/h)**: Added `maxRelativeChange_` member, initialized in constructor, read adaptive_stepping JSON section in `parseDoc()`, replaced hard-coded 0.05 values, re-computes kinetics-based initial timestep after config loaded

2. **IC_FLOOR Proactive Depletion Prevention**
   - **Problem**: Test simulation HY-TestAdaptiveUI-01 failed with E05IPM (R-matrix degeneration) due to ICs at 1e-5 to 1e-6 mol — above ICTHRESH (1e-8) but too small for numerical stability
   - **Solution**: Added `IC_FLOOR = 1.0e-5` constant to `global.h` (separate from ICTHRESH)
   - Updated `checkICMoles()` in `ChemicalSystem.h` to trigger at IC_FLOOR instead of ICTHRESH
   - **User constraint**: IC_FLOOR must NOT go above 1e-5; if problems persist, a fundamentally different approach is needed

3. **Runtime Electrolyte Concentration Safety**
   - **Problem**: Default electrolyte concentrations (1e-6 mol/kg) can produce DC moles below IC_FLOOR when water mass is small
   - **Solution**: In `setInitialElectrolyteComposition()` (ChemicalSystem.cc), computes `minConc = IC_FLOOR / waterMass` dynamically based on actual water mass
   - Any DC concentration below `minConc` is automatically overridden
   - Writes `concentration_overrides.json` to operation directory for UI notification
   - Logs all overrides to `std::clog`

4. **UI Notification of Concentration Overrides**
   - Added `_check_concentration_overrides()` method to `operations_monitoring_panel.py`
   - Reads `concentration_overrides.json` on first successful hydration progress update
   - Shows info dialog listing adjusted species, minimum concentration, and water mass
   - Each operation checked only once (tracked by `_overrides_checked` set)

5. **Reverted Unnecessary Python UI Changes**
   - Reverted default electrolyte concentrations back to 1e-6 mol/kg (simparams_service.py)
   - Removed `MIN_RECOMMENDED_CONCENTRATION` constant and import
   - Removed CSS warning provider and concentration warning logic from electrolyte_composition_editor.py
   - Reverted new-DC and fallback defaults back to 1e-6
   - Rationale: Runtime C++ check handles this dynamically, so static UI defaults/warnings are unnecessary

**Files Modified:**

*C++ (thames-hydration submodule):*
- `src/thameslib/Controller.h`: Added `maxRelativeChange_` member variable
- `src/thameslib/Controller.cc`: Constructor init, `parseDoc()` JSON reading for adaptive_stepping, replaced hard-coded `0.05` values, re-computes kinetics-based initial timestep after config load
- `src/thameslib/global.h`: Added `IC_FLOOR = 1.0e-5` with warning documentation
- `src/thameslib/ChemicalSystem.h`: Updated `checkICMoles()` to use IC_FLOOR (3 places)
- `src/thameslib/ChemicalSystem.cc`: Added runtime min_concentration check in `setInitialElectrolyteComposition()`, writes `concentration_overrides.json`

*Python (main repo):*
- `src/app/services/simparams_service.py`: Added `AdaptiveSteppingConfig` dataclass, updated `TimeConfig`, updated `_build_time_parameters()`, reverted electrolyte defaults to 1e-6, removed `MIN_RECOMMENDED_CONCENTRATION`
- `src/app/services/hydration_input_service.py`: Added `adaptive_stepping` field to `HydrationInputConfig`, wired through `to_dict()`/`from_dict()`/`_generate_simparams()`
- `src/app/windows/panels/thames_hydration_panel.py`: Added adaptive time stepping UI section (checkbox + expander + 7 SpinButtons), updated `_build_config()`
- `src/app/widgets/electrolyte_composition_editor.py`: Removed `MIN_RECOMMENDED_CONCENTRATION` import, removed CSS warning provider, removed concentration warning logic, reverted defaults to 1e-6
- `src/app/windows/panels/operations_monitoring_panel.py`: Added `_check_concentration_overrides()` method, hooked into hydration progress update

**JSON Output Format (adaptive_stepping in simparams.json):**
```json
"time_parameters": {
    "finaltime": 28.0,
    "outtimes": [...],
    "adaptive_stepping": {
        "enabled": true,
        "dt_initial": 0.001,
        "dt_max": 4.0,
        "growth_factor": 1.5,
        "shrink_factor": 0.5,
        "successes_for_growth": 2,
        "max_consecutive_failures": 50,
        "max_relative_change": 0.05
    }
}
```

**concentration_overrides.json Format:**
```json
{
  "message": "Some electrolyte concentrations were below the minimum...",
  "ic_floor_mol": 1e-05,
  "min_concentration_mol_per_kg": 0.000227,
  "water_mass_kg": 0.044,
  "overrides": [
    "AlO2H@: 1e-06 -> 0.000227 mol/kg",
    "Fe(CO3)@: 1e-06 -> 0.000227 mol/kg"
  ]
}
```

**Key Technical Details:**
- `minConc = IC_FLOOR / waterMass` where `waterMass = 0.001 × waterMoles × waterMolarMass` (kg)
- `waterMoles = pscaledMass / waterMolarMass` where `pscaledMass = wsRatio × 100.0` (grams, normalized to 100g total solids)
- Therefore `waterMass_kg = wsRatio × 0.1`
- For W/S = 0.45: `waterMass = 0.045 kg`, `minConc = 1e-5 / 0.045 ≈ 2.2e-4 mol/kg`
- Default DC concentrations (1e-6) will be overridden for most realistic W/S ratios

**Test Status:**
- C++ compiles cleanly, binary installed to `bin/thames`
- HY-TestAdaptiveUI-01 test revealed E05IPM failure → fixed by IC_FLOOR
- User testing runtime concentration override and UI notification — results pending

---

## PRIORITY TASKS

### 1. Adaptive Time Stepping Implementation (COMPLETE)

**Status:** Implementation complete including UI configuration (Session 32).

**Implementation Plan:** `docs/adaptive_timestepping_implementation_plan.md`

**Phases:**
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Add GEMS convergence accessors to ChemicalSystem | ✅ Complete |
| 2 | Create AdaptiveTimeController class | ✅ Complete |
| 3 | Integrate into Controller::doCycle() | ✅ Complete |
| 3d | Remove random guessing from calculateState() | ✅ Complete |
| 4 | Kinetics-based initial timestep | ✅ Complete |
| 5 | Configuration via simparams.json & UI | ✅ Complete (Session 32) |
| 6 | Performance tuning | ✅ Complete (Session 30 - unified params) |

**Unified Parameters (Session 30):**
- Removed model-type detection in favor of unified parameters
- Kinetics-based timestep constraint provides dynamic adaptation for all model types
- Parameters: dt_initial=0.001h, dt_max=4h, growth_factor=1.5, successes_for_growth=2

**UI Configuration (Session 32):**
- Enable/disable checkbox + 7 SpinButtons in Hydration panel
- Written to `adaptive_stepping` section in simparams.json
- C++ reads in `parseDoc()` and applies via `AdaptiveTimeController::setConfig()`

**Key Files Created:**
- `AdaptiveTimeController.h` - Header with class definition
- `AdaptiveTimeController.cc` - Implementation

**Key Files Modified:**
- `ChemicalSystem.h/cc` - Added getPCI(), getDXM(), getDetailedIterations(), getConvergenceRatio()
- `Controller.h/cc` - Integrated adaptive controller into doCycle(), removed random guessing, reads config from JSON

**To Disable Adaptive Stepping (if needed):**
In Controller constructor, change `useAdaptiveTimeStepping_ = true;` to `false`
Or uncheck "Enable adaptive time stepping" in the Hydration panel UI.

### 2. Documentation and User Guide (MOSTLY COMPLETE)

**Status:** User Manual substantially complete with screenshots integrated

**Completed:**
- `docs/USER_MANUAL.md` - Comprehensive user manual (~1,200 lines)
- `docs/images/` - 26 screenshots with descriptive names
- ✅ All screenshots captured and integrated (February 4, 2026)
- ✅ Section ordering fixed (Microstructure merged into Mix Design)
- ✅ Tab Navigation table corrected
- ✅ Preferences section updated to match actual UI
- ✅ Materials creation section expanded
- ✅ Aggregates section added
- ✅ Data Plots section updated with new features (time units, multi-sim comparison)
- ✅ Import/Export marked as future feature

**Remaining:**
- 2 missing screenshots (elastic results, workflow1 results) - references removed
- Review for any remaining inconsistencies with actual UI

---

### 3. GEMS Error Recovery Strategies (SUBSTANTIALLY COMPLETE)

**Status:** IC depletion recovery + runtime concentration safety implemented

**Completed:**
- ✅ IC depletion recovery: Add aqueous DC mass when ICs drop below IC_FLOOR (Session 30)
- ✅ Charge compensation: Balance added ionic DCs with H+ or OH- (Session 30)
- ✅ UI exit status messaging: Alert user when simulation fails abnormally (Session 30)
- ✅ Maintainer documentation for extending IC-to-DC mapping (Session 30)
- ✅ IC_FLOOR (1e-5) proactive depletion prevention in checkICMoles() (Session 32)
- ✅ Runtime electrolyte concentration safety: minConc = IC_FLOOR / waterMass (Session 32)
- ✅ concentration_overrides.json + UI notification dialog (Session 32)

**User Constraint:** IC_FLOOR must NOT exceed 1e-5 mol. If GEMS degeneration persists at this floor, a fundamentally different approach is needed (e.g., reformulating the system to remove trace ICs, or GEMS preconditioner adjustments).

**Potential Future Improvements:**
- Anticipatory IC monitoring before problems occur (detect when ICs approaching IC_FLOOR)
- Classify error types (E05IPM vs E07IPM) and apply different recovery strategies

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

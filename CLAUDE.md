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

## PRIORITY TASKS

### 1. Adaptive Time Stepping Implementation (COMPLETED - NEEDS TESTING)

**Status:** Implementation complete on `adaptive-timestepping` branch, awaiting testing

**Implementation Plan:** `docs/adaptive_timestepping_implementation_plan.md`

**Phases:**
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Add GEMS convergence accessors to ChemicalSystem | ✅ Complete |
| 2 | Create AdaptiveTimeController class | ✅ Complete |
| 3 | Integrate into Controller::doCycle() | ✅ Complete |
| 3d | Remove random guessing from calculateState() | ✅ Complete |
| 4 | Optional kinetic prediction module | Not started |
| 5 | Configuration via simparams.json | Not started |

**Key Files Created:**
- `AdaptiveTimeController.h` - Header with class definition
- `AdaptiveTimeController.cc` - Implementation

**Key Files Modified:**
- `ChemicalSystem.h/cc` - Added getPCI(), getDXM(), getDetailedIterations(), getConvergenceRatio()
- `Controller.h/cc` - Integrated adaptive controller into doCycle(), removed random guessing

**To Test:**
```bash
# In thames-hydration submodule
git checkout adaptive-timestepping

# Run a simulation and look for log messages:
# "AdaptiveTime: SUCCESS iter=..."
# "AdaptiveTime: FAILURE code=..."
# "##### Controller::doCycle - START NEW CYCLE (ADAPTIVE) ..."
```

**To Disable Adaptive Stepping (if needed):**
In Controller constructor, change `useAdaptiveTimeStepping_ = true;` to `false`

### 2. Documentation and User Guide (LOWER PRIORITY)

Create documentation for THAMES in the same form as VCCTL project.

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

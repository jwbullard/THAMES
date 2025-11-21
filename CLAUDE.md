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

**Context**: THAMES requires GEMS3K thermodynamic database for phase definitions. Unlike VCCTL's fixed material categories (Cement, Fly Ash, etc.), GEMS has 92 phases that don't map to rigid types. Phases like "Aluminate" can appear in both cement AND fly ash.

**Key Accomplishments**:

1. **GEMS Database Integration** (`src/data/gems/`)
   - Added 4 GEMS3K database files: thames-dch.dat (32KB), thames-dbr.dat (15KB), thames-ipm.dat (20KB), thames-dat.lst
   - Database contains: 13 ICs, 180 DCs (chemical species), 92 GEM phases
   - Critical structure: `<nDCinPH>` array defines which DCs belong to which phase
     - Phase 1 (aq_gen): DCs 1-69 (aqueous ions)
     - Phase 2 (gas_gen): DCs 70-77 (gases)
     - Phase 3+: Solid phases (cement, pozzolans, etc.)

2. **GEMS Parser Service** (`src/app/services/gems_parser_service.py`)
   - 400-line service that parses thames-dch.dat key-value format
   - Auto-builds phase-to-DC mappings using nDCinPH ordering
   - API: `get_phase()`, `get_dcs_for_phase()`, `validate_phase_dc_configuration()`
   - Tested with `test_gems_parser.py` - all 92 phases verified

3. **Phase Mappings** (`src/app/config/phase_mappings.py`, `docs/vcctl_to_gems_phase_mapping.md`)
   - **Cement**: 9 phases (C3S→Alite, C2S→Belite, C3A→Aluminate, C4AF→Ferrite, GYPSUM→Gypsum, etc.)
   - **Limestone**: 4 phases (Calcite, Dolomite-dis, Dolomite-ord, lime)
   - **Fly Ash**: 8 typical phases (Quartz, Mullite, Aluminate, C2AS(am), CA2S(am), etc.)
   - **Key insight**: Phases are NOT exclusive - Aluminate in both cement & fly ash

4. **Materials Architecture Design** (tag-based system)
   - **Problem**: VCCTL has 5 rigid categories, but GEMS has 92 phases with overlaps
   - **Solution**: Materials = phase composition + flexible tags, NO kinetics
     ```python
     Material {
         name: "Portland Cement Type I"
         tags: ["cement", "type-i", "portland"]  # User-defined, searchable
         phases: [{gem_phase: "Alite", mass_fraction: 0.60}, ...]
         density: 3.15
         # NO kinetic parameters
     }
     ```
   - **Kinetics in Mix Design**: User defines model + parameters when adding material to mix
   - **Migration plan**: Cements & limestones from VCCTL → THAMES, fly ash/slag/fillers user-defined

5. **Virtual Environment** (`thames-env/`)
   - Python 3.11.13 with PyGObject 3.52.3 (pinned - 3.54.5 has brew issues)
   - All dependencies installed (GTK, SQLAlchemy, Pandas, PyVista, etc.)
   - Activate: `source thames-env/bin/activate`

**Files Created**:
- `src/data/gems/` - GEMS database (4 files)
- `src/app/services/gems_parser_service.py` - Parser (~400 lines)
- `src/app/config/phase_mappings.py` - VCCTL↔GEMS mappings
- `test_gems_parser.py` - Comprehensive tests
- `docs/gems_parser_summary.md` - API documentation
- `docs/vcctl_to_gems_phase_mapping.md` - Migration reference
- `requirements.txt` - Python dependencies
- `SESSION_SUMMARY_2025_11_15.md` - Complete session details

**Next Steps** (for next session):
1. Design tag-based Material database schema (flexible tags, phase composition)
2. Create migration script to read VCCTL cements/limestones and convert to THAMES format
3. Build Material creation service (CRUD, tag management, validation with GEMS parser)
4. Adapt Materials UI panel from VCCTL (tag-based search, phase editor)

**Critical Files for Next Session**:
- VCCTL database: `/Users/jwbullard/Software/vcctl-gtk/src/data/database/vcctl.db`
- Phase mappings: `src/app/config/phase_mappings.py`
- GEMS parser: `src/app/services/gems_parser_service.py`
- VCCTL cement service (reference): `vcctl-gtk/src/app/services/cement_service.py`

---

### Session 3: Material System + UI Phase 1
November 16, 2025 (Full Day)

**Context**: Implemented complete material management system with tag-based architecture, automatic density calculations, VCCTL migration, service layer, and basic UI.

**Key Accomplishments**:

1. **Material Database Schema** (Tag-based, Flexible)
   - Created 4 tables: `material`, `tag`, `material_tags`, `material_phase`
   - PSD data required for all materials (consistent with VCCTL)
   - Materials store composition only; kinetics defined in Mix Design
   - Immutable flag for migrated VCCTL materials
   - Files: `src/app/models/material.py`, `src/app/models/material_phase.py`

2. **Automatic Density Calculation from GEMS**
   - Enhanced GEMSParserService with molar volume (V0) parsing
   - Calculate material SG from phase composition: ρ = 1 / Σ(w_i / ρ_i)
   - Methods: `get_dc_density()`, `get_phase_density()`, `calculate_material_specific_gravity()`
   - Validated: <1% error on known materials (C3S: 3.120 vs 3.15 g/cm³)
   - Optional feature - users can override with measured values

3. **VCCTL to THAMES Migration**
   - **37 materials migrated** (36 cements + 1 limestone)
   - **183 phase entries** created
   - **3 tags** created (cement, limestone, migrated-vcctl)
   - 100% success rate, all materials marked immutable
   - Phase name mappings: C3S→Alite, C2S→Belite, C3A→Aluminate, etc.
   - Script: `scripts/migrate_vcctl_materials.py` (440 lines)
   - Database: `~/Library/Application Support/VCCTL/database/thames.db` (252 KB)

4. **Material Service Layer**
   - Complete CRUD operations (~800 lines)
   - CRUD: `get_all()`, `get_by_name()`, `create()`, `update()`, `delete()`
   - Tag management: `add_tag()`, `remove_tag()`, `get_all_tags()`, `search_by_tags()`
   - Phase management: `add_phase()`, `update_phase()`, `remove_phase()`
   - Search: `search_by_tags()`, `search_by_phase()`
   - GEMS integration for validation and auto-SG calculation
   - Immutable material protection
   - File: `src/app/services/material_service.py`
   - Tests: 10/10 passed

5. **Materials UI - Phase 1** (~1,070 lines)

   **MaterialsPanel** (`src/app/windows/panels/materials_panel.py` - 409 lines)
   - Unified list view showing all materials (tag-based, no type tabs)
   - Columns: Name, Tags, SG, Phase Count, Read-only status
   - Toolbar: Add Material, Delete, Refresh buttons
   - Double-click to edit, delete with confirmation
   - Protection for immutable materials
   - Connected to MaterialService

   **TagChipInput Widget** (`src/app/widgets/tag_chip_input.py` - 220 lines)
   - Visual "chips" for tags (Material Design style)
   - Enter or comma to add tag, × button to remove
   - Duplicate detection, lowercase normalization
   - API: `get_tags()`, `set_tags()`, `add_tag()`, `clear()`

   **MaterialDialog** (`src/app/windows/dialogs/material_dialog.py` - 440 lines)
   - Create and edit modes
   - Fields: Name, Tags (chip input), SG, SSA, PSD ID, Description
   - Form validation (name required, PSD ID ≥ 1)
   - Save via MaterialService
   - Immutable material protection (disables form)
   - **Note**: Phase composition editing NOT in Phase 1 (deferred to Phase 2)

**Testing Results**:
- MaterialService: 10/10 tests passed
- Density Calculation: All tests passed
- Migration: 100% success (37/37 materials)
- UI Phase 1: 6/6 automated tests passed
- **Total: 16/16 tests passed (100%)**

**Files Created**: 20+ files
- Models: `material.py`, `material_phase.py`
- Services: `material_service.py` (enhanced `gems_parser_service.py`)
- Scripts: `init_thames_tables.py`, `migrate_vcctl_materials.py`
- UI: `materials_panel.py`, `tag_chip_input.py`, `material_dialog.py`
- Tests: `test_material_service.py`, `test_density_calculation.py`, `test_materials_ui.py`
- Docs: `material_database_schema.md`, `MIGRATION_SUMMARY.md`, `MATERIALS_UI_PHASE1.md`, `MATERIALS_UI_PHASE1_TEST_REPORT.md`

**Total Code Written**: ~4,240 lines
- Backend: ~2,400 lines (models, services, migration)
- UI: ~1,070 lines (panels, widgets, dialogs)
- Tests: ~770 lines

**Database Status**:
- Location: `~/Library/Application Support/VCCTL/database/thames.db`
- Size: 252 KB
- Records: 297 total (37 materials + 3 tags + 74 associations + 183 phases)

**Next Steps** (for next session):
1. **Manual GUI Testing** (5-10 minutes)
   - Launch THAMES, navigate to Materials tab
   - Test Add/Edit/Delete operations
   - Verify tag display and immutable protection

2. **Materials UI - Phase 2** (2-3 days)
   - PhaseCompositionEditor widget (~400-500 lines)
   - GEMS phase selector with autocomplete (~150-200 lines)
   - Add/edit/remove phases in MaterialDialog
   - Tag filtering in MaterialsPanel
   - Enhanced PSD data selection
   - Auto-calculate SG button

3. **Mix Design Service & UI**
   - Combine materials into mixes
   - Define kinetic parameters per material
   - Water/cement ratio management

**Critical Files for Next Session**:
- Materials UI: `src/app/windows/panels/materials_panel.py`
- Material Dialog: `src/app/windows/dialogs/material_dialog.py`
- Material Service: `src/app/services/material_service.py`
- GEMS Parser: `src/app/services/gems_parser_service.py`
- Database: `~/Library/Application Support/VCCTL/database/thames.db`
- Test Report: `MATERIALS_UI_PHASE1_TEST_REPORT.md`

---

### Session 4: Clinker/Cement Material System
November 18, 2025

**Context**: Implemented the clinker-to-cement workflow where clinker is the special material type with surface area fractions and correlation functions. Cements are created by adding phases from clinker materials plus additional phases (sulfates, etc.).

**Key Accomplishments**:

1. **Clinker Extension Database Schema**
   - Created `ClinkerExtension` model with 6 surface area fractions (C3S, C2S, C3A, C4AF, K2SO4, Na2SO4)
   - Added 7 correlation function BLOB columns (sil, c3s, alu, c3a, c4af, k2o, n2o)
   - Created `MaterialComponent` model for future composite support
   - Added `is_clinker`, `has_clinker`, `clinker_source_id` fields to Material model
   - Fixed SQLite autoincrement issue by overriding inherited `id` column

2. **MaterialService Clinker Methods** (~740 lines added)
   - `set_clinker_surface_fractions()` / `get_clinker_surface_fractions()`
   - `set_clinker_correlation()` / `get_clinker_correlation()`
   - `get_clinker_for_composite()` - retrieve clinker source for a cement
   - Full CRUD for clinker extension data

3. **MaterialDialog Clinker UI**
   - Material type selector: Simple Material / Clinker (removed Composite)
   - Clinker surface fraction editor with 6 spinbuttons
   - Real-time total calculation with color-coded validation
   - Clinker surface fractions saved to ClinkerExtension table

4. **"Add from Material" Feature** (PhaseCompositionEditor)
   - New button in phase editor toolbar
   - Dialog shows all materials with phases, highlights clinkers in blue
   - Scales phases by user-specified mass fraction
   - Automatically merges duplicate phases (adds fractions together)
   - Emits `clinker-source-added` signal when clinker is added

5. **Automatic Clinker Tracking**
   - When phases from a clinker material are added, `clinker_source_id` is set
   - Materials with clinker phases get `has_clinker=True`
   - Enables THAMES-Hydration to access correlation functions during simulation

**Workflow for Creating Cement**:
1. Create Clinker material with phases and surface area fractions
2. Create Simple material
3. Click "Add from Material" → select clinker (e.g., 0.95 fraction)
4. Click "Add Phase" → add gypsum, hemihydrate at remaining fractions
5. Save - system automatically tracks clinker source

**Files Created/Modified**:
- `src/app/models/clinker_extension.py` (NEW - 164 lines)
- `src/app/models/material_component.py` (NEW - 50 lines)
- `src/app/models/material.py` (updated with clinker fields + Pydantic models)
- `src/app/services/material_service.py` (added ~740 lines clinker methods)
- `src/app/widgets/phase_composition_editor.py` (added AddFromMaterialDialog)
- `src/app/windows/dialogs/thames_material_dialog.py` (clinker UI, removed composite)
- `scripts/init_thames_tables.py` (updated for new tables)

**Database Status**:
- Location: `~/Library/Application Support/THAMES/database/thames.db`
- New tables: `clinker_extension`, `material_component`
- New columns on `material`: `is_clinker`, `has_clinker`, `clinker_source_id`
- 42 materials loaded successfully

**Next Steps** (for next session):
1. **Correlation Function Import/Edit UI** (CRITICAL)
   - Add UI to import 7 correlation files (.sil, .c3s, .alu, .c3a, .c4af, .k2o, .n2o)
   - File browser for each correlation type
   - Display correlation data status in clinker editor
   - Store as BLOBs in ClinkerExtension table

2. **Mix Design Service & UI**
   - Combine materials into mixes
   - Define kinetic parameters per material
   - Water/cement ratio management

3. **VCCTL Migration Update**
   - Re-migrate VCCTL cements as clinker materials with proper surface fractions

**Critical Files for Next Session**:
- Clinker Extension: `src/app/models/clinker_extension.py`
- Material Dialog: `src/app/windows/dialogs/thames_material_dialog.py`
- Phase Editor: `src/app/widgets/phase_composition_editor.py`
- Material Service: `src/app/services/material_service.py`
- Database: `~/Library/Application Support/THAMES/database/thames.db`

---

### Session 5: Clinker Re-migration + PSD UI + Clinker Fraction Editor
November 20, 2025

**Context**: Completed three major tasks: (1) re-migrated VCCTL cements with clinker data, (2) integrated VCCTL's PSD UI widget, (3) implemented editable aggregate clinker fraction in phase editor.

**Key Accomplishments**:

1. **VCCTL Cement Re-migration with Clinker Data**
   - Updated migration script to create ClinkerExtension records
   - Migrated 36 cements with surface area fractions and 161 correlation functions
   - Fixed column name mappings (c4f → correlation_c4af)
   - Added missing database columns: `is_clinker`, `has_clinker`, `clinker_source_id`
   - 100% success rate, all correlation BLOBs stored correctly

2. **PSD UI Integration**
   - Replaced confusing "PSD Data ID" spinner with VCCTL's UnifiedPSDWidget
   - Made MaterialDialog scrollable (max height 600px) to prevent overflow
   - PSD section in collapsible Expander (collapsed by default)
   - All 5 distribution types available: Rosin-Rammler, Log-Normal, Fuller-Thompson, Custom, Discrete
   - CSV import/export working
   - Fixed: `material_service.database_service` → `material_service.db_service`

3. **Clinker Fraction Editor** (NEW FEATURE)
   - Added "Clinker from: [Material Name]" section in PhaseCompositionEditor
   - Editable "Total Clinker Fraction" spinner appears when clinker phases added
   - Proportional scaling: edit total → all 6 phases scale, maintaining ratios
   - Bidirectional sync: edit individual phase → total updates
   - Handles adding same clinker multiple times (sums fractions correctly)
   - Restores clinker tracking when loading existing materials
   - Fixed visibility bug: `set_no_show_all(False)` before `show_all()`

**Workflow Example**:
1. Create Simple Material
2. "Add from Material" → Cement 116 at 0.95
3. See "Clinker from: Cement 116" with "Total Clinker Fraction: 0.9500"
4. Edit spinner to 0.90 → all 6 phases scale proportionally
5. Add gypsum, hemihydrate at remaining fractions
6. Save - clinker tracking preserved

**Files Modified**:
- `scripts/migrate_vcctl_materials.py` - added clinker migration methods (~100 lines)
- `src/app/windows/dialogs/thames_material_dialog.py` - PSD widget + clinker restoration (~150 lines)
- `src/app/widgets/phase_composition_editor.py` - clinker fraction editor (~150 lines)

**Database Status**:
- Location: `~/Library/Application Support/THAMES/database/thames.db`
- 39 materials (36 cements + 1 limestone + 2 test)
- 36 clinker extensions with surface fractions
- 161 correlation functions (BLOBs)

**Testing Status**: ✓ All manual tests passed
- ✓ Cement migration: 36/36 with clinker data
- ✓ PSD widget: All distributions work, CSV import/export
- ✓ Clinker editor: Scaling, summing, persistence all verified

**User Feedback**: "That is definitely working now. I like it a lot. I don't immediately see anything else that needs to be done with the Materials page."

**Next Steps** (for next session):
1. **Mix Design Service & UI** (HIGH PRIORITY)
   - Design MixDesign database schema
   - Create MixDesignService with CRUD operations
   - Basic UI for creating mixes from materials
   - Water/cement ratio calculator
   - Kinetic parameter inputs per material

2. **Materials Testing** (MEDIUM PRIORITY)
   - Create test materials (fly ash, slag, limestone filler)
   - Verify phase composition validation
   - Test auto-SG calculation

**Critical Files for Next Session**:
- Material Service: `src/app/services/material_service.py`
- GEMS Parser: `src/app/services/gems_parser_service.py`
- VCCTL Mix Design (reference): `vcctl-gtk/src/app/windows/panels/mix_design_panel.py`
- VCCTL Mix Service (reference): `vcctl-gtk/src/app/services/mix_design_service.py`
- Database: `~/Library/Application Support/THAMES/database/thames.db`
- Session 5 Summary: `docs/SESSION_5_SUMMARY.md`

---

### Session 6: Mix Design Validation + Phase ID Mapping System
November 21, 2025

**Context**: Fixed Mix Design validation for THAMES mode (MaterialSelector vs type_combo), suppressed concrete-specific validation warnings, and designed/implemented dynamic Phase ID Mapping system.

**Key Accomplishments**:

1. **Mix Design Validation Fix for THAMES Mode**
   - Fixed `_create_mix_design_from_ui` to handle THAMES MaterialSelector widget
   - Fixed `_get_current_components_for_validation` similarly
   - Added conditional checks: `row.get('material_selector')` before accessing `type_combo`/`name_combo`
   - Fixed SG label parsing (format "SG: X.XXX" vs just number)
   - Validate button now works correctly in THAMES mode

2. **Concrete-Specific Warning Suppression**
   - Added `thames_mode: bool = True` flag to `MixDesignValidator` class
   - Added early-return checks in 4 validation methods:
     - `_validate_aggregate_content` - "Very high aggregate content" warning
     - `_validate_water_binder_ratio` - workability/durability warnings
     - `_validate_air_content` - strength reduction warning
     - `_validate_binder_content` - "uneconomical" warning
   - Warnings suppressed by default for THAMES (materials beyond portland cement)

3. **Phase ID Mapping Service** (NEW - ~385 lines)
   - Dynamic phase ID assignment based on mix composition
   - **THAMES Phase ID Rules**:
     - ID 0: VOID (empty pores, gas phase)
     - ID 1: ELECTROLYTE (aqueous solution, "aq_gen")
     - IDs 2-7: Clinker phases (Alite, Belite, Aluminate, Ferrite, arcanite, thenardite)
     - IDs 8+: Other phases (sulfates, pozzolans, hydration products)
   - For mixes WITHOUT clinker: IDs start at 2
   - Key classes:
     - `PhaseIdMapping` dataclass with bidirectional lookups
     - `PhaseIdMappingService` with `create_mapping_from_mix()` method
   - Phase priority sorting: sulfates → carbonates → pozzolans → others
   - Optional hydration products (Portite, CSHQ, ettr, etc.)
   - Validation method for mapping consistency

4. **Comprehensive Test Suite** (NEW - ~367 lines)
   - 10 test cases covering all scenarios:
     - `test_reserved_ids_constants` - VOID=0, ELECTROLYTE=1, FIRST_SOLID=2
     - `test_clinker_phases_list` - 6 phases in correct order
     - `test_portland_cement_mix` - IDs 2-7 for clinker, 8+ for others
     - `test_pozzolanic_mix_without_clinker` - IDs start at 2
     - `test_blended_cement_mix` - Clinker IDs reserved
     - `test_bidirectional_mapping_consistency` - gem_to_micro ↔ micro_to_gem
     - `test_validation` - Mapping validity checks
     - `test_hydration_products_included` - Optional products added
     - `test_to_dict_serialization` - JSON-ready output
     - `test_partial_clinker` - All 6 slots reserved even if partial
   - **All 10 tests pass**

**Files Created**:
- `src/app/services/phase_id_mapping_service.py` (NEW - 385 lines)
- `tests/test_phase_id_mapping_service.py` (NEW - 367 lines)

**Files Modified**:
- `src/app/windows/panels/mix_design_panel.py` - THAMES MaterialSelector handling
- `src/app/validation/mix_design_validator.py` - thames_mode flag

**Testing Status**: ✓ All tests passed
- ✓ Validate button works in THAMES mode
- ✓ Concrete warnings suppressed
- ✓ Phase ID mapping: 10/10 tests pass

**Run Tests**:
```bash
source thames-env/bin/activate
python -m pytest tests/test_phase_id_mapping_service.py -v
# Or simply:
python tests/test_phase_id_mapping_service.py
```

**BLOCKED**: Microstructure input file generation
- User needs to modify C program (genmic) first
- Exact input requirements unknown until C modifications complete

**Next Steps** (for next session):
1. **Microstructure Input File Generation** (when C program ready)
   - Integrate PhaseIdMappingService with input generation
   - Generate phase ID mapping file for THAMES-Hydration
   - Create microstructure input file format

2. **PhaseIdMappingService Integration**
   - Connect to Mix Design UI
   - Display phase ID assignments to user
   - Export mapping with simulation inputs

**Critical Files for Next Session**:
- Phase ID Mapping: `src/app/services/phase_id_mapping_service.py`
- Tests: `tests/test_phase_id_mapping_service.py`
- Mix Design Panel: `src/app/windows/panels/mix_design_panel.py`
- Mix Design Validator: `src/app/validation/mix_design_validator.py`
- THAMES global.h: `thames-hydration/src/THAMES/global.h`

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

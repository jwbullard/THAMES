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

### Session 7: MicgenInputService Implementation & Testing
November 26, 2025

**Context**: Implemented complete MicgenInputService for generating properly formatted micgen.c input files, including PSD discretization, weighted combination, and UI integration.

**Key Accomplishments**:

1. **Debugged micgen.c C Program**
   - Fixed stack overflow: `numparts[500][5000]` (9.5MB) → reduced to `[50][100]` (20KB)
   - Fixed unallocated pointer: `int *Onepixnum;` → `int Onepixnum[MAXNUMPHASES];`
   - micgen.c now runs simple examples successfully

2. **Complete PSD System Implementation** (~400 lines)
   - **Discretization methods for all 5 modes:**
     - Rosin-Rammler: R = 1 - exp(-(d/d50)^n)
     - Log-Normal: Using scipy.stats.lognorm
     - Fuller-Thompson: P(d) = (d/dmax)^exponent
     - Custom: JSON parsing with auto-normalization
     - Default: Fallback log-normal
   - **Conversion methods:**
     - `_psd_to_dict()` - Handles all modes
     - `_convert_psd_to_size_classes()` - μm→voxels, filters <0.5 voxels, renormalizes

3. **Weighted PSD Combination** (TODO 1 - CRITICAL)
   - Proper weighted averaging when multiple materials contribute to same phase
   - Algorithm: Discretize → Union grid → Interpolate → Weight → Sum → Renormalize
   - Handles edge cases (single contribution, different grids, negligible fractions)

4. **Phase Data Collection System**
   - `_aggregate_phases_by_name()` - Combines duplicate phases from materials
   - `_calculate_solids_volume_fraction()` - Normalizes to solids basis
   - `_collect_phase_data()` - Complete pipeline (aggregate → normalize → PSD → order)
   - Volume fraction calculations for clinker, other solids, electrolyte, void

5. **Clinker Distribution System**
   - `_find_clinker_material()` - UI enforces ≤1 clinker per mix
   - `_get_clinker_extension()` - Retrieves 6 surface fractions + 7 correlation BLOBs
   - `_write_correlation_files()` - Writes .sil, .c3s, .alu, .c3a, .c4af, .k2o, .n2o to temp files
   - `_get_clinker_phase_fractions()` - Extracts volume/surface fractions

6. **Comprehensive Unit Tests** (~414 lines)
   - **15/15 tests passing** ✅
   - PSD Discretization (5 tests): All modes, normalization, ranges
   - PSD Conversion (5 tests): Mode conversion, μm→voxel, filtering
   - PSD Combination (3 tests): Single/multiple contributions, interpolation
   - Utility Methods (2 tests): Volume fraction calculations

7. **UI Integration Complete**
   - Imported MicgenInputService, MaterialService, PSDDataService
   - Modified `_create_microstructure_input_file()` to use service
   - Loads database MixDesign model (using saved_mix_design_id)
   - Calls `micgen_input_service.generate_input_file()`
   - Created `_execute_genmic_program()` wrapper method

8. **Fixed Critical Executable Name Issue**
   - **IMPORTANT:** Changed all references from `genmic` → `micgen`
   - micgen.c ≠ genmic.c (different programs, different input formats!)
   - Executable location: `./backend/bin/micgen` (macOS), `./backend/bin/micgen.exe` (Windows)
   - Verified menu numbers: SPECSIZE=2, ADDAGG=3, ADDPART=4 (micgen.c format)

**Files Created**:
- `src/app/services/micgen_input_service.py` (~1,100 lines)
- `tests/test_micgen_input_service.py` (~414 lines)
- `docs/MICGEN_INPUT_SERVICE_TEST_PROCEDURE.md` (~350 lines)
- `docs/SESSION_7_SUMMARY.md` (comprehensive documentation)

**Files Modified**:
- `src/app/windows/panels/mix_design_panel.py` (~50 lines changed)
- `backend/src/micgen.c` (3 bug fixes)

**Dependencies Installed**:
```bash
pip install scipy  # Required for scipy.stats.lognorm
```

**Testing Status**:
- ✅ Unit tests: 15/15 passing
- ⏳ Integration tests: Pending manual testing (user offline)
- ⏳ End-to-end: Not started

**Run Tests**:
```bash
source thames-env/bin/activate
python -m pytest tests/test_micgen_input_service.py -v
```

**Known Limitations** (Deferred):
- ❌ Real-shape particles (TODO 4) - Infrastructure exists, needs Material model fields + UI
- ❌ Aggregate slab auto-detection - Currently hardcoded to False
- ❌ Void phase handling - Currently hardcoded to False

**Next Steps** (for next session):
1. **Manual Testing** - Follow `docs/MICGEN_INPUT_SERVICE_TEST_PROCEDURE.md`
   - Create simple single-cement mix
   - Verify input file generation
   - Run micgen.c executable
   - Check output files

2. **Debug & Iterate** - Based on test results
   - Check logs if errors occur
   - Verify input file format matches micgen-input.md
   - Test micgen.c manually if needed

3. **Future Enhancements** (After successful test)
   - Real-shape particles implementation
   - Aggregate slab auto-detection
   - Void phase based on air content
   - Additional testing (multi-material, different PSD modes, larger systems)

**Critical Files for Next Session**:
- Test Procedure: `docs/MICGEN_INPUT_SERVICE_TEST_PROCEDURE.md`
- Service: `src/app/services/micgen_input_service.py`
- Tests: `tests/test_micgen_input_service.py`
- UI Integration: `src/app/windows/panels/mix_design_panel.py` (lines 2255-2297, 3178-3210)
- Input Format: `micgen-input.md`
- Session Summary: `docs/SESSION_7_SUMMARY.md`

---

### Session 8: Results Page Adaptation & Phase Color System
November 27, 2025

**Context**: Adapted the Results page for THAMES with dynamic phase ID mappings, created a comprehensive phase color service, and standardized phase naming conventions across the codebase.

**Key Accomplishments**:

1. **Phase Color Service** (NEW - `src/app/services/phase_color_service.py`)
   - Created ~400 line service for managing phase colors
   - `PHASE_COLORS` dictionary mapping ~90 GEMS phase names to hex colors
   - Colors derived from VCCTL `colors.csv` where applicable
   - `PhaseColorMapping` dataclass for storing phase-to-color mappings
   - Key methods:
     - `get_color_for_phase(phase_name)` - returns hex color
     - `create_color_mapping(operation_name, phase_id_mapping)` - creates complete mapping
     - `save_color_mapping()` / `load_color_mapping()` - JSON persistence
     - `save_phase_id_mapping()` / `load_phase_id_mapping()` - JSON persistence
     - `hex_to_rgb()` / `hex_to_rgb_normalized()` - color format conversion

2. **Phase Mapping Integration in Mix Design**
   - Updated `mix_design_panel.py` to save phase mappings during microstructure generation
   - After `generate_input_file()`, now saves:
     - `<operation_name>_phase_mapping.json` - phase ID to name mapping
     - `<operation_name>_phase_colors.json` - phase ID to color mapping
   - Colors linked to phase **names** (not IDs) for consistency across simulations

3. **Results Viewer Updates** (`hydration_results_viewer.py`)
   - Added `_load_thames_phase_mapping()` to load JSON mappings from operation folder
   - Added unified `_get_phase_mapping()` that tries THAMES JSON first, falls back to defaults
   - Updated `_get_default_phase_mapping()` to use THAMES conventions (not VCCTL)
   - VOID (phase ID 0) always included in phase list, even if not in microstructure
   - Added support for THAMES microstructure header format (`#THAMES:` prefix)
   - Info label now shows "Phase Colors: THAMES" or "Phase Colors: VCCTL"

4. **THAMES Microstructure File Format Support**
   - Updated `_read_microstructure_file()` to handle both formats:
     - VCCTL: `X_Size: 100`
     - THAMES: `#THAMES: X_Size: 100`
   - Voxel ordering (z fastest, then y, then x) remains the same

5. **Phase Name Standardization**
   - Renamed `aq_gen` → `Electrolyte` throughout codebase
   - Renamed `arcanite` → `Arcanite` (capitalized)
   - Renamed `thenardite` → `Thenardite` (capitalized)
   - Legacy aliases kept in `phase_color_service.py` for backward compatibility
   - Updated files:
     - `phase_id_mapping_service.py` - CLINKER_PHASES list, mapping methods
     - `phase_color_service.py` - PHASE_COLORS dictionary
     - `phase_mappings.py` - VCCTL_TO_GEMS mappings
     - `hydration_results_viewer.py` - default mappings

6. **Color Corrections**
   - VOID: RGB(0,0,0) - Black
   - Electrolyte: RGB(0,20,25) - Dark blue (`#001419`)

7. **Operations Page Progress Fix** (from conversation context)
   - Fixed filename mismatch: `genmic_progress.json` → `micgen_progress.json`
   - Progress tracking now works correctly on Operations page

**THAMES Phase ID Convention** (Standardized):
| Phase ID | Name | Color |
|----------|------|-------|
| 0 | VOID | Black (0,0,0) |
| 1 | Electrolyte | Dark blue (0,20,25) |
| 2 | Alite | Blue (42,42,210) |
| 3 | Belite | Brown (139,79,19) |
| 4 | Aluminate | Light gray (178,178,178) |
| 5 | Ferrite | White (253,253,253) |
| 6 | Arcanite | Red (255,0,0) |
| 7 | Thenardite | Red-orange (255,20,0) |
| 8 | AGGREGATE | Gold (255,192,65) |
| 9+ | Other phases | Dynamic assignment |

**Files Created**:
- `src/app/services/phase_color_service.py` (~400 lines)

**Files Modified**:
- `src/app/windows/panels/mix_design_panel.py` - Added phase mapping saving
- `src/app/windows/dialogs/hydration_results_viewer.py` - THAMES phase support
- `src/app/services/phase_id_mapping_service.py` - Electrolyte/Arcanite/Thenardite naming
- `src/app/services/phase_color_service.py` - Color corrections
- `src/app/config/phase_mappings.py` - Phase name updates
- `src/app/windows/panels/operations_monitoring_panel.py` - Progress file fix
- `src/data/gems/thames-dch.dat` - User updated PHNL list

**GEMS Database Updates** (User-modified):
- Changed `aq_gen` → `Electrolyte` in PHNL list
- Changed `arcanite` → `Arcanite` in PHNL list
- Changed `thenardite` → `Thenardite` in PHNL list

**Testing Status**:
- ✅ Phase color service imports correctly
- ✅ Results viewer loads THAMES microstructures
- ✅ Phase names display correctly (user verified)
- ✅ Colors display correctly (user verified)
- ✅ VOID always appears in phase list

**User Feedback**: "It looks very good now. All the phase names are specific and the colors too."

**Next Steps** (for next session):
1. **Hydration Simulation Integration**
   - Connect THAMES-Hydration C++ engine
   - Use saved phase mappings for hydration output
   - Time-series microstructure visualization

2. **Additional Results Features**
   - Phase volume fraction plots over time
   - Export phase statistics to CSV
   - Compare multiple simulations

**Critical Files for Next Session**:
- Phase Color Service: `src/app/services/phase_color_service.py`
- Phase ID Mapping: `src/app/services/phase_id_mapping_service.py`
- Results Viewer: `src/app/windows/dialogs/hydration_results_viewer.py`
- GEMS Database: `src/data/gems/thames-dch.dat`
- Mix Design Panel: `src/app/windows/panels/mix_design_panel.py`

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

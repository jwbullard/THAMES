# Session 13: Elastic Moduli UI Integration for THAMES

**Date:** December 10, 2025

## Overview

This session focused on integrating THAMES elastic calculations into the Elastic Moduli panel UI. The work included adding THAMES backend detection, fixing operation/microstructure discovery for THAMES file formats, auto-populating UI fields, and ensuring pimg (phase ID mapping) files are properly handled for elastic calculations.

## Key Accomplishments

### 1. THAMES Backend Detection and Support

Added methods to detect and use THAMES backend for elastic calculations:

- `_is_thames_mode()` - Detects if THAMES executable is available
- `_get_thames_executable_path()` - Gets path to THAMES executable (handles PyInstaller bundle)
- `_launch_thames_elastic()` - Launches THAMES with `-s 5` flag for elastic calculation mode
- Added backend info section to UI header showing "THAMES" or "VCCTL" mode
- Disabled aggregate/ITZ settings in THAMES mode with notice about future concelas support

### 2. Fixed THAMES Hydration Operations Discovery

**Problem:** Hydration operations dropdown was empty because detection only looked for VCCTL output file patterns.

**Solution:** Updated `_load_available_hydration_operations` in `elastic_moduli_panel.py` to also detect THAMES patterns:
- Files in `Result/` subdirectory
- `simparams.json` file
- `*_Microstructure.csv` files
- `.img` files with THAMES naming convention

### 3. Fixed THAMES Microstructure Discovery

**Problem:** Microstructure dropdown was disabled because `discover_hydrated_microstructures` only recognized VCCTL file patterns.

**Solution:** Updated `elastic_lineage_service.py` with:
- THAMES pattern regex: `r'^.+\.\d{3}y\d{3}d\d{2}h\d{2}m\.\d+K\.img$'`
- Example: `HydOf-Cem152-Neat.000y030d00h00m.298K.img`
- Time label extraction from THAMES format (years, days, hours, minutes)
- Search in `Result/` subdirectory where THAMES writes outputs
- Made lineage resolution failure non-fatal (continues with microstructure discovery)

### 4. Auto-Population of UI Fields

**Problem:** Fields weren't populating when microstructure was selected because code required full lineage resolution which fails in THAMES mode.

**Solution:** Updated `_populate_fields_from_selection` to:
- Fall back to database lookup when lineage resolution fails
- Get hydration operation name directly from `_current_hydration_id`
- Auto-generate operation name: `Elastic-{HydrationName}-{TimeStep}`
- Auto-populate output directory path
- Auto-populate pimg file path

### 5. Collapsible Microstructure Settings

Changed Microstructure Settings from `Gtk.Frame` to `Gtk.Expander`:
- Collapsed by default (since fields are auto-populated)
- Label: "Microstructure Settings (auto-populated)"
- Info message explaining auto-population

### 6. Pimg File Handling for Elastic Calculations

**Context:** User is modifying THAMES elastic model to require pimg file for phase ID mapping.

**Changes:**

1. **Removed THAMES mode pimg clearing** (`elastic_moduli_panel.py`):
   - Previously cleared pimg field with "Not required for THAMES mode"
   - Now populates pimg for both THAMES and VCCTL modes

2. **Added pimg fallback discovery** (`elastic_lineage_service.py`):
   - First tries lineage resolution to find pimg in original microstructure directory
   - Falls back to searching hydration directory for `*.pimg` files

3. **Added pimg copy during hydration setup** (`thames_execution_service.py`):
   - Copies pimg file from microstructure directory to hydration directory
   - Logs warning if pimg file not found

## Files Modified

### `src/app/windows/panels/elastic_moduli_panel.py`
- Added THAMES mode detection (`_is_thames_mode`, `_get_thames_executable_path`)
- Added `_launch_thames_elastic` for THAMES elastic calculation
- Updated `_load_available_hydration_operations` for THAMES patterns
- Updated `_populate_fields_from_selection` with database fallback
- Changed Microstructure Settings to collapsible Expander
- Removed THAMES mode pimg clearing code
- Added backend info display in header
- Disabled aggregate/ITZ controls in THAMES mode with notice

### `src/app/services/elastic_lineage_service.py`
- Added THAMES microstructure file pattern recognition
- Added `_extract_time_label_thames` method
- Added pimg fallback discovery in hydration directory
- Made lineage resolution failure non-fatal
- Added `_update_lineage_display_thames_fallback` method

### `src/app/services/thames_execution_service.py`
- Added pimg file copy during hydration simulation setup
- Copies `*.pimg` alongside `*.img` to hydration directory

### `src/app/services/simparams_service.py`
- Minor updates (from earlier work)

### New File: `src/app/services/elastic_defaults_service.py`
- New service file (details TBD)

## THAMES Elastic Calculation Workflow

1. User navigates to Elastic Moduli tab
2. System detects THAMES mode and shows backend info
3. User selects a hydration operation from dropdown
4. System discovers hydrated microstructures in `Result/` subdirectory
5. User selects a hydrated microstructure (time step)
6. System auto-populates:
   - Operation name: `Elastic-{HydrationName}-{TimeStep}`
   - Output directory
   - Image filename
   - Pimg file path
7. User can expand Microstructure Settings to verify auto-populated values
8. User clicks Run to launch `thames -s 5` with simparams.json and microstructure

## THAMES File Patterns

### Hydrated Microstructure Files
- Location: `{hydration_dir}/Result/`
- Pattern: `{name}.{YYYy}{DDDd}{HHh}{MMm}.{TTT}K.img`
- Example: `HydOf-Cem152-Neat.000y030d00h00m.298K.img`
- Components:
  - `YYY` - years (3 digits)
  - `DDD` - days (3 digits)
  - `HH` - hours (2 digits)
  - `MM` - minutes (2 digits)
  - `TTT` - temperature in Kelvin

### Phase ID Mapping File
- Extension: `.pimg`
- Location: Created in microstructure operation directory, copied to hydration directory
- Purpose: Maps phase IDs to phase names for elastic calculations

## Testing Status

- ✅ Application launches successfully
- ✅ THAMES mode detection works
- ✅ Hydration operations discovered correctly
- ✅ Microstructures discovered with proper time labels
- ✅ Fields auto-populate when microstructure selected
- ✅ Microstructure Settings expander works
- ✅ Pimg file copy added to hydration setup
- ⏳ End-to-end elastic calculation test pending

## Known Issues / Future Work

1. **Aggregate/ITZ support** - Disabled in THAMES mode until concelas integration
2. **Existing hydration operations** - Won't have pimg file copied (user will recreate)
3. **Lineage tracking** - THAMES operations don't have `parent_operation_id` set

## Critical Files for Next Session

- Elastic Panel: `src/app/windows/panels/elastic_moduli_panel.py`
- Lineage Service: `src/app/services/elastic_lineage_service.py`
- THAMES Execution: `src/app/services/thames_execution_service.py`
- Elastic Defaults: `src/app/services/elastic_defaults_service.py`

## Next Steps

1. Test end-to-end elastic calculation with THAMES
2. Verify pimg file is used correctly by THAMES elastic model
3. Implement concelas integration for aggregate support (future)

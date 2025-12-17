# Session 14 Summary: Executable Paths & Elastic Moduli Input Fix
December 16, 2025

## Overview

This session focused on fixing multiple issues preventing elastic moduli calculations from running correctly. The main problems were: (1) hydration operations not tracking their parent microstructure operation, (2) executables scattered across different directories, and (3) THAMES elastic calculation not receiving proper stdin input.

## Key Accomplishments

### 1. Fixed Hydration Operation Lineage Tracking

**Problem:** Elastic moduli calculations failed with error "Parent operation microstructure not found for hydration X"

**Root Cause:** When hydration operations were created in the database, the `parent_operation_id` field was not being set, breaking the lineage chain needed by elastic calculations.

**Solution:**
- Added `source_microstructure_operation` parameter to `start_simulation()` in `thames_execution_service.py`
- Store the source operation name temporarily: `self._current_source_operation = source_microstructure_operation`
- In `_update_operation_status()`, look up the parent operation by name and set `parent_operation_id`:
  ```python
  if hasattr(self, '_current_source_operation') and self._current_source_operation:
      parent_op = session.query(Operation).filter_by(
          name=self._current_source_operation
      ).first()
      if parent_op:
          parent_operation_id = parent_op.id
  ```
- Updated `thames_hydration_panel.py` to pass `source_microstructure_operation=self.selected_operation_name`

### 2. Standardized Executable Paths to Top-Level `bin/` Folder

**User Preference:** All executables should be in `./bin/` for simplicity, not scattered across `./backend/bin/` and `./backend/thames-hydration/bin/`.

**Files Updated (6 total):**

| File | Executables | Primary Path | Fallback Paths |
|------|-------------|--------------|----------------|
| `thames_execution_service.py` | thames | `bin/` | `backend/bin/`, `backend/thames-hydration/bin/` |
| `hydration_executor_service.py` | disrealnew | `bin/` | `backend/bin/` |
| `elastic_moduli_panel.py` | thames, elastic | `bin/` | `backend/bin/`, `backend/thames-hydration/bin/` |
| `mix_design_panel.py` | micgen | `bin/` | `backend/bin/` |
| `pyvista_3d_viewer.py` | stat3d, perc3d | `bin/` | `backend/bin/` |

**Git Configuration:**
- Updated `.gitignore` to ignore `bin/*` contents but allow `bin/.gitkeep`
- Created `bin/.gitkeep` to track the directory in git

### 3. Fixed THAMES Elastic Calculation Input Format

**Problem:** Elastic moduli panel was passing command-line arguments (`-s 5 simparams.json mic.img`), but THAMES reads its input from stdin, not command-line arguments.

**Misconception:** The `-s` flag means "suppress warnings", NOT "simulation type 5".

**THAMES stdin Input Format for Elastic Calculations:**
```
5                      # Simulation type (ELASTIC_CALC = 5)
thames-dat.lst         # GEM input file
simparams.json         # Simulation parameters
<microstructure>.img   # Microstructure file to analyze
```

**Solution in `_launch_thames_elastic()`:**
1. Copy GEMS database files to output directory:
   - thames-dat.lst
   - thames-dch.dat
   - thames-ipm.dat
   - thames-dbr.dat

2. Create `input.in` file with proper format:
   ```python
   with open(input_file, 'w') as f:
       f.write("5\n")
       f.write("thames-dat.lst\n")
       f.write("simparams.json\n")
       f.write(f"{output_mic.name}\n")
   ```

3. Pass input data to process via stdin:
   ```python
   with open(input_file, 'r') as f:
       input_data = f.read()

   operation_id = operations_panel.start_real_process_operation(
       name=operation_name,
       operation_type=OperationType.ELASTIC_MODULI_CALCULATION,
       command=[str(thames_path), "-o", "Result"],
       working_dir=str(output_dir),
       input_data=input_data,  # This goes to stdin
   )
   ```

## Files Modified

### Services
- `src/app/services/thames_execution_service.py`
  - Added `source_microstructure_operation` parameter
  - Updated executable path to use `bin/` as primary
  - Added parent operation lookup in `_update_operation_status()`

- `src/app/services/hydration_executor_service.py`
  - Updated executable path to use `bin/` as primary with fallback

### Panels
- `src/app/windows/panels/thames_hydration_panel.py`
  - Pass `source_microstructure_operation=self.selected_operation_name` to `start_simulation()`

- `src/app/windows/panels/elastic_moduli_panel.py`
  - Updated `_get_thames_executable_path()` for new path hierarchy
  - Updated `_get_vcctl_elastic_path()` for new path hierarchy
  - Rewrote `_launch_thames_elastic()` to create input.in and use stdin
  - Updated error messages to reference `bin/` instead of `backend/bin/`

- `src/app/windows/panels/mix_design_panel.py`
  - Updated micgen executable path to use `bin/` as primary

### Visualization
- `src/app/visualization/pyvista_3d_viewer.py`
  - Updated stat3d path (2 locations)
  - Updated perc3d path (2 locations)

### Configuration
- `.gitignore`
  - Added `bin/*` and `!bin/.gitkeep`
  - Reorganized executable ignore patterns

### New Files
- `bin/.gitkeep` - Empty file to track bin/ directory in git

## Testing Results

- ✅ Hydration operations now correctly set `parent_operation_id`
- ✅ Elastic moduli calculation launches successfully
- ✅ `input.in` file created with correct THAMES format
- ✅ GEMS database files copied to elastic output directory
- ✅ Executables found correctly from `bin/` directory
- ⏳ Elastic progress tracking not yet implemented (user will add C++ side)

## Pending Items for Next Session

1. **Add progress tracking for Elastic Moduli operations**
   - THAMES C++ needs to write `progress.json` during elastic calculations
   - Operations panel needs to parse elastic progress format

2. **Fix small glitches in 3D visualization functionality**
   - User reported minor issues to be investigated

## How to Resume

1. The elastic moduli calculation is now working for mixes without aggregate slabs
2. User mentioned wanting to add progress tracking for elastic operations
3. There are minor 3D visualization glitches to address
4. All executables should now be placed in the top-level `bin/` directory

## Key Code Patterns Established

### Executable Path Resolution Pattern:
```python
# Primary location: top-level bin/
exe_path = project_root / "bin" / exe_name

# Fallback locations
if not exe_path.exists():
    fallback = project_root / "backend" / "bin" / exe_name
    if fallback.exists():
        exe_path = fallback
```

### THAMES stdin Input Pattern:
```python
# Create input file
input_file = output_dir / "input.in"
with open(input_file, 'w') as f:
    f.write(f"{simulation_type}\n")
    f.write(f"{gem_input_file}\n")
    f.write(f"{simparams_file}\n")
    f.write(f"{microstructure_file}\n")

# Read for stdin
with open(input_file, 'r') as f:
    input_data = f.read()

# Launch with stdin redirection
start_real_process_operation(..., input_data=input_data)
```

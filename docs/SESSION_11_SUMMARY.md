# Session 11 Summary: Hydration Progress Tracking & Bug Fixes
**Date:** December 5, 2025

## Overview
This session focused on implementing hydration progress tracking on the Operations page and fixing several bugs in the microstructure generation and hydration simulation workflow.

## Problems Solved

### 1. Arcanite/Thenardite Case Mismatch Bug
**Symptom:** micgen.log showed 0 volume fractions for Arcanite/Thenardite despite non-zero surface fractions in the cement data.

**Root Cause:** In `micgen_input_service.py`, dictionary keys used lowercase `'arcanite'`/`'thenardite'` but the database stores capitalized names `'Arcanite'`/`'Thenardite'`.

**Fix:** Updated `_get_clinker_phase_fractions()` in `micgen_input_service.py`:
```python
'Arcanite': {
    'volume': 0.0,
    'surface': clinker_ext.k2so4_surface_fraction or 0.0
},
'Thenardite': {
    'volume': 0.0,
    'surface': clinker_ext.na2so4_surface_fraction or 0.0
}
```

### 2. phase_colors.json Remapping Bug
**Symptom:** After micgen phase ID remapping, the Results viewer showed wrong phase names (e.g., Arcanite/Thenardite for IDs 6/7 but actual phases were Anhydrite/Bassanite).

**Root Cause:** `_remap_phase_colors()` in `operations_monitoring_panel.py` treated the nested JSON structure as flat, not properly handling the separate dictionaries.

**Fix:** Rewrote to properly handle `phase_id_to_name`, `phase_id_to_color`, and `phase_name_to_color` keys:
```python
def _remap_phase_colors(self, colors_path: Path, old_to_new: Dict[int, int]) -> None:
    # Remap phase_id_to_name
    if 'phase_id_to_name' in colors_data:
        old_id_to_name = colors_data['phase_id_to_name']
        new_id_to_name = {}
        for old_id_str, name in old_id_to_name.items():
            old_id = int(old_id_str)
            if old_id in old_to_new:
                new_id = old_to_new[old_id]
                new_id_to_name[str(new_id)] = name
        colors_data['phase_id_to_name'] = new_id_to_name
    # Similarly for phase_id_to_color...
```

### 3. THAMES C++ progress.json Format
**Symptom:** Python couldn't parse progress.json due to malformed JSON.

**Root Cause:** THAMES C++ code (Controller.cc) wrote JSON without commas between key-value pairs:
```
json {"cycle": 10 "time_hours": 0.24 "timestamp": "..."}
```

**Fix:** User corrected Controller.cc to write proper JSON and added `target_time_hours`:
```cpp
progressFile << "{";
progressFile << "\"cycle\": " << cyc << ", ";
progressFile << "\"time_hours\": " << currTime << ", ";
progressFile << "\"target_time_hours\": " << (time_[timeSize - 1]) << ", ";
progressFile << "\"timestamp\": \"" << lgf::time_stamp() << "\"";
progressFile << "}";
```

### 4. Hydration Progress Not Showing on Operations Page
**Symptom:** Operations page showed "Hydration simulation in progress..." with 0% progress even though progress.json was updating.

**Root Cause:** Multiple issues:
1. `_update_hydration_progress()` was only called when `operation.is_process_running()` returned True
2. Operations loaded from database don't have process handles attached
3. Code looked in wrong directory (Result/ subdirectory instead of operation directory)

**Fix:**
1. Moved `_update_hydration_progress()` call before the process handle check
2. Fixed path to look in operation directory directly
3. Added auto-refresh of details panel in `_update_ui()`

### 5. "Simulation completed successfully!" Showing Immediately
**Symptom:** Hydration panel showed completion message immediately after clicking Run.

**Root Cause:** `start_simulation()` returns `(True, [])` when the process successfully *starts*, but the code treated this as simulation completion.

**Fix:**
1. Added `_on_simulation_started()` method to handle successful start
2. Completion now detected via `_poll_progress()` when `percent_complete >= 100`
3. Also checks if simulation is no longer in `active_simulations`

### 6. Progress Callback Signature Mismatch
**Symptom:** Error: `THAMESHydrationPanel._on_progress_update() takes 2 positional arguments but 3 were given`

**Root Cause:** Execution service calls `callback(operation_name, progress)` but panel method only accepted `(self, progress)`.

**Fix:** Changed signature in `thames_hydration_panel.py`:
```python
def _on_progress_update(self, operation_name: str, progress: Any) -> None:
```

## Files Modified

### Python Files
- `src/app/services/micgen_input_service.py` - Arcanite/Thenardite capitalization
- `src/app/windows/panels/operations_monitoring_panel.py`:
  - `_remap_phase_colors()` - Fixed nested JSON handling
  - `_update_hydration_progress()` - Simplified, reads from correct path
  - `_update_running_operations()` - Call hydration progress before process check
  - `_update_ui()` - Auto-refresh details panel
  - Completion detection logic
- `src/app/windows/panels/thames_hydration_panel.py`:
  - `_on_run_clicked()` - Don't call completion immediately
  - `_on_progress_update()` - Fixed signature
  - `_poll_progress()` - Detect actual completion
  - Added `_on_simulation_started()` method
- `src/app/ui/theme_manager.py` - Always-visible scrollbars CSS
- Multiple files - Added `set_can_focus(True)` for keyboard navigation

### C++ Files (User Modified)
- `backend/thames-hydration/src/thameslib/Controller.cc` - Fixed progress.json format

## Testing Results
- ✅ Microstructures generate correctly with all 6 clinker phases
- ✅ Hydration simulations run and complete successfully
- ✅ Progress tracking works on Operations page
- ✅ Progress bar and step message auto-update
- ✅ Hydration panel shows correct running/completed status

## Pending Issues for Next Session

### 1. Fix bug on attaching a kinetic model to a phase
User reported issue - needs investigation.

### 2. Fix 3D visualization of hydration time sequence on Results Tab
User reported issue - needs investigation.

## Key Code Patterns Learned

### Progress File Location
THAMES writes `progress.json` to the **operation directory** (e.g., `/Operations/HY-Cem116-04/progress.json`), NOT to the Result subdirectory.

### Operations Without Process Handles
Operations loaded from database don't have subprocess handles. Progress tracking must work by reading files directly, not relying on `operation.is_process_running()`.

### Simulation Start vs Complete
`start_simulation()` returns success when the process **starts**. Completion must be detected separately via:
- Polling progress percentage
- Checking if operation is no longer in `active_simulations`
- Reading progress.json `time_hours >= target_time_hours`

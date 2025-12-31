# Session 12: Hydration Results Visualization & Preferences UI

**Date:** December 6, 2025

## Overview

This session focused on completing the hydration results visualization system and implementing user-configurable kinetic defaults. Major accomplishments include fixing bugs in kinetic model attachment and 3D visualization, implementing a comprehensive Preferences UI for kinetic defaults, and adding time-series data plotting capabilities to the Results viewer.

## Key Accomplishments

### 1. Fixed Kinetic Model Attachment Bug

**Problem:** When assigning a kinetic model to a phase like Calcite (originally "Thermodynamic"), the kinetic model didn't appear in `simparams.json` even though it was saved in the UI.

**Root Cause:** In `kinetic_defaults_service.py`, the `get_kinetics_with_override()` method returned `None` for phases without built-in default kinetics, even when an override with a valid kinetic type was provided.

**Solution:** Modified `get_kinetics_with_override()` to create kinetics from scratch when:
- The phase has no default kinetics (`defaults is None`)
- The override includes a `type` field that isn't "Thermodynamic"

**File Modified:** `src/app/services/kinetic_defaults_service.py`

```python
def get_kinetics_with_override(self, phase_name: str, override: Dict[str, Any]) -> Optional[KineticParameters]:
    defaults = self.get_kinetics_for_phase(phase_name)
    if defaults is not None:
        return defaults.with_override(override)

    # Phase has NO default kinetics - check if override specifies a type
    kinetic_type = override.get('type')
    if kinetic_type and kinetic_type != 'Thermodynamic':
        # Use generic defaults as base, then apply override
        if kinetic_type == 'ParrotKilloh':
            generic_defaults = self.PARROT_KILLOH_DEFAULTS.get("Alite")
        elif kinetic_type == 'Standard':
            generic_defaults = self.STANDARD_DEFAULTS.get("Gypsum")
        elif kinetic_type == 'Pozzolanic':
            generic_defaults = self.POZZOLANIC_DEFAULTS.get("Quartz")
        else:
            return None
        if generic_defaults:
            return generic_defaults.with_override(override)
    return None
```

### 2. Fixed 3D Visualization Time Sequence Bug

**Problem:** The 3D visualization only showed the initial microstructure image, not the time steps from hydration simulation.

**Root Cause:** Multiple issues:
- Wrong search directory (operation root vs `Result/` subfolder)
- Wrong file pattern (expected `.img` before time vs THAMES format with `.img` at end)
- Wrong regex for time extraction

**Solution:** Updated `hydration_results_viewer.py` with correct THAMES file pattern:
```python
# THAMES time-series format: JobRoot.YYYyDDDdHHhMMm.TTTK.img
thames_time_pattern = re.compile(r'\.(\d+)y(\d+)d(\d+)h(\d+)m\.(\d+)K\.img$')
```

**Files Modified:** `src/app/windows/dialogs/hydration_results_viewer.py`

### 3. Implemented Preferences UI for Kinetic Defaults

Created a complete system for user-configurable kinetic defaults that persist across sessions.

#### Backend: KineticPreferencesService

**New File:** `src/app/services/kinetic_preferences_service.py` (~273 lines)

Features:
- Stores user preferences in JSON file at platform-specific location:
  - macOS: `~/Library/Application Support/THAMES/preferences/kinetic_defaults.json`
  - Windows: `%LOCALAPPDATA%\THAMES\preferences\kinetic_defaults.json`
  - Linux: `~/.local/share/THAMES/preferences/kinetic_defaults.json`
- CRUD operations for phase kinetic defaults
- Import/export functionality
- Singleton pattern with `get_kinetic_preferences_service()`

#### Backend Integration

**Modified:** `src/app/services/kinetic_defaults_service.py`
- Added check for user preferences before returning built-in defaults
- User preferences override built-in defaults when present

#### UI: Kinetic Defaults Tab in Preferences

**Modified:** `src/app/windows/dialogs/preferences_dialog.py`

Added `KineticDefaultsTab` class with:
- Searchable list of all 89 GEM phases (from PHNL list)
- Current kinetic type displayed for each phase
- "Edit Kinetics..." button opens `KineticModelEditorDialog`
- "Reset to Default" button removes user override
- "Export..." and "Import..." buttons for sharing configurations
- Real-time search/filter functionality

### 4. Implemented Hydration Output Visualization

Added comprehensive time-series data plotting to the Results viewer.

#### Tabbed Interface

**Modified:** `src/app/windows/dialogs/hydration_results_viewer.py` (major rewrite ~1700 lines total)

The dialog now uses a `Gtk.Notebook` with two tabs:
1. **"3D Visualization"** - Existing 3D microstructure evolution viewer
2. **"Data Plots"** - New time-series plotting for CSV output files

#### Data Plots Tab Features

**Data Categories** (CSV files from `Result/` directory):
- Phase Volumes (`*_Microstructure.csv`)
- Solution Chemistry (`*_Solution.csv`)
- Saturation Indices (`*_SI.csv`)
- Surface Areas (`*_SurfaceAreas.csv`)
- Enthalpy (`*_Enthalpy.csv`)

**Plot Controls:**
- Multi-select variable list with checkboxes
- Select All / Deselect All buttons
- Logarithmic X-axis checkbox
- Logarithmic Y-axis checkbox
- Line width spinner (0.5 - 5.0)
- Color scheme dropdown:
  - Tab10 (Default)
  - Set1
  - Dark2
  - Paired
  - Pastel1
  - Single Color
- Axis range controls (X min/max, Y min/max) - leave blank for auto

**Actions:**
- "Create Plot" button generates matplotlib plot
- "Export Plot" button saves to PNG, PDF, or SVG (300 DPI)

#### Key Methods Added

```python
def _create_data_plots_tab(self) -> None:
    """Create the time-series data plots tab with all controls."""

def _load_csv_files(self) -> None:
    """Load CSV files from Result/ subdirectory."""

def _on_data_file_changed(self, combo) -> None:
    """Handle data category selection change."""

def _load_csv_data(self, filepath: Path) -> None:
    """Load CSV and populate variables list."""

def _on_create_data_plot_clicked(self, button) -> None:
    """Create plot with selected variables and options."""

def _get_color_palette(self, scheme_name: str, num_colors: int) -> List:
    """Get color palette based on selected scheme."""

def _parse_range(self, min_entry, max_entry) -> Tuple[Optional[float], Optional[float]]:
    """Parse min/max range from entry widgets."""

def _on_export_data_plot_clicked(self, button) -> None:
    """Export plot to file."""
```

### 5. UI Improvements

#### Button Rename
**Modified:** `src/app/windows/panels/results_panel.py`
- Changed "View 3D Results" to "View Results"
- Updated description to "3D visualization and time-series data plots"

#### Dialog Sizing
**Modified:** `src/app/windows/dialogs/hydration_results_viewer.py`
- Reduced default size: 1100x750 → 1000x650
- Explicitly enabled resizing with `set_resizable(True)`
- Made controls panel scrollable for smaller screens
- Reduced variables list height: 250px → 150px
- Reduced 3D viewer frame height: 450px → 380px
- Tightened margins and spacing

## Files Created

| File | Lines | Description |
|------|-------|-------------|
| `src/app/services/kinetic_preferences_service.py` | ~273 | User preference storage for kinetic defaults |

## Files Modified

| File | Changes |
|------|---------|
| `src/app/services/kinetic_defaults_service.py` | Added user preference checking, fixed override handling |
| `src/app/windows/dialogs/preferences_dialog.py` | Added `KineticDefaultsTab` class |
| `src/app/windows/dialogs/hydration_results_viewer.py` | Complete rewrite with tabs, data plotting |
| `src/app/windows/panels/results_panel.py` | Button label and description update |

## Testing Status

- ✅ Kinetic model attachment for phases without defaults
- ✅ 3D visualization shows all time steps
- ✅ Preferences UI for kinetic defaults works
- ✅ Data plots tab displays and creates plots
- ✅ All plot options (log scale, ranges, colors, line width) work
- ✅ Export plot functionality works
- ✅ Dialog is resizable and fits on screen

## CSV Output Files Supported

| Display Name | File Pattern | Description |
|--------------|--------------|-------------|
| Phase Volumes | `*_Microstructure.csv` | Phase volume fractions over time |
| Solution Chemistry | `*_Solution.csv` | Aqueous species concentrations (68+ columns) |
| Saturation Indices | `*_SI.csv` | SI values for each phase |
| Surface Areas | `*_SurfaceAreas.csv` | Phase surface areas (m²/100g) |
| Enthalpy | `*_Enthalpy.csv` | System enthalpy (J/100g) |

## Architecture Notes

### Data Flow for Kinetic Preferences
1. User edits kinetic defaults in Preferences → Kinetic Defaults tab
2. `KineticPreferencesService` saves to JSON file
3. When loading kinetics for simulation, `KineticDefaultsService` checks user preferences first
4. User preferences override built-in defaults

### Data Flow for CSV Visualization
1. User opens Results viewer for hydration operation
2. `_load_microstructure_files()` sets `output_path` and calls `_load_csv_files()`
3. CSV files from `Result/` subdirectory are detected and added to dropdown
4. User selects category → `_load_csv_data()` parses CSV and populates variable list
5. User selects variables and options → `_on_create_data_plot_clicked()` creates matplotlib plot
6. Plot can be exported via `_on_export_data_plot_clicked()`

## Next Steps (for future sessions)

1. **Additional CSV file support** - Add more output file types as needed
2. **Plot templates** - Save/load plot configurations
3. **Multi-plot comparison** - Compare results from different simulations
4. **Data export** - Export selected data to new CSV files

## Critical Files for Next Session

- Kinetic Preferences: `src/app/services/kinetic_preferences_service.py`
- Kinetic Defaults: `src/app/services/kinetic_defaults_service.py`
- Preferences Dialog: `src/app/windows/dialogs/preferences_dialog.py`
- Results Viewer: `src/app/windows/dialogs/hydration_results_viewer.py`
- Results Panel: `src/app/windows/panels/results_panel.py`

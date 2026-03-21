# Session 34: Suppressed Phases, Time Unit Seconds & Carbonation Analysis

**Date:** March 20, 2026
**Platform:** macOS (Darwin 25.3.0)

## Overview

This session addressed three main areas: (1) adding seconds as a time unit throughout the Hydration panel, (2) implementing a suppressed phases mechanism to prevent GEMS from precipitating unchecked phases, and (3) analyzing carbonation simulation results to understand Portlandite dissolution and Calcite precipitation behavior.

## Changes Made

### 1. Seconds Time Unit in Hydration Panel

**Files:** `src/app/windows/panels/thames_hydration_panel.py`

- Added "seconds" (`"s"`) option to all 5 existing time unit dropdowns (final time, custom times, linear spacing, exponential t0, exact times)
- Added unit dropdown combos next to dt_initial and dt_max SpinButtons in Adaptive Time Stepping section
  - dt_initial: defaults to 3.6 seconds (= 0.001 hours), options: seconds/minutes/hours
  - dt_max: defaults to 4.0 hours, options: seconds/minutes/hours
  - SpinButton ranges, increments, and digits auto-adjust on unit change
- Added `_convert_to_hours()` helper and `_on_adaptive_dt_unit_changed()` callback
- Updated `_get_unit_from_combo_id()` to map `"s"` to `TimeUnit.SECONDS`
- `_build_config()` converts dt_initial/dt_max to hours before writing to simparams.json

### 2. Suppressed Phases Feature

**Problem:** When a user does not check a phase in the Hydration panel product list, that phase has no microstructure ID and cannot appear as voxels. However, GEMS was still free to precipitate it thermodynamically. In carbonation simulations, this caused Aragonite to form instead of Calcite.

**Solution:** Implemented a full pipeline to suppress unchecked GEMS phases:

#### Python Side
- **`hydration_input_service.py`**: After generating simparams.json, computes `suppressed_phases = all_GEMS_phases - active_GEMS_phases` (where active = phases in the microstructure section). Writes the list as a top-level `"suppressed_phases"` array in simparams.json.

#### C++ Side
- **`Controller.cc` (`parseDoc()`)**: Reads the `"suppressed_phases"` array. For each phase name, looks up its GEMS phase index via `getGEMPhaseId()`. Builds a complete phase-to-DC index mapping from the GEMS `nDCinPH` array (which gives the count of DCs per phase in sequential order). Registers each DC via `addSuppressedDC()` and sets `DCUpperLimit` to 0.0.
- **`ChemicalSystem.h`**: Added `suppressedDCIds_` (std::set<int>) member variable and `addSuppressedDC(int dcId)` method. Modified `initDCUpperLimit(double val)` to keep suppressed DCs at 0.0 instead of resetting to the given value.
- **`global.h`**: Added `#include <set>`.

#### Key Debugging Journey

1. **First attempt**: Used `GEMPhaseDCMembers_` map to look up DCs — crashed because this map only contains microstructure phases (3 entries), not all 100 GEMS phases.
2. **Second attempt**: Used `nDCinPH` array to compute DC indices — worked for the mapping, but all 97 suppressed phases were "skipped" because `getGEMPhaseId()` was returning valid indices yet they weren't in the DC members map.
3. **Third attempt**: Fixed the DC mapping using `nDCinPH`. Suppression count was correct (97 phases), but Aragonite still formed. Debug logging revealed `DCUpperLimit_[149] = 1e6` at GEMS call time despite being set to 0 in parseDoc.
4. **Root cause found**: `Controller::calculateState()` calls `chemSys_->initDCUpperLimit(1.0e6)` at the START of every cycle, wiping all upper limits back to 1e6.
5. **Final fix**: Added `suppressedDCIds_` set to persist suppression across cycles. `initDCUpperLimit()` now checks this set and keeps suppressed DCs at 0.0.

### 3. Empty Category Row Fix

**File:** `src/app/widgets/hydration_product_selector.py`

- Added check before adding category rows: if all products in a category are already microstructure phases, skip the category entirely
- Fixes the "CH" category appearing as an empty expandable row when Portlandite is already shown under "Microstructure Phases"

### 4. Submodule Branch Merge

- Merged `adaptive-timestepping` branch (12 commits, 16 files, +2236 lines) into `main` in the thames-hydration submodule
- The `adaptive-timestepping` branch had accumulated work from Sessions 24-32
- Fast-forward merge, no conflicts
- All future C++ work continues on `main`

## Carbonation Simulation Analysis

### Test Series: CarbPort / Bloop

| Operation | Configuration | Result |
|-----------|--------------|--------|
| CarbPort-03-bc100i | Fixed Na+=0.02, CO3²⁻=0.01 mol/kg | Aragonite formed instead of Calcite |
| CarbPort-03-bc1000j | First suppression attempt | Crashed: gas_gen not in DC members map |
| CarbPort-03-bc1000k | Fixed DC mapping | 0 phases suppressed (all skipped) |
| Bloop01 | Correct nDCinPH mapping | 97 suppressed but limits reset each cycle |
| Bloop02 | Debug: DCUpperLimit=1e6 at GEMS call | Confirmed initDCUpperLimit wipe |
| Bloop03 | Debug: verified correct DC index | Confirmed suppression code targets right DC |
| Bloop04 | Final fix: suppressedDCIds_ persistence | Aragonite=0, Calcite grows correctly |
| Bloop05 | max_relative_change=0.01 | Smooth solution chemistry, no oscillations |
| Bloop06 | Initial CO3²⁻=0.06 (not fixed) | Portlandite SI plateaus at ~0.01 |

### Key Findings

1. **Aqueous Ca complexation dominates**: In carbonate solutions, ~79% of dissolved Ca exists as Ca(CO3)@ complex, not free Ca²⁺. This suppresses the Portlandite ion activity product and keeps SI << 1.

2. **Fixed vs Initial concentration**: Fixed CO₃²⁻ continuously injects carbon into the system, which is unrealistic for most experiments. Initial CO₃²⁻ is consumed and gives more physical behavior.

3. **Operator-splitting oscillations**: The sequential kinetic-step → GEMS-equilibration architecture causes oscillations in aqueous speciation when driving forces are large. Reducing `max_relative_change` from 5% to 1% dampens these effectively.

4. **Portlandite thermodynamics in carbonate solutions**: Portlandite cannot approach saturation (SI → 1) in carbonate-rich solutions regardless of dissolution kinetics — this is correct physical behavior driven by Ca²⁺ complexation.

## Technical Details

### Phase-to-DC Mapping from nDCinPH

The GEMS DATACH structure stores `nDCinPH[nPH]` — the number of DCs in each phase. DCs are assigned sequentially:
- Phase 0 (Electrolyte): DCs 0..77 (78 DCs)
- Phase 1 (gas_gen): DCs 78..86 (9 DCs)
- Phase 2 (C3(AF)S0.84H): DCs 87..88 (2 DCs)
- ...
- Phase 51 (Aragonite): DC 149 (1 DC, name="Arg")
- Phase 52 (Calcite): DC 150 (1 DC, name="Cal")

This mapping is accessed via `chemSys_->getNode()->pCSD()->nDCinPH[ph]`.

### initDCUpperLimit Behavior

Before fix:
```cpp
void initDCUpperLimit(double val) {
    for (int i = 0; i < numDCs_; i++)
        DCUpperLimit_[i] = val;  // Resets ALL DCs to 1e6 every cycle
}
```

After fix:
```cpp
void initDCUpperLimit(double val) {
    for (int i = 0; i < numDCs_; i++) {
        if (suppressedDCIds_.count(i) > 0)
            DCUpperLimit_[i] = 0.0;  // Keep suppressed
        else
            DCUpperLimit_[i] = val;
    }
}
```

## How to Continue

### Running Carbonation Simulations
1. Select only the phases you want in the Hydration panel product list
2. All unchecked phases are automatically suppressed in GEMS
3. Use `max_relative_change` of 0.01 (1%) for smooth aqueous chemistry
4. Use "initial" (not "fixed") for electrolyte species unless modeling a continuously-replenished reservoir

### Potential Future Work
- Under-relaxation of kinetic dissolution increments to further reduce oscillations
- Sub-cycling between kinetics and GEMS equilibration within a single timestep
- UI indicator showing which phases are suppressed in the simulation log

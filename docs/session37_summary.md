# Session 37: Lattice Retry Limit, False Termination Fix, UI Race Condition & Glass Phase Names

**Date:** March 29-31, 2026
**Platform:** macOS (Darwin 25.4.0)

## Overview

This session addressed multiple simulation robustness issues: an infinite retry loop in lattice microstructure changes, a false early termination from the kinetics timestep floor, a UI race condition producing contradictory messages, and corrected glass phase naming in the GEMS database to prevent spurious precipitation.

## Changes Made

### 1. Lattice Retry Limit with Voxel Mismatch Logging

**Problem:** When `changeMicrostructure()` couldn't dissolve/grow the exact number of voxels GEMS requested (e.g., 71 OH-hydrotalcite voxels requested but only 70 interface sites available), the simulation entered an infinite retry loop. Observed in HY-OPC-FA-30 at cycle 3863 with 329,350+ retries consuming 100% CPU for hours.

**Fix:** Added `MAX_LATTICE_RETRIES = 50` limit to the `while (changeLattice == 0)` loop. When reached:
- Logs a warning to thames.log
- Appends detailed mismatch info to `voxel_mismatch.log` in the operation directory (phase ID, name, number of voxels that couldn't be changed)
- Accepts the current microstructure state and continues to the next cycle

**File:** `Controller.cc` (line ~1141 region)

### 2. False "FINAL TIME REACHED" Termination Fix

**Problem:** After adding the kinetics timestep floor (`stepTimeTHR_ = 1e-5 hours`), the floor value could still trigger the `timestep < 1e-12` termination check via a different path. HY-OPC-FA-30 terminated after 1 cycle because `computeKineticsBasedMaxTimestep()` returned 1.19e-13, which was floored to 1e-5, but on a subsequent check the unfloored value was used.

**Fix:** The termination check `timestep < 1e-12` now also requires `(initialLastTime - lastGoodTime_) < 1e-6` — ensuring the simulation is actually near its target time before declaring completion.

**File:** `Controller.cc` (line ~807 region)

### 3. UI Race Condition Fix — False FAILED/Success Messages

**Problem:** When launching a simulation, the user saw contradictory messages:
1. "Starting hydration simulation:..."
2. "Loaded phase mapping with 0 phases"
3. "Simulation FAILED:" / "Simulation ended unexpectedly"
4. "Simulation started successfully - monitoring progress..."

**Root Cause:** Progress polling (`GLib.timeout_add(1000, _poll_progress)`) started immediately when the run button was clicked, but the simulation launch ran in a background thread. The first poll (1 second later) checked `active_simulations` before the background thread had registered the simulation, triggering the "ended unexpectedly" path. The "started successfully" message arrived later when the background thread completed.

**Fix:** Moved progress polling from the run button handler into `_on_simulation_started()`, which only fires after the background thread confirms the simulation is running. Also increased initial poll delay to 2 seconds.

**File:** `thames_hydration_panel.py` (lines ~1598, ~1700)

### 4. Glass Phase Name Corrections (am suffix)

**Problem:** HY-OPC-FA-30 simulation had CA2S (fly ash glass) explosively precipitating from SI=217 to SI=3.6 billion, consuming 66% of the microstructure and triggering nucleation failure (735,344 sites requested, 1,446 available).

**Root Cause:** Comparison with a working simulation (`/Users/jwbullard/Software/tests/PC-FlyAsh-200/`) revealed the GEMS database had dropped the `(am)` (amorphous) suffix from five calcium alumino-silicate glass phases. Without `(am)`, GEMS treats them as crystalline phases which are thermodynamically much more stable, causing massive precipitation.

**Fix:** Updated `hydration_products_service.py` to use `(am)` suffix:
| Old name | New name |
|----------|----------|
| C2AS | C2AS(am) |
| CA2S | CA2S(am) |
| CAS | CAS(am) |
| CAS2 | CAS2(am) |
| K6A2S | K6A2S(am) |

User will separately update the GEMS database files (`thames-dch.dat` PHNL and DCNL sections).

**Additional finding:** CA and CA2 DC molar volumes (V0) are zero across all temperatures in the current database but have correct values in the working database. User needs to re-export from GEMS to fix this.

### 5. HY-OPC-FA-30 Diagnostic Analysis

Extensive analysis of the failing OPC + fly ash simulation:
- Identified IC recovery mechanism injecting 60,000 mol Al and 20,000 mol Si (from Mullite SI=2.4e23)
- Identified CA2S precipitation consuming 66% of microstructure
- Traced root cause to crystalline vs amorphous phase definitions in GEMS database
- The nucleation failure (735K requested, 1.4K available) was a downstream effect of CA2S consuming all available space

## Files Modified

### C++ (thames-hydration submodule):
- `src/thameslib/Controller.cc`:
  - MAX_LATTICE_RETRIES=50 with voxel_mismatch.log output
  - Kinetics timestep floor enforcement
  - False termination fix (proximity check)

### Python (main repo):
- `src/app/windows/panels/thames_hydration_panel.py`: Fixed race condition — moved progress polling to _on_simulation_started()
- `src/app/services/hydration_products_service.py`: Renamed 5 glass phases to use (am) suffix

## Technical Notes

### Voxel Mismatch Log Format
```
Cycle 3863, Time(h) 0.000950988, Retries 50
  Phase 25 (OH-hydrotalc): 1 voxels could not be changed
```

### Nucleation Failure Cascade
When a phase precipitates massively and consumes most electrolyte sites, subsequent phases that need to nucleate find no available sites. The `nucStopPrg` flag terminates the simulation, but the root cause is typically an upstream thermodynamic issue (wrong phase stability) rather than a microstructure geometry problem.

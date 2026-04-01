# Session 38: Post-Failure Kinetics Constraint Fix & Simulation Diagnostics

**Date:** March 31 - April 1, 2026
**Platform:** macOS (Darwin 25.4.0)

## Overview

This session diagnosed and fixed a critical bug where GEMS failure recovery bypassed the kinetics timestep constraint, causing massive timestep jumps that led to IC overshoot, spurious IC recovery injections, and explosive phase precipitation. Also investigated GEMS database issues with glass phase naming.

## Root Cause Analysis

### The Problem
Plain OPC hydration simulation (HydrationOf-ccr152-wc45) terminated after only 1.51 hours of a 28-day request. Portlandite tried to nucleate 5.96 million voxels (75% of microstructure) in a single step.

### The Chain of Events
1. Cycles 1-93: Kinetics constraint keeps timesteps at ~0.001h — stable operation
2. Cycle 94: GEMS fails (IPM solver error)
3. `adaptiveTimeController_->recordFailure()` returns ~1.0h (shrunk from dt_max=4.0h)
4. **Kinetics constraint NOT applied** on the failure recovery path
5. Cycle 95 runs with timestep=1.0h (1000x larger than kinetics-constrained steps)
6. Kinetic step computes dissolution for 1 full hour → massive overshoot
7. Ca IC goes to -1.53 mol (deeply negative)
8. IC recovery injects 1.53 mol Ca²⁺ + 3.07 mol OH⁻ (creating material from nothing)
9. Portlandite SI spikes to 206,538
10. GEMS requests 5.96M Portlandite voxels → nucleation failure → simulation stops

### Why Carbonation Simulations Were Unaffected
The carbonation simulations (Bloop series, CarbPort, Diss-Gyp) all ran with 100% GEMS success rate — the failure recovery path was never entered, so the missing constraint had no effect.

## Fix Applied

Added kinetics constraint to the GEMS failure recovery path in `Controller.cc`, matching the constraint already present on the success path:

```cpp
// After adaptiveTimeController_->recordFailure():
double kineticsMax = kineticController_->computeKineticsBasedMaxTimestep(maxRelativeChange_);
if (kineticsMax < stepTimeTHR_) {
    kineticsMax = stepTimeTHR_;
}
if (kineticsMax < timestep) {
    timestep = kineticsMax;
}
```

This ensures the post-failure timestep respects the same physics-based kinetics limit as successful cycles, preventing the massive overshoot.

## GEMS Database Investigation

### Glass Phase Names (continued from Session 37)
Confirmed that the `(am)` suffix issue (C2AS vs C2AS(am), etc.) is separate from the kinetics constraint bug. The plain OPC simulation had no glass phases — it failed purely from the missing kinetics constraint on the failure path.

### HY-OPC-FA-30 Analysis
The OPC + fly ash simulation had TWO compounding issues:
1. Missing kinetics constraint on failure path (fixed this session)
2. Glass phases without `(am)` suffix causing crystalline thermodynamic behavior (identified Session 37, user updating GEMS database)

## Files Modified

### C++ (thames-hydration submodule):
- `src/thameslib/Controller.cc`: Added kinetics constraint to GEMS failure recovery path (12 lines, lines 735-746)

## Windows Development Notes

The following changes from Sessions 34-38 will need attention when syncing to Windows:

### C++ Changes (require rebuild on Windows)
1. **Controller.cc** — Multiple changes:
   - Suppressed phases support (Session 34)
   - `initialLastTime` fix for early termination (Session 35)
   - Time vector bounds check (Session 36)
   - Kinetics timestep floor (Session 36)
   - False termination fix (Session 36)
   - Lattice retry limit with voxel_mismatch.log (Session 37)
   - Post-failure kinetics constraint (Session 38 — this session)
2. **ChemicalSystem.h** — `suppressedDCIds_` set, `addSuppressedDC()`, modified `initDCUpperLimit()` (Session 34)
3. **ChemicalSystem.cc** — Runtime concentration safety, removed debug prints (Session 32/34)
4. **global.h** — `#include <set>`, `IC_FLOOR` constant (Sessions 32/34)
5. **CMakeLists.txt** — macOS POST_BUILD codesign (Session 35) — this is inside `if(APPLE)` so won't affect Windows build

### Python Changes (cross-platform, no rebuild needed)
1. **thames_hydration_panel.py** — Seconds time units, adaptive dt unit combos, 4 decimal places, race condition fix
2. **hydration_input_service.py** — Suppressed phases computation
3. **hydration_product_selector.py** — Empty category row fix
4. **hydration_products_service.py** — Glass phase `(am)` suffix rename
5. **kinetic_model_editor.py** — 4 decimal places
6. **operations_monitoring_panel.py** — Concentration overrides notification

### Windows Build Reminders
- Working directory: `C:\Users\jwbullard\Desktop\foo\THAMES`
- Build with MSYS2 MinGW-w64 Clang: `cmake -G "MinGW Makefiles" -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ ..`
- The `codesign` POST_BUILD step is wrapped in `if(APPLE)` — no Windows impact
- `#include <set>` in global.h should work on all platforms
- `long int` vs `long long int` differences (Session 21) — already addressed

### Pre-Session Sync on Windows
Run `./pre-session-sync.sh` to pull all macOS changes before starting Windows development.

# Session 36: Time Vector Bounds Fix, Kinetics Timestep Floor & False Termination Fix

**Date:** March 28, 2026
**Platform:** macOS (Darwin 25.4.0)

## Overview

This session fixed three related bugs in the Controller simulation loop that were exposed by the Session 35 early-termination fix, and continued testing with carbonation and cement hydration simulations.

## Changes Made

### 1. Time Vector Out-of-Bounds Write Fix

**Problem:** After the Session 35 fix changed the main loop condition to use `initialLastTime`, the simulation could run far more cycles than the `time_` vector had entries. Line 679 (`time_[lastGoodI] = currTime`) wrote past the end of the vector — undefined behavior causing memory corruption. Observed in CarbPort-bc05-het where `lastGoodI` reached 370 but `time_.size()` was only 139.

**Fix:** Added bounds check: only write `time_[lastGoodI]` when `lastGoodI < time_.size()`.

**File:** `Controller.cc` (line 679 region)

### 2. Kinetics Timestep Floor

**Problem:** `computeKineticsBasedMaxTimestep()` could return absurdly small values (e.g., 1.19e-13 hours) when a kinetic phase had a very high rate relative to its DC moles. This made simulations either stuck (taking millions of tiny steps) or triggered false termination.

**Fix:** Enforce `stepTimeTHR_` (1e-5 hours = 0.036 seconds) as a floor for the kinetics constraint. The kinetics timestep can no longer go below this minimum.

**File:** `Controller.cc` (line 791 region)

### 3. False "FINAL TIME REACHED" Termination Fix

**Problem:** The termination check `if (timestep < 1e-12)` triggered when the kinetics constraint produced a tiny timestep, even though the simulation was nowhere near the target time. HY-OPC-FA-30 (28-day target) terminated after 1 cycle at 0.41 seconds because the kinetics constraint reduced the timestep to 1.19e-13.

**Fix:** Added additional condition: termination only triggers when `initialLastTime - lastGoodTime_ < 1e-6` (i.e., the simulation is actually near the target time).

**Before:**
```cpp
if (timestep < 1.0e-12) {
    // terminate
}
```

**After:**
```cpp
if (timestep < 1.0e-12 &&
    (initialLastTime - lastGoodTime_) < 1.0e-6) {
    // terminate
}
```

**File:** `Controller.cc` (line 806 region)

## Testing

| Operation | Issue | Result After Fix |
|-----------|-------|-----------------|
| CarbPort-bc05-het | Memory corruption from out-of-bounds time_ write | Fixed — simulation runs correctly |
| Diss-Gyp-LS100-smalltime | 30-second simulation completes correctly | Confirmed working |
| HY-OPC-FA-30 | False termination after 1 cycle (0.41 seconds of 28 days) | Fixed — simulation continues past first cycle |
| Multiple carbonation sims | Various tests | Running correctly |

## Discussion: Pre-flight Kinetics Validation

Discussed adding a pre-flight validation check in the UI to warn users when kinetic parameters would produce very small timesteps. Three options considered:

1. **Pre-flight validation** (recommended): Check kinetics before launch, show warning dialog with option to edit parameters
2. **Runtime warnings.json**: C++ writes warning file after first few cycles if estimated completion is unreasonable
3. **Estimated completion time**: Display ETA in Operations panel

Decision deferred to a future session.

## Files Modified

### C++ (thames-hydration submodule):
- `src/thameslib/Controller.cc`:
  - Bounds check on `time_[lastGoodI]` write
  - Kinetics timestep floor at `stepTimeTHR_`
  - False termination fix requiring proximity to target time

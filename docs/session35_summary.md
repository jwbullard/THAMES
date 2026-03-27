# Session 35: Early Termination Bug Fix, UI Decimal Places & macOS Signing

**Date:** March 27, 2026
**Platform:** macOS (Darwin 25.4.0)

## Overview

This session fixed a critical simulation early-termination bug, added decimal places to UI SpinButtons, resolved a macOS code signing issue after OS update, and continued carbonation simulation analysis from Session 34.

## Changes Made

### 1. Simulation Early Termination Bug Fix (Critical)

**Problem:** Simulations terminated far earlier than the requested final time. A 30-second simulation stopped at ~6 seconds; a 5-minute simulation stopped at ~2.1 minutes.

**Root Cause:** The `time_[]` vector in Controller.cc gets modified during the simulation loop. Line 677 overwrites `time_[lastGoodI] = currTime` each cycle, replacing original scheduled times with actual cycle times. Two termination conditions used `time_[timeSize - 1]` which eventually pointed to the current time rather than the original final time:
1. Main `while` loop condition (line 641)
2. Adaptive time stepping termination check (line 791)

**Fix:** Used `initialLastTime` (saved at line 632 before any modifications) instead of `time_[timeSize - 1]` in three locations:
- Line 641: Main loop condition
- Line 791: Adaptive termination check
- Line 657: Progress.json target_time_hours

**Files:** `Controller.cc` (3 lines changed)

### 2. UI Decimal Places (4 Decimal Places for Floating-Point Fields)

**Problem:** Floating-point SpinButtons in the Adaptive Time Stepping section and Kinetic Model Editor only showed 1-3 decimal places, insufficient for fine control.

**Fix:** Updated all floating-point SpinButtons to show 4 decimal places.

**Files:**
- `thames_hydration_panel.py`: 5 adaptive stepping fields (dt_initial, dt_max, growth_factor, shrink_factor, max_relative_change) + unit change defaults table
- `kinetic_model_editor.py`: All three kinetic model types (ParrotKilloh, Standard, Pozzolanic) in both the Hydration panel popup and Preferences dialog versions

**Fields updated:**
| Model | Fields changed to 4 digits |
|-------|---------------------------|
| Adaptive Stepping | dt_initial, dt_max, growth, shrink, max_change |
| ParrotKilloh | k1, k3, n1, n3, dorHcoeff |
| Standard | siexp, dfexp, dorexp |
| Pozzolanic | siexp, dfexp, dorexp, ohexp, sio2 |

Integer fields (dissolvedUnits, activationEnergy, successes, max_failures) and fields already at 4+ digits were left unchanged.

### 3. macOS Code Signing Fix

**Problem:** After updating macOS from 26.3 to 26.4, the `thames` binary crashed immediately (SIGKILL, exit code 137) before producing any output. Affected all simulations regardless of size or configuration.

**Root Cause:** macOS 26.4 tightened code signing requirements. Linker-signed ad-hoc binaries (automatically created during build) were being rejected by the OS.

**Fix:** Added automatic ad-hoc signing as a post-build step in CMakeLists.txt:
```cmake
if(APPLE)
  add_custom_command(TARGET thames POST_BUILD
    COMMAND codesign --force --sign - $<TARGET_FILE:thames>
    COMMENT "Ad-hoc signing thames binary for macOS"
  )
endif()
```

**Debugging journey:**
- Verified binary dependencies (otool -L) — all libraries present
- Tried rebuilding Xcode Command Line Tools — didn't help
- Manual `codesign --force --sign -` resolved the issue
- Added to CMakeLists.txt for automatic application

**Files:** `CMakeLists.txt` (added post-build signing step)

### 4. Gypsum Dissolution Simulation Analysis

Analyzed `Diss-Gyp-LS100-smalltime` operation:
- Gypsum (CaSO4·2H2O) dissolving in water with W/S=100
- Standard kinetics with k=1e-6 mol/m²/h
- Calcite present as thermodynamic (no kinetics)
- 97 phases suppressed via Session 34 feature
- After early-termination fix: full 30-second simulation runs correctly

## Files Modified

### C++ (thames-hydration submodule):
- `src/thameslib/Controller.cc`: Fixed 3 uses of `time_[timeSize-1]` → `initialLastTime`
- `CMakeLists.txt`: Added macOS post-build ad-hoc signing

### Python (main repo):
- `src/app/windows/panels/thames_hydration_panel.py`: 4 decimal places for adaptive stepping SpinButtons + unit change defaults
- `src/app/widgets/kinetic_model_editor.py`: 4 decimal places for all floating-point kinetic parameter fields

## Technical Notes

### time_ Vector Modification During Simulation

The `time_[]` vector is pre-built in `parseDoc()` with entries spanning 0 to finalTime. During the simulation loop, `time_[lastGoodI] = currTime` (line 677) replaces each entry with the actual cycle time. After N cycles (where N = timeSize), all entries are overwritten and `time_[timeSize-1]` equals the last cycle time, not the original final time.

`initialLastTime` (line 632) captures `time_[timeSize-1]` before any modifications and is the correct value for all termination and progress checks.

### macOS Code Signing

Starting with macOS 26.4, linker-signed binaries may be rejected. The `codesign --force --sign -` command creates an explicit ad-hoc signature that satisfies the OS requirements. The `-` means no developer identity is used. This is added as a POST_BUILD step so it runs automatically after every compilation.

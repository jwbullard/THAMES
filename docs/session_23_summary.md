# Session 23 Summary: Adaptive Time Stepping Analysis & Planning

**Date:** January 6, 2026
**Platform:** macOS (Darwin 25.2.0)

## Overview

This session focused on two main areas: (1) fixing build and UI bugs, and (2) conducting a deep analysis of the THAMES C++ backend to design an adaptive time stepping system. A comprehensive implementation plan was created for the adaptive time stepping feature.

## Key Accomplishments

### 1. Fixed GEMS3K Standalone Build Issues

**Problem:** The `install.sh` script failed with missing `png.h` files.

**Root Cause:** The GEMS3K CMakeLists.txt was incorrectly including thameslib files:
```cmake
file(GLOB HEADER_FILES *.h ../../thameslib/*.h)  # WRONG
```
This pulled in `PngWriter.h` which requires libpng.

**Solution:**
1. Removed thameslib references from GEMS3K CMakeLists.txt
2. Added platform auto-detection to `install.sh` using `uname -s`
3. Created `strainenergy_standalone.cpp` to provide the missing `strainenergy` extern symbol

### 2. Fixed Output Time Preview Bug

**Problem:** Setting Final Time = 1 minute with spacing = 0.01 minutes showed only "1 ms" instead of ~100 time points.

**Root Cause:** The `merge_times()` deduplication logic in `time_generator_service.py` used an absolute tolerance of 0.001 days (1.44 minutes) when comparing against time 0. This caused all small time points to be deduplicated as "duplicates" of 0.

**Solution:**
1. Changed deduplication to use 1-second absolute tolerance for small times
2. Added unit synchronization: spacing unit now automatically follows final time unit when changed

**Files Modified:**
- `src/app/services/time_generator_service.py`
- `src/app/windows/panels/thames_hydration_panel.py`

### 3. Deep Analysis of THAMES C++ Time Stepping

Conducted thorough analysis of time stepping code in `backend/thames-hydration/src/thameslib/`:

**Current Architecture:**
- Time steps pre-generated at startup with fixed linear increment (`testTime += 0.00006` hours)
- On GEMS failure: halve timestep, or random time sampling (up to 1000 tries)
- "GODZILLA" comments in code flag need for adaptive stepping

**Key Variables (Controller.h):**
| Variable | Purpose |
|----------|---------|
| `time_` | Pre-generated list of simulation times |
| `deltaTime_` | Used for failure recovery |
| `lastGoodTime_` | Last successfully completed time |
| `stepTimeTHR_` | Minimum threshold for halving (0.001 hours) |

**Kinetic Models:**
- `ParrotKillohModel` - Clinker phases (C3S, C2S, C3A, C4AF)
- `StandardKineticModel` - Generic phases using Dove-Crerar kinetics
- `PozzolanicModel` - Pozzolanic materials

### 4. Deep Analysis of GEMS3K Solver

Analyzed the GEMS3K source code to understand failure modes:

**Algorithm:** Interior Point Method (IPM-3)
- Minimizes Gibbs free energy under mass balance constraints
- Max 7000 IPM iterations, 130 FIA iterations
- Convergence criterion: Dikin's criterion (PCI ≤ DXM)

**Failure Modes:**
| Code | Type | Description |
|------|------|-------------|
| 2 | Max iterations | PCI still > DXM after 7000 iterations |
| 5 | Dual divergence | Chemical potentials oscillate |
| 1 | R Matrix singular | Phase composition rank-deficient |
| 4 | Mass balance broken | Recovery fails |
| 9 | Terminal error | Memory corruption, need restart |

**Key Insight:** GEMS has NO built-in step rejection. Failures must be handled by THAMES.

**Accessible Convergence Data:**
```cpp
GEM_Iterations(&precLoops, &fiaIter, &ipmIter)  // Iteration counts
CNode->NodeStatusCH                              // Success/failure enum
pmm->PCI                                         // Dikin criterion value
pmm->DXM                                         // Convergence threshold
```

### 5. Created Adaptive Time Stepping Implementation Plan

Comprehensive 700-line implementation plan at `docs/adaptive_timestepping_implementation_plan.md`.

**Architecture:**
- New `AdaptiveTimeController` class
- PI-like control based on GEMS iteration counts
- History tracking for smoothing
- Distinguishes stiffness failures from structural failures
- Optional kinetic-based prediction module

**Implementation Phases:**
| Phase | Description | Effort |
|-------|-------------|--------|
| 1 | Add GEMS accessors to ChemicalSystem | 1-2 hrs |
| 2 | Create AdaptiveTimeController class | 4-6 hrs |
| 3 | Integrate into Controller::doCycle() | 4-6 hrs |
| 4 | Optional kinetic prediction | 3-4 hrs |
| 5 | Configuration and polish | 2-3 hrs |

## Files Created

| File | Description |
|------|-------------|
| `docs/adaptive_timestepping_implementation_plan.md` | Comprehensive implementation plan (~700 lines) |
| `backend/.../strainenergy_standalone.cpp` | Provides strainenergy symbol for standalone GEMS3K |

## Files Modified

| File | Changes |
|------|---------|
| `backend/.../GEMS3K/CMakeLists.txt` | Removed thameslib references |
| `backend/.../install.sh` | Added platform auto-detection |
| `src/app/services/time_generator_service.py` | Fixed deduplication tolerance |
| `src/app/windows/panels/thames_hydration_panel.py` | Added unit sync for spacing |
| `CLAUDE.md` | Added Session 23 summary and Priority Tasks section |

## Technical Details

### Adaptive Time Controller Design

```cpp
class AdaptiveTimeController {
    // PI-like control parameters
    double growth_factor_ = 1.2;
    double shrink_factor_ = 0.5;
    long int target_iterations_ = 500;
    long int warning_iterations_ = 5000;

    // State tracking
    std::deque<long int> iteration_history_;
    int consecutive_successes_;
    int consecutive_failures_;

    // Main interface
    double getNextTimestep();
    void recordSuccess(long int iterDone, double pci, double dxm);
    double recordFailure(int errorCode);
};
```

### Adaptation Algorithm

1. **On Success:**
   - If iterations < 500 and 3+ consecutive successes: grow timestep by 1.2×
   - If iterations > 5000: shrink timestep by 0.7× (preemptive)
   - Otherwise: maintain current timestep

2. **On Failure:**
   - Code 2 or 5 (stiffness): shrink by 0.5×
   - Code 1, 3, 4 (structural): shrink by 0.25×
   - Clear iteration history, retry

3. **Bounds:** Always clamp to [dt_min, dt_max]

## Next Steps (Priority Order)

1. **Phase 1:** Add GEMS convergence accessors to ChemicalSystem
   - `getPCI()`, `getDXM()`, `getDetailedIterations()`

2. **Phase 2:** Create AdaptiveTimeController class
   - Header and implementation files
   - Add to CMakeLists.txt

3. **Phase 3:** Integrate into Controller::doCycle()
   - Replace fixed time stepping with adaptive
   - Keep legacy mode as fallback

4. **Lower Priority:** Create THAMES documentation and user guide

## Lessons Learned

1. **Time tolerance matters:** 0.001 days sounds small but is 1.44 minutes - too large for sub-minute simulations

2. **GEMS3K is a black box:** It either succeeds or fails, with no partial solutions or automatic retry

3. **Iteration count is a good proxy:** High iteration counts correlate with convergence difficulty, making them useful for adaptive control

4. **Cascading failures explained:** Random time sampling doesn't reduce the magnitude of chemical change, just picks different times - this is why failures cascade

## References

- Implementation plan: `docs/adaptive_timestepping_implementation_plan.md`
- GEMS3K node interface: `GEMS3K-standalone/GEMS3K/node.h`
- GEMS3K solver: `GEMS3K-standalone/GEMS3K/ipm_main.cpp`
- THAMES kinetic models: `thameslib/StandardKineticModel.cc`, `ParrotKillohModel.cc`, `PozzolanicModel.cc`

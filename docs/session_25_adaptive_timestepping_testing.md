# Session 25: Adaptive Time Stepping Testing & Kinetics-Based Initial Timestep

**Date:** January 13, 2026
**Platform:** macOS (Darwin 25.2.0)
**Duration:** ~2 hours

## Overview

This session focused on testing the adaptive time stepping implementation from Session 24, fixing GEMS solver failures encountered during testing, and implementing a physics-based initial timestep selection based on kinetic model rates.

## Test Results

### Result-Adaptive-01: Initial Test (Failed)

**Outcome:** Failed at ~12.9 simulated hours

**Error Type:** E04IPM - GEMS Mass Balance Refinement (MBR) errors

**Root Cause Analysis:**
- Near-zero IC (Independent Component) moles triggered precision issues
- ICTHRESH threshold (1.0e-9) was too tight for the accumulated numerical errors
- `checkICMoles()` was only being called on the first cycle

**Console Output Pattern:**
```
E04IPM: Mass balance broken in MBR() in node 0; IC: ...
```

### Result-Adaptive-02: SIA Mode Experiment (Failed)

**Hypothesis:** Using Smart Initial Approximation (SIA) for non-first cycles might improve convergence by starting from the previous solution.

**Changes Tested:**
1. Use `NEED_GEM_SIA` instead of `NEED_GEM_AIA` for non-first cycles
2. Call `GEM_run(isFirst)` instead of `GEM_run(true)`

**Outcome:** Failed much earlier at ~0.031 simulated hours

**Error Type:** E06IPM - IPM Main Descent failure

**Root Cause Analysis:**
- Large IC changes between cycles made the previous solution a poor starting point
- SIA assumes the previous solution is "close" to the new equilibrium
- In cement hydration, rapid phase changes violate this assumption

**Decision:** Reverted SIA changes, keeping AIA mode for all cycles

### Result-Adaptive-03: Successful Test (In Progress)

**Fixes Applied:**
1. Raised ICTHRESH from 1.0e-9 to 1.0e-8 in `global.h`
2. Call `checkICMoles()` every cycle (not just first cycle)
3. Kept AIA mode with `GEM_run(true)` for all cycles

**Status at Session End:**
| Metric | Value |
|--------|-------|
| Simulated Time | 47.6 hours (~2 days) |
| Target Time | 720 hours (30 days) |
| Progress | ~6.6% |
| Cycles Completed | ~248 |
| Degree of Hydration | 34.7% |
| GEMS Errors | None |

**Performance Observation:**
The adaptive approach is significantly slower than the random sampling approach. The conservative growth factor (1.2) and requirement for 3 consecutive successes before growing limits throughput. Future optimization should investigate:
- Increasing `growth_factor` to 1.5 or 2.0
- Reducing `successes_for_growth` from 3 to 2
- Relaxing `target_iterations` threshold

## Kinetics-Based Initial Timestep Implementation

### Problem Statement

The hard-coded initial timestep of 0.001 hours is not physics-based. It may be:
- Too large for fast-reacting systems (causing early failures)
- Too small for slow-reacting systems (wasting computation)

### Solution Design

Set the initial timestep to limit the relative change in any DC moles to a maximum percentage (default 5%) per timestep:

```
dt_initial = maxRelativeChange / maxRate
```

Where:
- `maxRelativeChange` = 0.05 (5%)
- `maxRate` = maximum dissolution rate across all kinetic models [1/hour]

### Implementation Details

#### 1. KineticModel Base Class (KineticModel.h)

Added virtual method with default implementation:
```cpp
virtual double estimateInitialDissolutionRate() const { return 0.0; }
double getInitScaledMass() const { return initScaledMass_; }
```

#### 2. ParrotKillohModel Implementation

Uses the Parrot-Killoh rate equations evaluated at DOR = 0.001:

```cpp
double ParrotKillohModel::estimateInitialDissolutionRate() const {
  const double DOR = 0.001;

  // Nucleation and growth rate
  double ngrate = (k1_ / n1_) * (1.0 - DOR) * pow((-log(1.0 - DOR)), (1.0 - n1_));
  ngrate *= ssaFactor_;

  // Hydration shell rate
  double hsrate = k3_ * pow((1.0 - DOR), n3_);

  // Early diffusion rate
  double diffrate = (k2_ * pow((1.0 - DOR), (2.0 / 3.0))) /
                    (1.0 - pow((1.0 - DOR), (1.0 / 3.0)));

  // Rate-limiting step (minimum)
  double rate = min(ngrate, min(hsrate, diffrate));

  // Apply corrections, convert per-day to per-hour
  rate *= (pfk_ * rhFactor_ * arrhenius_ / 24.0);
  return rate;
}
```

#### 3. StandardKineticModel Implementation

Uses the rate constant with conservative assumptions:
```cpp
double StandardKineticModel::estimateInitialDissolutionRate() const {
  double initMass = getInitScaledMass();
  if (initMass <= 0.0) return 0.0;

  // Assume mass fraction term is approximately 1.0 initially
  double rate = k_ * pow(initMass, n_);
  return rate;  // Already in per-hour
}
```

#### 4. PozzolanicModel Implementation

Similar to Standard model with OH- activity consideration:
```cpp
double PozzolanicModel::estimateInitialDissolutionRate() const {
  double initMass = getInitScaledMass();
  if (initMass <= 0.0) return 0.0;

  // Conservative estimate assuming moderate OH- activity
  double rate = k_ * pow(initMass, n_);
  return rate;
}
```

#### 5. KineticController Method

Scans all kinetic models and returns the maximum rate:
```cpp
double KineticController::getMaxInitialDissolutionRate() const {
  double maxRate = 0.0;
  for (int i = 0; i < pKMsize_; ++i) {
    if (phaseKineticModel_[i] != nullptr) {
      double rate = phaseKineticModel_[i]->estimateInitialDissolutionRate();
      if (rate > maxRate) {
        maxRate = rate;
      }
    }
  }
  return maxRate;
}
```

#### 6. AdaptiveTimeController Method

Computes the physics-based initial timestep:
```cpp
void AdaptiveTimeController::setInitialTimestepFromKinetics(
    double maxRate, double maxRelativeChange) {
  if (maxRate <= 0.0 || maxRelativeChange <= 0.0) {
    dt_current_ = clampTimestep(config_.dt_initial);
    return;
  }

  double dt_kinetic = maxRelativeChange / maxRate;
  dt_current_ = clampTimestep(dt_kinetic);
  config_.dt_initial = dt_current_;  // Update for reset()
}
```

#### 7. Controller Integration

Called in Controller constructor after kinetic models are loaded:
```cpp
double maxKineticRate = kc->getMaxInitialDissolutionRate();
if (maxKineticRate > 0.0) {
  adaptiveTimeController_->setInitialTimestepFromKinetics(maxKineticRate, 0.05);
  std::clog << "Controller: Initial timestep set from kinetics, maxRate="
            << maxKineticRate << " 1/h, dt_initial="
            << adaptiveTimeController_->getCurrentTimestep() << " h" << endl;
}
```

## Microstructure Consistency Check Verification

Confirmed that the existing microstructure consistency check (pre-dating adaptive time stepping) is still functional. Located in `Controller.cc` lines 1015-1290:

1. `lattice_->changeMicrostructure()` attempts to implement GEMS-calculated phase changes
2. If it returns 0, some voxels couldn't be dissolved due to lattice topology
3. System resets to initial state (`iniLattice`)
4. Lower limits set on DCs based on `numSitesNotAvailable`
5. GEMS re-runs with these constraints
6. Loop repeats until success or GEMS failure

**Key Distinction:**
- Adaptive time stepping: Handles GEMS solver failures → reduces timestep
- Microstructure consistency: Handles lattice implementation failures → constrains GEMS

Both mechanisms work together for robust simulation.

## Files Modified

### GEMS Stability Fixes
| File | Change |
|------|--------|
| `global.h` | ICTHRESH: 1.0e-9 → 1.0e-8 |
| `ChemicalSystem.cc` | checkICMoles() called every cycle |

### Kinetics-Based Initial Timestep
| File | Lines Added |
|------|-------------|
| `KineticModel.h` | +5 |
| `ParrotKillohModel.h` | +1 |
| `ParrotKillohModel.cc` | +45 |
| `StandardKineticModel.h` | +1 |
| `StandardKineticModel.cc` | +30 |
| `PozzolanicModel.h` | +1 |
| `PozzolanicModel.cc` | +35 |
| `KineticController.h` | +1 |
| `KineticController.cc` | +15 |
| `AdaptiveTimeController.h` | +5 |
| `AdaptiveTimeController.cc` | +30 |
| `Controller.cc` | +10 |

**Total:** ~180 lines added

## Next Steps

1. **Monitor Result-Adaptive-03**: Wait for 30-day simulation to complete
2. **Performance Tuning**: If test passes, experiment with:
   - `growth_factor`: 1.2 → 1.5 or 2.0
   - `successes_for_growth`: 3 → 2
   - `target_iterations`: 500 → 1000
3. **Configuration**: Add adaptive time stepping parameters to `simparams.json`
4. **Merge to Main**: Once testing confirms stability

## Technical Notes

### GEMS Error Codes Reference
| Code | Name | Meaning |
|------|------|---------|
| E04IPM | MBR Error | Mass Balance Refinement failed |
| E06IPM | Main Descent | IPM main descent algorithm failed |
| 4 | ERR_GEM_AIA | Failure with Automatic Initial Approximation |
| 8 | ERR_GEM_SIA | Failure with Smart Initial Approximation |
| 9 | T_ERROR_GEM | Terminal error |

### Why AIA Works Better Than SIA for Cement Hydration

SIA (Smart Initial Approximation) uses the previous equilibrium solution as the starting point for the next calculation. This works well when:
- Changes between steps are small
- The system evolves gradually

In cement hydration:
- Phase changes can be dramatic (dissolution, precipitation)
- IC moles change significantly each cycle
- The previous equilibrium may be far from the new one

AIA (Automatic Initial Approximation) builds a fresh starting point based on current constraints, avoiding the assumption that the previous solution is "close."

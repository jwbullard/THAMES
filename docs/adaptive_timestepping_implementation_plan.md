# THAMES Adaptive Time Stepping Implementation Plan

**Document Version:** 1.0
**Date:** January 6, 2026
**Authors:** Jeffrey W. Bullard, Claude (Anthropic)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Architecture](#3-solution-architecture)
4. [Implementation Phases](#4-implementation-phases)
5. [Detailed Component Specifications](#5-detailed-component-specifications)
6. [File Changes Summary](#6-file-changes-summary)
7. [Testing Strategy](#7-testing-strategy)
8. [Configuration and Tuning](#8-configuration-and-tuning)
9. [Risk Assessment](#9-risk-assessment)
10. [Future Enhancements](#10-future-enhancements)

---

## 1. Executive Summary

### Goal
Implement intelligent adaptive time stepping in THAMES to:
- Reduce GEMS solver failures by proactively adjusting timestep size
- Improve simulation efficiency by using larger timesteps when the system is stable
- Eliminate cascading failure loops caused by random time sampling
- Provide diagnostic information about solver performance

### Approach
A two-pronged strategy combining:
1. **Reactive adaptation:** Adjust timestep based on GEMS solver feedback (iteration counts, convergence metrics)
2. **Predictive constraint:** Optionally limit DC changes per step to reduce failure probability

### Key Innovation
Leverage previously unused GEMS3K convergence data (`iterDone`, `PCI`, `DXM`) to make informed timestep decisions rather than relying on random trial-and-error.

---

## 2. Problem Statement

### Current Behavior

The existing THAMES time stepping has several issues:

1. **Fixed Linear Time Steps:** Generated at startup with constant increment (`testTime += 0.00006` hours)

2. **Reactive-Only Failure Handling:**
   - When GEMS fails, timestep is halved
   - If still failing, random times are sampled in an interval
   - Up to 1000 random attempts before giving up

3. **No Proactive Adjustment:**
   - Timestep size doesn't adapt to simulation state
   - No feedback from GEMS convergence difficulty
   - Early hydration (fast kinetics) uses same timestep as late hydration (slow kinetics)

4. **Cascading Failures:**
   - One GEMS failure often leads to many more
   - Random sampling doesn't systematically reduce the "magnitude" of change
   - Simulations can get stuck for thousands of iterations

### Root Cause Analysis

GEMS3K failures occur when:
- DC mole changes are too large for the solver to find a new equilibrium
- System crosses phase boundaries (assemblage changes)
- Numerical precision issues with very small/large DC amounts

The current random time sampling doesn't address the fundamental issue: **the magnitude of chemical change requested is too large for GEMS to handle**.

---

## 3. Solution Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Controller::doCycle()                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AdaptiveTimeController                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────────┐   │
│  │ State Tracking  │  │ Decision Logic   │  │ History Management      │   │
│  │ - dt_current    │  │ - getNextStep()  │  │ - iteration_history     │   │
│  │ - consecutives  │  │ - recordSuccess()│  │ - pci_history           │   │
│  │ - last_pci      │  │ - recordFailure()│  │ - moving averages       │   │
│  └─────────────────┘  └──────────────────┘  └─────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              Optional: Kinetic Prediction Module                     │   │
│  │  - Estimate DC changes for proposed timestep                         │   │
│  │  - Constrain timestep to limit max DC change to X%                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
            │  Kinetic    │    │  Chemical   │    │   GEMS3K    │
            │ Controller  │    │   System    │    │   Solver    │
            │             │◄───│             │◄───│             │
            │ (rates)     │    │ (interface) │    │ (equilib.)  │
            └─────────────┘    └─────────────┘    └─────────────┘
```

### Data Flow

```
1. AdaptiveTimeController proposes timestep (dt)
       │
       ▼
2. [Optional] Kinetic prediction constrains dt based on max DC change
       │
       ▼
3. KineticController calculates DC mole changes for dt
       │
       ▼
4. ChemicalSystem passes changes to GEMS via GEM_from_MT
       │
       ▼
5. GEMS3K attempts equilibrium calculation (GEM_run)
       │
       ├──► SUCCESS: Extract iterDone, PCI, DXM
       │              AdaptiveTimeController::recordSuccess()
       │              Advance simulation time
       │
       └──► FAILURE: Extract error code
                     AdaptiveTimeController::recordFailure()
                     Restore state, retry with smaller dt
```

---

## 4. Implementation Phases

### Phase 1: Infrastructure (Foundation)
**Goal:** Expose GEMS convergence data to THAMES

| Task | File | Description |
|------|------|-------------|
| 1.1 | ChemicalSystem.h | Add accessor methods for PCI, DXM, detailed iterations |
| 1.2 | ChemicalSystem.cc | Implement accessor methods |
| 1.3 | ChemicalSystem.cc | Add diagnostic logging for convergence metrics |

**Estimated effort:** 1-2 hours
**Risk:** Low (additive changes only)

### Phase 2: Core Controller (Main Feature)
**Goal:** Implement AdaptiveTimeController class

| Task | File | Description |
|------|------|-------------|
| 2.1 | AdaptiveTimeController.h | Create new header with class definition |
| 2.2 | AdaptiveTimeController.cc | Implement core logic |
| 2.3 | CMakeLists.txt | Add new source files to build |

**Estimated effort:** 4-6 hours
**Risk:** Medium (new code, needs testing)

### Phase 3: Integration (Connect the Pieces)
**Goal:** Integrate AdaptiveTimeController into simulation loop

| Task | File | Description |
|------|------|-------------|
| 3.1 | Controller.h | Add AdaptiveTimeController member |
| 3.2 | Controller.cc | Modify doCycle() to use adaptive stepping |
| 3.3 | Controller.cc | Remove or modify existing random sampling logic |
| 3.4 | Controller.cc | Add state save/restore for retry mechanism |

**Estimated effort:** 4-6 hours
**Risk:** High (modifies critical simulation loop)

### Phase 4: Kinetic Prediction (Optional Enhancement)
**Goal:** Add predictive timestep constraint based on kinetic rates

| Task | File | Description |
|------|------|-------------|
| 4.1 | KineticController.h | Add method to estimate rates without modifying state |
| 4.2 | KineticController.cc | Implement rate estimation |
| 4.3 | AdaptiveTimeController | Add prediction module |

**Estimated effort:** 3-4 hours
**Risk:** Medium (requires careful state management)

### Phase 5: Configuration & Polish
**Goal:** Make the system configurable and production-ready

| Task | File | Description |
|------|------|-------------|
| 5.1 | simparams.json schema | Add adaptive stepping parameters |
| 5.2 | Controller.cc | Parse new parameters from JSON |
| 5.3 | Various | Add comprehensive logging |
| 5.4 | Documentation | Update user guide |

**Estimated effort:** 2-3 hours
**Risk:** Low

---

## 5. Detailed Component Specifications

### 5.1 ChemicalSystem Accessor Methods

**File:** `ChemicalSystem.h`

```cpp
// Add to public section of ChemicalSystem class (around line 5660)

/**
 * @brief Get the Dikin criterion (PCI) from last GEMS calculation.
 *
 * PCI measures how close the IPM algorithm is to convergence.
 * Lower values indicate better convergence. When PCI < DXM,
 * the solver has converged.
 *
 * @return Current PCI value from GEMS IPM solver
 */
double getPCI() const;

/**
 * @brief Get the convergence threshold (DXM) used by GEMS.
 *
 * This is the target value for the Dikin criterion.
 * Default is typically 1e-5 to 1e-6.
 *
 * @return Convergence threshold DXM
 */
double getDXM() const;

/**
 * @brief Get detailed iteration counts from last GEMS calculation.
 *
 * Provides breakdown of iterations in different solver phases:
 * - precLoops: Precision refinement loops
 * - fiaIter: Feasible Initial Approximation iterations (max 130)
 * - ipmIter: Interior Point Method main iterations (max 7000)
 *
 * @param[out] precLoops Number of precision loops performed
 * @param[out] fiaIter Number of FIA/EFD iterations
 * @param[out] ipmIter Number of IPM descent iterations
 * @return Total iterations (fiaIter + ipmIter)
 */
long int getDetailedIterations(long int& precLoops,
                                long int& fiaIter,
                                long int& ipmIter) const;

/**
 * @brief Get the ratio of PCI to DXM as a convergence quality metric.
 *
 * Returns PCI/DXM ratio:
 * - < 1.0: Converged (good)
 * - 1-10: Marginal convergence
 * - 10-100: Poor convergence (solver struggled)
 * - > 100: Near failure
 *
 * @return PCI/DXM ratio, or -1 if DXM is zero
 */
double getConvergenceRatio() const;
```

**File:** `ChemicalSystem.cc`

```cpp
// Add implementations (after line 3200 or in appropriate section)

double ChemicalSystem::getPCI() const {
    if (node_ && node_->pMulti()) {
        return node_->pMulti()->GetPM()->PCI;
    }
    return -1.0;  // Invalid/unavailable
}

double ChemicalSystem::getDXM() const {
    if (node_ && node_->pMulti()) {
        return node_->pMulti()->GetPM()->DXM;
    }
    return -1.0;  // Invalid/unavailable
}

long int ChemicalSystem::getDetailedIterations(long int& precLoops,
                                                long int& fiaIter,
                                                long int& ipmIter) const {
    if (node_) {
        return node_->GEM_Iterations(precLoops, fiaIter, ipmIter);
    }
    precLoops = fiaIter = ipmIter = 0;
    return 0;
}

double ChemicalSystem::getConvergenceRatio() const {
    double dxm = getDXM();
    if (dxm <= 0.0) return -1.0;
    return getPCI() / dxm;
}
```

---

### 5.2 AdaptiveTimeController Class

**File:** `AdaptiveTimeController.h` (NEW FILE)

```cpp
/**
 * @file AdaptiveTimeController.h
 * @brief Adaptive time stepping controller for THAMES hydration simulations.
 *
 * This controller adjusts simulation timestep based on GEMS solver feedback
 * to minimize failures while maximizing efficiency.
 *
 * Key features:
 * - PI-like control based on iteration counts
 * - Smoothing via moving average of recent history
 * - Distinguishes stiffness failures from structural failures
 * - Optional kinetic-based prediction for proactive constraint
 */

#ifndef ADAPTIVETIMECONTROLLER_H
#define ADAPTIVETIMECONTROLLER_H

#include <deque>
#include <vector>
#include <string>

class KineticController;  // Forward declaration

/**
 * @brief GEMS solver result codes for adaptive stepping decisions.
 */
enum class GEMSResultType {
    SUCCESS_EASY,      ///< Converged quickly (iterations < target)
    SUCCESS_NORMAL,    ///< Converged normally
    SUCCESS_HARD,      ///< Converged but struggled (iterations > warning threshold)
    FAILURE_STIFFNESS, ///< Failed due to stiffness (codes 2, 5)
    FAILURE_STRUCTURAL,///< Failed due to structural issues (codes 1, 3, 4)
    FAILURE_TERMINAL   ///< Terminal error (code 9)
};

/**
 * @brief Configuration parameters for adaptive time stepping.
 */
struct AdaptiveTimeConfig {
    // Timestep bounds (hours)
    double dt_min = 1.0e-6;       ///< Minimum timestep (~3.6 ms)
    double dt_max = 1.0;          ///< Maximum timestep (1 hour)
    double dt_initial = 0.001;    ///< Initial timestep

    // PI controller parameters
    double growth_factor = 1.2;   ///< Multiply dt by this on easy success
    double shrink_factor = 0.5;   ///< Multiply dt by this on failure
    double hard_shrink_factor = 0.7; ///< Multiply dt on hard success

    // Iteration thresholds
    long int target_iterations = 500;    ///< "Easy" convergence threshold
    long int warning_iterations = 5000;  ///< "Struggling" threshold

    // Consecutive success requirement for growth
    int successes_for_growth = 3;

    // History size for moving average
    int history_size = 5;

    // Optional kinetic prediction
    bool use_kinetic_prediction = false;
    double max_dc_change_fraction = 0.05; ///< Max 5% change per step
    double mass_threshold = 1.0e-6;       ///< Skip phases below this mass

    // Logging
    bool verbose = false;
};

/**
 * @brief Adaptive time stepping controller.
 */
class AdaptiveTimeController {

public:
    /**
     * @brief Construct with configuration.
     * @param config Configuration parameters
     */
    explicit AdaptiveTimeController(const AdaptiveTimeConfig& config = AdaptiveTimeConfig());

    /**
     * @brief Destructor.
     */
    ~AdaptiveTimeController() = default;

    // =========================================================================
    // Main Interface
    // =========================================================================

    /**
     * @brief Get the next proposed timestep.
     *
     * Returns the current adaptive timestep, which has been adjusted
     * based on recent solver performance.
     *
     * @return Proposed timestep in hours
     */
    double getNextTimestep() const;

    /**
     * @brief Record a successful GEMS calculation.
     *
     * Updates internal state based on how hard GEMS worked to converge.
     * May adjust future timesteps proactively.
     *
     * @param iterDone Total iterations performed
     * @param pci Dikin criterion value at convergence
     * @param dxm Convergence threshold used
     */
    void recordSuccess(long int iterDone, double pci, double dxm);

    /**
     * @brief Record a failed GEMS calculation.
     *
     * Shrinks timestep based on failure type. Stiffness failures
     * (codes 2, 5) result in moderate reduction; structural failures
     * result in aggressive reduction.
     *
     * @param gemsErrorCode GEMS NodeStatusCH error code
     * @return New timestep to use for retry
     */
    double recordFailure(int gemsErrorCode);

    /**
     * @brief Reset controller state.
     *
     * Clears history and resets timestep to initial value.
     * Call this when starting a new simulation or after major state changes.
     */
    void reset();

    // =========================================================================
    // Optional Kinetic Prediction
    // =========================================================================

    /**
     * @brief Predict a safe timestep based on kinetic rates.
     *
     * Estimates the timestep that would limit the maximum DC change
     * to the configured fraction. This is a PREDICTION that does not
     * modify any state.
     *
     * @param kineticController Pointer to kinetic controller
     * @param proposedDt The timestep being considered
     * @return Constrained timestep (may be smaller than proposedDt)
     */
    double predictSafeTimestep(KineticController* kineticController,
                               double proposedDt) const;

    // =========================================================================
    // Diagnostics
    // =========================================================================

    /**
     * @brief Get current controller state as string for logging.
     * @return Diagnostic string
     */
    std::string getStatusString() const;

    /**
     * @brief Get statistics about recent performance.
     * @param[out] avgIterations Average iterations over recent history
     * @param[out] successRate Success rate over recent attempts
     * @param[out] avgTimestep Average timestep used
     */
    void getStatistics(double& avgIterations,
                       double& successRate,
                       double& avgTimestep) const;

    // =========================================================================
    // Configuration
    // =========================================================================

    /**
     * @brief Update configuration parameters.
     * @param config New configuration
     */
    void setConfig(const AdaptiveTimeConfig& config);

    /**
     * @brief Get current configuration.
     * @return Current configuration
     */
    const AdaptiveTimeConfig& getConfig() const { return config_; }

    /**
     * @brief Set minimum timestep bound.
     * @param dt_min Minimum timestep in hours
     */
    void setMinTimestep(double dt_min) { config_.dt_min = dt_min; }

    /**
     * @brief Set maximum timestep bound.
     * @param dt_max Maximum timestep in hours
     */
    void setMaxTimestep(double dt_max) { config_.dt_max = dt_max; }

private:
    // Configuration
    AdaptiveTimeConfig config_;

    // Current state
    double dt_current_;
    int consecutive_successes_;
    int consecutive_failures_;
    double last_pci_;
    double last_dxm_;

    // History tracking
    std::deque<long int> iteration_history_;
    std::deque<double> timestep_history_;
    std::deque<bool> success_history_;

    // Statistics
    long int total_successes_;
    long int total_failures_;
    long int total_steps_;

    // Helper methods
    GEMSResultType classifyResult(long int iterDone, int errorCode) const;
    double computeMovingAverage() const;
    void updateHistory(long int iterations, double timestep, bool success);
    void adjustTimestepOnSuccess(GEMSResultType resultType);
    void adjustTimestepOnFailure(GEMSResultType resultType);
    double clampTimestep(double dt) const;
};

#endif // ADAPTIVETIMECONTROLLER_H
```

**File:** `AdaptiveTimeController.cc` (NEW FILE)

```cpp
/**
 * @file AdaptiveTimeController.cc
 * @brief Implementation of adaptive time stepping controller.
 */

#include "AdaptiveTimeController.h"
#include "KineticController.h"
#include <algorithm>
#include <numeric>
#include <sstream>
#include <iomanip>
#include <cmath>
#include <iostream>

AdaptiveTimeController::AdaptiveTimeController(const AdaptiveTimeConfig& config)
    : config_(config)
    , dt_current_(config.dt_initial)
    , consecutive_successes_(0)
    , consecutive_failures_(0)
    , last_pci_(0.0)
    , last_dxm_(1.0e-5)
    , total_successes_(0)
    , total_failures_(0)
    , total_steps_(0)
{
}

double AdaptiveTimeController::getNextTimestep() const {
    return dt_current_;
}

void AdaptiveTimeController::recordSuccess(long int iterDone, double pci, double dxm) {
    total_successes_++;
    total_steps_++;
    consecutive_failures_ = 0;
    consecutive_successes_++;
    last_pci_ = pci;
    last_dxm_ = dxm;

    // Update history
    updateHistory(iterDone, dt_current_, true);

    // Classify result and adjust
    GEMSResultType result = classifyResult(iterDone, 0);
    adjustTimestepOnSuccess(result);

    if (config_.verbose) {
        std::clog << "AdaptiveTime: SUCCESS iter=" << iterDone
                  << " pci=" << pci << " dt=" << dt_current_ << std::endl;
    }
}

double AdaptiveTimeController::recordFailure(int gemsErrorCode) {
    total_failures_++;
    total_steps_++;
    consecutive_successes_ = 0;
    consecutive_failures_++;

    // Update history
    updateHistory(0, dt_current_, false);

    // Classify and adjust
    GEMSResultType result = classifyResult(0, gemsErrorCode);
    adjustTimestepOnFailure(result);

    if (config_.verbose) {
        std::clog << "AdaptiveTime: FAILURE code=" << gemsErrorCode
                  << " new_dt=" << dt_current_ << std::endl;
    }

    return dt_current_;
}

void AdaptiveTimeController::reset() {
    dt_current_ = config_.dt_initial;
    consecutive_successes_ = 0;
    consecutive_failures_ = 0;
    last_pci_ = 0.0;
    last_dxm_ = 1.0e-5;
    iteration_history_.clear();
    timestep_history_.clear();
    success_history_.clear();
    // Don't reset totals - they track lifetime statistics
}

GEMSResultType AdaptiveTimeController::classifyResult(long int iterDone,
                                                       int errorCode) const {
    if (errorCode == 0) {
        // Success - classify by difficulty
        if (iterDone < config_.target_iterations) {
            return GEMSResultType::SUCCESS_EASY;
        } else if (iterDone < config_.warning_iterations) {
            return GEMSResultType::SUCCESS_NORMAL;
        } else {
            return GEMSResultType::SUCCESS_HARD;
        }
    } else {
        // Failure - classify by type
        // Error codes: 2=max iterations, 5=dual divergence (stiffness-related)
        //              1=singular matrix, 3=activity coeff, 4=mass balance (structural)
        //              9=terminal error
        if (errorCode == 9) {
            return GEMSResultType::FAILURE_TERMINAL;
        } else if (errorCode == 2 || errorCode == 5 ||
                   errorCode == 4 || errorCode == 8) {
            // ERR_GEM_AIA=4, ERR_GEM_SIA=8 are failure codes
            return GEMSResultType::FAILURE_STIFFNESS;
        } else {
            return GEMSResultType::FAILURE_STRUCTURAL;
        }
    }
}

double AdaptiveTimeController::computeMovingAverage() const {
    if (iteration_history_.empty()) return 0.0;

    double sum = std::accumulate(iteration_history_.begin(),
                                  iteration_history_.end(), 0.0);
    return sum / iteration_history_.size();
}

void AdaptiveTimeController::updateHistory(long int iterations,
                                            double timestep,
                                            bool success) {
    iteration_history_.push_back(iterations);
    timestep_history_.push_back(timestep);
    success_history_.push_back(success);

    // Maintain fixed history size
    while (iteration_history_.size() > static_cast<size_t>(config_.history_size)) {
        iteration_history_.pop_front();
    }
    while (timestep_history_.size() > static_cast<size_t>(config_.history_size)) {
        timestep_history_.pop_front();
    }
    while (success_history_.size() > static_cast<size_t>(config_.history_size * 2)) {
        success_history_.pop_front();
    }
}

void AdaptiveTimeController::adjustTimestepOnSuccess(GEMSResultType resultType) {
    switch (resultType) {
        case GEMSResultType::SUCCESS_EASY:
            // GEMS found it easy - consider growing timestep
            if (consecutive_successes_ >= config_.successes_for_growth) {
                dt_current_ *= config_.growth_factor;
            }
            break;

        case GEMSResultType::SUCCESS_NORMAL:
            // Normal convergence - maintain current timestep
            break;

        case GEMSResultType::SUCCESS_HARD:
            // GEMS struggled - preemptively reduce timestep
            dt_current_ *= config_.hard_shrink_factor;
            consecutive_successes_ = 0;  // Reset growth counter
            break;

        default:
            break;
    }

    dt_current_ = clampTimestep(dt_current_);
}

void AdaptiveTimeController::adjustTimestepOnFailure(GEMSResultType resultType) {
    switch (resultType) {
        case GEMSResultType::FAILURE_STIFFNESS:
            // Stiffness-related - standard reduction
            dt_current_ *= config_.shrink_factor;
            break;

        case GEMSResultType::FAILURE_STRUCTURAL:
            // Structural failure - more aggressive reduction
            dt_current_ *= config_.shrink_factor * config_.shrink_factor;
            break;

        case GEMSResultType::FAILURE_TERMINAL:
            // Terminal error - aggressive reduction
            dt_current_ *= 0.1;
            break;

        default:
            dt_current_ *= config_.shrink_factor;
            break;
    }

    dt_current_ = clampTimestep(dt_current_);

    // Clear iteration history on failure - past performance not relevant
    iteration_history_.clear();
}

double AdaptiveTimeController::clampTimestep(double dt) const {
    return std::max(config_.dt_min, std::min(dt, config_.dt_max));
}

double AdaptiveTimeController::predictSafeTimestep(
    KineticController* kineticController,
    double proposedDt) const
{
    if (!config_.use_kinetic_prediction || !kineticController) {
        return proposedDt;
    }

    // This method should be implemented to:
    // 1. Loop through kinetic phases
    // 2. For each phase with mass > threshold:
    //    a. Get current mass
    //    b. Get estimated dissolution rate (without modifying state)
    //    c. Calculate timestep for max_dc_change_fraction change
    // 3. Return minimum of all calculated timesteps

    // Placeholder - actual implementation requires KineticController interface
    // to provide rate estimates without state modification
    return proposedDt;
}

std::string AdaptiveTimeController::getStatusString() const {
    std::ostringstream oss;
    oss << std::scientific << std::setprecision(3);
    oss << "AdaptiveTimeController: "
        << "dt=" << dt_current_ << "h, "
        << "consec_success=" << consecutive_successes_ << ", "
        << "consec_fail=" << consecutive_failures_ << ", "
        << "total=" << total_steps_ << " ("
        << total_successes_ << " ok, "
        << total_failures_ << " fail)";

    if (!iteration_history_.empty()) {
        oss << ", avg_iter=" << std::fixed << std::setprecision(0)
            << computeMovingAverage();
    }

    return oss.str();
}

void AdaptiveTimeController::getStatistics(double& avgIterations,
                                            double& successRate,
                                            double& avgTimestep) const {
    avgIterations = computeMovingAverage();

    if (total_steps_ > 0) {
        successRate = static_cast<double>(total_successes_) / total_steps_;
    } else {
        successRate = 0.0;
    }

    if (!timestep_history_.empty()) {
        avgTimestep = std::accumulate(timestep_history_.begin(),
                                       timestep_history_.end(), 0.0)
                      / timestep_history_.size();
    } else {
        avgTimestep = dt_current_;
    }
}

void AdaptiveTimeController::setConfig(const AdaptiveTimeConfig& config) {
    config_ = config;
    dt_current_ = clampTimestep(dt_current_);
}
```

---

### 5.3 Controller Integration

**File:** `Controller.h`

```cpp
// Add near other includes (around line 30)
#include "AdaptiveTimeController.h"

// Add to private members (around line 200)
/**
 * @brief Adaptive time stepping controller.
 *
 * Manages timestep selection based on GEMS solver feedback.
 * Replaces fixed linear time stepping with intelligent adaptation.
 */
std::unique_ptr<AdaptiveTimeController> adaptiveTimeController_;

/**
 * @brief Flag to enable/disable adaptive time stepping.
 */
bool useAdaptiveTimeStepping_;
```

**File:** `Controller.cc`

Changes to `doCycle()` method (around line 570-800):

```cpp
// MODIFIED: Main simulation loop with adaptive time stepping
// Replace the existing time iteration loop with:

void Controller::doCycle() {
    // ... existing initialization code ...

    // Initialize adaptive controller if enabled
    if (useAdaptiveTimeStepping_ && !adaptiveTimeController_) {
        AdaptiveTimeConfig config;
        config.dt_initial = 0.001;  // 3.6 seconds
        config.dt_min = stepTimeTHR_;
        config.dt_max = 1.0;        // 1 hour
        config.verbose = verbose_;
        adaptiveTimeController_ = std::make_unique<AdaptiveTimeController>(config);
    }

    double currTime = 0.0;
    lastGoodTime_ = 0.0;

    // Main simulation loop
    while (currTime < finalHydrationTime_) {

        // Determine next timestep
        double proposedDt;
        if (useAdaptiveTimeStepping_) {
            proposedDt = adaptiveTimeController_->getNextTimestep();

            // Ensure we don't overshoot final time
            if (currTime + proposedDt > finalHydrationTime_) {
                proposedDt = finalHydrationTime_ - currTime;
            }

            // Ensure we hit output times
            for (const auto& outTime : outputImageTime_) {
                if (outTime > currTime && outTime < currTime + proposedDt) {
                    proposedDt = outTime - currTime;
                    break;
                }
            }
        } else {
            // Fall back to pre-generated time array
            proposedDt = getNextPreGeneratedTimestep(currTime);
        }

        // Save state for potential rollback
        saveStateForRollback();

        // Run kinetic step
        int kineticStatus = kineticController_->calculateKineticStep(
            currTime, proposedDt, cycleCount_);

        // Run GEMS equilibration
        int gemsStatus = chemSys_->calculateState(currTime + proposedDt, cycleCount_);

        if (gemsStatus == 0) {
            // SUCCESS
            if (useAdaptiveTimeStepping_) {
                long int iterDone = chemSys_->getIterDone();
                double pci = chemSys_->getPCI();
                double dxm = chemSys_->getDXM();
                adaptiveTimeController_->recordSuccess(iterDone, pci, dxm);
            }

            // Advance simulation
            currTime += proposedDt;
            lastGoodTime_ = currTime;
            cycleCount_++;

            // Handle output if this is an output time
            checkAndWriteOutput(currTime);

        } else {
            // FAILURE
            restoreStateFromRollback();

            if (useAdaptiveTimeStepping_) {
                double newDt = adaptiveTimeController_->recordFailure(gemsStatus);

                if (newDt <= stepTimeTHR_) {
                    // Cannot reduce further - fatal
                    throw GEMException("Controller", "doCycle",
                        "GEMS failed at minimum timestep");
                }
                // Loop will retry with smaller timestep

            } else {
                // Existing random sampling logic as fallback
                handleGEMSFailureLegacy(currTime, proposedDt);
            }
        }

        // Progress reporting
        if (cycleCount_ % 100 == 0) {
            reportProgress(currTime, cycleCount_);
        }
    }

    // ... existing cleanup code ...
}
```

---

## 6. File Changes Summary

### New Files
| File | Location | Description |
|------|----------|-------------|
| `AdaptiveTimeController.h` | `thameslib/` | Header for adaptive controller |
| `AdaptiveTimeController.cc` | `thameslib/` | Implementation |

### Modified Files
| File | Changes |
|------|---------|
| `ChemicalSystem.h` | Add 4 new accessor methods |
| `ChemicalSystem.cc` | Implement accessor methods (~30 lines) |
| `Controller.h` | Add member variable and flag (~5 lines) |
| `Controller.cc` | Modify `doCycle()` loop (~100 lines changed) |
| `CMakeLists.txt` | Add new source files |

### Optional Future Files
| File | Description |
|------|-------------|
| `KineticController.h/cc` | Add rate estimation method for prediction |

---

## 7. Testing Strategy

### Unit Tests

**Test 1: AdaptiveTimeController Basic Behavior**
```cpp
TEST(AdaptiveTimeController, GrowsTimestepOnEasySuccess) {
    AdaptiveTimeConfig config;
    config.successes_for_growth = 2;
    config.growth_factor = 1.5;
    AdaptiveTimeController controller(config);

    double initial_dt = controller.getNextTimestep();

    controller.recordSuccess(100, 1e-7, 1e-5);  // Easy
    controller.recordSuccess(100, 1e-7, 1e-5);  // Easy

    double new_dt = controller.getNextTimestep();
    EXPECT_GT(new_dt, initial_dt);
}

TEST(AdaptiveTimeController, ShrinksTimestepOnFailure) {
    AdaptiveTimeController controller;

    double initial_dt = controller.getNextTimestep();
    controller.recordFailure(4);  // ERR_GEM_AIA

    double new_dt = controller.getNextTimestep();
    EXPECT_LT(new_dt, initial_dt);
}

TEST(AdaptiveTimeController, RespectsMinMaxBounds) {
    AdaptiveTimeConfig config;
    config.dt_min = 0.001;
    config.dt_max = 1.0;
    AdaptiveTimeController controller(config);

    // Many failures should not go below min
    for (int i = 0; i < 100; i++) {
        controller.recordFailure(4);
    }
    EXPECT_GE(controller.getNextTimestep(), config.dt_min);

    // Many successes should not exceed max
    controller.reset();
    for (int i = 0; i < 100; i++) {
        controller.recordSuccess(10, 1e-8, 1e-5);
    }
    EXPECT_LE(controller.getNextTimestep(), config.dt_max);
}
```

### Integration Tests

**Test 2: Simple Hydration with Adaptive Stepping**
- Run a short hydration simulation (e.g., 1 hour simulated time)
- Verify no GEMS failures occur that aren't recovered
- Compare timestep distribution to fixed stepping

**Test 3: Stress Test with Difficult Chemistry**
- Use a mix design known to cause GEMS failures
- Verify adaptive controller recovers gracefully
- Count total GEMS calls compared to fixed stepping

### Regression Tests

**Test 4: Reproducibility**
- Run same simulation twice with same seed
- Verify identical results (timesteps are deterministic given same inputs)

**Test 5: Comparison to Legacy**
- Run simulation with adaptive stepping disabled
- Verify results match previous behavior exactly

---

## 8. Configuration and Tuning

### JSON Configuration (simparams.json)

```json
{
  "adaptive_timestepping": {
    "enabled": true,
    "dt_initial": 0.001,
    "dt_min": 1e-6,
    "dt_max": 1.0,
    "growth_factor": 1.2,
    "shrink_factor": 0.5,
    "target_iterations": 500,
    "warning_iterations": 5000,
    "successes_for_growth": 3,
    "use_kinetic_prediction": false,
    "max_dc_change_fraction": 0.05,
    "verbose": false
  }
}
```

### Recommended Initial Values

| Parameter | Conservative | Balanced | Aggressive |
|-----------|--------------|----------|------------|
| `dt_initial` | 0.0001 | 0.001 | 0.01 |
| `growth_factor` | 1.1 | 1.2 | 1.5 |
| `shrink_factor` | 0.3 | 0.5 | 0.7 |
| `target_iterations` | 200 | 500 | 1000 |
| `warning_iterations` | 3000 | 5000 | 6000 |
| `successes_for_growth` | 5 | 3 | 2 |

**Recommendation:** Start with "Balanced" settings and tune based on observed behavior.

---

## 9. Risk Assessment

### High Risk
| Risk | Mitigation |
|------|------------|
| Breaking existing simulations | Keep legacy mode as fallback (`useAdaptiveTimeStepping_ = false`) |
| Infinite retry loops | Hard limit on consecutive failures (e.g., 100) |
| Very small timesteps causing slow progress | Floor on minimum timestep, warning when hitting floor |

### Medium Risk
| Risk | Mitigation |
|------|------------|
| Missing output times | Explicit check to hit output times exactly |
| State save/restore overhead | Only save minimal required state |
| Thread safety issues | Document that controller is not thread-safe |

### Low Risk
| Risk | Mitigation |
|------|------------|
| Configuration complexity | Provide sensible defaults, document tuning |
| Increased memory usage | History limited to small fixed size |

---

## 10. Future Enhancements

### Phase 6: Advanced Prediction
- Implement full kinetic rate prediction
- Use machine learning to predict GEMS failure probability
- Consider phase boundary detection

### Phase 7: Multi-Level Adaptation
- Different adaptation strategies for different simulation stages
- Early hydration: aggressive growth allowed
- Near phase transitions: conservative stepping

### Phase 8: Parallel Time Stepping
- Speculative execution of multiple timesteps
- Cancel failed branches, continue successful ones

### Phase 9: User Interface
- Real-time visualization of timestep size
- Convergence metrics in progress display
- Interactive tuning during simulation

---

## Appendix A: GEMS3K Error Code Reference

| Code | Constant | Meaning | Adaptive Response |
|------|----------|---------|-------------------|
| 0 | `NO_GEM_SOLVER` | No calculation needed | N/A |
| 1 | `NEED_GEM_AIA` | Need AIA calculation | N/A |
| 2 | `OK_GEM_AIA` | Success with AIA | Record success |
| 3 | `BAD_GEM_AIA` | Warning with AIA | Record success (cautious) |
| 4 | `ERR_GEM_AIA` | Failure with AIA | Record failure (stiffness) |
| 5 | `NEED_GEM_SIA` | Need SIA calculation | N/A |
| 6 | `OK_GEM_SIA` | Success with SIA | Record success |
| 7 | `BAD_GEM_SIA` | Warning with SIA | Record success (cautious) |
| 8 | `ERR_GEM_SIA` | Failure with SIA | Record failure (stiffness) |
| 9 | `T_ERROR_GEM` | Terminal error | Record failure (terminal) |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **PCI** | Dikin criterion - convergence measure in IPM algorithm |
| **DXM** | Convergence threshold for PCI |
| **IPM** | Interior Point Method - GEMS3K's optimization algorithm |
| **FIA** | Feasible Initial Approximation - first phase of GEMS calculation |
| **AIA** | Automatic Initial Approximation - cold start mode |
| **SIA** | Smart Initial Approximation - warm start using previous solution |
| **DC** | Dependent Component - chemical species in GEMS |
| **IC** | Independent Component - chemical element in GEMS |

---

*End of Implementation Plan*

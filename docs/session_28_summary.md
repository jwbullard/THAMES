# Session 28 Summary: Model-Aware Adaptive Time Stepping & UI Charge Balance Validation

**Date:** January 25, 2026
**Platform:** macOS (Darwin 25.2.0)

## Overview

This session focused on optimizing adaptive time stepping performance for different kinetic model types and fixing a charge balance validation issue in the electrolyte composition editor.

## Key Issues Addressed

### 1. ParrotKilloh-Only Simulations Too Slow (5-10x)

**Problem:** After implementing adaptive time stepping, cement hydration simulations using only ParrotKilloh models were running 5-10x slower than the original code.

**Root Cause:** Conservative adaptive parameters (designed for numerically stiff SI-driven models) were being applied to all simulations.

**Solution:** Implemented model-aware detection via `KineticController::hasSignificantSIDrivenMass()`:
- Detects whether simulation uses SI-driven models (Standard, Pozzolanic) or DOR-driven models (ParrotKilloh)
- Applies appropriate parameters automatically:

| Model Type | dt_initial | dt_max | growth_factor | successes_for_growth |
|------------|------------|--------|---------------|---------------------|
| SI-driven | 0.0001h | 1.0h | 1.2 | 3 |
| DOR-driven (PK only) | 0.01h | 12.0h | 2.0 | 1 |

**Additional Fix:** Excluded fast-dissolving sulfate phases (Bassanite, Gypsum, Arcanite, Thenardite) from the SI-driven check since they dissolve quickly and don't cause numerical stiffness.

### 2. GEMS E05IPM Failure at 209 Hours (PKTest-03)

**Problem:** Simulation failed with Mass Balance Refinement errors after running for 8.72 days.

**Root Cause:** Carbon IC moles dropped from ~8.9e-08 to ~4.9e-08, approaching ICTHRESH (1e-8).

**Solution:** User increased initial DC concentrations by 10x, which provided more "buffer" for IC consumption. Simulation then completed in ~5 minutes.

### 3. CalciteTestAfter Charge Imbalance Error

**Problem:** Carbonation test failed immediately with "Electrolyte charge imbalance" error, but the UI showed charge balance as OK.

**Root Cause:** The C++ backend uses `std::map::insert()` which **ignores duplicate keys**. The JSON had K+ listed twice:
- First K+: 2e-05 mol (kept)
- Second K+: 0.004 mol (ignored!)

The UI was summing both entries (balanced), but the backend only saw the first entry (not balanced).

**Solution:** Updated `ElectrolyteCompositionEditor` to:
1. Detect duplicate DC entries
2. Show red ERROR message when duplicates exist
3. Calculate charge balance using first-occurrence-only logic (matching backend behavior)
4. Return `is_charge_balanced() = False` if duplicates exist

## Files Modified

### C++ (thames-hydration submodule)
- `src/thameslib/KineticController.h` - Added `hasSignificantSIDrivenMass()` declaration
- `src/thameslib/KineticController.cc` - Implemented model detection with exclusions
- `src/thameslib/Controller.cc` - Model-aware adaptive parameter selection

### Python (main repo)
- `src/app/widgets/electrolyte_composition_editor.py` - Duplicate detection and charge calculation fix

## How to Continue

### If Testing Carbonation Simulations
The CalciteTestAfter issue was due to duplicate K+ entries in the electrolyte. User substituted Na+ for the second K+ entry and the simulation is working.

### If Testing Cement Hydration
PK-only simulations should now run at approximately the same speed as before (with additional stability from adaptive stepping). If simulations are still slow, check:
1. Whether any SI-driven phases have kinetic models attached
2. The ipmlog.txt for GEMS errors that might be causing timestep reductions

### For Future GEMS Error Recovery
Discussed but not implemented:
- IC adjustment strategies when E05IPM errors occur
- Anticipatory IC monitoring before problems occur
- Automatic DC concentration boosting when ICs approach ICTHRESH

## Test Results

| Test | Configuration | Result |
|------|---------------|--------|
| PKTest-03 (initial) | Default adaptive params | Slow (~10x) |
| PKTest-03 (with exclusions) | Model-aware + fast-dissolving excluded | Still slow (Bassanite/Gypsum) |
| PKTest-03 (with 10x DCs) | Model-aware + higher DC concentrations | Success (~5 min) |
| CalciteTestAfter | Duplicate K+ entries | Failed: charge imbalance |
| CalciteTestAfter (fixed) | Single Na+ entry | Working |

## Code Snippets for Reference

### Model Detection (KineticController.cc)
```cpp
bool KineticController::hasSignificantSIDrivenMass() const {
  static const std::vector<std::string> fastDissolvingPhases = {
      "Bassanite", "Gypsum", "Arcanite", "Thenardite",
      "bassanite", "gypsum", "arcanite", "thenardite"
  };

  for (int i = 0; i < pKMsize_; ++i) {
    if (phaseKineticModel_[i] != nullptr) {
      std::string modelType = phaseKineticModel_[i]->getType();
      if (modelType == StandardType || modelType == PozzolanicType) {
        std::string phaseName = phaseKineticModel_[i]->getName();
        // Skip fast-dissolving phases
        bool isFastDissolving = false;
        for (const auto &fastPhase : fastDissolvingPhases) {
          if (phaseName == fastPhase) {
            isFastDissolving = true;
            break;
          }
        }
        if (isFastDissolving) continue;
        return true;
      }
    }
  }
  return false;
}
```

### Duplicate Detection (electrolyte_composition_editor.py)
```python
def _update_charge_balance(self):
    seen_dcs: Dict[str, float] = {}
    duplicate_dcs: List[str] = []

    for condition in self.conditions:
        if condition.dc_name in seen_dcs:
            if condition.dc_name not in duplicate_dcs:
                duplicate_dcs.append(condition.dc_name)
        else:
            seen_dcs[condition.dc_name] = condition.concentration

    # Calculate charge using only first occurrence (like C++ backend)
    # ...

    if duplicate_dcs:
        self.charge_label.set_markup(
            f'<span foreground="red">ERROR: Duplicate entries for {", ".join(duplicate_dcs)}. '
            f'Only first value will be used!</span>'
        )
```

## Next Session Suggestions

1. **Test carbonation simulations** with the updated electrolyte composition editor
2. **Consider implementing IC recovery strategies** for long-running simulations
3. **Add adaptive time stepping configuration** to simparams.json (Phase 5)
4. **Capture screenshots** for the User Manual (27 placeholders waiting)

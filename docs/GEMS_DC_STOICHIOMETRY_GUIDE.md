# Extracting DC Stoichiometry from GEMS

This document explains how to extract the stoichiometry of Dependent Components (DCs) and phases from GEMS (Gibbs Energy Minimization Software) using the GEMS3K library as implemented in THAMES.

## Overview

In GEMS, the chemical system is described using:

- **Independent Components (ICs)**: The fundamental chemical elements and charge (e.g., Ca, Si, O, H, Zz for charge)
- **Dependent Components (DCs)**: Chemical species made up of ICs (e.g., Ca+2, SiO2@, H2O@, Ca3SiO5)
- **Phases**: Groups of DCs that form thermodynamic phases (e.g., Electrolyte, Portlandite, CSHQ)

The stoichiometry matrix **A** describes how many moles of each IC are contained in one mole of each DC.

## Key Data Structures

### DATACH Structure (datach.h)

The core data is stored in the DATACH structure:

```cpp
// Number of components
nIC     // Total number of Independent Components
nDC     // Total number of Dependent Components
nPH     // Number of phases

// Stoichiometry matrix
A[nIC * nDC]  // Stoichiometry matrix, stored column-major
              // Access: A[icidx + dcidx * nIC]

// Phase composition
nDCinPH[nPH]  // Number of DCs in each phase
              // DCs are stored sequentially by phase
```

## Accessing DC Stoichiometry

### Method 1: Using TNode Interface (Direct GEMS3K Access)

The `TNode` class provides direct access to GEMS data:

```cpp
#include "node.h"

TNode* node;  // Assume initialized

// Get stoichiometry coefficient of IC in DC formula
// Parameters: xdc = DC index, xic = IC index
double stoich = node->DCaJI(xdc, xic);

// Example: Get moles of Ca in Ca3SiO5 (Alite)
int dcIdx = node->DC_name_to_xCH("Ca3SiO5");
int icIdx = node->IC_name_to_xCH("Ca");
double ca_in_alite = node->DCaJI(dcIdx, icIdx);  // Returns 3.0
```

### Method 2: Using ChemicalSystem Wrapper (THAMES)

THAMES wraps GEMS3K in the `ChemicalSystem` class with convenient accessors:

```cpp
#include "ChemicalSystem.h"

ChemicalSystem* chemSys;  // Assume initialized

// Get stoichiometry coefficient for a single IC in a DC
double stoich = chemSys->getDCStoich(dcIdx, icIdx);

// Get all IC stoichiometries for a DC (returns vector)
std::vector<double> dcStoich = chemSys->getDCStoich(dcIdx);

// Get full stoichiometry matrix (returns 2D vector)
std::vector<std::vector<double>> allStoich = chemSys->getDCStoich();

// Get charge of a DC (last IC is always charge)
double charge = chemSys->getDCCharge(dcIdx);
// Or by name:
double charge = chemSys->getDCCharge("Ca+2");  // Returns 2.0
```

## Accessing Phase Composition

### Which DCs Belong to a Phase?

```cpp
// Get list of DC indices that belong to a phase
std::vector<int> dcMembers = chemSys->getGEMPhaseDCMembers(phaseIdx);
// Or by name:
std::vector<int> dcMembers = chemSys->getGEMPhaseDCMembers("CSHQ");

// Example: List all DCs in the C-S-H solid solution
int cshqIdx = chemSys->getGEMPhaseId("CSHQ");
std::vector<int> cshDCs = chemSys->getGEMPhaseDCMembers(cshqIdx);
for (int dcId : cshDCs) {
    std::cout << chemSys->getDCName(dcId) << std::endl;
}
// Output: CSHQ_TobH, CSHQ_TobD, CSHQ_JenH, CSHQ_JenD
```

### DC Mole Amounts and Mole Fractions

```cpp
// Get current mole amount of a DC
double moles = chemSys->getDCMoles(dcIdx);

// Get mole fraction (concentration) of DC in its phase
// For aqueous species: returns molality
// For other phases: returns mole fraction
double moleFrac = node->Get_cDC(dcIdx);

// Get phase total moles
double phaseMoles = node->Ph_Moles(phaseIdx);
```

### Phase Bulk Composition (IC Moles)

For solid solutions and multicomponent phases, you can get the phase bulk composition:

```cpp
// Get IC composition of a phase (moles of each IC)
double* composition = node->Ph_BC(phaseIdx, nullptr);
// Note: Returns array of nIC elements, caller must free if nullptr passed

// Or use THAMES wrapper:
double icMoles = chemSys->getGEMPhaseStoich(phaseIdx, icIdx);
// Or by name:
double icMoles = chemSys->getGEMPhaseStoich("CSHQ", chemSys->getICId("Ca"));
```

## Working with Solid Solutions

Solid solutions (like C-S-H) have variable composition depending on equilibrium conditions. The phase composition is the weighted sum of its end-member DCs.

### Example: Calculate C-S-H Composition

```cpp
// Get DC members of C-S-H phase
int cshqIdx = chemSys->getGEMPhaseId("CSHQ");
std::vector<int> dcIds = chemSys->getGEMPhaseDCMembers(cshqIdx);

// Get current mole amounts
double totalMoles = 0.0;
for (int dcId : dcIds) {
    totalMoles += chemSys->getDCMoles(dcId);
}

// Calculate effective Ca/Si ratio
double totalCa = 0.0, totalSi = 0.0;
int caIdx = chemSys->getICId("Ca");
int siIdx = chemSys->getICId("Si");

for (int dcId : dcIds) {
    double dcMoles = chemSys->getDCMoles(dcId);
    totalCa += dcMoles * chemSys->getDCStoich(dcId, caIdx);
    totalSi += dcMoles * chemSys->getDCStoich(dcId, siIdx);
}

double casiRatio = totalCa / totalSi;
std::cout << "C-S-H Ca/Si ratio: " << casiRatio << std::endl;
```

## Complete Example: Print DC Stoichiometry Table

```cpp
void printDCStoichiometry(ChemicalSystem* chemSys) {
    int numDCs = chemSys->getNumDCs();
    int numICs = chemSys->getNumICs();

    // Print header
    std::cout << std::setw(20) << "DC Name";
    for (int i = 0; i < numICs; i++) {
        std::cout << std::setw(8) << chemSys->getICName(i);
    }
    std::cout << std::endl;

    // Print stoichiometry for each DC
    for (int dc = 0; dc < numDCs; dc++) {
        std::cout << std::setw(20) << chemSys->getDCName(dc);
        for (int ic = 0; ic < numICs; ic++) {
            double stoich = chemSys->getDCStoich(dc, ic);
            if (stoich != 0.0) {
                std::cout << std::setw(8) << std::fixed
                          << std::setprecision(2) << stoich;
            } else {
                std::cout << std::setw(8) << "-";
            }
        }
        std::cout << std::endl;
    }
}
```

## Function Reference Summary

### TNode (GEMS3K Direct Access)

| Function | Description |
|----------|-------------|
| `DCaJI(xdc, xic)` | Stoichiometry coefficient of IC in DC |
| `DC_n(xCH)` | Current mole amount of DC |
| `Get_nDC(xdc)` | Current mole amount of DC (node) |
| `Get_cDC(xdc)` | Concentration/mole fraction of DC |
| `Ph_BC(xph, ARout)` | Phase bulk composition (IC moles) |
| `Ph_Moles(xph)` | Phase amount in moles |
| `DC_name_to_xCH(name)` | Get DC index from name |
| `IC_name_to_xCH(name)` | Get IC index from name |

### ChemicalSystem (THAMES Wrapper)

| Function | Description |
|----------|-------------|
| `getDCStoich(dcIdx, icIdx)` | Stoichiometry coefficient |
| `getDCStoich(dcIdx)` | All IC stoichiometries for DC |
| `getDCStoich()` | Full stoichiometry matrix |
| `getDCCharge(dcIdx)` | Charge of DC |
| `getDCMoles(idx)` | Mole amount of DC |
| `getGEMPhaseDCMembers(phaseIdx)` | List of DC ids in phase |
| `getGEMPhaseStoich(phaseIdx, icIdx)` | IC stoichiometry for phase |
| `getDCId(name)` | Get DC index from name |
| `getICId(name)` | Get IC index from name |
| `getGEMPhaseId(name)` | Get phase index from name |
| `getDCName(idx)` | Get DC name from index |
| `getICName(idx)` | Get IC name from index |
| `getGEMPhaseName(idx)` | Get phase name from index |

## Notes

1. **Index Systems**: GEMS uses two index systems:
   - **xCH** (DCH index): Index in the full chemical system definition
   - **xDB** (DBR index): Index in the current data bridge (subset for transport)

   Most functions accept xCH indices. Use `DC_xCH_to_xDB()` to convert.

2. **Charge**: The last IC is always "Zz" (electric charge). DC charge can be obtained as `getDCStoich(dcIdx, numICs-1)` or using `getDCCharge(dcIdx)`.

3. **Units**: Stoichiometry coefficients are in moles of IC per mole of DC.

4. **Solid Solutions**: For variable-composition phases, use `getGEMPhaseDCMembers()` to get end-members, then sum weighted by their mole amounts.

## See Also

- `backend/thames-hydration/src/thameslib/ChemicalSystem.h` - THAMES wrapper class
- `backend/thames-hydration/src/GEMS3K-standalone/GEMS3K/node.h` - TNode interface
- `backend/thames-hydration/src/GEMS3K-standalone/GEMS3K/datach.h` - Data structures

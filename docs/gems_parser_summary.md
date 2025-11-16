# GEMS Parser Service - Summary

## Overview

The GEMS Parser Service (`gems_parser_service.py`) successfully parses the THAMES thermodynamic database files to extract phase and dependent component (DC) information needed for the UI.

## Key Features

### 1. Data Extraction
- **13 Independent Components (ICs)**: Al, C, Ca, Fe, H, K, Mg, Na, Nit, O, S, Si, Zz
- **180 Dependent Components (DCs)**: Chemical species made from ICs
- **92 GEM Phases**: Phase assemblages containing one or more DCs

### 2. Phase-DC Relationship Mapping
The parser correctly implements the ordering relationship:
- **Phase 1 (aq_gen)**: DCs 1-69 (aqueous ions and species)
- **Phase 2 (gas_gen)**: DCs 70-77 (gases: CO2, CH4, H2, N2, O2, H2S, SO3, H2O)
- **Phase 3 onwards**: Solid phases with varying numbers of DCs

### 3. Phase Classification
- **Aqueous phases (class 'a')**: 1 phase (aq_gen)
- **Gas phases (class 'g')**: 1 phase (gas_gen)
- **Solid phases (class 's')**: 90 phases (various minerals and hydrates)

## Cement-Related Phase Names

GEMS uses descriptive names for cement phases:

| GEMS Phase Name | Chemical Formula | Phase Type |
|-----------------|------------------|------------|
| Alite | C3S | Clinker |
| Belite | C2S | Clinker |
| Aluminate | C3A | Clinker |
| Ferrite | C4AF | Clinker |
| Portlandite | CH | Hydration Product |
| C3AH6 | C3AH6 | Hydration Product |
| CSHQ | C-S-H | Hydration Product (variable composition) |
| ettr | Ettringite | Hydration Product |
| Gypsum | CaSO4·2H2O | Sulfate |
| Anhydrite | CaSO4 | Sulfate |
| Calcite | CaCO3 | Carbonate |
| Quartz | SiO2 | Silica |
| Sfume | Silica Fume | SCM |

## API Usage Examples

### Basic Usage
```python
from pathlib import Path
from app.services.gems_parser_service import GEMSParserService

# Initialize parser
gems_dir = Path("src/data/gems")
parser = GEMSParserService(gems_dir)

# Get summary
print(parser.get_summary())
```

### Query Specific Phase
```python
# Get aqueous phase
aq_gen = parser.get_phase('aq_gen')
print(f"Phase: {aq_gen.name}")
print(f"Number of DCs: {aq_gen.num_dcs}")
print(f"DC names: {aq_gen.dc_names[:5]}")  # First 5
```

### Get DCs for a Phase
```python
# Get all DCs for gas phase
gas_dcs = parser.get_dcs_for_phase('gas_gen')
for dc in gas_dcs:
    print(f"{dc.name}: {dc.molar_mass} kg/mol")
```

### Filter Phases by Type
```python
# Get all solid phases
solid_phases = parser.get_solid_phases()
print(f"Found {len(solid_phases)} solid phases")

# Get cement clinker phases
clinker_phases = ['Alite', 'Belite', 'Aluminate', 'Ferrite']
for name in clinker_phases:
    phase = parser.get_phase(name)
    if phase:
        dcs = parser.get_dcs_for_phase(name)
        print(f"{name}: {[dc.name for dc in dcs]}")
```

### Validate Phase Configuration
```python
# Check if DCs are valid for a phase
dc_names = ['Ca+2', 'OH-', 'H2O@']
is_valid, msg = parser.validate_phase_dc_configuration('aq_gen', dc_names)
if is_valid:
    print("✅ Valid configuration")
else:
    print(f"❌ Invalid: {msg}")
```

## Data Structures

### GEMPhase
```python
@dataclass
class GEMPhase:
    name: str              # Phase name (e.g., 'Alite')
    index: int             # 0-based index
    num_dcs: int           # Number of DCs in this phase
    dc_indices: List[int]  # Indices of DCs
    dc_names: List[str]    # Names of DCs
    class_code: str        # 'a', 'g', 's', etc.
```

### DependentComponent
```python
@dataclass
class DependentComponent:
    name: str          # DC name (e.g., 'Ca+2')
    index: int         # 0-based index
    molar_mass: float  # kg/mol
    class_code: str    # 'S', 'I', 'J', 'M', 'O', 'G', etc.
```

## UI Integration Points

### 1. Materials Panel
When defining materials for THAMES, the UI can:
- Query available solid phases for cement clinker phases
- Get DC information for each phase
- Validate user selections against GEMS database

### 2. Phase Selection Dropdowns
```python
# Populate dropdown with cement phases
cement_phases = ['Alite', 'Belite', 'Aluminate', 'Ferrite',
                 'Gypsum', 'Anhydrite', 'Portlandite']
for name in cement_phases:
    phase = parser.get_phase(name)
    if phase:
        # Add to dropdown with DCs automatically mapped
```

### 3. Hydration Configuration
When building simparams.json:
```python
# For each selected phase
phase_config = {
    "thamesname": phase.name,
    "id": phase_id,  # User-assigned or auto
    "gemphase_data": [
        {
            "gemphasename": phase.name,
            "gemdc": [
                {"gemdcname": dc.name, "gemdcporosity": 1}
                for dc in parser.get_dcs_for_phase(phase.name)
            ]
        }
    ]
}
```

## Testing

Run the test script:
```bash
source thames-env/bin/activate
python test_gems_parser.py
```

## Next Steps for UI Development

1. **Materials Panel Adaptation**
   - Map VCCTL material types to GEMS phases
   - Provide phase selection interface
   - Auto-populate DCs for selected phases

2. **JSON Generation Service**
   - Use parser to build correct DC lists for each phase
   - Validate phase configurations before writing JSON
   - Generate simparams.json with proper structure

3. **Phase Property Editor**
   - Allow users to set kinetic parameters per phase
   - Set impurity concentrations
   - Define sub-voxel porosity (e.g., for C-S-H)

## File Locations

- **Parser Service**: `src/app/services/gems_parser_service.py`
- **GEMS Data Files**: `src/data/gems/`
  - `thames-dch.dat` (32 KB)
  - `thames-dbr.dat` (15 KB)
  - `thames-ipm.dat` (20 KB)
  - `thames-dat.lst` (55 bytes)
- **Test Script**: `test_gems_parser.py`
- **This Document**: `docs/gems_parser_summary.md`

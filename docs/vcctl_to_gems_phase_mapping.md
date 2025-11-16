# VCCTL to GEMS Phase Mapping

## Cement Phases

Complete mapping from VCCTL cement phase names to GEMS phase names in `thames-dch.dat`:

| VCCTL Phase Name | GEMS Phase Name (`<PHNL>`) | Chemical Formula | Notes |
|------------------|---------------------------|------------------|-------|
| C3S | Alite | Ca3SiO5 | Tricalcium silicate |
| C2S | Belite | Ca2SiO4 | Dicalcium silicate |
| C3A | Aluminate | Ca3Al2O6 | Tricalcium aluminate |
| C4AF | Ferrite | Ca4Al2Fe2O10 | Tetracalcium aluminoferrite |
| K2SO4 | arcanite | K2SO4 | Potassium sulfate |
| NA2SO4 | thenardite | Na2SO4 | Sodium sulfate |
| GYPSUM | Gypsum | CaSO4·2H2O | Calcium sulfate dihydrate |
| HEMIHYD | hemihydrate | CaSO4·0.5H2O | Calcium sulfate hemihydrate |
| ANHYDRITE | Anhydrite | CaSO4 | Calcium sulfate anhydrite |

## Migration Strategy

### Cements
**Status**: ✅ Ready to migrate

All VCCTL cements can be migrated using the mapping above. Each cement in the VCCTL database contains some combination of these 9 phases with mass fractions.

**Migration steps**:
1. Read VCCTL cement database
2. For each cement, extract phase mass fractions
3. Map VCCTL phase names → GEMS phase names
4. Create THAMES Material with:
   - Original cement name
   - Tags: ["cement", "migrated-from-vcctl"]
   - Phase composition using GEMS names
   - Density, PSD (if available)

### Limestone
**Status**: ✅ Ready to migrate

Limestone phases in GEMS:
- **Calcite** (CaCO3)
- **Dolomite-dis** (CaMg(CO3)2, disordered)
- **Dolomite-ord** (CaMg(CO3)2, ordered)
- **lime** (CaO)

**Migration steps**:
1. Read VCCTL limestone database
2. For each limestone, extract phase mass fractions
3. Map to GEMS phase names (likely just Calcite for most)
4. Create THAMES Material with tags: ["limestone", "migrated-from-vcctl"]

### Fly Ash
**Status**: ✅ Phase list available (user-defined materials)

Typical fly ash phases (users will create custom fly ash materials):
- **Quartz** (SiO2) - crystalline silica
- **Mullite** (Al6Si2O13) - aluminum silicate
- **Aluminate** (C3A) - ⚠️ Also in cement!
- **C2AS(am)** - amorphous calcium aluminum silicate
- **CA2S(am)** - amorphous calcium aluminum silicate
- **CAS(am)** - amorphous calcium aluminum silicate
- **CAS2(am)** - amorphous calcium aluminum silicate
- **K6A2S(am)** - amorphous potassium aluminum silicate

**Note**: These will NOT be migrated from VCCTL. Users define fly ash materials using these phases.

### Slag
**Status**: ❌ Not ready

Slag phases are still being added to the GEMS thermodynamic database. Will be available later.

### Fillers
**Status**: ❌ Not migrating

Fillers will not be migrated. Users will define their own using available phases like:
- Quartz (SiO2)
- Periclase (MgO)
- Calcite (CaCO3)
- Magnesite (MgCO3)
- etc.

## Phase Verification

Verify all GEMS phases exist in `thames-dch.dat`:

```python
from app.services.gems_parser_service import GEMSParserService
from pathlib import Path

parser = GEMSParserService(Path("src/data/gems"))

cement_phases = [
    "Alite", "Belite", "Aluminate", "Ferrite",
    "arcanite", "thenardite", "Gypsum",
    "hemihydrate", "Anhydrite"
]

for phase_name in cement_phases:
    phase = parser.get_phase(phase_name)
    if phase:
        print(f"✅ {phase_name}: {phase.num_dcs} DCs")
    else:
        print(f"❌ {phase_name}: NOT FOUND")
```

Expected output:
```
✅ Alite: 1 DCs
✅ Belite: 1 DCs
✅ Aluminate: 1 DCs
✅ Ferrite: 1 DCs
✅ arcanite: 1 DCs
✅ thenardite: 1 DCs
✅ Gypsum: 1 DCs
✅ hemihydrate: 1 DCs
✅ Anhydrite: 1 DCs
```

## Important Notes

### Phase Reuse Across Materials
⚠️ **GEM phases are NOT exclusive to one material type**. For example:
- **Aluminate** appears in both cement and fly ash
- **Quartz** can be in fly ash, fillers, aggregates, etc.
- Any GEM phase can potentially be part of any material grouping

This is why the **tag-based system** is essential - rigid material categories would be too limiting.

### Database Structure
- All migrated phases are solid phases (class code 's')
- Each phase has exactly 1 DC in the GEMS database
- VCCTL uses uppercase names; GEMS uses mixed/lowercase
- Kinetic parameters will NOT be migrated - users define them in Mix Design

### Migration Summary
| Material Type | Status | Source |
|---------------|--------|--------|
| Cement | ✅ Migrate | VCCTL database |
| Limestone | ✅ Migrate | VCCTL database |
| Fly Ash | ❌ No migration | User-defined |
| Slag | ❌ Not ready | Phases still in development |
| Fillers | ❌ No migration | User-defined |

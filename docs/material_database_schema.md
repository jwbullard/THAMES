# THAMES Material Database Schema

## Overview

THAMES uses a tag-based material system that differs significantly from VCCTL's rigid material categories. This design provides flexibility for the 92 GEM phases in the GEMS database.

**Key Design Principles:**
1. **Tag-based classification** - No rigid "Cement" vs "Fly Ash" categories
2. **Phase composition storage** - Materials defined by GEM phase fractions
3. **No kinetic parameters** - Kinetics defined in Mix Design, not materials
4. **Flexible and searchable** - User-defined tags enable powerful filtering

---

## Database Tables

### 1. Material Table

**Purpose**: Main table storing material information without rigid categories.

```sql
CREATE TABLE material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL UNIQUE,
    specific_gravity FLOAT DEFAULT 3.15,
    specific_surface_area FLOAT,
    psd_data_id INTEGER NOT NULL REFERENCES psd_data(id),  -- REQUIRED
    description TEXT,
    source VARCHAR(255),
    notes TEXT,
    immutable BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Fields:**
- `id`: Auto-increment primary key
- `name`: Unique material name (e.g., "Portland Cement Type I")
- `specific_gravity`: Material density (default 3.15 for cement)
- `specific_surface_area`: SSA in m²/kg (optional)
- `psd_data_id`: **REQUIRED** - Foreign key to PSDData table (shared with VCCTL)
- `description`: User description
- `source`: Material source/origin
- `notes`: Additional notes
- `immutable`: Read-only flag for VCCTL migrated materials

**Important**: Every material MUST have PSD data since particle size distribution is essential for microstructure generation.

**Example Records:**
```python
Material(
    name="Portland Cement Type I",
    tags=["cement", "type-i", "portland", "migrated-vcctl"],
    specific_gravity=3.15,
    immutable=True
)

Material(
    name="Class F Fly Ash Custom",
    tags=["fly_ash", "class-f", "custom"],
    specific_gravity=2.35,
    immutable=False
)
```

---

### 2. Tag Table

**Purpose**: User-defined tags for material classification and search.

```sql
CREATE TABLE tag (
    name VARCHAR(64) PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Fields:**
- `name`: Tag name (e.g., "cement", "type-i", "portland", "fly_ash", "class-f")
- `description`: Optional tag description

**Example Tags:**
- Cement types: `cement`, `type-i`, `type-ii`, `type-iii`, `type-v`, `portland`, `blended`
- Limestone: `limestone`, `high-purity`, `dolomitic`
- Fly ash: `fly_ash`, `class-f`, `class-c`
- Slag: `slag`, `ggbfs`, `grade-100`, `grade-120`
- General: `migrated-vcctl`, `custom`, `experimental`

---

### 3. MaterialTags Association Table

**Purpose**: Many-to-many relationship between Materials and Tags.

```sql
CREATE TABLE material_tags (
    material_id INTEGER NOT NULL REFERENCES material(id),
    tag VARCHAR(64) NOT NULL REFERENCES tag(name),
    PRIMARY KEY (material_id, tag)
);
```

**Example Associations:**
```
material_id=1, tag="cement"
material_id=1, tag="type-i"
material_id=1, tag="portland"
material_id=1, tag="migrated-vcctl"

material_id=2, tag="limestone"
material_id=2, tag="high-purity"
```

---

### 4. MaterialPhase Table

**Purpose**: Stores phase composition for each material (many-to-many with validation).

```sql
CREATE TABLE material_phase (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES material(id),
    gem_phase_name VARCHAR(64) NOT NULL,
    mass_fraction FLOAT NOT NULL CHECK (mass_fraction >= 0 AND mass_fraction <= 1),
    volume_fraction FLOAT CHECK (volume_fraction >= 0 AND volume_fraction <= 1),
    surface_fraction FLOAT CHECK (surface_fraction >= 0 AND surface_fraction <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (material_id, gem_phase_name)
);
```

**Fields:**
- `id`: Auto-increment primary key
- `material_id`: Foreign key to Material
- `gem_phase_name`: GEM phase name from GEMS database (e.g., "Alite", "Belite", "Gypsum")
- `mass_fraction`: Mass fraction (0.0-1.0, required)
- `volume_fraction`: Volume fraction (0.0-1.0, optional - can be calculated)
- `surface_fraction`: Surface area fraction (0.0-1.0, optional - can be calculated)

**Validation:**
- Each material-phase combination must be unique
- Mass fraction is required and must sum to ≤ 1.0 for a material
- GEM phase name must exist in GEMS database

**Example Phase Composition (Portland Cement Type I):**
```
material_id=1, gem_phase_name="Alite", mass_fraction=0.60
material_id=1, gem_phase_name="Belite", mass_fraction=0.15
material_id=1, gem_phase_name="Aluminate", mass_fraction=0.08
material_id=1, gem_phase_name="Ferrite", mass_fraction=0.08
material_id=1, gem_phase_name="Gypsum", mass_fraction=0.05
```

---

### 5. PSDData Table (Shared with VCCTL)

**Purpose**: Particle size distribution data (reused from VCCTL).

This table already exists in VCCTL and will be shared. See `src/app/models/psd_data.py` for full schema.

**Key Fields:**
- `id`: Primary key
- `psd_mode`: Distribution type (rosin_rammler, log_normal, fuller, custom)
- `psd_d50`, `psd_n`, `psd_dmax`: Rosin-Rammler parameters
- `psd_median`, `psd_spread`: Log-normal parameters
- `psd_exponent`: Fuller-Thompson parameter
- `psd_custom_points`: JSON custom distribution

---

## Schema Diagram

```
┌─────────────────┐
│   Material      │
├─────────────────┤
│ id (PK)         │◄────┐
│ name (UNIQUE)   │     │
│ specific_gravity│     │
│ psd_data_id (FK)│──┐  │
│ description     │  │  │
│ immutable       │  │  │
└─────────────────┘  │  │
         │           │  │
         │ 1         │  │
         │           │  │
         │ M         │  │
         ▼           │  │
┌─────────────────┐ │  │
│ MaterialPhase   │ │  │
├─────────────────┤ │  │
│ id (PK)         │ │  │
│ material_id (FK)│─┘  │
│ gem_phase_name  │    │
│ mass_fraction   │    │
└─────────────────┘    │
                       │
         ┌─────────────┤
         │             │
         ▼ M           │
┌─────────────────┐    │
│   PSDData       │    │
├─────────────────┤    │
│ id (PK)         │◄───┘
│ psd_mode        │
│ psd_d50         │
│ psd_median      │
└─────────────────┘

┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Material      │ M   │  material_tags   │  M  │      Tag        │
│                 │─────│  (association)   │─────│                 │
│ id (PK)         │     │ material_id (FK) │     │ name (PK)       │
│                 │     │ tag (FK)         │     │ description     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Differences from VCCTL

| Aspect | VCCTL | THAMES |
|--------|-------|--------|
| **Material Types** | 5 rigid tables (Cement, FlyAsh, Slag, Limestone, Filler) | 1 flexible Material table |
| **Classification** | Table name determines type | User-defined tags |
| **Phase Storage** | Embedded columns (c3s_mass_fraction, c2s_mass_fraction, etc.) | Separate MaterialPhase table |
| **Kinetic Parameters** | Stored in material (activation_energy) | **NOT stored** - defined in Mix Design |
| **Extensibility** | Hard to add new phases | Easy to add any GEM phase |
| **Phase Naming** | VCCTL notation (C3S, C2S) | GEM notation (Alite, Belite) |

---

## Migration Strategy

### From VCCTL → THAMES:

**Cements:**
1. Read VCCTL `cement` table
2. Create Material with tags: `["cement", "migrated-vcctl", <type>]`
3. Map phase names using `phase_mappings.py`:
   - C3S → Alite
   - C2S → Belite
   - C3A → Aluminate
   - C4AF → Ferrite
   - GYPSUM → Gypsum (dihyd), hemihydrate (hemihyd), Anhydrite (anhyd)
   - K2SO4 → arcanite
   - NA2SO4 → thenardite
4. Create MaterialPhase entries for each phase with mass_fraction
5. Link to PSDData (already exists, just use psd_data_id)
6. **DO NOT** migrate activation_energy (that's a kinetic parameter)

**Limestones:**
1. Read VCCTL `limestone` table
2. Create Material with tags: `["limestone", "migrated-vcctl"]`
3. Create MaterialPhase with gem_phase_name="Calcite", mass_fraction=1.0
4. Link to PSDData

**Fly Ash, Slag, Fillers:**
- **NOT migrated** - let users create custom materials with appropriate tags

---

## Example Queries

### Search materials by tag:
```python
# Find all cement materials
materials = session.query(Material)\
    .join(Material.tags)\
    .filter(Tag.name == 'cement')\
    .all()

# Find all Type I Portland cements
materials = session.query(Material)\
    .join(Material.tags)\
    .filter(Tag.name.in_(['cement', 'type-i', 'portland']))\
    .group_by(Material.id)\
    .having(func.count(Tag.name) == 3)\
    .all()
```

### Get phase composition:
```python
# Get all phases for a material
material = session.query(Material).filter_by(name="Portland Cement Type I").first()
for phase in material.phases:
    print(f"{phase.gem_phase_name}: {phase.mass_fraction}")
```

### Validate total phase fraction:
```python
# Ensure phases sum to ≤ 1.0
total = sum(phase.mass_fraction for phase in material.phases)
if total > 1.0:
    raise ValueError(f"Total phase fraction exceeds 1.0: {total}")
```

---

## Validation Rules

1. **Material name must be unique** across all materials
2. **PSD data is REQUIRED** - every material must have a particle size distribution
3. **Tags are lowercase** and stripped of whitespace
4. **Phase fractions** must be 0.0-1.0
5. **Total mass fraction** per material must be ≤ 1.0
6. **GEM phase names** must exist in GEMS database (validated via GEMSParserService)
7. **Each material-phase combination** must be unique (no duplicate phases per material)
8. **Specific gravity** must be > 0 and typically ≤ 5.0

---

## Automatic Specific Gravity Calculation

**NEW FEATURE**: THAMES can automatically calculate material specific gravity from phase composition using GEMS database thermodynamic data.

### How It Works:

1. Each DC has molar mass (kg/mol) and molar volume (m³/mol) in GEMS database
2. DC density = molar_mass / molar_volume
3. Phase density calculated from constituent DCs
4. Material specific gravity = mass-weighted average of phase densities

**Formula:**
```
density_material = 1 / Σ(w_i / ρ_i)
```
where `w_i` is mass fraction of phase i, `ρ_i` is density of phase i

### Example Results:

**Portland Cement Type I:**
- Alite (60%): 3.120 g/cm³
- Belite (15%): 3.326 g/cm³
- Aluminate (8%): 3.028 g/cm³
- Ferrite (8%): 3.732 g/cm³
- Gypsum (5%): 2.305 g/cm³
- **Calculated material SG: 3.164** (expected ~3.15) ✅

**High-Purity Limestone:**
- Calcite (97%): 2.710 g/cm³
- Dolomite (3%): 2.866 g/cm³
- **Calculated material SG: 2.716** (expected ~2.71) ✅

### Usage:

```python
from pathlib import Path
from app.services.gems_parser_service import GEMSParserService
from app.models import Material

# Initialize GEMS parser
parser = GEMSParserService(Path("src/data/gems"))

# Material has phase composition
material = Material(name="Portland Cement Type I", ...)

# Auto-calculate specific gravity
calculated_sg = material.calculate_specific_gravity_from_gems(parser)

# Use calculated value or allow user override
if material.specific_gravity is None:
    material.specific_gravity = calculated_sg
```

**Note:** User can always override the calculated value manually.

---

## Future Enhancements

1. **Auto-tagging from phase composition**: Automatically suggest tags based on detected phases
2. **Tag hierarchy**: Parent-child tag relationships (e.g., "cement" → "type-i" → "portland")
3. **Multi-DC phase densities**: Use actual DC mole fractions from GEMS equilibrium data (currently uses simplification for multi-DC phases)
4. **GEM phase validation**: Real-time validation against GEMS database when adding phases
5. **Material templates**: Pre-defined phase compositions for common materials
6. **Batch import**: CSV/Excel import for multiple materials
7. **Volume/surface fractions**: Auto-calculate from mass fractions and densities

---

## Implementation Files

- `src/app/models/material.py` - Material and Tag models
- `src/app/models/material_phase.py` - MaterialPhase model
- `src/app/models/psd_data.py` - PSDData model (shared with VCCTL)
- `src/app/config/phase_mappings.py` - VCCTL↔GEMS phase name mappings
- `src/app/services/gems_parser_service.py` - GEMS database parser for validation

---

## Schema Creation

The schema will be created automatically by SQLAlchemy when the database is initialized:

```python
from app.database.base import Base, engine
from app.models import Material, Tag, MaterialPhase, PSDData

# Create all tables
Base.metadata.create_all(bind=engine)
```

**Note**: The new THAMES tables (`material`, `tag`, `material_tags`, `material_phase`) will coexist with the legacy VCCTL tables (`cement`, `limestone`, `fly_ash`, etc.) in the same database during the transition period.

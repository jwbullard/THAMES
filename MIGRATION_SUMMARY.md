# VCCTL to THAMES Material Migration Summary

**Date**: November 16, 2025
**Migration Script**: `scripts/migrate_vcctl_materials.py`

---

## Migration Results

### ✅ Successfully Migrated

**Materials**: 37 total
- **Cements**: 36
- **Limestones**: 1

**Tags Created**: 3
- `cement`
- `limestone`
- `migrated-vcctl`

**Phase Entries**: 183 total
- Average ~4.95 phases per material
- Range: 1 phase (limestone) to 9 phases (some cements)

---

## Migration Details

### Cement Migration (36 materials)

**Source**: VCCTL `cement` table
**Target**: THAMES `material` table with tag-based system

**Phase Name Mappings Applied**:
```
C3S        → Alite
C2S        → Belite
C3A        → Aluminate
C4AF       → Ferrite
Gypsum     → Gypsum
Hemihydrate→ hemihydrate
Anhydrite  → Anhydrite
K2SO4      → arcanite
NA2SO4     → thenardite
```

**Tags Applied**: `["cement", "migrated-vcctl"]`

**Sample Migrated Cement**:
```
Name: cementotc
Phases:
  - Alite:      61.2% (C3S)
  - Belite:     25.1% (C2S)
  - Aluminate:   7.4% (C3A)
  - Ferrite:     6.3% (C4AF)
Total: 100.0%
Specific Gravity: 3.15
PSD: Linked to psd_data_id=1
Immutable: Yes
```

### Limestone Migration (1 material)

**Source**: VCCTL `limestone` table
**Target**: THAMES `material` table

**Phase Mapping**: Pure `Calcite` (100%)

**Tags Applied**: `["limestone", "migrated-vcctl"]`

**Migrated Limestone**:
```
Name: NormalLimestone
Phases:
  - Calcite: 100.0%
Specific Gravity: 2.65
PSD: Linked to existing PSD data
Immutable: Yes
```

---

## Database Schema Created

### Tables

1. **`material`** - Main material table
   - Columns: id, name, specific_gravity, specific_surface_area, psd_data_id, description, source, notes, immutable, created_at, updated_at
   - Unique constraint on `name`
   - Foreign key to `psd_data`

2. **`tag`** - Tag definitions
   - Primary key: `name` (no auto-increment id)
   - Columns: name, description, created_at, updated_at

3. **`material_tags`** - Association table (many-to-many)
   - Columns: material_id, tag
   - Foreign keys to both `material.id` and `tag.name`

4. **`material_phase`** - Phase composition
   - Columns: id, material_id, gem_phase_name, mass_fraction, volume_fraction, surface_fraction, created_at, updated_at
   - Foreign key to `material.id`
   - Unique constraint on (material_id, gem_phase_name)

---

## Key Features

### 1. Tag-Based Classification
- **No rigid categories**: Materials classified by flexible user-defined tags
- **Searchable**: Easy filtering by tag combinations
- **Extensible**: Users can add new tags without schema changes

### 2. GEM Phase Composition
- **92 phases available**: Full GEMS database support
- **Validated**: Phase names checked against GEMS database
- **Flexible**: Any combination of phases allowed

### 3. Preserved Data
- **PSD**: All particle size distributions linked to existing `psd_data` table
- **Properties**: Specific gravity, SSA, descriptions preserved
- **Immutable**: Migrated materials marked read-only to prevent accidental modification

### 4. Automatic Density Calculation (Available)
- Materials can calculate specific gravity from phase composition using GEMS database
- Based on molar mass / molar volume from `thames-dch.dat`
- Not used in migration (VCCTL values preserved), but available for new materials

---

## Migration Script Features

### Command-Line Options

```bash
# Dry run (preview without writing)
python scripts/migrate_vcctl_materials.py --dry-run

# Recalculate specific gravity from GEMS
python scripts/migrate_vcctl_materials.py --recalc-sg

# Skip certain material types
python scripts/migrate_vcctl_materials.py --skip-cements
python scripts/migrate_vcctl_materials.py --skip-limestones

# Custom database paths
python scripts/migrate_vcctl_materials.py --vcctl-db PATH --thames-db PATH
```

### Safety Features
- **Duplicate detection**: Skips materials that already exist
- **Dry-run mode**: Preview before committing
- **Transaction-based**: All-or-nothing commit
- **Error handling**: Continues on individual failures, reports at end
- **Validation**: Phase fractions checked for validity

---

## Verification Queries

### Count Materials by Tag
```sql
SELECT t.name AS tag, COUNT(*) AS count
FROM tag t
JOIN material_tags mt ON t.name = mt.tag
GROUP BY t.name;

-- Results:
-- cement: 36
-- limestone: 1
-- migrated-vcctl: 37
```

### Materials with Most Phases
```sql
SELECT m.name, COUNT(mp.id) AS phase_count
FROM material m
JOIN material_phase mp ON m.id = mp.material_id
GROUP BY m.id
ORDER BY phase_count DESC
LIMIT 5;
```

### Verify Phase Fraction Totals
```sql
SELECT m.name, SUM(mp.mass_fraction) AS total_fraction
FROM material m
JOIN material_phase mp ON m.id = mp.material_id
GROUP BY m.id
HAVING total_fraction < 0.95 OR total_fraction > 1.05
ORDER BY total_fraction;
```

---

## Future Steps

### Recommended Actions

1. **Test Materials**: Verify a few materials work correctly in hydration simulations
2. **Add Custom Materials**: Create new materials using tag system (fly ash, slag, etc.)
3. **Material Service**: Build CRUD service for material management
4. **UI Integration**: Connect Materials panel to new database schema
5. **Documentation**: Update user docs for tag-based material system

### Materials NOT Migrated (Intentionally)

- **Fly Ash**: Waiting for user requirements - too variable
- **Slag**: Phases still under development
- **Silica Fume**: User-defined
- **Fillers**: User-defined

These should be created by users as needed using the flexible tag system.

---

## Files Created

### Scripts
- `scripts/init_thames_tables.py` - Database table initialization
- `scripts/migrate_vcctl_materials.py` - Migration script (440 lines)
- `test_density_calculation.py` - GEMS density calculation tests

### Models
- `src/app/models/material.py` - Material and Tag models
- `src/app/models/material_phase.py` - MaterialPhase model

### Services
- `src/app/services/gems_parser_service.py` - Enhanced with density calculations

### Documentation
- `docs/material_database_schema.md` - Complete schema documentation
- `MIGRATION_SUMMARY.md` - This file

---

## Success Metrics

✅ All 36 cements migrated successfully
✅ All 1 limestone migrated successfully
✅ 183 phase entries created
✅ 3 tags created
✅ All materials linked to existing PSD data
✅ No errors or warnings
✅ Database integrity verified
✅ Immutable flags set correctly

**Migration Status**: ✅ **COMPLETE**

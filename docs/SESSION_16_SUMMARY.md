# Session 16: Multi-Temperature GEMS Database & Hydration Products Expansion
December 20, 2025

## Context

This session focused on enabling multi-temperature support (277-353K) for THAMES by creating working thermodynamic input files from GEM-Selektor, and expanding the hydration products available in the UI.

## Key Accomplishments

### 1. Multi-Temperature GEMS Database Debugging

**Problem:** New exports from GEM-Selektor v3.9.6 were failing with E06IPM errors or hanging during GEM_init, despite having the same phases as the working pyrrcem database.

**Root Cause Analysis:**
- Compared working `/Users/jwbullard/Software/tests/pyrrcem-298K-sat/pyrrox-*.dat` with new exports
- Created detailed comparison file: `/Users/jwbullard/NewThermoData/DBR_Differences.md`

**Key Differences Identified:**

| Parameter | Working pyrrcem | Failed Exports |
|-----------|-----------------|----------------|
| Temperature grid | 39 points (277.15-353.15K) | 38 points (278.15-352.15K) |
| Bulk composition (bIC) | Specific cement pore solution | Different test system |
| dul for Cl- (pos 63) | **1e-08** | 1000000 |
| dul for Cl2 (pos 80) | **0.001** | 1000000 |
| pe/Eh | Reducing (-10.89/-0.64V) | Oxidizing (7.81/0.46V) |

**Solution:**
- User replicated the working pyrrcem DBR parameters in GEM-Selektor
- Set temperature grid to 277.15-353.15K (39 points, 2K increments)
- Set upper metastability limits: Cl- = 1e-08, Cl2 = 0.001
- Created BaseIC export that matched working database

### 2. Successfully Added 11 New Phases

User added phases for pozzolanic materials simulation:
- **Glass phases:** Mullite, C2AS, CA2S, CAS, CAS2, K6A2S
- **Minerals:** Diopside, Albite, Anorthite, Fayalite, Forsterite

**Final Database Statistics:**
- **Phases (nPH):** 100
- **DCs (nDC):** 198
- **Temperature points (nTp):** 39 (277.15-353.15K)
- **Interpolation mode (mLook):** 0 (Lagrange interpolation)

### 3. Name Fixing Script

Applied to all new exports before copying to THAMES:

```bash
sed -i '' \
    -e "s/'aq_gen'/'Electrolyte'/g" \
    -e "s/'ettringite-AlFe'/'ettr-AlFe'/g" \
    -e "s/'ettringite05'/'ettr05'/g" \
    -e "s/'Fe-ettringite05'/'Fe-ettr05'/g" \
    -e "s/'ettringite30'/'ettr30'/g" \
    -e "s/'ettringite03_ss'/'ettr03_ss'/g" \
    -e "s/'ettringite13'/'ettr13'/g" \
    -e "s/'ettringite9'/'ettr9'/g" \
    -e "s/'ettringite'/'ettr'/g" \
    -e "s/'hydrotalc-pyro'/'Hydrotalc-pyr'/g" \
    -e "s/'monosulphate1205'/'monosulf1205'/g" \
    -e "s/'Fe-monosulph05'/'Fe-monosulf05'/g" \
    -e "s/'monosulphate10.5'/'monosulf10.5'/g" \
    -e "s/'monosulphate12'/'monosulf12'/g" \
    -e "s/'monosulphate14'/'monosulf14'/g" \
    -e "s/'monosulphate16'/'monosulf16'/g" \
    -e "s/'monosulphate9'/'monosulf9'/g" \
    -e "s/'monosulph-AlFe'/'monosulf-AlFe'/g" \
    -e "s/'monocarbonate9'/'monocarb9'/g" \
    -e "s/'monocarbonate'/'monocarb'/g" \
    -e "s/'hemicarbonat10.5'/'hemicarb10.5'/g" \
    -e "s/'hemicarbonate9'/'hemicarb9'/g" \
    -e "s/'hemicarbonate'/'hemicarb'/g" \
    -e "s/'Fe-hemicarbonate'/'Fe-hemicarb'/g" \
    -e "s/'Femonocarbonate'/'Femonocarb'/g" \
    -e "s/'hemihydrate'/'Bassanite'/g" \
    -e "s/'tricarboalu03'/'tricarb03'/g" \
    -e "s/'Ferrihydrite-am'/'Ferrihyd-am'/g" \
    -e "s/'Ferrihydrite-mc'/'Ferrihyd-mc'/g" \
    -e "s/'arcanite'/'Arcanite'/g" \
    -e "s/'thenardite'/'Thenardite'/g" \
    -e "s/'Silica-fume'/'Sfume'/g" \
    -e "s/'Sil-Fume'/'Sfume'/g" \
    -e "s/'OH-hydrotalcite'/'OH-hydrotalc'/g" \
    thames-dch.dat thames-dbr.dat
```

### 4. Expanded Hydration Products Service

Updated `/Users/jwbullard/Software/THAMES/src/app/services/hydration_products_service.py`:

**Before:** ~32 phases in dictionaries
**After:** 82 phases covering all hydration products

**Phases Added by Category:**

| Category | Phases Added |
|----------|--------------|
| Chloride AFm | Friedels, Kuzels |
| Zeolites | ZeoliteX, ZeoliteY, zeoliteP_Ca, Natrolite |
| Silicates | Forsterite, Fayalite, Mullite, Diopside, Albite, Anorthite |
| Pozzolanic | Sfume, K6A2S, CAS, CA2S, C2AS, CAS2 |
| Al hydroxides | Al(OH)3am, Al(OH)3mic, Gibbsite |
| Carbonates | Aragonite, Dolomite-dis, Dolomite-ord, Magnesite, Siderite, Fe-carbonate |
| Aluminate hydrates | C2AH75, CAH10, straetlingite, C2ASH55 |
| Ferrite hydrates | C3FS0.84H4.32, C3FS1.34H3.32, C4Fc05H10, C4FcH12 |
| Hydrotalcites | hydrotalcite, OH-hydrotalc |
| Fe oxides | Goethite, Hematite, Magnetite, Ferrihyd-am, Ferrihyd-mc |
| Other | thaumasite, syngenite, Kaolinite, Periclase, Melanterite, Pyrrhotite, Troilite, Sulphur, lime |

**Fixed Phase Names:**
- `straet` → `straetlingite` (match GEMS)
- `hydrotalc-pyro` → `Hydrotalc-pyr` (match GEMS)

**Phases NOT in service (input/dissolving phases - intentional):**
- Clinker: Alite, Belite, Aluminate, Ferrite, Mayenite, CA, CA2
- Sulfates: Arcanite, Thenardite, Bassanite, Gypsum, Anhydrite
- Silica: Quartz, Silica-amorph
- Non-solid: Electrolyte, gas_gen
- Other: Iron, Graphite, K-oxide, Na-oxide

### 5. Testing Results

- **BaseIC (89 phases):** Successfully ran hydration
- **BaseICAllPhases (100 phases):** Successfully ran hydration at 10°C, 25°C, and 40°C
- **Hydration products service:** 82 phases load correctly, no syntax errors

## Files Modified

### GEMS Database Files
- `/Users/jwbullard/Software/THAMES/src/data/gems/thames-dch.dat` - Updated with 100 phases, 198 DCs
- `/Users/jwbullard/Software/THAMES/src/data/gems/thames-ipm.dat` - Updated IPM parameters
- `/Users/jwbullard/Software/THAMES/src/data/gems/thames-dbr.dat` - Updated with correct bIC, dul constraints

### Python Files
- `/Users/jwbullard/Software/THAMES/src/app/services/hydration_products_service.py` - Added ~50 new phases

## Files Created

- `/Users/jwbullard/NewThermoData/DBR_Differences.md` - Detailed comparison of working vs failing DBR files
- `/Users/jwbullard/NewThermoData/BaseIC/` - Working 89-phase export
- `/Users/jwbullard/NewThermoData/BaseICAllPhases/` - Final 100-phase export

## Known Issues / Pending Work

1. **C++ Backend Debugging:** User identified issues when running arbitrary material systems (e.g., no clinker, diopside only). This requires C++ debugging in THAMES-Hydration.

2. **Affinity Data:** Most new phases have empty default affinities. User can configure these per-simulation in the UI.

## Key Learnings

1. **DBR Configuration is Critical:** The DBR file's bulk composition, dul constraints, and redox conditions must be appropriate for the system being modeled. The working pyrrcem database has specific constraints that help the GEM solver converge.

2. **Temperature Grid Matters:** The 39-point grid (277.15-353.15K) with 2K increments is the correct format for multi-T interpolation.

3. **Phase Name Consistency:** THAMES requires specific phase names (≤13 characters) that differ from GEM-Selektor defaults. The sed script handles these conversions.

4. **Hydration Products vs Input Phases:** The hydration products service should only contain phases that can precipitate (products), not phases that dissolve (inputs like clinker, sulfates, silica).

## Critical Files for Next Session

- **GEMS Database:** `src/data/gems/thames-*.dat`
- **Hydration Products:** `src/app/services/hydration_products_service.py`
- **Name Fixing Script:** See Section 3 above
- **DBR Differences:** `/Users/jwbullard/NewThermoData/DBR_Differences.md`
- **Working Export:** `/Users/jwbullard/NewThermoData/BaseICAllPhases/`

## Next Steps

1. Debug C++ backend for non-standard material systems
2. Test additional pozzolanic simulations (fly ash, slag)
3. Verify phase volume outputs make physical sense
4. Consider adding default affinities for new phases based on testing

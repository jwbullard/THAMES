# MicgenInputService Test Procedure

**Date:** November 26, 2025
**Purpose:** Test the newly implemented MicgenInputService integration with THAMES UI

## Overview

This document describes how to test the end-to-end microstructure generation workflow using the new MicgenInputService. The service replaces the old manual input generation with a systematic approach that:
- Discretizes PSDs for all 5 distribution modes
- Combines PSDs from multiple materials with weighted averaging
- Generates properly formatted micgen.c input files
- Integrates with the Phase ID Mapping system

## Prerequisites

✅ MicgenInputService implemented and tested (15/15 unit tests passing)
✅ UI integration complete
✅ micgen executable located at `./backend/bin/micgen`
✅ THAMES database has migrated materials (36 cements + 1 limestone)

## Test Procedure

### Step 1: Launch THAMES

```bash
cd /Users/jwbullard/Software/THAMES
source thames-env/bin/activate
python src/main.py
```

### Step 2: Navigate to Mix Design Panel

1. Click on the **Mix Design** tab in THAMES main window
2. Verify the panel loads without errors

### Step 3: Create a Simple Test Mix Design

Configure the following parameters:

**Basic Information:**
- **Mix Name:** `Test_Mix_1`
- **Description:** (optional) "Simple test with single cement"

**Materials:**
1. Click **Add Material** button
2. Select one of the migrated cements from dropdown (e.g., "Cement 116")
3. Set **Mass:** `1.0` kg
4. Verify specific gravity displays correctly

**Mix Parameters:**
- **Water/Binder Ratio:** `0.4`
- **Air Content:** `0.0` % (keep at zero for initial test)

**Microstructure Parameters:**
- **System Size X:** `100` voxels
- **System Size Y:** `100` voxels
- **System Size Z:** `100` voxels
- **Resolution:** `1.0` μm/voxel
- **Random Seed:** (leave at default or set to `-12345`)

**Advanced Settings:**
- **Flocculation:** Disabled (unchecked)
- **Dispersion Factor:** `0` (random)

### Step 4: Validate Mix Design

1. Click **Validate** button
2. Review validation results
3. Expected: Mix should validate successfully
   - If warnings appear about concrete-specific issues (w/b ratio, air content), these are expected and can be ignored (THAMES mode suppresses most of these)

### Step 5: Generate Microstructure

1. Click **Create Mix** button
2. Confirm the dialog that appears
3. Observe the following sequence:

**Expected Behavior:**

1. **Auto-save phase:**
   - Mix design saved to database
   - Status message: "Mix design auto-saved..."

2. **Input generation phase:**
   - MicgenInputService called
   - Input file generated
   - Status message: "Input file created, starting 3D microstructure generation..."

3. **Execution phase:**
   - micgen program starts
   - Operations panel shows progress
   - Status updates appear

### Step 6: Verify Output Files

Navigate to the operations directory:

```bash
cd ~/Library/Application\ Support/THAMES/operations/Test_Mix_1
ls -la
```

**Expected Files:**

1. **Test_Mix_1_input.txt** - Generated micgen input file
2. **Test_Mix_1_stdout.log** - Standard output from micgen
3. **Test_Mix_1_stderr.log** - Standard error from micgen (may be empty)
4. **cement116.sil, cement116.c3s, etc.** - Clinker correlation files (7 files)
5. **Test_Mix_1_microstructure.img** - Generated microstructure (after completion)
6. **Test_Mix_1_particle_ids.img** - Particle ID file (after completion)

### Step 7: Inspect Input File

```bash
cat Test_Mix_1_input.txt
```

**Expected Format:**

```
# THAMES Microstructure Generation Input File
# Mix Name: Test_Mix_1
# Generated: 2025-11-26 [timestamp]

-12345              # Random seed (negative integer)
2                   # SPECSIZE - Set system size
100                 # X size (voxels)
100                 # Y size (voxels)
100                 # Z size (voxels)
1.000000            # Resolution (micrometers/voxel)
4                   # ADDPART - Add particles
0                   # Shape mode: SPHERES
0.600000            # PC clinker volume fraction
0.000000            # Other solids volume fraction
0.400000            # Electrolyte volume fraction
0.000000            # Void volume fraction
6                   # Total number of phases
2                   # Phase ID: Alite
0.350000            # Volume fraction (solids basis)
10                  # Number of size classes
5.500000            # Diameter (voxels)
0.120000            # Volume fraction in this size class
...                 # More size classes
3                   # Phase ID: Belite
...                 # More phases
0                   # Dispersion factor
6                   # DISTRIB - Clinker distribution
cement116           # Path/root for correlation files
0.60 0.65           # Alite volume/surface fractions
0.20 0.18           # Belite volume/surface fractions
...                 # More clinker phases
9                   # ONEVOX - One pixel particles
10                  # OUTPUTMIC - Output files
Test_Mix_1_microstructure.img
Test_Mix_1_particle_ids.img
1                   # EXIT
```

**Key Things to Verify:**

✅ Menu numbers match micgen.c (not genmic.c): SPECSIZE=2, ADDPART=4, etc.
✅ System size matches input (100×100×100)
✅ Resolution matches input (1.0)
✅ Volume fractions sum appropriately
✅ Phase IDs are in range 2-7 for clinker phases
✅ Size classes are in voxel units (not micrometers)
✅ Clinker correlation path is correct

### Step 8: Monitor Execution

1. Switch to **Operations** panel
2. Find "Test_Mix_1" operation
3. Monitor progress updates
4. Expected duration: 1-5 minutes for 100³ voxel system

**Success Indicators:**
- Progress bar advances
- Status updates show "Processing..." → "Completed"
- Return code: 0
- Output files created

**Failure Indicators:**
- Return code: non-zero
- Error messages in stderr log
- Missing output files

### Step 9: Check for Common Issues

If the test fails, check these common issues:

**Issue 1: micgen executable not found**
```
Error: micgen executable not found at: /path/to/backend/bin/micgen
```
**Solution:** Verify micgen is compiled and in the correct location

**Issue 2: Database model mismatch**
```
Error: Could not load mix design from database
```
**Solution:** Check that mix design was saved successfully (check saved_mix_design_id)

**Issue 3: Missing PSD data**
```
Error: PSD data ID X not found
```
**Solution:** Verify material has valid PSD data associated

**Issue 4: Phase mapping issues**
```
Warning: Phase 'XYZ' not in phase mapping, skipping
```
**Solution:** Check that material phases are valid GEM phases

**Issue 5: Segmentation fault in micgen**
```
micgen execution completed with return code: -11
```
**Solution:** Check input file format, verify all required inputs present

## Success Criteria

The test is successful if:

1. ✅ Input file generated without errors
2. ✅ Input file has correct micgen.c format
3. ✅ micgen program executes without crashing
4. ✅ Microstructure .img files are created
5. ✅ File sizes are reasonable (100³ system ≈ 1MB)
6. ✅ No Python exceptions in logs

## Advanced Test: Multi-Material Mix

Once basic test passes, try a more complex mix:

**Materials:**
- Cement 116: 0.85 kg
- Limestone (from migration): 0.15 kg

**Expected Behavior:**
- Both materials contribute phases
- PSDs are combined with weighted averaging
- Multiple materials with same phase (if applicable) are merged

## Troubleshooting

### Enable Debug Logging

Edit `src/app/services/micgen_input_service.py` and change line 28:
```python
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Add this line
```

### Check Generated Input Manually

Compare the generated input file against `micgen-input.md` to verify sequence.

### Run micgen Manually

```bash
cd ~/Library/Application\ Support/THAMES/operations/Test_Mix_1
/Users/jwbullard/Software/THAMES/backend/bin/micgen < Test_Mix_1_input.txt
```

This runs micgen directly to see any error messages.

## Next Steps After Successful Test

1. Test with different PSD modes (Rosin-Rammler, Log-Normal, Fuller-Thompson)
2. Test with multiple materials
3. Test with flocculation enabled
4. Test with real-shape particles (when implemented)
5. Test with aggregate slab
6. Performance testing with larger systems (200³, 300³)

## Related Documentation

- `micgen-input.md` - micgen.c input format specification
- `tests/test_micgen_input_service.py` - Unit tests
- `src/app/services/micgen_input_service.py` - Implementation
- `docs/SESSION_7_SUMMARY.md` - Implementation session notes

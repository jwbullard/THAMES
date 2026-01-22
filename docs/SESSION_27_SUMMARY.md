# Session 27: Carbonation Testing, Timestep Tuning & Sub-Minute Output Files

**Date:** January 22, 2026
**Platform:** macOS (Darwin 25.2.0)

## Overview

This session focused on debugging carbonation simulations (CalThermoHet series) where Portlandite dissolves and Calcite precipitates in a CO2-rich environment. Two major issues were addressed:

1. Numerical instability from high kinetic rate constants
2. Missing output files due to filename collisions at sub-minute intervals

## Issue 1: Numerical Instability (CalThermoHet-10)

### Problem Description

User tested carbonation simulation with:
- 10× higher Portlandite dissolution rate constant (4e-5 → 4e-4)
- Fixed HCO3- concentration reduced by half

**Symptoms:**
- Portlandite SI overshot equilibrium in first 17 seconds (reached 5.5)
- SI came back down to ~1 at 21 seconds
- At 108 seconds, SI dropped to 0 then increased rapidly to 8
- GEMS solver failed 50+ consecutive times
- Simulation terminated at 130 seconds instead of target 600 seconds

### Root Cause Analysis

The high rate constant made the system "stiff" - large changes in composition per timestep caused the GEMS thermodynamic solver to struggle finding equilibrium. The adaptive time stepping tried to reduce the timestep, but the minimum was too large (1e-3 hours = 3.6 seconds).

### Solution: Smaller Minimum Timestep

Modified `Controller.cc` to use smaller timesteps for stiff systems:

```cpp
// Before
stepTimeTHR_ = 1.e-3;  // Minimum timestep: 3.6 seconds

// After
stepTimeTHR_ = 1.e-5;  // Minimum timestep: 0.036 seconds
```

Also reduced initial timestep and max relative change:

```cpp
// Initial timestep reduced
adaptiveConfig.dt_initial = 0.0001; // ~0.36 seconds (was 0.001)

// More conservative relative change limit
adaptiveTimeController_->setInitialTimestepFromKinetics(maxKineticRate, 0.02); // 2% (was 5%)
```

### Saturation Index Clarification

Important correction on SI interpretation:
- **SI = 1**: Equilibrium (activity product equals solubility product)
- **SI < 1**: Undersaturated (phase will dissolve)
- **SI > 1**: Supersaturated (phase will precipitate)
- **SI = 0**: Infinitely undersaturated (like pure water)

This is different from the common convention where SI = 0 means equilibrium.

## Issue 2: Missing Output Files (CalThermoHet-11)

### Problem Description

User configured simulation with:
- Final time: 10 minutes (600 seconds)
- Output interval: 0.3 minutes (18 seconds) linear spacing
- Expected: ~35 output images

**Actual result:** Only 11 .img files created

### Root Cause Analysis

The `getTimeString()` function in `Controller.cc` only used minutes as the smallest unit:

```cpp
// Old format: 000y000d00h00m
string timeString = timestrY + "y" + timestrD + "d" + timestrH + "h" + timestrM + "m";
```

With 0.3-minute spacing:
- t = 0.0 min → `00h00m`
- t = 0.3 min (18 sec) → `00h00m` (rounds down, 18 < 30)
- t = 0.6 min (36 sec) → `00h01m` (rounds up, 36 >= 30)
- t = 0.9 min (54 sec) → `00h01m`
- t = 1.2 min (72 sec) → `00h01m`

Multiple output times mapped to the same filename, overwriting each other!

### Solution: Add Seconds to Filename

Modified `getTimeString()` to include seconds when non-zero:

```cpp
// Keep track of seconds instead of rounding
secs = curtime_s;  // Remaining seconds after extracting minutes

// Build filename with optional seconds suffix
string timeString = timestrY + "y" + timestrD + "d" + timestrH + "h" + timestrM + "m";
if (secs > 0) {
    timeString += timestrS + "s";
}
```

**New filename format:**
- `000y000d00h00m.298K.img` (when seconds = 0, backward compatible)
- `000y000d00h00m18s.298K.img` (when seconds > 0)

### Python Updates

Updated regex patterns in two files to handle the new format:

**elastic_lineage_service.py (line 635):**
```python
# Before
thames_match = re.search(r'\.(\d{3})y(\d{3})d(\d{2})h(\d{2})m\.\d+K\.img$', filename)

# After (optional seconds group)
thames_match = re.search(r'\.(\d{3})y(\d{3})d(\d{2})h(\d{2})m(?:(\d{2})s)?\.\d+K\.img$', filename)
```

**hydration_results_viewer.py (line 494):**
```python
# Before
thames_time_pattern = re.compile(r'\.(\d+)y(\d+)d(\d+)h(\d+)m\.(\d+)K\.img$')

# After (optional seconds group)
thames_time_pattern = re.compile(r'\.(\d+)y(\d+)d(\d+)h(\d+)m(?:(\d+)s)?\.(\d+)K\.img$')
```

Both files also updated time calculations to include seconds:
```python
seconds = int(thames_match.group(5)) if thames_match.group(5) else 0
time_hours = years * 365 * 24 + days * 24 + hours + minutes / 60.0 + seconds / 3600.0
```

## Files Modified

### C++ (thames-hydration submodule)

| File | Changes |
|------|---------|
| `src/thameslib/Controller.cc` | `getTimeString()` now includes seconds; removed unused rounding variables; smaller minimum timestep |

### Python (main repo)

| File | Changes |
|------|---------|
| `src/app/services/elastic_lineage_service.py` | Updated regex for THAMES filenames; added seconds to time calculation |
| `src/app/windows/dialogs/hydration_results_viewer.py` | Updated regex for THAMES filenames; added seconds to time calculation |

## Test Results

| Test | Rate Constant | Result |
|------|---------------|--------|
| CalThermoHet-10 | 4e-4 (10×) | Failed - SI overshoot, GEMS failures |
| CalThermoHet-11 | 1.2e-5 (3×) | Ran 17,790 cycles, but only 11 images (filename bug) |

## Next Steps

1. **User to test sub-minute output** - Run CalThermoHet with 0.3-minute spacing and verify all 35 images created
2. **Continue carbonation tuning** - Find optimal Portlandite rate constant that balances speed vs stability
3. **Consider UI warning** - Add warning in Hydration Panel if output interval < 1 minute

## Code Location Reference

Key code sections for future reference:

- **getTimeString()**: `Controller.cc:2775-2834`
- **Timestep parameters**: `Controller.cc` constructor (~line 200-250)
- **Adaptive time stepping config**: `AdaptiveTimeController.h:AdaptiveTimeConfig`
- **THAMES filename parsing**: `elastic_lineage_service.py:631-658`, `hydration_results_viewer.py:492-523`

## Building After Changes

```bash
cd /Users/jwbullard/Software/THAMES/backend/thames-hydration/build
make -j4
cp thames /Users/jwbullard/Software/THAMES/bin/
```

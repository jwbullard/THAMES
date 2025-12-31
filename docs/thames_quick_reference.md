# THAMES-Hydration Quick Reference for VCCTL Integration

## Core Takeaways

### What is THAMES?

**THAMES** = **The Hydration and Microstructure Evolution Simulator**

- **Language**: C++17 (40+ classes, 40,000 lines)
- **Purpose**: Simulate cement hydration with full thermodynamic rigor
- **Input**: Microstructure image + JSON parameters + GEMS3K thermodynamic database
- **Output**: 11 CSV files + microstructure snapshots (.img) + visualization data
- **Simulation time**: 5-240 minutes (depends on lattice size and duration)

---

## Key Input Files (What VCCTL Must Provide)

### 1. GEMS Thermodynamic Databases (3 files)
```
thames-dat.lst     # Master reference
thames-dch.dat     # Dependent components (84 species)
thames-dbr.dat     # Database records
thames-ipm.dat     # Algorithm parameters
```
**Action**: Bundle these with VCCTL application

### 2. Simulation Parameters (simparams.json)
```json
{
  "environment": {
    "temperature": 298.15,      // [K]
    "saturated": 0,             // 0=sealed, 1=saturated
    "electrolyte_conditions": [ // Initial pore solution
      { "DCname": "Ca+2", "condition": "initial", "concentration": 0.01 }
    ]
  },
  "microstructure": {
    "numentries": 19,           // Number of phases
    "phases": [
      { "thamesname": "C3S", "id": 1, "kinetic_model": "ParrotKilloh" },
      { "thamesname": "C-S-H", "id": 20 },
      // ... more phases ...
    ],
    "time_parameters": {
      "initial_time": 0.0,
      "final_time": 1000.0,     // [hours]
      "output_frequency": 0.5   // Save every 0.5 hours
    }
  }
}
```
**Action**: Generate from VCCTL operation parameters

### 3. Microstructure Image (microstructure.img)
```
#THAMES:Version:5.0
#THAMES:X_Size:100
#THAMES:Y_Size:100
#THAMES:Z_Size:100
#THAMES:Image_Resolution:1.0
0 0 1 1 2 3 3 1 0 0 ... [1,000,000 space-separated integers]
```
**Action**: Convert from VCCTL .img format using `vcctl2thames` converter tool

### 4. Input Control File (input.in - for stdin)
```
2                      # Line 1: Simulation type (2=Hydration)
thames-dat.lst        # Line 2: GEMS master file
simparams.json        # Line 3: Simulation parameters
microstructure.img    # Line 4: Microstructure image
output_root_name      # Line 5: Output file prefix
```
**Action**: Create text file for pipe to stdin

---

## Key Output Files (What VCCTL Must Parse)

### CSV Files (11 total)

| File | Content | Key Use |
|------|---------|---------|
| `_dcmoles.csv` | Moles of each chemical species over time | Degree of hydration |
| `_CSH.csv` | C-S-H elemental composition | Product properties |
| `_phasevolume.csv` | Volume of each phase | Phase evolution tracking |
| `_porosity.csv` | Total porosity evolution | Durability prediction |
| `_phasemass.csv` | Mass of each phase | Material balance |
| `_phasecount.csv` | Voxel count per phase | Spatial distribution |
| `_surfacearea.csv` | Interface surface areas | Reaction kinetics |
| `_psdlin.csv` | Pore size distribution (linear) | Permeability analysis |
| `_psdlog.csv` | Pore size distribution (log) | Pore structure |
| `_CSratio_solid.csv` | Bulk Ca/Si ratio | Product identification |
| `_percolation.csv` | Pore connectivity | Transport properties |

### Microstructure Images

```
image_t_0.000.img      # t=0 hours
image_t_1.000.img      # t=1 hour
image_t_10.000.img     # t=10 hours
image_t_100.000.img    # t=100 hours
image_t_1000.000.img   # t=1000 hours
```
**Action**: Load these to display 3D evolution or create visualization

### Report File
```
_Report.txt     # Summary statistics, input echo, timing data
```

---

## How VCCTL Should Integrate THAMES

### Phase 1: Input Preparation

```python
def prepare_for_thames(vcctl_operation):
    op_dir = create_operation_directory()
    
    # 1. Copy GEMS databases
    copy(bundled_gems_files, op_dir)
    
    # 2. Generate JSON from VCCTL parameters
    json_params = generate_json(
        temperature = vcctl_operation.temperature,
        duration = vcctl_operation.duration,
        saturated = vcctl_operation.moisture_condition,
        phases = vcctl_operation.mix_design.phases,
    )
    write_json(json_params, f"{op_dir}/simparams.json")
    
    # 3. Convert microstructure
    thames_img = vcctl2thames(vcctl_operation.pimg_path)
    write_thames_img(thames_img, f"{op_dir}/microstructure.img")
    
    # 4. Create stdin input file
    write_input_file(op_dir)
    
    return op_dir
```

### Phase 2: Launch Simulation

```python
def launch_thames(op_dir):
    # Create input.in for stdin
    input_lines = [
        "2",                     # Hydration
        "thames-dat.lst",
        "simparams.json",
        "microstructure.img",
        "operation_results"
    ]
    
    # Launch process
    process = subprocess.Popen(
        [thames_executable],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=op_dir,
        text=True
    )
    
    # Send input via stdin
    process.stdin.writelines([line + "\n" for line in input_lines])
    process.stdin.close()
    
    # Monitor and return process
    return process
```

### Phase 3: Monitor Progress

```python
def monitor_progress(op_dir, operation):
    """Poll output files to estimate progress"""
    
    expected_timesteps = estimate_timesteps(operation.duration)
    
    while process_is_running():
        try:
            csv_data = read_csv(f"{op_dir}/operation_results_dcmoles.csv")
            current_timesteps = len(csv_data)
            progress = (current_timesteps / expected_timesteps) * 100
            
            update_ui_progress(progress)
            time.sleep(5)  # Check every 5 seconds
        except FileNotFoundError:
            # CSV not created yet
            update_ui_status("THAMES initializing...")
            time.sleep(10)
```

### Phase 4: Parse Results

```python
def parse_thames_results(op_dir):
    """Load all results into database"""
    
    results = {
        'phase_volumes': read_csv(f"{op_dir}/_phasevolume.csv"),
        'csh_composition': read_csv(f"{op_dir}/_CSH.csv"),
        'porosity': read_csv(f"{op_dir}/_porosity.csv"),
        'pore_size_dist': read_csv(f"{op_dir}/_psdlin.csv"),
        'final_porosity': float(read_csv(...)[-1]['porosity']),
        'final_csh_volume': float(read_csv(...)[-1]['CSH']),
        'images': glob(f"{op_dir}/image_t_*.img"),
        'csv_files': glob(f"{op_dir}/*_*.csv"),
    }
    
    # Store in database or return
    return results
```

---

## Phase ID Mapping (vcctl2thames.h)

VCCTL must convert its phase IDs to THAMES phase IDs using this table:

```cpp
const int ELECTROLYTE_ID = 0;      // Pore solution (saturated)
const int C3S = 1;                 // Tricalcium silicate
const int C2S = 2;                 // Dicalcium silicate
const int C3A = 3;                 // Tricalcium aluminate
const int C4AF = 4;                // Tetracalcium aluminoferrite
const int K2SO4 = 5;               // Potassium sulfate
const int NA2SO4 = 6;              // Sodium sulfate
const int GYPSUM = 7;              // Gypsum (dihydrate)
const int HEMIHYD = 8;             // Hemihydrate (bassanite)
const int ANHYDRITE = 9;           // Anhydrite
const int SFUME = 10;              // Silica fume
const int INERT = 11;              // Inert material
const int SLAG = 12;               // Slag (GGBFS)
const int INERTAGG = 13;           // Inert aggregate
const int ASG = 14;                // Aluminosilicate glass
const int CH = 19;                 // Portlandite
const int CSH = 20;                // C-S-H
const int C3AH6 = 21;              // C3A hexahydrate
const int ETTR = 22;               // Ettringite
const int AFM = 24;                // Monosulfate
const int FH3 = 25;                // Fe(OH)3
const int POZZCSH = 26;            // Pozzolanic C-S-H
const int SLAGCSH = 27;            // Slag C-S-H
const int CACO3 = 33;              // Limestone (CaCO3)
const int EMPTYP = 55;             // Empty porosity (self-dessication)
// ... 65 phases total
```

---

## Kinetic Models Available

THAMES supports multiple kinetic models for different phases:

### 1. **ParrotKilloh** (Classical C3S hydration)
```
dC3S/dt = -A × f(T) × (1-α)^n × [1 - (Q/K)]^m
```
- Used for: C3S, C2S, C3A, C4AF
- Parameters: Activation energy, pre-exponential factor, reaction orders

### 2. **Pozzolanic** (Supplementary materials)
```
dSCM/dt = -k × [OH⁻] × (1 - fractional reaction)^0.5
```
- Used for: Silica fume, fly ash, slag
- Depends on: Hydroxide ion concentration, particle size

### 3. **Standard** (Generic dissolution)
- User-defined rate expressions
- Flexible for non-standard phases

---

## Common Pitfalls and Solutions

### Problem 1: Conversion from VCCTL to THAMES Phase IDs
**Solution**: Use provided `vcctl2thames` converter tool
```bash
vcctl2thames < input_vcctl.img > output_thames.img
```

### Problem 2: THAMES doesn't output progress during run
**Solution**: Monitor by counting rows in .csv files
```python
# Count lines in dcmoles.csv → estimate progress
timesteps = len(read_csv(csv_file))
progress = timesteps / expected_timesteps * 100
```

### Problem 3: GEMS thermodynamic database mismatch
**Solution**: Use exact GEMS database files matching THAMES version
- Currently: GEMS3K v5.0 (84 dependent components)
- Don't mix versions

### Problem 4: Slow performance (240 minutes for 100×100×100)
**Solution**: 
- Reduce lattice size (100³ is typical, 50³ is 8× faster)
- Reduce simulation duration (100 hours instead of 1000)
- Run on fast CPU (THAMES is single-threaded)

---

## File Size Expectations

| File | Size |
|------|------|
| `.img` microstructure (100×100×100) | ~2-4 MB |
| `simparams.json` | ~20-50 KB |
| GEMS database files (4 total) | ~70 KB |
| `_dcmoles.csv` (1000 timesteps) | ~100-200 KB |
| `_phasevolume.csv` | ~50-100 KB |
| `image_t_*.img` (per snapshot) | ~2-4 MB |
| **Total output** (150 timesteps) | ~500 MB |

---

## Recommended VCCTL Workflow

### User Perspective

1. **Create mix design** (cement, SCM, aggregate)
2. **Generate microstructure** (e.g., using genmic or provided template)
3. **Define hydration operation**:
   - Select microstructure
   - Set temperature (e.g., 298.15 K)
   - Set duration (e.g., 1000 hours)
   - Select moisture condition (sealed/saturated)
4. **Run THAMES** (automatic)
5. **View results**:
   - Phase evolution graphs (from CSV)
   - 3D microstructure snapshots
   - Computed properties (porosity, Ca/Si ratio)

### Backend Implementation

```python
# Operation Type: "THAMESHydration"
class THAMESHydration(Operation):
    # Input parameters
    hydration_operation_id: int        # Parent hydration operation
    temperature: float                 # [K]
    duration: float                    # [hours]
    saturated: bool                    # Moisture condition
    output_frequency: float            # Save every N hours
    
    # Status tracking
    status: OperationStatus
    progress: float                    # 0-100%
    
    # Output files
    operation_folder: Path
    csv_files: List[Path]
    image_files: List[Path]
    
    def run(self):
        # 1. Prepare input files
        # 2. Launch THAMES subprocess
        # 3. Monitor progress
        # 4. Parse results
        # 5. Update database
```

---

## Integration Checklist

- [ ] Bundle GEMS3K database files (4 files, ~70 KB total)
- [ ] Implement `vcctl2thames` phase ID conversion
- [ ] Generate JSON from operation parameters
- [ ] Create input.in file format handler
- [ ] Implement THAMES subprocess launching
- [ ] Implement progress monitoring (poll CSV file row count)
- [ ] CSV parsing (numpy or pandas recommended)
- [ ] Microstructure image loading (PIL or custom)
- [ ] Error handling (THAMES convergence failures, file I/O)
- [ ] Results database storage
- [ ] Results visualization (phase evolution graphs, 3D snapshots)

---

## External Resources

- **THAMES Source**: https://github.com/jwbullard/THAMES
- **GEMS3K**: https://gems.web.psi.ch
- **Output Guide**: `doc/OutputGuide/outputGuide.pdf`
- **Test Cases**: 14 examples in `tests/` directory
- **Build Instructions**: `INSTALL.md`

---

## Summary

THAMES is a powerful thermodynamic hydration simulator that:

✅ **Produces rigorous predictions** via GEMS3K coupling
✅ **Handles complex systems** (multi-SCM, sulfate attack, leaching)
✅ **Provides comprehensive output** (11 CSV files + snapshots)
✅ **Supports reproducible runs** (fixed RNG seed)

But requires:
- **Complex input setup** (JSON + GEMS database)
- **Significant compute time** (5-240 minutes)
- **Custom integration work** (VCCTL must handle file I/O and monitoring)

**Best use case for VCCTL**: Advanced users wanting thermodynamically rigorous predictions beyond simple disrealnew kinetics.


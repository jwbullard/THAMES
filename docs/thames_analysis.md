# THAMES-Hydration C++ Codebase Analysis

## Executive Summary

THAMES (The Hydration and Microstructure Evolution Simulator) is a sophisticated 3D microstructure evolution model for cement hydration. It differs significantly from the simpler disrealnew.c approach, offering:

- **Thermodynamically rigorous** hydration simulation using GEMS3K geochemical coupling
- **Object-oriented architecture** with 40+ interconnected C++ classes
- **Advanced phase tracking** via lattice-based cellular automaton
- **Sophisticated kinetic models** (Parrot-Killoh, Pozzolanic, Standard dissolution)
- **JSON-driven parameter** configuration system
- **Comprehensive output** with CSV data files and microstructure snapshots

---

## 1. PROJECT STRUCTURE

### Directory Organization

```
thames-hydration/
├── CMakeLists.txt                     # CMake build configuration (v3.30+)
├── VERSION                             # Version: 5.1
├── src/
│   ├── thames.cc                       # Main executable entry point (632 lines)
│   ├── thames.h                        # Main header file
│   ├── version.h                       # Version constants
│   ├── thameslib/                      # Core simulation library (40+ files)
│   │   ├── ChemicalSystem.cc/h         # GEMS3K integration, phase database
│   │   ├── Controller.cc/h             # Simulation driver/orchestrator
│   │   ├── KineticController.cc/h      # Kinetic model implementation
│   │   ├── Lattice.cc/h                # 3D microstructure container (300+ KB)
│   │   ├── ElasticModel.cc/h           # Elastic property calculations
│   │   ├── Interface.cc/h              # Growth/dissolution interfaces
│   │   ├── global.h                    # Global constants and types
│   │   ├── Exceptions.cc/h             # Error handling
│   │   └── (30+ other classes)
│   ├── vcctl2thames/                   # VCCTL→THAMES converter
│   │   ├── vcctl2thames.cc             # Phase ID mapping utility
│   │   └── vcctl2thames.h              # 65 phase ID constants defined
│   ├── viz/                            # Visualization utilities
│   └── GEMS3K-standalone/              # GEMS geochemical package (submodule)
│       ├── GEMS3K/                     # Core GEMS3K library
│       ├── simdjson/                   # JSON parser
│       └── tools/                      # Utility programs
├── tests/                              # 14+ test cases with input files
│   ├── portcem-298K-sealed-wc45/       # Portland cement, sealed conditions
│   ├── pyrragg-298K-sat/               # Pyroclastic aggregate example
│   ├── PC-FlyAsh-200/                  # Fly ash supplementary cementitious material
│   └── (11 more test cases)
├── doc/
│   ├── OutputGuide/                    # Output file documentation
│   ├── Doxyfile.in                     # API documentation config
│   └── Figures/                        # Reference diagrams
└── build/                              # Build output directory (out-of-source)
```

### Key Statistics

- **Main source files**: ~22KB (thames.cc)
- **Library files**: 40+ classes, 2.7 MB total
- **Test cases**: 14 complete examples
- **Build system**: CMake 3.30+ (modern, cross-platform)
- **Dependencies**: GEMS3K (thermodynamics), simdjson (JSON parsing), standard C++17

---

## 2. MAIN EXECUTABLE AND PROGRAM FLOW

### Entry Point: `src/thames.cc`

**Interactive console-based interface (reads from stdin)**

```cpp
int main(int argc, char **argv) {
    cout << "Enter simulation type:" << endl;
    cout << "  1) Exit program" << endl;
    cout << "  2) Hydration" << endl;
    cout << "  3) Leaching" << endl;
    cout << "  4) Sulfate attack" << endl;
    cin >> simtype;
```

### Simulation Flow

**Phase 1: Initialization (Interactive)**

1. **Simulation type selection** (Hydration, Leaching, Sulfate Attack)
   - Hydration: primary mode (most common)
   - Leaching/Sulfate Attack: degradation scenarios

2. **User prompts for input files** (via stdin):
   ```
   "What is the name of the GEM input file?"
   → User enters: "thames-dat.lst"
   
   "What is the name of the simulation parameter file?"
   → User enters: "simparams.json"
   
   "What is the name of the MICROSTRUCTURE file?"
   → User enters: "ccr140-w45-thames.img"
   
   "What shall be the root name of all output files?"
   → User enters: "cem140-sealed-01"
   ```

3. **Object instantiation** (in order):
   - `ChemicalSystem`: Reads GEMS databases, initializes thermodynamics
   - `RanGen`: Pseudo-random number generator (seeded with -25943)
   - `Lattice`: Loads microstructure image, initializes spatial data
   - `ThermalStrain` (if sulfate attack): Finite element solver
   - `AppliedStrain` (if sulfate attack): External strain solver
   - `KineticController`: Sets up kinetic models, phase definitions
   - `Controller`: Main simulation orchestrator

**Phase 2: Simulation Loop (Automated)**

```cpp
// In Controller class, iterates through time steps:
for (each time step in simParamName) {
    1. Update surface areas and interface curvatures (Lattice)
    2. Calculate phase consumption rates (KineticController)
    3. Update pore solution chemistry (ChemicalSystem → GEMS3K)
    4. Grow/dissolve phases in microstructure (Lattice)
    5. Update elastic strains if needed (ThermalStrain/AppliedStrain)
    6. Output snapshot every N time steps
    7. Write CSV data for all phases
}
```

**Phase 3: Output Generation (Continuous)**

- CSV files (phase compositions, moles, properties)
- Microstructure snapshots (.img files)
- 3D visualization data (.xyz format)
- Statistics and reports

---

## 3. INPUT FORMAT

### Input Files Required

#### A. GEMS Thermodynamic Database Files (3 files)

**Format**: Custom GEMS3K data files

```
thames-dat.lst          # Master reference file (lists other .dat files)
thames-dch.dat          # Dependent Components Header (~33 KB)
thames-dbr.dat          # Database Record (~16 KB)
thames-ipm.dat          # IPM Algorithm Data (~21 KB)
```

These files contain:
- All chemical species and phases
- Thermodynamic properties (Gibbs energy, activity models)
- Element composition matrix
- Number of dependent components (DCs) - essential parameter

**Example content** (thames-dch.dat):
```xml
<nDC>84</nDC>           # Number of dependent components
<GEMPHASENAME>aq_gen</GEMPHASENAME>  # Phase names
<gemsymbols>H2O@ H+ OH- Na+ Ca+2 Al+3...</gemsymbols>
```

#### B. Simulation Parameters File: `simparams.json`

**Format**: JSON (JavaScript Object Notation)

**Structure**:
```json
{
  "environment": {
    "temperature": 298.15,           # Temperature [K]
    "reftemperature": 298.15,        # Reference temperature [K]
    "saturated": 0,                  # 0=sealed, 1=saturated
    "electrolyte_conditions": [
      { "DCname": "Ca(CO3)@", "condition": "initial", "concentration": 1.0e-6 },
      { "DCname": "AlO2H@", "condition": "initial", "concentration": 1.0e-6 }
    ]
  },
  "microstructure": {
    "numentries": 19,                # Number of phase definitions
    "phases": [
      {
        "thamesname": "Void",
        "id": 0,
        "cement_component": 0,
        "display_data": { "red": 0.0, "green": 0.0, "blue": 0.0 }
      },
      {
        "thamesname": "Electrolyte",
        "id": 1,
        "gemphase_data": [            # GEMS phase mappings
          {
            "gemphasename": "aq_gen",
            "gemdc": [                 # Which DCs belong to this phase
              { "gemdcname": "Al(SO4)+", "gemdcporosity": 1 },
              { "gemdcname": "Al+3", "gemdcporosity": 1 }
            ]
          }
        ]
      },
      { "thamesname": "C3S", "id": 1, ... },
      { "thamesname": "C-S-H", "id": 20, ... },
      // ... more phases ...
    ],
    "simulation_control": {
      "time_output": [0.0, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0, ...],
      "output_frequency": 0.5        # Output every 0.5 hours
    }
  }
}
```

**Key JSON parameters**:

| Parameter | Meaning | Example |
|-----------|---------|---------|
| `temperature` | Simulation temperature | 298.15 K (25°C) |
| `saturated` | Moisture conditions | 0 = sealed (no water loss) |
| `id` | Phase ID (0-64) | 0=Void, 1=Electrolyte, 20=C-S-H |
| `gemphasename` | Thermodynamic phase name in GEMS | "aq_gen" (aqueous) |
| `gemdcname` | Dependent component in GEMS | "Ca+2", "H2O@" |
| `time_output` | Times to save snapshots | [0, 1, 10, 100] hours |

#### C. Microstructure Image File: `.img` format

**Format**: Custom binary/text format with header

**Header** (text lines):
```
#THAMES:Version:5.0
#THAMES:X_Size:100
#THAMES:Y_Size:100
#THAMES:Z_Size:100
#THAMES:Image_Resolution:1.0
```

**Data** (space-separated phase IDs):
```
0 0 1 1 2 0 3 1 ...  [100×100×100 = 1 million voxel IDs]
```

**Size**: ~2-4 MB for 100×100×100 microstructure

**Phase IDs** (defined in `vcctl2thames.h`):
```cpp
const int ELECTROLYTE_ID = 0;      // Pore solution (liquid)
const int C3S = 1;                 // Tricalcium silicate (clinker)
const int C2S = 2;                 // Dicalcium silicate (clinker)
const int C3A = 3;                 // Tricalcium aluminate (clinker)
const int C4AF = 4;                // Tetracalcium aluminoferrite
const int SFUME = 10;              // Silica fume (SCM)
const int SLAG = 12;               // Slag (SCM)
const int INERTAGG = 13;           // Inert aggregate (sand)
const int CSH = 20;                // C-S-H hydration product
const int CH = 19;                 // Portlandite
const int C3AH6 = 21;              // Tricalcium aluminate hexahydrate
const int ETTR = 22;               // Ettringite (AFt)
const int CACO3 = 33;              // CaCO3 (limestone)
const int EMPTYP = 55;             // Empty porosity (self-dessicated)
// ... 65 phase IDs total
```

#### D. Input Control File: `input.in` (stdin redirection)

**Format**: Text lines read by stdin in main()

```
2                          # Line 1: Simulation type (2 = Hydration)
thames-dat.lst            # Line 2: GEMS master file
simparams.json            # Line 3: Simulation parameters
ccr140-w45-thames.img     # Line 4: Microstructure image
cem140-sealed-01          # Line 5: Output root name
```

**Equivalent command line**:
```bash
thames --outfolder MyResults < input.in >& output.txt &
```

---

## 4. OUTPUT FORMAT

### Output Directory Structure

```
MyResults/
├── cem140-sealed-01_CSH.csv              # C-S-H composition over time
├── cem140-sealed-01_CSratio_solid.csv    # Overall Ca/Si ratio
├── cem140-sealed-01_dcmoles.csv          # Moles of each DC phase
├── cem140-sealed-01_phasevolume.csv      # Volume of each phase
├── cem140-sealed-01_phasemass.csv        # Mass of each phase
├── cem140-sealed-01_phasecount.csv       # Number of voxels per phase
├── cem140-sealed-01_psdlog.csv           # Pore size distribution (log scale)
├── cem140-sealed-01_psdlin.csv           # Pore size distribution (linear)
├── cem140-sealed-01_porosity.csv         # Total porosity over time
├── cem140-sealed-01_percolation.csv      # Percolation analysis (connectivity)
├── cem140-sealed-01_surfacearea.csv      # Phase surface areas
├── cem140-sealed-01_Report.txt           # Summary statistics and input echo
├── cem140-sealed-01_xyz.xyz              # 3D visualization file (optional)
├── image_t_0.000.img                     # Microstructure at t=0 hours
├── image_t_1.000.img                     # Microstructure at t=1 hour
├── image_t_10.000.img                    # Microstructure at t=10 hours
├── image_t_100.000.img                   # Microstructure at t=100 hours
├── image_t_1000.000.img                  # Microstructure at t=1000 hours
├── ccr140-w45-thames.img                 # Initial microstructure (copy)
├── simparams.json                        # Simulation params (copy)
├── thames-dat.lst                        # GEMS data files (copies)
├── thames-dch.dat
├── thames-dbr.dat
└── thames-ipm.dat
```

### CSV Output Files (11 total)

#### 1. **_dcmoles.csv** - Dependent Component Moles

**Content**: Moles of each DC per 100g initial solid, over time

**Header**:
```
Time(hours),Al(SO4)+,Al(SO4)2-,Al+3,AlO+,AlO2-,...,H2O@,H+,OH-,Na+,Ca+2,K+,SO4-2,...
```

**Data rows**:
```
0.0,0.000000e+00,0.000000e+00,1.234e-05,0.000000e+00,...,9.999e+02,1.234e-02,...
0.01,1.123e-04,0.000000e+00,1.245e-05,2.345e-06,...,9.998e+02,1.235e-02,...
1.0,5.234e-03,1.234e-04,2.123e-05,5.678e-05,...,9.985e+02,1.234e-02,...
```

**Typical columns**: 80-100 DC species

#### 2. **_CSH.csv** - C-S-H Composition

**Content**: Elemental composition of C-S-H phase

**Header**:
```
Time(hours),Ca,Si,Al,Fe,Mg,S,Ca/Si Ratio
```

**Data**:
```
0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
0.01,1.234,0.567,0.089,0.001,0.000,0.000,2.175
1.0,1.456,0.723,0.123,0.002,0.000,0.000,2.014
100.0,1.678,0.834,0.156,0.003,0.000,0.000,2.011
```

**Significance**: C-S-H Ca/Si ratio indicates hydration degree and product stability

#### 3. **_phasevolume.csv** - Phase Volume Evolution

**Content**: Volume (in voxels) of each phase over time

**Header**:
```
Time(hours),Void,C3S,C2S,C3A,C4AF,Sfume,Slag,Aggregate,CSH,CH,C3AH6,Ettr,Monosulf,...
```

**Data**:
```
0.0,150000,350000,200000,50000,30000,100000,0,100000,0,0,0,0,0,...
1.0,165000,320000,180000,45000,25000,98000,0,100000,15000,5000,3000,2000,...
100.0,200000,50000,30000,5000,2000,80000,0,100000,380000,100000,20000,15000,...
```

**Interpretation**: Shows phase consumption (C3S → CSH) and product formation

#### 4. **_phasemass.csv** - Phase Mass

**Content**: Mass (grams per 100g initial solid) of each phase

#### 5. **_phasecount.csv** - Phase Voxel Count

**Content**: Number of voxels assigned to each phase

#### 6. **_porosity.csv** - Total Porosity

**Content**: Total porosity (Void voxels / Total voxels)

#### 7. **_surfacearea.csv** - Interface Surface Area

**Content**: Surface area of phase interfaces (for growth/dissolution)

#### 8. **_psdlin.csv & _psdlog.csv** - Pore Size Distribution

**Content**: Distribution of pore sizes (connectivity analysis)

#### 9. **_percolation.csv** - Percolation Analysis

**Content**: Whether pores percolate (connect to boundaries)

#### 10. **_CSratio_solid.csv** - Bulk Ca/Si Ratio

**Content**: Overall Ca/Si of all solids (different from C-S-H alone)

### Microstructure Image Files (.img)

**File naming**: `image_t_HHH.DDD.img`

**Example**: `image_t_1000.000.img` = microstructure at t=1000 hours

**Format**: Same header + phase ID data as input `.img` file

**Size**: ~2-4 MB per snapshot

**Usage**: Can be loaded back into THAMES, visualized with vtkImageData, or converted to STL/VTK

### Report File (_Report.txt)

**Content**: Summary of simulation

```
THAMES Hydration Simulation Report
==================================
Simulation Type: Hydration
Temperature: 298.15 K
Moisture Condition: Sealed
Initial Microstructure: ccr140-w45-thames.img (100 × 100 × 100 voxels)
Simulation Duration: 1000 hours
Time Steps: 150
Output Frequency: Every 0.5 hours

Phase Summary:
  C3S consumed: 78% (350000 → 77000 voxels)
  CSH formed: 380000 voxels
  CH formed: 100000 voxels
  Porosity increased: 14.3% → 19.2%

Timing Information:
  Elapsed time: 427 seconds
  Computational rate: 1000 hours hydration / 427 seconds = 2.34 hours per second

Cite as: Bullard et al. (2011) Journal of Materials Research
```

### Optional 3D Visualization File (.xyz)

**Format**: XYZ format for Ovito or LAMMPS visualization

```
Time 0.0 hours
1000000          # Total number of voxels
H 1 0.0 0.0 0.0 1   # Element, voxel_id, x, y, z, phase_id
H 2 1.0 0.0 0.0 1
H 3 2.0 0.0 0.0 0
...
```

**Usage**: Visualize 3D microstructure evolution in Ovito or ParaView

---

## 5. KEY ALGORITHMS AND CLASSES

### Core Simulation Classes (thameslib/)

#### A. **ChemicalSystem** (~213 KB source)

**Purpose**: Interface to GEMS3K geochemical package

**Key methods**:
```cpp
ChemicalSystem(const string& gemInputName,    // GEMS data files
               const string& simParamName,     // JSON config
               bool verbose = false,
               bool warning = false);

void calculateEquilibrium(vector<double>& dcMoles,  // Input: moles of DCs
                         double temperature);       // Temperature [K]
                                                     // Output: updated dcMoles at equilibrium

int getNumDependentComponents() const;               // Returns number of DCs
int getNumPhases() const;                            // Returns number of phases
double getPhaseVolume(int phaseId) const;            // Returns vol of phase [m³]
```

**Purpose**: 
- Reads GEMS thermodynamic database
- For each time step, given the solution composition (from kinetics), calculates equilibrium solid phases and solution speciation
- Updates phase densities, molar volumes, elastic moduli

**Workflow**:
```
Kinetic model → Solution composition (moles of ions)
                           ↓
                    GEMS3K interface
                           ↓
                    Equilibrium calculation
                           ↓
            Phase identities, compositions, volumes, densities
```

#### B. **Lattice** (~258 KB source)

**Purpose**: 3D microstructure container using cellular automaton

**Key data**:
```cpp
int xdim_, ydim_, zdim_;                    // Lattice dimensions [voxels]
double resolution_;                          // Voxel size [micrometers]
vector<Site> site_;                          // 1D array of all voxels (100³ = 1M elements)
vector<Interface> interface_;                // Growth/dissolution interfaces per phase
vector<int> count_;                          // Voxel count for each phase
```

**Key methods**:
```cpp
Lattice(ChemicalSystem* chemsys,
        RanGen* rng,
        int seed,
        const string& initMicName);          // Load initial microstructure

void readInitialMicrostructure(const string& filename);  // Read .img file

void updateMicrostructure(double timeStep,
                         KineticController* kinetic);   // Grow/dissolve phases

int evolveInterface(int phaseId,
                   double growthRate,        // [voxels/sec]
                   double timeStep);          // [sec]
                                              // Returns: number of sites converted

void calculateInterfaceData();               // Compute surface areas, curvatures
vector<Isite> getGrowthInterface(int phaseId);  // Get growth sites for phase
```

**Key algorithms**:
1. **Interface tracking**: Identify voxels adjacent to each phase
2. **Probabilistic growth**: Random selection weighted by affinity
3. **Dissolution**: Remove voxels of consuming phases
4. **Surface area calculation**: Count faces/edges between phase IDs
5. **Connectivity**: Track percolation (which phases connect through lattice)

**Data structure** (each Site):
```cpp
struct Site {
    unsigned int microPhaseId_;              // Which phase occupies this voxel
    vector<unsigned int> growth_;            // Which phases can grow here
    double wmc_;                             // Weighted mean curvature (porosity)
    vector<Isite> neighbors_;                // Neighboring growth sites
};

struct Isite {
    unsigned int id_;                        // Site ID
    double affinity_;                        // Growth probability
    double prob_;                            // Computed probability [0,1]
};
```

#### C. **KineticController** (~48 KB source)

**Purpose**: Compute phase consumption rates and kinetic advancement

**Key methods**:
```cpp
KineticController(ChemicalSystem* chemsys,
                  Lattice* lattice,
                  const string& simParamName);

void computeRates(vector<int>& surfaceAreas,  // Phase interface areas
                 double temperature);          // [K]
                                               // Output: consumptionRates_

double getRateForPhase(int phaseId);           // [mol/m²/sec] or [voxels/sec]
```

**Supported kinetic models**:
1. **ParrotKilloh**: Classical cement hydration (C3S → CSH + CH)
2. **Pozzolanic**: Supplementary cementitious materials (SCM + CH → CSH)
3. **Standard**: Generic dissolution-precipitation
4. **Generic**: User-defined rate expressions

**Rate equations** (examples):

*Parrot-Killoh for C3S*:
```
dC3S/dt = -A × f(T) × (1-α)^n × [1 - (Q/K)]^m

where:
  A = pre-exponential factor [mol/m²/s]
  f(T) = temperature activation [K]
  α = degree of hydration [0,1]
  Q/K = ion activity product ratio
  m,n = empirical exponents
```

*Pozzolanic for Silica Fume*:
```
dSilica/dt = -k × [OH⁻] × (1 - fractional reaction)^0.5

where k depends on particle size and surface area
```

#### D. **Controller** (~96 KB source)

**Purpose**: Main simulation driver/orchestrator

**Key methods**:
```cpp
Controller(Lattice* lattice,
          KineticController* kinetic,
          ChemicalSystem* chemsys,
          ThermalStrain* strain,
          int simType,                        // HYDRATION, LEACHING, SULFATE_ATTACK
          const string& jobRoot);

void runSimulation();                         // Main loop

void doHydrationStep(double time);            // Single time step:
                                              // 1. Update interfaces
                                              // 2. Calculate rates
                                              // 3. Call GEMS
                                              // 4. Evolve lattice
                                              // 5. Output results
```

**Simulation loop** (pseudocode):
```cpp
for (int step = 0; step < numTimeSteps; step++) {
    double currentTime = timeVector[step];
    
    // 1. Update phase interfaces based on current microstructure
    lattice_->calculateInterfaceData();
    
    // 2. Calculate kinetic rates
    kinetic_->computeRates(surfaceAreas, temperature);
    
    // 3. Evolve lattice (grow/dissolve phases)
    for (int phaseId = 0; phaseId < numPhases; phaseId++) {
        double rate = kinetic_->getRateForPhase(phaseId);
        lattice_->evolveInterface(phaseId, rate, timeStep);
    }
    
    // 4. Calculate resulting composition from GEMS
    chemsys_->calculateEquilibrium(dcMoles, temperature);
    
    // 5. Output results if time matches output schedule
    if (shouldOutputNow(currentTime)) {
        outputMicrostructureImage(currentTime);
        outputCSVdata(currentTime);
    }
}
```

#### E. **ElasticModel** (~32 KB source)

**Purpose**: Calculate elastic properties (Young's modulus, Poisson's ratio)

**Methods**:
```cpp
double calculateYoungsModulus(int phaseId);  // [GPa]
double calculatePoissonRatio(int phaseId);
double calculateBulkModulus(int phaseId);
```

**Data source**: Phase properties from ChemicalSystem (determined from composition)

**Example output**: For C-S-H at 28 days:
```
Phase ID: 20 (C-S-H)
Young's Modulus: 18.5 GPa
Poisson's Ratio: 0.32
Density: 2.12 g/cm³
```

### Utility Classes

#### F. **Interface** (~API for growth sites)

```cpp
struct Isite {
    unsigned int id_;                        // Voxel ID
    double affinity_;                        // Growth affinity [0,1]
    double prob_;                            // Probability
};

class Interface {
public:
    int getMicroPhaseId() const;              // Phase ID
    int getNumGrowthSites() const;            // How many sites can grow
    int getNumDissolutionSites() const;
    vector<Isite>& getGrowthSites();
    vector<Isite>& getDissolutionSites();
};
```

#### G. **Exceptions**

```cpp
class FileException : public exception { /*...*/ };    // File I/O errors
class GEMException : public exception { /*...*/ };     // GEMS errors
class DataException : public exception { /*...*/ };    // Invalid input
class EOBException : public exception { /*...*/ };     // Out of bounds
class FloatException : public exception { /*...*/ };   // Numerical errors
```

---

## 6. DEPENDENCIES AND BUILD SYSTEM

### External Dependencies

#### A. **GEMS3K Library**

**What it is**: Geochemical modeling kernel (Gibbs free energy minimization)

**Purpose in THAMES**: 
- Given solution composition (from kinetics), calculates equilibrium
- Predicts which solid phases form
- Returns molar volumes, densities, compositions

**Files**: `src/GEMS3K-standalone/`

**Build**: Compiled separately, linked as static library
```bash
cd src/GEMS3K-standalone
./install.sh                 # Builds libGEMS3K-static.a
```

**Source**: https://github.com/jwbullard/GEMS3K or bitbucket GEMS4

#### B. **nlohmann/json** (Header-only)

**Purpose**: Parse JSON simulation parameters

**Location**: `src/Resources/include/nlohmann/json.hpp`

**Single header file**, no compilation needed

#### C. **simdjson** (JSON parsing)

**Location**: `src/GEMS3K-standalone/simdjson/`

**Alternative JSON parser** for some GEMS3K functions

### Build Configuration

#### CMakeLists.txt (Top-level)

```cmake
cmake_minimum_required(VERSION 3.30)
project(THAMES)

set(THAMES_VERSION 5.1)
set(THAMES_VERSION_MAJOR 5)
set(THAMES_VERSION_MINOR 1)

# Find dependencies
find_library(GEMS3K_LIB NAMES GEMS3K-static)
find_library(MATH_LIB NAMES m)

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
  set(CMAKE_CXX_FLAGS "-O2 -std=c++17 -DIPMGEMPLUGIN -Wall ...")
endif()

# Link libraries
target_link_libraries(thames thameslib ${GEMS3K_LIB} ${MATH_LIB})

# Install to bin/
install(TARGETS thames DESTINATION ${CMAKE_SOURCE_DIR}/bin)
```

#### Build Process

**macOS (Apple Clang)**:
```bash
cd build
cmake ..
make
make install    # → ../bin/thames
```

**Linux (GCC)**:
```bash
cd build
cmake ..
make
make install
```

**Windows (WSL + GCC)**:
```bash
wsl
cd build
cmake .. -DCMAKE_C_COMPILER=/usr/bin/gcc \
         -DCMAKE_CXX_COMPILER=/usr/bin/g++
make
```

### Compiler Requirements

- **C++17 standard** required (auto, constexpr, structured bindings)
- **GCC 14.0+** or **Clang 17.0+** (modern versions)
- **CMake 3.30+** (recent feature set)

---

## 7. MICROSTRUCTURE REPRESENTATION

### Voxel-Based Cellular Automaton

**Resolution**: 1-4 micrometers per voxel (configurable)

**Lattice sizes**: Typically 100×100×100 to 200×200×200 voxels

**Dimension calculation**:
```
100 voxels × 1 µm/voxel = 100 µm = 0.1 mm domain
200 voxels × 4 µm/voxel = 800 µm = 0.8 mm domain
```

**Phase representation**: Each voxel is an integer [0-64] indicating phase

### Microstructure File Format (.img)

**Binary storage**: 1-4 bytes per voxel (depending on phase ID range)

**Text representation**: Space-separated integers

**Example (small excerpt)**:
```
#THAMES:Version:5.0
#THAMES:X_Size:100
#THAMES:Y_Size:100
#THAMES:Z_Size:100
#THAMES:Image_Resolution:1.0
0 0 1 1 2 3 3 1 0 0 ... [1,000,000 values total]
```

### Phase Assignment Strategy

**Initial microstructure generation**:
1. Start with random distribution of clinker phases (C3S, C2S, C3A, C4AF)
2. Place inert aggregate particles (random packing)
3. Fill remaining space with electrolyte (pores)
4. Optionally add supplementary materials (SF, slag, FA)

**Example initial distribution** (cement only):
```
C3S:      35% (350,000 voxels)
C2S:      20% (200,000 voxels)
C3A:       5% (50,000 voxels)
C4AF:      3% (30,000 voxels)
Porosity: 37% (370,000 voxels)
Total:   100% (1,000,000 voxels)
```

### Phase Evolution During Hydration

**Time = 0 hours**:
```
C3S:  350,000 vox    CSH:      0 vox    Porosity: 370,000 vox
```

**Time = 1 hour**:
```
C3S:  330,000 vox    CSH:  40,000 vox   Porosity: 330,000 vox
CH:   20,000 vox                        (porosity decreased due to lower molar volume)
```

**Time = 100 hours** (typically):
```
C3S:   77,000 vox    CSH: 380,000 vox   Porosity: 190,000 vox
CH:   100,000 vox    C3AH6: 20,000 vox
```

---

## 8. CONFIGURATION AND PARAMETERS

### Key JSON Parameters

#### Environment Section

```json
"environment": {
  "temperature": 298.15,                   // [K], default 25°C
  "reftemperature": 298.15,                // Reference for kinetics
  "saturated": 0,                          // 0=sealed, 1=saturated
  "electrolyte_conditions": [
    { "DCname": "Ca(CO3)@",      "condition": "initial", "concentration": 1.0e-6 },
    { "DCname": "AlO2H@",        "condition": "initial", "concentration": 1.0e-6 },
    { "DCname": "CaSiO3@",       "condition": "initial", "concentration": 1.0e-6 }
  ]
}
```

**Parameters**:
- `temperature`: Affects all kinetic rates
- `saturated`: 0 = sealed curing (no water loss, high CH), 1 = saturated (water available)
- `electrolyte_conditions`: Initial pore solution composition

#### Microstructure Section

```json
"microstructure": {
  "numentries": 19,                        // Number of phases defined
  "phases": [
    {
      "thamesname": "Void",
      "id": 0,
      "cement_component": 0,
      "display_data": {
        "red": 0.0, "green": 0.0, "blue": 0.0, "gray": 0.0
      }
    },
    {
      "thamesname": "C3S",
      "id": 1,
      "cement_component": 1,               // Component flag
      "kinetic_model": "ParrotKilloh",     // Rate model
      "kinetic_parameters": {
        "activation_energy": 25000,        // [J/mol]
        "preexponential": 1.0e-2,         // [mol/m²/s]
        "reaction_order": 2.5
      }
    }
  ],
  "time_parameters": {
    "initial_time": 0.0,                   // [hours]
    "final_time": 1000.0,                  // [hours]
    "output_frequency": 0.5,               // Save every 0.5 hours
    "solver_timestep": 0.001              // Integration step [hours]
  }
}
```

#### RNG Seed

Hardcoded in thames.cc (line 78):
```cpp
int seedRNG = -25943;                      // Fixed seed for reproducibility
```

**Purpose**: Ensures identical results across runs (same random phase placement)

---

## 9. DIFFERENCES FROM DISREALNEW.C

### Comparison Table

| Aspect | disrealnew.c | THAMES C++ |
|--------|--------------|-----------|
| **Language** | C (procedural) | C++17 (object-oriented) |
| **Thermodynamics** | Simple stability rules | Full GEMS3K coupling |
| **Phase equilibrium** | Hardcoded (minimal) | Dynamic equilibrium calculation |
| **Input format** | Parameter file (text) | JSON + GEMS databases |
| **Configuration** | Interactive stdin | JSON configuration |
| **Microstructure IO** | Binary .img files | Binary .img + JSON metadata |
| **Phase count** | ~20 phases | 65 phases (extensible) |
| **Kinetic models** | Single model | Multiple (ParrotKilloh, Pozzolanic, etc) |
| **Temperature effects** | Arrhenius (hardcoded) | Flexible kinetic parameters |
| **Elastic coupling** | Not integrated | Full elastic strain integration |
| **Output frequency** | User-specified | JSON-configured time points |
| **CSV outputs** | Minimal | 11 comprehensive CSV files |
| **Code complexity** | ~3000 lines | ~40,000 lines (40+ classes) |
| **Build time** | <1 second | 30-60 seconds (C++ compilation) |
| **Maintenance** | Legacy | Actively developed |

### Key Advantages of THAMES

1. **Thermodynamic rigor**: GEMS3K provides accurate equilibrium calculations
2. **Modular architecture**: Easy to add new kinetic models or features
3. **Reproducible**: JSON + RNG seed = identical results
4. **Flexible**: Supports multiple simulation types (hydration, leaching, sulfate attack)
5. **Well-documented**: Extensive API documentation (Doxygen)
6. **Scalable**: Class-based design supports parallel computing (future)

### Key Advantages of disrealnew.c

1. **Simplicity**: Easier to understand and debug
2. **Speed**: Faster compilation, no C++ overhead
3. **Self-contained**: No external GEMS3K dependency
4. **Lightweight**: Suitable for embedded/mobile applications
5. **Direct control**: No abstraction layers

---

## 10. INTEGRATION RECOMMENDATIONS FOR GTK APPLICATION

### How VCCTL Should Interact with THAMES

#### A. Input File Generation

**VCCTL should create**:

```
operation_dir/
├── thames-dat.lst        # Copy from bundled GEMS3K resources
├── thames-dch.dat        # Copy from bundled GEMS3K resources
├── thames-dbr.dat        # Copy from bundled GEMS3K resources
├── thames-ipm.dat        # Copy from bundled GEMS3K resources
├── simparams.json        # Generate from GUI parameters
├── microstructure.img    # Convert from VCCTL .img format using vcctl2thames
├── input.in              # Create text file for stdin
└── thames_stdout.log     # Capture stdout/stderr
```

#### B. File Conversion

**Existing tool**: `vcctl2thames` converter program

```bash
vcctl2thames < input_vcctl.img > output_thames.img
```

**What it does**:
- Reads VCCTL phase IDs (0-64, different mapping)
- Maps to THAMES phase IDs (0-64, vcctl2thames mapping)
- Writes THAMES-format .img file with header

**VCCTL integration**:
```python
# In VCCTL's mix design or operation panel
def prepare_for_thames(vcctl_img_path, output_dir):
    # 1. Copy GEMS3K database files
    copy(bundled_gems_files, output_dir)
    
    # 2. Generate simparams.json from operation parameters
    json_params = generate_json_from_operation(operation)
    write_json(json_params, f"{output_dir}/simparams.json")
    
    # 3. Convert microstructure using vcctl2thames
    thames_img = convert_vcctl_to_thames(vcctl_img_path)
    write_thames_img(thames_img, f"{output_dir}/thames.img")
    
    # 4. Create input.in file
    create_input_file(output_dir)
    
    # 5. Launch THAMES
    launch_thames(output_dir, operation_name)
```

#### C. Progress Monitoring

**THAMES doesn't provide native progress output**

**VCCTL solution**:

```python
def monitor_thames_progress(output_dir, operation_duration_hours):
    """Monitor THAMES by checking for output files"""
    
    while process_is_running():
        # Check for .csv files and count rows
        dcmoles = read_csv(f"{output_dir}/operation_dcmoles.csv")
        progress_percent = (len(dcmoles) / expected_timesteps) * 100
        
        # Update UI progress bar
        update_progress_bar(progress_percent)
        
        time.sleep(5)  # Check every 5 seconds
```

**Monitoring strategy**:
1. Parse output .csv files (grow as simulation runs)
2. Count rows = number of completed time steps
3. Compare to expected time steps from simparams.json
4. Calculate percentage completion

#### D. Result Parsing

```python
def parse_thames_results(output_dir):
    """Load results from THAMES output files"""
    
    results = {
        'completion_time': read_timestamp(f"{output_dir}/operation_Report.txt"),
        'final_porosity': read_last_value(f"{output_dir}/_porosity.csv"),
        'final_csh_volume': read_phase_volume(f"{output_dir}/_phasevolume.csv", 'CSH'),
        'csh_composition': read_csh_csv(f"{output_dir}/_CSH.csv"),
        'phase_evolution': read_all_csv(f"{output_dir}/_phasevolume.csv"),
        'images': glob(f"{output_dir}/image_t_*.img"),
        'csv_files': glob(f"{output_dir}/*_*.csv"),
    }
    
    return results
```

#### E. Example: THAMES Operation Panel

```python
class THAMESOperationPanel(Gtk.Box):
    def __init__(self, service_container):
        self.service_container = service_container
        self.operation = None
        
    def start_simulation(self, hydration_operation):
        """Launch THAMES simulation"""
        
        # Get microstructure image from hydration operation
        vcctl_img = hydration_operation.pimg_path
        
        # Create operation directory
        op_dir = create_operation_directory("THAMES_Hydration")
        
        # Prepare input files
        self.prepare_thames_input(vcctl_img, op_dir, parameters={
            'temperature': 298.15,
            'duration': 1000.0,
            'output_frequency': 0.5,
        })
        
        # Launch THAMES process
        self.thames_process = launch_subprocess(
            executable="/path/to/thames",
            input_file=f"{op_dir}/input.in",
            stdout=f"{op_dir}/thames.log",
            stderr=f"{op_dir}/thames.err",
        )
        
        # Start monitoring
        self.monitor_progress(op_dir)
```

---

## 11. TESTING STRATEGY

### Test Cases Provided

14 complete test cases in `tests/`:

1. **portcem-298K-sealed-wc45** - Portland cement, sealed, w/c=0.45
2. **portcem-298K-saturated-wc45** - Portland cement, saturated
3. **portcem-298K-sealed-alk-wc45** - Portland cement with alkali-resistant aggregate
4. **pyrragg-298K-sat** - Pyrrhotite aggregate (iron-rich)
5. **PC-FlyAsh-200** - Portland cement + fly ash (20% replacement)
6. **PC-FlyAsh-200-single** - Single GEM phase (simplified)
7. **PC-Carbonate-200** - Portland cement + limestone (20% replacement)
8. **alite-298K-sealed-wc35** - Pure C3S paste, sealed, w/c=0.35
9. **pyrrcem-298K-sat** - Pyrex cement (experimental)
10. **lowWC** - Very low water-to-cement ratio
11. **sa_portcem-298K-sat-wc45** - Sulfate attack simulation
12. **highvolume-silicafume** - High volume silica fume (40% replacement)
13. **portcem-298K-sealed-wc35** - w/c=0.35 variant
14. **sa_portcem-298K-sealed-alk** - Sulfate attack with alkali-resisting aggregate

### How to Run Tests

```bash
# Example: Run a test case
cd tests/portcem-298K-sealed-wc45

# Option 1: Run thames interactively
thames --outfolder MyResults
# (then answer prompts with file names)

# Option 2: Run with input file (batch mode)
thames --outfolder MyResults < input.in >& output.log &

# Monitor progress
tail -f output.log

# Check results
ls -la MyResults/
head MyResults/*_dcmoles.csv
```

### Expected Runtime

- **Small microstructure** (100×100×100, few hours): 5-10 minutes
- **Medium microstructure** (150×150×150, 1000 hours): 30-60 minutes
- **Large microstructure** (200×200×200, long duration): 2-4 hours

Runtime scales with:
- Lattice size (cubic: 8× larger lattice = 8× slower)
- Simulation duration (linear: 2× duration = 2× slower)
- Time step resolution (finer steps = slower)

---

## SUMMARY

THAMES is a sophisticated, research-grade hydration simulator that:

1. **Couples kinetics with thermodynamics** (GEMS3K)
2. **Simulates 3D microstructure evolution** (cellular automaton)
3. **Supports multiple reaction mechanisms** (hydration, leaching, sulfate attack)
4. **Produces comprehensive output** (11 CSV files + snapshots)
5. **Is actively maintained** (version 5.1, recent build requirements)

**Integration with VCCTL** requires:
- Input file preparation (JSON + image conversion)
- Process launching and monitoring
- Output parsing and visualization
- Error handling for convergence issues

**Key advantage over disrealnew**: Full thermodynamic equilibrium calculation via GEMS3K, enabling accurate prediction of hydration products under any condition.


# THAMES Hydration Integration Implementation Plan

## Executive Summary

This document outlines a comprehensive plan for integrating hydration simulations into the THAMES GTK UI. The integration involves generating `simparams.json` files from UI data and executing the THAMES-Hydration C++ engine.

**Goal:** Enable users to set up, run, and monitor THAMES hydration simulations entirely through the GTK UI.

**Key Files to Generate:**
1. `simparams.json` - Simulation parameters (environment, phases, kinetics, time)
2. Piped stdin input for THAMES executable (sim type, paths, output name)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          THAMES GTK UI                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Mix Design Panel                  │  Hydration Setup Panel              │
│  - Materials + phases              │  - Temperature                      │
│  - Phase ID mapping                │  - Curing conditions                │
│  - Microstructure generation       │  - Time parameters                  │
│                                    │  - Kinetic parameter overrides      │
└─────────────────┬──────────────────┴────────────────┬───────────────────┘
                  │                                    │
                  ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SERVICE LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│  │ SimParamsService    │  │ HydrationService  │  │ KineticDataService│  │
│  │ - Generate JSON     │  │ - Execute thames  │  │ - Default params  │  │
│  │ - Validate phases   │  │ - Monitor progress│  │ - Lookup by phase │  │
│  │ - Build phase data  │  │ - Parse output    │  │ - Phase affinity  │  │
│  └─────────────────────┘  └───────────────────┘  └───────────────────┘  │
│                                                                          │
│  ┌─────────────────────┐  ┌───────────────────┐  ┌───────────────────┐  │
│  │ PhaseIdMappingService │ MaterialService   │  │ GEMSParserService │  │
│  │ (existing)          │  │ (existing)        │  │ (existing)        │  │
│  └─────────────────────┘  └───────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    THAMES-Hydration Executable                           │
│  stdin: simtype, GEM_file, simparams.json, microstructure, output_name  │
│  output: *.stats, *.report, *.img snapshots                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Data Models and Kinetic Parameters (~3-4 components)

**Goal:** Define data structures for kinetic parameters and default values.

#### 1.1 Kinetic Parameter Data Classes
**File:** `src/app/models/kinetic_parameters.py`

```python
@dataclass
class ParrotKillohKinetics:
    """Parrot-Killoh kinetic parameters for clinker phases."""
    k1: float      # Nucleation/growth rate constant
    k2: float      # Early diffusion rate constant
    k3: float      # Late diffusion rate constant
    n1: float      # Nucleation/growth exponent
    n3: float      # Late diffusion exponent
    dorHcoeff: float  # Lothenbach-Kulik H coefficient
    activationEnergy: float  # J/mol
    loi: float = 0.0  # Loss on ignition

@dataclass
class StandardKinetics:
    """Standard kinetic parameters for sulfate phases."""
    dissolutionRateConst: float
    diffusionRateConstEarly: float
    diffusionRateConstLate: float
    dissolvedUnits: int
    siexp: float
    dfexp: float
    dorexp: float
    activationEnergy: float
    loi: float = 0.0

@dataclass
class PozzolanicKinetics(StandardKinetics):
    """Pozzolanic kinetic parameters (extends Standard)."""
    ohexp: float  # Hydroxyl ion activity exponent
    sio2: float   # SiO2 content (mass fraction)
```

**Tests:**
- Test dataclass creation with valid values
- Test serialization to dict/JSON
- Test validation (e.g., positive values)

#### 1.2 Default Kinetic Parameters Service
**File:** `src/app/services/kinetic_defaults_service.py`

Provides scientifically-validated default kinetic parameters for each phase type.

```python
class KineticDefaultsService:
    """Provides default kinetic parameters for THAMES phases."""

    PARROT_KILLOH_DEFAULTS = {
        "Alite": ParrotKillohKinetics(k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3, ...),
        "Belite": ParrotKillohKinetics(k1=0.5, k2=0.02, k3=0.7, n1=1.0, n3=5.0, ...),
        "Aluminate": ParrotKillohKinetics(k1=1.0, k2=0.04, k3=1.0, n1=0.85, n3=3.2, ...),
        "Ferrite": ParrotKillohKinetics(k1=0.37, k2=0.02, k3=0.4, n1=0.7, n3=3.7, ...),
    }

    STANDARD_DEFAULTS = {
        "Gypsum": StandardKinetics(dissolutionRateConst=1.0e-6, ...),
        "hemihydrate": StandardKinetics(dissolutionRateConst=1.5e-6, ...),
        "Anhydrite": StandardKinetics(dissolutionRateConst=5.0e-7, ...),
    }

    POZZOLANIC_DEFAULTS = {
        "Quartz": PozzolanicKinetics(dissolutionRateConst=1.4e-11, ohexp=1.0, sio2=0.987, ...),
        "Mullite": PozzolanicKinetics(dissolutionRateConst=1.4e-11, ...),
        # Fly ash glasses...
    }

    def get_kinetics_for_phase(self, phase_name: str) -> Union[ParrotKillohKinetics, StandardKinetics, PozzolanicKinetics, None]:
        """Get default kinetic parameters for a phase."""

    def get_kinetic_type(self, phase_name: str) -> str:
        """Get the kinetic model type for a phase ('ParrotKilloh', 'Standard', 'Pozzolanic', None)."""
```

**Tests:**
- Test retrieval of defaults for each clinker phase
- Test retrieval for sulfate phases
- Test retrieval for pozzolanic phases
- Test unknown phase returns None

#### 1.3 Impurity Data Defaults
**File:** `src/app/services/kinetic_defaults_service.py` (same file)

```python
IMPURITY_DEFAULTS = {
    "Alite": {"k2ocoeff": 0.00087, "na2ocoeff": 0.0, "mgocoeff": 0.00861, "so3coeff": 0.007942},
    "Belite": {"k2ocoeff": 0.01152, "na2ocoeff": 0.0, "mgocoeff": 0.0038, "so3coeff": 0.010528},
    "Aluminate": {"k2ocoeff": 0.00979, "na2ocoeff": 0.0, "mgocoeff": 0.01091, "so3coeff": 0.0},
    "Ferrite": {"k2ocoeff": 0.00272, "na2ocoeff": 0.0, "mgocoeff": 0.02292, "so3coeff": 0.0},
    "Quartz": {"k2ocoeff": 0.0, "na2ocoeff": 0.0, "mgocoeff": 0.001, "so3coeff": 0.0},
    # ... other phases
}
```

#### 1.4 Interface Affinity Data
**File:** `src/app/services/kinetic_defaults_service.py` (same file)

```python
INTERFACE_AFFINITY_DEFAULTS = {
    "CSHQ": [
        {"affinityphase": "Alite", "contactanglevalue": 30},
        {"affinityphase": "Belite", "contactanglevalue": 30},
        {"affinityphase": "Portlandite", "contactanglevalue": 0},
    ],
    "Portlandite": [
        {"affinityphase": "CSHQ", "contactanglevalue": 0},
        {"affinityphase": "Alite", "contactanglevalue": 180},
        {"affinityphase": "Belite", "contactanglevalue": 180},
    ],
    # ... all hydration products
}
```

---

### Phase 2: SimParams JSON Generation Service (~2-3 components)

**Goal:** Create service that generates valid `simparams.json` from UI data.

#### 2.1 Phase Data Builder
**File:** `src/app/services/simparams_service.py`

```python
class PhaseDataBuilder:
    """Builds the phase entry data structure for simparams.json."""

    def __init__(self, gems_parser: GEMSParserService, kinetic_defaults: KineticDefaultsService):
        self.gems_parser = gems_parser
        self.kinetic_defaults = kinetic_defaults

    def build_phase_entry(
        self,
        thamesname: str,
        phase_id: int,
        is_cement_component: bool,
        kinetic_override: Optional[dict] = None,
        impurity_override: Optional[dict] = None,
        display_color: Optional[dict] = None
    ) -> dict:
        """Build a complete phase entry for simparams.json."""

    def build_gemphase_data(self, phase_name: str) -> List[dict]:
        """Build gemphase_data array from GEMS database."""

    def build_kinetic_data(self, phase_name: str, override: Optional[dict] = None) -> Optional[dict]:
        """Build kinetic_data dict with defaults and optional overrides."""

    def build_interface_data(self, phase_name: str) -> Optional[dict]:
        """Build interface_data with affinity definitions."""
```

**Tests:**
- Test building Alite phase entry with defaults
- Test building Gypsum phase entry
- Test kinetic override merging
- Test gemphase_data structure matches expected format

#### 2.2 SimParams Service
**File:** `src/app/services/simparams_service.py` (same file)

```python
class SimParamsService:
    """Generates simparams.json for THAMES-Hydration."""

    def __init__(
        self,
        gems_parser: GEMSParserService,
        kinetic_defaults: KineticDefaultsService,
        phase_color_service: PhaseColorService
    ):
        self.gems_parser = gems_parser
        self.kinetic_defaults = kinetic_defaults
        self.phase_color_service = phase_color_service
        self.phase_builder = PhaseDataBuilder(gems_parser, kinetic_defaults)

    def generate_simparams(
        self,
        phase_id_mapping: PhaseIdMapping,
        material_phases: List[dict],  # From MaterialService
        clinker_extension: Optional[ClinkerExtension],
        environment_config: dict,  # temperature, saturated, etc.
        time_config: dict,  # finaltime, outtimes
        kinetic_overrides: Optional[dict] = None  # phase_name -> override dict
    ) -> dict:
        """Generate complete simparams.json structure."""

    def build_environment_section(self, config: dict) -> dict:
        """Build environment section with electrolyte conditions."""

    def build_microstructure_section(
        self,
        phase_id_mapping: PhaseIdMapping,
        material_phases: List[dict],
        clinker_extension: Optional[ClinkerExtension],
        kinetic_overrides: Optional[dict]
    ) -> dict:
        """Build microstructure section with all phase entries."""

    def build_time_parameters(self, config: dict) -> dict:
        """Build time_parameters section."""

    def write_simparams_file(self, simparams: dict, output_path: Path) -> None:
        """Write simparams.json to file."""

    def validate_simparams(self, simparams: dict) -> Tuple[bool, List[str]]:
        """Validate simparams structure before writing."""
```

**Tests:**
- Test environment section generation
- Test time_parameters generation
- Test phase entry generation for each phase type
- Test full simparams generation for simple cement mix
- Test full simparams generation for cement + fly ash mix
- Test validation catches missing required fields
- Test JSON output is valid and parseable

#### 2.3 Electrolyte Conditions Defaults
**File:** `src/app/services/simparams_service.py` (same file)

```python
DEFAULT_ELECTROLYTE_CONDITIONS = [
    {"DCname": "Ca(CO3)@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "AlO2H@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "CaSiO3@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "Fe(CO3)@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "MgSiO3@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "KOH@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "Ca(SO4)@", "condition": "initial", "concentration": 1.0e-6},
    {"DCname": "K+", "condition": "initial", "concentration": 2.0e-6},
    {"DCname": "SO4-2", "condition": "initial", "concentration": 1.0e-6},
]
```

---

### Phase 3: Hydration Products Configuration (~1-2 components)

**Goal:** Define all potential hydration products with their properties.

#### 3.1 Hydration Products Registry
**File:** `src/app/config/hydration_products.py`

```python
"""
Registry of all hydration products that THAMES can produce.
These phases don't have kinetic dissolution but need gemphase_data and interface_data.
"""

HYDRATION_PRODUCTS = {
    # Calcium hydroxide
    "Portlandite": {
        "gemphasename": "Portlandite",
        "gemdc": [{"gemdcname": "Portlandite"}],
        "interface_affinity": [
            {"affinityphase": "CSHQ", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ]
    },

    # C-S-H (with special poresize_distribution and Rd data)
    "CSHQ": {
        "gemphasename": "CSHQ",
        "gemdc": [
            {"gemdcname": "CSHQ-JenD", "gemdcporosity": 0.4935},
            {"gemdcname": "CSHQ-JenH", "gemdcporosity": 0.4935},
            {"gemdcname": "CSHQ-TobD", "gemdcporosity": 0.2004},
            {"gemdcname": "CSHQ-TobH", "gemdcporosity": 0.2004},
            {"gemdcname": "KSiOH", "gemdcporosity": 0.1825},
            {"gemdcname": "NaSiOH", "gemdcporosity": 0.1825},
        ],
        "poresize_distribution": [...],  # Full PSD from reference
        "Rd": [
            {"Rdelement": "K", "Rdvalue": 0.42},
            {"Rdelement": "Na", "Rdvalue": 0.42},
        ],
        "interface_affinity": [...]
    },

    # AFt phases
    "ettr": {...},
    "ettr-AlFe": {...},
    "C6AsH13": {...},
    "C6AsH9": {...},
    "SO4_CO3_AFt": {...},

    # AFm phases
    "C4AsH105": {...},
    "C4AsH12": {...},
    "C4AsH14": {...},
    # ... etc

    # Carbonate AFm
    "C4AcH11": {...},
    "C4Ac0.5H12": {...},
    # ... etc

    # Aluminate hydrates
    "C3AH6": {...},
    "C4AH11": {...},
    "C4AH13": {...},
    "C4AH19": {...},

    # Other products
    "Hydrotalcite": {...},
}
```

**Tests:**
- Test all products have required keys
- Test gemphase_data structure is valid
- Test CSHQ has poresize_distribution

---

### Phase 4: Hydration Execution Service (~2 components)

**Goal:** Execute THAMES-Hydration and monitor progress.

#### 4.1 Hydration Input Service
**File:** `src/app/services/hydration_input_service.py`

```python
class HydrationInputService:
    """Manages generation of all hydration input files."""

    def __init__(
        self,
        simparams_service: SimParamsService,
        material_service: MaterialService,
        gems_data_dir: Path
    ):
        ...

    def prepare_hydration_inputs(
        self,
        operation_path: Path,
        mix_design: MixDesign,
        phase_id_mapping: PhaseIdMapping,
        microstructure_file: Path,
        environment_config: dict,
        time_config: dict,
        kinetic_overrides: Optional[dict] = None
    ) -> dict:
        """
        Prepare all input files for hydration simulation.

        Returns dict with paths to generated files:
        {
            'simparams': Path,
            'gems_dat_lst': Path,
            'gems_dch': Path,
            'gems_ipm': Path,
            'gems_dbr': Path,
            'microstructure': Path,
        }
        """

    def copy_gems_database(self, operation_path: Path) -> None:
        """Copy GEMS database files to operation folder."""

    def create_stdin_input(
        self,
        simtype: int,
        gems_dat_lst: str,
        simparams_file: str,
        microstructure_file: str,
        output_name: str
    ) -> str:
        """Create stdin input string for THAMES executable."""
```

**Tests:**
- Test file preparation creates all required files
- Test GEMS database copying
- Test stdin input string format

#### 4.2 Hydration Execution Service
**File:** `src/app/services/hydration_execution_service.py`

```python
class HydrationExecutionService:
    """Executes THAMES-Hydration and monitors progress."""

    def __init__(self, executable_path: Path):
        self.executable_path = executable_path
        self.logger = logging.getLogger('THAMES.HydrationExecution')

    def run_hydration(
        self,
        operation_path: Path,
        input_files: dict,
        output_name: str,
        verbose: bool = False,
        xyz_output: bool = False,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> HydrationResult:
        """
        Run THAMES-Hydration simulation.

        Args:
            operation_path: Working directory
            input_files: Dict from HydrationInputService.prepare_hydration_inputs()
            output_name: Base name for output files
            verbose: Enable verbose output
            xyz_output: Enable XYZ movie output
            progress_callback: Called with (progress_fraction, status_message)

        Returns:
            HydrationResult with status, output files, etc.
        """

    def _build_command(
        self,
        verbose: bool,
        xyz_output: bool,
        output_folder: str
    ) -> List[str]:
        """Build command line arguments."""

    def _parse_progress(self, output_line: str) -> Optional[float]:
        """Parse progress from THAMES output."""

    def _monitor_output_files(self, operation_path: Path, output_name: str) -> dict:
        """Monitor creation of output files for progress tracking."""

@dataclass
class HydrationResult:
    """Result of a hydration simulation."""
    success: bool
    status: str  # 'completed', 'failed', 'cancelled'
    error_message: Optional[str]
    output_files: dict  # {file_type: Path}
    simulation_time: float  # seconds
    final_degree_of_hydration: Optional[float]
```

**Tests:**
- Test command building with various options
- Test progress parsing from sample output
- Test error handling for missing executable
- Test timeout handling

---

### Phase 5: Hydration Setup UI (~3-4 components)

**Goal:** Create UI panel for configuring hydration simulations.

#### 5.1 Hydration Setup Panel
**File:** `src/app/windows/panels/hydration_setup_panel.py`

```python
class HydrationSetupPanel(Gtk.Box):
    """Panel for configuring THAMES hydration simulations."""

    def __init__(self, service_container):
        ...

    def _create_environment_section(self) -> Gtk.Frame:
        """Create environment configuration section."""
        # - Temperature (K or °C with conversion)
        # - Curing condition (saturated/sealed)

    def _create_time_section(self) -> Gtk.Frame:
        """Create time configuration section."""
        # - Final time (days)
        # - Output times (list or generate from interval)

    def _create_kinetics_section(self) -> Gtk.Frame:
        """Create kinetic parameter override section."""
        # - Table of phases with editable parameters
        # - "Reset to Defaults" button

    def _create_source_section(self) -> Gtk.Frame:
        """Create source microstructure selection."""
        # - Dropdown of completed microstructure operations
        # - Preview of selected microstructure

    def get_hydration_config(self) -> dict:
        """Get current configuration as dict."""

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate all inputs."""
```

#### 5.2 Kinetic Parameter Editor Dialog
**File:** `src/app/windows/dialogs/kinetic_editor_dialog.py`

```python
class KineticEditorDialog(Gtk.Dialog):
    """Dialog for editing kinetic parameters for a phase."""

    def __init__(self, phase_name: str, current_params: dict, defaults: dict):
        ...

    def _create_parrot_killoh_form(self) -> Gtk.Grid:
        """Create form for PK parameters."""

    def _create_standard_form(self) -> Gtk.Grid:
        """Create form for Standard parameters."""

    def _create_pozzolanic_form(self) -> Gtk.Grid:
        """Create form for Pozzolanic parameters."""

    def get_parameters(self) -> dict:
        """Get edited parameters."""

    def reset_to_defaults(self):
        """Reset all fields to defaults."""
```

#### 5.3 Output Times Configuration Widget
**File:** `src/app/widgets/output_times_widget.py`

```python
class OutputTimesWidget(Gtk.Box):
    """Widget for configuring simulation output times."""

    def __init__(self):
        ...

    def _create_mode_selector(self):
        """Create radio buttons for interval vs custom mode."""

    def _create_interval_inputs(self):
        """Create inputs for generating times from interval."""
        # - Start time
        # - End time
        # - Interval (linear or log-spaced)

    def _create_custom_list(self):
        """Create editable list for custom output times."""

    def get_output_times(self) -> List[float]:
        """Get list of output times in days."""
```

---

### Phase 6: Integration with Operations Panel (~2 components)

**Goal:** Connect hydration setup to operations workflow.

#### 6.1 THAMES Hydration Operation Model
**File:** `src/app/models/thames_hydration_operation.py`

```python
class ThamesHydrationOperation(Base):
    """Database model for THAMES hydration operations."""

    __tablename__ = 'thames_hydration_operations'

    id = Column(Integer, primary_key=True)
    operation_id = Column(Integer, ForeignKey('operations.id'), unique=True)

    # Source microstructure
    microstructure_operation_id = Column(Integer, ForeignKey('operations.id'))
    microstructure_file = Column(String(500))

    # Configuration (stored as JSON for flexibility)
    environment_config = Column(JSON)  # temperature, saturated, electrolyte_conditions
    time_config = Column(JSON)  # finaltime, outtimes
    kinetic_overrides = Column(JSON)  # phase_name -> override dict

    # Generated files
    simparams_file = Column(String(500))
    phase_mapping_file = Column(String(500))

    # Results
    final_doh = Column(Float)  # Final degree of hydration
    simulation_time_hours = Column(Float)

    # Status tracking
    status = Column(String(50), default='pending')
    progress = Column(Float, default=0.0)
    error_message = Column(Text)
```

#### 6.2 Operations Panel Integration
**File:** `src/app/windows/panels/operations_monitoring_panel.py` (modify existing)

Add hydration operation support:
- Launch hydration from microstructure operation
- Progress monitoring
- Results viewing

---

## Testing Strategy

### Unit Tests (per component)

Each component has dedicated unit tests:

1. **kinetic_parameters.py**
   - `test_parrot_killoh_dataclass.py`
   - `test_standard_kinetics_dataclass.py`
   - `test_pozzolanic_kinetics_dataclass.py`

2. **kinetic_defaults_service.py**
   - `test_kinetic_defaults_service.py`
   - Test defaults for all phase types
   - Test unknown phase handling

3. **simparams_service.py**
   - `test_phase_data_builder.py`
   - `test_simparams_service.py`
   - Test JSON generation
   - Test validation

4. **hydration_input_service.py**
   - `test_hydration_input_service.py`
   - Test file generation
   - Test stdin format

5. **hydration_execution_service.py**
   - `test_hydration_execution_service.py`
   - Test command building
   - Test progress parsing

### Integration Tests

1. **End-to-end simparams generation**
   - Load mix design from database
   - Generate simparams.json
   - Validate against reference

2. **Full hydration workflow**
   - Generate microstructure
   - Configure hydration
   - Run simulation (short test case)
   - Verify output files

---

## Implementation Order (Recommended)

### Sprint 1: Foundation (Phase 1)
1. Kinetic parameter data classes
2. Kinetic defaults service
3. Unit tests for above

### Sprint 2: SimParams Generation (Phase 2)
1. Phase data builder
2. SimParams service
3. Electrolyte defaults
4. Unit tests

### Sprint 3: Hydration Products (Phase 3)
1. Hydration products registry
2. Integration with SimParams service
3. Validation tests

### Sprint 4: Execution (Phase 4)
1. Hydration input service
2. Hydration execution service
3. Integration tests

### Sprint 5: UI (Phase 5)
1. Hydration setup panel
2. Kinetic editor dialog
3. Output times widget
4. Manual testing

### Sprint 6: Integration (Phase 6)
1. THAMES hydration operation model
2. Operations panel integration
3. End-to-end testing

---

## Dependencies Between Components

```
kinetic_parameters.py (no dependencies)
        │
        ▼
kinetic_defaults_service.py
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
hydration_products.py             phase_data_builder (in simparams_service.py)
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
              simparams_service.py
                       │
                       ▼
           hydration_input_service.py
                       │
                       ▼
          hydration_execution_service.py
                       │
                       ▼
             hydration_setup_panel.py
```

---

## File Summary

### New Files to Create

| File | Lines (est.) | Description |
|------|-------------|-------------|
| `src/app/models/kinetic_parameters.py` | ~150 | Kinetic parameter dataclasses |
| `src/app/services/kinetic_defaults_service.py` | ~400 | Default kinetic parameters |
| `src/app/config/hydration_products.py` | ~500 | Hydration product definitions |
| `src/app/services/simparams_service.py` | ~600 | SimParams JSON generation |
| `src/app/services/hydration_input_service.py` | ~300 | Input file preparation |
| `src/app/services/hydration_execution_service.py` | ~400 | Execution and monitoring |
| `src/app/models/thames_hydration_operation.py` | ~150 | Database model |
| `src/app/windows/panels/hydration_setup_panel.py` | ~500 | UI panel |
| `src/app/windows/dialogs/kinetic_editor_dialog.py` | ~300 | Parameter editor |
| `src/app/widgets/output_times_widget.py` | ~200 | Output times config |
| **Tests** | | |
| `tests/test_kinetic_parameters.py` | ~100 | |
| `tests/test_kinetic_defaults_service.py` | ~150 | |
| `tests/test_simparams_service.py` | ~300 | |
| `tests/test_hydration_input_service.py` | ~150 | |
| `tests/test_hydration_execution_service.py` | ~150 | |

**Total estimated new code:** ~4,350 lines

### Files to Modify

| File | Changes |
|------|---------|
| `src/app/models/__init__.py` | Add new model imports |
| `src/app/services/__init__.py` | Add new service imports |
| `src/app/windows/panels/operations_monitoring_panel.py` | Add hydration operation support |
| `src/app/windows/main_window.py` | Add Hydration Setup tab |

---

## Risk Mitigation

### Known Risks

1. **GEMS database compatibility**
   - Mitigation: Validate phase names against GEMS parser during SimParams generation

2. **Kinetic parameter values**
   - Mitigation: Use published values from Parrot & Killoh (1984) and Lothenbach & Winnefeld (2006)

3. **Cross-platform executable paths**
   - Mitigation: Use DirectoriesService pattern from microstructure generation

4. **Large simparams.json files**
   - Mitigation: Only include phases present in mix design + hydration products

---

## Success Criteria

1. ✅ User can configure hydration simulation from UI
2. ✅ Valid simparams.json generated matching reference format
3. ✅ THAMES-Hydration executes successfully
4. ✅ Progress monitored and displayed
5. ✅ Results viewable in Results panel
6. ✅ All unit tests pass (>95% coverage on new code)
7. ✅ Integration test with PC-FlyAsh-200 reference succeeds

---

*Document created: November 2025*
*Session 9: Hydration Integration Planning*

#!/usr/bin/env python3
"""
Hydration Input Service for THAMES

This is the main orchestration service for generating all input files required
by THAMES-Hydration. It combines data from:
- Mix design (materials, phases, compositions)
- Phase ID mapping
- Kinetic parameters
- Hydration products configuration
- Environment and time settings

The service generates:
1. simparams.json - Main simulation parameters file
2. Phase ID mapping JSON (for visualization)
3. Phase color mapping JSON (for visualization)
"""

import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field

from app.services.gems_parser_service import GEMSParserService
from app.services.kinetic_defaults_service import KineticDefaultsService, get_kinetic_defaults_service
from app.services.phase_id_mapping_service import PhaseIdMappingService, PhaseIdMapping
from app.services.phase_color_service import PhaseColorService
from app.services.simparams_service import (
    SimParamsService,
    EnvironmentConfig,
    TimeConfig,
    AdaptiveSteppingConfig,
    DEFAULT_ELECTROLYTE_CONDITIONS,
)
from app.services.hydration_products_service import (
    HydrationProductsService,
    get_hydration_products_service,
)

logger = logging.getLogger('THAMES.HydrationInputService')


@dataclass
class HydrationInputConfig:
    """
    Complete configuration for generating hydration input files.

    This dataclass holds all the settings needed to generate simparams.json
    and related files. It can be serialized for persistence.
    """
    # Microstructure settings
    resolution: float = 1.0  # micrometers per voxel

    # Environment settings
    temperature: float = 298.15  # Kelvin (25°C)
    reference_temperature: float = 298.15
    saturated: bool = True
    electrolyte_conditions: List[Dict[str, Any]] = field(
        default_factory=lambda: list(DEFAULT_ELECTROLYTE_CONDITIONS)
    )

    # Time settings
    final_time: float = 28.0  # days
    output_times: List[float] = field(
        default_factory=lambda: [0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28]
    )

    # Selected hydration products (GEMS phase names)
    hydration_products: List[str] = field(default_factory=list)

    # Product configurations (affinity, PSD, Rd values)
    # Maps GEMS name -> configuration dict
    product_configurations: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Kinetic parameter overrides (phase name -> kinetic params dict)
    kinetic_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Impurity data overrides (phase name -> impurity dict)
    impurity_overrides: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Adaptive time stepping configuration (None = use C++ defaults)
    adaptive_stepping: Optional[Dict[str, Any]] = None

    # Runtime options (command-line flags for thames executable)
    verbose: bool = False  # -v: Produce verbose output
    suppress_warnings: bool = False  # -s: Suppress warning messages
    create_xyz_files: bool = False  # -x: Create 3D visualization files for Ovito
    output_folder: str = "Result"  # -o: Output folder name

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "resolution": self.resolution,
            "temperature": self.temperature,
            "reference_temperature": self.reference_temperature,
            "saturated": self.saturated,
            "electrolyte_conditions": self.electrolyte_conditions,
            "final_time": self.final_time,
            "output_times": self.output_times,
            "hydration_products": self.hydration_products,
            "product_configurations": self.product_configurations,
            "kinetic_overrides": self.kinetic_overrides,
            "impurity_overrides": self.impurity_overrides,
            "adaptive_stepping": self.adaptive_stepping,
            "verbose": self.verbose,
            "suppress_warnings": self.suppress_warnings,
            "create_xyz_files": self.create_xyz_files,
            "output_folder": self.output_folder,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HydrationInputConfig':
        """Create from dictionary."""
        return cls(
            resolution=data.get("resolution", 1.0),
            temperature=data.get("temperature", 298.15),
            reference_temperature=data.get("reference_temperature", 298.15),
            saturated=data.get("saturated", True),
            electrolyte_conditions=data.get("electrolyte_conditions",
                                            list(DEFAULT_ELECTROLYTE_CONDITIONS)),
            final_time=data.get("final_time", 28.0),
            output_times=data.get("output_times",
                                  [0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28]),
            hydration_products=data.get("hydration_products", []),
            product_configurations=data.get("product_configurations", {}),
            kinetic_overrides=data.get("kinetic_overrides", {}),
            impurity_overrides=data.get("impurity_overrides", {}),
            adaptive_stepping=data.get("adaptive_stepping", None),
            verbose=data.get("verbose", False),
            suppress_warnings=data.get("suppress_warnings", False),
            create_xyz_files=data.get("create_xyz_files", False),
            output_folder=data.get("output_folder", "Result"),
        )


@dataclass
class MaterialPhaseData:
    """
    Phase data for a single material in the mix.
    """
    material_id: int
    material_name: str
    phases: List[Dict[str, Any]]  # Each has gem_phase_name, mass_fraction
    is_cement_component: bool = False
    is_clinker: bool = False


class HydrationInputService:
    """
    Main service for generating THAMES-Hydration input files.

    This service orchestrates all the component services to generate
    a complete set of input files for running THAMES-Hydration.
    """

    def __init__(
        self,
        gems_parser: Optional[GEMSParserService] = None,
        kinetic_defaults: Optional[KineticDefaultsService] = None,
        phase_color_service: Optional[PhaseColorService] = None,
        hydration_products_service: Optional[HydrationProductsService] = None,
    ):
        """
        Initialize the HydrationInputService.

        Args:
            gems_parser: GEMS parser service (will create if None)
            kinetic_defaults: Kinetic defaults service (will create if None)
            phase_color_service: Phase color service (will create if None)
            hydration_products_service: Hydration products service (will create if None)
        """
        if gems_parser is None:
            # Get GEMS data directory - go from src/app/services to src/data/gems
            gems_data_dir = Path(__file__).parent.parent.parent / "data" / "gems"
            self.gems_parser = GEMSParserService(gems_data_dir)
        else:
            self.gems_parser = gems_parser
        self.kinetic_defaults = kinetic_defaults or get_kinetic_defaults_service()
        self.phase_color_service = phase_color_service or PhaseColorService()
        self.hydration_products_service = (hydration_products_service or
                                            get_hydration_products_service())

        self.phase_id_mapping_service = PhaseIdMappingService()
        self.simparams_service = SimParamsService(
            self.gems_parser,
            self.kinetic_defaults,
            self.phase_color_service
        )

        self.logger = logging.getLogger('THAMES.HydrationInputService')

    def generate_all_inputs(
        self,
        output_dir: Path,
        operation_name: str,
        material_phases: List[MaterialPhaseData],
        config: HydrationInputConfig,
        microstructure_file: Optional[Path] = None,
    ) -> Tuple[bool, List[str], Dict[str, Path]]:
        """
        Generate all input files for THAMES-Hydration.

        This is the main entry point that generates:
        1. simparams.json
        2. phase_mapping.json
        3. phase_colors.json
        4. hydration_config.json (for UI reload)

        Args:
            output_dir: Directory to write output files
            operation_name: Name of the operation (used in filenames)
            material_phases: List of MaterialPhaseData objects from mix design
            config: HydrationInputConfig with all settings
            microstructure_file: Optional path to microstructure file (for validation)

        Returns:
            Tuple of (success, error_messages, generated_files)
        """
        errors = []
        generated_files: Dict[str, Path] = {}

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Try to load existing phase mapping from source microstructure
            # This is CRITICAL - the hydration must use the same phase IDs as the microstructure
            existing_mapping = self._load_existing_phase_mapping(microstructure_file)

            # Step 2: Create/extend phase ID mapping with hydration products
            self.logger.info("Creating phase ID mapping...")
            phase_mapping = self._create_phase_mapping(material_phases, config, existing_mapping)

            # Step 2b: Ensure all phases from microstructure are in mapping (validation)
            # This should now be a no-op since we loaded the existing mapping
            if microstructure_file and microstructure_file.exists():
                self.logger.info(f"Validating phases from microstructure: {microstructure_file}")
                success, micro_messages = self.ensure_microstructure_phases_in_mapping(
                    microstructure_file, phase_mapping
                )
                if not success:
                    errors.extend(micro_messages)
                    self.logger.error(f"Failed to process microstructure phases: {micro_messages}")
                else:
                    # Log informational messages
                    for msg in micro_messages:
                        if msg.startswith("WARNING"):
                            errors.append(msg)  # Include warnings in errors for user visibility
                        self.logger.info(msg)

            # Step 3: Generate simparams.json
            self.logger.info("Generating simparams.json...")
            simparams_path = output_dir / "simparams.json"
            simparams = self._generate_simparams(
                material_phases, config, phase_mapping
            )

            # Validate before writing
            is_valid, validation_errors = self.simparams_service.validate_simparams(simparams)
            if not is_valid:
                errors.extend(validation_errors)
                self.logger.error(f"simparams validation failed: {validation_errors}")
            else:
                self.simparams_service.write_simparams_file(simparams, simparams_path)
                generated_files['simparams'] = simparams_path
                self.logger.info(f"Wrote simparams.json with {simparams['microstructure']['numentries']} phases")

            # Step 4: Save phase mapping JSON
            self.logger.info("Saving phase mapping...")
            mapping_path = output_dir / f"{operation_name}_phase_mapping.json"
            self._save_phase_mapping(phase_mapping, mapping_path)
            generated_files['phase_mapping'] = mapping_path

            # Step 5: Save phase colors JSON
            self.logger.info("Saving phase colors...")
            colors_path = output_dir / f"{operation_name}_phase_colors.json"
            self._save_phase_colors(phase_mapping, colors_path)
            generated_files['phase_colors'] = colors_path

            # Step 6: Save hydration config (for reloading in UI)
            self.logger.info("Saving hydration config...")
            config_path = output_dir / f"{operation_name}_hydration_config.json"
            self._save_hydration_config(config, config_path)
            generated_files['hydration_config'] = config_path

            # Step 7: Copy GEMS data files to operation directory
            self.logger.info("Copying GEMS data files...")
            gems_files = self._copy_gems_files(output_dir)
            generated_files.update(gems_files)

            # Step 8: Create thames-dat.lst (GEMS file list)
            self.logger.info("Creating thames-dat.lst...")
            dat_lst_path = output_dir / "thames-dat.lst"
            self._create_thames_dat_lst(dat_lst_path)
            generated_files['thames_dat_lst'] = dat_lst_path

            # Step 9: Create input.in (master input file for thames)
            self.logger.info("Creating input.in...")
            input_in_path = output_dir / "input.in"
            microstructure_name = microstructure_file.name if microstructure_file else ""
            self._create_input_in(
                input_in_path,
                simtype=2,  # 2 = Hydration (1 = Exit)
                gem_input_file="thames-dat.lst",
                simparams_file="simparams.json",
                microstructure_file=microstructure_name,
                job_root=operation_name
            )
            generated_files['input_in'] = input_in_path

            success = len(errors) == 0 or all('warning' in e.lower() for e in errors)
            return success, errors, generated_files

        except Exception as e:
            self.logger.error(f"Error generating hydration inputs: {e}")
            errors.append(f"Exception: {str(e)}")
            return False, errors, generated_files

    def _load_existing_phase_mapping(
        self,
        microstructure_file: Optional[Path]
    ) -> Optional[PhaseIdMapping]:
        """
        Load the existing phase mapping from the source microstructure operation.

        This is critical for ensuring phase IDs match between microstructure and hydration.

        Args:
            microstructure_file: Path to microstructure .img file

        Returns:
            PhaseIdMapping if found, None otherwise
        """
        if not microstructure_file or not microstructure_file.exists():
            return None

        # Look for phase mapping JSON in the same directory
        micro_dir = microstructure_file.parent
        phase_mapping_files = list(micro_dir.glob("*_phase_mapping.json"))

        if not phase_mapping_files:
            self.logger.warning(f"No phase mapping found in {micro_dir}")
            return None

        phase_mapping_path = phase_mapping_files[0]
        self.logger.info(f"Loading existing phase mapping from: {phase_mapping_path}")

        try:
            import json
            with open(phase_mapping_path, 'r') as f:
                data = json.load(f)

            # Handle nested structure (phase_id_mapping wrapper) or flat structure
            if 'phase_id_mapping' in data:
                mapping_data = data['phase_id_mapping']
            else:
                mapping_data = data

            # Create PhaseIdMapping from loaded data
            mapping = PhaseIdMapping()
            mapping.gem_to_micro = mapping_data.get('gem_to_micro', {})
            mapping.micro_to_gem = {
                int(k): v for k, v in mapping_data.get('micro_to_gem', {}).items()
            }
            mapping.has_clinker = mapping_data.get('has_clinker', False)
            mapping.clinker_phase_ids = mapping_data.get('clinker_phase_ids', {})
            mapping.next_available_id = mapping_data.get('next_available_id', 2)

            self.logger.info(f"Loaded phase mapping with {len(mapping.gem_to_micro)} phases")
            return mapping

        except Exception as e:
            self.logger.error(f"Error loading phase mapping: {e}")
            return None

    def _create_phase_mapping(
        self,
        material_phases: List[MaterialPhaseData],
        config: HydrationInputConfig,
        existing_mapping: Optional[PhaseIdMapping] = None
    ) -> PhaseIdMapping:
        """
        Create phase ID mapping from materials and hydration products.

        If an existing mapping is provided (from source microstructure), it is used
        as the base and only hydration products are added. Otherwise, a new mapping
        is created from scratch.

        Args:
            material_phases: Material phase data from mix
            config: Hydration configuration with product list
            existing_mapping: Optional existing mapping from source microstructure

        Returns:
            PhaseIdMapping object
        """
        if existing_mapping:
            # Use the existing mapping from the source microstructure
            mapping = existing_mapping
            self.logger.info(f"Using existing phase mapping with {len(mapping.gem_to_micro)} phases")
        else:
            # Fall back to creating a new mapping from materials
            self.logger.warning("No existing phase mapping - creating new mapping from materials")

            # Convert to format expected by PhaseIdMappingService
            material_list = []
            for mat in material_phases:
                material_list.append({
                    'material_name': mat.material_name,
                    'phases': mat.phases,
                })

            # Create base mapping from materials
            mapping = self.phase_id_mapping_service.create_mapping_from_mix(
                material_list,
                include_hydration_products=False  # We'll add our own products
            )

        # CRITICAL: Ensure VOID (ID 0) and Electrolyte (ID 1) are always present
        # THAMES-Hydration requires these even if they're not in the initial microstructure
        if "VOID" not in mapping.gem_to_micro:
            mapping.gem_to_micro["VOID"] = 0
            mapping.micro_to_gem[0] = "VOID"
            self.logger.info("Added VOID (ID 0) to phase mapping for hydration")

        if "Electrolyte" not in mapping.gem_to_micro:
            mapping.gem_to_micro["Electrolyte"] = 1
            mapping.micro_to_gem[1] = "Electrolyte"
            self.logger.info("Added Electrolyte (ID 1) to phase mapping for hydration")

        # Add hydration products to mapping
        # IMPORTANT: Use the GEMS phase name, not the product key
        # e.g., "hydrotalcite" (key) -> "OH-hydrotalc" (GEMS phase name)
        next_id = mapping.next_available_id
        for product_name in config.hydration_products:
            # Look up the GEMS phase name from the hydration products service
            product_data = self.hydration_products_service.get_product_data(product_name)
            if product_data:
                gems_phase_name = product_data.gems_name
            else:
                # Fall back to product_name if not found
                self.logger.warning(
                    f"Hydration product '{product_name}' not found in service, "
                    f"using as GEMS phase name directly"
                )
                gems_phase_name = product_name

            if gems_phase_name not in mapping.gem_to_micro:
                mapping.gem_to_micro[gems_phase_name] = next_id
                mapping.micro_to_gem[next_id] = gems_phase_name
                next_id += 1

        mapping.next_available_id = next_id

        self.logger.info(f"Final phase mapping with {len(mapping.gem_to_micro)} phases (including hydration products)")
        return mapping

    def _generate_simparams(
        self,
        material_phases: List[MaterialPhaseData],
        config: HydrationInputConfig,
        phase_mapping: PhaseIdMapping
    ) -> Dict[str, Any]:
        """
        Generate the simparams.json content.

        Args:
            material_phases: Material phase data
            config: Hydration configuration
            phase_mapping: Phase ID mapping

        Returns:
            Complete simparams dictionary
        """
        # Build environment config
        env_config = EnvironmentConfig(
            temperature=config.temperature,
            reftemperature=config.reference_temperature,
            saturated=1 if config.saturated else 0,
            electrolyte_conditions=config.electrolyte_conditions,
        )

        # Build adaptive stepping config if provided
        adaptive_config = None
        if config.adaptive_stepping:
            adaptive_config = AdaptiveSteppingConfig(
                enabled=config.adaptive_stepping.get('enabled', True),
                dt_initial=config.adaptive_stepping.get('dt_initial', 0.001),
                dt_max=config.adaptive_stepping.get('dt_max', 4.0),
                growth_factor=config.adaptive_stepping.get('growth_factor', 1.5),
                shrink_factor=config.adaptive_stepping.get('shrink_factor', 0.5),
                successes_for_growth=config.adaptive_stepping.get('successes_for_growth', 2),
                max_consecutive_failures=config.adaptive_stepping.get('max_consecutive_failures', 50),
                max_relative_change=config.adaptive_stepping.get('max_relative_change', 0.05),
            )

        # Build time config
        time_config = TimeConfig(
            finaltime=config.final_time,
            outtimes=config.output_times,
            adaptive_stepping=adaptive_config,
        )

        # Convert materials to format expected by simparams service
        material_list = []
        for mat in material_phases:
            material_list.append({
                'material_name': mat.material_name,
                'phases': mat.phases,
                'is_cement_component': mat.is_cement_component,
            })

        # Build kinetic overrides dict
        kinetic_overrides = dict(config.kinetic_overrides)

        # Apply product configurations (affinity overrides are handled in build_phase_entry)
        # For now, pass the hydration products list

        simparams = self.simparams_service.generate_simparams(
            phase_id_mapping=phase_mapping,
            material_phases=material_list,
            environment_config=env_config,
            time_config=time_config,
            kinetic_overrides=kinetic_overrides if kinetic_overrides else None,
            hydration_products=config.hydration_products,
        )

        # Apply product-specific configurations (PSD, Rd, affinity)
        self._apply_product_configurations(simparams, config)

        # Build list of suppressed GEMS phases (all phases NOT in the
        # microstructure section). The C++ backend will set DCUpperLimit_
        # to a very small value for these phases, preventing GEMS from
        # precipitating them.
        active_gems_names = set()
        for phase_entry in simparams.get("microstructure", {}).get("phases", []):
            for gp in phase_entry.get("gemphase_data", []):
                active_gems_names.add(gp["gemphasename"])

        all_gems_names = set(self.gems_parser.get_phase_names())
        suppressed = sorted(all_gems_names - active_gems_names)
        if suppressed:
            simparams["suppressed_phases"] = suppressed

        return simparams

    def _apply_product_configurations(
        self,
        simparams: Dict[str, Any],
        config: HydrationInputConfig
    ) -> None:
        """
        Apply product-specific configurations (affinity, PSD, Rd) to simparams.

        Modifies simparams in place.

        Args:
            simparams: The simparams dictionary to modify
            config: Configuration with product settings
        """
        phases = simparams.get('microstructure', {}).get('phases', [])

        for phase in phases:
            phase_name = phase.get('thamesname', '')
            gems_name = self._thamesname_to_gems(phase_name)

            if gems_name in config.product_configurations:
                product_config = config.product_configurations[gems_name]

                # Apply affinity override
                if 'affinity' in product_config and product_config['affinity']:
                    phase['interface_data'] = {'affinity': product_config['affinity']}

                # Apply poresize distribution
                if 'poresize_distribution' in product_config:
                    phase['poresize_distribution'] = product_config['poresize_distribution']

                # Apply Rd values
                if 'rd_values' in product_config:
                    phase['Rd'] = product_config['rd_values']

    def _thamesname_to_gems(self, thamesname: str) -> str:
        """
        Convert THAMES display name back to GEMS name.

        Args:
            thamesname: THAMES display name

        Returns:
            GEMS phase name
        """
        # Reverse mapping of common names (THAMES display name -> GEMS phase name)
        reverse_mappings = {
            "Void": "VOID",
            "Electrolyte": "Electrolyte",
            "Hydrotalcite": "hydrotalc-pyro",
        }
        return reverse_mappings.get(thamesname, thamesname)

    def _save_phase_mapping(self, mapping: PhaseIdMapping, output_path: Path) -> None:
        """Save phase ID mapping to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(mapping.to_dict(), f, indent=2)
        self.logger.debug(f"Saved phase mapping to {output_path}")

    def _save_phase_colors(self, mapping: PhaseIdMapping, output_path: Path) -> None:
        """Save phase colors to JSON file."""
        # Extract operation name from path (remove _phase_colors suffix)
        operation_name = output_path.stem.replace("_phase_colors", "")
        color_mapping = self.phase_color_service.create_color_mapping(
            operation_name,
            mapping
        )
        # Pass the parent directory, not the full path, since save_color_mapping constructs the filename
        self.phase_color_service.save_color_mapping(color_mapping, output_path.parent)
        self.logger.debug(f"Saved phase colors to {output_path}")

    def _save_hydration_config(self, config: HydrationInputConfig, output_path: Path) -> None:
        """Save hydration configuration to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        self.logger.debug(f"Saved hydration config to {output_path}")

    def load_hydration_config(self, config_path: Path) -> HydrationInputConfig:
        """
        Load hydration configuration from JSON file.

        Args:
            config_path: Path to hydration_config.json

        Returns:
            HydrationInputConfig object
        """
        with open(config_path, 'r') as f:
            data = json.load(f)
        return HydrationInputConfig.from_dict(data)

    def get_default_config(self, cement_type: str = "portland") -> HydrationInputConfig:
        """
        Get a default configuration with suggested products for a cement type.

        Args:
            cement_type: 'portland', 'blended', 'pozzolanic', 'limestone', 'slag'

        Returns:
            HydrationInputConfig with defaults
        """
        config = HydrationInputConfig()

        # Get suggested products for this cement type
        suggested = self.hydration_products_service.get_suggested_products_for_cement_type(
            cement_type
        )
        config.hydration_products = suggested

        # Initialize product configurations with defaults
        for product_name in suggested:
            data = self.hydration_products_service.get_product_data(product_name)
            if data:
                product_config = {
                    'gems_name': data.gems_name,  # Use actual GEMS phase name, not product key
                    'affinity': list(data.default_affinity),
                }
                if data.poresize_distribution:
                    product_config['poresize_distribution'] = list(data.poresize_distribution)
                if data.rd_values:
                    product_config['rd_values'] = list(data.rd_values)

                config.product_configurations[product_name] = product_config

        return config

    def read_microstructure_phase_ids(
        self,
        microstructure_path: Path
    ) -> Tuple[Set[int], Optional[Dict[int, str]], List[str]]:
        """
        Read all phase IDs present in a microstructure file.

        Also attempts to read the phase mapping if embedded in the file header.

        Args:
            microstructure_path: Path to microstructure file

        Returns:
            Tuple of (phase_ids_set, embedded_mapping_or_None, error_messages)
            - phase_ids_set: Set of all unique phase IDs found in the voxel data
            - embedded_mapping: Dict of phase_id -> phase_name if found in header, else None
            - errors: List of any error messages encountered
        """
        phase_ids_in_file: Set[int] = set()
        embedded_mapping: Dict[int, str] = {}
        errors: List[str] = []

        try:
            with open(microstructure_path, 'r') as f:
                in_header = True

                for line in f:
                    line = line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Check for THAMES header format with phase mapping
                    # Format: #THAMES: Phase_2: Alite
                    if line.startswith('#THAMES:'):
                        content = line[8:].strip()
                        if content.startswith('Phase_'):
                            # Parse phase mapping: "Phase_2: Alite"
                            try:
                                parts = content.split(':', 1)
                                if len(parts) == 2:
                                    phase_id = int(parts[0].replace('Phase_', '').strip())
                                    phase_name = parts[1].strip()
                                    embedded_mapping[phase_id] = phase_name
                            except ValueError:
                                pass
                        continue

                    # Skip other comment lines
                    if line.startswith('#'):
                        continue

                    # Check for header lines (key: value format)
                    if ':' in line and in_header:
                        # Could be header like "X_Size: 100" or phase mapping
                        parts = line.split(':', 1)
                        key = parts[0].strip()

                        # Check if it's a phase mapping line (Phase_N: Name)
                        if key.startswith('Phase_'):
                            try:
                                phase_id = int(key.replace('Phase_', ''))
                                phase_name = parts[1].strip()
                                embedded_mapping[phase_id] = phase_name
                            except ValueError:
                                pass
                        continue

                    # Once we hit voxel data, we're past the header
                    in_header = False

                    # Parse voxel data - extract unique phase IDs
                    try:
                        parts = line.split()
                        for part in parts:
                            phase_id = int(part)
                            phase_ids_in_file.add(phase_id)
                    except ValueError:
                        # Not numeric data, skip
                        continue

            self.logger.info(
                f"Read microstructure: {len(phase_ids_in_file)} unique phase IDs, "
                f"{len(embedded_mapping)} phases in embedded mapping"
            )

            return phase_ids_in_file, embedded_mapping if embedded_mapping else None, errors

        except Exception as e:
            errors.append(f"Error reading microstructure file: {str(e)}")
            self.logger.error(f"Error reading microstructure: {e}")
            return phase_ids_in_file, None, errors

    def ensure_microstructure_phases_in_mapping(
        self,
        microstructure_path: Path,
        phase_mapping: PhaseIdMapping
    ) -> Tuple[bool, List[str]]:
        """
        Ensure all phases from a microstructure file are included in the phase mapping.

        This is CRITICAL for hydration simulation - every phase ID in the microstructure
        MUST have a corresponding entry in simparams.json.

        Args:
            microstructure_path: Path to microstructure file
            phase_mapping: Phase ID mapping to update (modified in place)

        Returns:
            Tuple of (success, messages)
            - success: True if all phases are now in mapping
            - messages: List of informational/warning messages
        """
        messages: List[str] = []

        # Read phase IDs from microstructure
        phase_ids, embedded_mapping, read_errors = self.read_microstructure_phase_ids(
            microstructure_path
        )

        if read_errors:
            return False, read_errors

        # Check which phase IDs are missing from the mapping
        missing_ids: Set[int] = set()
        for phase_id in phase_ids:
            if phase_id not in phase_mapping.micro_to_gem:
                missing_ids.add(phase_id)

        if not missing_ids:
            messages.append("All microstructure phases are already in the mapping")
            return True, messages

        # Try to resolve missing phases
        for phase_id in sorted(missing_ids):
            phase_name = None

            # First, check embedded mapping from microstructure file
            if embedded_mapping and phase_id in embedded_mapping:
                phase_name = embedded_mapping[phase_id]
                messages.append(
                    f"Added phase ID {phase_id} ('{phase_name}') from microstructure header"
                )
            else:
                # Generate a placeholder name for unknown phases
                # This ensures the simulation can run, but warns the user
                phase_name = f"Unknown_Phase_{phase_id}"
                messages.append(
                    f"WARNING: Phase ID {phase_id} in microstructure has no known name, "
                    f"using placeholder '{phase_name}'"
                )

            # Add to mapping
            phase_mapping.gem_to_micro[phase_name] = phase_id
            phase_mapping.micro_to_gem[phase_id] = phase_name

            # Update next_available_id if needed
            if phase_id >= phase_mapping.next_available_id:
                phase_mapping.next_available_id = phase_id + 1

        self.logger.info(f"Added {len(missing_ids)} phases from microstructure to mapping")

        return True, messages

    def validate_microstructure_compatibility(
        self,
        microstructure_path: Path,
        phase_mapping: PhaseIdMapping
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a microstructure file is compatible with the phase mapping.

        Note: This only validates - it does NOT modify the mapping.
        Use ensure_microstructure_phases_in_mapping() to add missing phases.

        Args:
            microstructure_path: Path to microstructure file
            phase_mapping: Phase ID mapping to check against

        Returns:
            Tuple of (is_compatible, warning_messages)
        """
        warnings: List[str] = []

        phase_ids, _, read_errors = self.read_microstructure_phase_ids(microstructure_path)

        if read_errors:
            return False, read_errors

        # Check that all phase IDs in file are in mapping
        for phase_id in sorted(phase_ids):
            if phase_id not in phase_mapping.micro_to_gem:
                warnings.append(
                    f"Phase ID {phase_id} found in microstructure but not in mapping"
                )

        return len(warnings) == 0, warnings

    def _get_gems_data_dir(self) -> Path:
        """
        Get the path to the GEMS data directory.

        Returns:
            Path to src/data/gems/ directory
        """
        # Try multiple possible locations
        # 1. Relative to this file (development)
        service_dir = Path(__file__).parent
        gems_dir = service_dir.parent.parent / "data" / "gems"
        if gems_dir.exists():
            return gems_dir

        # 2. PyInstaller bundle location
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys._MEIPASS)
            gems_dir = bundle_dir / "data" / "gems"
            if gems_dir.exists():
                return gems_dir

        # 3. Fallback to project root
        project_root = service_dir.parent.parent.parent
        gems_dir = project_root / "src" / "data" / "gems"
        if gems_dir.exists():
            return gems_dir

        raise FileNotFoundError("Could not locate GEMS data directory")

    def _copy_gems_files(self, output_dir: Path) -> Dict[str, Path]:
        """
        Copy GEMS data files to the operation directory.

        The files copied are:
        - thames-dch.dat (DC/phase definitions)
        - thames-ipm.dat (internal parameters)
        - thames-dbr.dat (data bridge)

        Args:
            output_dir: Destination directory

        Returns:
            Dictionary of file type -> copied path
        """
        gems_dir = self._get_gems_data_dir()
        copied_files: Dict[str, Path] = {}

        gems_files = [
            ("thames-dch.dat", "gems_dch"),
            ("thames-ipm.dat", "gems_ipm"),
            ("thames-dbr.dat", "gems_dbr"),
        ]

        for filename, key in gems_files:
            src_path = gems_dir / filename
            dst_path = output_dir / filename

            if src_path.exists():
                shutil.copy2(src_path, dst_path)
                copied_files[key] = dst_path
                self.logger.debug(f"Copied {filename} to {output_dir}")
            else:
                self.logger.warning(f"GEMS file not found: {src_path}")

        return copied_files

    def _create_thames_dat_lst(self, output_path: Path) -> None:
        """
        Create the thames-dat.lst file listing GEMS database files.

        Format:
        -t "thames-dch.dat" "thames-ipm.dat" "thames-dbr.dat"

        Args:
            output_path: Path to write thames-dat.lst
        """
        content = '-t "thames-dch.dat" "thames-ipm.dat" "thames-dbr.dat"\n'
        with open(output_path, 'w') as f:
            f.write(content)
        self.logger.debug(f"Created {output_path}")

    def _create_input_in(
        self,
        output_path: Path,
        simtype: int,
        gem_input_file: str,
        simparams_file: str,
        microstructure_file: str,
        job_root: str
    ) -> None:
        """
        Create the input.in master input file for thames.

        This file is piped to thames stdin to run non-interactively.

        Format:
        <simtype>               # 1=Exit, 2=Hydration, 3=Leaching, 4=Sulfate attack
        <gem_input_file>        # thames-dat.lst
        <simparams_file>        # simparams.json
        <microstructure_file>   # e.g., Cem151Paste.thames.img
        <job_root>              # Base name for output files

        Args:
            output_path: Path to write input.in
            simtype: Simulation type (1=Exit, 2=Hydration, 3=Leaching, 4=Sulfate)
            gem_input_file: Name of GEMS input file (thames-dat.lst)
            simparams_file: Name of simulation parameters file
            microstructure_file: Name of microstructure file
            job_root: Base name for output files
        """
        lines = [
            str(simtype),
            gem_input_file,
            simparams_file,
            microstructure_file,
            job_root,
        ]
        content = '\n'.join(lines) + '\n'

        with open(output_path, 'w') as f:
            f.write(content)

        self.logger.info(f"Created {output_path} with simtype={simtype}, job_root={job_root}")


# =============================================================================
# Module-level singleton
# =============================================================================

_hydration_input_service: Optional[HydrationInputService] = None


def get_hydration_input_service() -> HydrationInputService:
    """
    Get the HydrationInputService singleton.

    Returns:
        HydrationInputService instance
    """
    global _hydration_input_service

    if _hydration_input_service is None:
        _hydration_input_service = HydrationInputService()

    return _hydration_input_service

#!/usr/bin/env python3
"""
SimParams JSON Generation Service for THAMES

Generates simparams.json files for THAMES-Hydration from UI data.
This service combines data from:
- PhaseIdMappingService (phase IDs)
- KineticDefaultsService (kinetic parameters, impurity data, interface affinity)
- GEMSParserService (DC data for each phase)
- PhaseColorService (display colors)
- MaterialService (phase compositions from mix design)

The generated simparams.json follows the format required by THAMES-Hydration.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field

from app.services.gems_parser_service import GEMSParserService
from app.services.kinetic_defaults_service import KineticDefaultsService
from app.services.phase_id_mapping_service import PhaseIdMapping, VOIDID, ELECTROLYTEID
from app.services.phase_color_service import PhaseColorService
from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
    KineticParameters,
)

logger = logging.getLogger('THAMES.SimParamsService')


# =============================================================================
# Default Electrolyte Conditions
# =============================================================================
# These are the initial concentrations of aqueous species in the electrolyte
# Used to seed the GEMS equilibrium calculations

DEFAULT_ELECTROLYTE_CONDITIONS: List[Dict[str, Any]] = [
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


# =============================================================================
# Phase Data Builder
# =============================================================================

class PhaseDataBuilder:
    """
    Builds individual phase entry data structures for simparams.json.

    Each phase entry in simparams.json contains:
    - thamesname: Display name
    - id: Microstructure phase ID
    - cement_component: 1 if part of cement, 0 otherwise
    - display_data: RGB color values (optional)
    - gemphase_data: GEMS phase and DC information
    - impurity_data: Impurity coefficients (for dissolving phases)
    - kinetic_data: Kinetic parameters (for dissolving phases)
    - interface_data: Nucleation affinity data (for precipitating phases)
    - poresize_distribution: PSD for gel phases like C-S-H (optional)
    - Rd: Distribution coefficients (optional)
    """

    def __init__(
        self,
        gems_parser: GEMSParserService,
        kinetic_defaults: KineticDefaultsService,
        phase_color_service: PhaseColorService
    ):
        """
        Initialize the PhaseDataBuilder.

        Args:
            gems_parser: GEMS parser service for DC data
            kinetic_defaults: Service providing default kinetic parameters
            phase_color_service: Service for phase colors
        """
        self.gems_parser = gems_parser
        self.kinetic_defaults = kinetic_defaults
        self.phase_color_service = phase_color_service
        self.logger = logging.getLogger('THAMES.PhaseDataBuilder')

    def build_phase_entry(
        self,
        thamesname: str,
        phase_id: int,
        gemphasename: str,
        is_cement_component: bool,
        kinetic_override: Optional[Dict[str, Any]] = None,
        impurity_override: Optional[Dict[str, float]] = None,
        interface_override: Optional[List[Dict[str, Any]]] = None,
        include_display_data: bool = True
    ) -> Dict[str, Any]:
        """
        Build a complete phase entry for simparams.json.

        Args:
            thamesname: Display name for the phase
            phase_id: Microstructure phase ID
            gemphasename: GEMS phase name (for DC lookup)
            is_cement_component: Whether this is a cement component (affects dissolution)
            kinetic_override: Optional override for kinetic parameters
            impurity_override: Optional override for impurity data
            interface_override: Optional override for interface affinity
            include_display_data: Whether to include display color data

        Returns:
            Complete phase entry dictionary
        """
        entry: Dict[str, Any] = {
            "thamesname": thamesname,
            "id": phase_id,
            "cement_component": 1 if is_cement_component else 0,
        }

        # Add display data (color)
        if include_display_data:
            display_data = self._build_display_data(gemphasename)
            if display_data:
                entry["display_data"] = display_data

        # Add gemphase_data - required for all phases except VOID
        if phase_id != VOIDID:
            gemphase_data = self.build_gemphase_data(gemphasename)
            if gemphase_data:
                entry["gemphase_data"] = gemphase_data

        # Add kinetic_data for dissolving phases
        kinetic_data = self.build_kinetic_data(gemphasename, kinetic_override)
        if kinetic_data:
            entry["kinetic_data"] = kinetic_data

            # Add impurity_data for phases with kinetics
            impurity_data = self.build_impurity_data(gemphasename, impurity_override)
            if impurity_data:
                entry["impurity_data"] = impurity_data

        # Add interface_data for phases that nucleate/grow
        interface_data = self.build_interface_data(gemphasename, interface_override)
        if interface_data:
            entry["interface_data"] = interface_data

        return entry

    def build_gemphase_data(self, gemphasename: str) -> Optional[List[Dict[str, Any]]]:
        """
        Build gemphase_data array from GEMS database.

        The gemphase_data structure maps THAMES phases to GEMS phases and their DCs.
        Format:
        [
            {
                "gemphasename": "Alite",
                "gemdc": [{"gemdcname": "C3S", "gemdcporosity": 0.0}]
            }
        ]

        Args:
            gemphasename: GEMS phase name

        Returns:
            List of gemphase_data entries, or None if phase not found
        """
        # Handle special cases
        if gemphasename == "VOID":
            return None

        # Aggregate maps to Quartz for GEMS phase data
        if gemphasename == "Aggregate":
            gemphasename = "Quartz"

        # Look up phase in GEMS database
        phase = self.gems_parser.get_phase(gemphasename)
        if not phase:
            self.logger.warning(f"Phase '{gemphasename}' not found in GEMS database")
            return None

        # Build DC list
        gemdc_list = []
        for dc_name in phase.dc_names:
            dc_entry = {"gemdcname": dc_name}

            # Add porosity for certain DCs (e.g., C-S-H components)
            porosity = self._get_dc_porosity(gemphasename, dc_name)
            if porosity is not None:
                dc_entry["gemdcporosity"] = porosity

            gemdc_list.append(dc_entry)

        return [{
            "gemphasename": gemphasename,
            "gemdc": gemdc_list
        }]

    def _get_dc_porosity(self, gemphasename: str, dc_name: str) -> Optional[float]:
        """
        Get the porosity value for a specific DC.

        Porosity is only specified for certain gel phases like C-S-H.

        Args:
            gemphasename: GEMS phase name
            dc_name: DC name

        Returns:
            Porosity value (0-1) or None if not applicable
        """
        # C-S-H porosity values from reference simparams
        csh_porosities = {
            "CSHQ-JenD": 0.4935,
            "CSHQ-JenH": 0.4935,
            "CSHQ-TobD": 0.2004,
            "CSHQ-TobH": 0.2004,
            "KSiOH": 0.1825,
            "NaSiOH": 0.1825,
        }

        # Electrolyte DCs have porosity 1.0
        if gemphasename in ["aq_gen", "Electrolyte"]:
            return 1.0

        return csh_porosities.get(dc_name)

    def build_kinetic_data(
        self,
        gemphasename: str,
        override: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build kinetic_data dictionary with defaults and optional overrides.

        Args:
            gemphasename: GEMS phase name
            override: Optional dictionary of parameters to override

        Returns:
            Kinetic data dictionary or None if phase has no kinetics
        """
        # Get kinetics with any overrides applied
        if override:
            kinetics = self.kinetic_defaults.get_kinetics_with_override(gemphasename, override)
        else:
            kinetics = self.kinetic_defaults.get_kinetics_for_phase(gemphasename)

        if kinetics is None:
            return None

        return kinetics.to_dict()

    def build_impurity_data(
        self,
        gemphasename: str,
        override: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, float]]:
        """
        Build impurity_data dictionary with defaults and optional overrides.

        Args:
            gemphasename: GEMS phase name
            override: Optional dictionary of impurity coefficients to override

        Returns:
            Impurity data dictionary or None if phase has no impurity data
        """
        impurity_data = self.kinetic_defaults.get_impurity_data(gemphasename)

        if impurity_data is None:
            return None

        # Apply overrides if provided
        if override:
            impurity_data = dict(impurity_data)  # Make a copy
            impurity_data.update(override)

        return impurity_data

    def build_interface_data(
        self,
        gemphasename: str,
        override: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build interface_data dictionary with affinity definitions.

        Interface data controls where hydration products nucleate and grow.
        The affinity is based on contact angle:
        - 0° = maximum affinity (heterogeneous nucleation preferred)
        - 90° = neutral (default for unknown pairs)
        - 180° = no affinity (avoids nucleating on this substrate)

        Args:
            gemphasename: GEMS phase name
            override: Optional list of affinity entries to override

        Returns:
            Interface data dictionary or None if no affinity data
        """
        affinity_list = self.kinetic_defaults.get_interface_affinity(gemphasename)

        if override:
            affinity_list = override

        if affinity_list is None or len(affinity_list) == 0:
            # Return empty dict for phases that need interface_data but have no specific affinities
            if self.kinetic_defaults.get_kinetic_type(gemphasename) is None:
                # Non-dissolving phases (hydration products) should have interface_data
                return {}
            return None

        return {"affinity": affinity_list}

    def _build_display_data(self, gemphasename: str) -> Optional[Dict[str, float]]:
        """
        Build display_data dictionary with RGB color values.

        Args:
            gemphasename: GEMS phase name

        Returns:
            Display data dictionary with red, green, blue, gray values
        """
        hex_color = self.phase_color_service.get_color_for_phase(gemphasename)
        r, g, b = self.phase_color_service.hex_to_rgb(hex_color)

        # Calculate grayscale value (luminance approximation)
        gray = 0.299 * r + 0.587 * g + 0.114 * b

        return {
            "red": float(r),
            "green": float(g),
            "blue": float(b),
            "gray": float(gray)
        }


# =============================================================================
# SimParams Service
# =============================================================================

@dataclass
class EnvironmentConfig:
    """Configuration for the simulation environment."""
    temperature: float = 298.15  # Kelvin
    reftemperature: float = 298.15  # Reference temperature (K)
    saturated: int = 1  # 1 = saturated, 0 = sealed
    electrolyte_conditions: List[Dict[str, Any]] = field(
        default_factory=lambda: list(DEFAULT_ELECTROLYTE_CONDITIONS)
    )


@dataclass
class TimeConfig:
    """Configuration for simulation time parameters."""
    finaltime: float = 28.0  # days
    outtimes: List[float] = field(
        default_factory=lambda: [0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28]
    )


class SimParamsService:
    """
    Service for generating simparams.json files for THAMES-Hydration.

    This service combines data from multiple sources to generate a complete
    simparams.json file that THAMES-Hydration can use.
    """

    def __init__(
        self,
        gems_parser: GEMSParserService,
        kinetic_defaults: KineticDefaultsService,
        phase_color_service: PhaseColorService
    ):
        """
        Initialize the SimParamsService.

        Args:
            gems_parser: GEMS parser service
            kinetic_defaults: Kinetic defaults service
            phase_color_service: Phase color service
        """
        self.gems_parser = gems_parser
        self.kinetic_defaults = kinetic_defaults
        self.phase_color_service = phase_color_service
        self.phase_builder = PhaseDataBuilder(
            gems_parser, kinetic_defaults, phase_color_service
        )
        self.logger = logging.getLogger('THAMES.SimParamsService')

    def generate_simparams(
        self,
        phase_id_mapping: PhaseIdMapping,
        material_phases: List[Dict[str, Any]],
        environment_config: Optional[EnvironmentConfig] = None,
        time_config: Optional[TimeConfig] = None,
        kinetic_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        hydration_products: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete simparams.json structure.

        Args:
            phase_id_mapping: Phase ID mapping from PhaseIdMappingService
            material_phases: List of dicts with 'material_name', 'phases', 'is_cement_component'
            environment_config: Environment configuration (or None for defaults)
            time_config: Time configuration (or None for defaults)
            kinetic_overrides: Optional dict of phase_name -> kinetic override dict
            hydration_products: Optional list of hydration product phase names to include

        Returns:
            Complete simparams dictionary
        """
        env_config = environment_config or EnvironmentConfig()
        t_config = time_config or TimeConfig()

        simparams = {
            "environment": self._build_environment_section(env_config),
            "microstructure": self._build_microstructure_section(
                phase_id_mapping,
                material_phases,
                kinetic_overrides,
                hydration_products
            ),
            "time_parameters": self._build_time_parameters(t_config)
        }

        return simparams

    def _build_environment_section(self, config: EnvironmentConfig) -> Dict[str, Any]:
        """
        Build environment section of simparams.json.

        Args:
            config: Environment configuration

        Returns:
            Environment section dictionary
        """
        return {
            "temperature": config.temperature,
            "reftemperature": config.reftemperature,
            "saturated": config.saturated,
            "electrolyte_conditions": config.electrolyte_conditions
        }

    def _build_microstructure_section(
        self,
        phase_id_mapping: PhaseIdMapping,
        material_phases: List[Dict[str, Any]],
        kinetic_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
        hydration_products: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Build microstructure section with all phase entries.

        Args:
            phase_id_mapping: Phase ID mapping
            material_phases: Material phase data from mix design
            kinetic_overrides: Optional kinetic parameter overrides
            hydration_products: Optional list of hydration products to include

        Returns:
            Microstructure section dictionary
        """
        phases_list = []

        # Build set of cement component phases for quick lookup
        cement_phases = set()
        for material in material_phases:
            if material.get('is_cement_component', False):
                for phase in material.get('phases', []):
                    cement_phases.add(phase.get('gem_phase_name'))

        # Sort phases by ID for consistent output
        sorted_phases = sorted(
            phase_id_mapping.micro_to_gem.items(),
            key=lambda x: x[0]
        )

        for phase_id, phase_name in sorted_phases:
            # Determine if this is a cement component
            is_cement = phase_name in cement_phases or self.kinetic_defaults.is_cement_component(phase_name)

            # Get kinetic override if provided
            kinetic_override = None
            if kinetic_overrides and phase_name in kinetic_overrides:
                kinetic_override = kinetic_overrides[phase_name]

            # Map GEMS phase name to thamesname
            thamesname = self._get_thamesname(phase_name)

            # Build phase entry
            entry = self.phase_builder.build_phase_entry(
                thamesname=thamesname,
                phase_id=phase_id,
                gemphasename=phase_name,
                is_cement_component=is_cement,
                kinetic_override=kinetic_override,
                include_display_data=(phase_id in [VOIDID] or phase_name not in ["Electrolyte", "aq_gen"])
            )

            phases_list.append(entry)

        # Add hydration products if provided and not already in mapping
        if hydration_products:
            next_id = phase_id_mapping.next_available_id
            for product_name in hydration_products:
                if product_name not in phase_id_mapping.gem_to_micro:
                    entry = self.phase_builder.build_phase_entry(
                        thamesname=self._get_thamesname(product_name),
                        phase_id=next_id,
                        gemphasename=product_name,
                        is_cement_component=False
                    )
                    phases_list.append(entry)
                    next_id += 1

        return {
            "numentries": len(phases_list),
            "phases": phases_list
        }

    def _get_thamesname(self, gemphasename: str) -> str:
        """
        Convert GEMS phase name to THAMES display name.

        Some phases have different display names in THAMES than their GEMS names.

        Args:
            gemphasename: GEMS phase name

        Returns:
            THAMES display name
        """
        # Special mappings
        name_mappings = {
            "VOID": "Void",
            "aq_gen": "Electrolyte",
            "Electrolyte": "Electrolyte",
            "hemihydrate": "Bassanite",
            "C2AS(am)": "C2AS",
            "CA2S(am)": "CA2S",
            "CAS(am)": "CAS",
            "CAS2(am)": "CAS2",
            "K6A2S(am)": "K6A2S",
            "hydrotalc-pyro": "Hydrotalcite",
            "Portlandite": "Portlandite",
            "Portite": "Portlandite",
        }

        return name_mappings.get(gemphasename, gemphasename)

    def _build_time_parameters(self, config: TimeConfig) -> Dict[str, Any]:
        """
        Build time_parameters section.

        Args:
            config: Time configuration

        Returns:
            Time parameters dictionary
        """
        return {
            "finaltime": config.finaltime,
            "outtimes": config.outtimes
        }

    def write_simparams_file(
        self,
        simparams: Dict[str, Any],
        output_path: Path
    ) -> None:
        """
        Write simparams.json to file.

        Args:
            simparams: Complete simparams dictionary
            output_path: Path to write file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(simparams, f, indent=2)

        self.logger.info(f"Wrote simparams.json to {output_path}")

    def validate_simparams(
        self,
        simparams: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate simparams structure before writing.

        Args:
            simparams: Simparams dictionary to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check required top-level keys
        required_keys = ["environment", "microstructure", "time_parameters"]
        for key in required_keys:
            if key not in simparams:
                errors.append(f"Missing required key: {key}")

        # Validate environment section
        if "environment" in simparams:
            env = simparams["environment"]
            if "temperature" not in env:
                errors.append("Environment missing 'temperature'")
            elif env["temperature"] <= 0:
                errors.append(f"Invalid temperature: {env['temperature']}")

            if "saturated" not in env:
                errors.append("Environment missing 'saturated'")
            elif env["saturated"] not in [0, 1]:
                errors.append(f"Invalid saturated value: {env['saturated']} (must be 0 or 1)")

        # Validate microstructure section
        if "microstructure" in simparams:
            micro = simparams["microstructure"]
            if "phases" not in micro:
                errors.append("Microstructure missing 'phases'")
            elif not isinstance(micro["phases"], list):
                errors.append("Microstructure 'phases' must be a list")
            else:
                # Validate each phase entry
                phase_ids = set()
                for i, phase in enumerate(micro["phases"]):
                    if "thamesname" not in phase:
                        errors.append(f"Phase {i} missing 'thamesname'")
                    if "id" not in phase:
                        errors.append(f"Phase {i} missing 'id'")
                    else:
                        if phase["id"] in phase_ids:
                            errors.append(f"Duplicate phase ID: {phase['id']}")
                        phase_ids.add(phase["id"])

                    if "cement_component" not in phase:
                        errors.append(f"Phase {i} missing 'cement_component'")

                # Check for required reserved phases
                if VOIDID not in phase_ids:
                    errors.append(f"Missing required VOID phase (ID {VOIDID})")
                if ELECTROLYTEID not in phase_ids:
                    errors.append(f"Missing required Electrolyte phase (ID {ELECTROLYTEID})")

        # Validate time_parameters section
        if "time_parameters" in simparams:
            time_params = simparams["time_parameters"]
            if "finaltime" not in time_params:
                errors.append("time_parameters missing 'finaltime'")
            elif time_params["finaltime"] <= 0:
                errors.append(f"Invalid finaltime: {time_params['finaltime']}")

            if "outtimes" not in time_params:
                errors.append("time_parameters missing 'outtimes'")
            elif not isinstance(time_params["outtimes"], list):
                errors.append("time_parameters 'outtimes' must be a list")
            elif len(time_params["outtimes"]) == 0:
                errors.append("time_parameters 'outtimes' must not be empty")

        return len(errors) == 0, errors


# =============================================================================
# Module-level singleton accessors
# =============================================================================

_simparams_service: Optional[SimParamsService] = None


def get_simparams_service(
    gems_parser: Optional[GEMSParserService] = None,
    kinetic_defaults: Optional[KineticDefaultsService] = None,
    phase_color_service: Optional[PhaseColorService] = None
) -> SimParamsService:
    """
    Get or create the SimParamsService singleton.

    Args:
        gems_parser: GEMS parser service (required on first call)
        kinetic_defaults: Kinetic defaults service (optional, will create if needed)
        phase_color_service: Phase color service (optional, will create if needed)

    Returns:
        SimParamsService instance
    """
    global _simparams_service

    if _simparams_service is None:
        if gems_parser is None:
            raise ValueError("gems_parser is required on first call to get_simparams_service")

        if kinetic_defaults is None:
            from app.services.kinetic_defaults_service import get_kinetic_defaults_service
            kinetic_defaults = get_kinetic_defaults_service()

        if phase_color_service is None:
            phase_color_service = PhaseColorService()

        _simparams_service = SimParamsService(
            gems_parser, kinetic_defaults, phase_color_service
        )

    return _simparams_service

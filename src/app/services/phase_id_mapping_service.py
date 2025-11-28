#!/usr/bin/env python3
"""
Phase ID Mapping Service for THAMES

Dynamically assigns microstructure phase IDs based on the mix design composition.
This replaces VCCTL's hard-coded phase ID scheme with a flexible system that
works with any combination of GEMS phases.

THAMES Phase ID Rules (ALWAYS reserved, regardless of mix composition):
- ID 0: VOID (empty pores, gas phase)
- ID 1: ELECTROLYTE (aqueous solution)
- ID 2: Alite (C3S)
- ID 3: Belite (C2S)
- ID 4: Aluminate (C3A)
- ID 5: Ferrite (C4AF)
- ID 6: arcanite (K2SO4)
- ID 7: thenardite (Na2SO4)
- ID 8: AGGREGATE (coarse/fine aggregate, ITZ boundary)
- IDs 9+: Other phases (calcium sulfates, pozzolans, hydration products)

The reserved IDs (0-8) are ALWAYS assigned regardless of whether those phases
are present in the mix. This ensures consistent phase ID mapping across all
THAMES simulations and compatibility with the THAMES-Hydration C++ code.
"""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field

from app.config.phase_mappings import (
    VCCTL_TO_GEMS_CEMENT,
    PHASE_CATEGORIES,
)


# Reserved phase IDs (must match global.h in thames-hydration)
VOIDID = 0
ELECTROLYTEID = 1
FIRST_SOLID = 2

# Clinker phase names (GEMS format) - must be in this order for THAMES compatibility
# Includes the four main clinker minerals plus alkali sulfates
CLINKER_PHASES = ["Alite", "Belite", "Aluminate", "Ferrite", "Arcanite", "Thenardite"]
NUM_CLINKER_PHASES = len(CLINKER_PHASES)

# Aggregate phase ID - always reserved after clinker phases
AGGREGATEID = FIRST_SOLID + NUM_CLINKER_PHASES  # ID 8

# First ID available for other solid phases (after clinker + aggregate)
FIRST_OTHER_SOLID = AGGREGATEID + 1  # ID 9


@dataclass
class PhaseIdMapping:
    """
    Holds the complete phase ID mapping for a mix design.

    Attributes:
        gem_to_micro: Maps GEMS phase name to microstructure phase ID
        micro_to_gem: Maps microstructure phase ID to GEMS phase name
        has_clinker: Whether the mix contains clinker phases
        clinker_phase_ids: Dict of clinker phase name to ID (if present)
        next_available_id: Next available phase ID for new phases
    """
    gem_to_micro: Dict[str, int] = field(default_factory=dict)
    micro_to_gem: Dict[int, str] = field(default_factory=dict)
    has_clinker: bool = False
    clinker_phase_ids: Dict[str, int] = field(default_factory=dict)
    next_available_id: int = FIRST_SOLID

    def get_phase_id(self, gem_phase_name: str) -> Optional[int]:
        """Get microstructure phase ID for a GEMS phase name."""
        return self.gem_to_micro.get(gem_phase_name)

    def get_phase_name(self, phase_id: int) -> Optional[str]:
        """Get GEMS phase name for a microstructure phase ID."""
        return self.micro_to_gem.get(phase_id)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "gem_to_micro": self.gem_to_micro,
            "micro_to_gem": {str(k): v for k, v in self.micro_to_gem.items()},
            "has_clinker": self.has_clinker,
            "clinker_phase_ids": self.clinker_phase_ids,
            "next_available_id": self.next_available_id,
        }


class PhaseIdMappingService:
    """
    Service for creating and managing phase ID mappings for THAMES simulations.

    This service takes a mix design and creates a mapping between GEMS phase names
    and microstructure phase IDs that THAMES-Hydration uses internally.
    """

    def __init__(self):
        self.logger = logging.getLogger('THAMES.PhaseIdMappingService')

    def create_mapping_from_mix(
        self,
        material_phases: List[Dict[str, Any]],
        include_hydration_products: bool = True
    ) -> PhaseIdMapping:
        """
        Create a phase ID mapping from a list of materials and their phases.

        Args:
            material_phases: List of dicts with 'material_name' and 'phases' keys.
                            Each phase dict has 'gem_phase_name' and 'mass_fraction'.
            include_hydration_products: Whether to reserve IDs for common hydration products.

        Returns:
            PhaseIdMapping object with complete phase-to-ID mappings.

        Example:
            material_phases = [
                {
                    'material_name': 'Cement 116',
                    'phases': [
                        {'gem_phase_name': 'Alite', 'mass_fraction': 0.60},
                        {'gem_phase_name': 'Belite', 'mass_fraction': 0.15},
                        {'gem_phase_name': 'Aluminate', 'mass_fraction': 0.08},
                        {'gem_phase_name': 'Ferrite', 'mass_fraction': 0.10},
                        {'gem_phase_name': 'Gypsum', 'mass_fraction': 0.05},
                    ]
                },
                {
                    'material_name': 'Class F Fly Ash',
                    'phases': [
                        {'gem_phase_name': 'Quartz', 'mass_fraction': 0.50},
                        {'gem_phase_name': 'Mullite', 'mass_fraction': 0.30},
                    ]
                }
            ]
        """
        mapping = PhaseIdMapping()

        # Always add void and electrolyte
        mapping.gem_to_micro["VOID"] = VOIDID
        mapping.micro_to_gem[VOIDID] = "VOID"
        mapping.gem_to_micro["Electrolyte"] = ELECTROLYTEID  # GEMS aqueous phase name
        mapping.micro_to_gem[ELECTROLYTEID] = "Electrolyte"

        # Collect all unique phases from materials
        all_phases: Set[str] = set()
        for material in material_phases:
            for phase in material.get('phases', []):
                gem_name = phase.get('gem_phase_name')
                if gem_name:
                    all_phases.add(gem_name)

        # Check if mix contains clinker phases
        clinker_in_mix = all_phases & set(CLINKER_PHASES)
        mapping.has_clinker = len(clinker_in_mix) > 0

        # ALWAYS reserve IDs 2-7 for clinker phases (even if not present in mix)
        # This ensures consistent phase ID mapping across all THAMES simulations
        self.logger.info("Reserving IDs 2-7 for clinker phases")
        for i, clinker_phase in enumerate(CLINKER_PHASES):
            phase_id = FIRST_SOLID + i
            mapping.gem_to_micro[clinker_phase] = phase_id
            mapping.micro_to_gem[phase_id] = clinker_phase
            mapping.clinker_phase_ids[clinker_phase] = phase_id

        # ALWAYS reserve ID 8 for aggregate
        self.logger.info("Reserving ID 8 for aggregate")
        mapping.gem_to_micro["AGGREGATE"] = AGGREGATEID
        mapping.micro_to_gem[AGGREGATEID] = "AGGREGATE"

        # Set next available ID to 9 (after clinker + aggregate)
        mapping.next_available_id = FIRST_OTHER_SOLID

        # Assign IDs to remaining phases (excluding clinker phases which are already assigned)
        non_clinker_phases = all_phases - set(CLINKER_PHASES)

        # Sort phases for deterministic ordering
        # Priority: sulfates first, then other cement phases, then pozzolans, then others
        sorted_phases = self._sort_phases_by_priority(non_clinker_phases)

        for phase_name in sorted_phases:
            if phase_name not in mapping.gem_to_micro:
                phase_id = mapping.next_available_id
                mapping.gem_to_micro[phase_name] = phase_id
                mapping.micro_to_gem[phase_id] = phase_name
                mapping.next_available_id += 1
                self.logger.debug(f"Assigned phase ID {phase_id} to '{phase_name}'")

        # Optionally add common hydration products
        if include_hydration_products:
            self._add_hydration_products(mapping)

        self.logger.info(
            f"Created phase mapping: {len(mapping.gem_to_micro)} phases, "
            f"has_clinker={mapping.has_clinker}"
        )

        return mapping

    def _sort_phases_by_priority(self, phases: Set[str]) -> List[str]:
        """
        Sort phases by priority for consistent ID assignment.

        Priority order (for non-clinker phases):
        1. Calcium sulfates (Gypsum, hemihydrate, Anhydrite)
        2. Carbonates (Calcite, Dolomite)
        3. Pozzolanic phases
        4. Everything else (alphabetical)

        Note: Clinker phases (Alite, Belite, Aluminate, Ferrite, arcanite,
        thenardite) are handled separately and always get IDs 2-7.
        """
        sulfates = []
        carbonates = []
        pozzolans = []
        others = []

        # Note: arcanite and thenardite are clinker phases, handled separately
        sulfate_names = {"Gypsum", "hemihydrate", "Anhydrite"}
        carbonate_names = {"Calcite", "Dolomite-dis", "Dolomite-ord", "lime"}
        pozzolan_names = {
            "Quartz", "Mullite", "Sfume", "Silica-amorph",
            "C2AS(am)", "CA2S(am)", "CAS(am)", "CAS2(am)", "K6A2S(am)"
        }

        for phase in phases:
            if phase in sulfate_names:
                sulfates.append(phase)
            elif phase in carbonate_names:
                carbonates.append(phase)
            elif phase in pozzolan_names:
                pozzolans.append(phase)
            else:
                others.append(phase)

        # Sort each category alphabetically
        return (
            sorted(sulfates) +
            sorted(carbonates) +
            sorted(pozzolans) +
            sorted(others)
        )

    def _add_hydration_products(self, mapping: PhaseIdMapping) -> None:
        """
        Add common hydration products to the mapping.

        These phases may form during hydration and need assigned IDs.
        """
        hydration_products = [
            "Portite",      # CH - Portlandite
            "CSHQ",         # C-S-H
            "ettr",         # Ettringite
            "C4AsH14",      # Monosulfate
            "C4AcH11",      # Monocarboaluminate
            "C3AH6",        # Hydrogarnet
            "hydrotalc-pyro",  # Hydrotalcite
            "FeSite",       # Fe(OH)3
            "Straetli",     # Stratlingite
            "Brucite",      # Mg(OH)2
        ]

        for product in hydration_products:
            if product not in mapping.gem_to_micro:
                phase_id = mapping.next_available_id
                mapping.gem_to_micro[product] = phase_id
                mapping.micro_to_gem[phase_id] = product
                mapping.next_available_id += 1

    def create_mapping_from_mix_design(
        self,
        mix_design: Any,
        material_service: Any
    ) -> PhaseIdMapping:
        """
        Create phase mapping from a MixDesign object.

        Args:
            mix_design: MixDesign object with components
            material_service: MaterialService to look up material phases

        Returns:
            PhaseIdMapping object
        """
        material_phases = []

        for component in mix_design.components:
            material_name = component.material_name

            # Look up material to get its phases
            material = material_service.get_by_name(material_name)
            if material and hasattr(material, 'phases'):
                phases = [
                    {
                        'gem_phase_name': p.gem_phase_name,
                        'mass_fraction': p.mass_fraction
                    }
                    for p in material.phases
                ]
                material_phases.append({
                    'material_name': material_name,
                    'phases': phases
                })

        return self.create_mapping_from_mix(material_phases)

    def get_vcctl_compatible_mapping(self) -> PhaseIdMapping:
        """
        Create a mapping compatible with VCCTL's fixed phase ID scheme.

        This is useful for testing or when importing VCCTL microstructures.
        """
        mapping = PhaseIdMapping()
        mapping.has_clinker = True

        # VCCTL phase IDs (from vcctl2thames.h)
        vcctl_phases = {
            "VOID": 0,
            "Electrolyte": 0,  # VCCTL uses 0 for electrolyte
            "Alite": 1,      # C3S
            "Belite": 2,     # C2S
            "Aluminate": 3,  # C3A
            "Ferrite": 4,    # C4AF
            "Arcanite": 5,   # K2SO4
            "Thenardite": 6, # Na2SO4
            "Gypsum": 7,
            "hemihydrate": 8,
            "Anhydrite": 9,
            "Sfume": 10,     # Silica fume
            # ... more phases can be added
        }

        for phase_name, phase_id in vcctl_phases.items():
            mapping.gem_to_micro[phase_name] = phase_id
            mapping.micro_to_gem[phase_id] = phase_name

        mapping.next_available_id = max(vcctl_phases.values()) + 1

        return mapping

    def validate_mapping(self, mapping: PhaseIdMapping) -> Tuple[bool, List[str]]:
        """
        Validate a phase ID mapping for consistency.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check that void and electrolyte are assigned
        if VOIDID not in mapping.micro_to_gem:
            errors.append("VOID phase (ID 0) not assigned")
        if ELECTROLYTEID not in mapping.micro_to_gem:
            errors.append("ELECTROLYTE phase (ID 1) not assigned")

        # Check for duplicate IDs
        ids_seen = set()
        for phase_name, phase_id in mapping.gem_to_micro.items():
            if phase_id in ids_seen:
                existing = mapping.micro_to_gem.get(phase_id)
                errors.append(
                    f"Duplicate phase ID {phase_id}: '{phase_name}' and '{existing}'"
                )
            ids_seen.add(phase_id)

        # Check bidirectional consistency
        for phase_name, phase_id in mapping.gem_to_micro.items():
            reverse = mapping.micro_to_gem.get(phase_id)
            if reverse != phase_name:
                errors.append(
                    f"Inconsistent mapping: {phase_name} -> {phase_id} -> {reverse}"
                )

        # Check that clinker phase IDs are always reserved (IDs 2-7)
        for i, clinker_phase in enumerate(CLINKER_PHASES):
            expected_id = FIRST_SOLID + i
            actual_id = mapping.gem_to_micro.get(clinker_phase)
            if actual_id != expected_id:
                errors.append(
                    f"Clinker phase '{clinker_phase}' should have ID {expected_id}, "
                    f"but has {actual_id}"
                )

        # Check that aggregate ID is reserved (ID 8)
        if AGGREGATEID not in mapping.micro_to_gem:
            errors.append(f"AGGREGATE phase (ID {AGGREGATEID}) not assigned")

        return len(errors) == 0, errors


# Module-level singleton
_phase_id_mapping_service: Optional[PhaseIdMappingService] = None


def get_phase_id_mapping_service() -> PhaseIdMappingService:
    """Get the singleton PhaseIdMappingService instance."""
    global _phase_id_mapping_service
    if _phase_id_mapping_service is None:
        _phase_id_mapping_service = PhaseIdMappingService()
    return _phase_id_mapping_service

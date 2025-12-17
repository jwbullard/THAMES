#!/usr/bin/env python3
"""
Phase ID Mapping Service for THAMES

Dynamically assigns microstructure phase IDs based on the mix design composition.
This replaces VCCTL's hard-coded phase ID scheme with a flexible system that
works with any combination of GEMS phases.

THAMES Phase ID Assignment (Two-Phase Approach):

1. During Microstructure Generation (micgen.c):
   - ID 0: VOID (empty pores, gas phase) - always reserved
   - ID 1: Electrolyte (aqueous solution) - always reserved
   - IDs 2-7: Reserved for clinker phases (Alite, Belite, Aluminate, Ferrite,
              Arcanite, Thenardite) because micgen.c needs to identify phases
              with correlation functions and surface area fractions
   - ID 8: Aggregate (if present)
   - IDs 9+: Other phases (calcium sulfates, pozzolans, etc.)

2. After Microstructure Generation (remap_to_sequential):
   - Phase IDs are remapped to be sequential with no gaps
   - Example: If only phases 0, 1, 2, 3, 8, 9 exist, they become 0, 1, 2, 3, 4, 5
   - This is required by THAMES-Hydration C++ code which expects sequential IDs
   - The phase_mapping.json and phase_colors.json files are updated accordingly

The remap_to_sequential() method is called automatically after micgen completes.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field

import numpy as np

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

# Build case-insensitive lookup for clinker phase names
# This handles GEMS database variations (arcanite vs Arcanite, etc.)
_CLINKER_PHASE_LOOKUP = {name.lower(): name for name in CLINKER_PHASES}


def normalize_phase_name(phase_name: str) -> str:
    """
    Normalize a phase name to its canonical form.

    Clinker phases are normalized to their capitalized form (e.g., arcanite -> Arcanite).
    Other phases are returned unchanged.

    Args:
        phase_name: The phase name to normalize

    Returns:
        The normalized phase name
    """
    lower_name = phase_name.lower()
    if lower_name in _CLINKER_PHASE_LOOKUP:
        return _CLINKER_PHASE_LOOKUP[lower_name]
    return phase_name


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
        include_hydration_products: bool = True,
        include_aggregate: bool = False
    ) -> PhaseIdMapping:
        """
        Create a phase ID mapping from a list of materials and their phases.

        Args:
            material_phases: List of dicts with 'material_name' and 'phases' keys.
                            Each phase dict has 'gem_phase_name' and 'mass_fraction'.
            include_hydration_products: Whether to reserve IDs for common hydration products.
            include_aggregate: Whether to include AGGREGATE phase (only if actually in microstructure).

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

        # Collect all unique phases from materials, normalizing clinker phase names
        all_phases: Set[str] = set()
        for material in material_phases:
            for phase in material.get('phases', []):
                gem_name = phase.get('gem_phase_name')
                if gem_name:
                    # Normalize to handle case variations (arcanite -> Arcanite, etc.)
                    all_phases.add(normalize_phase_name(gem_name))

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

        # Only include Aggregate if it's actually in the microstructure
        if include_aggregate:
            self.logger.info("Including Aggregate at ID 8")
            mapping.gem_to_micro["Aggregate"] = AGGREGATEID
            mapping.micro_to_gem[AGGREGATEID] = "Aggregate"

        # Set next available ID to 9 (after clinker + aggregate slot)
        # Note: ID 8 is reserved for AGGREGATE even if not present, to maintain consistent IDs
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
        1. Calcium sulfates (Gypsum, Bassanite, Anhydrite)
        2. Carbonates (Calcite, Dolomite)
        3. Pozzolanic phases
        4. Everything else (alphabetical)

        Note: Clinker phases (Alite, Belite, Aluminate, Ferrite, Arcanite,
        Thenardite) are handled separately and always get IDs 2-7.
        """
        sulfates = []
        carbonates = []
        pozzolans = []
        others = []

        # Note: Arcanite and Thenardite are clinker phases, handled separately
        sulfate_names = {"Gypsum", "Bassanite", "Anhydrite"}
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
            "Bassanite": 8,
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

        # Note: AGGREGATE (ID 8) is optional - only required if aggregate is in microstructure
        # No validation error if AGGREGATE is missing

        return len(errors) == 0, errors

    def remap_to_sequential(
        self,
        microstructure_path: Path,
        phase_mapping_path: Path,
        output_microstructure_path: Optional[Path] = None,
        output_mapping_path: Optional[Path] = None
    ) -> Tuple[Dict[int, int], PhaseIdMapping]:
        """
        Remap phase IDs in a microstructure file to be sequential with no gaps.

        This is called after microstructure generation to ensure phase IDs are
        sequential (0, 1, 2, 3, ...) which is required by the THAMES-Hydration
        C++ code.

        Args:
            microstructure_path: Path to the .img microstructure file
            phase_mapping_path: Path to the _phase_mapping.json file
            output_microstructure_path: Output path for remapped microstructure (default: overwrite input)
            output_mapping_path: Output path for remapped mapping (default: overwrite input)

        Returns:
            Tuple of (old_to_new_id_map, new_phase_mapping)

        Example:
            Original IDs: 0, 1, 2, 3, 5, 8, 9 (gaps at 4, 6, 7)
            Remapped IDs: 0, 1, 2, 3, 4, 5, 6 (sequential)
        """
        if output_microstructure_path is None:
            output_microstructure_path = microstructure_path
        if output_mapping_path is None:
            output_mapping_path = phase_mapping_path

        self.logger.info(f"Remapping phase IDs in {microstructure_path}")

        # Step 1: Read the existing phase mapping
        with open(phase_mapping_path, 'r') as f:
            raw_data = json.load(f)

        # Handle nested structure (phase_id_mapping wrapper) or flat structure
        if 'phase_id_mapping' in raw_data:
            mapping_data = raw_data['phase_id_mapping']
            operation_name = raw_data.get('operation_name', '')
        else:
            mapping_data = raw_data
            operation_name = ''

        # Step 2: Read microstructure and find used phase IDs
        header_lines, voxel_data, dimensions = self._read_microstructure_file(microstructure_path)
        used_ids = set(np.unique(voxel_data))
        self.logger.info(f"Phase IDs found in microstructure: {sorted(used_ids)}")

        # Step 3: Create old-to-new ID mapping (sequential, no gaps)
        # VOID (0) and Electrolyte (1) always stay at 0 and 1 if present
        # Only remap IDs >= 2 to be sequential
        old_to_new: Dict[int, int] = {}

        # Keep 0 and 1 unchanged if present
        if 0 in used_ids:
            old_to_new[0] = 0
        if 1 in used_ids:
            old_to_new[1] = 1

        # Remap IDs >= 2 to be sequential starting from 2
        next_id = 2
        for old_id in sorted(used_ids):
            if old_id >= 2:
                old_to_new[old_id] = next_id
                next_id += 1

        self.logger.info(f"ID remapping: {old_to_new}")

        # Check if remapping is actually needed
        if all(old == new for old, new in old_to_new.items()):
            self.logger.info("Phase IDs are already sequential, no remapping needed")
            # Still return the mapping for consistency
            new_mapping = self._create_mapping_from_dict(mapping_data)
            return old_to_new, new_mapping

        # Step 4: Remap voxel data
        remapped_voxels = np.vectorize(lambda x: old_to_new.get(x, x))(voxel_data)

        # Step 5: Write remapped microstructure
        self._write_microstructure_file(
            output_microstructure_path, header_lines, remapped_voxels, dimensions
        )
        self.logger.info(f"Wrote remapped microstructure to {output_microstructure_path}")

        # Step 6: Update phase mapping
        new_mapping = self._remap_phase_mapping(mapping_data, old_to_new)

        # Step 7: Write updated phase mapping (preserve nested structure if original had it)
        output_data = new_mapping.to_dict()
        if operation_name:
            output_data = {
                "operation_name": operation_name,
                "phase_id_mapping": output_data
            }
        with open(output_mapping_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        self.logger.info(f"Wrote remapped phase mapping to {output_mapping_path}")

        return old_to_new, new_mapping

    def _read_microstructure_file(
        self, file_path: Path
    ) -> Tuple[List[str], np.ndarray, Tuple[int, int, int]]:
        """
        Read a microstructure file and return header, voxel data, and dimensions.

        Returns:
            Tuple of (header_lines, voxel_array, (x_size, y_size, z_size))
        """
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Parse header
        x_size = y_size = z_size = None
        header_end = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Handle THAMES format prefix
            if stripped.startswith('#THAMES:'):
                stripped = stripped[8:].strip()

            if stripped.startswith('X_Size:'):
                x_size = int(stripped.split(':')[1].strip())
            elif stripped.startswith('Y_Size:'):
                y_size = int(stripped.split(':')[1].strip())
            elif stripped.startswith('Z_Size:'):
                z_size = int(stripped.split(':')[1].strip())
            elif stripped.startswith('Image_Resolution:'):
                header_end = i + 1
                break

        if not all([x_size, y_size, z_size]):
            raise ValueError(f"Could not parse dimensions from {file_path}")

        header_lines = lines[:header_end]

        # Parse voxel data
        voxel_data = []
        for line in lines[header_end:]:
            line = line.strip()
            if line and not line.startswith('#'):
                values = [int(x) for x in line.split()]
                voxel_data.extend(values)

        total_voxels = x_size * y_size * z_size
        if len(voxel_data) < total_voxels:
            raise ValueError(
                f"Insufficient voxel data: got {len(voxel_data)}, expected {total_voxels}"
            )

        # Reshape with X as first axis, Y second, Z third (last axis varies fastest in C-order)
        # This matches the file format where Z varies fastest, then Y, then X
        voxel_array = np.array(voxel_data[:total_voxels]).reshape((x_size, y_size, z_size))

        return header_lines, voxel_array, (x_size, y_size, z_size)

    def _write_microstructure_file(
        self,
        file_path: Path,
        header_lines: List[str],
        voxel_data: np.ndarray,
        dimensions: Tuple[int, int, int]
    ) -> None:
        """
        Write a microstructure file with header and voxel data.
        """
        x_size, y_size, z_size = dimensions

        with open(file_path, 'w') as f:
            # Write header
            for line in header_lines:
                f.write(line)

            # Write voxel data (one value per line, z fastest, then y, then x)
            for x in range(x_size):
                for y in range(y_size):
                    for z in range(z_size):
                        f.write(f"{voxel_data[x, y, z]}\n")

    def _remap_phase_mapping(
        self,
        mapping_data: Dict[str, Any],
        old_to_new: Dict[int, int]
    ) -> PhaseIdMapping:
        """
        Create a new PhaseIdMapping with remapped IDs.
        """
        new_mapping = PhaseIdMapping()

        # Get the original mappings
        gem_to_micro = mapping_data.get('gem_to_micro', {})
        micro_to_gem = mapping_data.get('micro_to_gem', {})

        # Remap gem_to_micro
        for phase_name, old_id in gem_to_micro.items():
            if old_id in old_to_new:
                new_id = old_to_new[old_id]
                new_mapping.gem_to_micro[phase_name] = new_id
                new_mapping.micro_to_gem[new_id] = phase_name

        # Handle any phases in micro_to_gem that weren't in gem_to_micro
        for old_id_str, phase_name in micro_to_gem.items():
            old_id = int(old_id_str)
            if old_id in old_to_new:
                new_id = old_to_new[old_id]
                if new_id not in new_mapping.micro_to_gem:
                    new_mapping.micro_to_gem[new_id] = phase_name
                if phase_name not in new_mapping.gem_to_micro:
                    new_mapping.gem_to_micro[phase_name] = new_id

        # Update other fields
        new_mapping.has_clinker = mapping_data.get('has_clinker', False)

        # Remap clinker_phase_ids
        old_clinker_ids = mapping_data.get('clinker_phase_ids', {})
        for phase_name, old_id in old_clinker_ids.items():
            if old_id in old_to_new:
                new_mapping.clinker_phase_ids[phase_name] = old_to_new[old_id]

        # Update next_available_id
        if new_mapping.micro_to_gem:
            new_mapping.next_available_id = max(new_mapping.micro_to_gem.keys()) + 1
        else:
            new_mapping.next_available_id = FIRST_SOLID

        return new_mapping

    def _create_mapping_from_dict(self, mapping_data: Dict[str, Any]) -> PhaseIdMapping:
        """Create a PhaseIdMapping from a dictionary (e.g., loaded from JSON)."""
        mapping = PhaseIdMapping()

        mapping.gem_to_micro = mapping_data.get('gem_to_micro', {})
        mapping.micro_to_gem = {
            int(k): v for k, v in mapping_data.get('micro_to_gem', {}).items()
        }
        mapping.has_clinker = mapping_data.get('has_clinker', False)
        mapping.clinker_phase_ids = mapping_data.get('clinker_phase_ids', {})
        mapping.next_available_id = mapping_data.get('next_available_id', FIRST_SOLID)

        return mapping


# Module-level singleton
_phase_id_mapping_service: Optional[PhaseIdMappingService] = None


def get_phase_id_mapping_service() -> PhaseIdMappingService:
    """Get the singleton PhaseIdMappingService instance."""
    global _phase_id_mapping_service
    if _phase_id_mapping_service is None:
        _phase_id_mapping_service = PhaseIdMappingService()
    return _phase_id_mapping_service

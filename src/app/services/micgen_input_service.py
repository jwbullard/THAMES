#!/usr/bin/env python3
"""
Micgen Input File Generation Service for THAMES

Generates properly formatted input files for the micgen.c microstructure generation program.
Converts THAMES MixDesign objects into the sequential input format required by micgen.

Author: THAMES Development Team
Date: November 2025
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
import json
import os
import numpy as np
from scipy.stats import lognorm

from app.models.mix_design import MixDesign, MixDesignComponentData
from app.models.material import Material
from app.models.psd_data import PSDData
from app.models.clinker_extension import ClinkerExtension
from app.services.material_service import MaterialService
from app.services.phase_id_mapping_service import PhaseIdMappingService, PhaseIdMapping, CLINKER_PHASES
from app.services.psd_data_service import PSDDataService


logger = logging.getLogger(__name__)


class MicgenInputGenerationError(Exception):
    """Raised when input file generation fails."""
    pass


class MicgenInputService:
    """
    Service for generating micgen input files from THAMES Mix Design objects.

    Responsibilities:
    - Convert MixDesign to micgen sequential input format
    - Handle phase ID mapping using PhaseIdMappingService
    - Retrieve and format clinker correlation data
    - Generate PSD (particle size distribution) data for each phase
    - Handle optional features (aggregate slab, flocculation, etc.)
    - Write properly formatted input files

    Input Sequence (from micgen-input.md):
    1. Random number seed (negative integer)
    2. SPECSIZE (2)
    3. X_size, Y_size, Z_size (voxels)
    4. Image_resolution (micrometers)
    5. [Optional] ADDAGG (3) - aggregate slab
    6. ADDPART (4)
    7. Particle shape mode (0=spheres, 1=real-shape, 2=mixed)
    8. Volume fractions (clinker, other solids, electrolyte, void)
    9. Phase-by-phase data (IDs, volume fractions, PSDs)
    10. Dispersion factor
    11. [Optional] FLOCC (5) - flocculation
    12. [If clinker > 0] DISTRIB (6) - clinker correlations
    13. [Optional] ADDVOID (7)
    14. ONEVOX (9)
    15. OUTPUTMIC (10) - output file names
    16. EXIT (1)
    """

    # Menu command numbers from micgen.c lines 115-124
    EXIT = 1
    SPECSIZE = 2
    ADDAGG = 3
    ADDPART = 4
    FLOCC = 5
    DISTRIB = 6
    ADDVOID = 7
    CONNECTIVITY = 8
    ONEVOX = 9
    OUTPUTMIC = 10

    # Shape mode constants
    SPHERES = 0
    REALSHAPE = 1
    MIXEDSHAPE = 2

    def __init__(self, material_service: MaterialService, psd_service: PSDDataService):
        """
        Initialize the micgen input generation service.

        Args:
            material_service: Service for retrieving material data
            psd_service: Service for retrieving PSD data
        """
        self.material_service = material_service
        self.psd_service = psd_service
        self.phase_mapping_service = PhaseIdMappingService()

    def generate_input_file(
        self,
        mix_design: MixDesign,
        output_path: Path,
        microstructure_filename: str = "microstructure.img",
        particle_id_filename: str = "particle_ids.img",
        add_aggregate_slab: bool = False,
        add_void_phase: bool = False,
        shape_database_path: Optional[Path] = None
    ) -> PhaseIdMapping:
        """
        Generate a complete micgen input file from a MixDesign object.

        Args:
            mix_design: The THAMES mix design to convert
            output_path: Path where the input file will be written
            microstructure_filename: Name for the output microstructure file
            particle_id_filename: Name for the output particle ID file
            add_aggregate_slab: Whether to add a one-voxel aggregate slab
            add_void_phase: Whether to add void phase after particles
            shape_database_path: Path to shape database directory (if using real shapes)

        Returns:
            PhaseIdMapping object containing the phase ID assignments

        Raises:
            MicgenInputGenerationError: If input generation fails
        """
        logger.info(f"Generating micgen input file for mix design: {mix_design.name}")

        try:
            # Step 1: Create phase ID mapping
            phase_mapping = self._create_phase_mapping(mix_design)

            # Step 2: Calculate volume fractions
            volume_fractions = self._calculate_volume_fractions(mix_design, phase_mapping)

            # Step 3: Collect material data for each phase
            phase_data = self._collect_phase_data(mix_design, phase_mapping)

            # Step 4: Determine shape mode and shape set name
            shape_mode = self._determine_shape_mode(mix_design)
            shape_set_name = None
            if shape_mode != self.SPHERES:
                # Get the shape set name from materials - find a material using real shapes
                shape_set_name = self._find_shape_set_from_materials(mix_design)
                if not shape_set_name:
                    raise MicgenInputGenerationError(
                        "Real-shape mode detected but no valid shape set found in materials"
                    )
                logger.info(f"Using shape set from material: {shape_set_name}")

            # Step 5: Determine if ADDVOID should be enabled
            # Auto-enable ADDVOID when void volume fraction > 0 (from VOID components)
            # Note: This is separate from air_volume_fraction which is already in void_vfrac
            effective_add_void = add_void_phase or (volume_fractions['void_vfrac'] > 0)
            if effective_add_void and not add_void_phase:
                logger.info(f"Auto-enabling ADDVOID due to void_vfrac={volume_fractions['void_vfrac']:.4f}")

            # Step 6: Generate input lines
            input_lines = self._generate_input_sequence(
                mix_design=mix_design,
                phase_mapping=phase_mapping,
                volume_fractions=volume_fractions,
                phase_data=phase_data,
                shape_mode=shape_mode,
                microstructure_filename=microstructure_filename,
                particle_id_filename=particle_id_filename,
                add_aggregate_slab=add_aggregate_slab,
                add_void_phase=effective_add_void,
                shape_database_path=shape_database_path,
                shape_set_name=shape_set_name,
                output_dir=output_path.parent
            )

            # Step 7: Write to file
            self._write_input_file(output_path, input_lines)

            logger.info(f"Successfully generated micgen input file: {output_path}")
            logger.info(f"Phase ID mapping: {phase_mapping.to_dict()}")

            return phase_mapping

        except Exception as e:
            logger.error(f"Failed to generate micgen input file: {e}", exc_info=True)
            raise MicgenInputGenerationError(f"Input generation failed: {e}") from e

    def _create_phase_mapping(self, mix_design: MixDesign) -> PhaseIdMapping:
        """
        Create phase ID mapping for this mix design.

        Uses PhaseIdMappingService to assign phase IDs dynamically based on
        the materials in the mix.

        Args:
            mix_design: The mix design to map

        Returns:
            PhaseIdMapping object with bidirectional phase name <-> ID mapping
        """
        # Import here to avoid circular dependency
        from app.widgets.material_selector import MaterialSelector

        # Collect all materials with their phases in the format expected by PhaseIdMappingService
        # Format: [{'material_name': str, 'phases': [{'gem_phase_name': str, 'mass_fraction': float}, ...]}, ...]
        material_phases = []

        for component in mix_design.components:
            material_id = component.get('material_id')

            # Skip VOID pseudo-material - it has no phases
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                logger.debug("Skipping VOID pseudo-material in phase mapping")
                continue

            material = self.material_service.get_by_id(material_id)
            if not material:
                raise MicgenInputGenerationError(
                    f"Material ID {component['material_id']} not found"
                )

            # Build phases list for this material, scaling mass fractions by component fraction
            phases_list = []
            for phase in material.phases:
                phases_list.append({
                    'gem_phase_name': phase.gem_phase_name,
                    'mass_fraction': phase.mass_fraction * component['mass_fraction']
                })

            material_phases.append({
                'material_name': material.name,
                'phases': phases_list
            })

            logger.debug(f"Material {material.name}: {len(phases_list)} phases")

        # Generate phase ID mapping
        phase_mapping = self.phase_mapping_service.create_mapping_from_mix(
            material_phases=material_phases,
            include_hydration_products=False  # Don't include hydration products in initial microstructure
        )

        return phase_mapping

    def _calculate_volume_fractions(
        self,
        mix_design: MixDesign,
        phase_mapping: PhaseIdMapping
    ) -> Dict[str, float]:
        """
        Calculate volume fractions for micgen input.

        Micgen requires volume fractions for the PASTE only (excluding aggregate):
        - PC clinker volume fraction (sum of all 6 clinker phases)
        - Other solids volume fraction (non-clinker solid phases)
        - Electrolyte volume fraction
        - Void volume fraction

        These 4 fractions must sum to 1.0 for the paste.
        Aggregate is handled separately via ADDAGG.

        Volume fractions are calculated from mass fractions and specific gravities:
        1. Calculate volume of each component: V_i = m_i / SG_i
        2. Calculate total paste volume: V_paste = sum(V_i)
        3. Calculate volume fraction: φ_i = V_i / V_paste

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping

        Returns:
            Dictionary with keys: 'clinker_vfrac', 'other_solid_vfrac',
                                  'electrolyte_vfrac', 'void_vfrac'

        Raises:
            MicgenInputGenerationError: If void volume fraction >= electrolyte volume fraction
        """
        # Import here to avoid circular dependency
        from app.widgets.material_selector import MaterialSelector

        # Step 1: Calculate volumes for each component (using mass_fraction as proxy for mass)
        # We use mass_fraction / SG to get relative volumes, then normalize
        clinker_volume = 0.0
        other_solid_volume = 0.0
        void_volume = 0.0

        for component in mix_design.components:
            material_id = component.get('material_id')
            mass_fraction = component.get('mass_fraction', 0.0)
            specific_gravity = component.get('specific_gravity', 3.15)

            # Skip aggregate components (they're handled separately)
            material_type = component.get('material_type', '')
            if material_type == 'aggregate':
                continue

            # Skip water component (handled separately)
            material_name = component.get('material_name', '')
            if material_name == 'Water' or material_type == 'water':
                continue

            # Calculate relative volume: V = m / SG
            component_volume = mass_fraction / specific_gravity if specific_gravity > 0 else 0.0

            # Check for VOID pseudo-material
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                void_volume += component_volume
                logger.debug(f"VOID component: mass_fraction={mass_fraction:.4f}, volume={component_volume:.6f}")
                continue

            # Skip components without valid material_id
            if not material_id:
                continue

            material = self.material_service.get_by_id(material_id)
            if not material:
                logger.warning(f"Material ID {material_id} not found, skipping")
                continue

            # Check if material is clinker or contains clinker phases
            logger.info(f"Material '{material.name}': is_clinker={material.is_clinker}, has_clinker={material.has_clinker}")
            if material.is_clinker or material.has_clinker:
                clinker_volume += component_volume
                logger.info(f"Clinker material '{material.name}': mass_fraction={mass_fraction:.4f}, "
                            f"SG={specific_gravity:.2f}, volume={component_volume:.6f}")
            else:
                other_solid_volume += component_volume
                logger.debug(f"Other solid '{material.name}': mass_fraction={mass_fraction:.4f}, "
                            f"SG={specific_gravity:.2f}, volume={component_volume:.6f}")

        # Step 2: Calculate water volume from water-binder ratio
        # w/b = mass_water / mass_binder
        # For paste: mass_water = w/b × mass_binder
        # Volume_water = mass_water / SG_water = mass_water / 1.0 = mass_water
        # Since we're using mass_fractions, water "volume" = w/b × (clinker_vol × SG_clinker + other_vol × SG_other)
        # Simpler approach: use the water_reference_mass if available, or calculate from w/b ratio

        # Get total binder mass fraction (clinker + other solids in mass terms)
        total_binder_mass_frac = 0.0
        for component in mix_design.components:
            material_id = component.get('material_id')
            material_type = component.get('material_type', '')
            material_name = component.get('material_name', '')

            # Skip aggregate, water, and VOID
            if material_type == 'aggregate':
                continue
            if material_name == 'Water' or material_type == 'water':
                continue
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                continue
            if not material_id:
                continue

            total_binder_mass_frac += component.get('mass_fraction', 0.0)

        # Water volume (relative) = w/b × binder_mass / SG_water
        # Since SG_water = 1.0, water_volume = w/b × total_binder_mass_frac
        water_binder_ratio = mix_design.water_binder_ratio or 0.485
        water_volume = water_binder_ratio * total_binder_mass_frac

        logger.debug(f"Water calculation: w/b={water_binder_ratio:.3f}, binder_mass_frac={total_binder_mass_frac:.4f}, "
                    f"water_volume={water_volume:.6f}")

        # Step 3: Calculate total paste volume and normalize to get fractions
        total_paste_volume = clinker_volume + other_solid_volume + water_volume + void_volume

        if total_paste_volume <= 0:
            raise MicgenInputGenerationError("Total paste volume is zero - no valid components found")

        # Normalize to get volume fractions
        clinker_vfrac = clinker_volume / total_paste_volume
        other_solid_vfrac = other_solid_volume / total_paste_volume
        electrolyte_vfrac = water_volume / total_paste_volume
        void_vfrac = void_volume / total_paste_volume

        # NOTE: air_volume_fraction from mix design is for concrete air entrainment
        # and should NOT be included in paste volume fractions.
        # Only "paste void" (VOID pseudo-material added as a component) is included.

        logger.info(f"Volume fractions (paste only): clinker={clinker_vfrac:.4f}, other_solids={other_solid_vfrac:.4f}, "
                   f"electrolyte={electrolyte_vfrac:.4f}, paste_void={void_vfrac:.4f}, "
                   f"total={clinker_vfrac + other_solid_vfrac + electrolyte_vfrac + void_vfrac:.4f}")

        # Validate void volume fraction
        if void_vfrac >= electrolyte_vfrac and void_vfrac > 0:
            raise MicgenInputGenerationError(
                f"Void volume fraction ({void_vfrac:.4f}) must be less than "
                f"electrolyte volume fraction ({electrolyte_vfrac:.4f}). "
                f"Reduce the VOID amount or increase water content."
            )

        return {
            'clinker_vfrac': clinker_vfrac,
            'other_solid_vfrac': other_solid_vfrac,
            'electrolyte_vfrac': electrolyte_vfrac,
            'void_vfrac': void_vfrac
        }

    def _aggregate_phases_by_name(
        self,
        mix_design: MixDesign
    ) -> Dict[str, Dict]:
        """
        Aggregate all phase contributions by GEM phase name.

        When multiple materials contribute to the same phase (e.g., two different
        cements both contain Alite), this method combines their contributions.

        Args:
            mix_design: The mix design

        Returns:
            Dictionary mapping GEM phase name to aggregated data:
            {
                'Alite': {
                    'total_mass_fraction': 0.42,
                    'contributions': [
                        {
                            'material_id': 1,
                            'material_name': 'Cement A',
                            'mass_fraction': 0.25,
                            'volume_fraction': 0.20,
                            'specific_gravity': 3.15,
                            'psd_data_id': 5
                        },
                        ...
                    ]
                },
                ...
            }
        """
        # Import here to avoid circular dependency
        from app.widgets.material_selector import MaterialSelector

        phase_aggregates = {}

        for component in mix_design.components:
            material_id = component.get('material_id')

            # Skip VOID pseudo-material - it has no phases or PSD
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                logger.debug("Skipping VOID pseudo-material in phase aggregation")
                continue

            # Skip components without valid material_id
            if not material_id:
                continue

            material = self.material_service.get_by_id(material_id)
            if not material:
                raise MicgenInputGenerationError(
                    f"Material ID {material_id} not found"
                )

            component_mass_frac = component['mass_fraction']
            component_vol_frac = component['volume_fraction']

            # Process each phase in this material
            for material_phase in material.phases:
                phase_name = material_phase.gem_phase_name

                # Initialize aggregate for this phase if not seen before
                if phase_name not in phase_aggregates:
                    phase_aggregates[phase_name] = {
                        'total_mass_fraction': 0.0,
                        'total_volume_fraction': 0.0,
                        'contributions': []
                    }

                # Calculate this material's contribution to this phase
                phase_mass_in_component = material_phase.mass_fraction * component_mass_frac

                # For volume fraction, we need to weight by the phase's fraction of the material
                # Assuming phase mass fractions sum to 1.0 in the material
                phase_vol_in_component = material_phase.mass_fraction * component_vol_frac

                # Add to aggregate
                phase_aggregates[phase_name]['total_mass_fraction'] += phase_mass_in_component
                phase_aggregates[phase_name]['total_volume_fraction'] += phase_vol_in_component

                # Record this contribution for PSD weighting and shape info
                phase_aggregates[phase_name]['contributions'].append({
                    'material_id': material.id,
                    'material_name': material.name,
                    'mass_fraction': phase_mass_in_component,
                    'volume_fraction': phase_vol_in_component,
                    'specific_gravity': material.specific_gravity,
                    'psd_data_id': material.psd_data_id,
                    # Shape info - clinker materials will use cement_shape_set from mix design
                    'is_clinker': material.is_clinker or material.has_clinker,
                    'particle_shape_type': getattr(material, 'particle_shape_type', 0) or 0,
                    'particle_shape_set': getattr(material, 'particle_shape_set', None)
                })

        logger.debug(f"Aggregated {len(phase_aggregates)} unique phases from mix")
        return phase_aggregates

    def _calculate_solids_volume_fraction(
        self,
        phase_total_volume: float,
        total_solids_volume: float
    ) -> float:
        """
        Calculate volume fraction on solids-only basis.

        Micgen requires volume fractions normalized to the solid portion only,
        excluding electrolyte and void.

        Args:
            phase_total_volume: Phase volume fraction on total system basis
            total_solids_volume: Total solids volume fraction

        Returns:
            Volume fraction on solids-only basis
        """
        if total_solids_volume <= 0.0:
            raise MicgenInputGenerationError("Total solids volume fraction must be > 0")

        return phase_total_volume / total_solids_volume

    def _combine_psd_data(
        self,
        contributions: List[Dict],
        resolution: float
    ) -> Dict:
        """
        Combine PSD data from multiple material contributions.

        When multiple materials contribute to the same phase, their PSDs must be
        combined with weighting based on their relative contributions.

        Args:
            contributions: List of contribution dicts with psd_data_id and mass_fraction
            resolution: Microstructure resolution in micrometers/voxel

        Returns:
            Combined PSD data dictionary with size classes and fractions
        """
        if not contributions:
            raise MicgenInputGenerationError("No contributions to combine")

        # If only one contribution, just use its PSD directly
        if len(contributions) == 1:
            psd = self.psd_service.get_by_id(contributions[0]['psd_data_id'])
            if not psd:
                raise MicgenInputGenerationError(
                    f"PSD data ID {contributions[0]['psd_data_id']} not found"
                )
            return self._psd_to_dict(psd, resolution)

        # Multiple contributions - combine PSDs with weighted averaging
        logger.info(f"Combining {len(contributions)} PSD contributions with weighted averaging")

        # Step 1: Get discretized PSDs for all contributions
        psd_data_list = []
        for contrib in contributions:
            psd = self.psd_service.get_by_id(contrib['psd_data_id'])
            if not psd:
                raise MicgenInputGenerationError(
                    f"PSD data ID {contrib['psd_data_id']} not found"
                )
            psd_dict = self._psd_to_dict(psd, resolution)
            psd_data_list.append({
                'weight': contrib['mass_fraction'],
                'size_classes': psd_dict['size_classes_um'],  # [(d, f), ...]
                'mode': psd_dict['mode']
            })

        # Step 2: Collect all unique diameter values from all PSDs
        all_diameters = set()
        for psd_data in psd_data_list:
            for diameter, _ in psd_data['size_classes']:
                all_diameters.add(diameter)

        # Sort diameters for interpolation
        sorted_diameters = sorted(all_diameters)

        # Step 3: For each PSD, interpolate onto common diameter grid
        combined_fractions = np.zeros(len(sorted_diameters))

        for psd_data in psd_data_list:
            # Extract diameters and fractions from this PSD
            diameters = np.array([d for d, _ in psd_data['size_classes']])
            fractions = np.array([f for _, f in psd_data['size_classes']])

            # Interpolate onto common diameter grid
            # Use linear interpolation, with zero outside original range
            interpolated = np.interp(
                sorted_diameters,
                diameters,
                fractions,
                left=0.0,
                right=0.0
            )

            # Add weighted contribution to combined distribution
            combined_fractions += interpolated * psd_data['weight']

        # Step 4: Renormalize to ensure sum = 1.0
        total = np.sum(combined_fractions)
        if total > 0:
            combined_fractions /= total
        else:
            raise MicgenInputGenerationError(
                "Combined PSD has zero total volume fraction"
            )

        # Step 5: Convert back to list of tuples format
        size_classes_um = [
            (diameter, float(fraction))
            for diameter, fraction in zip(sorted_diameters, combined_fractions)
            if fraction > 1e-6  # Remove negligible fractions
        ]

        logger.info(
            f"Combined PSD has {len(size_classes_um)} size classes "
            f"(from {sum(len(p['size_classes']) for p in psd_data_list)} total classes)"
        )

        return {
            'mode': 'combined',  # Mark as combined from multiple sources
            'size_classes_um': size_classes_um,
            'raw_psd': None  # No single raw PSD for combined distribution
        }

    def _psd_to_dict(self, psd: PSDData, resolution: float) -> Dict:
        """
        Convert PSD database object to dictionary format with discretized size classes.

        Args:
            psd: PSD data from database
            resolution: Microstructure resolution in micrometers/voxel

        Returns:
            Dictionary with mode and discretized size classes in micrometers
        """
        mode = psd.psd_mode or 'log_normal'

        if mode == 'rosin_rammler':
            size_classes_um = self._discretize_rosin_rammler(
                psd.psd_d50 or 15.0,
                psd.psd_n or 1.0,
                psd.psd_dmax or 75.0
            )
        elif mode == 'log_normal':
            size_classes_um = self._discretize_log_normal(
                psd.psd_median or 15.0,
                psd.psd_spread or 0.5
            )
        elif mode == 'fuller':
            size_classes_um = self._discretize_fuller_thompson(
                psd.psd_exponent or 0.5,
                psd.psd_dmax or 75.0
            )
        elif mode == 'custom':
            size_classes_um = self._parse_custom_psd(psd.psd_custom_points)
        else:  # default mode
            # Generate default log-normal distribution
            size_classes_um = self._discretize_log_normal(15.0, 0.5)

        return {
            'mode': mode,
            'size_classes_um': size_classes_um,  # [(diameter_um, vol_frac), ...]
            'raw_psd': psd
        }

    def _discretize_rosin_rammler(
        self,
        d50: float,
        n: float,
        dmax: float
    ) -> List[Tuple[float, float]]:
        """
        Discretize Rosin-Rammler distribution to size classes.

        R = 1 - exp(-(d/d50)^n)

        Args:
            d50: Characteristic diameter (μm)
            n: Distribution parameter
            dmax: Maximum diameter (μm)

        Returns:
            List of (diameter_um, volume_fraction) tuples
        """
        # Generate logarithmically-spaced diameters
        max_diameter = min(75.0, dmax)
        diameters = np.logspace(np.log10(0.25), np.log10(max_diameter), 30)

        # Rosin-Rammler cumulative distribution
        cumulative = 1 - np.exp(-((diameters / d50) ** n))

        # Convert to differential (volume fractions)
        volume_fractions = np.diff(np.concatenate([[0], cumulative]))

        # Ensure same length
        if len(volume_fractions) < len(diameters):
            volume_fractions = np.append(volume_fractions, 0)

        # Normalize
        volume_fractions = volume_fractions / np.sum(volume_fractions)

        return [(float(d), float(f)) for d, f in zip(diameters, volume_fractions) if f > 1e-6]

    def _discretize_log_normal(
        self,
        median: float,
        spread: float
    ) -> List[Tuple[float, float]]:
        """
        Discretize log-normal distribution to size classes.

        Args:
            median: Median diameter (μm)
            spread: Distribution spread parameter (sigma)

        Returns:
            List of (diameter_um, volume_fraction) tuples
        """
        # Generate logarithmically-spaced diameters
        diameters = np.logspace(np.log10(0.25), np.log10(75.0), 30)

        # Log-normal PDF
        pdf_values = lognorm.pdf(diameters, s=spread, scale=median)

        # Normalize to get volume fractions
        volume_fractions = pdf_values / np.sum(pdf_values)

        return [(float(d), float(f)) for d, f in zip(diameters, volume_fractions) if f > 1e-6]

    def _discretize_fuller_thompson(
        self,
        exponent: float,
        dmax: float
    ) -> List[Tuple[float, float]]:
        """
        Discretize Fuller-Thompson distribution to size classes.

        P(d) = (d/dmax)^exponent

        Args:
            exponent: Distribution exponent (typically 0.5 for Fuller)
            dmax: Maximum diameter (μm)

        Returns:
            List of (diameter_um, volume_fraction) tuples
        """
        max_diameter = min(75.0, dmax)
        diameters = np.logspace(np.log10(0.25), np.log10(max_diameter), 30)

        # Fuller-Thompson cumulative distribution
        cumulative = (diameters / max_diameter) ** exponent

        # Convert to differential
        volume_fractions = np.diff(np.concatenate([[0], cumulative]))

        # Ensure same length
        if len(volume_fractions) < len(diameters):
            volume_fractions = np.append(volume_fractions, 0)

        # Normalize
        volume_fractions = volume_fractions / np.sum(volume_fractions)

        return [(float(d), float(f)) for d, f in zip(diameters, volume_fractions) if f > 1e-6]

    def _parse_custom_psd(self, custom_points_json: Optional[str]) -> List[Tuple[float, float]]:
        """
        Parse custom PSD points from JSON.

        Args:
            custom_points_json: JSON string with custom PSD data

        Returns:
            List of (diameter_um, volume_fraction) tuples
        """
        if not custom_points_json:
            # Fallback to default
            return self._discretize_log_normal(15.0, 0.5)

        try:
            points = json.loads(custom_points_json)
            # Expecting format: [[d1, f1], [d2, f2], ...]
            if isinstance(points, list) and len(points) > 0:
                result = [(float(p[0]), float(p[1])) for p in points if len(p) >= 2]

                # Normalize
                total = sum(f for _, f in result)
                if total > 0:
                    result = [(d, f/total) for d, f in result]

                return result
        except Exception as e:
            logger.warning(f"Failed to parse custom PSD: {e}, using default")

        # Fallback
        return self._discretize_log_normal(15.0, 0.5)

    def _convert_psd_to_size_classes(
        self,
        psd_dict: Dict,
        resolution: float
    ) -> List[Dict]:
        """
        Convert PSD data to micgen size class format.

        Micgen expects:
        - Diameter in INTEGER voxel units
        - Volume fraction for each size class

        Args:
            psd_dict: PSD data dictionary from _psd_to_dict with 'size_classes_um'
            resolution: Microstructure resolution in micrometers/voxel

        Returns:
            List of size class dictionaries:
            [
                {'diameter_voxels': 2, 'volume_fraction': 0.15},
                {'diameter_voxels': 5, 'volume_fraction': 0.35},
                ...
            ]
        """
        size_classes_um = psd_dict.get('size_classes_um', [])

        if not size_classes_um:
            # Fallback to single default size class
            logger.warning("No size classes in PSD, using default 10μm particle")
            return [{'diameter_voxels': 10, 'volume_fraction': 1.0}]

        # Convert diameters from micrometers to voxels and consolidate by integer diameter
        # micgen.c expects integer diameters, so we need to combine fractions for same diameters
        diameter_fractions = {}  # {int_diameter: total_vol_frac}

        for diameter_um, vol_frac in size_classes_um:
            diameter_voxels = diameter_um / resolution

            # Round to nearest integer
            int_diameter = int(round(diameter_voxels))

            # Skip zero-diameter particles (too small)
            if int_diameter < 1:
                continue

            # Accumulate volume fractions for same integer diameter
            if int_diameter in diameter_fractions:
                diameter_fractions[int_diameter] += vol_frac
            else:
                diameter_fractions[int_diameter] = vol_frac

        # Convert to list of dicts, sorted by diameter
        size_classes = [
            {'diameter_voxels': d, 'volume_fraction': f}
            for d, f in sorted(diameter_fractions.items())
        ]

        # Renormalize after filtering and combining
        total = sum(sc['volume_fraction'] for sc in size_classes)
        if total > 0:
            for sc in size_classes:
                sc['volume_fraction'] /= total

        # If all were filtered out, use minimum size
        if not size_classes:
            logger.warning("All particles too small for resolution, using 1 voxel minimum")
            return [{'diameter_voxels': 1, 'volume_fraction': 1.0}]

        logger.debug(f"Generated {len(size_classes)} size classes from PSD (consolidated from {len(size_classes_um)} original)")
        return size_classes

    def _order_phases_for_micgen(
        self,
        phase_data: List[Dict],
        phase_mapping: PhaseIdMapping
    ) -> List[Dict]:
        """
        Order phases correctly for micgen input.

        Phases should be ordered by their phase ID:
        - Clinker phases (IDs 2-7) first
        - Other phases (IDs 8+) after

        Args:
            phase_data: Unordered list of phase data dictionaries
            phase_mapping: Phase ID mapping

        Returns:
            Phase data list sorted by phase ID
        """
        return sorted(phase_data, key=lambda p: p['phase_id'])

    def _determine_phase_shape(
        self,
        contributions: List[Dict],
        phase_name: str,
        mix_design: MixDesign
    ) -> Tuple[int, Optional[str]]:
        """
        Determine the particle shape settings for a phase.

        Rules:
        - Clinker phases use the shape settings from the clinker/cement material
        - Non-clinker phases use shape settings from the dominant contributor material
        - If multiple materials contribute, use the one with highest volume fraction

        Args:
            contributions: List of material contributions to this phase
            phase_name: GEM phase name
            mix_design: Mix design object (not used for shape, kept for API compatibility)

        Returns:
            Tuple of (shape_type, shape_set):
            - shape_type: 0=SPHERES, 1=REALSHAPE
            - shape_set: Name of shape set if real shapes, None otherwise
        """
        if not contributions:
            return (self.SPHERES, None)

        # Check if this is a clinker phase
        is_clinker_phase = phase_name in CLINKER_PHASES

        # Check if any contributor is a clinker material
        clinker_contributors = [c for c in contributions if c.get('is_clinker', False)]

        if is_clinker_phase or clinker_contributors:
            # Use the clinker material's shape settings
            # Find the dominant clinker contributor (by volume fraction)
            if clinker_contributors:
                dominant_clinker = max(clinker_contributors, key=lambda c: c.get('volume_fraction', 0.0))
            else:
                # Phase is clinker but contributor not marked as clinker - use dominant contributor
                dominant_clinker = max(contributions, key=lambda c: c.get('volume_fraction', 0.0))

            shape_type = dominant_clinker.get('particle_shape_type', 0) or 0
            shape_set = dominant_clinker.get('particle_shape_set', None)

            if shape_type == self.REALSHAPE and shape_set:
                return (self.REALSHAPE, shape_set)
            else:
                return (self.SPHERES, None)

        # Non-clinker phase - use dominant contributor's shape settings
        # Sort by volume fraction (descending) to find dominant contributor
        sorted_contributions = sorted(
            contributions,
            key=lambda c: c.get('volume_fraction', 0.0),
            reverse=True
        )

        dominant = sorted_contributions[0]
        shape_type = dominant.get('particle_shape_type', 0) or 0
        shape_set = dominant.get('particle_shape_set', None)

        if shape_type == self.REALSHAPE and shape_set:
            return (self.REALSHAPE, shape_set)
        else:
            return (self.SPHERES, None)

    def _find_default_shape_set(self, phase_data: List[Dict]) -> Optional[str]:
        """
        Find a default shape set from the phase data.

        Used for MIXEDSHAPE mode when no explicit default is provided.
        Returns the shape set of the first phase that uses real shapes.

        Args:
            phase_data: List of phase data dictionaries

        Returns:
            Shape set name, or None if no phases use real shapes
        """
        for phase in phase_data:
            if phase.get('shape_type') == self.REALSHAPE and phase.get('shape_set'):
                return phase['shape_set']
        return None

    def _find_shape_set_from_materials(self, mix_design: MixDesign) -> Optional[str]:
        """
        Find a shape set name from the materials in the mix design.

        Iterates through all materials and returns the first real-shape set found.
        Used as the default shape set for REALSHAPE and MIXEDSHAPE modes.

        Args:
            mix_design: The mix design

        Returns:
            Shape set name, or None if no materials use real shapes
        """
        # Import here to avoid circular dependency
        from app.widgets.material_selector import MaterialSelector

        for component in mix_design.components:
            material_id = component.get('material_id')

            # Skip VOID pseudo-material
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                continue

            material = self.material_service.get_by_id(material_id)
            if not material:
                continue

            # Check if this material uses real shapes
            shape_type = getattr(material, 'particle_shape_type', 0) or 0
            shape_set = getattr(material, 'particle_shape_set', None)

            if shape_type == self.REALSHAPE and shape_set:
                logger.debug(f"Found shape set '{shape_set}' from material '{material.name}'")
                return shape_set

        return None

    def _collect_phase_data(
        self,
        mix_design: MixDesign,
        phase_mapping: PhaseIdMapping
    ) -> List[Dict]:
        """
        Collect data for each solid phase in the mix.

        IMPORTANT: Clinker phases (Alite, Belite, Aluminate, Ferrite, Arcanite, Thenardite)
        are handled specially:
        - All 6 clinker phases are COMBINED into a single entry as "Alite" (phase ID 2)
        - The combined volume fraction includes all 6 phases
        - The PSD is the cement's PSD (clinker phases share the same PSD)
        - Later, DISTRIB transforms Alite particles into individual clinker phases

        Non-clinker phases (Gypsum, Hemihydrate, etc.) are added individually.

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping

        Returns:
            List of phase data dictionaries
        """
        from app.services.phase_id_mapping_service import CLINKER_PHASES

        logger.info("Collecting phase data for micgen input")

        # Step 1: Aggregate all phases by name
        phase_aggregates = self._aggregate_phases_by_name(mix_design)

        # Step 2: Combine clinker phases into a single "Alite" entry
        # All clinker phases will be placed as Alite particles, then DISTRIB transforms them
        clinker_volume_fraction = 0.0
        clinker_contributions = []
        clinker_phase_names = set(CLINKER_PHASES)

        for phase_name in list(phase_aggregates.keys()):
            if phase_name in clinker_phase_names:
                aggregate = phase_aggregates[phase_name]
                clinker_volume_fraction += aggregate['total_volume_fraction']
                clinker_contributions.extend(aggregate['contributions'])
                # Remove individual clinker phases - they'll be combined as Alite
                del phase_aggregates[phase_name]
                logger.debug(f"Combining clinker phase '{phase_name}' into Alite")

        # Add combined clinker as "Alite" if there are clinker phases
        if clinker_volume_fraction > 0 and clinker_contributions:
            phase_aggregates['Alite'] = {
                'total_mass_fraction': sum(c['mass_fraction'] for c in clinker_contributions),
                'total_volume_fraction': clinker_volume_fraction,
                'contributions': clinker_contributions,
                'is_combined_clinker': True  # Flag to indicate this is combined clinker
            }
            logger.info(f"Combined {len(clinker_contributions)} clinker contributions into Alite "
                       f"with volume fraction {clinker_volume_fraction:.4f}")

        # Step 3: Calculate total solids volume fraction
        total_solids_vol = sum(
            agg['total_volume_fraction']
            for agg in phase_aggregates.values()
        )

        if total_solids_vol <= 0.0:
            raise MicgenInputGenerationError("No solid phases in mix design")

        # Step 4: Build phase data list
        phase_data = []

        for phase_name, aggregate in phase_aggregates.items():
            # Get phase ID from mapping
            if phase_name not in phase_mapping.gem_to_micro:
                logger.warning(f"Phase '{phase_name}' not in phase mapping, skipping")
                continue

            phase_id = phase_mapping.gem_to_micro[phase_name]

            # Calculate volume fraction on solids-only basis
            vol_frac_solids = self._calculate_solids_volume_fraction(
                aggregate['total_volume_fraction'],
                total_solids_vol
            )

            # Combine PSD data from all contributions
            psd_dict = self._combine_psd_data(
                aggregate['contributions'],
                mix_design.resolution
            )

            # Convert PSD to size classes
            size_classes = self._convert_psd_to_size_classes(
                psd_dict,
                mix_design.resolution
            )

            # Determine shape type and shape set for this phase
            # Use the dominant contributor's shape settings
            shape_type, shape_set = self._determine_phase_shape(
                aggregate['contributions'],
                phase_name,
                mix_design
            )

            # Build phase data entry
            phase_data.append({
                'phase_id': phase_id,
                'gem_phase_name': phase_name,
                'volume_fraction_solids_basis': vol_frac_solids,
                'size_classes': size_classes,
                'shape_type': shape_type,
                'shape_set': shape_set,
                'is_combined_clinker': aggregate.get('is_combined_clinker', False)
            })

        # Step 5: Order phases by ID
        phase_data = self._order_phases_for_micgen(phase_data, phase_mapping)

        logger.info(f"Collected data for {len(phase_data)} phases")
        return phase_data

    def _determine_shape_mode(self, mix_design: MixDesign) -> int:
        """
        Determine particle shape mode for micgen.

        Examines all materials in the mix to determine:
        - SPHERES (0): All materials use spherical particles
        - REALSHAPE (1): All materials use the same real-shape set
        - MIXEDSHAPE (2): Materials use different shapes (some spheres, some real-shapes, or different shape sets)

        Shape settings come from each material's particle_shape_type and particle_shape_set fields.
        Clinker materials and non-clinker materials are treated the same way.

        Args:
            mix_design: The mix design

        Returns:
            Shape mode: 0=SPHERES, 1=REALSHAPE, 2=MIXEDSHAPE
        """
        # Import here to avoid circular dependency
        from app.widgets.material_selector import MaterialSelector

        # Track shape configurations for all materials
        has_spheres = False
        has_real_shapes = False
        real_shape_sets = set()

        for component in mix_design.components:
            material_id = component.get('material_id')

            # Skip VOID pseudo-material
            if material_id == MaterialSelector.VOID_MATERIAL_ID:
                continue

            material = self.material_service.get_by_id(material_id)
            if not material:
                continue

            # All materials use their own shape settings from the Material model
            shape_type = getattr(material, 'particle_shape_type', 0) or 0
            shape_set = getattr(material, 'particle_shape_set', None)

            if shape_type == self.REALSHAPE and shape_set:
                has_real_shapes = True
                real_shape_sets.add(shape_set)
            else:
                has_spheres = True

        # Determine overall shape mode
        if not has_real_shapes:
            # All materials use spheres
            logger.debug("Shape mode: SPHERES (all materials use spherical particles)")
            return self.SPHERES
        elif not has_spheres and len(real_shape_sets) == 1:
            # All materials use the same real-shape set
            logger.info(f"Shape mode: REALSHAPE (all materials use shape set: {real_shape_sets.pop()})")
            return self.REALSHAPE
        else:
            # Mixed: some spheres and some real shapes, or different shape sets
            logger.info(f"Shape mode: MIXEDSHAPE (spheres={has_spheres}, real_shape_sets={real_shape_sets})")
            return self.MIXEDSHAPE

    def _generate_input_sequence(
        self,
        mix_design: MixDesign,
        phase_mapping: PhaseIdMapping,
        volume_fractions: Dict[str, float],
        phase_data: List[Dict],
        shape_mode: int,
        microstructure_filename: str,
        particle_id_filename: str,
        add_aggregate_slab: bool,
        add_void_phase: bool,
        shape_database_path: Optional[Path],
        shape_set_name: Optional[str],
        output_dir: Path
    ) -> List[str]:
        """
        Generate the complete sequence of input lines for micgen.

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping
            volume_fractions: Calculated volume fractions
            phase_data: Phase-specific data
            shape_mode: Particle shape mode
            microstructure_filename: Output microstructure file name
            particle_id_filename: Output particle ID file name
            add_aggregate_slab: Whether to add aggregate slab
            add_void_phase: Whether to add void phase
            shape_database_path: Path to shape database directory (parent of shape sets)
            shape_set_name: Name of the shape set directory to use
            output_dir: Directory where output files are written (for correlation files)

        Returns:
            List of input lines
        """
        lines = []

        # 1. Random number seed (negative integer)
        lines.append(str(mix_design.random_seed))

        # 2. SPECSIZE (2)
        lines.append(str(self.SPECSIZE))

        # 3. System dimensions
        lines.append(str(mix_design.system_size_x))
        lines.append(str(mix_design.system_size_y))
        lines.append(str(mix_design.system_size_z))

        # 4. Image resolution (micrometers)
        lines.append(str(mix_design.resolution))

        # 5. [Optional] Add aggregate slab
        if add_aggregate_slab:
            lines.append(str(self.ADDAGG))

        # 6. ADDPART (4)
        lines.append(str(self.ADDPART))

        # 7. Particle shape mode
        lines.append(str(shape_mode))

        # 7a. If REALSHAPE mode (all particles use same shape set), add default path and set name
        # For MIXEDSHAPE mode, the default path/set is also read by micgen.c
        if shape_mode == self.REALSHAPE:
            # REALSHAPE: All particles use the same shape set - required
            if shape_database_path and shape_set_name:
                path_str = str(shape_database_path)
                if not path_str.endswith(os.sep):
                    path_str += os.sep
                lines.append(path_str)
                lines.append(shape_set_name)
                logger.info(f"Using real-shape particles from: {path_str}{shape_set_name}")
            else:
                raise MicgenInputGenerationError(
                    f"Real-shape mode selected but shape database path or set name is missing. "
                    f"path={shape_database_path}, set_name={shape_set_name}"
                )
        elif shape_mode == self.MIXEDSHAPE:
            # MIXEDSHAPE: micgen.c reads a default path/set, then each phase specifies its own
            # We need to provide a default path even if not all phases use real shapes
            if shape_database_path:
                path_str = str(shape_database_path)
                if not path_str.endswith(os.sep):
                    path_str += os.sep
                lines.append(path_str)
                # For default shape set, use the first real-shape phase's set or a placeholder
                default_set = shape_set_name or self._find_default_shape_set(phase_data)
                lines.append(default_set or "default")
                logger.info(f"Mixed shape mode with default path: {path_str}")
            else:
                raise MicgenInputGenerationError(
                    f"Mixed-shape mode selected but shape database path is missing"
                )

        # 8-9. Volume fractions and phase data
        lines.extend(self._generate_volume_fraction_lines(volume_fractions))
        lines.extend(self._generate_phase_input_lines(phase_data, shape_mode, shape_database_path))

        # 10. Dispersion factor
        lines.append(str(mix_design.dispersion_factor))

        # 11. [Optional] Flocculation
        if mix_design.flocculation_enabled:
            lines.append(str(self.FLOCC))
            lines.append(str(mix_design.flocculation_degree))

        # 12. [If clinker > 0] DISTRIB (6)
        if volume_fractions['clinker_vfrac'] > 0.0:
            lines.extend(self._generate_clinker_distribution_lines(mix_design, phase_mapping, output_dir))

        # 13. [Optional] ADDVOID (7)
        if add_void_phase:
            lines.append(str(self.ADDVOID))

        # 14. ONEVOX (9)
        lines.append(str(self.ONEVOX))

        # 15. OUTPUTMIC (10)
        lines.append(str(self.OUTPUTMIC))
        lines.append(microstructure_filename)
        lines.append(particle_id_filename)

        # 16. EXIT (1)
        lines.append(str(self.EXIT))

        return lines

    def _generate_volume_fraction_lines(self, volume_fractions: Dict[str, float]) -> List[str]:
        """
        Generate volume fraction input lines.

        Args:
            volume_fractions: Dictionary with clinker, other solids, electrolyte, void

        Returns:
            List of input lines
        """
        return [
            f"{volume_fractions['clinker_vfrac']:.6f}",
            f"{volume_fractions['other_solid_vfrac']:.6f}",
            f"{volume_fractions['electrolyte_vfrac']:.6f}",
            f"{volume_fractions['void_vfrac']:.6f}"
        ]

    def _generate_phase_input_lines(
        self,
        phase_data: List[Dict],
        shape_mode: int,
        shape_database_path: Optional[Path] = None
    ) -> List[str]:
        """
        Generate phase-by-phase input lines.

        For each phase:
        - Phase ID
        - Volume fraction on solids basis
        - Number of size classes
        - For each size class: diameter, volume fraction
        - [If MIXEDSHAPE] shape type for this phase (0=spheres, 1=real)
        - [If MIXEDSHAPE and real shape] shape path and set name

        Args:
            phase_data: List of phase data dictionaries
            shape_mode: Shape mode (SPHERES, REALSHAPE, MIXEDSHAPE)
            shape_database_path: Path to shape database directory (for MIXEDSHAPE mode)

        Returns:
            List of input lines
        """
        lines = []

        # First line: total number of solid phases to add
        num_phases = len(phase_data)
        lines.append(str(num_phases))

        # For each phase, generate its input lines
        for phase in phase_data:
            phase_id = phase['phase_id']
            vol_frac = phase['volume_fraction_solids_basis']
            size_classes = phase['size_classes']
            phase_shape_type = phase.get('shape_type', self.SPHERES)
            phase_shape_set = phase.get('shape_set', None)

            # 1. Phase ID
            lines.append(str(phase_id))

            # 2. Volume fraction (on solids basis)
            lines.append(f"{vol_frac:.6f}")

            # 3. Number of size classes
            num_size_classes = len(size_classes)
            lines.append(str(num_size_classes))

            # 4. For each size class: diameter and volume fraction
            for size_class in size_classes:
                diameter = size_class['diameter_voxels']
                class_vol_frac = size_class['volume_fraction']

                # Diameter in voxel units - micgen.c expects INTEGER diameters
                lines.append(str(int(round(diameter))))

                # Volume fraction in this size class
                lines.append(f"{class_vol_frac:.6f}")

            # 5. If MIXEDSHAPE mode, specify shape type for this phase
            if shape_mode == self.MIXEDSHAPE:
                lines.append(str(phase_shape_type))

                # 6. If this phase uses real shapes, add path and shape set name
                if phase_shape_type == self.REALSHAPE:
                    if shape_database_path and phase_shape_set:
                        # micgen.c expects path with trailing separator
                        path_str = str(shape_database_path)
                        if not path_str.endswith(os.sep):
                            path_str += os.sep
                        lines.append(path_str)
                        lines.append(phase_shape_set)
                        logger.debug(
                            f"Phase {phase_id} ({phase.get('gem_phase_name', 'unknown')}) "
                            f"uses real shapes: {path_str}{phase_shape_set}"
                        )
                    else:
                        raise MicgenInputGenerationError(
                            f"Phase {phase_id} ({phase.get('gem_phase_name', 'unknown')}) "
                            f"is set to use real shapes but shape database path or set name is missing. "
                            f"path={shape_database_path}, set_name={phase_shape_set}"
                        )

        logger.debug(f"Generated input lines for {num_phases} phases")
        return lines

    def _find_clinker_material(self, mix_design: MixDesign) -> Optional[Material]:
        """
        Find the clinker material in the mix design.

        Due to UI constraints, there can be at most one material with has_clinker=True.

        There are two cases:
        1. Materials created through "Add from Material" workflow have clinker_source_id
           pointing to a separate clinker material
        2. Migrated/self-contained cements have has_clinker=True but no clinker_source_id;
           in this case, the material itself contains the clinker phases

        Args:
            mix_design: The mix design

        Returns:
            The clinker material, or None if no clinker in mix
        """
        for component in mix_design.components:
            material = self.material_service.get_by_id(component['material_id'])
            logger.info(f"_find_clinker_material: checking material_id={component['material_id']}, "
                       f"name={material.name if material else 'NOT FOUND'}, "
                       f"is_clinker={material.is_clinker if material else 'N/A'}, "
                       f"has_clinker={material.has_clinker if material else 'N/A'}")
            if material and material.has_clinker:
                if material.clinker_source_id:
                    # Case 1: Material references a separate clinker source
                    clinker_material = self.material_service.get_by_id(material.clinker_source_id)
                    if clinker_material:
                        logger.debug(
                            f"Found clinker material '{clinker_material.name}' "
                            f"(source for '{material.name}')"
                        )
                        return clinker_material
                    else:
                        logger.warning(
                            f"Material '{material.name}' references clinker_source_id={material.clinker_source_id} "
                            f"but that material not found"
                        )
                else:
                    # Case 2: Self-contained cement (e.g., migrated VCCTL cement)
                    # The material itself contains the clinker phases
                    logger.debug(
                        f"Found self-contained clinker material '{material.name}' "
                        f"(has_clinker=True, no clinker_source_id)"
                    )
                    return material

        logger.debug("No clinker material found in mix")
        return None

    def _get_clinker_extension(self, clinker_material_id: int) -> ClinkerExtension:
        """
        Retrieve ClinkerExtension data for a clinker material.

        Args:
            clinker_material_id: ID of the clinker material

        Returns:
            ClinkerExtension object

        Raises:
            MicgenInputGenerationError: If clinker extension not found
        """
        clinker_ext = self.material_service.get_clinker_extension(clinker_material_id)
        if not clinker_ext:
            raise MicgenInputGenerationError(
                f"ClinkerExtension not found for material ID {clinker_material_id}"
            )
        return clinker_ext

    def _write_correlation_files(
        self,
        clinker_ext: ClinkerExtension,
        clinker_name: str,
        output_dir: Path
    ) -> str:
        """
        Write correlation function BLOBs to the output directory.

        Creates up to 7 files: {name}.sil, {name}.c3s, {name}.alu, {name}.c3a,
                              {name}.c4af, {name}.k2o, {name}.n2o

        Args:
            clinker_ext: ClinkerExtension object with correlation BLOBs
            clinker_name: Base name for correlation files
            output_dir: Directory where correlation files should be written

        Returns:
            Path/root string (directory + base name without extension)
            Example: "/path/to/operations/Test_Mix_01/cement116"
            (micgen will append .c3s, .c2s, etc.)

        Raises:
            MicgenInputGenerationError: If write fails
        """
        # Ensure output directory exists
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Writing correlation files to: {output_dir}")

        # Define correlation file extensions and their corresponding BLOB attributes
        correlation_files = {
            'sil': clinker_ext.correlation_sil,
            'c3s': clinker_ext.correlation_c3s,
            'alu': clinker_ext.correlation_alu,
            'c3a': clinker_ext.correlation_c3a,
            'c4af': clinker_ext.correlation_c4af,
            'k2o': clinker_ext.correlation_k2o,
            'n2o': clinker_ext.correlation_n2o
        }

        # Write each correlation BLOB to file
        # Note: Some cements may not have all correlation files - this is OK
        # micgen.c will use defaults or skip missing correlations
        files_written = 0
        for ext, blob in correlation_files.items():
            if blob is None or len(blob) == 0:
                logger.warning(
                    f"Correlation function '{ext}' is missing for clinker '{clinker_name}' - skipping"
                )
                continue

            filepath = output_dir / f"{clinker_name}.{ext}"
            try:
                with open(filepath, 'wb') as f:
                    f.write(blob)
                files_written += 1
                logger.debug(f"Wrote correlation file: {filepath}")
            except Exception as e:
                raise MicgenInputGenerationError(
                    f"Failed to write correlation file '{filepath}': {e}"
                ) from e

        # Return path/root (directory + base name, no extension)
        path_root = str(output_dir / clinker_name)
        logger.info(f"Wrote {files_written}/7 correlation files with path/root: {path_root}")
        return path_root

    def _get_clinker_phase_fractions(
        self,
        clinker_ext: ClinkerExtension
    ) -> Dict[str, Dict[str, float]]:
        """
        Extract volume and surface fractions for all 6 clinker phases.

        Args:
            clinker_ext: ClinkerExtension object

        Returns:
            Dictionary mapping phase name to volume/surface fractions:
            {
                'Alite': {'volume': 0.60, 'surface': 0.65},
                'Belite': {'volume': 0.20, 'surface': 0.15},
                ...
            }
        """
        # Map clinker phase names to their fraction attributes
        # Note: Volume fractions come from the material's phase composition
        # Surface fractions come from ClinkerExtension
        phase_fractions = {
            'Alite': {
                'volume': 0.0,  # Will be filled from material phases
                'surface': clinker_ext.c3s_surface_fraction or 0.0
            },
            'Belite': {
                'volume': 0.0,
                'surface': clinker_ext.c2s_surface_fraction or 0.0
            },
            'Aluminate': {
                'volume': 0.0,
                'surface': clinker_ext.c3a_surface_fraction or 0.0
            },
            'Ferrite': {
                'volume': 0.0,
                'surface': clinker_ext.c4af_surface_fraction or 0.0
            },
            'Arcanite': {
                'volume': 0.0,
                'surface': clinker_ext.k2so4_surface_fraction or 0.0
            },
            'Thenardite': {
                'volume': 0.0,
                'surface': clinker_ext.na2so4_surface_fraction or 0.0
            }
        }

        # Get volume fractions from the clinker material's phases
        clinker_material = self.material_service.get_by_id(clinker_ext.material_id)
        if clinker_material and clinker_material.phases:
            for phase in clinker_material.phases:
                phase_name = phase.gem_phase_name
                if phase_name in phase_fractions:
                    phase_fractions[phase_name]['volume'] = phase.mass_fraction

        logger.debug(f"Extracted fractions for {len(phase_fractions)} clinker phases")
        return phase_fractions

    def _generate_clinker_distribution_lines(
        self,
        mix_design: MixDesign,
        phase_mapping: PhaseIdMapping,
        output_dir: Path
    ) -> List[str]:
        """
        Generate DISTRIB (6) input lines for clinker correlation functions.

        Input format:
        - DISTRIB (6)
        - Path/root name of correlation function files
        - For each of 6 clinker phases (Alite, Belite, Aluminate, Ferrite, Arcanite, Thenardite):
          - Volume fraction
          - Surface fraction

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping
            output_dir: Directory where correlation files should be written

        Returns:
            List of input lines
        """
        logger.info("Generating clinker distribution input lines")

        lines = [str(self.DISTRIB)]

        # Step 1: Find the clinker material in the mix
        clinker_material = self._find_clinker_material(mix_design)
        if not clinker_material:
            raise MicgenInputGenerationError(
                "No clinker material found in mix, but clinker volume fraction > 0"
            )

        # Step 2: Get ClinkerExtension data
        clinker_ext = self._get_clinker_extension(clinker_material.id)

        # Step 3: Write correlation function BLOBs to the output directory
        path_root = self._write_correlation_files(clinker_ext, clinker_material.name, output_dir)
        lines.append(path_root)

        # Step 4: Get volume and surface fractions for all 6 clinker phases
        phase_fractions = self._get_clinker_phase_fractions(clinker_ext)

        # Step 5: Add volume and surface fractions in the correct order
        # Order must match: Alite, Belite, Aluminate, Ferrite, Arcanite, Thenardite
        clinker_phase_order = ['Alite', 'Belite', 'Aluminate', 'Ferrite', 'Arcanite', 'Thenardite']

        for phase_name in clinker_phase_order:
            fractions = phase_fractions.get(phase_name, {'volume': 0.0, 'surface': 0.0})

            # Volume fraction
            lines.append(f"{fractions['volume']:.6f}")

            # Surface fraction
            lines.append(f"{fractions['surface']:.6f}")

        logger.info(
            f"Generated clinker distribution lines for '{clinker_material.name}' "
            f"with {len(clinker_phase_order)} phases"
        )

        return lines

    def _write_input_file(self, output_path: Path, lines: List[str]) -> None:
        """
        Write input lines to file.

        Args:
            output_path: Path where file will be written
            lines: List of input lines
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            for line in lines:
                f.write(line + '\n')

        logger.info(f"Wrote {len(lines)} lines to {output_path}")

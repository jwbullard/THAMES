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
import tempfile
import json
import numpy as np
from scipy.stats import lognorm

from app.models.mix_design import MixDesign, MixDesignComponentData
from app.models.material import Material
from app.models.psd_data import PSDData
from app.models.clinker_extension import ClinkerExtension
from app.services.material_service import MaterialService
from app.services.phase_id_mapping_service import PhaseIdMappingService, PhaseIdMapping
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

            # Step 4: Determine shape mode
            shape_mode = self._determine_shape_mode(mix_design)

            # Step 5: Generate input lines
            input_lines = self._generate_input_sequence(
                mix_design=mix_design,
                phase_mapping=phase_mapping,
                volume_fractions=volume_fractions,
                phase_data=phase_data,
                shape_mode=shape_mode,
                microstructure_filename=microstructure_filename,
                particle_id_filename=particle_id_filename,
                add_aggregate_slab=add_aggregate_slab,
                add_void_phase=add_void_phase,
                shape_database_path=shape_database_path
            )

            # Step 6: Write to file
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
        # Collect all material phases from the mix design components
        material_phases = []

        for component in mix_design.components:
            material = self.material_service.get_by_id(component['material_id'])
            if not material:
                raise MicgenInputGenerationError(
                    f"Material ID {component['material_id']} not found"
                )

            for phase in material.phases:
                material_phases.append({
                    'gem_phase_name': phase.gem_phase_name,
                    'mass_fraction': phase.mass_fraction * component['mass_fraction']
                })

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

        Micgen requires:
        - PC clinker volume fraction (sum of all 6 clinker phases)
        - Other solids volume fraction (non-clinker solid phases)
        - Electrolyte volume fraction
        - Void volume fraction

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping

        Returns:
            Dictionary with keys: 'clinker_vfrac', 'other_solid_vfrac',
                                  'electrolyte_vfrac', 'void_vfrac'
        """
        clinker_vfrac = 0.0
        other_solid_vfrac = 0.0
        electrolyte_vfrac = mix_design.water_volume_fraction
        void_vfrac = mix_design.air_volume_fraction

        # Sum volume fractions by category
        for component in mix_design.components:
            material = self.material_service.get_by_id(component['material_id'])
            comp_vfrac = component['volume_fraction']

            # Check if material has clinker phases
            if material.has_clinker:
                # This material contributes to clinker volume
                clinker_vfrac += comp_vfrac
            else:
                # This material contributes to other solids
                other_solid_vfrac += comp_vfrac

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
        phase_aggregates = {}

        for component in mix_design.components:
            material = self.material_service.get_by_id(component['material_id'])
            if not material:
                raise MicgenInputGenerationError(
                    f"Material ID {component['material_id']} not found"
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

                # Record this contribution for PSD weighting later
                phase_aggregates[phase_name]['contributions'].append({
                    'material_id': material.id,
                    'material_name': material.name,
                    'mass_fraction': phase_mass_in_component,
                    'volume_fraction': phase_vol_in_component,
                    'specific_gravity': material.specific_gravity,
                    'psd_data_id': material.psd_data_id
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
        - Diameter in voxel units
        - Volume fraction for each size class

        Args:
            psd_dict: PSD data dictionary from _psd_to_dict with 'size_classes_um'
            resolution: Microstructure resolution in micrometers/voxel

        Returns:
            List of size class dictionaries:
            [
                {'diameter_voxels': 1.5, 'volume_fraction': 0.15},
                {'diameter_voxels': 5.0, 'volume_fraction': 0.35},
                ...
            ]
        """
        size_classes_um = psd_dict.get('size_classes_um', [])

        if not size_classes_um:
            # Fallback to single default size class
            logger.warning("No size classes in PSD, using default 10μm particle")
            return [{'diameter_voxels': 10.0 / resolution, 'volume_fraction': 1.0}]

        # Convert diameters from micrometers to voxels
        size_classes = []
        for diameter_um, vol_frac in size_classes_um:
            diameter_voxels = diameter_um / resolution

            # Skip very small particles (less than 0.5 voxels)
            if diameter_voxels < 0.5:
                continue

            size_classes.append({
                'diameter_voxels': diameter_voxels,
                'volume_fraction': vol_frac
            })

        # Renormalize after filtering
        total = sum(sc['volume_fraction'] for sc in size_classes)
        if total > 0:
            for sc in size_classes:
                sc['volume_fraction'] /= total

        # If all were filtered out, use minimum size
        if not size_classes:
            logger.warning("All particles too small for resolution, using 1 voxel minimum")
            return [{'diameter_voxels': 1.0, 'volume_fraction': 1.0}]

        logger.debug(f"Generated {len(size_classes)} size classes from PSD")
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

    def _collect_phase_data(
        self,
        mix_design: MixDesign,
        phase_mapping: PhaseIdMapping
    ) -> List[Dict]:
        """
        Collect data for each solid phase in the mix.

        For each phase, collect:
        - Phase ID from mapping
        - Volume fraction on total solids basis
        - PSD data (size classes, volume fractions per class)
        - Shape information

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping

        Returns:
            List of phase data dictionaries
        """
        logger.info("Collecting phase data for micgen input")

        # Step 1: Aggregate all phases by name
        phase_aggregates = self._aggregate_phases_by_name(mix_design)

        # Step 2: Calculate total solids volume fraction
        total_solids_vol = sum(
            agg['total_volume_fraction']
            for agg in phase_aggregates.values()
        )

        if total_solids_vol <= 0.0:
            raise MicgenInputGenerationError("No solid phases in mix design")

        # Step 3: Build phase data list
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

            # Build phase data entry
            phase_data.append({
                'phase_id': phase_id,
                'gem_phase_name': phase_name,
                'volume_fraction_solids_basis': vol_frac_solids,
                'size_classes': size_classes,
                'shape_type': self.SPHERES  # TODO: Determine from material settings
            })

        # Step 4: Order phases by ID
        phase_data = self._order_phases_for_micgen(phase_data, phase_mapping)

        logger.info(f"Collected data for {len(phase_data)} phases")
        return phase_data

    def _determine_shape_mode(self, mix_design: MixDesign) -> int:
        """
        Determine particle shape mode for micgen.

        Args:
            mix_design: The mix design

        Returns:
            Shape mode: 0=SPHERES, 1=REALSHAPE, 2=MIXEDSHAPE
        """
        # Check if any component uses real shapes
        # For now, default to spheres
        # TODO: Implement shape mode detection based on material settings
        return self.SPHERES

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
        shape_database_path: Optional[Path]
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
            shape_database_path: Path to shape database

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

        # 7a. If real shape or mixed, add shape database path and set name
        if shape_mode != self.SPHERES and shape_database_path:
            lines.append(str(shape_database_path))
            # TODO: Add specific shape set name

        # 8-9. Volume fractions and phase data
        lines.extend(self._generate_volume_fraction_lines(volume_fractions))
        lines.extend(self._generate_phase_input_lines(phase_data, shape_mode))

        # 10. Dispersion factor
        lines.append(str(mix_design.dispersion_factor))

        # 11. [Optional] Flocculation
        if mix_design.flocculation_enabled:
            lines.append(str(self.FLOCC))
            lines.append(str(mix_design.flocculation_degree))

        # 12. [If clinker > 0] DISTRIB (6)
        if volume_fractions['clinker_vfrac'] > 0.0:
            lines.extend(self._generate_clinker_distribution_lines(mix_design, phase_mapping))

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

    def _generate_phase_input_lines(self, phase_data: List[Dict], shape_mode: int) -> List[str]:
        """
        Generate phase-by-phase input lines.

        For each phase:
        - Phase ID
        - Volume fraction on solids basis
        - Number of size classes
        - For each size class: diameter, volume fraction
        - [If MIXEDSHAPE] shape type for this phase
        - [If real shape] shape path and set name

        Args:
            phase_data: List of phase data dictionaries
            shape_mode: Shape mode (SPHERES, REALSHAPE, MIXEDSHAPE)

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
            shape_type = phase['shape_type']

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

                # Diameter in voxel units
                lines.append(f"{diameter:.6f}")

                # Volume fraction in this size class
                lines.append(f"{class_vol_frac:.6f}")

            # 5. If MIXEDSHAPE mode, specify shape type for this phase
            if shape_mode == self.MIXEDSHAPE:
                lines.append(str(shape_type))

                # 6. If this phase is real shape, add path and shape set name
                if shape_type == self.REALSHAPE:
                    # TODO: Get actual shape path and set name from material/phase data
                    # For now, these are placeholders
                    logger.warning(
                        f"Phase {phase_id} ({phase.get('gem_phase_name', 'unknown')}) "
                        f"uses real shapes but shape path not yet implemented"
                    )
                    # Would add:
                    # lines.append(shape_path_with_separator)
                    # lines.append(shape_set_name)

        logger.debug(f"Generated input lines for {num_phases} phases")
        return lines

    def _find_clinker_material(self, mix_design: MixDesign) -> Optional[Material]:
        """
        Find the clinker material in the mix design.

        Due to UI constraints, there can be at most one material with has_clinker=True.

        Args:
            mix_design: The mix design

        Returns:
            The clinker material, or None if no clinker in mix
        """
        for component in mix_design.components:
            material = self.material_service.get_by_id(component['material_id'])
            if material and material.has_clinker and material.clinker_source_id:
                # Found material with clinker - get the actual clinker source
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
        temp_dir: Optional[Path] = None
    ) -> str:
        """
        Write correlation function BLOBs to temporary files.

        Creates 7 files: {name}.sil, {name}.c3s, {name}.alu, {name}.c3a,
                        {name}.c4af, {name}.k2o, {name}.n2o

        Args:
            clinker_ext: ClinkerExtension object with correlation BLOBs
            clinker_name: Base name for correlation files
            temp_dir: Optional temporary directory path (creates one if None)

        Returns:
            Path/root string (directory + base name without extension)
            Example: "/tmp/tmpxyz/cement116" (micgen will append .c3s, .c2s, etc.)

        Raises:
            MicgenInputGenerationError: If any correlation BLOB is missing or write fails
        """
        # Create temp directory if not provided
        if temp_dir is None:
            temp_dir = Path(tempfile.mkdtemp(prefix="thames_correlations_"))
            logger.debug(f"Created temporary directory: {temp_dir}")
        else:
            temp_dir = Path(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

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
        for ext, blob in correlation_files.items():
            if blob is None:
                raise MicgenInputGenerationError(
                    f"Correlation function '{ext}' is missing for clinker"
                )

            filepath = temp_dir / f"{clinker_name}.{ext}"
            try:
                with open(filepath, 'wb') as f:
                    f.write(blob)
                logger.debug(f"Wrote correlation file: {filepath}")
            except Exception as e:
                raise MicgenInputGenerationError(
                    f"Failed to write correlation file '{filepath}': {e}"
                ) from e

        # Return path/root (directory + base name, no extension)
        path_root = str(temp_dir / clinker_name)
        logger.info(f"Wrote 7 correlation files with path/root: {path_root}")
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
            'arcanite': {
                'volume': 0.0,
                'surface': clinker_ext.k2so4_surface_fraction or 0.0
            },
            'thenardite': {
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
        phase_mapping: PhaseIdMapping
    ) -> List[str]:
        """
        Generate DISTRIB (6) input lines for clinker correlation functions.

        Input format:
        - DISTRIB (6)
        - Path/root name of correlation function files
        - For each of 6 clinker phases (alite, belite, aluminate, ferrite, arcanite, thenardite):
          - Volume fraction
          - Surface fraction

        Args:
            mix_design: The mix design
            phase_mapping: Phase ID mapping

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

        # Step 3: Write correlation function BLOBs to temporary files
        path_root = self._write_correlation_files(clinker_ext, clinker_material.name)
        lines.append(path_root)

        # Step 4: Get volume and surface fractions for all 6 clinker phases
        phase_fractions = self._get_clinker_phase_fractions(clinker_ext)

        # Step 5: Add volume and surface fractions in the correct order
        # Order must match: Alite, Belite, Aluminate, Ferrite, arcanite, thenardite
        clinker_phase_order = ['Alite', 'Belite', 'Aluminate', 'Ferrite', 'arcanite', 'thenardite']

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

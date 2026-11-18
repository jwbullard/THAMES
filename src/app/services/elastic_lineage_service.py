#!/usr/bin/env python3
"""
Elastic Moduli Lineage Resolution Service

Handles complete lineage tracking for elastic moduli operations:
Elastic -> Hydration -> Microstructure -> Mix Design -> Aggregate Properties

Provides services for:
- Tracing operation lineage chains
- Extracting aggregate properties from database
- Resolving volume fractions from mix design components
- Finding hydrated microstructures with time steps
- Converting file paths to relative paths
"""

import logging
import os
import re
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.operation import Operation, OperationStatus, OperationType
from app.models.mix_design import MixDesign
from app.models.aggregate import Aggregate
from app.services.service_container import ServiceContainer


class HydratedMicrostructure:
    """Represents a hydrated microstructure file with time information."""
    
    def __init__(self, file_path: str, time_label: str, is_final: bool = False):
        self.file_path = file_path
        self.time_label = time_label
        self.is_final = is_final
        self.pimg_path = file_path.replace('.img', '.pimg')
    
    def __repr__(self):
        return f"<HydratedMicrostructure(time='{self.time_label}', final={self.is_final})>"


class AggregateProperties:
    """Represents aggregate mechanical and physical properties."""
    
    def __init__(self, name: str, bulk_modulus: float, shear_modulus: float, 
                 volume_fraction: float, grading_path: str = None, grading_template_name: str = None):
        self.name = name
        self.bulk_modulus = bulk_modulus
        self.shear_modulus = shear_modulus
        self.volume_fraction = volume_fraction
        self.grading_path = grading_path or ""
        self.grading_template_name = grading_template_name  # Store template name if available
    
    def __repr__(self):
        return f"<AggregateProperties(name='{self.name}', bulk={self.bulk_modulus}, shear={self.shear_modulus}, vf={self.volume_fraction})>"


class ElasticLineageService:
    """Service for resolving elastic moduli operation lineage and dependencies."""
    
    def __init__(self, service_container: ServiceContainer):
        self.service_container = service_container
        self.database_service = service_container.database_service
        self.logger = logging.getLogger(__name__)

        # Get operations directory from configuration
        self.operations_dir = service_container.directories_service.get_operations_path()
    
    def resolve_lineage_chain(self, hydration_operation_id: int, output_directory: str = None) -> Dict[str, Any]:
        """
        Resolve complete lineage chain from hydration operation.
        
        Returns dictionary with:
        - hydration_operation: Hydration Operation object
        - microstructure_operation: Parent Microstructure Operation object  
        - mix_design_data: Mix design parameters from stored UI parameters
        - aggregate_properties: Resolved fine/coarse aggregate properties
        - volume_fractions: Calculated volume fractions
        """
        with self.database_service.get_session() as session:
            # 1. Get hydration operation
            hydration_op = session.query(Operation).filter_by(id=hydration_operation_id).first()
            if not hydration_op:
                raise ValueError(f"Hydration operation {hydration_operation_id} not found")
            
            if hydration_op.operation_type != OperationType.HYDRATION.value:
                raise ValueError(f"Operation {hydration_operation_id} is not a hydration operation")
            
            # 2. Get source microstructure operation (with legacy support)
            microstructure_op = None
            microstructure_name = None
            
            # First try: Use parent_operation_id linkage (Phase 3+ operations)
            if hydration_op.parent_operation_id:
                microstructure_op = session.query(Operation).filter_by(
                    id=hydration_op.parent_operation_id
                ).first()
                
                # Check if parent is a microstructure operation (handle both canonical and legacy types)
                microstructure_types = [
                    OperationType.MICROSTRUCTURE.value,  # "MICROSTRUCTURE"
                    "microstructure_generation",         # Legacy type from operations panel
                    "MICROSTRUCTURE_GENERATION"          # Alternative format
                ]
                if microstructure_op and microstructure_op.operation_type not in microstructure_types:
                    raise ValueError(f"Parent operation is not a microstructure operation (type: {microstructure_op.operation_type})")
            
            # Second try: Use stored UI parameters for legacy operations
            if not microstructure_op and hydration_op.stored_ui_parameters:
                ui_params = hydration_op.stored_ui_parameters
                if 'source_microstructure' in ui_params:
                    source_info = ui_params['source_microstructure']
                    if isinstance(source_info, dict) and 'name' in source_info:
                        microstructure_name = source_info['name']
                        # Find microstructure operation by name (support both old and new operation types)
                        microstructure_op = session.query(Operation).filter(
                            Operation.name == microstructure_name,
                            Operation.operation_type.in_([OperationType.MICROSTRUCTURE.value, "microstructure_generation"])
                        ).first()
                        
                        self.logger.info(f"Found microstructure operation via UI parameters: {microstructure_name}")
            
            if not microstructure_op:
                error_msg = f"Parent microstructure operation not found for hydration {hydration_operation_id}"
                if microstructure_name:
                    error_msg += f" (looking for '{microstructure_name}')"
                raise ValueError(error_msg)
            
            # 3. Extract mix design data from linked SavedMixDesign record
            mix_design_data = self._get_mix_design_data_from_microstructure_operation(session, microstructure_op)
            
            # 4. Resolve aggregate properties from mix design
            aggregate_properties = self._resolve_aggregate_properties(session, mix_design_data, output_directory)
            
            # 5. Calculate volume fractions from mix design components
            volume_fractions = self._calculate_volume_fractions(mix_design_data)
            
            lineage = {
                'hydration_operation': hydration_op,
                'microstructure_operation': microstructure_op,
                'mix_design_data': mix_design_data,
                'aggregate_properties': aggregate_properties,
                'volume_fractions': volume_fractions
            }
            
            self.logger.info(f"Resolved lineage chain for hydration operation {hydration_operation_id}")
            return lineage
    
    def _resolve_aggregate_properties(self, session: Session, mix_design_data: Dict[str, Any], output_directory: str = None) -> Dict[str, Optional[AggregateProperties]]:
        """Resolve aggregate properties from mix design data and database."""
        properties = {
            'fine_aggregate': None,
            'coarse_aggregate': None
        }
        
        # Extract aggregate names from mix design
        fine_agg_name = mix_design_data.get('fine_aggregate_name')
        coarse_agg_name = mix_design_data.get('coarse_aggregate_name')
        
        # Extract volume fractions from components or direct fields
        volume_fractions = self._calculate_volume_fractions(mix_design_data)
        
        # Resolve fine aggregate
        fine_vf = volume_fractions.get('fine_aggregate_volume_fraction', 0.0)
        fine_mass = mix_design_data.get('fine_aggregate_mass', 0.0)

        # More robust detection: include if we have a name AND either mass OR volume fraction OR grading template
        fine_template_name = mix_design_data.get('fine_aggregate_grading_template')
        should_include_fine = (fine_agg_name and
                              (fine_vf > 0.0 or fine_mass > 0.0 or fine_template_name))

        self.logger.info(f"🔍 Fine aggregate detection: name='{fine_agg_name}', vf={fine_vf:.4f}, mass={fine_mass:.2f}, template='{fine_template_name}', include={should_include_fine}")

        if should_include_fine:
            fine_agg = session.query(Aggregate).filter(
                (Aggregate.display_name == fine_agg_name) | 
                (Aggregate.name == fine_agg_name)
            ).first()
            
            if fine_agg:
                self.logger.info(f"🔍 Fine template name from mix design: {fine_template_name}")
                properties['fine_aggregate'] = AggregateProperties(
                    name=fine_agg.display_name or fine_agg.name,
                    bulk_modulus=fine_agg.bulk_modulus or 30.0,  # Default GPa
                    shear_modulus=fine_agg.shear_modulus or 18.0,
                    volume_fraction=fine_vf,
                    grading_path=self._get_aggregate_grading_path(
                        fine_agg, output_directory, fine_template_name,
                        mix_design_data.get('fine_aggregate_grading_data')),
                    grading_template_name=fine_template_name
                )
                self.logger.info(f"Resolved fine aggregate: {fine_agg.display_name} (VF: {fine_vf:.3f}) with template: {fine_template_name}")
            else:
                self.logger.warning(f"Fine aggregate '{fine_agg_name}' not found in database")
        
        # Resolve coarse aggregate
        coarse_vf = volume_fractions.get('coarse_aggregate_volume_fraction', 0.0)
        coarse_mass = mix_design_data.get('coarse_aggregate_mass', 0.0)

        # More robust detection: include if we have a name AND either mass OR volume fraction OR grading template
        coarse_template_name = mix_design_data.get('coarse_aggregate_grading_template')
        should_include_coarse = (coarse_agg_name and
                                (coarse_vf > 0.0 or coarse_mass > 0.0 or coarse_template_name))

        self.logger.info(f"🔍 Coarse aggregate detection: name='{coarse_agg_name}', vf={coarse_vf:.4f}, mass={coarse_mass:.2f}, template='{coarse_template_name}', include={should_include_coarse}")

        if should_include_coarse:
            coarse_agg = session.query(Aggregate).filter(
                (Aggregate.display_name == coarse_agg_name) | 
                (Aggregate.name == coarse_agg_name)
            ).first()
            
            if coarse_agg:
                self.logger.info(f"🔍 Coarse template name from mix design: {coarse_template_name}")
                properties['coarse_aggregate'] = AggregateProperties(
                    name=coarse_agg.display_name or coarse_agg.name,
                    bulk_modulus=coarse_agg.bulk_modulus or 36.7,  # Default GPa
                    shear_modulus=coarse_agg.shear_modulus or 22.0,
                    volume_fraction=coarse_vf,
                    grading_path=self._get_aggregate_grading_path(
                        coarse_agg, output_directory, coarse_template_name,
                        mix_design_data.get('coarse_aggregate_grading_data')),
                    grading_template_name=coarse_template_name
                )
                self.logger.info(f"Resolved coarse aggregate: {coarse_agg.display_name} (VF: {coarse_vf:.3f}) with template: {coarse_template_name}")
            else:
                self.logger.warning(f"Coarse aggregate '{coarse_agg_name}' not found in database")
        
        return properties
    
    def _get_aggregate_grading_path(self, aggregate: Aggregate, output_directory: str = None,
                                    template_name: str = None, grading_points=None) -> str:
        """Write the aggregate's grading to a .gdg file and return its path ("" on failure).

        Uses the grading points stored with the mix when present (mixes saved
        from alpha-4.3 on). Older mixes fall back to a template: by name, then
        one tied to the aggregate, then a standard or any template of the type.
        """
        from app.models.grading import GradingType

        agg_type_str = "fine" if aggregate.is_fine_aggregate else "coarse"
        grading_type = GradingType.FINE if aggregate.is_fine_aggregate else GradingType.COARSE
        try:
            if grading_points:
                grading_name = template_name or "grading applied in Mix Design"
                grading_sieve_data = [[float(size), float(value)] for size, value in grading_points]
                self.logger.info(f"Using the mix's stored {agg_type_str} grading for "
                                 f"{aggregate.display_name} ({len(grading_sieve_data)} points)")
            else:
                grading_name, grading_sieve_data = self._find_grading_template(
                    aggregate, grading_type, agg_type_str, template_name)
            if not grading_sieve_data:
                self.logger.warning(f"No grading found for {agg_type_str} aggregate: {aggregate.display_name}")
                return ""
            return self._write_grading_file(aggregate, agg_type_str, output_directory,
                                            grading_name, grading_sieve_data)
        except Exception as e:
            self.logger.error(f"Failed to create grading file for aggregate {aggregate.display_name}: {e}")
            return ""

    def _find_grading_template(self, aggregate: Aggregate, grading_type, agg_type_str: str,
                               template_name: Optional[str]):
        """Find a template for a mix with no stored grading points; returns (name, sieve_data)."""
        from app.models.grading import Grading

        with self.database_service.get_session() as session:
            grading = None
            if template_name:
                grading = session.query(Grading).filter(
                    Grading.name == template_name, Grading.type == grading_type).first()
            if not grading:
                grading = session.query(Grading).filter(
                    Grading.aggregate_id == aggregate.id).first()
            fallback = None
            if not grading:
                grading = session.query(Grading).filter(
                    Grading.type == grading_type, Grading.is_standard == 1).first()
                fallback = "standard"
            if not grading:
                grading = session.query(Grading).filter(Grading.type == grading_type).first()
                fallback = "first available"
            if not grading or not grading.sieve_data:
                return None, None
            if fallback:
                # Older mix with no stored grading and no usable template name
                self.logger.warning(
                    f"No grading stored for {agg_type_str} aggregate {aggregate.display_name}; "
                    f"using the {fallback} {agg_type_str} template '{grading.name}'")
            return grading.name, list(grading.sieve_data)  # copy before the session closes

    def _write_grading_file(self, aggregate: Aggregate, agg_type_str: str,
                            output_directory: Optional[str], grading_name: str,
                            grading_sieve_data) -> str:
        """Write [[sieve_mm, % retained], ...] as the CSV .gdg file elastic.c reads."""
        from pathlib import Path

        grading_filename = f"{aggregate.display_name}_{agg_type_str}_grading.gdg"
        # Path relative to the operation's working directory
        temp_grading_path = f"./{grading_filename}"
        if not output_directory:
            # Lineage resolved for display only (no run folder yet): name the
            # file but do not write it. Writing it into the Operations root
            # left stray .gdg files there before alpha-4.3.
            return temp_grading_path
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        actual_file_path = output_path / grading_filename

        # Header line required by elastic.c; one line per sieve, largest first,
        # with individual fraction retained (no pan entry)
        lines = ["Opening_diameter_mm,Fraction_retained"]
        for size_mm, percent_retained in sorted(grading_sieve_data, key=lambda x: x[0], reverse=True):
            lines.append(f"{size_mm:.3f},{max(0.0, percent_retained / 100.0):.6f}")
        with open(actual_file_path, 'w') as f:
            f.write('\n'.join(lines))

        total_fraction = sum(max(0.0, value) for _, value in grading_sieve_data) / 100.0
        self.logger.info(f"Created grading file for {aggregate.display_name}: {actual_file_path} "
                         f"({grading_name}, {len(grading_sieve_data)} sieves, "
                         f"total fraction retained {total_fraction:.6f})")
        return temp_grading_path

    def _calculate_volume_fractions(self, mix_design_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate volume fractions from mix design components."""
        volume_fractions = {
            'fine_aggregate_volume_fraction': 0.0,
            'coarse_aggregate_volume_fraction': 0.0,
            'air_volume_fraction': 0.0
        }
        
        # Try to get from direct fields first
        volume_fractions['air_volume_fraction'] = mix_design_data.get('air_volume_fraction', 0.0)
        
        # Don't use component volume fractions as they might be incorrect
        # We'll calculate them correctly below using masses and densities
        components = mix_design_data.get('components', [])
        if isinstance(components, list):
            self.logger.info(f"🔍 Found {len(components)} components in mix design data")
            for component in components:
                if not isinstance(component, dict):
                    continue

                material_type = component.get('material_type', '').lower()
                material_name = component.get('material_name', '').lower()
                volume_fraction = component.get('volume_fraction', 0.0)

                self.logger.info(f"  Component: {material_name}, type={material_type}, vf={volume_fraction:.4f} (will recalculate)")

                # Only extract air content from components
                if 'air' in material_type:
                    volume_fractions['air_volume_fraction'] += volume_fraction
        
        # Also try calculated properties
        calculated_props = mix_design_data.get('calculated_properties', {})
        if isinstance(calculated_props, dict):
            for key, value in calculated_props.items():
                if key in volume_fractions and isinstance(value, (int, float)):
                    volume_fractions[key] = max(volume_fractions[key], value)
        
        # Try direct aggregate mass fields (convert to approximate volume fractions)
        fine_mass = mix_design_data.get('fine_aggregate_mass', 0.0)
        coarse_mass = mix_design_data.get('coarse_aggregate_mass', 0.0)
        
        # Log current state before correction
        self.logger.info(f"🔍 Before correction: fine_vf={volume_fractions['fine_aggregate_volume_fraction']:.4f}, "
                        f"coarse_vf={volume_fractions['coarse_aggregate_volume_fraction']:.4f}, "
                        f"fine_mass={fine_mass:.2f}, coarse_mass={coarse_mass:.2f}")

        # ALWAYS recalculate volume fractions when we have mass data
        # The components might have incorrect volume fractions from the UI
        if (fine_mass > 0 or coarse_mass > 0):
            # Get air content (default to 0.02 if not specified)
            air_content = volume_fractions.get('air_volume_fraction', 0.02)

            # We need to properly calculate volume fractions accounting for all solids
            # Don't trust the volume fractions from components as they might be wrong

            # Use typical densities
            fine_density = 2650.0  # kg/m³ (typical for sand)
            coarse_density = 2650.0  # kg/m³ (typical for gravel)
            cement_density = 3150.0  # kg/m³ (typical for cement)
            water_density = 1000.0  # kg/m³

            # Try to estimate total solid volume from known data
            # If we have total_water_content and water_binder_ratio, we can estimate cement mass
            total_water = mix_design_data.get('total_water_content', 0.0)
            w_b_ratio = mix_design_data.get('water_binder_ratio', 0.0)

            if total_water > 0 and w_b_ratio > 0:
                # Estimate cement mass from water content and w/b ratio
                cement_mass = total_water / w_b_ratio
            else:
                # Use a typical cement mass if we can't calculate it
                # Assume cement is roughly equal to fine aggregate for a typical mix
                cement_mass = fine_mass if fine_mass > 0 else 300.0  # kg/m³

            # Calculate sum of (mass/density) for ALL components
            sum_mass_over_density = 0.0

            # Add cement
            if cement_mass > 0:
                sum_mass_over_density += cement_mass / cement_density

            # Add water
            if total_water > 0:
                sum_mass_over_density += total_water / water_density

            # Add aggregates
            if fine_mass > 0:
                sum_mass_over_density += fine_mass / fine_density
            if coarse_mass > 0:
                sum_mass_over_density += coarse_mass / coarse_density

            # Apply corrected equation if we have valid data
            if sum_mass_over_density > 0:
                correction_factor = (1 - air_content) / sum_mass_over_density

                # Validate correction factor
                import math
                if math.isnan(correction_factor) or math.isinf(correction_factor):
                    self.logger.error(f"Invalid correction factor: {correction_factor}")
                    correction_factor = 1.0  # Use safe default

                self.logger.info(f"🔍 Calculation details:")
                self.logger.info(f"  - Air content: {air_content:.4f}")
                self.logger.info(f"  - Cement mass: {cement_mass:.2f} kg/m³")
                self.logger.info(f"  - Water mass: {total_water:.2f} kg/m³")
                self.logger.info(f"  - Fine aggregate mass: {fine_mass:.2f} kg/m³")
                self.logger.info(f"  - Coarse aggregate mass: {coarse_mass:.2f} kg/m³")
                self.logger.info(f"  - Sum(mass/density): {sum_mass_over_density:.6f}")
                self.logger.info(f"  - Correction factor: {correction_factor:.6f}")

                if fine_mass > 0:
                    fine_vf = (fine_mass / fine_density) * correction_factor
                    # Ensure volume fraction is within valid range [0, 1]
                    fine_vf = max(0.0, min(1.0, fine_vf))
                    volume_fractions['fine_aggregate_volume_fraction'] = fine_vf
                    self.logger.info(f"  -> Fine VF = ({fine_mass}/{fine_density}) * {correction_factor:.6f} = {fine_vf:.4f}")

                if coarse_mass > 0:
                    coarse_vf = (coarse_mass / coarse_density) * correction_factor
                    # Ensure volume fraction is within valid range [0, 1]
                    coarse_vf = max(0.0, min(1.0, coarse_vf))
                    volume_fractions['coarse_aggregate_volume_fraction'] = coarse_vf
                    self.logger.info(f"  -> Coarse VF = ({coarse_mass}/{coarse_density}) * {correction_factor:.6f} = {coarse_vf:.4f}")
        
        return volume_fractions
    
    def discover_hydrated_microstructures(self, hydration_operation: Operation) -> List[HydratedMicrostructure]:
        """
        Discover all available hydrated microstructures from hydration operation directory.

        Supports both VCCTL and THAMES output patterns:
        - VCCTL: HydrationOf_[NAME].img.25.100, [NAME].img.332.05h.25.100
        - THAMES: [NAME].<YYYyDDDdHHhMMm>.<TTTK>.img in Result/ subdirectory

        Returns list sorted with final microstructure first.
        """
        hydration_dir = self.operations_dir / hydration_operation.name

        if not hydration_dir.exists():
            self.logger.warning(f"Hydration directory not found: {hydration_dir}")
            return []

        # Resolve lineage to find the original microstructure operation
        original_pimg_path = None
        try:
            lineage = self.resolve_lineage_chain(hydration_operation.id)
            microstructure_operation = lineage.get('microstructure_operation')
            if microstructure_operation:
                # Find the original .pimg file in the microstructure operation's directory
                original_microstructure_dir = self.operations_dir / microstructure_operation.name
                original_pimg_path = original_microstructure_dir / f"{microstructure_operation.name}.pimg"

                if not original_pimg_path.exists():
                    self.logger.warning(f"Original .pimg file not found: {original_pimg_path}")
                    original_pimg_path = None
                else:
                    self.logger.info(f"Using original .pimg file: {original_pimg_path}")
            else:
                self.logger.warning(f"No microstructure operation found in lineage for {hydration_operation.name}")

        except Exception as e:
            self.logger.warning(f"Error resolving lineage for {hydration_operation.name}: {e}")

        # Fallback: Look for pimg file directly in hydration directory
        # (pimg is copied from microstructure operation to hydration directory during setup)
        if original_pimg_path is None:
            pimg_files = list(hydration_dir.glob("*.pimg"))
            if pimg_files:
                original_pimg_path = pimg_files[0]  # Use first one found
                self.logger.info(f"Found .pimg file in hydration directory (fallback): {original_pimg_path}")
            else:
                self.logger.warning(f"No .pimg file found in hydration directory: {hydration_dir}")

        img_files = []

        # =====================================================================
        # Check for THAMES output files in Result/ subdirectory
        # Pattern: <name>.<YYYyDDDdHHhMMm>.<TTTK>.img
        # Example: HydOf-Cem152-Neat.000y003d00h00m.298K.img
        # =====================================================================
        result_dir = hydration_dir / "Result"
        if result_dir.exists():
            # THAMES pattern: ends with .<digits>K.img (temperature in Kelvin)
            thames_pattern = re.compile(r'^.+\.\d{3}y\d{3}d\d{2}h\d{2}m\.\d+K\.img$')

            for file_path in result_dir.iterdir():
                if file_path.is_file() and thames_pattern.match(file_path.name):
                    img_files.append(file_path)
                    self.logger.debug(f"Found THAMES microstructure: {file_path.name}")

        # =====================================================================
        # Check for VCCTL output files in main directory
        # Pattern 1: HydrationOf_[NAME].img.25.100
        # Pattern 2: [NAME].img.332.05h.25.100
        # =====================================================================
        all_files = list(hydration_dir.glob("*"))

        # Valid combinations of Csh2flag (0-1), Adiaflag (0,1,2), Sealed (0-1)
        valid_suffixes = [
            '000', '001', '010', '011', '020', '021',
            '100', '101', '110', '111', '120', '121'
        ]

        for file_path in all_files:
            filename = file_path.name
            # Include hydrated microstructures but exclude original microstructure
            # Pattern: filename.img.{time}h.{temp}.{Csh2flag}{Adiaflag}{Sealed}
            # Examples:
            #   Isothermal (Adiaflag=0, Sealed=0): PLC-C109.img.24.00h.23.100
            #   Temperature profile (Adiaflag=2, Sealed=1): PLC-C109.img.24.00h.15.121
            #   Adiabatic (Adiaflag=1, Sealed=0): PLC-C109.img.24.00h.25.110
            if (filename.count('.') >= 3 and
                'h.' in filename and
                '.img.' in filename and
                any(filename.endswith('.' + suffix) for suffix in valid_suffixes)):
                img_files.append(file_path)
            # Also include HydrationOf_* files
            elif filename.startswith('HydrationOf_') and '.img.' in filename:
                img_files.append(file_path)

        self.logger.info(f"Found {len(img_files)} microstructure files for {hydration_operation.name}")

        microstructures = []

        # Process each file and extract time information
        for img_file in img_files:
            filename = img_file.name

            # Extract time label from filename
            time_label, time_minutes = self._extract_time_label_thames(filename, hydration_operation.name)

            microstructure = HydratedMicrostructure(
                file_path=str(img_file),
                time_label=time_label,
                is_final=False  # Will determine final below
            )
            # Store time in minutes for sorting
            microstructure._time_minutes = time_minutes
            # Use the original .pimg file for all hydrated microstructures
            microstructure.pimg_path = str(original_pimg_path) if original_pimg_path else None
            microstructures.append(microstructure)

        # Determine final microstructure (highest time value)
        if microstructures:
            # Sort by time in minutes to find the latest
            microstructures.sort(key=lambda x: x._time_minutes, reverse=True)
            microstructures[0].is_final = True
            microstructures[0].time_label = f"Final ({microstructures[0].time_label})"

        # Sort with final first, then by time (descending so most recent is at top)
        microstructures.sort(key=lambda x: (not x.is_final, -x._time_minutes))

        self.logger.info(f"Found {len(microstructures)} hydrated microstructures for {hydration_operation.name}")
        return microstructures

    def _extract_time_label_thames(self, filename: str, operation_name: str) -> tuple:
        """
        Extract time label from microstructure filename.

        Supports both VCCTL and THAMES patterns:
        - THAMES: <name>.<YYYyDDDdHHhMMm>.<TTTK>.img -> "X days Y hours"
        - VCCTL: Various patterns

        Returns:
            Tuple of (time_label: str, time_in_minutes: int)
        """
        # =====================================================================
        # THAMES pattern: <name>.<YYYyDDDdHHhMMm[SSs]>.<TTTK>.img
        # Examples: HydOf-Cem152-Neat.000y003d00h00m.298K.img
        #           HydOf-Cem152-Neat.000y000d00h00m18s.298K.img (with seconds)
        # =====================================================================
        thames_match = re.search(r'\.(\d{3})y(\d{3})d(\d{2})h(\d{2})m(?:(\d{2})s)?\.\d+K\.img$', filename)
        if thames_match:
            years = int(thames_match.group(1))
            days = int(thames_match.group(2))
            hours = int(thames_match.group(3))
            minutes = int(thames_match.group(4))
            seconds = int(thames_match.group(5)) if thames_match.group(5) else 0

            # Calculate total seconds for sorting (more precise than minutes)
            total_seconds = years * 365 * 24 * 60 * 60 + days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60 + seconds

            # Build human-readable label
            parts = []
            if years > 0:
                parts.append(f"{years}y")
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0 or (years == 0 and days == 0 and minutes == 0 and seconds == 0):
                parts.append(f"{hours}h")
            if minutes > 0 and days == 0:
                parts.append(f"{minutes}m")
            if seconds > 0 and days == 0 and hours == 0:
                parts.append(f"{seconds}s")

            time_label = " ".join(parts) if parts else "0h"
            return (time_label, total_seconds)

        # =====================================================================
        # VCCTL patterns
        # =====================================================================
        # Remove operation name prefix to get time suffix
        if filename.startswith(operation_name):
            suffix = filename[len(operation_name):]
            # Remove .img extension
            suffix = suffix.replace('.img', '')

            # Parse common patterns
            if suffix.startswith('_'):
                suffix = suffix[1:]  # Remove leading underscore

                # Pattern: "028days" -> "28 days"
                days_match = re.match(r'(\d+)days?', suffix)
                if days_match:
                    days = int(days_match.group(1))
                    return (f"{days} days", days * 24 * 60)

                # Pattern: "001hours" -> "1 hours"
                hours_match = re.match(r'(\d+)hours?', suffix)
                if hours_match:
                    hours = int(hours_match.group(1))
                    return (f"{hours} hours", hours * 60)

                # Pattern: "1year" -> "1 year"
                year_match = re.match(r'(\d+)years?', suffix)
                if year_match:
                    years = int(year_match.group(1))
                    return (f"{years} year{'s' if years != 1 else ''}", years * 365 * 24 * 60)

                # Return cleaned suffix if no pattern matches
                return (suffix.replace('_', ' ').title(), 0)

        # Fallback to filename without extension
        return (filename.replace('.img', ''), 0)
    
    def convert_to_relative_path(self, absolute_path: str, elastic_operation_dir: str) -> str:
        """
        Convert absolute file path to relative path from elastic operation directory.
        
        Args:
            absolute_path: Absolute path to file
            elastic_operation_dir: Absolute path to elastic operation directory
            
        Returns:
            Relative path from elastic operation directory
        """
        try:
            abs_path = Path(absolute_path).resolve()
            op_dir = Path(elastic_operation_dir).resolve()
            
            relative_path = os.path.relpath(abs_path, op_dir)
            
            self.logger.debug(f"Converted path: {absolute_path} -> {relative_path}")
            return relative_path
            
        except Exception as e:
            self.logger.error(f"Error converting path to relative: {e}")
            return absolute_path
    
    def get_itz_detection(self, aggregate_properties: Dict[str, Optional[AggregateProperties]]) -> bool:
        """
        Determine if ITZ calculations should be performed based on aggregate presence.
        
        Args:
            aggregate_properties: Dictionary with fine_aggregate and coarse_aggregate
            
        Returns:
            True if ITZ calculations should be performed
        """
        has_aggregates = (
            aggregate_properties.get('fine_aggregate') is not None or 
            aggregate_properties.get('coarse_aggregate') is not None
        )
        
        self.logger.info(f"ITZ detection: {has_aggregates}")
        return has_aggregates
    
    def validate_lineage_completeness(self, lineage: Dict[str, Any]) -> List[str]:
        """
        Validate that lineage contains all necessary data for elastic calculation.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not lineage.get('hydration_operation'):
            errors.append("Hydration operation not found")
        
        if not lineage.get('microstructure_operation'):
            errors.append("Parent microstructure operation not found")
        
        mix_design_data = lineage.get('mix_design_data', {})
        if not mix_design_data:
            errors.append("Mix design data not found in microstructure operation")
        
        aggregate_props = lineage.get('aggregate_properties', {})
        volume_fractions = lineage.get('volume_fractions', {})
        
        # Check if we have meaningful volume fractions
        total_volume = (
            volume_fractions.get('fine_aggregate_volume_fraction', 0.0) +
            volume_fractions.get('coarse_aggregate_volume_fraction', 0.0) +
            volume_fractions.get('air_volume_fraction', 0.0)
        )
        
        if total_volume > 1.0:
            errors.append(f"Total volume fractions exceed 1.0: {total_volume:.3f}")
        
        return errors
    
    def _get_mix_design_data_from_microstructure_operation(self, session, microstructure_op) -> Dict[str, Any]:
        """
        Get mix design data from linked SavedMixDesign record.
        
        Args:
            session: Database session
            microstructure_op: Microstructure Operation object
            
        Returns:
            Dictionary with mix design data in expected format
        """
        try:
            # Import required models
            from app.models.microstructure_operation import MicrostructureOperation
            from app.services.mix_design_service import MixDesignService
            
            # Find MicrostructureOperation record
            micro_op = session.query(MicrostructureOperation).filter_by(operation_id=microstructure_op.id).first()
            
            if not micro_op or not micro_op.mix_design_id:
                self.logger.warning(f"No MicrostructureOperation or mix_design_id for operation {microstructure_op.name}")
                return {}
            
            # Get SavedMixDesign via MixDesignService
            mix_design_service = MixDesignService(self.database_service)
            mix_design = mix_design_service.get_by_id(micro_op.mix_design_id)
            
            if not mix_design:
                self.logger.warning(f"SavedMixDesign not found for ID {micro_op.mix_design_id}")
                return {}
            
            # Convert SavedMixDesign to expected format
            mix_design_data = {
                'name': mix_design.name,
                'water_binder_ratio': mix_design.water_binder_ratio,
                'total_water_content': mix_design.total_water_content,
                'air_content': mix_design.air_content,
                'air_volume_fraction': mix_design.air_volume_fraction,
                'water_volume_fraction': mix_design.water_volume_fraction,
                'system_size_x': mix_design.system_size_x,
                'system_size_y': mix_design.system_size_y,
                'system_size_z': mix_design.system_size_z,
                
                # Convert components to expected format (list for volume fraction calculation)
                'components': [],
                
                # Aggregate data
                'fine_aggregate_name': mix_design.fine_aggregate_name,
                'fine_aggregate_mass': mix_design.fine_aggregate_mass,
                'coarse_aggregate_name': mix_design.coarse_aggregate_name,
                'coarse_aggregate_mass': mix_design.coarse_aggregate_mass,
                
                # Grading template associations
                'fine_aggregate_grading_template': mix_design.fine_aggregate_grading_template,
                'coarse_aggregate_grading_template': mix_design.coarse_aggregate_grading_template,
                'fine_aggregate_grading_data': getattr(mix_design, 'fine_aggregate_grading_data', None),
                'coarse_aggregate_grading_data': getattr(mix_design, 'coarse_aggregate_grading_data', None),
            }
            
            # Convert components to list format for volume fraction calculation
            if hasattr(mix_design, 'components') and mix_design.components:
                for component in mix_design.components:
                    if isinstance(component, dict):
                        # Component is already a dict
                        mix_design_data['components'].append(component)
                    else:
                        # Component is a Pydantic model object
                        mix_design_data['components'].append({
                            'material_name': getattr(component, 'material_name', ''),
                            'material_type': getattr(component, 'material_type', ''),
                            'mass_fraction': getattr(component, 'mass_fraction', 0.0),
                            'volume_fraction': getattr(component, 'volume_fraction', 0.0),
                            'specific_gravity': getattr(component, 'specific_gravity', 1.0),
                        })
            
            self.logger.info(f"Successfully loaded mix design data for {mix_design.name}: {len(mix_design_data['components'])} components")
            return mix_design_data
            
        except Exception as e:
            self.logger.error(f"Error loading mix design data from microstructure operation: {e}")
            return {}
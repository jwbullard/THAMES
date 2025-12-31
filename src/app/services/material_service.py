#!/usr/bin/env python3
"""
Material Service for THAMES

Provides business logic for tag-based material management with phase composition.
Handles CRUD operations, tag management, phase validation, and GEMS integration.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple, Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.database.service import DatabaseService
from app.models import (
    Material,
    MaterialCreate,
    MaterialUpdate,
    MaterialResponse,
    Tag,
    MaterialPhase,
    MaterialPhaseCreate,
    PSDData,
    ClinkerExtension,
    MaterialComponent
)
from app.services.base_service import BaseService, ServiceError, NotFoundError, AlreadyExistsError
from app.services.gems_parser_service import GEMSParserService


class MaterialService(BaseService[Material, MaterialCreate, MaterialUpdate]):
    """
    Service for managing materials in THAMES.

    Provides CRUD operations, tag management, phase composition validation,
    and integration with GEMS database for density calculations and phase validation.
    """

    def __init__(self, db_service: DatabaseService, gems_data_dir: Optional[Path] = None):
        """
        Initialize the material service.

        Args:
            db_service: Database service instance
            gems_data_dir: Path to GEMS data directory (optional, for validation and density calculations)
        """
        super().__init__(Material, db_service)
        self.logger = logging.getLogger('THAMES.MaterialService')

        # Initialize GEMS parser if data directory provided
        self.gems_parser = None
        if gems_data_dir and gems_data_dir.exists():
            try:
                self.gems_parser = GEMSParserService(gems_data_dir)
                self.logger.info(f"GEMS parser initialized with {self.gems_parser.num_phases} phases")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GEMS parser: {e}")

    # ========== CRUD Operations ==========

    def get_all(self, include_immutable: bool = True) -> List[Material]:
        """
        Get all materials with eagerly loaded relationships.

        Args:
            include_immutable: If False, exclude migrated VCCTL materials

        Returns:
            List of Material instances
        """
        try:
            with self.db_service.get_read_only_session() as session:
                query = session.query(Material).options(
                    joinedload(Material.psd_data),
                    joinedload(Material.phases),
                    joinedload(Material.tags)
                )

                if not include_immutable:
                    query = query.filter(Material.immutable == False)

                return query.order_by(Material.name).all()

        except Exception as e:
            self.logger.error(f"Failed to get all materials: {e}")
            raise ServiceError(f"Failed to retrieve materials: {e}")

    def get_by_name(self, name: str) -> Optional[Material]:
        """
        Get material by name with eagerly loaded relationships.

        Args:
            name: Material name

        Returns:
            Material instance or None if not found
        """
        try:
            with self.db_service.get_read_only_session() as session:
                return session.query(Material).options(
                    joinedload(Material.psd_data),
                    joinedload(Material.phases),
                    joinedload(Material.tags)
                ).filter_by(name=name).first()

        except Exception as e:
            self.logger.error(f"Failed to get material {name}: {e}")
            raise ServiceError(f"Failed to retrieve material: {e}")

    def get_by_id(self, material_id: int) -> Optional[Material]:
        """
        Get material by ID with eagerly loaded relationships.

        Args:
            material_id: Material ID

        Returns:
            Material instance or None if not found
        """
        try:
            with self.db_service.get_read_only_session() as session:
                return session.query(Material).options(
                    joinedload(Material.psd_data),
                    joinedload(Material.phases),
                    joinedload(Material.tags)
                ).filter_by(id=material_id).first()

        except Exception as e:
            self.logger.error(f"Failed to get material ID {material_id}: {e}")
            raise ServiceError(f"Failed to retrieve material: {e}")

    def get_phases_as_dicts(self, material_id: int) -> List[Dict[str, Any]]:
        """
        Get phases for a material as plain dictionaries.

        This avoids lazy-loading issues by converting to dicts within the session.

        Args:
            material_id: Material ID

        Returns:
            List of phase dictionaries with gem_phase_name and mass_fraction
        """
        try:
            with self.db_service.get_read_only_session() as session:
                from app.models.material_phase import MaterialPhase
                phases = session.query(MaterialPhase).filter_by(material_id=material_id).all()
                return [
                    {
                        'gem_phase_name': p.gem_phase_name,
                        'mass_fraction': p.mass_fraction
                    }
                    for p in phases
                ]
        except Exception as e:
            self.logger.error(f"Failed to get phases for material {material_id}: {e}")
            return []

    def create(
        self,
        material_data: MaterialCreate,
        phase_compositions: Optional[List[Dict[str, float]]] = None,
        auto_calculate_sg: bool = False
    ) -> Material:
        """
        Create a new material with tags and phase composition.

        Args:
            material_data: Material creation data
            phase_compositions: List of dicts with 'gem_phase_name' and 'mass_fraction'
                               Example: [{"gem_phase_name": "Alite", "mass_fraction": 0.60}, ...]
            auto_calculate_sg: If True, calculate specific gravity from phase composition using GEMS

        Returns:
            Created Material instance

        Raises:
            AlreadyExistsError: If material name already exists
            ServiceError: If creation fails
        """
        try:
            with self.db_service.get_session() as session:
                # Check if material already exists
                existing = session.query(Material).filter_by(name=material_data.name).first()
                if existing:
                    raise AlreadyExistsError(f"Material '{material_data.name}' already exists")

                # Extract data
                material_dict = material_data.dict(exclude_unset=True)

                # Separate PSD fields from material fields
                psd_fields = ['psd_mode', 'psd_d50', 'psd_n', 'psd_dmax', 'psd_median',
                             'psd_spread', 'psd_exponent', 'psd_custom_points']
                psd_data = {}
                for field in list(material_dict.keys()):
                    if field in psd_fields:
                        psd_data[field] = material_dict.pop(field)

                # Separate tags
                tag_names = material_dict.pop('tags', [])

                # Create or get PSD data
                if psd_data:
                    new_psd = PSDData(**psd_data)
                    session.add(new_psd)
                    session.flush()  # Get the ID
                    material_dict['psd_data_id'] = new_psd.id
                elif not material_dict.get('psd_data_id'):
                    raise ServiceError("Material must have PSD data (provide psd_data_id or PSD parameters)")

                # Create material object
                material = Material(**material_dict)

                # Add tags
                for tag_name in tag_names:
                    tag = self._get_or_create_tag(session, tag_name)
                    material.tags.append(tag)

                # Add phase composition
                if phase_compositions:
                    self._add_phases(session, material, phase_compositions)

                # Auto-calculate specific gravity if requested
                if auto_calculate_sg and self.gems_parser and material.phases:
                    calculated_sg = material.calculate_specific_gravity_from_gems(self.gems_parser)
                    if calculated_sg:
                        material.specific_gravity = calculated_sg
                        self.logger.info(f"Auto-calculated SG for {material.name}: {calculated_sg:.3f}")

                # Validate material
                self._validate_material(material)

                session.add(material)
                session.flush()

                self.logger.info(f"Created material: {material.name} with {len(material.phases)} phases and {len(material.tags)} tags")
                return material

        except AlreadyExistsError:
            raise
        except IntegrityError as e:
            self.logger.error(f"Database integrity error creating material: {e}")
            raise ServiceError(f"Database error: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create material: {e}")
            raise ServiceError(f"Failed to create material: {e}")

    def update(self, material_id: int, material_data: MaterialUpdate) -> Material:
        """
        Update an existing material.

        Args:
            material_id: Material ID to update
            material_data: Update data

        Returns:
            Updated Material instance

        Raises:
            NotFoundError: If material not found
            ServiceError: If material is immutable or update fails
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable (migrated from VCCTL)")

                # Update material fields
                update_dict = material_data.dict(exclude_unset=True, exclude={'tags'})

                # Handle PSD updates
                psd_fields = ['psd_mode', 'psd_d50', 'psd_n', 'psd_dmax', 'psd_median',
                             'psd_spread', 'psd_exponent', 'psd_custom_points']
                psd_updates = {k: v for k, v in update_dict.items() if k in psd_fields}

                if psd_updates and material.psd_data:
                    for key, value in psd_updates.items():
                        setattr(material.psd_data, key, value)
                    # Remove PSD fields from material updates
                    for key in psd_updates:
                        update_dict.pop(key, None)

                # Update material attributes
                for key, value in update_dict.items():
                    setattr(material, key, value)

                # Update tags if provided
                if hasattr(material_data, 'tags') and material_data.tags is not None:
                    self._update_tags(session, material, material_data.tags)

                # Validate
                self._validate_material(material)

                session.flush()
                self.logger.info(f"Updated material: {material.name}")
                return material

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to update material ID {material_id}: {e}")
            raise ServiceError(f"Failed to update material: {e}")

    def delete(self, material_id: int) -> bool:
        """
        Delete a material.

        Args:
            material_id: Material ID to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If material not found
            ServiceError: If material is immutable or deletion fails
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable (migrated from VCCTL)")

                name = material.name
                session.delete(material)
                session.flush()

                self.logger.info(f"Deleted material: {name}")
                return True

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to delete material ID {material_id}: {e}")
            raise ServiceError(f"Failed to delete material: {e}")

    # ========== Phase Composition Management ==========

    def add_phase(
        self,
        material_id: int,
        gem_phase_name: str,
        mass_fraction: float,
        volume_fraction: Optional[float] = None,
        surface_fraction: Optional[float] = None,
        validate_gems: bool = True,
        validate_total: bool = True
    ) -> MaterialPhase:
        """
        Add a phase to a material's composition.

        Args:
            material_id: Material ID
            gem_phase_name: GEM phase name
            mass_fraction: Mass fraction (0.0-1.0)
            volume_fraction: Optional volume fraction
            surface_fraction: Optional surface fraction
            validate_gems: If True, validate phase name against GEMS database
            validate_total: If True, validate total phase fractions sum to 1.0

        Returns:
            Created MaterialPhase instance

        Raises:
            NotFoundError: If material not found
            ServiceError: If validation fails or phase already exists
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                # Validate phase name against GEMS if requested
                if validate_gems and self.gems_parser:
                    if gem_phase_name not in self.gems_parser.phases:
                        raise ServiceError(f"Phase '{gem_phase_name}' not found in GEMS database")

                # Check if phase already exists
                existing_phase = session.query(MaterialPhase).filter_by(
                    material_id=material_id,
                    gem_phase_name=gem_phase_name
                ).first()
                if existing_phase:
                    raise ServiceError(f"Phase '{gem_phase_name}' already exists in material")

                # Create phase
                phase = MaterialPhase(
                    material_id=material_id,
                    gem_phase_name=gem_phase_name,
                    mass_fraction=mass_fraction,
                    volume_fraction=volume_fraction,
                    surface_fraction=surface_fraction
                )

                # Validate fractions
                is_valid, message = phase.validate_fractions()
                if not is_valid:
                    raise ServiceError(f"Invalid phase fractions: {message}")

                session.add(phase)
                session.flush()

                # Validate total material composition (skip during batch operations)
                if validate_total:
                    self._validate_material(material)

                self.logger.info(f"Added phase '{gem_phase_name}' to material '{material.name}'")
                return phase

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to add phase to material ID {material_id}: {e}")
            raise ServiceError(f"Failed to add phase: {e}")

    def update_phase(
        self,
        material_id: int,
        gem_phase_name: str,
        mass_fraction: Optional[float] = None,
        volume_fraction: Optional[float] = None,
        surface_fraction: Optional[float] = None
    ) -> MaterialPhase:
        """
        Update a phase in a material's composition.

        Args:
            material_id: Material ID
            gem_phase_name: GEM phase name
            mass_fraction: New mass fraction (optional)
            volume_fraction: New volume fraction (optional)
            surface_fraction: New surface fraction (optional)

        Returns:
            Updated MaterialPhase instance

        Raises:
            NotFoundError: If material or phase not found
            ServiceError: If material is immutable or validation fails
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                phase = session.query(MaterialPhase).filter_by(
                    material_id=material_id,
                    gem_phase_name=gem_phase_name
                ).first()
                if not phase:
                    raise NotFoundError(f"Phase '{gem_phase_name}' not found in material")

                # Update fractions
                if mass_fraction is not None:
                    phase.mass_fraction = mass_fraction
                if volume_fraction is not None:
                    phase.volume_fraction = volume_fraction
                if surface_fraction is not None:
                    phase.surface_fraction = surface_fraction

                # Validate
                is_valid, message = phase.validate_fractions()
                if not is_valid:
                    raise ServiceError(f"Invalid phase fractions: {message}")

                session.flush()

                # Validate total material composition
                self._validate_material(material)

                self.logger.info(f"Updated phase '{gem_phase_name}' in material '{material.name}'")
                return phase

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to update phase in material ID {material_id}: {e}")
            raise ServiceError(f"Failed to update phase: {e}")

    def remove_phase(self, material_id: int, gem_phase_name: str) -> bool:
        """
        Remove a phase from a material's composition.

        Args:
            material_id: Material ID
            gem_phase_name: GEM phase name

        Returns:
            True if removed successfully

        Raises:
            NotFoundError: If material or phase not found
            ServiceError: If material is immutable
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                phase = session.query(MaterialPhase).filter_by(
                    material_id=material_id,
                    gem_phase_name=gem_phase_name
                ).first()
                if not phase:
                    raise NotFoundError(f"Phase '{gem_phase_name}' not found in material")

                session.delete(phase)
                session.flush()

                self.logger.info(f"Removed phase '{gem_phase_name}' from material '{material.name}'")
                return True

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove phase from material ID {material_id}: {e}")
            raise ServiceError(f"Failed to remove phase: {e}")

    # ========== Tag Management ==========

    def add_tag(self, material_id: int, tag_name: str) -> Material:
        """
        Add a tag to a material.

        Args:
            material_id: Material ID
            tag_name: Tag name (will be lowercased)

        Returns:
            Updated Material instance

        Raises:
            NotFoundError: If material not found
            ServiceError: If material is immutable or tag already exists
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.tags)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                tag_name = tag_name.strip().lower()
                if tag_name in material.tag_names:
                    raise ServiceError(f"Tag '{tag_name}' already exists on material")

                tag = self._get_or_create_tag(session, tag_name)
                material.tags.append(tag)
                session.flush()

                self.logger.info(f"Added tag '{tag_name}' to material '{material.name}'")
                return material

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to add tag to material ID {material_id}: {e}")
            raise ServiceError(f"Failed to add tag: {e}")

    def remove_tag(self, material_id: int, tag_name: str) -> Material:
        """
        Remove a tag from a material.

        Args:
            material_id: Material ID
            tag_name: Tag name

        Returns:
            Updated Material instance

        Raises:
            NotFoundError: If material or tag not found
            ServiceError: If material is immutable
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.tags)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                tag_name = tag_name.strip().lower()
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag or tag not in material.tags:
                    raise NotFoundError(f"Tag '{tag_name}' not found on material")

                material.tags.remove(tag)
                session.flush()

                self.logger.info(f"Removed tag '{tag_name}' from material '{material.name}'")
                return material

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove tag from material ID {material_id}: {e}")
            raise ServiceError(f"Failed to remove tag: {e}")

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tag names in the database.

        Returns:
            List of tag names
        """
        try:
            with self.db_service.get_read_only_session() as session:
                tags = session.query(Tag.name).order_by(Tag.name).all()
                return [tag[0] for tag in tags]

        except Exception as e:
            self.logger.error(f"Failed to get all tags: {e}")
            raise ServiceError(f"Failed to retrieve tags: {e}")

    # ========== Search and Filter ==========

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = True,
        include_immutable: bool = True
    ) -> List[Material]:
        """
        Search materials by tags.

        Args:
            tags: List of tag names to search for
            match_all: If True, require all tags; if False, match any tag
            include_immutable: If False, exclude migrated materials

        Returns:
            List of matching Material instances
        """
        try:
            with self.db_service.get_read_only_session() as session:
                query = session.query(Material).options(
                    joinedload(Material.psd_data),
                    joinedload(Material.phases),
                    joinedload(Material.tags)
                ).join(Material.tags)

                # Normalize tags
                tags = [t.strip().lower() for t in tags]

                if match_all:
                    # Require all tags
                    for tag in tags:
                        query = query.filter(Material.tags.any(Tag.name == tag))
                else:
                    # Match any tag
                    query = query.filter(Tag.name.in_(tags))

                if not include_immutable:
                    query = query.filter(Material.immutable == False)

                return query.distinct().order_by(Material.name).all()

        except Exception as e:
            self.logger.error(f"Failed to search materials by tags: {e}")
            raise ServiceError(f"Failed to search materials: {e}")

    def search_by_phase(self, gem_phase_name: str) -> List[Material]:
        """
        Find all materials containing a specific GEM phase.

        Args:
            gem_phase_name: GEM phase name

        Returns:
            List of Material instances containing this phase
        """
        try:
            with self.db_service.get_read_only_session() as session:
                return session.query(Material).options(
                    joinedload(Material.psd_data),
                    joinedload(Material.phases),
                    joinedload(Material.tags)
                ).join(Material.phases).filter(
                    MaterialPhase.gem_phase_name == gem_phase_name
                ).distinct().order_by(Material.name).all()

        except Exception as e:
            self.logger.error(f"Failed to search materials by phase: {e}")
            raise ServiceError(f"Failed to search materials: {e}")

    # ========== Helper Methods ==========

    def _get_or_create_tag(self, session: Session, tag_name: str) -> Tag:
        """Get or create a tag."""
        tag_name = tag_name.strip().lower()
        tag = session.query(Tag).filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.flush()
        return tag

    def _update_tags(self, session: Session, material: Material, tag_names: List[str]) -> None:
        """Update material tags (replace all)."""
        # Clear existing tags
        material.tags.clear()

        # Add new tags
        for tag_name in tag_names:
            tag = self._get_or_create_tag(session, tag_name)
            material.tags.append(tag)

    def _add_phases(
        self,
        session: Session,
        material: Material,
        phase_compositions: List[Dict[str, float]]
    ) -> None:
        """Add phase composition to material."""
        for phase_data in phase_compositions:
            gem_phase_name = phase_data.get('gem_phase_name')
            mass_fraction = phase_data.get('mass_fraction')

            if not gem_phase_name or mass_fraction is None:
                raise ServiceError("Phase data must include 'gem_phase_name' and 'mass_fraction'")

            # Validate phase name against GEMS if available
            if self.gems_parser and gem_phase_name not in self.gems_parser.phases:
                raise ServiceError(f"Phase '{gem_phase_name}' not found in GEMS database")

            phase = MaterialPhase(
                material=material,
                gem_phase_name=gem_phase_name,
                mass_fraction=mass_fraction,
                volume_fraction=phase_data.get('volume_fraction'),
                surface_fraction=phase_data.get('surface_fraction')
            )

            # Validate fractions
            is_valid, message = phase.validate_fractions()
            if not is_valid:
                raise ServiceError(f"Invalid phase fractions for '{gem_phase_name}': {message}")

            session.add(phase)

    def _validate_material(self, material: Material) -> None:
        """Validate material properties."""
        # Validate phase fractions
        is_valid, message = material.validate_phase_fractions()
        if not is_valid:
            raise ServiceError(f"Material validation failed: {message}")

        # Check specific gravity is reasonable
        if material.specific_gravity and (material.specific_gravity <= 0 or material.specific_gravity > 5.0):
            raise ServiceError(f"Specific gravity {material.specific_gravity} is out of range (0-5)")

    def validate_material(self, material_id: int) -> Tuple[bool, str]:
        """
        Validate a material's total composition.

        Call this after batch operations (adding multiple phases with validate_total=False).

        Args:
            material_id: Material ID to validate

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.phases)
                ).filter_by(id=material_id).first()
                if not material:
                    return False, f"Material ID {material_id} not found"

                self._validate_material(material)
                return True, "Valid"
        except ServiceError as e:
            return False, str(e)
        except Exception as e:
            self.logger.error(f"Validation error for material {material_id}: {e}")
            return False, str(e)

    # ========== Clinker Extension Management ==========

    def set_clinker_surface_fractions(
        self,
        material_id: int,
        fractions: Dict[str, float]
    ) -> ClinkerExtension:
        """
        Set surface area fractions for a clinker material.

        Args:
            material_id: Material ID (must be marked as is_clinker=True)
            fractions: Dict with keys 'c3s', 'c2s', 'c3a', 'c4af', 'k2so4', 'na2so4'

        Returns:
            Updated ClinkerExtension instance

        Raises:
            NotFoundError: If material not found
            ServiceError: If material is not a clinker or fractions invalid
        """
        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                # Allow both pure clinkers (is_clinker) and cements with clinker (has_clinker)
                if not material.is_clinker and not material.has_clinker:
                    raise ServiceError(f"Material '{material.name}' is not marked as clinker")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                # Get or create clinker extension
                clinker_data = material.clinker_data
                if not clinker_data:
                    clinker_data = ClinkerExtension(material_id=material_id)
                    session.add(clinker_data)

                # Set fractions
                clinker_data.set_surface_fractions(fractions)

                # Validate
                is_valid, message = clinker_data.validate_surface_fractions()
                if not is_valid:
                    raise ServiceError(f"Invalid surface fractions: {message}")

                session.flush()
                self.logger.info(f"Set surface fractions for clinker '{material.name}'")
                return clinker_data

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to set clinker surface fractions: {e}")
            raise ServiceError(f"Failed to set surface fractions: {e}")

    def get_clinker_surface_fractions(self, material_id: int) -> Optional[Dict[str, float]]:
        """
        Get surface area fractions for a clinker material.

        Args:
            material_id: Material ID

        Returns:
            Dict of surface fractions or None if not a clinker
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                # Check if material has clinker data (is_clinker for pure clinkers, has_clinker for cements)
                if not material.clinker_data:
                    return None

                return material.clinker_data.get_surface_fractions_dict()

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get clinker surface fractions: {e}")
            raise ServiceError(f"Failed to get surface fractions: {e}")

    def get_clinker_extension(self, material_id: int) -> Optional[ClinkerExtension]:
        """
        Get the full ClinkerExtension object for a material.

        Works for both pure clinker materials (is_clinker=True) and
        self-contained cements that have clinker phases (has_clinker=True).

        Args:
            material_id: Material ID

        Returns:
            ClinkerExtension object or None if material has no clinker data
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                # Return clinker_data if available (works for both is_clinker and has_clinker)
                if material.clinker_data:
                    # Detach from session so it can be used after session closes
                    session.expunge(material.clinker_data)
                    return material.clinker_data

                return None

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get clinker extension: {e}")
            raise ServiceError(f"Failed to get clinker extension: {e}")

    def set_clinker_correlation(
        self,
        material_id: int,
        correlation_name: str,
        data: bytes
    ) -> ClinkerExtension:
        """
        Set a correlation function BLOB for a clinker material.

        Args:
            material_id: Material ID
            correlation_name: One of 'sil', 'c3s', 'alu', 'c3a', 'c4af', 'k2o', 'n2o'
            data: Binary correlation data

        Returns:
            Updated ClinkerExtension instance

        Raises:
            NotFoundError: If material not found
            ServiceError: If invalid correlation name or material not a clinker
        """
        valid_names = ['sil', 'c3s', 'alu', 'c3a', 'c4af', 'k2o', 'n2o']

        try:
            with self.db_service.get_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                # Allow both pure clinkers (is_clinker) and cements with clinker (has_clinker)
                if not material.is_clinker and not material.has_clinker:
                    raise ServiceError(f"Material '{material.name}' is not marked as clinker")

                if material.immutable:
                    raise ServiceError(f"Material '{material.name}' is immutable")

                if correlation_name not in valid_names:
                    raise ServiceError(f"Invalid correlation name '{correlation_name}'. Must be one of: {valid_names}")

                # Get or create clinker extension
                clinker_data = material.clinker_data
                if not clinker_data:
                    clinker_data = ClinkerExtension(material_id=material_id)
                    session.add(clinker_data)

                # Set the correlation data
                attr_name = f"correlation_{correlation_name}"
                setattr(clinker_data, attr_name, data)

                session.flush()
                self.logger.info(f"Set correlation '{correlation_name}' for clinker '{material.name}'")
                return clinker_data

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to set clinker correlation: {e}")
            raise ServiceError(f"Failed to set correlation: {e}")

    def get_clinker_correlation(self, material_id: int, correlation_name: str) -> Optional[bytes]:
        """
        Get a correlation function BLOB for a clinker material.

        Args:
            material_id: Material ID
            correlation_name: One of 'sil', 'c3s', 'alu', 'c3a', 'c4af', 'k2o', 'n2o'

        Returns:
            Binary correlation data or None
        """
        valid_names = ['sil', 'c3s', 'alu', 'c3a', 'c4af', 'k2o', 'n2o']

        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if correlation_name not in valid_names:
                    raise ServiceError(f"Invalid correlation name '{correlation_name}'. Must be one of: {valid_names}")

                # Check if material has clinker data (works for both is_clinker and has_clinker)
                if not material.clinker_data:
                    return None

                attr_name = f"correlation_{correlation_name}"
                return getattr(material.clinker_data, attr_name, None)

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to get clinker correlation: {e}")
            raise ServiceError(f"Failed to get correlation: {e}")

    def get_all_clinker_correlations(self, material_id: int) -> Dict[str, Optional[bytes]]:
        """
        Get all correlation functions for a clinker material.

        Args:
            material_id: Material ID

        Returns:
            Dict mapping correlation names to binary data (None if not set)
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.clinker_data)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                # Check if material has clinker data (works for both is_clinker and has_clinker)
                if not material.clinker_data:
                    return {}

                clinker_data = material.clinker_data
                return {
                    'sil': clinker_data.correlation_sil,
                    'c3s': clinker_data.correlation_c3s,
                    'alu': clinker_data.correlation_alu,
                    'c3a': clinker_data.correlation_c3a,
                    'c4af': clinker_data.correlation_c4af,
                    'k2o': clinker_data.correlation_k2o,
                    'n2o': clinker_data.correlation_n2o
                }

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get clinker correlations: {e}")
            raise ServiceError(f"Failed to get correlations: {e}")

    def create_clinker_material(
        self,
        material_data: MaterialCreate,
        phase_compositions: List[Dict[str, float]],
        surface_fractions: Dict[str, float],
        correlations: Optional[Dict[str, bytes]] = None,
        auto_calculate_sg: bool = True
    ) -> Material:
        """
        Create a complete clinker material with extension data.

        This is a convenience method that creates the material, sets is_clinker=True,
        adds phase composition, and initializes the clinker extension data.

        Args:
            material_data: Material creation data
            phase_compositions: Phase composition data
            surface_fractions: Surface area fractions for 6 clinker phases
            correlations: Optional dict of correlation name -> binary data
            auto_calculate_sg: Whether to auto-calculate specific gravity

        Returns:
            Created Material instance with clinker extension

        Raises:
            ServiceError: If creation fails
        """
        try:
            with self.db_service.get_session() as session:
                # Force is_clinker=True
                material_data_dict = material_data.dict()
                material_data_dict['is_clinker'] = True

                # Create material
                material = self.create(
                    MaterialCreate(**material_data_dict),
                    phase_compositions=phase_compositions,
                    auto_calculate_sg=auto_calculate_sg
                )

                # Now add clinker extension data
                self.set_clinker_surface_fractions(material.id, surface_fractions)

                # Add correlations if provided
                if correlations:
                    for name, data in correlations.items():
                        if data:
                            self.set_clinker_correlation(material.id, name, data)

                self.logger.info(f"Created clinker material: {material.name}")
                return material

        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create clinker material: {e}")
            raise ServiceError(f"Failed to create clinker material: {e}")

    # ========== Composite Material Management ==========

    def add_component(
        self,
        parent_material_id: int,
        component_material_id: int,
        mass_fraction: float
    ) -> MaterialComponent:
        """
        Add a component material to a composite material.

        Args:
            parent_material_id: ID of the composite (parent) material
            component_material_id: ID of the component material to add
            mass_fraction: Mass fraction of this component (0.0-1.0)

        Returns:
            Created MaterialComponent instance

        Raises:
            NotFoundError: If parent or component material not found
            ServiceError: If validation fails
        """
        try:
            with self.db_service.get_session() as session:
                # Get parent material
                parent = session.query(Material).options(
                    joinedload(Material.components)
                ).filter_by(id=parent_material_id).first()

                if not parent:
                    raise NotFoundError(f"Parent material ID {parent_material_id} not found")

                if parent.immutable:
                    raise ServiceError(f"Material '{parent.name}' is immutable")

                # Get component material
                component = session.query(Material).filter_by(id=component_material_id).first()
                if not component:
                    raise NotFoundError(f"Component material ID {component_material_id} not found")

                # Validate
                if parent_material_id == component_material_id:
                    raise ServiceError("Component cannot be the same as parent")

                if mass_fraction <= 0 or mass_fraction > 1.0:
                    raise ServiceError(f"Mass fraction must be between 0 and 1, got {mass_fraction}")

                # Check if component already exists
                existing = session.query(MaterialComponent).filter_by(
                    parent_material_id=parent_material_id,
                    component_material_id=component_material_id
                ).first()
                if existing:
                    raise ServiceError(f"Component '{component.name}' already exists in material")

                # Create component entry
                mat_component = MaterialComponent(
                    parent_material_id=parent_material_id,
                    component_material_id=component_material_id,
                    mass_fraction=mass_fraction
                )

                # Validate component
                is_valid, message = mat_component.validate()
                if not is_valid:
                    raise ServiceError(f"Invalid component: {message}")

                session.add(mat_component)

                # Update has_clinker flag if component is clinker or has clinker
                if component.is_clinker or component.has_clinker:
                    parent.has_clinker = True
                    parent.clinker_source_id = component.id if component.is_clinker else component.clinker_source_id

                session.flush()
                self.logger.info(f"Added component '{component.name}' to '{parent.name}' ({mass_fraction:.2%})")
                return mat_component

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to add component: {e}")
            raise ServiceError(f"Failed to add component: {e}")

    def remove_component(
        self,
        parent_material_id: int,
        component_material_id: int
    ) -> bool:
        """
        Remove a component from a composite material.

        Args:
            parent_material_id: ID of the composite (parent) material
            component_material_id: ID of the component material to remove

        Returns:
            True if removed successfully

        Raises:
            NotFoundError: If parent or component not found
            ServiceError: If material is immutable
        """
        try:
            with self.db_service.get_session() as session:
                # Get parent material
                parent = session.query(Material).options(
                    joinedload(Material.components).joinedload(MaterialComponent.component_material)
                ).filter_by(id=parent_material_id).first()

                if not parent:
                    raise NotFoundError(f"Parent material ID {parent_material_id} not found")

                if parent.immutable:
                    raise ServiceError(f"Material '{parent.name}' is immutable")

                # Find component
                mat_component = session.query(MaterialComponent).filter_by(
                    parent_material_id=parent_material_id,
                    component_material_id=component_material_id
                ).first()

                if not mat_component:
                    raise NotFoundError(f"Component ID {component_material_id} not found in material")

                component_name = mat_component.component_material.name if mat_component.component_material else "Unknown"

                session.delete(mat_component)

                # Update has_clinker flag - recalculate from remaining components
                remaining_components = session.query(MaterialComponent).filter_by(
                    parent_material_id=parent_material_id
                ).all()

                has_clinker = False
                clinker_source_id = None
                for comp in remaining_components:
                    if comp.component_material_id != component_material_id:
                        comp_mat = session.query(Material).filter_by(id=comp.component_material_id).first()
                        if comp_mat and (comp_mat.is_clinker or comp_mat.has_clinker):
                            has_clinker = True
                            clinker_source_id = comp_mat.id if comp_mat.is_clinker else comp_mat.clinker_source_id

                parent.has_clinker = has_clinker
                parent.clinker_source_id = clinker_source_id

                session.flush()
                self.logger.info(f"Removed component '{component_name}' from '{parent.name}'")
                return True

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove component: {e}")
            raise ServiceError(f"Failed to remove component: {e}")

    def update_component_fraction(
        self,
        parent_material_id: int,
        component_material_id: int,
        mass_fraction: float
    ) -> MaterialComponent:
        """
        Update the mass fraction of a component in a composite material.

        Args:
            parent_material_id: ID of the composite (parent) material
            component_material_id: ID of the component material
            mass_fraction: New mass fraction (0.0-1.0)

        Returns:
            Updated MaterialComponent instance

        Raises:
            NotFoundError: If parent or component not found
            ServiceError: If validation fails
        """
        try:
            with self.db_service.get_session() as session:
                # Get parent material
                parent = session.query(Material).filter_by(id=parent_material_id).first()
                if not parent:
                    raise NotFoundError(f"Parent material ID {parent_material_id} not found")

                if parent.immutable:
                    raise ServiceError(f"Material '{parent.name}' is immutable")

                # Find component
                mat_component = session.query(MaterialComponent).filter_by(
                    parent_material_id=parent_material_id,
                    component_material_id=component_material_id
                ).first()

                if not mat_component:
                    raise NotFoundError(f"Component ID {component_material_id} not found in material")

                if mass_fraction <= 0 or mass_fraction > 1.0:
                    raise ServiceError(f"Mass fraction must be between 0 and 1, got {mass_fraction}")

                mat_component.mass_fraction = mass_fraction
                session.flush()

                self.logger.info(f"Updated component fraction in '{parent.name}' to {mass_fraction:.2%}")
                return mat_component

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            self.logger.error(f"Failed to update component fraction: {e}")
            raise ServiceError(f"Failed to update component fraction: {e}")

    def get_components(self, material_id: int) -> List[Dict]:
        """
        Get all components of a composite material.

        Args:
            material_id: Material ID

        Returns:
            List of dicts with component info: {'id', 'name', 'mass_fraction', 'is_clinker'}
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.components).joinedload(MaterialComponent.component_material)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if not material.components:
                    return []

                result = []
                for comp in material.components:
                    comp_mat = comp.component_material
                    result.append({
                        'id': comp.component_material_id,
                        'name': comp_mat.name if comp_mat else f"Material {comp.component_material_id}",
                        'mass_fraction': comp.mass_fraction,
                        'is_clinker': comp_mat.is_clinker if comp_mat else False,
                        'has_clinker': comp_mat.has_clinker if comp_mat else False
                    })

                return result

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get components: {e}")
            raise ServiceError(f"Failed to get components: {e}")

    def validate_component_fractions(self, material_id: int) -> Tuple[bool, str]:
        """
        Validate that component mass fractions sum to 1.0.

        Args:
            material_id: Material ID

        Returns:
            (is_valid, message)
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.components)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if not material.components:
                    return True, "No components"

                total = sum(comp.mass_fraction for comp in material.components)
                if abs(total - 1.0) > 0.01:
                    return False, f"Component fractions sum to {total:.4f}, should be 1.0"

                return True, "Valid"

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to validate component fractions: {e}")
            raise ServiceError(f"Failed to validate: {e}")

    def calculate_composite_phases(self, material_id: int) -> List[Dict[str, float]]:
        """
        Calculate aggregated phase composition from all components.

        For each component, multiplies its phase fractions by the component's
        mass fraction, then sums across all components.

        Args:
            material_id: Material ID

        Returns:
            List of dicts: [{'gem_phase_name': str, 'mass_fraction': float}, ...]
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).options(
                    joinedload(Material.components).joinedload(MaterialComponent.component_material).joinedload(Material.phases)
                ).filter_by(id=material_id).first()

                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if not material.components:
                    # Not a composite - return existing phases
                    return [
                        {'gem_phase_name': p.gem_phase_name, 'mass_fraction': p.mass_fraction}
                        for p in material.phases
                    ]

                # Aggregate phases from all components
                phase_totals: Dict[str, float] = {}

                for comp in material.components:
                    comp_mat = comp.component_material
                    if not comp_mat or not comp_mat.phases:
                        continue

                    for phase in comp_mat.phases:
                        if phase.mass_fraction is None:
                            continue

                        # Scale by component's mass fraction
                        scaled_fraction = phase.mass_fraction * comp.mass_fraction
                        phase_name = phase.gem_phase_name

                        if phase_name in phase_totals:
                            phase_totals[phase_name] += scaled_fraction
                        else:
                            phase_totals[phase_name] = scaled_fraction

                # Convert to list
                return [
                    {'gem_phase_name': name, 'mass_fraction': fraction}
                    for name, fraction in sorted(phase_totals.items())
                ]

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to calculate composite phases: {e}")
            raise ServiceError(f"Failed to calculate phases: {e}")

    def create_composite_material(
        self,
        material_data: MaterialCreate,
        components: List[Dict[str, float]],
        auto_calculate_phases: bool = True,
        auto_calculate_sg: bool = True
    ) -> Material:
        """
        Create a composite material from existing materials.

        Args:
            material_data: Material creation data
            components: List of dicts with 'material_id' and 'mass_fraction'
            auto_calculate_phases: If True, calculate aggregated phases from components
            auto_calculate_sg: If True, calculate specific gravity from composition

        Returns:
            Created Material instance

        Raises:
            ServiceError: If creation fails
        """
        try:
            # Validate component fractions sum to 1.0
            total_fraction = sum(c['mass_fraction'] for c in components)
            if abs(total_fraction - 1.0) > 0.01:
                raise ServiceError(f"Component fractions must sum to 1.0, got {total_fraction:.4f}")

            # Create the material first (without phases - will add from components)
            material = self.create(material_data, phase_compositions=None, auto_calculate_sg=False)

            # Add components
            for comp_data in components:
                self.add_component(
                    material.id,
                    comp_data['material_id'],
                    comp_data['mass_fraction']
                )

            # Calculate and set aggregated phases if requested
            if auto_calculate_phases:
                aggregated_phases = self.calculate_composite_phases(material.id)
                for phase_data in aggregated_phases:
                    self.add_phase(
                        material.id,
                        phase_data['gem_phase_name'],
                        phase_data['mass_fraction'],
                        validate_gems=True
                    )

            # Auto-calculate SG if requested
            if auto_calculate_sg and self.gems_parser:
                with self.db_service.get_session() as session:
                    mat = session.query(Material).options(
                        joinedload(Material.phases)
                    ).filter_by(id=material.id).first()

                    if mat and mat.phases:
                        calculated_sg = mat.calculate_specific_gravity_from_gems(self.gems_parser)
                        if calculated_sg:
                            mat.specific_gravity = calculated_sg
                            session.flush()

            self.logger.info(f"Created composite material: {material.name} with {len(components)} components")
            return material

        except ServiceError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create composite material: {e}")
            raise ServiceError(f"Failed to create composite material: {e}")

    def get_clinker_for_composite(self, material_id: int) -> Optional[Material]:
        """
        Get the clinker material for a composite that contains clinker.

        Args:
            material_id: Composite material ID

        Returns:
            Clinker Material or None if no clinker
        """
        try:
            with self.db_service.get_read_only_session() as session:
                material = session.query(Material).filter_by(id=material_id).first()
                if not material:
                    raise NotFoundError(f"Material ID {material_id} not found")

                if not material.has_clinker or not material.clinker_source_id:
                    return None

                return session.query(Material).options(
                    joinedload(Material.clinker_data),
                    joinedload(Material.phases)
                ).filter_by(id=material.clinker_source_id).first()

        except NotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get clinker for composite: {e}")
            raise ServiceError(f"Failed to get clinker: {e}")

#!/usr/bin/env python3
"""
Material Service for THAMES

Provides business logic for tag-based material management with phase composition.
Handles CRUD operations, tag management, phase validation, and GEMS integration.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
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
    PSDData
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
        validate_gems: bool = True
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

                # Validate total material composition
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

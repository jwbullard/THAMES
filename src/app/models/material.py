#!/usr/bin/env python3
"""
Material Model for THAMES

Tag-based material system for flexible phase composition.
Unlike VCCTL's rigid material categories (Cement, Fly Ash, etc.),
THAMES uses user-defined tags for material classification.

Materials store only composition and physical properties.
Kinetic parameters are defined in Mix Design, not in materials.
"""

from typing import Optional, List
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator, model_validator

from app.database.base import Base


# Association table for many-to-many Material <-> Tags
material_tags = Table(
    'material_tags',
    Base.metadata,
    Column('material_id', Integer, ForeignKey('material.id'), primary_key=True),
    Column('tag', String(64), ForeignKey('tag.name'), primary_key=True)
)


class Material(Base):
    """
    Material model representing any powder material in THAMES.

    Uses tag-based classification instead of rigid categories.
    Phase composition stored in MaterialPhase relationship.
    NO kinetic parameters - those are defined in Mix Design.
    """

    __tablename__ = 'material'

    # Primary key - auto-incrementing integer ID
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Material name - unique identifier
    name = Column(String(128), nullable=False, unique=True)

    # Tags for classification and search (many-to-many)
    # Examples: ["cement", "type-i"], ["limestone", "high-purity"], ["fly_ash", "class-f"]
    tags = relationship(
        "Tag",
        secondary=material_tags,
        back_populates="materials",
        cascade="all, delete"
    )

    # Physical properties
    specific_gravity = Column(Float, nullable=True, default=3.15,
                            doc="Specific gravity of material")
    specific_surface_area = Column(Float, nullable=True,
                                   doc="Specific surface area (m²/kg)")

    # PSD relationship (shared with VCCTL models) - REQUIRED for THAMES
    psd_data_id = Column(Integer, ForeignKey('psd_data.id'), nullable=False)
    psd_data = relationship('PSDData', backref='thames_materials')

    # Phase composition (many-to-many via MaterialPhase)
    phases = relationship(
        'MaterialPhase',
        back_populates='material',
        cascade='all, delete-orphan'
    )

    # Metadata
    description = Column(Text, nullable=True, doc="Material description")
    source = Column(String(255), nullable=True, doc="Material source")
    notes = Column(Text, nullable=True, doc="Additional notes")

    # Immutable flag for migrated VCCTL materials
    immutable = Column(Boolean, nullable=False, default=False,
                      doc="Whether this material is read-only (migrated from VCCTL)")

    # Clinker and composite material flags
    is_clinker = Column(Boolean, nullable=False, default=False,
                       doc="Whether this material is a clinker (has correlation functions, surface fractions)")
    has_clinker = Column(Boolean, nullable=False, default=False,
                        doc="Whether this composite material contains clinker")
    clinker_source_id = Column(Integer, ForeignKey('material.id'), nullable=True,
                               doc="ID of the clinker material this composite contains")

    # Relationship to clinker source (for composites)
    clinker_source = relationship('Material', remote_side=[id], foreign_keys=[clinker_source_id])

    # Particle shape settings
    # shape_type: 0 = SPHERES (default), 1 = REALSHAPE
    # shape_set: Name of the particle shape set (e.g., "cement116") if using real shapes
    particle_shape_type = Column(Integer, nullable=False, default=0,
                                  doc="Particle shape type: 0=spheres, 1=real shapes")
    particle_shape_set = Column(String(128), nullable=True,
                                 doc="Name of particle shape set for real shapes")

    # Relationship to clinker extension data (for clinker materials)
    clinker_data = relationship('ClinkerExtension', uselist=False, back_populates='material',
                                cascade='all, delete-orphan')

    # Relationship to components (for composite materials)
    components = relationship('MaterialComponent', foreign_keys='MaterialComponent.parent_material_id',
                              back_populates='parent_material', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        """String representation of the material."""
        tag_str = ",".join([t.name for t in self.tags]) if self.tags else "no-tags"
        return f"<Material(name='{self.name}', tags=[{tag_str}])>"

    @property
    def tag_names(self) -> List[str]:
        """Get list of tag names."""
        return [tag.name for tag in self.tags] if self.tags else []

    @property
    def has_phase_data(self) -> bool:
        """Check if material has phase composition data."""
        return len(self.phases) > 0

    @property
    def total_phase_fraction(self) -> Optional[float]:
        """Calculate total mass fraction from all phases."""
        if not self.phases:
            return None
        return sum(phase.mass_fraction for phase in self.phases if phase.mass_fraction is not None)

    @property
    def gem_phase_names(self) -> List[str]:
        """Get list of GEM phase names in this material."""
        return [phase.gem_phase_name for phase in self.phases]

    @property
    def density(self) -> Optional[float]:
        """Calculate density from specific gravity (kg/m³)."""
        if self.specific_gravity is not None:
            return self.specific_gravity * 1000  # kg/m³
        return None

    @property
    def is_composite(self) -> bool:
        """Check if material is a composite (has component materials)."""
        return len(self.components) > 0 if self.components else False

    @property
    def component_count(self) -> int:
        """Get number of component materials."""
        return len(self.components) if self.components else 0

    def validate_phase_fractions(self) -> tuple[bool, str]:
        """
        Validate that phase fractions are reasonable.

        Returns:
            (is_valid, message)
        """
        if not self.phases:
            return True, "No phases to validate"

        # Check individual fractions are in valid range
        for phase in self.phases:
            if phase.mass_fraction is not None:
                if phase.mass_fraction < 0 or phase.mass_fraction > 1:
                    return False, f"Phase '{phase.gem_phase_name}' has invalid fraction: {phase.mass_fraction}"

        # Check total is approximately 1.0 (with tolerance for floating-point precision)
        total = self.total_phase_fraction
        TOLERANCE = 0.001  # Allow 0.1% tolerance for floating-point errors
        if total is not None and abs(total - 1.0) > TOLERANCE:
            return False, f"Total phase fraction must equal 1.0 (got {total:.6f})"

        return True, "Valid"

    def has_tag(self, tag_name: str) -> bool:
        """Check if material has a specific tag."""
        return tag_name in self.tag_names

    def calculate_specific_gravity_from_gems(self, gems_parser) -> Optional[float]:
        """
        Calculate specific gravity from GEM phase composition using GEMS database.

        This method uses the molar mass and molar volume data from the GEMS database
        to calculate material density as a mass-weighted average of phase densities.

        Args:
            gems_parser: GEMSParserService instance

        Returns:
            Calculated specific gravity, or None if calculation fails

        Example:
            >>> from pathlib import Path
            >>> from app.services.gems_parser_service import GEMSParserService
            >>> parser = GEMSParserService(Path("src/data/gems"))
            >>> material.calculate_specific_gravity_from_gems(parser)
            3.12  # Calculated specific gravity for cement

        Note:
            This is an automatic calculation based on phase composition.
            User can override by setting specific_gravity manually.
        """
        if not self.phases:
            return None

        # Build phase mass fractions dictionary
        phase_mass_fractions = {
            phase.gem_phase_name: phase.mass_fraction
            for phase in self.phases
            if phase.mass_fraction is not None
        }

        return gems_parser.calculate_material_specific_gravity(phase_mass_fractions)

    def to_dict_extended(self) -> dict:
        """Convert to dictionary with relationships."""
        result = self.to_dict()
        result['tags'] = self.tag_names
        result['phases'] = [
            {
                'gem_phase_name': p.gem_phase_name,
                'mass_fraction': p.mass_fraction,
                'volume_fraction': p.volume_fraction,
                'surface_fraction': p.surface_fraction
            }
            for p in self.phases
        ]
        result['psd_summary'] = self.psd_data.get_distribution_summary() if self.psd_data else None
        return result


class Tag(Base):
    """
    Tag model for material classification.

    Tags are user-defined and searchable.
    Examples: "cement", "type-i", "portland", "limestone", "fly_ash", "class-f"
    """

    __tablename__ = 'tag'

    # Override BaseModel's id column - Tag uses name as primary key
    id = None

    # Tag name is the primary key (unique identifier)
    name = Column(String(64), primary_key=True)

    # Materials with this tag (many-to-many)
    materials = relationship(
        "Material",
        secondary=material_tags,
        back_populates="tags"
    )

    # Optional description for tag
    description = Column(Text, nullable=True, doc="Tag description")

    def __repr__(self) -> str:
        """String representation of the tag."""
        return f"<Tag(name='{self.name}')>"


class MaterialCreate(BaseModel):
    """Pydantic model for creating material instances."""

    name: str = Field(..., min_length=1, max_length=128, description="Material name (unique identifier)")
    tags: List[str] = Field(default_factory=list, description="Material tags for classification")

    # Physical properties
    specific_gravity: Optional[float] = Field(3.15, gt=0.0, le=5.0, description="Specific gravity")
    specific_surface_area: Optional[float] = Field(None, gt=0.0, description="Specific surface area (m²/kg)")

    # PSD data (will be handled via relationship) - REQUIRED
    psd_data_id: Optional[int] = Field(None, description="PSD data ID (will be created if PSD fields provided)")

    # PSD fields that can be provided during creation
    psd_mode: Optional[str] = Field(None, description="PSD mode (rosin_rammler, log_normal, fuller, custom)")
    psd_d50: Optional[float] = Field(None, ge=0.0, le=1000.0, description="D50 particle size (μm)")
    psd_n: Optional[float] = Field(None, ge=0.0, le=10.0, description="Distribution parameter")
    psd_dmax: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Maximum particle size (μm)")
    psd_median: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Median particle size (μm)")
    psd_spread: Optional[float] = Field(None, ge=0.0, le=10.0, description="Distribution spread parameter")
    psd_exponent: Optional[float] = Field(None, ge=0.0, le=2.0, description="Exponent parameter")
    psd_custom_points: Optional[str] = Field(None, description="Custom PSD points as JSON")

    # Metadata
    description: Optional[str] = Field(None, description="Material description")
    source: Optional[str] = Field(None, max_length=255, description="Material source")
    notes: Optional[str] = Field(None, description="Additional notes")
    immutable: Optional[bool] = Field(False, description="Whether this material is read-only")

    # Clinker flags
    is_clinker: Optional[bool] = Field(False, description="Whether this material is a clinker")
    has_clinker: Optional[bool] = Field(False, description="Whether this material contains clinker phases")
    clinker_source_id: Optional[int] = Field(None, description="ID of the clinker material this was derived from")

    # Particle shape settings
    particle_shape_type: Optional[int] = Field(0, ge=0, le=1, description="Particle shape type: 0=spheres, 1=real shapes")
    particle_shape_set: Optional[str] = Field(None, max_length=128, description="Name of particle shape set for real shapes")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate material name."""
        if not v or not v.strip():
            raise ValueError('Material name cannot be empty')
        return v.strip()

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags."""
        if v is None:
            return []
        # Strip whitespace and convert to lowercase
        return [tag.strip().lower() for tag in v if tag and tag.strip()]


class MaterialUpdate(BaseModel):
    """Pydantic model for updating material instances."""

    name: Optional[str] = Field(None, min_length=1, max_length=128, description="Material name")
    tags: Optional[List[str]] = Field(None, description="Material tags")

    # Physical properties
    specific_gravity: Optional[float] = Field(None, gt=0.0, le=5.0, description="Specific gravity")
    specific_surface_area: Optional[float] = Field(None, gt=0.0, description="Specific surface area (m²/kg)")

    # PSD data (optional for updates - material always has PSD in database)
    psd_data_id: Optional[int] = Field(None, description="PSD data ID")

    # PSD fields that can be updated
    psd_mode: Optional[str] = Field(None, description="PSD mode")
    psd_d50: Optional[float] = Field(None, ge=0.0, le=1000.0, description="D50 particle size (μm)")
    psd_n: Optional[float] = Field(None, ge=0.0, le=10.0, description="Distribution parameter")
    psd_dmax: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Maximum particle size (μm)")
    psd_median: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Median particle size (μm)")
    psd_spread: Optional[float] = Field(None, ge=0.0, le=10.0, description="Distribution spread parameter")
    psd_exponent: Optional[float] = Field(None, ge=0.0, le=2.0, description="Exponent parameter")
    psd_custom_points: Optional[str] = Field(None, description="Custom PSD points as JSON")

    # Metadata
    description: Optional[str] = Field(None, description="Material description")
    source: Optional[str] = Field(None, max_length=255, description="Material source")
    notes: Optional[str] = Field(None, description="Additional notes")
    immutable: Optional[bool] = Field(None, description="Whether this material is read-only")

    # Clinker flags
    is_clinker: Optional[bool] = Field(None, description="Whether this material is a clinker")
    has_clinker: Optional[bool] = Field(None, description="Whether this material contains clinker phases")
    clinker_source_id: Optional[int] = Field(None, description="ID of the clinker material this was derived from")

    # Particle shape settings
    particle_shape_type: Optional[int] = Field(None, ge=0, le=1, description="Particle shape type: 0=spheres, 1=real shapes")
    particle_shape_set: Optional[str] = Field(None, max_length=128, description="Name of particle shape set for real shapes")


class MaterialResponse(BaseModel):
    """Pydantic model for material API responses."""

    id: int
    name: str
    tags: List[str]

    # Physical properties
    specific_gravity: Optional[float]
    specific_surface_area: Optional[float]

    # PSD data (always present - required by database schema)
    psd_data_id: int

    # Metadata
    description: Optional[str]
    source: Optional[str]
    notes: Optional[str]
    immutable: bool

    # Clinker and composite flags
    is_clinker: bool
    has_clinker: bool
    is_composite: bool

    # Particle shape settings
    particle_shape_type: int
    particle_shape_set: Optional[str]

    # Calculated properties
    has_phase_data: bool
    total_phase_fraction: Optional[float]
    density: Optional[float]
    gem_phase_names: List[str]

    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

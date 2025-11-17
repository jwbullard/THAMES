#!/usr/bin/env python3
"""
MaterialPhase Model for THAMES

Represents the phase composition of a material.
Links Material to GEM phase names with mass/volume/surface fractions.
"""

from typing import Optional
from sqlalchemy import Column, String, Float, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, field_validator

from app.database.base import Base


class MaterialPhase(Base):
    """
    MaterialPhase model representing phase composition.

    Links a Material to a GEM phase name with fractions.
    Validates phase names against GEMS database.
    """

    __tablename__ = 'material_phase'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Material
    material_id = Column(Integer, ForeignKey('material.id'), nullable=False)
    material = relationship('Material', back_populates='phases')

    # GEM phase name (from GEMS database)
    # Examples: "Alite", "Belite", "Aluminate", "Gypsum", "Calcite", etc.
    gem_phase_name = Column(String(64), nullable=False,
                           doc="GEM phase name from GEMS database")

    # Mass fraction (required)
    mass_fraction = Column(Float, nullable=False,
                          doc="Mass fraction of this phase in the material (0.0-1.0)")

    # Volume fraction (optional - can be calculated from mass fraction and densities)
    volume_fraction = Column(Float, nullable=True,
                            doc="Volume fraction of this phase (0.0-1.0)")

    # Surface fraction (optional - can be calculated from mass fraction and SSA)
    surface_fraction = Column(Float, nullable=True,
                             doc="Surface area fraction of this phase (0.0-1.0)")

    # Ensure each material-phase combination is unique
    __table_args__ = (
        UniqueConstraint('material_id', 'gem_phase_name', name='uq_material_phase'),
    )

    def __repr__(self) -> str:
        """String representation of the material phase."""
        return f"<MaterialPhase(material_id={self.material_id}, phase='{self.gem_phase_name}', mass_fraction={self.mass_fraction})>"

    def validate_fractions(self) -> tuple[bool, str]:
        """
        Validate that fractions are in valid range.

        Returns:
            (is_valid, message)
        """
        if self.mass_fraction < 0 or self.mass_fraction > 1:
            return False, f"Mass fraction must be between 0 and 1, got {self.mass_fraction}"

        if self.volume_fraction is not None and (self.volume_fraction < 0 or self.volume_fraction > 1):
            return False, f"Volume fraction must be between 0 and 1, got {self.volume_fraction}"

        if self.surface_fraction is not None and (self.surface_fraction < 0 or self.surface_fraction > 1):
            return False, f"Surface fraction must be between 0 and 1, got {self.surface_fraction}"

        return True, "Valid"


class MaterialPhaseCreate(BaseModel):
    """Pydantic model for creating material phase instances."""

    material_id: int = Field(..., gt=0, description="Material ID")
    gem_phase_name: str = Field(..., min_length=1, max_length=64, description="GEM phase name")
    mass_fraction: float = Field(..., ge=0.0, le=1.0, description="Mass fraction")
    volume_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Volume fraction")
    surface_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Surface fraction")

    @field_validator('gem_phase_name')
    @classmethod
    def validate_gem_phase_name(cls, v):
        """Validate GEM phase name."""
        if not v or not v.strip():
            raise ValueError('GEM phase name cannot be empty')
        return v.strip()


class MaterialPhaseUpdate(BaseModel):
    """Pydantic model for updating material phase instances."""

    gem_phase_name: Optional[str] = Field(None, min_length=1, max_length=64, description="GEM phase name")
    mass_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Mass fraction")
    volume_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Volume fraction")
    surface_fraction: Optional[float] = Field(None, ge=0.0, le=1.0, description="Surface fraction")


class MaterialPhaseResponse(BaseModel):
    """Pydantic model for material phase API responses."""

    id: int
    material_id: int
    gem_phase_name: str
    mass_fraction: float
    volume_fraction: Optional[float]
    surface_fraction: Optional[float]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

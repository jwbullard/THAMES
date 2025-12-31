#!/usr/bin/env python3
"""
Material Component Model for THAMES

Tracks constituent materials in composite materials.
For example, a cement is composed of:
- Clinker material (e.g., 97%)
- Gypsum material (e.g., 3%)

This allows materials to be combined to create new composite materials
while preserving the link to the original component materials.
"""

from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class MaterialComponent(Base):
    """
    Association table for composite materials.

    Links a parent (composite) material to its component materials
    with their mass fractions.
    """

    __tablename__ = 'material_component'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Parent material (the composite being created)
    parent_material_id = Column(Integer, ForeignKey('material.id'), nullable=False)

    # Component material (one of the ingredients)
    component_material_id = Column(Integer, ForeignKey('material.id'), nullable=False)

    # Mass fraction of this component in the parent (0.0-1.0)
    mass_fraction = Column(Float, nullable=False,
                           doc="Mass fraction of this component in the composite")

    # Relationships
    parent_material = relationship(
        'Material',
        foreign_keys=[parent_material_id],
        back_populates='components'
    )

    component_material = relationship(
        'Material',
        foreign_keys=[component_material_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return (f"<MaterialComponent(parent={self.parent_material_id}, "
                f"component={self.component_material_id}, "
                f"fraction={self.mass_fraction})>")

    @property
    def component_name(self) -> str:
        """Get the name of the component material."""
        if self.component_material:
            return self.component_material.name
        return f"Material ID {self.component_material_id}"

    @property
    def parent_name(self) -> str:
        """Get the name of the parent material."""
        if self.parent_material:
            return self.parent_material.name
        return f"Material ID {self.parent_material_id}"

    def validate(self) -> tuple[bool, str]:
        """
        Validate the component entry.

        Returns:
            (is_valid, message)
        """
        if self.mass_fraction is None:
            return False, "Mass fraction is required"

        if self.mass_fraction < 0.0 or self.mass_fraction > 1.0:
            return False, f"Mass fraction must be between 0 and 1, got {self.mass_fraction}"

        if self.parent_material_id == self.component_material_id:
            return False, "Component cannot be the same as parent"

        return True, "Valid"

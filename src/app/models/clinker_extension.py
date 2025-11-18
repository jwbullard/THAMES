#!/usr/bin/env python3
"""
Clinker Extension Model for THAMES

Stores clinker-specific data that only applies to clinker materials:
- Surface area fractions for the 6 clinker phases
- Two-point correlation functions (binary BLOBs)

This data is separate from the main Material model because only
clinker materials have this information.
"""

from sqlalchemy import Column, Integer, Float, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class ClinkerExtension(Base):
    """
    Extension table for clinker-specific data.

    Linked one-to-one with Material where is_clinker=True.
    Contains surface area fractions and correlation functions
    needed for microstructure generation.
    """

    __tablename__ = 'clinker_extension'

    # Override BaseModel's id column - ClinkerExtension uses material_id as primary key
    id = None

    # Primary key is also foreign key to material
    material_id = Column(Integer, ForeignKey('material.id'), primary_key=True)

    # Surface area fractions for the 6 clinker phases (must sum to 1.0)
    # These are separate from mass/volume fractions
    c3s_surface_fraction = Column(Float, nullable=True, default=0.0,
                                  doc="Alite (C3S) surface area fraction")
    c2s_surface_fraction = Column(Float, nullable=True, default=0.0,
                                  doc="Belite (C2S) surface area fraction")
    c3a_surface_fraction = Column(Float, nullable=True, default=0.0,
                                  doc="Aluminate (C3A) surface area fraction")
    c4af_surface_fraction = Column(Float, nullable=True, default=0.0,
                                   doc="Ferrite (C4AF) surface area fraction")
    k2so4_surface_fraction = Column(Float, nullable=True, default=0.0,
                                    doc="Arcanite (K2SO4) surface area fraction")
    na2so4_surface_fraction = Column(Float, nullable=True, default=0.0,
                                     doc="Thenardite (Na2SO4) surface area fraction")

    # Two-point correlation functions (binary BLOBs)
    # These are used by the THAMES-Hydration simulator for kinetic calculations
    # 7 correlation files: .sil, .c3s, .alu, .c3a, .c4af, .k2o, .n2o
    correlation_sil = Column(LargeBinary, nullable=True,
                             doc="Silicate correlation function (.sil)")
    correlation_c3s = Column(LargeBinary, nullable=True,
                             doc="C3S correlation function (.c3s)")
    correlation_alu = Column(LargeBinary, nullable=True,
                             doc="Aluminate correlation function (.alu)")
    correlation_c3a = Column(LargeBinary, nullable=True,
                             doc="C3A correlation function (.c3a)")
    correlation_c4af = Column(LargeBinary, nullable=True,
                              doc="C4AF correlation function (.c4af)")
    correlation_k2o = Column(LargeBinary, nullable=True,
                             doc="K2O correlation function (.k2o)")
    correlation_n2o = Column(LargeBinary, nullable=True,
                             doc="N2O correlation function (.n2o)")

    # Relationship back to Material
    material = relationship('Material', back_populates='clinker_data')

    def __repr__(self) -> str:
        """String representation."""
        return f"<ClinkerExtension(material_id={self.material_id})>"

    @property
    def total_surface_fraction(self) -> float:
        """Calculate total surface area fraction (should sum to 1.0)."""
        fractions = [
            self.c3s_surface_fraction or 0.0,
            self.c2s_surface_fraction or 0.0,
            self.c3a_surface_fraction or 0.0,
            self.c4af_surface_fraction or 0.0,
            self.k2so4_surface_fraction or 0.0,
            self.na2so4_surface_fraction or 0.0
        ]
        return sum(fractions)

    @property
    def has_correlation_data(self) -> bool:
        """Check if any correlation data is present."""
        return any([
            self.correlation_sil,
            self.correlation_c3s,
            self.correlation_alu,
            self.correlation_c3a,
            self.correlation_c4af,
            self.correlation_k2o,
            self.correlation_n2o
        ])

    @property
    def correlation_file_count(self) -> int:
        """Count how many correlation files are present."""
        count = 0
        if self.correlation_sil:
            count += 1
        if self.correlation_c3s:
            count += 1
        if self.correlation_alu:
            count += 1
        if self.correlation_c3a:
            count += 1
        if self.correlation_c4af:
            count += 1
        if self.correlation_k2o:
            count += 1
        if self.correlation_n2o:
            count += 1
        return count

    def get_surface_fractions_dict(self) -> dict:
        """Get surface fractions as a dictionary."""
        return {
            'c3s': self.c3s_surface_fraction or 0.0,
            'c2s': self.c2s_surface_fraction or 0.0,
            'c3a': self.c3a_surface_fraction or 0.0,
            'c4af': self.c4af_surface_fraction or 0.0,
            'k2so4': self.k2so4_surface_fraction or 0.0,
            'na2so4': self.na2so4_surface_fraction or 0.0
        }

    def set_surface_fractions(self, fractions: dict) -> None:
        """
        Set surface fractions from a dictionary.

        Args:
            fractions: Dict with keys 'c3s', 'c2s', 'c3a', 'c4af', 'k2so4', 'na2so4'
        """
        if 'c3s' in fractions:
            self.c3s_surface_fraction = fractions['c3s']
        if 'c2s' in fractions:
            self.c2s_surface_fraction = fractions['c2s']
        if 'c3a' in fractions:
            self.c3a_surface_fraction = fractions['c3a']
        if 'c4af' in fractions:
            self.c4af_surface_fraction = fractions['c4af']
        if 'k2so4' in fractions:
            self.k2so4_surface_fraction = fractions['k2so4']
        if 'na2so4' in fractions:
            self.na2so4_surface_fraction = fractions['na2so4']

    def validate_surface_fractions(self) -> tuple[bool, str]:
        """
        Validate that surface fractions sum to 1.0.

        Returns:
            (is_valid, message)
        """
        total = self.total_surface_fraction
        if abs(total - 1.0) > 0.01:
            return False, f"Surface fractions sum to {total:.4f}, should be 1.0"
        return True, "Valid"

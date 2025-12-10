"""
Service for providing default elastic moduli for THAMES phases.

Default values are from:
    Haecker et al., Cement and Concrete Research 35(2005)1948-1960, Table 1

Phase categories are used for fallback values when specific phase data is unavailable:
    - Clinker phases (Alite, Belite, etc.): High stiffness crystalline materials
    - Hydration products (C-S-H, AFt, etc.): Lower stiffness hydrated phases
    - Sulfates (Gypsum, Anhydrite, etc.): Intermediate stiffness
    - Carbonates (Calcite, Dolomite): Moderate-high stiffness
    - Pozzolans (SilicaAm, Quartz, etc.): Variable stiffness
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class ElasticModuli:
    """Elastic moduli for a phase."""
    bulk_modulus_GPa: float  # K - Bulk modulus in GPa
    shear_modulus_GPa: float  # G - Shear modulus in GPa
    source: str = "Haecker2005"  # Data source reference

    @property
    def youngs_modulus_GPa(self) -> float:
        """Calculate Young's modulus E from K and G."""
        # E = 9KG / (3K + G)
        if self.bulk_modulus_GPa == 0 and self.shear_modulus_GPa == 0:
            return 0.0
        denom = 3 * self.bulk_modulus_GPa + self.shear_modulus_GPa
        if denom == 0:
            return 0.0
        return 9 * self.bulk_modulus_GPa * self.shear_modulus_GPa / denom

    @property
    def poissons_ratio(self) -> float:
        """Calculate Poisson's ratio nu from K and G."""
        # nu = (3K - 2G) / (2(3K + G))
        if self.bulk_modulus_GPa == 0 and self.shear_modulus_GPa == 0:
            return 0.0
        denom = 2 * (3 * self.bulk_modulus_GPa + self.shear_modulus_GPa)
        if denom == 0:
            return 0.5  # Incompressible limit
        return (3 * self.bulk_modulus_GPa - 2 * self.shear_modulus_GPa) / denom

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "bulk_modulus_GPa": self.bulk_modulus_GPa,
            "shear_modulus_GPa": self.shear_modulus_GPa,
            "youngs_modulus_GPa": round(self.youngs_modulus_GPa, 2),
            "poissons_ratio": round(self.poissons_ratio, 3),
            "source": self.source
        }


class ElasticDefaultsService:
    """
    Service providing default elastic moduli for THAMES phases.

    Values are from Haecker et al., Cement and Concrete Research 35(2005)1948-1960.
    """

    # Default moduli from Haecker et al. (2005) Table 1
    # Format: phase_name -> (K, G) in GPa
    HAECKER_DEFAULTS: Dict[str, Tuple[float, float]] = {
        # Special phases
        "Void": (0.0, 0.0),
        "VOID": (0.0, 0.0),
        "Electrolyte": (2.2, 0.0),  # Bulk modulus of water, no shear

        # Clinker phases (all use Alite values from Haecker)
        "Alite": (105.2, 44.8),
        "Belite": (105.2, 44.8),
        "Aluminate": (105.2, 44.8),
        "Ferrite": (105.2, 44.8),
        "CaO": (105.2, 44.8),  # Free lime - same as clinker
        "Periclase": (105.2, 44.8),  # MgO - same as clinker

        # Sulfate phases
        "Gypsum": (42.5, 15.7),
        "Bassanite": (52.4, 24.2),
        "Anhydrite": (54.9, 29.3),
        "Arcanite": (31.9, 17.4),  # K2SO4
        "Thenardite": (43.4, 22.3),  # Na2SO4

        # Carbonate phases
        "Calcite": (69.8, 30.4),

        # Pozzolanic / SCM phases
        "SilicaAm": (36.5, 31.2),  # Amorphous silica / silica fume

        # Hydration products - C-S-H type (lower stiffness)
        "CSHQ": (14.9, 9.0),
        "Hydrogarnet": (14.9, 9.0),  # C3AH6
        "AFt": (14.9, 9.0),  # Ettringite
        "FH3": (14.9, 9.0),  # Iron hydroxide
        "Hydrocalumite": (14.9, 9.0),  # Friedel's salt
        "Stratlingite": (14.9, 9.0),  # C2ASH8
        "Hydrotalcite": (14.9, 9.0),
        "Damage": (14.9, 9.0),  # Damaged material - use C-S-H values

        # Hydration products - Portlandite type (higher stiffness)
        "Portlandite": (40.0, 16.0),  # CH
        "AFm": (40.0, 16.0),  # Monosulfate
        "AFmc": (40.0, 16.0),  # Monocarbonate
        "Brucite": (40.0, 16.0),  # Mg(OH)2
        "CaCl2": (40.0, 16.0),
    }

    # Category-based fallback values for phases not in HAECKER_DEFAULTS
    # These are approximate values based on material type
    CATEGORY_DEFAULTS: Dict[str, Tuple[float, float, str]] = {
        # (K, G, description)
        "clinker": (105.2, 44.8, "Clinker minerals - stiff crystalline"),
        "hydrate_csh": (14.9, 9.0, "C-S-H type hydrates - lower stiffness"),
        "hydrate_ch": (40.0, 16.0, "CH type hydrates - moderate stiffness"),
        "sulfate": (45.0, 20.0, "Sulfate minerals - intermediate"),
        "carbonate": (70.0, 30.0, "Carbonate minerals - moderate-high"),
        "pozzolan": (36.0, 30.0, "Pozzolanic materials - variable"),
        "oxide": (100.0, 40.0, "Oxide minerals - stiff"),
        "unknown": (20.0, 10.0, "Unknown phase - conservative estimate"),
    }

    # Map phase names to categories for fallback
    PHASE_CATEGORIES: Dict[str, str] = {
        # Additional clinker-like phases
        "lime": "clinker",

        # Carbonates
        "Dolomite-ord": "carbonate",
        "Dolomite-dis": "carbonate",
        "Magneite": "carbonate",
        "Aragonite": "carbonate",
        "Vaterite": "carbonate",

        # Sulfates (additional)
        "Syngenite": "sulfate",
        "Mirabilite": "sulfate",
        "Aphthitalite": "sulfate",

        # Pozzolans and SCMs
        "Quartz": "pozzolan",
        "Mullite": "pozzolan",
        "Cristobalite": "pozzolan",
        "Tridymite": "pozzolan",
        "C2AS(am)": "pozzolan",
        "CA2S(am)": "pozzolan",
        "K6A2S(am)": "pozzolan",

        # Iron phases
        "Hematite": "oxide",
        "Magnetite": "oxide",
        "Goethite": "oxide",
        "Pyrite": "oxide",
        "Pyrrhotite": "oxide",
        "Troilite": "oxide",
        "Wite": "oxide",  # Wustite

        # Silicates
        "Diopside": "pozzolan",
        "Forsterite": "pozzolan",
        "Merwinite": "pozzolan",
        "Akermanite": "pozzolan",
        "Gehlenite": "pozzolan",

        # Zeolites and other hydrates
        "Zeolite": "hydrate_csh",
        "Sodalite": "hydrate_csh",
        "Cancrinite": "hydrate_csh",
        "Katoite": "hydrate_csh",
        "cHite": "hydrate_csh",
        "hcite": "hydrate_csh",
        "Jennite": "hydrate_csh",
        "Tobermorite-I": "hydrate_csh",
        "Tobermorite-II": "hydrate_csh",
        "Tobermorite": "hydrate_csh",

        # Aluminates
        "C3AH6": "hydrate_csh",
        "C4AH13": "hydrate_ch",
        "C2AH8": "hydrate_ch",
        "CAH10": "hydrate_csh",
        "C4AcH11": "hydrate_ch",  # Monocarbonate
        "C4AsH12": "hydrate_ch",  # Monosulfate
        "C6As3H32": "hydrate_csh",  # Ettringite
        "Thaumasite": "hydrate_csh",

        # Other phases
        "Aggregate": "carbonate",  # Typically limestone or siliceous
        "AGGREGATE": "carbonate",
    }

    def __init__(self):
        """Initialize the elastic defaults service."""
        self._cache: Dict[str, ElasticModuli] = {}

    def get_elastic_moduli(self, phase_name: str) -> ElasticModuli:
        """
        Get elastic moduli for a phase.

        Args:
            phase_name: Name of the phase (GEMS phase name)

        Returns:
            ElasticModuli dataclass with K, G values
        """
        # Check cache first
        if phase_name in self._cache:
            return self._cache[phase_name]

        # Check Haecker defaults
        if phase_name in self.HAECKER_DEFAULTS:
            K, G = self.HAECKER_DEFAULTS[phase_name]
            moduli = ElasticModuli(
                bulk_modulus_GPa=K,
                shear_modulus_GPa=G,
                source="Haecker2005"
            )
            self._cache[phase_name] = moduli
            return moduli

        # Check for category-based fallback
        category = self.PHASE_CATEGORIES.get(phase_name, "unknown")
        K, G, desc = self.CATEGORY_DEFAULTS[category]

        logger.debug(f"Using {category} defaults for phase '{phase_name}': K={K}, G={G}")

        moduli = ElasticModuli(
            bulk_modulus_GPa=K,
            shear_modulus_GPa=G,
            source=f"category:{category}"
        )
        self._cache[phase_name] = moduli
        return moduli

    def get_elastic_moduli_dict(self, phase_name: str) -> Dict:
        """
        Get elastic moduli as a dictionary suitable for JSON.

        Args:
            phase_name: Name of the phase

        Returns:
            Dictionary with bulk_modulus_GPa, shear_modulus_GPa, etc.
        """
        return self.get_elastic_moduli(phase_name).to_dict()

    def get_all_defaults(self) -> Dict[str, Dict]:
        """
        Get all default elastic moduli as a dictionary.

        Returns:
            Dictionary mapping phase names to moduli dictionaries
        """
        result = {}
        for phase_name in self.HAECKER_DEFAULTS:
            result[phase_name] = self.get_elastic_moduli_dict(phase_name)
        return result

    def has_explicit_default(self, phase_name: str) -> bool:
        """
        Check if a phase has an explicit default value (not category fallback).

        Args:
            phase_name: Name of the phase

        Returns:
            True if phase has explicit Haecker default
        """
        return phase_name in self.HAECKER_DEFAULTS

    def get_category_for_phase(self, phase_name: str) -> str:
        """
        Get the category for a phase (used for fallback selection).

        Args:
            phase_name: Name of the phase

        Returns:
            Category string
        """
        if phase_name in self.HAECKER_DEFAULTS:
            return "explicit"
        return self.PHASE_CATEGORIES.get(phase_name, "unknown")


# Singleton instance
_elastic_defaults_service: Optional[ElasticDefaultsService] = None


def get_elastic_defaults_service() -> ElasticDefaultsService:
    """Get the singleton elastic defaults service instance."""
    global _elastic_defaults_service
    if _elastic_defaults_service is None:
        _elastic_defaults_service = ElasticDefaultsService()
    return _elastic_defaults_service

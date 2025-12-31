#!/usr/bin/env python3
"""
Hydration Products Service for THAMES

Provides data and defaults for hydration products that can form during
cement hydration simulations. Users select which products to include
in their simulation, with sensible defaults suggested.

Key features:
- Suggested product sets for common cement types
- Default interface affinity data (contact angles)
- C-S-H special parameters (poresize distribution, Rd values)
- All defaults can be overridden by the user
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger('THAMES.HydrationProductsService')


# =============================================================================
# C-S-H Poresize Distribution (from reference simparams)
# =============================================================================
# This is the default poresize distribution for CSHQ
# Based on experimental data and modeling

CSHQ_PORESIZE_DISTRIBUTION: List[Dict[str, float]] = [
    {"diameter": 0.23228, "volumefraction": 0.01684781722375019},
    {"diameter": 0.49089, "volumefraction": 0.02276126023357459},
    {"diameter": 0.72108, "volumefraction": 0.029511617160234132},
    {"diameter": 0.98879, "volumefraction": 0.03330516053249656},
    {"diameter": 1.24669, "volumefraction": 0.03581553408506234},
    {"diameter": 1.49484, "volumefraction": 0.03721026788047437},
    {"diameter": 1.72364, "volumefraction": 0.03726604986833206},
    {"diameter": 1.99014, "volumefraction": 0.03525771420648546},
    {"diameter": 2.23709, "volumefraction": 0.03085056896778847},
    {"diameter": 2.48431, "volumefraction": 0.02778219143767598},
    {"diameter": 2.75073, "volumefraction": 0.025383381860825577},
    {"diameter": 2.98861, "volumefraction": 0.023263482223263608},
    {"diameter": 3.23612, "volumefraction": 0.021589838488563145},
    {"diameter": 3.49314, "volumefraction": 0.019804630778147304},
    {"diameter": 3.74069, "volumefraction": 0.018354114994877588},
    {"diameter": 3.98824, "volumefraction": 0.01684781722375019},
    {"diameter": 4.23585, "volumefraction": 0.015676395478738746},
    {"diameter": 4.48344, "volumefraction": 0.014393225659042096},
    {"diameter": 4.72156, "volumefraction": 0.013444747766491573},
    {"diameter": 4.9883, "volumefraction": 0.012552235960768569},
    {"diameter": 5.24554, "volumefraction": 0.011826886019648796},
    {"diameter": 5.49324, "volumefraction": 0.011101720177498855},
    {"diameter": 5.74097, "volumefraction": 0.010488118311064288},
    {"diameter": 5.9887, "volumefraction": 0.009874332345659894},
    {"diameter": 6.23646, "volumefraction": 0.00942807644279839},
    {"diameter": 6.48417, "volumefraction": 0.008702910600648449},
    {"diameter": 6.74146, "volumefraction": 0.008256470598817118},
    {"diameter": 6.99872, "volumefraction": 0.007642868732382551},
    {"diameter": 7.23693, "volumefraction": 0.007085048853805671},
    {"diameter": 7.49421, "volumefraction": 0.006583010963086481},
    {"diameter": 7.73244, "volumefraction": 0.00613657096125515},
    {"diameter": 7.98975, "volumefraction": 0.005746097046251335},
    {"diameter": 8.23755, "volumefraction": 0.005467187106962896},
    {"diameter": 8.49487, "volumefraction": 0.005132495179816769},
    {"diameter": 8.74268, "volumefraction": 0.004909367228386016},
    {"diameter": 12.0, "volumefraction": 0.0015534255057322317},
    {"diameter": 15.0, "volumefraction": 0.00272492417632637},
    {"diameter": 17.0, "volumefraction": 0.0033001847202133072},
    {"diameter": 20.0, "volumefraction": 0.004337822158874359},
    {"diameter": 23.0, "volumefraction": 0.005273625367665351},
    {"diameter": 26.0, "volumefraction": 0.006142693285742837},
    {"diameter": 29.0, "volumefraction": 0.007043723319901984},
    {"diameter": 32.0, "volumefraction": 0.008080913465303721},
    {"diameter": 35.0, "volumefraction": 0.00897834375043533},
    {"diameter": 38.0, "volumefraction": 0.009721701016706174},
    {"diameter": 41.0, "volumefraction": 0.01077285587748314},
    {"diameter": 44.0, "volumefraction": 0.011589497649770731},
    {"diameter": 47.0, "volumefraction": 0.01262257207894466},
    {"diameter": 50.0, "volumefraction": 0.013466392608488387},
    {"diameter": 52.0, "volumefraction": 0.013268521061538297},
    {"diameter": 55.0, "volumefraction": 0.013807734626341025},
    {"diameter": 58.0, "volumefraction": 0.014538359814615225},
    {"diameter": 61.0, "volumefraction": 0.014990723777949314},
    {"diameter": 64.0, "volumefraction": 0.01566147271843026},
    {"diameter": 67.0, "volumefraction": 0.016802876079524846},
    {"diameter": 70.0, "volumefraction": 0.017163156580334505},
    {"diameter": 73.0, "volumefraction": 0.017129420963162383},
    {"diameter": 76.0, "volumefraction": 0.01745964516260557},
    {"diameter": 79.0, "volumefraction": 0.01811002849163405},
    {"diameter": 82.0, "volumefraction": 0.01815315493167048},
    {"diameter": 85.0, "volumefraction": 0.0189718434975009},
    {"diameter": 87.0, "volumefraction": 0.01830075636877286},
    {"diameter": 90.0, "volumefraction": 0.017913476793453408},
    {"diameter": 93.0, "volumefraction": 0.018873239641531554},
    {"diameter": 96.0, "volumefraction": 0.017989599001311234},
    {"diameter": 99.0, "volumefraction": 0.0189581029096103},
]

# C-S-H Rd (distribution coefficient) values for alkali uptake
CSHQ_RD_VALUES: List[Dict[str, Any]] = [
    {"Rdelement": "K", "Rdvalue": 0.42},
    {"Rdelement": "Na", "Rdvalue": 0.42},
]


# =============================================================================
# Product Categories
# =============================================================================

class ProductCategory(Enum):
    """Categories of hydration products."""
    CALCIUM_SILICATE_HYDRATE = "C-S-H"
    CALCIUM_HYDROXIDE = "CH"
    AFT = "AFt (Ettringite family)"
    AFM = "AFm (Monosulfate family)"
    CARBONATE_AFM = "Carbonate AFm"
    ALUMINATE_HYDRATE = "Aluminate hydrates"
    FERRITE_HYDRATE = "Ferrite hydrates"
    HYDROTALCITE = "Hydrotalcite"
    ZEOLITE = "Zeolites"
    OTHER = "Other"


# =============================================================================
# Hydration Product Data
# =============================================================================

@dataclass
class HydrationProductData:
    """
    Data for a single hydration product.

    Attributes:
        gems_name: GEMS phase name (from PHNL)
        display_name: User-friendly display name
        category: Product category for grouping
        description: Brief description of the phase
        suggested_for: List of cement types where this product is commonly expected
        default_affinity: Default interface affinity entries (contact angles)
        poresize_distribution: Optional PSD for gel phases
        rd_values: Optional Rd values for alkali distribution
    """
    gems_name: str
    display_name: str
    category: ProductCategory
    description: str = ""
    suggested_for: List[str] = field(default_factory=list)
    default_affinity: List[Dict[str, Any]] = field(default_factory=list)
    poresize_distribution: Optional[List[Dict[str, float]]] = None
    rd_values: Optional[List[Dict[str, Any]]] = None


# =============================================================================
# Default Hydration Products Registry
# =============================================================================

# Products that are commonly formed and should be suggested for typical simulations
SUGGESTED_PRODUCTS: Dict[str, HydrationProductData] = {
    # ----- C-S-H -----
    "CSHQ": HydrationProductData(
        gems_name="CSHQ",
        display_name="C-S-H (CSHQ model)",
        category=ProductCategory.CALCIUM_SILICATE_HYDRATE,
        description="Calcium silicate hydrate - main binding phase in portland cement",
        suggested_for=["portland", "blended", "pozzolanic"],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 30},
            {"affinityphase": "Belite", "contactanglevalue": 30},
            {"affinityphase": "Portlandite", "contactanglevalue": 0},
        ],
        poresize_distribution=CSHQ_PORESIZE_DISTRIBUTION,
        rd_values=CSHQ_RD_VALUES,
    ),

    # ----- Portlandite -----
    "Portlandite": HydrationProductData(
        gems_name="Portlandite",
        display_name="Portlandite (CH)",
        category=ProductCategory.CALCIUM_HYDROXIDE,
        description="Calcium hydroxide - forms from silicate hydration",
        suggested_for=["portland", "blended"],
        default_affinity=[
            {"affinityphase": "CSHQ", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    # ----- AFt phases (Ettringite family) -----
    "ettr": HydrationProductData(
        gems_name="ettr",
        display_name="Ettringite",
        category=ProductCategory.AFT,
        description="Primary AFt phase - forms from aluminate + sulfate reaction",
        suggested_for=["portland", "blended"],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "C4AsH105", "contactanglevalue": 0},
            {"affinityphase": "C4AsH12", "contactanglevalue": 0},
            {"affinityphase": "C4AsH14", "contactanglevalue": 0},
            {"affinityphase": "C4AsH16", "contactanglevalue": 0},
            {"affinityphase": "C4AsH9", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "ettr-AlFe": HydrationProductData(
        gems_name="ettr-AlFe",
        display_name="Ettringite (Al-Fe solid solution)",
        category=ProductCategory.AFT,
        description="Al-Fe ettringite solid solution",
        suggested_for=["portland"],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "C4AsH105", "contactanglevalue": 0},
            {"affinityphase": "C4AsH12", "contactanglevalue": 0},
            {"affinityphase": "C4AsH14", "contactanglevalue": 0},
            {"affinityphase": "C4AsH16", "contactanglevalue": 0},
            {"affinityphase": "C4AsH9", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # ----- AFm phases (Monosulfate family) -----
    "monosulf-AlFe": HydrationProductData(
        gems_name="monosulf-AlFe",
        display_name="Monosulfate (Al-Fe)",
        category=ProductCategory.AFM,
        description="AFm monosulfate solid solution - forms after sulfate depletion",
        suggested_for=["portland", "blended"],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    "C4AsH12": HydrationProductData(
        gems_name="C4AsH12",
        display_name="Monosulfate-12",
        category=ProductCategory.AFM,
        description="Monosulfate with 12 water molecules",
        suggested_for=["portland"],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    "C4AsH14": HydrationProductData(
        gems_name="C4AsH14",
        display_name="Monosulfate-14",
        category=ProductCategory.AFM,
        description="Monosulfate with 14 water molecules",
        suggested_for=["portland"],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    # ----- Carbonate AFm -----
    "C4AcH11": HydrationProductData(
        gems_name="C4AcH11",
        display_name="Monocarboaluminate",
        category=ProductCategory.CARBONATE_AFM,
        description="Carbonate AFm - forms in limestone-blended cements",
        suggested_for=["limestone"],
        default_affinity=[
            {"affinityphase": "C3AH6", "contactanglevalue": 0},
            {"affinityphase": "C4AH11", "contactanglevalue": 0},
            {"affinityphase": "C4AH13", "contactanglevalue": 0},
            {"affinityphase": "C4AH19", "contactanglevalue": 0},
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C4Ac0.5H12": HydrationProductData(
        gems_name="C4Ac0.5H12",
        display_name="Hemicarboaluminate",
        category=ProductCategory.CARBONATE_AFM,
        description="Hemicarboaluminate - intermediate carbonate AFm",
        suggested_for=["limestone"],
        default_affinity=[
            {"affinityphase": "C3AH6", "contactanglevalue": 0},
            {"affinityphase": "C4AH11", "contactanglevalue": 0},
            {"affinityphase": "C4AH13", "contactanglevalue": 0},
            {"affinityphase": "C4AH19", "contactanglevalue": 0},
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # ----- Aluminate hydrates -----
    "C3AH6": HydrationProductData(
        gems_name="C3AH6",
        display_name="Hydrogarnet (C3AH6)",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminate hydrate - stable at high temperature",
        suggested_for=["portland"],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C4AH13": HydrationProductData(
        gems_name="C4AH13",
        display_name="C4AH13",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminate hydrate",
        suggested_for=["portland"],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # ----- Hydrotalcite -----
    "Hydrotalc-pyr": HydrationProductData(
        gems_name="Hydrotalc-pyr",
        display_name="Hydrotalcite (pyroaurite-type)",
        category=ProductCategory.HYDROTALCITE,
        description="Mg-Fe layered double hydroxide - forms in slag-blended cements",
        suggested_for=["slag", "blended"],
        default_affinity=[],
    ),

    "hydrotalcite": HydrationProductData(
        gems_name="hydrotalcite",
        display_name="Hydrotalcite",
        category=ProductCategory.HYDROTALCITE,
        description="Mg-Al layered double hydroxide",
        suggested_for=["slag", "blended"],
        default_affinity=[],
    ),
}

# Additional products that can be included (less commonly needed)
ADDITIONAL_PRODUCTS: Dict[str, HydrationProductData] = {
    # More AFt phases
    "C6AsH13": HydrationProductData(
        gems_name="C6AsH13",
        display_name="Ettringite-13",
        category=ProductCategory.AFT,
        description="Ettringite with 13 water molecules",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "C4AsH105", "contactanglevalue": 0},
            {"affinityphase": "C4AsH12", "contactanglevalue": 0},
            {"affinityphase": "C4AsH14", "contactanglevalue": 0},
            {"affinityphase": "C4AsH16", "contactanglevalue": 0},
            {"affinityphase": "C4AsH9", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C6AsH9": HydrationProductData(
        gems_name="C6AsH9",
        display_name="Ettringite-9",
        category=ProductCategory.AFT,
        description="Ettringite with 9 water molecules (dehydrated)",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "C4AsH105", "contactanglevalue": 0},
            {"affinityphase": "C4AsH12", "contactanglevalue": 0},
            {"affinityphase": "C4AsH14", "contactanglevalue": 0},
            {"affinityphase": "C4AsH16", "contactanglevalue": 0},
            {"affinityphase": "C4AsH9", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "SO4_CO3_AFt": HydrationProductData(
        gems_name="SO4_CO3_AFt",
        display_name="Thaumasite precursor",
        category=ProductCategory.AFT,
        description="SO4-CO3 AFt solid solution",
        suggested_for=["limestone"],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "C4AsH105", "contactanglevalue": 0},
            {"affinityphase": "C4AsH12", "contactanglevalue": 0},
            {"affinityphase": "C4AsH14", "contactanglevalue": 0},
            {"affinityphase": "C4AsH16", "contactanglevalue": 0},
            {"affinityphase": "C4AsH9", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # More AFm phases
    "C4AsH105": HydrationProductData(
        gems_name="C4AsH105",
        display_name="Monosulfate-10.5",
        category=ProductCategory.AFM,
        description="Monosulfate with 10.5 water molecules",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    "C4AsH16": HydrationProductData(
        gems_name="C4AsH16",
        display_name="Monosulfate-16",
        category=ProductCategory.AFM,
        description="Monosulfate with 16 water molecules (high hydration)",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    "C4AsH9": HydrationProductData(
        gems_name="C4AsH9",
        display_name="Monosulfate-9",
        category=ProductCategory.AFM,
        description="Monosulfate with 9 water molecules (dehydrated)",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    ),

    # More carbonate AFm
    "C4Ac0.5H105": HydrationProductData(
        gems_name="C4Ac0.5H105",
        display_name="Hemicarboaluminate-10.5",
        category=ProductCategory.CARBONATE_AFM,
        description="Hemicarboaluminate with 10.5 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "C3AH6", "contactanglevalue": 0},
            {"affinityphase": "C4AH11", "contactanglevalue": 0},
            {"affinityphase": "C4AH13", "contactanglevalue": 0},
            {"affinityphase": "C4AH19", "contactanglevalue": 0},
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C4Ac0.5H9": HydrationProductData(
        gems_name="C4Ac0.5H9",
        display_name="Hemicarboaluminate-9",
        category=ProductCategory.CARBONATE_AFM,
        description="Hemicarboaluminate with 9 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "C3AH6", "contactanglevalue": 0},
            {"affinityphase": "C4AH11", "contactanglevalue": 0},
            {"affinityphase": "C4AH13", "contactanglevalue": 0},
            {"affinityphase": "C4AH19", "contactanglevalue": 0},
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C4AcH9": HydrationProductData(
        gems_name="C4AcH9",
        display_name="Monocarboaluminate-9",
        category=ProductCategory.CARBONATE_AFM,
        description="Monocarboaluminate with 9 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "C3AH6", "contactanglevalue": 0},
            {"affinityphase": "C4AH11", "contactanglevalue": 0},
            {"affinityphase": "C4AH13", "contactanglevalue": 0},
            {"affinityphase": "C4AH19", "contactanglevalue": 0},
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # More aluminate hydrates
    "C4AH11": HydrationProductData(
        gems_name="C4AH11",
        display_name="C4AH11",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminate hydrate with 11 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "C4AH19": HydrationProductData(
        gems_name="C4AH19",
        display_name="C4AH19",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminate hydrate with 19 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # Ferrite hydrates
    "C3FH6": HydrationProductData(
        gems_name="C3FH6",
        display_name="Iron hydrogarnet (C3FH6)",
        category=ProductCategory.FERRITE_HYDRATE,
        description="Calcium ferrite hydrate",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    "C4FH13": HydrationProductData(
        gems_name="C4FH13",
        display_name="C4FH13",
        category=ProductCategory.FERRITE_HYDRATE,
        description="Calcium ferrite hydrate with 13 water",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    # Zeolites
    "Chabazite": HydrationProductData(
        gems_name="Chabazite",
        display_name="Chabazite",
        category=ProductCategory.ZEOLITE,
        description="Zeolite mineral - can form in alkali-activated systems",
        suggested_for=[],
        default_affinity=[],
    ),

    "ZeoliteP": HydrationProductData(
        gems_name="ZeoliteP",
        display_name="Zeolite P",
        category=ProductCategory.ZEOLITE,
        description="Zeolite P - can form in alkali-activated systems",
        suggested_for=[],
        default_affinity=[],
    ),

    # C-(A)-S-H variants
    "C3(AF)S0.84H": HydrationProductData(
        gems_name="C3(AF)S0.84H",
        display_name="C-A-S-H (Al-substituted)",
        category=ProductCategory.CALCIUM_SILICATE_HYDRATE,
        description="Al-substituted C-S-H",
        suggested_for=["pozzolanic"],
        default_affinity=[
            {"affinityphase": "Alite", "contactanglevalue": 30},
            {"affinityphase": "Belite", "contactanglevalue": 30},
        ],
    ),

    # MSH
    "MSH": HydrationProductData(
        gems_name="MSH",
        display_name="M-S-H",
        category=ProductCategory.OTHER,
        description="Magnesium silicate hydrate - forms in Mg-rich systems",
        suggested_for=["slag"],
        default_affinity=[],
    ),

    # Brucite
    "Brucite": HydrationProductData(
        gems_name="Brucite",
        display_name="Brucite",
        category=ProductCategory.OTHER,
        description="Magnesium hydroxide - forms in Mg-rich systems",
        suggested_for=["slag"],
        default_affinity=[],
    ),

    # Calcite
    "Calcite": HydrationProductData(
        gems_name="Calcite",
        display_name="Calcite",
        category=ProductCategory.OTHER,
        description="Calcium carbonate - can precipitate from carbonation",
        suggested_for=["limestone"],
        default_affinity=[],
    ),

    # ----- Chloride AFm phases -----
    "Friedels": HydrationProductData(
        gems_name="Friedels",
        display_name="Friedel's salt",
        category=ProductCategory.AFM,
        description="Chloride AFm - forms in chloride-rich environments",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "Kuzels": HydrationProductData(
        gems_name="Kuzels",
        display_name="Kuzel's salt",
        category=ProductCategory.AFM,
        description="Chloro-sulfate AFm - intermediate between Friedel's and monosulfate",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "monosulf-AlFe", "contactanglevalue": 0},
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    # ----- More Zeolites -----
    "ZeoliteX": HydrationProductData(
        gems_name="ZeoliteX",
        display_name="Zeolite X",
        category=ProductCategory.ZEOLITE,
        description="Zeolite X - can form in alkali-activated systems",
        suggested_for=[],
        default_affinity=[],
    ),

    "ZeoliteY": HydrationProductData(
        gems_name="ZeoliteY",
        display_name="Zeolite Y",
        category=ProductCategory.ZEOLITE,
        description="Zeolite Y - can form in alkali-activated systems",
        suggested_for=[],
        default_affinity=[],
    ),

    "zeoliteP_Ca": HydrationProductData(
        gems_name="zeoliteP_Ca",
        display_name="Zeolite P (Ca)",
        category=ProductCategory.ZEOLITE,
        description="Calcium-exchanged Zeolite P",
        suggested_for=[],
        default_affinity=[],
    ),

    # ----- Silicates and Pozzolanic Phases -----
    "Forsterite": HydrationProductData(
        gems_name="Forsterite",
        display_name="Forsterite",
        category=ProductCategory.OTHER,
        description="Magnesium silicate (Mg2SiO4) - olivine end-member",
        suggested_for=[],
        default_affinity=[],
    ),

    "Fayalite": HydrationProductData(
        gems_name="Fayalite",
        display_name="Fayalite",
        category=ProductCategory.OTHER,
        description="Iron silicate (Fe2SiO4) - olivine end-member",
        suggested_for=[],
        default_affinity=[],
    ),

    "Mullite": HydrationProductData(
        gems_name="Mullite",
        display_name="Mullite",
        category=ProductCategory.OTHER,
        description="Aluminosilicate (Al6Si2O13) - common in fly ash",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "Diopside": HydrationProductData(
        gems_name="Diopside",
        display_name="Diopside",
        category=ProductCategory.OTHER,
        description="Calcium magnesium silicate (CaMgSi2O6) - pyroxene mineral",
        suggested_for=[],
        default_affinity=[],
    ),

    "Albite": HydrationProductData(
        gems_name="Albite",
        display_name="Albite",
        category=ProductCategory.OTHER,
        description="Sodium feldspar (NaAlSi3O8)",
        suggested_for=[],
        default_affinity=[],
    ),

    "Anorthite": HydrationProductData(
        gems_name="Anorthite",
        display_name="Anorthite",
        category=ProductCategory.OTHER,
        description="Calcium feldspar (CaAl2Si2O8)",
        suggested_for=[],
        default_affinity=[],
    ),

    # ----- Glass/Pozzolanic Phases (fly ash, slag) -----
    "Sfume": HydrationProductData(
        gems_name="Sfume",
        display_name="Silica Fume",
        category=ProductCategory.OTHER,
        description="Amorphous silica - reactive pozzolan",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "K6A2S": HydrationProductData(
        gems_name="K6A2S",
        display_name="K6A2S Glass",
        category=ProductCategory.OTHER,
        description="Potassium aluminosilicate glass phase",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "CAS": HydrationProductData(
        gems_name="CAS",
        display_name="CAS Glass",
        category=ProductCategory.OTHER,
        description="Calcium aluminosilicate glass - fly ash phase",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "CA2S": HydrationProductData(
        gems_name="CA2S",
        display_name="CA2S Glass",
        category=ProductCategory.OTHER,
        description="Calcium dialuminosilicate glass - fly ash phase",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "C2AS": HydrationProductData(
        gems_name="C2AS",
        display_name="C2AS Glass (Gehlenite)",
        category=ProductCategory.OTHER,
        description="Dicalcium aluminosilicate glass - gehlenite composition",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "CAS2": HydrationProductData(
        gems_name="CAS2",
        display_name="CAS2 Glass (Anorthite)",
        category=ProductCategory.OTHER,
        description="Calcium aluminodisilicate glass - anorthite composition",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    # ----- Aluminum Hydroxides -----
    "Al(OH)3am": HydrationProductData(
        gems_name="Al(OH)3am",
        display_name="Al(OH)3 amorphous",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Amorphous aluminum hydroxide",
        suggested_for=[],
        default_affinity=[],
    ),

    "Al(OH)3mic": HydrationProductData(
        gems_name="Al(OH)3mic",
        display_name="Al(OH)3 microcrystalline",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Microcrystalline aluminum hydroxide",
        suggested_for=[],
        default_affinity=[],
    ),

    "Gibbsite": HydrationProductData(
        gems_name="Gibbsite",
        display_name="Gibbsite",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Crystalline aluminum hydroxide Al(OH)3",
        suggested_for=[],
        default_affinity=[],
    ),

    # ----- Carbonates -----
    "Aragonite": HydrationProductData(
        gems_name="Aragonite",
        display_name="Aragonite",
        category=ProductCategory.OTHER,
        description="Calcium carbonate polymorph (orthorhombic)",
        suggested_for=[],
        default_affinity=[],
    ),

    "Dolomite-dis": HydrationProductData(
        gems_name="Dolomite-dis",
        display_name="Dolomite (disordered)",
        category=ProductCategory.OTHER,
        description="Disordered calcium magnesium carbonate",
        suggested_for=[],
        default_affinity=[],
    ),

    "Dolomite-ord": HydrationProductData(
        gems_name="Dolomite-ord",
        display_name="Dolomite (ordered)",
        category=ProductCategory.OTHER,
        description="Ordered calcium magnesium carbonate",
        suggested_for=[],
        default_affinity=[],
    ),

    "Magnesite": HydrationProductData(
        gems_name="Magnesite",
        display_name="Magnesite",
        category=ProductCategory.OTHER,
        description="Magnesium carbonate MgCO3",
        suggested_for=[],
        default_affinity=[],
    ),

    "Siderite": HydrationProductData(
        gems_name="Siderite",
        display_name="Siderite",
        category=ProductCategory.OTHER,
        description="Iron carbonate FeCO3",
        suggested_for=[],
        default_affinity=[],
    ),

    "Fe-carbonate": HydrationProductData(
        gems_name="Fe-carbonate",
        display_name="Fe-carbonate",
        category=ProductCategory.OTHER,
        description="Iron carbonate phase",
        suggested_for=[],
        default_affinity=[],
    ),

    # ----- More Aluminate Hydrates -----
    "C2AH75": HydrationProductData(
        gems_name="C2AH75",
        display_name="C2AH7.5",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Dicalcium aluminate hydrate",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "CAH10": HydrationProductData(
        gems_name="CAH10",
        display_name="CAH10",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminate decahydrate",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
    ),

    "straetlingite": HydrationProductData(
        gems_name="straetlingite",
        display_name="Strätlingite",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Calcium aluminosilicate hydrate C2ASH8",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    "C2ASH55": HydrationProductData(
        gems_name="C2ASH55",
        display_name="C2ASH5.5 (Strätlingite variant)",
        category=ProductCategory.ALUMINATE_HYDRATE,
        description="Strätlingite with 5.5 water molecules",
        suggested_for=["pozzolanic"],
        default_affinity=[],
    ),

    # ----- Ferrite Hydrates -----
    "C3FS0.84H4.32": HydrationProductData(
        gems_name="C3FS0.84H4.32",
        display_name="Fe-siliceous hydrogarnet",
        category=ProductCategory.FERRITE_HYDRATE,
        description="Iron-siliceous hydrogarnet phase",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    "C3FS1.34H3.32": HydrationProductData(
        gems_name="C3FS1.34H3.32",
        display_name="Fe-siliceous hydrogarnet (high Si)",
        category=ProductCategory.FERRITE_HYDRATE,
        description="Iron-siliceous hydrogarnet with higher Si content",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    "C4Fc05H10": HydrationProductData(
        gems_name="C4Fc05H10",
        display_name="Fe-hemicarbonate",
        category=ProductCategory.CARBONATE_AFM,
        description="Iron hemicarbonate AFm",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    "C4FcH12": HydrationProductData(
        gems_name="C4FcH12",
        display_name="Fe-monocarbonate",
        category=ProductCategory.CARBONATE_AFM,
        description="Iron monocarbonate AFm",
        suggested_for=[],
        default_affinity=[
            {"affinityphase": "Ferrite", "contactanglevalue": 0},
        ],
    ),

    # ----- Hydrotalcites -----
    "OH-hydrotalc": HydrationProductData(
        gems_name="OH-hydrotalc",
        display_name="OH-Hydrotalcite",
        category=ProductCategory.HYDROTALCITE,
        description="Hydroxide hydrotalcite Mg-Al LDH",
        suggested_for=["slag"],
        default_affinity=[],
    ),

    # ----- Iron Oxides/Hydroxides -----
    "Goethite": HydrationProductData(
        gems_name="Goethite",
        display_name="Goethite",
        category=ProductCategory.OTHER,
        description="Iron oxyhydroxide FeOOH",
        suggested_for=[],
        default_affinity=[],
    ),

    "Hematite": HydrationProductData(
        gems_name="Hematite",
        display_name="Hematite",
        category=ProductCategory.OTHER,
        description="Iron oxide Fe2O3",
        suggested_for=[],
        default_affinity=[],
    ),

    "Magnetite": HydrationProductData(
        gems_name="Magnetite",
        display_name="Magnetite",
        category=ProductCategory.OTHER,
        description="Iron oxide Fe3O4",
        suggested_for=[],
        default_affinity=[],
    ),

    "Ferrihyd-am": HydrationProductData(
        gems_name="Ferrihyd-am",
        display_name="Ferrihydrite (amorphous)",
        category=ProductCategory.OTHER,
        description="Amorphous iron hydroxide",
        suggested_for=[],
        default_affinity=[],
    ),

    "Ferrihyd-mc": HydrationProductData(
        gems_name="Ferrihyd-mc",
        display_name="Ferrihydrite (microcrystalline)",
        category=ProductCategory.OTHER,
        description="Microcrystalline iron hydroxide",
        suggested_for=[],
        default_affinity=[],
    ),

    # ----- Other Hydration Products -----
    "thaumasite": HydrationProductData(
        gems_name="thaumasite",
        display_name="Thaumasite",
        category=ProductCategory.OTHER,
        description="Ca3Si(CO3)(SO4)(OH)6·12H2O - sulfate attack product",
        suggested_for=[],
        default_affinity=[],
    ),

    "syngenite": HydrationProductData(
        gems_name="syngenite",
        display_name="Syngenite",
        category=ProductCategory.OTHER,
        description="Potassium calcium sulfate K2Ca(SO4)2·H2O",
        suggested_for=[],
        default_affinity=[],
    ),

    "Natrolite": HydrationProductData(
        gems_name="Natrolite",
        display_name="Natrolite",
        category=ProductCategory.ZEOLITE,
        description="Sodium zeolite Na2Al2Si3O10·2H2O",
        suggested_for=[],
        default_affinity=[],
    ),

    "Kaolinite": HydrationProductData(
        gems_name="Kaolinite",
        display_name="Kaolinite",
        category=ProductCategory.OTHER,
        description="Clay mineral Al2Si2O5(OH)4",
        suggested_for=[],
        default_affinity=[],
    ),

    "Periclase": HydrationProductData(
        gems_name="Periclase",
        display_name="Periclase",
        category=ProductCategory.OTHER,
        description="Magnesium oxide MgO",
        suggested_for=[],
        default_affinity=[],
    ),

    "Melanterite": HydrationProductData(
        gems_name="Melanterite",
        display_name="Melanterite",
        category=ProductCategory.OTHER,
        description="Iron sulfate heptahydrate FeSO4·7H2O",
        suggested_for=[],
        default_affinity=[],
    ),

    "Pyrrhotite": HydrationProductData(
        gems_name="Pyrrhotite",
        display_name="Pyrrhotite",
        category=ProductCategory.OTHER,
        description="Iron sulfide Fe(1-x)S",
        suggested_for=[],
        default_affinity=[],
    ),

    "Troilite": HydrationProductData(
        gems_name="Troilite",
        display_name="Troilite",
        category=ProductCategory.OTHER,
        description="Iron sulfide FeS",
        suggested_for=[],
        default_affinity=[],
    ),

    "Sulphur": HydrationProductData(
        gems_name="Sulphur",
        display_name="Sulfur",
        category=ProductCategory.OTHER,
        description="Elemental sulfur S",
        suggested_for=[],
        default_affinity=[],
    ),

    "lime": HydrationProductData(
        gems_name="lime",
        display_name="Lime (free CaO)",
        category=ProductCategory.OTHER,
        description="Calcium oxide CaO",
        suggested_for=[],
        default_affinity=[],
    ),
}


# =============================================================================
# Default Contact Angle
# =============================================================================

DEFAULT_CONTACT_ANGLE = 90  # Neutral affinity for unknown phase pairs


# =============================================================================
# Hydration Products Service
# =============================================================================

class HydrationProductsService:
    """
    Service for managing hydration product selection and configuration.

    Provides:
    - List of all available hydration products from GEMS database
    - Suggested products for different cement types
    - Default affinity data that can be overridden
    - C-S-H special parameters (PSD, Rd values)
    """

    def __init__(self, gems_parser=None):
        """
        Initialize the service.

        Args:
            gems_parser: Optional GEMSParserService for getting full phase list
        """
        self.gems_parser = gems_parser
        self.logger = logging.getLogger('THAMES.HydrationProductsService')

        # Combine suggested and additional products
        self._all_products = {**SUGGESTED_PRODUCTS, **ADDITIONAL_PRODUCTS}

    def get_suggested_products(self) -> List[str]:
        """
        Get list of suggested product names for typical portland cement simulation.

        Returns:
            List of GEMS phase names
        """
        return list(SUGGESTED_PRODUCTS.keys())

    def get_suggested_products_for_cement_type(self, cement_type: str) -> List[str]:
        """
        Get suggested products for a specific cement type.

        Args:
            cement_type: One of 'portland', 'blended', 'pozzolanic', 'limestone', 'slag'

        Returns:
            List of GEMS phase names suggested for this cement type
        """
        suggested = []
        for name, data in self._all_products.items():
            if cement_type.lower() in [t.lower() for t in data.suggested_for]:
                suggested.append(name)

        # Always include CSHQ and Portlandite for any cement type
        if "CSHQ" not in suggested:
            suggested.insert(0, "CSHQ")
        if "Portlandite" not in suggested:
            suggested.insert(1, "Portlandite")

        return suggested

    def get_all_available_products(self) -> List[str]:
        """
        Get all products that have predefined data.

        Returns:
            List of GEMS phase names
        """
        return list(self._all_products.keys())

    def get_all_gems_phases(self) -> List[str]:
        """
        Get all phases from GEMS database that could potentially be hydration products.

        This excludes the electrolyte, gas, and dissolving phases.

        Returns:
            List of GEMS phase names
        """
        if self.gems_parser is None:
            # Return just our known products if no parser
            return list(self._all_products.keys())

        # Get all solid phases from GEMS
        solid_phases = self.gems_parser.get_solid_phases()

        # Filter out dissolving phases (clinker, sulfates, pozzolans)
        from app.services.kinetic_defaults_service import KineticDefaultsService
        kinetic_service = KineticDefaultsService()

        product_phases = []
        for phase in solid_phases:
            # If phase has kinetics, it's a dissolving phase, not a product
            if kinetic_service.get_kinetics_for_phase(phase.name) is None:
                product_phases.append(phase.name)

        return product_phases

    def get_product_data(self, gems_name: str) -> Optional[HydrationProductData]:
        """
        Get data for a specific hydration product.

        Args:
            gems_name: GEMS phase name

        Returns:
            HydrationProductData or None if not found
        """
        return self._all_products.get(gems_name)

    def get_default_affinity(self, gems_name: str) -> List[Dict[str, Any]]:
        """
        Get default interface affinity data for a phase.

        Args:
            gems_name: GEMS phase name

        Returns:
            List of affinity entries (may be empty)
        """
        data = self._all_products.get(gems_name)
        if data:
            return list(data.default_affinity)  # Return a copy
        return []

    def get_default_contact_angle(self) -> int:
        """
        Get the default contact angle for unknown phase pairs.

        Returns:
            Contact angle in degrees (90 = neutral)
        """
        return DEFAULT_CONTACT_ANGLE

    def get_cshq_poresize_distribution(self) -> List[Dict[str, float]]:
        """
        Get the default poresize distribution for C-S-H.

        Returns:
            List of {diameter, volumefraction} entries
        """
        return list(CSHQ_PORESIZE_DISTRIBUTION)

    def get_cshq_rd_values(self) -> List[Dict[str, Any]]:
        """
        Get the default Rd (distribution coefficient) values for C-S-H.

        Returns:
            List of {Rdelement, Rdvalue} entries
        """
        return list(CSHQ_RD_VALUES)

    def get_products_by_category(self) -> Dict[ProductCategory, List[str]]:
        """
        Get all products grouped by category.

        Returns:
            Dict mapping category to list of phase names
        """
        by_category: Dict[ProductCategory, List[str]] = {}

        for name, data in self._all_products.items():
            if data.category not in by_category:
                by_category[data.category] = []
            by_category[data.category].append(name)

        return by_category

    def get_category_for_phase(self, gems_name: str) -> Optional[ProductCategory]:
        """
        Get the category for a phase.

        Args:
            gems_name: GEMS phase name

        Returns:
            ProductCategory or None
        """
        data = self._all_products.get(gems_name)
        return data.category if data else None

    def get_display_name(self, gems_name: str) -> str:
        """
        Get the user-friendly display name for a phase.

        Args:
            gems_name: GEMS phase name

        Returns:
            Display name (or gems_name if not found)
        """
        data = self._all_products.get(gems_name)
        return data.display_name if data else gems_name

    def get_description(self, gems_name: str) -> str:
        """
        Get the description for a phase.

        Args:
            gems_name: GEMS phase name

        Returns:
            Description string (may be empty)
        """
        data = self._all_products.get(gems_name)
        return data.description if data else ""

    def has_special_csh_data(self, gems_name: str) -> bool:
        """
        Check if a phase has special C-S-H data (PSD, Rd).

        Args:
            gems_name: GEMS phase name

        Returns:
            True if phase has PSD and Rd data
        """
        data = self._all_products.get(gems_name)
        if data:
            return data.poresize_distribution is not None or data.rd_values is not None
        return False


# =============================================================================
# Module-level singleton
# =============================================================================

_hydration_products_service: Optional[HydrationProductsService] = None


def get_hydration_products_service(gems_parser=None) -> HydrationProductsService:
    """
    Get the HydrationProductsService singleton.

    Args:
        gems_parser: Optional GEMS parser (only needed on first call if want full phase list)

    Returns:
        HydrationProductsService instance
    """
    global _hydration_products_service

    if _hydration_products_service is None:
        _hydration_products_service = HydrationProductsService(gems_parser)

    return _hydration_products_service

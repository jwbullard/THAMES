"""
Phase Mapping Configuration for VCCTL to THAMES Migration

This module defines the mappings between VCCTL phase names and GEMS phase names,
as well as typical phase groupings for different material types.
"""

from typing import Dict, List, Set

# VCCTL Cement Phase → GEMS Phase Name Mapping
VCCTL_TO_GEMS_CEMENT: Dict[str, str] = {
    "C3S": "Alite",
    "C2S": "Belite",
    "C3A": "Aluminate",
    "C4AF": "Ferrite",
    "K2SO4": "Arcanite",
    "NA2SO4": "Thenardite",
    "GYPSUM": "Gypsum",
    "HEMIHYD": "hemihydrate",
    "ANHYDRITE": "Anhydrite",
}

# Reverse mapping (GEMS → VCCTL)
GEMS_TO_VCCTL_CEMENT: Dict[str, str] = {
    v: k for k, v in VCCTL_TO_GEMS_CEMENT.items()
}

# Limestone phases (VCCTL likely uses CACO3 or similar)
# These are GEMS phase names
LIMESTONE_PHASES: List[str] = [
    "Calcite",       # CaCO3
    "Dolomite-dis",  # CaMg(CO3)2 disordered
    "Dolomite-ord",  # CaMg(CO3)2 ordered
    "lime",          # CaO
]

# Typical Fly Ash phases (GEMS names)
# Note: Users will create custom fly ash materials using these
TYPICAL_FLYASH_PHASES: List[str] = [
    "Quartz",       # SiO2 - crystalline silica
    "Mullite",      # Al6Si2O13 - aluminum silicate
    "Aluminate",    # C3A - WARNING: Also in cement!
    "C2AS(am)",     # Amorphous calcium aluminum silicate
    "CA2S(am)",     # Amorphous calcium aluminum silicate
    "CAS(am)",      # Amorphous calcium aluminum silicate
    "CAS2(am)",     # Amorphous calcium aluminum silicate
    "K6A2S(am)",    # Amorphous potassium aluminum silicate
]

# Typical Filler phases (GEMS names)
# Users will define custom fillers using these
TYPICAL_FILLER_PHASES: List[str] = [
    "Quartz",       # SiO2
    "Calcite",      # CaCO3
    "Magnesite",    # MgCO3
    "periclase",    # MgO
    "Brucite",      # Mg(OH)2
]

# Default tags for migrated materials
DEFAULT_CEMENT_TAGS: List[str] = ["cement", "migrated-from-vcctl"]
DEFAULT_LIMESTONE_TAGS: List[str] = ["limestone", "migrated-from-vcctl"]

# Suggested tags for user-created materials
SUGGESTED_TAGS: Dict[str, List[str]] = {
    "cement": ["portland", "type-i", "type-ii", "type-iii", "type-iv", "type-v", "white", "oil-well"],
    "pozzolan": ["fly-ash", "silica-fume", "natural-pozzolan", "metakaolin", "class-c", "class-f"],
    "slag": ["ggbfs", "ground-granulated"],
    "limestone": ["filler", "calcite", "dolomite"],
    "filler": ["inert", "quartz", "calcite"],
    "aggregate": ["fine", "coarse", "lightweight"],
}


def get_gems_phase_name(vcctl_phase: str) -> str:
    """
    Convert a VCCTL cement phase name to GEMS phase name.

    Args:
        vcctl_phase: VCCTL phase name (e.g., 'C3S')

    Returns:
        GEMS phase name (e.g., 'Alite')

    Raises:
        KeyError: If phase not found in mapping
    """
    return VCCTL_TO_GEMS_CEMENT[vcctl_phase]


def get_vcctl_phase_name(gems_phase: str) -> str:
    """
    Convert a GEMS phase name to VCCTL cement phase name.

    Args:
        gems_phase: GEMS phase name (e.g., 'Alite')

    Returns:
        VCCTL phase name (e.g., 'C3S')

    Raises:
        KeyError: If phase not found in mapping
    """
    return GEMS_TO_VCCTL_CEMENT[gems_phase]


def is_cement_phase(phase_name: str, use_gems_names: bool = True) -> bool:
    """
    Check if a phase name is a valid cement phase.

    Args:
        phase_name: Phase name to check
        use_gems_names: If True, expects GEMS names; if False, expects VCCTL names

    Returns:
        True if phase is a cement phase
    """
    if use_gems_names:
        return phase_name in VCCTL_TO_GEMS_CEMENT.values()
    else:
        return phase_name in VCCTL_TO_GEMS_CEMENT.keys()


def is_limestone_phase(phase_name: str) -> bool:
    """
    Check if a phase name is a valid limestone phase (GEMS names).

    Args:
        phase_name: GEMS phase name

    Returns:
        True if phase is a limestone phase
    """
    return phase_name in LIMESTONE_PHASES


def is_flyash_phase(phase_name: str) -> bool:
    """
    Check if a phase name is a typical fly ash phase (GEMS names).

    Note: This is not exhaustive - users can create fly ash with any phases.

    Args:
        phase_name: GEMS phase name

    Returns:
        True if phase is a typical fly ash phase
    """
    return phase_name in TYPICAL_FLYASH_PHASES


def get_phase_overlap_warning(phases: List[str]) -> List[str]:
    """
    Check for phases that appear in multiple material categories.

    Args:
        phases: List of GEMS phase names

    Returns:
        List of warning messages for overlapping phases
    """
    warnings = []
    phase_set = set(phases)

    # Check for cement-fly ash overlap
    cement_set = set(VCCTL_TO_GEMS_CEMENT.values())
    flyash_set = set(TYPICAL_FLYASH_PHASES)
    overlap = phase_set & cement_set & flyash_set

    if overlap:
        warnings.append(
            f"Phase(s) {overlap} appear in both cement and fly ash categories. "
            "This is allowed but may indicate incorrect material definition."
        )

    return warnings


def get_all_known_phases() -> Set[str]:
    """
    Get set of all known phase names (GEMS format).

    Returns:
        Set of all GEMS phase names in mappings
    """
    all_phases = set(VCCTL_TO_GEMS_CEMENT.values())
    all_phases.update(LIMESTONE_PHASES)
    all_phases.update(TYPICAL_FLYASH_PHASES)
    all_phases.update(TYPICAL_FILLER_PHASES)
    return all_phases


# Phase categories for UI dropdowns
PHASE_CATEGORIES: Dict[str, List[str]] = {
    "Cement Clinker": [
        "Alite",      # C3S
        "Belite",     # C2S
        "Aluminate",  # C3A
        "Ferrite",    # C4AF
    ],
    "Cement Sulfates": [
        "Gypsum",       # CaSO4·2H2O
        "hemihydrate",  # CaSO4·0.5H2O
        "Anhydrite",    # CaSO4
    ],
    "Cement Alkalis": [
        "Arcanite",    # K2SO4
        "Thenardite",  # Na2SO4
    ],
    "Limestone": [
        "Calcite",       # CaCO3
        "Dolomite-dis",  # Disordered dolomite
        "Dolomite-ord",  # Ordered dolomite
        "lime",          # CaO
    ],
    "Pozzolanic (Amorphous)": [
        "C2AS(am)",
        "CA2S(am)",
        "CAS(am)",
        "CAS2(am)",
        "K6A2S(am)",
        "Silica-amorph",
    ],
    "Pozzolanic (Crystalline)": [
        "Quartz",
        "Mullite",
        "Sfume",  # Silica fume
    ],
    "Fillers": [
        "Quartz",
        "Calcite",
        "Magnesite",
        "periclase",
        "Brucite",
    ],
}

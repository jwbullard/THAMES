#!/usr/bin/env python3
"""
Phase Color Service for THAMES

Assigns consistent colors to GEMS phases based on phase names.
Colors are derived from VCCTL's colors.csv where possible, with
additional colors for GEMS-specific phases.

The key principle: Colors are linked to phase NAMES, not phase IDs.
This ensures consistent visualization across simulations even when
phase IDs differ.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from app.services.phase_id_mapping_service import PhaseIdMapping

logger = logging.getLogger('THAMES.PhaseColorService')


# =============================================================================
# GEMS Phase to Color Mapping
# =============================================================================
# Colors are in RGB hex format (#RRGGBB)
# Derived from VCCTL colors.csv where applicable, with additions for GEMS phases

PHASE_COLORS: Dict[str, str] = {
    # ----- Reserved/Special Phases -----
    "VOID": "#000000",           # Black (pure void/empty) - RGB(0,0,0)
    "Electrolyte": "#001419",    # Dark blue (aqueous/electrolyte) - RGB(0,20,25)
    "ELECTROLYTE": "#001419",    # Alias for Electrolyte - RGB(0,20,25)
    "aq_gen": "#001419",         # Legacy alias for Electrolyte - RGB(0,20,25)
    "gas_gen": "#E8E8E8",        # Very light gray (gas phase)
    "AGGREGATE": "#FFC041",      # Gold (from VCCTL Aggregate: 255,192,65)

    # ----- Clinker Phases (VCCTL IDs 1-6) -----
    "Alite": "#2A2AD2",          # Blue (from VCCTL C3S: 42,42,210)
    "Belite": "#8B4F13",         # Brown (from VCCTL C2S: 139,79,19)
    "Aluminate": "#B2B2B2",      # Light gray (from VCCTL C3A: 178,178,178)
    "Ferrite": "#FDFDFD",        # White (from VCCTL C4AF: 253,253,253)
    "Arcanite": "#FF0000",       # Red (from VCCTL K2SO4: 255,0,0)
    "arcanite": "#FF0000",       # Legacy alias for Arcanite
    "Thenardite": "#FF1400",     # Red-orange (from VCCTL Na2SO4: 255,20,0)
    "thenardite": "#FF1400",     # Legacy alias for Thenardite

    # ----- Calcium Sulfates (VCCTL IDs 7-9) -----
    "Gypsum": "#FFFF00",         # Yellow (from VCCTL: 255,255,0)
    "hemihydrate": "#FFF056",    # Light yellow (from VCCTL: 255,240,86)
    "Anhydrite": "#FFFF80",      # Pale yellow (from VCCTL: 255,255,128)

    # ----- Calcium Hydroxide / Portlandite -----
    "Portlandite": "#07488E",    # Dark blue (from VCCTL: 7,72,142)
    "lime": "#80FF00",           # Bright lime green (from VCCTL Free lime: 128,255,0)

    # ----- Calcium Carbonates -----
    "Calcite": "#00CC00",        # Green (from VCCTL CITE: 0,204,0)
    "Aragonite": "#00AA00",      # Darker green (similar to calcite)
    "Dolomite-dis": "#00DD44",   # Green with hint of cyan
    "Dolomite-ord": "#00BB44",   # Slightly different dolomite
    "Magnesite": "#44DD00",      # Yellow-green

    # ----- C-S-H Phases -----
    "CSHQ": "#F5DEB3",           # Wheat (from VCCTL CSH: 245,222,179)
    "C3(AF)S0.84H": "#E8D4A0",   # Tan (C-S-H variant)
    "MSH": "#D4C4A0",            # Tan/brown (Mg-Si-H)

    # ----- AFt Phases (Ettringite family) -----
    "ettr": "#7F00FF",           # Violet (from VCCTL AFt: 127,0,255)
    "ettr-AlFe": "#7F00FF",      # Same as ettringite
    "SO4_CO3_AFt": "#9020FF",    # Purple variant
    "thaumasite": "#6000CC",     # Dark violet

    # ----- AFm Phases (Monosulfate family) -----
    "monosulf-AlFe": "#F446CB",  # Pink (from VCCTL AFm: 244,70,203)
    "C4AsH105": "#F446CB",       # Pink
    "C4AsH12": "#F050D0",        # Pink variant
    "C4AsH14": "#E840C0",        # Pink variant
    "C4AsH16": "#E030B0",        # Pink variant
    "C4AsH9": "#F860E0",         # Light pink
    "C6AsH13": "#D030A0",        # Magenta
    "C6AsH9": "#C02090",         # Dark magenta

    # ----- Carbonate AFm Phases -----
    "C4AcH9": "#FAC6DC",         # Light pink (from VCCTL AFmc: 250,198,220)
    "C4AcH11": "#F8B8D0",        # Pink variant
    "C4Ac0.5H105": "#F0A8C8",    # Pink variant
    "C4Ac0.5H12": "#E898C0",     # Pink variant
    "C4Ac0.5H9": "#E088B8",      # Pink variant

    # ----- Hydrogarnet / Aluminate Hydrates -----
    "C3AH6": "#969600",          # Olive (from VCCTL: 150,150,0)
    "C2AH75": "#A0A000",         # Olive variant
    "C4AH11": "#888800",         # Darker olive
    "C4AH13": "#808000",         # Olive
    "C4AH19": "#787800",         # Dark olive
    "CAH10": "#909000",          # Olive variant
    "straet": "#404000",         # Dark olive (from VCCTL Straetlingite: 64,64,0)
    "C2ASH55": "#505010",        # Dark olive variant

    # ----- Iron Phases -----
    "C3FH6": "#408080",          # Teal (from VCCTL FH3: 64,128,128)
    "C4FH13": "#508888",         # Teal variant
    "C3FS0.84H4.32": "#488080",  # Teal variant
    "C3FS1.34H3.32": "#488888",  # Teal variant
    "C4Fc05H10": "#409090",      # Cyan-teal
    "C4FcH12": "#489898",        # Cyan-teal variant
    "Iron": "#808080",           # Gray (metallic)
    "Fe-carbonate": "#606060",   # Dark gray
    "Siderite": "#505050",       # Dark gray
    "Hematite": "#8B0000",       # Dark red
    "Magnetite": "#2F2F2F",      # Very dark gray
    "Ferrihyd-am": "#8B4513",    # Saddle brown
    "Ferrihyd-mc": "#A0522D",    # Sienna
    "Goethite": "#DAA520",       # Goldenrod
    "Pyrrhotite": "#704214",     # Bronze
    "Troilite": "#5C4033",       # Dark brown
    "Melanterite": "#90EE90",    # Light green (iron sulfate)

    # ----- Aluminum Hydroxides -----
    "Al(OH)3am": "#C0C0C0",      # Silver
    "Al(OH)3mic": "#D0D0D0",     # Light silver
    "Gibbsite": "#E0E0E0",       # Very light gray

    # ----- Silica Phases -----
    "Quartz": "#FFB347",         # Sandy/tan (from VCCTL Silica am: 26,100,26 adjusted)
    "Silica-amorph": "#1A641A",  # Forest green (from VCCTL: 26,100,26)
    "Sfume": "#28AD4B",          # Green (from VCCTL: 40,173,75)

    # ----- Calcium Aluminates (for calcium aluminate cements) -----
    "CA": "#8080FF",             # Light blue
    "CA2": "#6060FF",            # Medium blue
    "Mayenite": "#4040FF",       # Blue

    # ----- Pozzolanic / SCM Phases -----
    "Mullite": "#D2691E",        # Chocolate brown
    "Kaolinite": "#DEB887",      # Burlywood
    "C2AS(am)": "#B8860B",       # Dark goldenrod
    "CA2S(am)": "#CD853F",       # Peru
    "CAS(am)": "#D2B48C",        # Tan
    "CAS2(am)": "#C4A35A",       # Dark tan
    "K6A2S(am)": "#8B7355",      # Burly wood dark

    # ----- Zeolites -----
    "Chabazite": "#00CED1",      # Dark turquoise
    "ZeoliteP": "#20B2AA",       # Light sea green
    "ZeoliteX": "#48D1CC",       # Medium turquoise
    "ZeoliteY": "#40E0D0",       # Turquoise
    "Natrolite": "#5F9EA0",      # Cadet blue

    # ----- Alkali Phases -----
    "syngenite": "#FF6060",      # Light red
    "K-oxide": "#FF4040",        # Red
    "Na-oxide": "#FF2020",       # Bright red

    # ----- Magnesium Phases -----
    "periclase": "#1A671A",      # Dark green
    "Brucite": "#1A671A",        # Dark green (from VCCTL: 26,103,26)
    "hydrotalc-pyro": "#2E8B57", # Sea green

    # ----- Other -----
    "Graphite": "#1C1C1C",       # Near black
    "Sulphur": "#FFFF00",        # Yellow (same as gypsum family)
}

# Fallback colors for unknown phases (will cycle through these)
FALLBACK_COLORS = [
    "#FF6B6B",  # Coral red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Sky blue
    "#96CEB4",  # Sage green
    "#FFEAA7",  # Pale yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Soft yellow
    "#BB8FCE",  # Light purple
    "#85C1E9",  # Light blue
    "#F8B500",  # Amber
    "#00CED1",  # Dark turquoise
]


@dataclass
class PhaseColorMapping:
    """Complete phase color mapping for an operation."""
    operation_name: str
    phase_id_to_name: Dict[int, str]   # microstructure ID → GEMS name
    phase_id_to_color: Dict[int, str]  # microstructure ID → hex color
    phase_name_to_color: Dict[str, str]  # GEMS name → hex color (for reference)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "operation_name": self.operation_name,
            "phase_id_to_name": {str(k): v for k, v in self.phase_id_to_name.items()},
            "phase_id_to_color": {str(k): v for k, v in self.phase_id_to_color.items()},
            "phase_name_to_color": self.phase_name_to_color
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PhaseColorMapping':
        """Create from dictionary (e.g., loaded from JSON)."""
        return cls(
            operation_name=data.get("operation_name", ""),
            phase_id_to_name={int(k): v for k, v in data.get("phase_id_to_name", {}).items()},
            phase_id_to_color={int(k): v for k, v in data.get("phase_id_to_color", {}).items()},
            phase_name_to_color=data.get("phase_name_to_color", {})
        )


class PhaseColorService:
    """
    Service for assigning and managing phase colors.

    Colors are assigned based on phase names (not IDs) to ensure
    consistency across simulations. The service uses predefined
    colors from VCCTL where applicable, with additional colors
    for GEMS-specific phases.
    """

    def __init__(self):
        self.logger = logging.getLogger('THAMES.PhaseColorService')
        self._fallback_index = 0

    def get_color_for_phase(self, phase_name: str) -> str:
        """
        Get the color for a given phase name.

        Args:
            phase_name: GEMS phase name

        Returns:
            Hex color string (#RRGGBB)
        """
        if phase_name in PHASE_COLORS:
            return PHASE_COLORS[phase_name]

        # Generate a fallback color for unknown phases
        color = self._get_fallback_color(phase_name)
        self.logger.warning(f"No predefined color for phase '{phase_name}', using fallback: {color}")
        return color

    def _get_fallback_color(self, phase_name: str) -> str:
        """Generate a consistent fallback color for an unknown phase."""
        # Use hash of phase name to get consistent color assignment
        hash_val = hash(phase_name)
        index = abs(hash_val) % len(FALLBACK_COLORS)
        return FALLBACK_COLORS[index]

    def create_color_mapping(
        self,
        operation_name: str,
        phase_id_mapping: PhaseIdMapping
    ) -> PhaseColorMapping:
        """
        Create a complete color mapping for an operation.

        Args:
            operation_name: Name of the operation
            phase_id_mapping: Phase ID mapping from micgen_input_service

        Returns:
            PhaseColorMapping with colors for all phases
        """
        phase_id_to_color = {}
        phase_name_to_color = {}

        for phase_id, phase_name in phase_id_mapping.micro_to_gem.items():
            color = self.get_color_for_phase(phase_name)
            phase_id_to_color[phase_id] = color
            phase_name_to_color[phase_name] = color

        return PhaseColorMapping(
            operation_name=operation_name,
            phase_id_to_name=dict(phase_id_mapping.micro_to_gem),
            phase_id_to_color=phase_id_to_color,
            phase_name_to_color=phase_name_to_color
        )

    def save_color_mapping(
        self,
        color_mapping: PhaseColorMapping,
        output_dir: Path
    ) -> Path:
        """
        Save color mapping to JSON file.

        Args:
            color_mapping: The color mapping to save
            output_dir: Directory to save to

        Returns:
            Path to saved file
        """
        output_path = output_dir / f"{color_mapping.operation_name}_phase_colors.json"

        with open(output_path, 'w') as f:
            json.dump(color_mapping.to_dict(), f, indent=2)

        self.logger.info(f"Saved phase color mapping to {output_path}")
        return output_path

    def load_color_mapping(self, file_path: Path) -> Optional[PhaseColorMapping]:
        """
        Load color mapping from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            PhaseColorMapping or None if file doesn't exist
        """
        if not file_path.exists():
            self.logger.warning(f"Color mapping file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return PhaseColorMapping.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load color mapping from {file_path}: {e}")
            return None

    def save_phase_id_mapping(
        self,
        phase_mapping: PhaseIdMapping,
        operation_name: str,
        output_dir: Path
    ) -> Path:
        """
        Save phase ID mapping to JSON file.

        Args:
            phase_mapping: The phase ID mapping
            operation_name: Name of the operation
            output_dir: Directory to save to

        Returns:
            Path to saved file
        """
        output_path = output_dir / f"{operation_name}_phase_mapping.json"

        mapping_data = {
            "operation_name": operation_name,
            "phase_id_mapping": phase_mapping.to_dict()
        }

        with open(output_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)

        self.logger.info(f"Saved phase ID mapping to {output_path}")
        return output_path

    def load_phase_id_mapping(self, file_path: Path) -> Optional[PhaseIdMapping]:
        """
        Load phase ID mapping from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            PhaseIdMapping or None if file doesn't exist
        """
        if not file_path.exists():
            self.logger.warning(f"Phase mapping file not found: {file_path}")
            return None

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            mapping_data = data.get("phase_id_mapping", {})

            # Reconstruct PhaseIdMapping
            return PhaseIdMapping(
                gem_to_micro=mapping_data.get("gem_to_micro", {}),
                micro_to_gem={int(k): v for k, v in mapping_data.get("micro_to_gem", {}).items()},
                has_clinker=mapping_data.get("has_clinker", False),
                clinker_phase_ids=mapping_data.get("clinker_phase_ids", {}),
                next_available_id=mapping_data.get("next_available_id", 0)
            )
        except Exception as e:
            self.logger.error(f"Failed to load phase mapping from {file_path}: {e}")
            return None

    def hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple (0-255)."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def hex_to_rgb_normalized(self, hex_color: str) -> Tuple[float, float, float]:
        """Convert hex color to normalized RGB tuple (0.0-1.0) for VTK/PyVista."""
        r, g, b = self.hex_to_rgb(hex_color)
        return (r / 255.0, g / 255.0, b / 255.0)

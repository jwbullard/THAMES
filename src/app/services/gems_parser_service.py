"""
GEMS Database Parser Service

Parses the GEMS3K thermodynamic database files to extract:
- Independent Components (ICs)
- Dependent Components (DCs)
- GEM Phases
- Relationships between DCs and Phases

The parser reads thames-dch.dat which uses a key-value format where
keys are enclosed in angle brackets like <nDC> and values follow.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DependentComponent:
    """Represents a Dependent Component (DC) in GEMS"""
    name: str
    index: int  # 0-based index in DCNL list
    molar_mass: float  # kg/mol
    molar_volume: float  # m³/mol (V0 from GEMS database)
    class_code: str  # 'S', 'I', 'J', 'M', 'O', 'G', 'T', 'W'

    @property
    def density(self) -> float:
        """
        Calculate DC density from molar mass and molar volume.

        Returns:
            Density in kg/m³
        """
        if self.molar_volume == 0:
            return 0.0
        return self.molar_mass / self.molar_volume

    @property
    def specific_gravity(self) -> float:
        """
        Calculate DC specific gravity (density relative to water at 4°C).

        Returns:
            Specific gravity (dimensionless)
        """
        return self.density / 1000.0  # kg/m³ to g/cm³


@dataclass
class GEMPhase:
    """Represents a GEM Phase with its associated DCs"""
    name: str
    index: int  # 0-based index in PHNL list
    num_dcs: int  # Number of DCs in this phase
    dc_indices: List[int]  # Indices of DCs that belong to this phase
    dc_names: List[str]  # Names of DCs that belong to this phase
    class_code: str  # Phase class code


class GEMSParserService:
    """
    Service for parsing GEMS3K thermodynamic database files.

    Reads thames-dch.dat to extract phase and DC information needed
    by the THAMES UI for building simulation parameters.
    """

    def __init__(self, gems_data_dir: Path):
        """
        Initialize the GEMS parser.

        Args:
            gems_data_dir: Path to directory containing GEMS .dat files
        """
        self.gems_data_dir = Path(gems_data_dir)
        self.dch_file = self.gems_data_dir / "thames-dch.dat"

        # Parsed data
        self.num_ics: int = 0
        self.num_dcs: int = 0
        self.num_phases: int = 0
        self.num_tp: int = 1   # nTp - number of temperature grid points
        self.num_pp: int = 1   # nPp - number of pressure grid points
        self.standard_t_index: int = 0  # Index for 298.15 K in temperature grid

        self.ic_names: List[str] = []
        self.dc_names: List[str] = []
        self.phase_names: List[str] = []

        self.dc_molar_masses: List[float] = []
        self.dc_molar_volumes: List[float] = []  # V0 in m³/mol at standard T/P
        self.dc_class_codes: List[str] = []
        self.phase_class_codes: List[str] = []

        self.num_dcs_in_phase: List[int] = []

        # Temperature grid for finding standard conditions
        self.temperature_grid: List[float] = []

        # Derived data structures
        self.phases: Dict[str, GEMPhase] = {}
        self.dcs: Dict[str, DependentComponent] = {}

        # Parse on initialization
        if self.dch_file.exists():
            self._parse_dch_file()
        else:
            raise FileNotFoundError(f"GEMS DCH file not found: {self.dch_file}")

    def _parse_dch_file(self) -> None:
        """Parse the thames-dch.dat file to extract all data."""
        with open(self.dch_file, 'r') as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip comments and empty lines
            if not line or line.startswith('#') or line.startswith('$') or line.startswith(';'):
                i += 1
                continue

            # Parse key-value pairs
            if line.startswith('<'):
                key = self._extract_key(line)

                if key == 'nIC':
                    self.num_ics = self._parse_single_int(lines, i)
                elif key == 'nDC':
                    self.num_dcs = self._parse_single_int(lines, i)
                elif key == 'nPH':
                    self.num_phases = self._parse_single_int(lines, i)
                elif key == 'nTp':
                    self.num_tp = self._parse_single_int(lines, i)
                elif key == 'nPp':
                    self.num_pp = self._parse_single_int(lines, i)
                elif key == 'TKval':
                    self.temperature_grid = self._parse_float_array(lines, i)
                    # Find index closest to 298.15 K (standard conditions)
                    self._find_standard_temperature_index()
                elif key == 'ICNL':
                    self.ic_names = self._parse_name_list(lines, i)
                elif key == 'DCNL':
                    self.dc_names = self._parse_name_list(lines, i)
                elif key == 'PHNL':
                    self.phase_names = self._parse_name_list(lines, i)
                elif key == 'DCmm':
                    self.dc_molar_masses = self._parse_float_array(lines, i)
                elif key == 'V0':
                    # V0 has nDC * nTp * nPp values; extract at standard T/P
                    all_v0 = self._parse_float_array(lines, i)
                    self.dc_molar_volumes = self._extract_standard_tp_values(all_v0)
                elif key == 'ccDC':
                    self.dc_class_codes = self._parse_name_list(lines, i)
                elif key == 'ccPH':
                    self.phase_class_codes = self._parse_name_list(lines, i)
                elif key == 'nDCinPH':
                    self.num_dcs_in_phase = self._parse_int_array(lines, i)

            i += 1

        # Build derived data structures
        self._build_phase_dc_mappings()

    def _extract_key(self, line: str) -> str:
        """Extract key from a line like '<nDC>  180'"""
        if '<' in line and '>' in line:
            start = line.index('<') + 1
            end = line.index('>')
            return line[start:end]
        return ""

    def _parse_single_int(self, lines: List[str], start_idx: int) -> int:
        """Parse a single integer value that appears after the key."""
        line = lines[start_idx].strip()
        # Key and value on same line: <nDC>  180
        if '>' in line:
            parts = line.split('>')
            if len(parts) > 1:
                return int(parts[1].strip())
        return 0

    def _parse_int_array(self, lines: List[str], start_idx: int) -> List[int]:
        """Parse an array of integers that spans multiple lines."""
        values = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next key or empty line after data
            if line.startswith('<') or (line.startswith('#') and len(values) > 0):
                break

            # Skip comments
            if line.startswith('#') or line.startswith('$') or line.startswith(';'):
                i += 1
                continue

            if not line:
                i += 1
                continue

            # Parse integers from line
            tokens = line.split()
            for token in tokens:
                try:
                    values.append(int(token))
                except ValueError:
                    pass

            i += 1

        return values

    def _parse_float_array(self, lines: List[str], start_idx: int) -> List[float]:
        """Parse an array of floats that spans multiple lines."""
        values = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next key
            if line.startswith('<') or (line.startswith('#') and len(values) > 0):
                break

            # Skip comments
            if line.startswith('#') or line.startswith('$') or line.startswith(';'):
                i += 1
                continue

            if not line:
                i += 1
                continue

            # Parse floats from line
            tokens = line.split()
            for token in tokens:
                try:
                    values.append(float(token))
                except ValueError:
                    pass

            i += 1

        return values

    def _find_standard_temperature_index(self) -> None:
        """Find the index in the temperature grid closest to 298.15 K."""
        if not self.temperature_grid:
            self.standard_t_index = 0
            return

        standard_t = 298.15  # Standard temperature in K
        min_diff = float('inf')
        best_index = 0

        for i, t in enumerate(self.temperature_grid):
            diff = abs(t - standard_t)
            if diff < min_diff:
                min_diff = diff
                best_index = i

        self.standard_t_index = best_index

    def _extract_standard_tp_values(self, all_values: List[float]) -> List[float]:
        """
        Extract values at standard T/P from a full T/P grid array.

        The array is organized as [nDC * nTp * nPp] where values are stored
        as DC0_T0_P0, DC0_T0_P1, ..., DC0_T1_P0, ..., DC1_T0_P0, ...

        For nPp=1, this simplifies to: DC0_T0, DC0_T1, ..., DC0_T35, DC1_T0, ...
        """
        if self.num_tp <= 1 and self.num_pp <= 1:
            # Old format: one value per DC
            return all_values

        stride = self.num_tp * self.num_pp  # Values per DC
        t_index = self.standard_t_index
        p_index = 0  # Assume first pressure point

        extracted = []
        for dc_idx in range(self.num_dcs):
            # Index for this DC at standard T/P
            idx = dc_idx * stride + t_index * self.num_pp + p_index
            if idx < len(all_values):
                extracted.append(all_values[idx])
            else:
                extracted.append(0.0)

        return extracted

    def _parse_name_list(self, lines: List[str], start_idx: int) -> List[str]:
        """Parse a list of quoted names like 'Al(SO4)+' 'Al+3' ..."""
        names = []
        i = start_idx + 1

        while i < len(lines):
            line = lines[i].strip()

            # Stop at next key
            if line.startswith('<') or (line.startswith('#') and len(names) > 0):
                break

            # Skip comments
            if line.startswith('#') or line.startswith('$') or line.startswith(';'):
                i += 1
                continue

            if not line:
                i += 1
                continue

            # Parse quoted strings from line
            # Handle both 'name' and "name" formats
            tokens = line.split("'")
            for j, token in enumerate(tokens):
                # Odd indices are the quoted strings
                if j % 2 == 1:
                    names.append(token)

            i += 1

        return names

    def _build_phase_dc_mappings(self) -> None:
        """
        Build the phase-to-DC mappings based on nDCinPH array.

        The DCs in DCNL are ordered such that:
        - First n_1 DCs belong to phase 1
        - Next n_2 DCs belong to phase 2
        - And so on...
        """
        dc_index = 0

        # Build DC objects
        for i, dc_name in enumerate(self.dc_names):
            molar_mass = self.dc_molar_masses[i] if i < len(self.dc_molar_masses) else 0.0
            molar_volume = self.dc_molar_volumes[i] if i < len(self.dc_molar_volumes) else 0.0
            class_code = self.dc_class_codes[i] if i < len(self.dc_class_codes) else ''

            self.dcs[dc_name] = DependentComponent(
                name=dc_name,
                index=i,
                molar_mass=molar_mass,
                molar_volume=molar_volume,
                class_code=class_code
            )

        # Build phase objects with DC mappings
        for phase_idx, phase_name in enumerate(self.phase_names):
            num_dcs = self.num_dcs_in_phase[phase_idx] if phase_idx < len(self.num_dcs_in_phase) else 0
            class_code = self.phase_class_codes[phase_idx] if phase_idx < len(self.phase_class_codes) else ''

            # Get the indices and names of DCs for this phase
            dc_indices = list(range(dc_index, dc_index + num_dcs))
            dc_names_for_phase = [self.dc_names[i] for i in dc_indices if i < len(self.dc_names)]

            self.phases[phase_name] = GEMPhase(
                name=phase_name,
                index=phase_idx,
                num_dcs=num_dcs,
                dc_indices=dc_indices,
                dc_names=dc_names_for_phase,
                class_code=class_code
            )

            dc_index += num_dcs

    # Public API methods

    def get_phase(self, phase_name: str) -> Optional[GEMPhase]:
        """Get a GEM phase by name."""
        return self.phases.get(phase_name)

    def get_dc(self, dc_name: str) -> Optional[DependentComponent]:
        """Get a Dependent Component by name."""
        return self.dcs.get(dc_name)

    def get_all_phases(self) -> List[GEMPhase]:
        """Get all GEM phases sorted by index."""
        return sorted(self.phases.values(), key=lambda p: p.index)

    def get_all_dcs(self) -> List[DependentComponent]:
        """Get all Dependent Components sorted by index."""
        return sorted(self.dcs.values(), key=lambda d: d.index)

    def get_dcs_for_phase(self, phase_name: str) -> List[DependentComponent]:
        """Get all DCs that belong to a specific phase."""
        phase = self.phases.get(phase_name)
        if not phase:
            return []

        return [self.dcs[dc_name] for dc_name in phase.dc_names if dc_name in self.dcs]

    def get_phase_names(self) -> List[str]:
        """Get list of all phase names."""
        return [p.name for p in self.get_all_phases()]

    def get_dc_names(self) -> List[str]:
        """Get list of all DC names."""
        return [d.name for d in self.get_all_dcs()]

    def get_solution_phases(self) -> List[GEMPhase]:
        """Get phases that are solutions (class code 'a' for aqueous)."""
        return [p for p in self.phases.values() if p.class_code in ['a', 'A']]

    def get_solid_phases(self) -> List[GEMPhase]:
        """Get phases that are solids (class codes like 'I', 'J', 'M', 'O')."""
        solid_codes = ['I', 'J', 'M', 'O', 'i', 'j', 'm', 'o']
        return [p for p in self.phases.values() if p.class_code in solid_codes]

    def get_gas_phases(self) -> List[GEMPhase]:
        """Get phases that are gases (class code 'g' or 'G')."""
        return [p for p in self.phases.values() if p.class_code in ['g', 'G']]

    def validate_phase_dc_configuration(self, phase_name: str, dc_names: List[str]) -> Tuple[bool, str]:
        """
        Validate that a set of DC names are valid for a given phase.

        Returns:
            (is_valid, error_message)
        """
        phase = self.phases.get(phase_name)
        if not phase:
            return False, f"Phase '{phase_name}' not found in GEMS database"

        valid_dc_names = set(phase.dc_names)
        provided_dc_names = set(dc_names)

        # Check for invalid DCs
        invalid_dcs = provided_dc_names - valid_dc_names
        if invalid_dcs:
            return False, f"Invalid DCs for phase '{phase_name}': {invalid_dcs}"

        return True, ""

    def get_dc_density(self, dc_name: str) -> Optional[float]:
        """
        Get the density of a Dependent Component.

        Args:
            dc_name: Name of the DC

        Returns:
            Density in kg/m³, or None if DC not found or has zero molar volume
        """
        dc = self.dcs.get(dc_name)
        if not dc or dc.molar_volume == 0:
            return None
        return dc.density

    def get_phase_density(self, phase_name: str) -> Optional[float]:
        """
        Get the density of a GEM phase.

        For solid phases with a single DC, returns that DC's density.
        For phases with multiple DCs, this is a simplified calculation
        assuming equal mole fractions (future: use GEMS equilibrium data).

        Args:
            phase_name: Name of the GEM phase

        Returns:
            Density in kg/m³, or None if phase not found

        Note:
            For solution phases (aqueous, gas), densities vary with composition.
            This method provides an approximation only.
        """
        phase = self.phases.get(phase_name)
        if not phase:
            return None

        # For single-DC phases (most solid phases), use that DC's density
        if phase.num_dcs == 1:
            dc_name = phase.dc_names[0]
            return self.get_dc_density(dc_name)

        # For multi-DC phases, calculate weighted average
        # (Simplified: assuming equal mole fractions - not accurate for solution phases)
        densities = []
        for dc_name in phase.dc_names:
            density = self.get_dc_density(dc_name)
            if density is not None and density > 0:
                densities.append(density)

        if not densities:
            return None

        # Simple average (future enhancement: use actual mole fractions from GEMS)
        return sum(densities) / len(densities)

    def calculate_material_density(self, phase_mass_fractions: Dict[str, float]) -> Optional[float]:
        """
        Calculate material density from phase mass fractions.

        Args:
            phase_mass_fractions: Dictionary mapping GEM phase names to mass fractions
                                 Example: {"Alite": 0.60, "Belite": 0.15, ...}

        Returns:
            Material density in kg/m³, or None if calculation fails

        Formula:
            density_material = 1 / Σ(w_i / ρ_i)
            where w_i is mass fraction of phase i, ρ_i is density of phase i
        """
        if not phase_mass_fractions:
            return None

        # Calculate inverse density (specific volume)
        specific_volume = 0.0
        total_mass_fraction = 0.0

        for phase_name, mass_fraction in phase_mass_fractions.items():
            if mass_fraction <= 0:
                continue

            phase_density = self.get_phase_density(phase_name)
            if phase_density is None or phase_density <= 0:
                # Skip phases with unknown or invalid densities
                continue

            specific_volume += mass_fraction / phase_density
            total_mass_fraction += mass_fraction

        if specific_volume == 0 or total_mass_fraction == 0:
            return None

        # Normalize if total mass fraction != 1.0
        if abs(total_mass_fraction - 1.0) > 0.01:
            specific_volume = specific_volume / total_mass_fraction

        return 1.0 / specific_volume

    def calculate_material_specific_gravity(self, phase_mass_fractions: Dict[str, float]) -> Optional[float]:
        """
        Calculate material specific gravity from phase mass fractions.

        Args:
            phase_mass_fractions: Dictionary mapping GEM phase names to mass fractions

        Returns:
            Specific gravity (dimensionless), or None if calculation fails
        """
        density = self.calculate_material_density(phase_mass_fractions)
        if density is None:
            return None
        return density / 1000.0  # Convert kg/m³ to g/cm³

    def get_summary(self) -> str:
        """Get a summary of the GEMS database."""
        return f"""GEMS Database Summary:
  - Independent Components (ICs): {self.num_ics}
  - Dependent Components (DCs): {self.num_dcs}
  - GEM Phases: {self.num_phases}

Phase Type Distribution:
  - Aqueous phases: {len(self.get_solution_phases())}
  - Solid phases: {len(self.get_solid_phases())}
  - Gas phases: {len(self.get_gas_phases())}

Example phases:
  - {self.phase_names[0]}: {self.num_dcs_in_phase[0]} DCs
  - {self.phase_names[1]}: {self.num_dcs_in_phase[1]} DCs
  - {self.phase_names[2] if len(self.phase_names) > 2 else 'N/A'}: {self.num_dcs_in_phase[2] if len(self.num_dcs_in_phase) > 2 else 0} DCs
"""

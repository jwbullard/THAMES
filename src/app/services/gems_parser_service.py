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
    class_code: str  # 'S', 'I', 'J', 'M', 'O', 'G', 'T', 'W'


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

        self.ic_names: List[str] = []
        self.dc_names: List[str] = []
        self.phase_names: List[str] = []

        self.dc_molar_masses: List[float] = []
        self.dc_class_codes: List[str] = []
        self.phase_class_codes: List[str] = []

        self.num_dcs_in_phase: List[int] = []

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
                elif key == 'ICNL':
                    self.ic_names = self._parse_name_list(lines, i)
                elif key == 'DCNL':
                    self.dc_names = self._parse_name_list(lines, i)
                elif key == 'PHNL':
                    self.phase_names = self._parse_name_list(lines, i)
                elif key == 'DCmm':
                    self.dc_molar_masses = self._parse_float_array(lines, i)
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
            class_code = self.dc_class_codes[i] if i < len(self.dc_class_codes) else ''

            self.dcs[dc_name] = DependentComponent(
                name=dc_name,
                index=i,
                molar_mass=molar_mass,
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

#!/usr/bin/env python3
"""
Kinetic Parameter Data Classes for THAMES

Defines data structures for the three kinetic model types used by THAMES-Hydration:
1. ParrotKillohKinetics - For clinker phases (Alite, Belite, Aluminate, Ferrite)
2. StandardKinetics - For sulfate phases (Gypsum, Anhydrite, Hemihydrate)
3. PozzolanicKinetics - For pozzolanic phases (Quartz, Mullite, fly ash glasses)

These dataclasses are used to:
- Store kinetic parameters from the database or user input
- Serialize to simparams.json format for THAMES-Hydration
- Validate parameter values

References:
- Parrot, L.J., Killoh, D.C., Prediction of cement hydration, British Ceramic
  Proceedings 35 (1984) 41-53.
- Lothenbach, B., Winnefeld, F., Thermodynamic modelling of the hydration of
  portland cement, Cement and Concrete Research 36 (2006) 209-226.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Union
import json


@dataclass
class ParrotKillohKinetics:
    """
    Parrot-Killoh kinetic parameters for clinker phases.

    The Parrot-Killoh model calculates dissolution rates based on three
    rate-controlling mechanisms:
    1. Nucleation and growth (k1, n1)
    2. Early-age diffusion (k2)
    3. Late-age diffusion (k3, n3)

    The actual rate is the minimum of these three mechanisms.

    Attributes:
        k1: Nucleation/growth rate constant (dimensionless)
        k2: Early diffusion rate constant (dimensionless)
        k3: Late diffusion rate constant (dimensionless)
        n1: Nucleation/growth exponent (dimensionless)
        n3: Late diffusion exponent (dimensionless)
        dorHcoeff: Lothenbach-Kulik H coefficient for critical DOR calculation
        activationEnergy: Apparent activation energy (J/mol)
        loi: Loss on ignition (mass fraction, typically 0 for clinker)
    """
    k1: float
    k2: float
    k3: float
    n1: float
    n3: float
    dorHcoeff: float
    activationEnergy: float
    loi: float = 0.0

    def __post_init__(self):
        """Validate parameters after initialization."""
        self._validate()

    def _validate(self):
        """Validate that parameters are within reasonable bounds."""
        if self.k1 < 0:
            raise ValueError(f"k1 must be non-negative, got {self.k1}")
        if self.k2 < 0:
            raise ValueError(f"k2 must be non-negative, got {self.k2}")
        if self.k3 < 0:
            raise ValueError(f"k3 must be non-negative, got {self.k3}")
        if self.n1 <= 0:
            raise ValueError(f"n1 must be positive, got {self.n1}")
        if self.n3 <= 0:
            raise ValueError(f"n3 must be positive, got {self.n3}")
        if self.dorHcoeff < 0:
            raise ValueError(f"dorHcoeff must be non-negative, got {self.dorHcoeff}")
        if self.activationEnergy < 0:
            raise ValueError(f"activationEnergy must be non-negative, got {self.activationEnergy}")
        if self.loi < 0:
            raise ValueError(f"loi must be non-negative, got {self.loi}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for simparams.json serialization.

        Returns:
            Dictionary with 'type' field set to 'ParrotKilloh'
        """
        return {
            "type": "ParrotKilloh",
            "k1": self.k1,
            "k2": self.k2,
            "k3": self.k3,
            "n1": self.n1,
            "n3": self.n3,
            "dorHcoeff": self.dorHcoeff,
            "activationEnergy": self.activationEnergy,
            "loi": self.loi
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParrotKillohKinetics':
        """
        Create instance from dictionary.

        Args:
            data: Dictionary with kinetic parameters (may include 'type' field)

        Returns:
            ParrotKillohKinetics instance
        """
        # Remove 'type' field if present
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)

    def with_override(self, override: Dict[str, Any]) -> 'ParrotKillohKinetics':
        """
        Create a new instance with some parameters overridden.

        Args:
            override: Dictionary of parameters to override

        Returns:
            New ParrotKillohKinetics instance with overridden values
        """
        current = asdict(self)
        # Filter out 'type' field if present (it's not a constructor parameter)
        filtered_override = {k: v for k, v in override.items() if k != 'type'}
        current.update(filtered_override)
        return ParrotKillohKinetics(**current)


@dataclass
class StandardKinetics:
    """
    Standard kinetic parameters for sulfate and other dissolving phases.

    This model uses a simpler dissolution mechanism based on:
    - Surface dissolution rate
    - Diffusion through product layer
    - Saturation index effects

    Attributes:
        dissolutionRateConst: Dissolution rate constant (mol/m2/s)
        diffusionRateConstEarly: Early-age diffusion rate constant
        diffusionRateConstLate: Late-age diffusion rate constant
        dissolvedUnits: Number of DC units per dissolution event
        siexp: Saturation index exponent
        dfexp: Driving force exponent
        dorexp: Degree of reaction exponent
        activationEnergy: Apparent activation energy (J/mol)
        loi: Loss on ignition (mass fraction)
    """
    dissolutionRateConst: float
    diffusionRateConstEarly: float
    diffusionRateConstLate: float
    dissolvedUnits: int
    siexp: float
    dfexp: float
    dorexp: float
    activationEnergy: float
    loi: float = 0.0

    def __post_init__(self):
        """Validate parameters after initialization."""
        self._validate()

    def _validate(self):
        """Validate that parameters are within reasonable bounds."""
        if self.dissolutionRateConst < 0:
            raise ValueError(f"dissolutionRateConst must be non-negative, got {self.dissolutionRateConst}")
        if self.diffusionRateConstEarly < 0:
            raise ValueError(f"diffusionRateConstEarly must be non-negative, got {self.diffusionRateConstEarly}")
        if self.diffusionRateConstLate < 0:
            raise ValueError(f"diffusionRateConstLate must be non-negative, got {self.diffusionRateConstLate}")
        if self.dissolvedUnits < 1:
            raise ValueError(f"dissolvedUnits must be at least 1, got {self.dissolvedUnits}")
        if self.activationEnergy < 0:
            raise ValueError(f"activationEnergy must be non-negative, got {self.activationEnergy}")
        if self.loi < 0:
            raise ValueError(f"loi must be non-negative, got {self.loi}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for simparams.json serialization.

        Returns:
            Dictionary with 'type' field set to 'Standard'
        """
        return {
            "type": "Standard",
            "dissolutionRateConst": self.dissolutionRateConst,
            "diffusionRateConstEarly": self.diffusionRateConstEarly,
            "diffusionRateConstLate": self.diffusionRateConstLate,
            "dissolvedUnits": self.dissolvedUnits,
            "siexp": self.siexp,
            "dfexp": self.dfexp,
            "dorexp": self.dorexp,
            "activationEnergy": self.activationEnergy,
            "loi": self.loi
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardKinetics':
        """
        Create instance from dictionary.

        Args:
            data: Dictionary with kinetic parameters (may include 'type' field)

        Returns:
            StandardKinetics instance
        """
        # Remove 'type' field if present
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)

    def with_override(self, override: Dict[str, Any]) -> 'StandardKinetics':
        """
        Create a new instance with some parameters overridden.

        Args:
            override: Dictionary of parameters to override

        Returns:
            New StandardKinetics instance with overridden values
        """
        current = asdict(self)
        # Filter out 'type' field if present (it's not a constructor parameter)
        filtered_override = {k: v for k, v in override.items() if k != 'type'}
        current.update(filtered_override)
        return StandardKinetics(**current)


@dataclass
class PozzolanicKinetics:
    """
    Pozzolanic kinetic parameters for silica-rich phases.

    Extends the Standard model with additional parameters for
    pozzolanic reaction kinetics, which depend on:
    - Hydroxyl ion activity (OH- concentration)
    - Silica content of the material

    Attributes:
        dissolutionRateConst: Dissolution rate constant (mol/m2/s)
        diffusionRateConstEarly: Early-age diffusion rate constant
        diffusionRateConstLate: Late-age diffusion rate constant
        dissolvedUnits: Number of DC units per dissolution event
        siexp: Saturation index exponent
        dfexp: Driving force exponent
        dorexp: Degree of reaction exponent
        ohexp: Hydroxyl ion activity exponent
        sio2: SiO2 content (mass fraction, 0-1)
        activationEnergy: Apparent activation energy (J/mol)
        loi: Loss on ignition (mass fraction)
    """
    dissolutionRateConst: float
    diffusionRateConstEarly: float
    diffusionRateConstLate: float
    dissolvedUnits: int
    siexp: float
    dfexp: float
    dorexp: float
    ohexp: float
    sio2: float
    activationEnergy: float
    loi: float = 0.0

    def __post_init__(self):
        """Validate parameters after initialization."""
        self._validate()

    def _validate(self):
        """Validate that parameters are within reasonable bounds."""
        if self.dissolutionRateConst < 0:
            raise ValueError(f"dissolutionRateConst must be non-negative, got {self.dissolutionRateConst}")
        if self.diffusionRateConstEarly < 0:
            raise ValueError(f"diffusionRateConstEarly must be non-negative, got {self.diffusionRateConstEarly}")
        if self.diffusionRateConstLate < 0:
            raise ValueError(f"diffusionRateConstLate must be non-negative, got {self.diffusionRateConstLate}")
        if self.dissolvedUnits < 1:
            raise ValueError(f"dissolvedUnits must be at least 1, got {self.dissolvedUnits}")
        if self.activationEnergy < 0:
            raise ValueError(f"activationEnergy must be non-negative, got {self.activationEnergy}")
        if self.loi < 0:
            raise ValueError(f"loi must be non-negative, got {self.loi}")
        if not 0 <= self.sio2 <= 1:
            raise ValueError(f"sio2 must be between 0 and 1, got {self.sio2}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for simparams.json serialization.

        Returns:
            Dictionary with 'type' field set to 'Pozzolanic'
        """
        return {
            "type": "Pozzolanic",
            "dissolutionRateConst": self.dissolutionRateConst,
            "diffusionRateConstEarly": self.diffusionRateConstEarly,
            "diffusionRateConstLate": self.diffusionRateConstLate,
            "dissolvedUnits": self.dissolvedUnits,
            "siexp": self.siexp,
            "dfexp": self.dfexp,
            "dorexp": self.dorexp,
            "ohexp": self.ohexp,
            "sio2": self.sio2,
            "activationEnergy": self.activationEnergy,
            "loi": self.loi
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PozzolanicKinetics':
        """
        Create instance from dictionary.

        Args:
            data: Dictionary with kinetic parameters (may include 'type' field)

        Returns:
            PozzolanicKinetics instance
        """
        # Remove 'type' field if present
        params = {k: v for k, v in data.items() if k != 'type'}
        return cls(**params)

    def with_override(self, override: Dict[str, Any]) -> 'PozzolanicKinetics':
        """
        Create a new instance with some parameters overridden.

        Args:
            override: Dictionary of parameters to override

        Returns:
            New PozzolanicKinetics instance with overridden values
        """
        current = asdict(self)
        # Filter out 'type' field if present (it's not a constructor parameter)
        filtered_override = {k: v for k, v in override.items() if k != 'type'}
        current.update(filtered_override)
        return PozzolanicKinetics(**current)


# Type alias for any kinetic parameters type
KineticParameters = Union[ParrotKillohKinetics, StandardKinetics, PozzolanicKinetics]


def kinetics_from_dict(data: Dict[str, Any]) -> Optional[KineticParameters]:
    """
    Create appropriate kinetic parameters instance from dictionary.

    Args:
        data: Dictionary with 'type' field indicating model type

    Returns:
        Appropriate kinetic parameters instance, or None if type is missing/unknown
    """
    kinetic_type = data.get('type')

    if kinetic_type == 'ParrotKilloh':
        return ParrotKillohKinetics.from_dict(data)
    elif kinetic_type == 'Standard':
        return StandardKinetics.from_dict(data)
    elif kinetic_type == 'Pozzolanic':
        return PozzolanicKinetics.from_dict(data)
    else:
        return None


def get_kinetic_type_name(kinetics: KineticParameters) -> str:
    """
    Get the type name string for a kinetic parameters instance.

    Args:
        kinetics: Any kinetic parameters instance

    Returns:
        Type name string ('ParrotKilloh', 'Standard', or 'Pozzolanic')
    """
    if isinstance(kinetics, ParrotKillohKinetics):
        return 'ParrotKilloh'
    elif isinstance(kinetics, PozzolanicKinetics):
        return 'Pozzolanic'
    elif isinstance(kinetics, StandardKinetics):
        return 'Standard'
    else:
        raise TypeError(f"Unknown kinetic parameters type: {type(kinetics)}")

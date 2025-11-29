#!/usr/bin/env python3
"""
Kinetic Defaults Service for THAMES

Provides scientifically-validated default kinetic parameters, impurity coefficients,
and interface affinity data for all phase types in THAMES-Hydration simulations.

Default values are derived from:
- Parrot, L.J., Killoh, D.C., Prediction of cement hydration, British Ceramic
  Proceedings 35 (1984) 41-53.
- Lothenbach, B., Winnefeld, F., Thermodynamic modelling of the hydration of
  portland cement, Cement and Concrete Research 36 (2006) 209-226.
- THAMES reference simulations (tmp/PC-FlyAsh-200/simparams-new.json)
"""

import logging
from typing import Dict, Optional, List, Any, Union

from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
    KineticParameters
)


class KineticDefaultsService:
    """
    Service providing default kinetic parameters for THAMES phases.

    This service centralizes all default kinetic data so that:
    1. SimParamsService can build phase entries with correct defaults
    2. UI can show users the default values for each phase
    3. Users can override specific parameters while keeping others at defaults
    """

    def __init__(self):
        self.logger = logging.getLogger('THAMES.KineticDefaultsService')

    # =========================================================================
    # PARROT-KILLOH DEFAULTS (Clinker phases)
    # =========================================================================
    #
    # Reference: Parrot & Killoh (1984), Lothenbach & Winnefeld (2006)
    # Activation energies from various sources compiled in THAMES documentation

    PARROT_KILLOH_DEFAULTS: Dict[str, ParrotKillohKinetics] = {
        "Alite": ParrotKillohKinetics(
            k1=1.5,
            k2=0.05,
            k3=1.1,
            n1=0.7,
            n3=3.3,
            dorHcoeff=2.0,
            activationEnergy=41570.0,
            loi=0.0
        ),
        "Belite": ParrotKillohKinetics(
            k1=0.5,
            k2=0.02,
            k3=0.7,
            n1=1.0,
            n3=5.0,
            dorHcoeff=1.55,
            activationEnergy=20785.0,
            loi=0.0
        ),
        "Aluminate": ParrotKillohKinetics(
            k1=1.0,
            k2=0.04,
            k3=1.0,
            n1=0.85,
            n3=3.2,
            dorHcoeff=1.8,
            activationEnergy=54040.0,
            loi=0.0
        ),
        "Ferrite": ParrotKillohKinetics(
            k1=0.37,
            k2=0.02,
            k3=0.4,
            n1=0.7,
            n3=3.7,
            dorHcoeff=1.65,
            activationEnergy=34087.0,
            loi=0.0
        ),
    }

    # =========================================================================
    # STANDARD KINETICS DEFAULTS (Sulfate phases)
    # =========================================================================

    STANDARD_DEFAULTS: Dict[str, StandardKinetics] = {
        "Gypsum": StandardKinetics(
            dissolutionRateConst=1.0e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0,
            loi=0.0
        ),
        "hemihydrate": StandardKinetics(
            dissolutionRateConst=1.5e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0,
            loi=0.0
        ),
        "Anhydrite": StandardKinetics(
            dissolutionRateConst=5.0e-7,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0,
            loi=0.0
        ),
    }

    # =========================================================================
    # POZZOLANIC KINETICS DEFAULTS
    # =========================================================================
    #
    # Note: sio2 values should ideally come from material composition,
    # but these are reasonable defaults for typical materials

    POZZOLANIC_DEFAULTS: Dict[str, PozzolanicKinetics] = {
        # Crystalline silica phases
        "Quartz": PozzolanicKinetics(
            dissolutionRateConst=1.4e-11,
            diffusionRateConstEarly=2.8e-12,
            diffusionRateConstLate=2.8e-12,
            dissolvedUnits=1,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0,
            loi=1.3
        ),
        "Mullite": PozzolanicKinetics(
            dissolutionRateConst=1.4e-11,
            diffusionRateConstEarly=2.8e-12,
            diffusionRateConstLate=2.8e-12,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0,
            loi=1.3
        ),

        # Amorphous fly ash glass phases
        "C2AS(am)": PozzolanicKinetics(
            dissolutionRateConst=1.39e-6,
            diffusionRateConstEarly=8.33e-7,
            diffusionRateConstLate=8.33e-7,
            dissolvedUnits=7,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0,
            loi=1.3
        ),
        "CA2S(am)": PozzolanicKinetics(
            dissolutionRateConst=2.8e-7,
            diffusionRateConstEarly=8.33e-7,
            diffusionRateConstLate=8.33e-7,
            dissolvedUnits=4,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0,
            loi=1.3
        ),
        "K6A2S(am)": PozzolanicKinetics(
            dissolutionRateConst=8.3e-7,
            diffusionRateConstEarly=8.3e-7,
            diffusionRateConstLate=8.3e-7,
            dissolvedUnits=9,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0,
            loi=1.3
        ),

        # Silica fume (amorphous silica)
        "Sfume": PozzolanicKinetics(
            dissolutionRateConst=1.0e-9,
            diffusionRateConstEarly=1.0e-9,
            diffusionRateConstLate=1.0e-9,
            dissolvedUnits=1,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.95,
            activationEnergy=40000.0,
            loi=2.0
        ),

        # Generic amorphous silica
        "Silica-amorph": PozzolanicKinetics(
            dissolutionRateConst=1.0e-9,
            diffusionRateConstEarly=1.0e-9,
            diffusionRateConstLate=1.0e-9,
            dissolvedUnits=1,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.95,
            activationEnergy=40000.0,
            loi=2.0
        ),
    }

    # =========================================================================
    # IMPURITY DATA DEFAULTS
    # =========================================================================
    #
    # These coefficients define how impurities (K2O, Na2O, MgO, SO3) are
    # released during dissolution of each phase.

    IMPURITY_DEFAULTS: Dict[str, Dict[str, float]] = {
        # Clinker phases
        "Alite": {
            "k2ocoeff": 0.00087,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.00861,
            "so3coeff": 0.007942
        },
        "Belite": {
            "k2ocoeff": 0.01152,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.0038,
            "so3coeff": 0.010528
        },
        "Aluminate": {
            "k2ocoeff": 0.00979,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.01091,
            "so3coeff": 0.0
        },
        "Ferrite": {
            "k2ocoeff": 0.00272,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.02292,
            "so3coeff": 0.0
        },

        # Pozzolanic phases (typically low impurities)
        "Quartz": {
            "k2ocoeff": 0.0,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.001,
            "so3coeff": 0.0
        },
        "Mullite": {
            "k2ocoeff": 0.0,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.001,
            "so3coeff": 0.0
        },
        "C2AS(am)": {
            "k2ocoeff": 0.0,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.001,
            "so3coeff": 0.0
        },
        "CA2S(am)": {
            "k2ocoeff": 0.0,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.001,
            "so3coeff": 0.0
        },
        "K6A2S(am)": {
            "k2ocoeff": 0.0,
            "na2ocoeff": 0.0,
            "mgocoeff": 0.001,
            "so3coeff": 0.0
        },
    }

    # =========================================================================
    # INTERFACE AFFINITY DEFAULTS
    # =========================================================================
    #
    # Contact angle values define growth preferences:
    # - 0 = High affinity (grows preferentially on this phase)
    # - 180 = Low affinity (avoids growing on this phase)
    # - 30-60 = Moderate affinity
    #
    # These are used by hydration products to determine where they preferentially
    # precipitate on the microstructure.

    INTERFACE_AFFINITY_DEFAULTS: Dict[str, List[Dict[str, Any]]] = {
        # C-S-H prefers to grow on clinker surfaces
        "CSHQ": [
            {"affinityphase": "Alite", "contactanglevalue": 30},
            {"affinityphase": "Belite", "contactanglevalue": 30},
            {"affinityphase": "Portlandite", "contactanglevalue": 0},
        ],

        # Portlandite grows on C-S-H, avoids clinker
        "Portlandite": [
            {"affinityphase": "CSHQ", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],

        # Aluminate hydrates grow on aluminate
        "C3AH6": [
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
        "C4AH11": [
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
        "C4AH13": [
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],
        "C4AH19": [
            {"affinityphase": "Aluminate", "contactanglevalue": 0},
        ],

        # Ettringite and AFt phases
        "ettr": [
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
        "ettr-AlFe": [
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
        "C6AsH13": [
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
        "C6AsH9": [
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
        "SO4_CO3_AFt": [
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

        # Monosulfate (AFm) phases
        "C4AsH105": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "C4AsH12": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "C4AsH14": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "C4AsH16": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "C4AsH9": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "monosulf-AlFe": [
            {"affinityphase": "ettr-AlFe", "contactanglevalue": 0},
            {"affinityphase": "ettr", "contactanglevalue": 0},
            {"affinityphase": "C6AsH13", "contactanglevalue": 0},
            {"affinityphase": "C6AsH9", "contactanglevalue": 0},
            {"affinityphase": "SO4_CO3_AFt", "contactanglevalue": 0},
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],

        # Carboaluminate phases
        "C4Ac0.5H105": [
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
        "C4Ac0.5H12": [
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
        "C4Ac0.5H9": [
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
        "C4AcH11": [
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
        "C4AcH9": [
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

        # Pozzolanic phases avoid clinker
        "Quartz": [
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
        "Mullite": [
            {"affinityphase": "Alite", "contactanglevalue": 180},
            {"affinityphase": "Belite", "contactanglevalue": 180},
        ],
    }

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def get_kinetics_for_phase(self, phase_name: str) -> Optional[KineticParameters]:
        """
        Get default kinetic parameters for a phase.

        Args:
            phase_name: GEMS phase name (e.g., 'Alite', 'Gypsum', 'Quartz')

        Returns:
            Kinetic parameters instance, or None if phase has no kinetic model
            (e.g., hydration products, electrolyte)
        """
        # Check Parrot-Killoh (clinker phases)
        if phase_name in self.PARROT_KILLOH_DEFAULTS:
            return self.PARROT_KILLOH_DEFAULTS[phase_name]

        # Check Standard (sulfate phases)
        if phase_name in self.STANDARD_DEFAULTS:
            return self.STANDARD_DEFAULTS[phase_name]

        # Check Pozzolanic
        if phase_name in self.POZZOLANIC_DEFAULTS:
            return self.POZZOLANIC_DEFAULTS[phase_name]

        # Phase has no kinetic model (hydration product, electrolyte, etc.)
        return None

    def get_kinetic_type(self, phase_name: str) -> Optional[str]:
        """
        Get the kinetic model type for a phase.

        Args:
            phase_name: GEMS phase name

        Returns:
            'ParrotKilloh', 'Standard', 'Pozzolanic', or None
        """
        if phase_name in self.PARROT_KILLOH_DEFAULTS:
            return 'ParrotKilloh'
        if phase_name in self.STANDARD_DEFAULTS:
            return 'Standard'
        if phase_name in self.POZZOLANIC_DEFAULTS:
            return 'Pozzolanic'
        return None

    def get_impurity_data(self, phase_name: str) -> Optional[Dict[str, float]]:
        """
        Get impurity coefficients for a phase.

        Args:
            phase_name: GEMS phase name

        Returns:
            Dict with k2ocoeff, na2ocoeff, mgocoeff, so3coeff, or None
        """
        return self.IMPURITY_DEFAULTS.get(phase_name)

    def get_interface_affinity(self, phase_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get interface affinity data for a phase.

        Args:
            phase_name: GEMS phase name

        Returns:
            List of affinity dicts, or None if not defined
        """
        return self.INTERFACE_AFFINITY_DEFAULTS.get(phase_name)

    def is_cement_component(self, phase_name: str) -> bool:
        """
        Determine if a phase is a cement component (dissolves during hydration).

        Cement components have kinetic models and dissolution kinetics.
        Non-cement components are hydration products or inert phases.

        Args:
            phase_name: GEMS phase name

        Returns:
            True if phase is a cement component
        """
        # Clinker phases
        if phase_name in self.PARROT_KILLOH_DEFAULTS:
            return True

        # Sulfate phases (except alkali sulfates which dissolve instantly)
        if phase_name in self.STANDARD_DEFAULTS:
            return True

        # Alkali sulfates are cement components but dissolve instantly
        if phase_name in ['Arcanite', 'Thenardite']:
            return True

        # Pozzolanic phases
        if phase_name in self.POZZOLANIC_DEFAULTS:
            return False  # Pozzolans are not "cement" components

        return False

    def get_all_clinker_phases(self) -> List[str]:
        """Get list of all clinker phase names."""
        return list(self.PARROT_KILLOH_DEFAULTS.keys())

    def get_all_sulfate_phases(self) -> List[str]:
        """Get list of all sulfate phase names."""
        return list(self.STANDARD_DEFAULTS.keys())

    def get_all_pozzolanic_phases(self) -> List[str]:
        """Get list of all pozzolanic phase names with defaults."""
        return list(self.POZZOLANIC_DEFAULTS.keys())

    def get_kinetics_with_override(
        self,
        phase_name: str,
        override: Dict[str, Any]
    ) -> Optional[KineticParameters]:
        """
        Get kinetic parameters with user overrides applied.

        Args:
            phase_name: GEMS phase name
            override: Dict of parameters to override

        Returns:
            Kinetic parameters with overrides applied, or None if no kinetics
        """
        defaults = self.get_kinetics_for_phase(phase_name)
        if defaults is None:
            return None

        return defaults.with_override(override)


# Module-level singleton
_kinetic_defaults_service: Optional[KineticDefaultsService] = None


def get_kinetic_defaults_service() -> KineticDefaultsService:
    """Get the singleton KineticDefaultsService instance."""
    global _kinetic_defaults_service
    if _kinetic_defaults_service is None:
        _kinetic_defaults_service = KineticDefaultsService()
    return _kinetic_defaults_service

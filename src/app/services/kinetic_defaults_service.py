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
        "Bassanite": StandardKinetics(
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
        "Arcanite": StandardKinetics(
            dissolutionRateConst=3.0e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0,
            loi=0.0
        ),
        "Thenardite": StandardKinetics(
            dissolutionRateConst=3.0e-6,
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

        Checks user preferences first, then falls back to built-in defaults.
        If user has explicitly set "Thermodynamic", returns None and does NOT
        fall back to built-in defaults.

        Args:
            phase_name: GEMS phase name (e.g., 'Alite', 'Gypsum', 'Quartz')

        Returns:
            Kinetic parameters instance, or None if phase has no kinetic model
            (e.g., hydration products, electrolyte, or explicit Thermodynamic preference)
        """
        # Check if user has explicitly set Thermodynamic - this takes precedence
        if self._user_set_thermodynamic(phase_name):
            self.logger.debug(f"Phase {phase_name}: user preference is Thermodynamic, no kinetics")
            return None

        # Check user preferences for non-Thermodynamic kinetics
        user_kinetics = self._get_user_kinetics(phase_name)
        if user_kinetics is not None:
            return user_kinetics

        # Fall back to built-in defaults
        return self._get_builtin_kinetics(phase_name)

    def _user_set_thermodynamic(self, phase_name: str) -> bool:
        """Check if user explicitly set this phase to Thermodynamic (no kinetics).

        Args:
            phase_name: GEMS phase name

        Returns:
            True if user has explicitly set Thermodynamic preference
        """
        try:
            from app.services.kinetic_preferences_service import get_kinetic_preferences_service
            prefs_service = get_kinetic_preferences_service()
            user_default = prefs_service.get_user_default(phase_name)
            if user_default is not None:
                return user_default.get('type') == 'Thermodynamic'
        except Exception:
            pass
        return False

    def _get_builtin_kinetics(self, phase_name: str) -> Optional[KineticParameters]:
        """Get built-in kinetic defaults (without checking user preferences)."""
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

    def _get_user_kinetics(self, phase_name: str) -> Optional[KineticParameters]:
        """
        Get user-defined kinetic defaults for a phase.

        Args:
            phase_name: GEMS phase name

        Returns:
            KineticParameters if user has defined defaults, None otherwise
        """
        try:
            from app.services.kinetic_preferences_service import get_kinetic_preferences_service
            prefs_service = get_kinetic_preferences_service()

            user_default = prefs_service.get_user_default(phase_name)
            if user_default is None:
                return None

            kinetic_type = user_default.get('type')
            if not kinetic_type or kinetic_type == 'Thermodynamic':
                return None

            # Create kinetic parameters from user default
            if kinetic_type == 'ParrotKilloh':
                return ParrotKillohKinetics(
                    k1=user_default.get('k1', 1.5),
                    k2=user_default.get('k2', 0.05),
                    k3=user_default.get('k3', 1.1),
                    n1=user_default.get('n1', 0.7),
                    n3=user_default.get('n3', 3.3),
                    dorHcoeff=user_default.get('dorHcoeff', 2.0),
                    activationEnergy=user_default.get('activationEnergy', 41570.0),
                    loi=user_default.get('loi', 0.0),
                )
            elif kinetic_type == 'Standard':
                return StandardKinetics(
                    dissolutionRateConst=user_default.get('dissolutionRateConst', 1.0e-6),
                    diffusionRateConstEarly=user_default.get('diffusionRateConstEarly', 5.0e-6),
                    diffusionRateConstLate=user_default.get('diffusionRateConstLate', 5.0e-6),
                    dissolvedUnits=user_default.get('dissolvedUnits', 2),
                    siexp=user_default.get('siexp', 1.0),
                    dfexp=user_default.get('dfexp', 1.1),
                    dorexp=user_default.get('dorexp', 0.5),
                    activationEnergy=user_default.get('activationEnergy', 40000.0),
                    loi=user_default.get('loi', 0.0),
                )
            elif kinetic_type == 'Pozzolanic':
                return PozzolanicKinetics(
                    dissolutionRateConst=user_default.get('dissolutionRateConst', 1.4e-11),
                    diffusionRateConstEarly=user_default.get('diffusionRateConstEarly', 2.8e-12),
                    diffusionRateConstLate=user_default.get('diffusionRateConstLate', 2.8e-12),
                    dissolvedUnits=user_default.get('dissolvedUnits', 1),
                    siexp=user_default.get('siexp', 1.0),
                    dfexp=user_default.get('dfexp', 1.0),
                    dorexp=user_default.get('dorexp', 0.5),
                    ohexp=user_default.get('ohexp', 1.0),
                    sio2=user_default.get('sio2', 0.987),
                    activationEnergy=user_default.get('activationEnergy', 40000.0),
                    loi=user_default.get('loi', 1.3),
                )

            return None

        except Exception as e:
            self.logger.warning(f"Error loading user kinetics for {phase_name}: {e}")
            return None

    def get_kinetic_type(self, phase_name: str) -> Optional[str]:
        """
        Get the kinetic model type for a phase.

        Checks user preferences first, then falls back to built-in defaults.

        Args:
            phase_name: GEMS phase name

        Returns:
            'ParrotKilloh', 'Standard', 'Pozzolanic', or None
        """
        # Check user preferences first
        try:
            from app.services.kinetic_preferences_service import get_kinetic_preferences_service
            prefs_service = get_kinetic_preferences_service()

            user_default = prefs_service.get_user_default(phase_name)
            if user_default is not None:
                kinetic_type = user_default.get('type')
                if kinetic_type and kinetic_type != 'Thermodynamic':
                    return kinetic_type
                elif kinetic_type == 'Thermodynamic':
                    return None  # User explicitly set to Thermodynamic
        except Exception:
            pass

        # Fall back to built-in defaults
        if phase_name in self.PARROT_KILLOH_DEFAULTS:
            return 'ParrotKilloh'
        if phase_name in self.STANDARD_DEFAULTS:
            return 'Standard'
        if phase_name in self.POZZOLANIC_DEFAULTS:
            return 'Pozzolanic'
        return None

    def has_user_override(self, phase_name: str) -> bool:
        """
        Check if a phase has a user-defined kinetic default.

        Args:
            phase_name: GEMS phase name

        Returns:
            True if user has defined a default for this phase
        """
        try:
            from app.services.kinetic_preferences_service import get_kinetic_preferences_service
            return get_kinetic_preferences_service().has_user_default(phase_name)
        except Exception:
            return False

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

        Checks user preferences first, then falls back to built-in defaults.

        Args:
            phase_name: GEMS phase name

        Returns:
            List of affinity dicts, or None if not defined
        """
        # Check user preferences first
        user_affinity = self._get_user_affinity(phase_name)
        if user_affinity is not None:
            return user_affinity

        # Fall back to built-in defaults
        return self.INTERFACE_AFFINITY_DEFAULTS.get(phase_name)

    def _get_user_affinity(self, phase_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get user-defined affinity defaults for a phase.

        Args:
            phase_name: GEMS phase name

        Returns:
            List of affinity dicts if user has defined defaults, None otherwise
        """
        try:
            from app.services.affinity_preferences_service import get_affinity_preferences_service
            prefs_service = get_affinity_preferences_service()
            return prefs_service.get_user_default(phase_name)
        except Exception as e:
            self.logger.warning(f"Error loading user affinities for {phase_name}: {e}")
            return None

    def get_affinity_with_override(
        self,
        phase_name: str,
        override: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get affinity data with optional override.

        If override is provided, it completely replaces any defaults/preferences.
        If override is an empty list, returns empty list (explicit no affinities).
        If override is None, returns defaults/preferences.

        Args:
            phase_name: GEMS phase name
            override: Optional list of affinity dicts to override

        Returns:
            List of affinity dicts (may be empty), or None
        """
        # If explicit override is provided, use it (even if empty list)
        if override is not None:
            return override

        # Otherwise use defaults (which checks user preferences first)
        return self.get_interface_affinity(phase_name)

    def has_affinity_user_override(self, phase_name: str) -> bool:
        """
        Check if a phase has a user-defined affinity default.

        Args:
            phase_name: GEMS phase name

        Returns:
            True if user has defined affinities for this phase
        """
        try:
            from app.services.affinity_preferences_service import get_affinity_preferences_service
            return get_affinity_preferences_service().has_user_default(phase_name)
        except Exception:
            return False

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

        # Sulfate phases (including alkali sulfates Arcanite and Thenardite)
        if phase_name in self.STANDARD_DEFAULTS:
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

        If the override specifies 'type': 'Thermodynamic', returns None immediately
        (this allows users to explicitly disable kinetics even if defaults exist).

        If the phase has default kinetics, overlays the override on top.
        If the phase has NO default kinetics but the override specifies a 'type',
        creates kinetics from scratch using the override values (allowing users
        to add kinetics to phases that don't have them by default).

        Args:
            phase_name: GEMS phase name
            override: Dict of parameters to override (may include 'type' field)

        Returns:
            Kinetic parameters with overrides applied, or None if no kinetics
        """
        # Check for explicit Thermodynamic override FIRST - this takes precedence
        # over any defaults or user preferences
        kinetic_type = override.get('type')
        if kinetic_type == 'Thermodynamic':
            self.logger.debug(f"Phase {phase_name}: explicit Thermodynamic override, no kinetics")
            return None

        defaults = self.get_kinetics_for_phase(phase_name)

        if defaults is not None:
            # Phase has defaults - overlay the override
            return defaults.with_override(override)

        # Phase has NO default kinetics - check if override specifies a type
        # This allows users to add kinetics to phases that don't have them
        kinetic_type = override.get('type')
        if kinetic_type and kinetic_type != 'Thermodynamic':
            # Create kinetics from scratch using the override as the full specification
            # Get generic defaults for the specified type, then apply override
            if kinetic_type == 'ParrotKilloh':
                # Use Alite as generic default for ParrotKilloh
                generic_defaults = self.PARROT_KILLOH_DEFAULTS.get("Alite")
            elif kinetic_type == 'Standard':
                # Use Gypsum as generic default for Standard
                generic_defaults = self.STANDARD_DEFAULTS.get("Gypsum")
            elif kinetic_type == 'Pozzolanic':
                # Use Quartz as generic default for Pozzolanic
                generic_defaults = self.POZZOLANIC_DEFAULTS.get("Quartz")
            else:
                return None

            if generic_defaults:
                return generic_defaults.with_override(override)

        return None


# Module-level singleton
_kinetic_defaults_service: Optional[KineticDefaultsService] = None


def get_kinetic_defaults_service() -> KineticDefaultsService:
    """Get the singleton KineticDefaultsService instance."""
    global _kinetic_defaults_service
    if _kinetic_defaults_service is None:
        _kinetic_defaults_service = KineticDefaultsService()
    return _kinetic_defaults_service

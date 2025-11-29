#!/usr/bin/env python3
"""
Unit tests for KineticDefaultsService.

Tests the service that provides default kinetic parameters, impurity data,
and interface affinity data for THAMES phases.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.kinetic_defaults_service import (
    KineticDefaultsService,
    get_kinetic_defaults_service,
)
from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
)


class TestKineticDefaultsService:
    """Tests for KineticDefaultsService."""

    @pytest.fixture
    def service(self):
        """Create service instance for each test."""
        return KineticDefaultsService()

    # =========================================================================
    # Kinetics for Phase Tests
    # =========================================================================

    def test_get_kinetics_for_alite(self, service):
        """Test getting kinetics for Alite (clinker phase)."""
        kinetics = service.get_kinetics_for_phase("Alite")

        assert kinetics is not None
        assert isinstance(kinetics, ParrotKillohKinetics)
        assert kinetics.k1 == 1.5
        assert kinetics.k2 == 0.05
        assert kinetics.k3 == 1.1
        assert kinetics.n1 == 0.7
        assert kinetics.n3 == 3.3
        assert kinetics.dorHcoeff == 2.0
        assert kinetics.activationEnergy == 41570.0

    def test_get_kinetics_for_belite(self, service):
        """Test getting kinetics for Belite (clinker phase)."""
        kinetics = service.get_kinetics_for_phase("Belite")

        assert kinetics is not None
        assert isinstance(kinetics, ParrotKillohKinetics)
        assert kinetics.k1 == 0.5
        assert kinetics.n1 == 1.0
        assert kinetics.n3 == 5.0

    def test_get_kinetics_for_aluminate(self, service):
        """Test getting kinetics for Aluminate (clinker phase)."""
        kinetics = service.get_kinetics_for_phase("Aluminate")

        assert kinetics is not None
        assert isinstance(kinetics, ParrotKillohKinetics)
        assert kinetics.k1 == 1.0
        assert kinetics.n1 == 0.85

    def test_get_kinetics_for_ferrite(self, service):
        """Test getting kinetics for Ferrite (clinker phase)."""
        kinetics = service.get_kinetics_for_phase("Ferrite")

        assert kinetics is not None
        assert isinstance(kinetics, ParrotKillohKinetics)
        assert kinetics.k1 == 0.37

    def test_get_kinetics_for_gypsum(self, service):
        """Test getting kinetics for Gypsum (sulfate phase)."""
        kinetics = service.get_kinetics_for_phase("Gypsum")

        assert kinetics is not None
        assert isinstance(kinetics, StandardKinetics)
        assert kinetics.dissolutionRateConst == 1.0e-6
        assert kinetics.dissolvedUnits == 2

    def test_get_kinetics_for_hemihydrate(self, service):
        """Test getting kinetics for hemihydrate (sulfate phase)."""
        kinetics = service.get_kinetics_for_phase("hemihydrate")

        assert kinetics is not None
        assert isinstance(kinetics, StandardKinetics)
        assert kinetics.dissolutionRateConst == 1.5e-6

    def test_get_kinetics_for_anhydrite(self, service):
        """Test getting kinetics for Anhydrite (sulfate phase)."""
        kinetics = service.get_kinetics_for_phase("Anhydrite")

        assert kinetics is not None
        assert isinstance(kinetics, StandardKinetics)
        assert kinetics.dissolutionRateConst == 5.0e-7

    def test_get_kinetics_for_quartz(self, service):
        """Test getting kinetics for Quartz (pozzolanic phase)."""
        kinetics = service.get_kinetics_for_phase("Quartz")

        assert kinetics is not None
        assert isinstance(kinetics, PozzolanicKinetics)
        assert kinetics.dissolutionRateConst == 1.4e-11
        assert kinetics.ohexp == 1.0
        assert kinetics.sio2 == 0.987

    def test_get_kinetics_for_mullite(self, service):
        """Test getting kinetics for Mullite (pozzolanic phase)."""
        kinetics = service.get_kinetics_for_phase("Mullite")

        assert kinetics is not None
        assert isinstance(kinetics, PozzolanicKinetics)

    def test_get_kinetics_for_c2as_amorphous(self, service):
        """Test getting kinetics for C2AS(am) (fly ash glass)."""
        kinetics = service.get_kinetics_for_phase("C2AS(am)")

        assert kinetics is not None
        assert isinstance(kinetics, PozzolanicKinetics)
        assert kinetics.dissolutionRateConst == 1.39e-6
        assert kinetics.dissolvedUnits == 7

    def test_get_kinetics_for_unknown_phase(self, service):
        """Test that unknown phase returns None."""
        kinetics = service.get_kinetics_for_phase("Portlandite")
        assert kinetics is None

    def test_get_kinetics_for_electrolyte(self, service):
        """Test that Electrolyte returns None (no kinetics)."""
        kinetics = service.get_kinetics_for_phase("Electrolyte")
        assert kinetics is None

    # =========================================================================
    # Kinetic Type Tests
    # =========================================================================

    def test_get_kinetic_type_clinker(self, service):
        """Test kinetic type for clinker phases."""
        assert service.get_kinetic_type("Alite") == "ParrotKilloh"
        assert service.get_kinetic_type("Belite") == "ParrotKilloh"
        assert service.get_kinetic_type("Aluminate") == "ParrotKilloh"
        assert service.get_kinetic_type("Ferrite") == "ParrotKilloh"

    def test_get_kinetic_type_sulfate(self, service):
        """Test kinetic type for sulfate phases."""
        assert service.get_kinetic_type("Gypsum") == "Standard"
        assert service.get_kinetic_type("hemihydrate") == "Standard"
        assert service.get_kinetic_type("Anhydrite") == "Standard"

    def test_get_kinetic_type_pozzolanic(self, service):
        """Test kinetic type for pozzolanic phases."""
        assert service.get_kinetic_type("Quartz") == "Pozzolanic"
        assert service.get_kinetic_type("Mullite") == "Pozzolanic"
        assert service.get_kinetic_type("C2AS(am)") == "Pozzolanic"

    def test_get_kinetic_type_unknown(self, service):
        """Test kinetic type for unknown phase returns None."""
        assert service.get_kinetic_type("Portlandite") is None
        assert service.get_kinetic_type("CSHQ") is None

    # =========================================================================
    # Impurity Data Tests
    # =========================================================================

    def test_get_impurity_data_alite(self, service):
        """Test impurity data for Alite."""
        impurity = service.get_impurity_data("Alite")

        assert impurity is not None
        assert impurity["k2ocoeff"] == 0.00087
        assert impurity["na2ocoeff"] == 0.0
        assert impurity["mgocoeff"] == 0.00861
        assert impurity["so3coeff"] == 0.007942

    def test_get_impurity_data_belite(self, service):
        """Test impurity data for Belite."""
        impurity = service.get_impurity_data("Belite")

        assert impurity is not None
        assert impurity["k2ocoeff"] == 0.01152

    def test_get_impurity_data_ferrite(self, service):
        """Test impurity data for Ferrite."""
        impurity = service.get_impurity_data("Ferrite")

        assert impurity is not None
        assert impurity["mgocoeff"] == 0.02292  # Ferrite has highest MgO

    def test_get_impurity_data_quartz(self, service):
        """Test impurity data for Quartz (minimal impurities)."""
        impurity = service.get_impurity_data("Quartz")

        assert impurity is not None
        assert impurity["k2ocoeff"] == 0.0
        assert impurity["mgocoeff"] == 0.001

    def test_get_impurity_data_unknown(self, service):
        """Test impurity data for unknown phase returns None."""
        impurity = service.get_impurity_data("Portlandite")
        assert impurity is None

    # =========================================================================
    # Interface Affinity Tests
    # =========================================================================

    def test_get_interface_affinity_cshq(self, service):
        """Test interface affinity for CSHQ."""
        affinity = service.get_interface_affinity("CSHQ")

        assert affinity is not None
        assert len(affinity) == 3

        # Check specific affinities
        alite_affinity = next((a for a in affinity if a["affinityphase"] == "Alite"), None)
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 30

        portlandite_affinity = next((a for a in affinity if a["affinityphase"] == "Portlandite"), None)
        assert portlandite_affinity is not None
        assert portlandite_affinity["contactanglevalue"] == 0  # High affinity

    def test_get_interface_affinity_portlandite(self, service):
        """Test interface affinity for Portlandite."""
        affinity = service.get_interface_affinity("Portlandite")

        assert affinity is not None

        # Portlandite avoids clinker
        alite_affinity = next((a for a in affinity if a["affinityphase"] == "Alite"), None)
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 180  # Low affinity

    def test_get_interface_affinity_ettr(self, service):
        """Test interface affinity for ettringite."""
        affinity = service.get_interface_affinity("ettr")

        assert affinity is not None
        assert len(affinity) > 5  # Multiple affinities defined

    def test_get_interface_affinity_unknown(self, service):
        """Test interface affinity for unknown phase returns None."""
        affinity = service.get_interface_affinity("UnknownPhase")
        assert affinity is None

    # =========================================================================
    # Cement Component Tests
    # =========================================================================

    def test_is_cement_component_clinker(self, service):
        """Test cement component identification for clinker phases."""
        assert service.is_cement_component("Alite") is True
        assert service.is_cement_component("Belite") is True
        assert service.is_cement_component("Aluminate") is True
        assert service.is_cement_component("Ferrite") is True

    def test_is_cement_component_sulfates(self, service):
        """Test cement component identification for sulfate phases."""
        assert service.is_cement_component("Gypsum") is True
        assert service.is_cement_component("hemihydrate") is True
        assert service.is_cement_component("Anhydrite") is True

    def test_is_cement_component_alkali_sulfates(self, service):
        """Test cement component identification for alkali sulfates."""
        assert service.is_cement_component("Arcanite") is True
        assert service.is_cement_component("Thenardite") is True

    def test_is_cement_component_pozzolans(self, service):
        """Test that pozzolans are NOT cement components."""
        assert service.is_cement_component("Quartz") is False
        assert service.is_cement_component("Mullite") is False

    def test_is_cement_component_hydration_products(self, service):
        """Test that hydration products are NOT cement components."""
        assert service.is_cement_component("Portlandite") is False
        assert service.is_cement_component("CSHQ") is False
        assert service.is_cement_component("ettr") is False

    # =========================================================================
    # Phase List Tests
    # =========================================================================

    def test_get_all_clinker_phases(self, service):
        """Test getting all clinker phase names."""
        clinker = service.get_all_clinker_phases()

        assert "Alite" in clinker
        assert "Belite" in clinker
        assert "Aluminate" in clinker
        assert "Ferrite" in clinker
        assert len(clinker) == 4

    def test_get_all_sulfate_phases(self, service):
        """Test getting all sulfate phase names."""
        sulfates = service.get_all_sulfate_phases()

        assert "Gypsum" in sulfates
        assert "hemihydrate" in sulfates
        assert "Anhydrite" in sulfates
        assert len(sulfates) == 3

    def test_get_all_pozzolanic_phases(self, service):
        """Test getting all pozzolanic phase names."""
        pozzolans = service.get_all_pozzolanic_phases()

        assert "Quartz" in pozzolans
        assert "Mullite" in pozzolans
        assert "C2AS(am)" in pozzolans
        assert len(pozzolans) >= 5  # At least the main ones

    # =========================================================================
    # Override Tests
    # =========================================================================

    def test_get_kinetics_with_override(self, service):
        """Test getting kinetics with user overrides."""
        kinetics = service.get_kinetics_with_override("Alite", {"k1": 2.0})

        assert kinetics is not None
        assert isinstance(kinetics, ParrotKillohKinetics)
        assert kinetics.k1 == 2.0  # Overridden
        assert kinetics.k2 == 0.05  # Default preserved

    def test_get_kinetics_with_multiple_overrides(self, service):
        """Test getting kinetics with multiple overrides."""
        kinetics = service.get_kinetics_with_override(
            "Gypsum",
            {"dissolutionRateConst": 2.0e-6, "activationEnergy": 45000.0}
        )

        assert kinetics is not None
        assert kinetics.dissolutionRateConst == 2.0e-6
        assert kinetics.activationEnergy == 45000.0
        assert kinetics.dissolvedUnits == 2  # Default preserved

    def test_get_kinetics_with_override_unknown_phase(self, service):
        """Test that override for unknown phase returns None."""
        kinetics = service.get_kinetics_with_override("Portlandite", {"k1": 2.0})
        assert kinetics is None

    # =========================================================================
    # Singleton Tests
    # =========================================================================

    def test_singleton_pattern(self):
        """Test that get_kinetic_defaults_service returns same instance."""
        service1 = get_kinetic_defaults_service()
        service2 = get_kinetic_defaults_service()

        assert service1 is service2

    # =========================================================================
    # Serialization Tests (kinetics to dict)
    # =========================================================================

    def test_clinker_kinetics_to_dict_format(self, service):
        """Test that clinker kinetics serializes to correct format."""
        kinetics = service.get_kinetics_for_phase("Alite")
        d = kinetics.to_dict()

        # Check all required fields for simparams.json
        assert "type" in d
        assert d["type"] == "ParrotKilloh"
        assert "k1" in d
        assert "k2" in d
        assert "k3" in d
        assert "n1" in d
        assert "n3" in d
        assert "dorHcoeff" in d
        assert "activationEnergy" in d
        assert "loi" in d

    def test_sulfate_kinetics_to_dict_format(self, service):
        """Test that sulfate kinetics serializes to correct format."""
        kinetics = service.get_kinetics_for_phase("Gypsum")
        d = kinetics.to_dict()

        assert "type" in d
        assert d["type"] == "Standard"
        assert "dissolutionRateConst" in d
        assert "diffusionRateConstEarly" in d
        assert "diffusionRateConstLate" in d
        assert "dissolvedUnits" in d
        assert "siexp" in d
        assert "dfexp" in d
        assert "dorexp" in d
        assert "activationEnergy" in d
        assert "loi" in d

    def test_pozzolanic_kinetics_to_dict_format(self, service):
        """Test that pozzolanic kinetics serializes to correct format."""
        kinetics = service.get_kinetics_for_phase("Quartz")
        d = kinetics.to_dict()

        assert "type" in d
        assert d["type"] == "Pozzolanic"
        assert "ohexp" in d
        assert "sio2" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

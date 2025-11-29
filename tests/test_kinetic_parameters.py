#!/usr/bin/env python3
"""
Unit tests for kinetic parameter data classes.

Tests the ParrotKillohKinetics, StandardKinetics, and PozzolanicKinetics
dataclasses for proper validation, serialization, and deserialization.
"""

import pytest
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
    kinetics_from_dict,
    get_kinetic_type_name,
)


class TestParrotKillohKinetics:
    """Tests for ParrotKillohKinetics dataclass."""

    def test_create_valid_instance(self):
        """Test creating instance with valid parameters."""
        pk = ParrotKillohKinetics(
            k1=1.5,
            k2=0.05,
            k3=1.1,
            n1=0.7,
            n3=3.3,
            dorHcoeff=2.0,
            activationEnergy=41570.0,
            loi=0.0
        )
        assert pk.k1 == 1.5
        assert pk.k2 == 0.05
        assert pk.k3 == 1.1
        assert pk.n1 == 0.7
        assert pk.n3 == 3.3
        assert pk.dorHcoeff == 2.0
        assert pk.activationEnergy == 41570.0
        assert pk.loi == 0.0

    def test_default_loi(self):
        """Test that loi defaults to 0.0."""
        pk = ParrotKillohKinetics(
            k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
            dorHcoeff=2.0, activationEnergy=41570.0
        )
        assert pk.loi == 0.0

    def test_validation_negative_k1(self):
        """Test validation rejects negative k1."""
        with pytest.raises(ValueError, match="k1 must be non-negative"):
            ParrotKillohKinetics(
                k1=-1.0, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
                dorHcoeff=2.0, activationEnergy=41570.0
            )

    def test_validation_negative_n1(self):
        """Test validation rejects non-positive n1."""
        with pytest.raises(ValueError, match="n1 must be positive"):
            ParrotKillohKinetics(
                k1=1.5, k2=0.05, k3=1.1, n1=0.0, n3=3.3,
                dorHcoeff=2.0, activationEnergy=41570.0
            )

    def test_validation_invalid_loi(self):
        """Test validation rejects negative loi."""
        with pytest.raises(ValueError, match="loi must be non-negative"):
            ParrotKillohKinetics(
                k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
                dorHcoeff=2.0, activationEnergy=41570.0, loi=-0.5
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pk = ParrotKillohKinetics(
            k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
            dorHcoeff=2.0, activationEnergy=41570.0, loi=0.0
        )
        d = pk.to_dict()

        assert d["type"] == "ParrotKilloh"
        assert d["k1"] == 1.5
        assert d["k2"] == 0.05
        assert d["k3"] == 1.1
        assert d["n1"] == 0.7
        assert d["n3"] == 3.3
        assert d["dorHcoeff"] == 2.0
        assert d["activationEnergy"] == 41570.0
        assert d["loi"] == 0.0

    def test_to_json(self):
        """Test JSON serialization."""
        pk = ParrotKillohKinetics(
            k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
            dorHcoeff=2.0, activationEnergy=41570.0
        )
        json_str = pk.to_json()

        # Parse and verify
        parsed = json.loads(json_str)
        assert parsed["type"] == "ParrotKilloh"
        assert parsed["k1"] == 1.5

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "type": "ParrotKilloh",
            "k1": 1.5,
            "k2": 0.05,
            "k3": 1.1,
            "n1": 0.7,
            "n3": 3.3,
            "dorHcoeff": 2.0,
            "activationEnergy": 41570.0,
            "loi": 0.0
        }
        pk = ParrotKillohKinetics.from_dict(d)

        assert pk.k1 == 1.5
        assert pk.activationEnergy == 41570.0

    def test_from_dict_without_type(self):
        """Test from_dict handles missing type field."""
        d = {
            "k1": 1.5,
            "k2": 0.05,
            "k3": 1.1,
            "n1": 0.7,
            "n3": 3.3,
            "dorHcoeff": 2.0,
            "activationEnergy": 41570.0,
            "loi": 0.0
        }
        pk = ParrotKillohKinetics.from_dict(d)
        assert pk.k1 == 1.5

    def test_with_override(self):
        """Test creating copy with overridden values."""
        pk = ParrotKillohKinetics(
            k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
            dorHcoeff=2.0, activationEnergy=41570.0
        )
        pk2 = pk.with_override({"k1": 2.0, "activationEnergy": 50000.0})

        # Original unchanged
        assert pk.k1 == 1.5
        assert pk.activationEnergy == 41570.0

        # New instance has overrides
        assert pk2.k1 == 2.0
        assert pk2.activationEnergy == 50000.0

        # Other values preserved
        assert pk2.k2 == 0.05
        assert pk2.n1 == 0.7

    def test_roundtrip(self):
        """Test dict -> instance -> dict roundtrip."""
        original = {
            "type": "ParrotKilloh",
            "k1": 1.5,
            "k2": 0.05,
            "k3": 1.1,
            "n1": 0.7,
            "n3": 3.3,
            "dorHcoeff": 2.0,
            "activationEnergy": 41570.0,
            "loi": 0.0
        }
        pk = ParrotKillohKinetics.from_dict(original)
        result = pk.to_dict()

        assert result == original


class TestStandardKinetics:
    """Tests for StandardKinetics dataclass."""

    def test_create_valid_instance(self):
        """Test creating instance with valid parameters."""
        sk = StandardKinetics(
            dissolutionRateConst=1.0e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0,
            loi=0.0
        )
        assert sk.dissolutionRateConst == 1.0e-6
        assert sk.dissolvedUnits == 2
        assert sk.siexp == 1.0

    def test_validation_negative_dissolution_rate(self):
        """Test validation rejects negative dissolution rate."""
        with pytest.raises(ValueError, match="dissolutionRateConst must be non-negative"):
            StandardKinetics(
                dissolutionRateConst=-1.0e-6,
                diffusionRateConstEarly=5.0e-6,
                diffusionRateConstLate=5.0e-6,
                dissolvedUnits=2,
                siexp=1.0,
                dfexp=1.1,
                dorexp=0.5,
                activationEnergy=40000.0
            )

    def test_validation_dissolved_units_minimum(self):
        """Test validation requires dissolvedUnits >= 1."""
        with pytest.raises(ValueError, match="dissolvedUnits must be at least 1"):
            StandardKinetics(
                dissolutionRateConst=1.0e-6,
                diffusionRateConstEarly=5.0e-6,
                diffusionRateConstLate=5.0e-6,
                dissolvedUnits=0,
                siexp=1.0,
                dfexp=1.1,
                dorexp=0.5,
                activationEnergy=40000.0
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        sk = StandardKinetics(
            dissolutionRateConst=1.0e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0
        )
        d = sk.to_dict()

        assert d["type"] == "Standard"
        assert d["dissolutionRateConst"] == 1.0e-6
        assert d["dissolvedUnits"] == 2

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "type": "Standard",
            "dissolutionRateConst": 1.0e-6,
            "diffusionRateConstEarly": 5.0e-6,
            "diffusionRateConstLate": 5.0e-6,
            "dissolvedUnits": 2,
            "siexp": 1.0,
            "dfexp": 1.1,
            "dorexp": 0.5,
            "activationEnergy": 40000.0,
            "loi": 0.0
        }
        sk = StandardKinetics.from_dict(d)
        assert sk.dissolutionRateConst == 1.0e-6


class TestPozzolanicKinetics:
    """Tests for PozzolanicKinetics dataclass."""

    def test_create_valid_instance(self):
        """Test creating instance with valid parameters."""
        pk = PozzolanicKinetics(
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
        )
        assert pk.dissolutionRateConst == 1.4e-11
        assert pk.ohexp == 1.0
        assert pk.sio2 == 0.987

    def test_validation_invalid_sio2(self):
        """Test validation rejects sio2 outside [0, 1]."""
        with pytest.raises(ValueError, match="sio2 must be between 0 and 1"):
            PozzolanicKinetics(
                dissolutionRateConst=1.4e-11,
                diffusionRateConstEarly=2.8e-12,
                diffusionRateConstLate=2.8e-12,
                dissolvedUnits=1,
                siexp=1.0,
                dfexp=1.0,
                dorexp=0.5,
                ohexp=1.0,
                sio2=1.5,  # Invalid
                activationEnergy=40000.0
            )

    def test_to_dict(self):
        """Test conversion to dictionary."""
        pk = PozzolanicKinetics(
            dissolutionRateConst=1.4e-11,
            diffusionRateConstEarly=2.8e-12,
            diffusionRateConstLate=2.8e-12,
            dissolvedUnits=1,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0
        )
        d = pk.to_dict()

        assert d["type"] == "Pozzolanic"
        assert d["ohexp"] == 1.0
        assert d["sio2"] == 0.987

    def test_from_dict(self):
        """Test creation from dictionary."""
        d = {
            "type": "Pozzolanic",
            "dissolutionRateConst": 1.4e-11,
            "diffusionRateConstEarly": 2.8e-12,
            "diffusionRateConstLate": 2.8e-12,
            "dissolvedUnits": 1,
            "siexp": 1.0,
            "dfexp": 1.0,
            "dorexp": 0.5,
            "ohexp": 1.0,
            "sio2": 0.987,
            "activationEnergy": 40000.0,
            "loi": 1.3
        }
        pk = PozzolanicKinetics.from_dict(d)
        assert pk.sio2 == 0.987
        assert pk.ohexp == 1.0


class TestKineticsFromDict:
    """Tests for the kinetics_from_dict factory function."""

    def test_parrot_killoh(self):
        """Test parsing ParrotKilloh type."""
        d = {
            "type": "ParrotKilloh",
            "k1": 1.5,
            "k2": 0.05,
            "k3": 1.1,
            "n1": 0.7,
            "n3": 3.3,
            "dorHcoeff": 2.0,
            "activationEnergy": 41570.0,
            "loi": 0.0
        }
        result = kinetics_from_dict(d)
        assert isinstance(result, ParrotKillohKinetics)
        assert result.k1 == 1.5

    def test_standard(self):
        """Test parsing Standard type."""
        d = {
            "type": "Standard",
            "dissolutionRateConst": 1.0e-6,
            "diffusionRateConstEarly": 5.0e-6,
            "diffusionRateConstLate": 5.0e-6,
            "dissolvedUnits": 2,
            "siexp": 1.0,
            "dfexp": 1.1,
            "dorexp": 0.5,
            "activationEnergy": 40000.0,
            "loi": 0.0
        }
        result = kinetics_from_dict(d)
        assert isinstance(result, StandardKinetics)

    def test_pozzolanic(self):
        """Test parsing Pozzolanic type."""
        d = {
            "type": "Pozzolanic",
            "dissolutionRateConst": 1.4e-11,
            "diffusionRateConstEarly": 2.8e-12,
            "diffusionRateConstLate": 2.8e-12,
            "dissolvedUnits": 1,
            "siexp": 1.0,
            "dfexp": 1.0,
            "dorexp": 0.5,
            "ohexp": 1.0,
            "sio2": 0.987,
            "activationEnergy": 40000.0,
            "loi": 1.3
        }
        result = kinetics_from_dict(d)
        assert isinstance(result, PozzolanicKinetics)

    def test_unknown_type(self):
        """Test that unknown type returns None."""
        d = {"type": "Unknown", "param": 1.0}
        result = kinetics_from_dict(d)
        assert result is None

    def test_missing_type(self):
        """Test that missing type returns None."""
        d = {"param": 1.0}
        result = kinetics_from_dict(d)
        assert result is None


class TestGetKineticTypeName:
    """Tests for get_kinetic_type_name function."""

    def test_parrot_killoh(self):
        """Test type name for ParrotKillohKinetics."""
        pk = ParrotKillohKinetics(
            k1=1.5, k2=0.05, k3=1.1, n1=0.7, n3=3.3,
            dorHcoeff=2.0, activationEnergy=41570.0
        )
        assert get_kinetic_type_name(pk) == "ParrotKilloh"

    def test_standard(self):
        """Test type name for StandardKinetics."""
        sk = StandardKinetics(
            dissolutionRateConst=1.0e-6,
            diffusionRateConstEarly=5.0e-6,
            diffusionRateConstLate=5.0e-6,
            dissolvedUnits=2,
            siexp=1.0,
            dfexp=1.1,
            dorexp=0.5,
            activationEnergy=40000.0
        )
        assert get_kinetic_type_name(sk) == "Standard"

    def test_pozzolanic(self):
        """Test type name for PozzolanicKinetics."""
        pk = PozzolanicKinetics(
            dissolutionRateConst=1.4e-11,
            diffusionRateConstEarly=2.8e-12,
            diffusionRateConstLate=2.8e-12,
            dissolvedUnits=1,
            siexp=1.0,
            dfexp=1.0,
            dorexp=0.5,
            ohexp=1.0,
            sio2=0.987,
            activationEnergy=40000.0
        )
        assert get_kinetic_type_name(pk) == "Pozzolanic"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

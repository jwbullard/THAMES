#!/usr/bin/env python3
"""
Unit tests for SimParamsService and PhaseDataBuilder.

Tests the service that generates simparams.json files for THAMES-Hydration.
"""

import pytest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.simparams_service import (
    SimParamsService,
    PhaseDataBuilder,
    EnvironmentConfig,
    TimeConfig,
    DEFAULT_ELECTROLYTE_CONDITIONS,
    get_simparams_service,
)
from app.services.phase_id_mapping_service import PhaseIdMapping, VOIDID, ELECTROLYTEID
from app.services.kinetic_defaults_service import KineticDefaultsService
from app.services.phase_color_service import PhaseColorService
from app.models.kinetic_parameters import ParrotKillohKinetics, StandardKinetics


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_gems_parser():
    """Create a mock GEMS parser service."""
    parser = Mock()

    # Mock phase data
    mock_alite_phase = Mock()
    mock_alite_phase.dc_names = ["C3S"]

    mock_gypsum_phase = Mock()
    mock_gypsum_phase.dc_names = ["Gp"]

    mock_electrolyte_phase = Mock()
    mock_electrolyte_phase.dc_names = [
        "Ca+2", "OH-", "H2O@", "K+", "Na+", "SO4-2"
    ]

    mock_cshq_phase = Mock()
    mock_cshq_phase.dc_names = [
        "CSHQ-JenD", "CSHQ-JenH", "CSHQ-TobD", "CSHQ-TobH", "KSiOH", "NaSiOH"
    ]

    def get_phase(name):
        phases = {
            "Alite": mock_alite_phase,
            "Gypsum": mock_gypsum_phase,
            "Electrolyte": mock_electrolyte_phase,
            "aq_gen": mock_electrolyte_phase,
            "CSHQ": mock_cshq_phase,
        }
        return phases.get(name)

    parser.get_phase = get_phase
    return parser


@pytest.fixture
def kinetic_defaults():
    """Create a KineticDefaultsService instance."""
    return KineticDefaultsService()


@pytest.fixture
def phase_color_service():
    """Create a PhaseColorService instance."""
    return PhaseColorService()


@pytest.fixture
def phase_builder(mock_gems_parser, kinetic_defaults, phase_color_service):
    """Create a PhaseDataBuilder instance."""
    return PhaseDataBuilder(mock_gems_parser, kinetic_defaults, phase_color_service)


@pytest.fixture
def simparams_service(mock_gems_parser, kinetic_defaults, phase_color_service):
    """Create a SimParamsService instance."""
    return SimParamsService(mock_gems_parser, kinetic_defaults, phase_color_service)


@pytest.fixture
def sample_phase_id_mapping():
    """Create a sample phase ID mapping."""
    mapping = PhaseIdMapping()
    mapping.gem_to_micro = {
        "VOID": 0,
        "Electrolyte": 1,
        "Alite": 2,
        "Belite": 3,
        "Aluminate": 4,
        "Ferrite": 5,
        "Arcanite": 6,
        "Thenardite": 7,
        "AGGREGATE": 8,
        "Gypsum": 9,
    }
    mapping.micro_to_gem = {v: k for k, v in mapping.gem_to_micro.items()}
    mapping.has_clinker = True
    mapping.next_available_id = 10
    return mapping


# =============================================================================
# PhaseDataBuilder Tests
# =============================================================================

class TestPhaseDataBuilder:
    """Tests for PhaseDataBuilder class."""

    def test_build_phase_entry_alite(self, phase_builder):
        """Test building phase entry for Alite (clinker phase)."""
        entry = phase_builder.build_phase_entry(
            thamesname="Alite",
            phase_id=2,
            gemphasename="Alite",
            is_cement_component=True
        )

        assert entry["thamesname"] == "Alite"
        assert entry["id"] == 2
        assert entry["cement_component"] == 1

        # Should have gemphase_data
        assert "gemphase_data" in entry
        assert entry["gemphase_data"][0]["gemphasename"] == "Alite"
        assert entry["gemphase_data"][0]["gemdc"][0]["gemdcname"] == "C3S"

        # Should have kinetic_data (ParrotKilloh)
        assert "kinetic_data" in entry
        assert entry["kinetic_data"]["type"] == "ParrotKilloh"
        assert "k1" in entry["kinetic_data"]
        assert "n1" in entry["kinetic_data"]

        # Should have impurity_data
        assert "impurity_data" in entry
        assert "k2ocoeff" in entry["impurity_data"]

        # Should have display_data
        assert "display_data" in entry
        assert "red" in entry["display_data"]
        assert "green" in entry["display_data"]
        assert "blue" in entry["display_data"]

    def test_build_phase_entry_gypsum(self, phase_builder):
        """Test building phase entry for Gypsum (sulfate phase)."""
        entry = phase_builder.build_phase_entry(
            thamesname="Gypsum",
            phase_id=9,
            gemphasename="Gypsum",
            is_cement_component=True
        )

        assert entry["thamesname"] == "Gypsum"
        assert entry["id"] == 9
        assert entry["cement_component"] == 1

        # Should have kinetic_data (Standard)
        assert "kinetic_data" in entry
        assert entry["kinetic_data"]["type"] == "Standard"
        assert "dissolutionRateConst" in entry["kinetic_data"]
        assert "dissolvedUnits" in entry["kinetic_data"]

    def test_build_phase_entry_void(self, phase_builder):
        """Test building phase entry for VOID."""
        entry = phase_builder.build_phase_entry(
            thamesname="Void",
            phase_id=0,
            gemphasename="VOID",
            is_cement_component=False
        )

        assert entry["thamesname"] == "Void"
        assert entry["id"] == 0
        assert entry["cement_component"] == 0

        # VOID should NOT have gemphase_data
        assert "gemphase_data" not in entry

        # VOID should NOT have kinetic_data
        assert "kinetic_data" not in entry

    def test_build_phase_entry_with_kinetic_override(self, phase_builder):
        """Test building phase entry with kinetic parameter override."""
        override = {"k1": 2.5, "activationEnergy": 50000.0}

        entry = phase_builder.build_phase_entry(
            thamesname="Alite",
            phase_id=2,
            gemphasename="Alite",
            is_cement_component=True,
            kinetic_override=override
        )

        assert entry["kinetic_data"]["k1"] == 2.5
        assert entry["kinetic_data"]["activationEnergy"] == 50000.0
        # Other parameters should still be defaults
        assert entry["kinetic_data"]["n1"] == 0.7

    def test_build_gemphase_data_alite(self, phase_builder):
        """Test building gemphase_data for Alite."""
        gemphase_data = phase_builder.build_gemphase_data("Alite")

        assert gemphase_data is not None
        assert len(gemphase_data) == 1
        assert gemphase_data[0]["gemphasename"] == "Alite"
        assert gemphase_data[0]["gemdc"][0]["gemdcname"] == "C3S"

    def test_build_gemphase_data_void(self, phase_builder):
        """Test that VOID returns None for gemphase_data."""
        gemphase_data = phase_builder.build_gemphase_data("VOID")
        assert gemphase_data is None

    def test_build_gemphase_data_cshq_porosity(self, phase_builder):
        """Test that C-S-H DCs have porosity values."""
        gemphase_data = phase_builder.build_gemphase_data("CSHQ")

        assert gemphase_data is not None
        dc_list = gemphase_data[0]["gemdc"]

        # Find the JenD entry and check porosity
        jend_dc = next((dc for dc in dc_list if dc["gemdcname"] == "CSHQ-JenD"), None)
        assert jend_dc is not None
        assert "gemdcporosity" in jend_dc
        assert abs(jend_dc["gemdcporosity"] - 0.4935) < 0.001

    def test_build_kinetic_data_parrotkilloh(self, phase_builder):
        """Test building kinetic data for Parrot-Killoh phase."""
        kinetic_data = phase_builder.build_kinetic_data("Alite")

        assert kinetic_data is not None
        assert kinetic_data["type"] == "ParrotKilloh"
        assert kinetic_data["k1"] == 1.5
        assert kinetic_data["k2"] == 0.05
        assert kinetic_data["k3"] == 1.1
        assert kinetic_data["n1"] == 0.7
        assert kinetic_data["n3"] == 3.3

    def test_build_kinetic_data_standard(self, phase_builder):
        """Test building kinetic data for Standard phase."""
        kinetic_data = phase_builder.build_kinetic_data("Gypsum")

        assert kinetic_data is not None
        assert kinetic_data["type"] == "Standard"
        assert kinetic_data["dissolutionRateConst"] == 1.0e-6
        assert kinetic_data["dissolvedUnits"] == 2

    def test_build_kinetic_data_unknown_phase(self, phase_builder):
        """Test that unknown phase returns None for kinetic data."""
        kinetic_data = phase_builder.build_kinetic_data("Portlandite")
        assert kinetic_data is None

    def test_build_impurity_data(self, phase_builder):
        """Test building impurity data."""
        impurity_data = phase_builder.build_impurity_data("Alite")

        assert impurity_data is not None
        assert impurity_data["k2ocoeff"] == 0.00087
        assert impurity_data["mgocoeff"] == 0.00861
        assert impurity_data["so3coeff"] == 0.007942

    def test_build_interface_data_cshq(self, phase_builder):
        """Test building interface data for C-S-H."""
        interface_data = phase_builder.build_interface_data("CSHQ")

        assert interface_data is not None
        assert "affinity" in interface_data
        assert len(interface_data["affinity"]) > 0

        # Check for Alite affinity
        alite_affinity = next(
            (a for a in interface_data["affinity"] if a["affinityphase"] == "Alite"),
            None
        )
        assert alite_affinity is not None
        assert alite_affinity["contactanglevalue"] == 30


# =============================================================================
# SimParamsService Tests
# =============================================================================

class TestSimParamsService:
    """Tests for SimParamsService class."""

    def test_generate_simparams_basic(self, simparams_service, sample_phase_id_mapping):
        """Test basic simparams generation."""
        material_phases = [
            {
                "material_name": "Test Cement",
                "is_cement_component": True,
                "phases": [
                    {"gem_phase_name": "Alite", "mass_fraction": 0.60},
                    {"gem_phase_name": "Gypsum", "mass_fraction": 0.05},
                ]
            }
        ]

        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=material_phases
        )

        # Check top-level structure
        assert "environment" in simparams
        assert "microstructure" in simparams
        assert "time_parameters" in simparams

    def test_environment_section_defaults(self, simparams_service, sample_phase_id_mapping):
        """Test environment section with defaults."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        env = simparams["environment"]
        assert env["temperature"] == 298.15
        assert env["reftemperature"] == 298.15
        assert env["saturated"] == 1
        assert "electrolyte_conditions" in env
        assert len(env["electrolyte_conditions"]) == len(DEFAULT_ELECTROLYTE_CONDITIONS)

    def test_environment_section_custom(self, simparams_service, sample_phase_id_mapping):
        """Test environment section with custom config."""
        config = EnvironmentConfig(
            temperature=333.15,
            saturated=0,
            electrolyte_conditions=[
                {"DCname": "K+", "condition": "initial", "concentration": 5.0e-6}
            ]
        )

        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[],
            environment_config=config
        )

        env = simparams["environment"]
        assert env["temperature"] == 333.15
        assert env["saturated"] == 0
        assert len(env["electrolyte_conditions"]) == 1

    def test_time_parameters_defaults(self, simparams_service, sample_phase_id_mapping):
        """Test time parameters with defaults."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        time_params = simparams["time_parameters"]
        assert time_params["finaltime"] == 28.0
        assert 0.01 in time_params["outtimes"]
        assert 28 in time_params["outtimes"]

    def test_time_parameters_custom(self, simparams_service, sample_phase_id_mapping):
        """Test time parameters with custom config."""
        config = TimeConfig(
            finaltime=56.0,
            outtimes=[1, 7, 14, 28, 56]
        )

        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[],
            time_config=config
        )

        time_params = simparams["time_parameters"]
        assert time_params["finaltime"] == 56.0
        assert time_params["outtimes"] == [1, 7, 14, 28, 56]

    def test_microstructure_section_phase_count(self, simparams_service, sample_phase_id_mapping):
        """Test that microstructure section has correct phase count."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        micro = simparams["microstructure"]
        assert micro["numentries"] == len(sample_phase_id_mapping.micro_to_gem)
        assert len(micro["phases"]) == micro["numentries"]

    def test_microstructure_phase_ids_sequential(self, simparams_service, sample_phase_id_mapping):
        """Test that phases are sorted by ID."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        phases = simparams["microstructure"]["phases"]
        ids = [p["id"] for p in phases]
        assert ids == sorted(ids)

    def test_void_phase_present(self, simparams_service, sample_phase_id_mapping):
        """Test that VOID phase is present."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        phases = simparams["microstructure"]["phases"]
        void_phase = next((p for p in phases if p["id"] == VOIDID), None)

        assert void_phase is not None
        assert void_phase["thamesname"] == "Void"
        assert void_phase["cement_component"] == 0

    def test_electrolyte_phase_present(self, simparams_service, sample_phase_id_mapping):
        """Test that Electrolyte phase is present."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        phases = simparams["microstructure"]["phases"]
        electrolyte_phase = next((p for p in phases if p["id"] == ELECTROLYTEID), None)

        assert electrolyte_phase is not None
        assert electrolyte_phase["thamesname"] == "Electrolyte"

    def test_kinetic_overrides_applied(self, simparams_service, sample_phase_id_mapping):
        """Test that kinetic overrides are applied."""
        overrides = {
            "Alite": {"k1": 2.0, "activationEnergy": 45000.0}
        }

        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[],
            kinetic_overrides=overrides
        )

        phases = simparams["microstructure"]["phases"]
        alite_phase = next((p for p in phases if p["thamesname"] == "Alite"), None)

        assert alite_phase is not None
        assert alite_phase["kinetic_data"]["k1"] == 2.0
        assert alite_phase["kinetic_data"]["activationEnergy"] == 45000.0

    def test_thamesname_mapping(self, simparams_service):
        """Test GEMS to THAMES name mapping."""
        assert simparams_service._get_thamesname("hemihydrate") == "Bassanite"
        assert simparams_service._get_thamesname("C2AS(am)") == "C2AS"
        assert simparams_service._get_thamesname("hydrotalc-pyro") == "Hydrotalcite"
        assert simparams_service._get_thamesname("Alite") == "Alite"  # No mapping


# =============================================================================
# Validation Tests
# =============================================================================

class TestSimParamsValidation:
    """Tests for simparams validation."""

    def test_validate_valid_simparams(self, simparams_service, sample_phase_id_mapping):
        """Test validation of valid simparams."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert is_valid
        assert len(errors) == 0

    def test_validate_missing_environment(self, simparams_service):
        """Test validation catches missing environment section."""
        simparams = {
            "microstructure": {"numentries": 0, "phases": []},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("environment" in e for e in errors)

    def test_validate_missing_microstructure(self, simparams_service):
        """Test validation catches missing microstructure section."""
        simparams = {
            "environment": {"temperature": 298.15, "saturated": 1},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("microstructure" in e for e in errors)

    def test_validate_invalid_temperature(self, simparams_service):
        """Test validation catches invalid temperature."""
        simparams = {
            "environment": {"temperature": -10, "saturated": 1},
            "microstructure": {"numentries": 2, "phases": [
                {"thamesname": "Void", "id": 0, "cement_component": 0},
                {"thamesname": "Electrolyte", "id": 1, "cement_component": 0}
            ]},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("temperature" in e for e in errors)

    def test_validate_invalid_saturated(self, simparams_service):
        """Test validation catches invalid saturated value."""
        simparams = {
            "environment": {"temperature": 298.15, "saturated": 2},
            "microstructure": {"numentries": 2, "phases": [
                {"thamesname": "Void", "id": 0, "cement_component": 0},
                {"thamesname": "Electrolyte", "id": 1, "cement_component": 0}
            ]},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("saturated" in e for e in errors)

    def test_validate_duplicate_phase_id(self, simparams_service):
        """Test validation catches duplicate phase IDs."""
        simparams = {
            "environment": {"temperature": 298.15, "saturated": 1},
            "microstructure": {"numentries": 3, "phases": [
                {"thamesname": "Void", "id": 0, "cement_component": 0},
                {"thamesname": "Electrolyte", "id": 1, "cement_component": 0},
                {"thamesname": "Duplicate", "id": 1, "cement_component": 0}  # Duplicate ID
            ]},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("Duplicate phase ID" in e for e in errors)

    def test_validate_missing_void_phase(self, simparams_service):
        """Test validation catches missing VOID phase."""
        simparams = {
            "environment": {"temperature": 298.15, "saturated": 1},
            "microstructure": {"numentries": 1, "phases": [
                {"thamesname": "Electrolyte", "id": 1, "cement_component": 0}
            ]},
            "time_parameters": {"finaltime": 28, "outtimes": [1, 7, 28]}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("VOID" in e for e in errors)

    def test_validate_empty_outtimes(self, simparams_service):
        """Test validation catches empty outtimes."""
        simparams = {
            "environment": {"temperature": 298.15, "saturated": 1},
            "microstructure": {"numentries": 2, "phases": [
                {"thamesname": "Void", "id": 0, "cement_component": 0},
                {"thamesname": "Electrolyte", "id": 1, "cement_component": 0}
            ]},
            "time_parameters": {"finaltime": 28, "outtimes": []}
        }

        is_valid, errors = simparams_service.validate_simparams(simparams)
        assert not is_valid
        assert any("outtimes" in e for e in errors)


# =============================================================================
# File I/O Tests
# =============================================================================

class TestSimParamsFileIO:
    """Tests for simparams file I/O."""

    def test_write_simparams_file(self, simparams_service, sample_phase_id_mapping):
        """Test writing simparams to file."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "simparams.json"
            simparams_service.write_simparams_file(simparams, output_path)

            assert output_path.exists()

            # Verify JSON is valid
            with open(output_path) as f:
                loaded = json.load(f)

            assert "environment" in loaded
            assert "microstructure" in loaded
            assert "time_parameters" in loaded

    def test_write_simparams_creates_directory(self, simparams_service, sample_phase_id_mapping):
        """Test that write_simparams_file creates parent directories."""
        simparams = simparams_service.generate_simparams(
            phase_id_mapping=sample_phase_id_mapping,
            material_phases=[]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "nested" / "simparams.json"
            simparams_service.write_simparams_file(simparams, output_path)

            assert output_path.exists()


# =============================================================================
# Default Electrolyte Conditions Tests
# =============================================================================

class TestElectrolyteConditions:
    """Tests for default electrolyte conditions."""

    def test_default_conditions_structure(self):
        """Test structure of default electrolyte conditions."""
        for condition in DEFAULT_ELECTROLYTE_CONDITIONS:
            assert "DCname" in condition
            assert "condition" in condition
            assert "concentration" in condition
            assert condition["condition"] == "initial"
            assert condition["concentration"] > 0

    def test_default_conditions_dc_names(self):
        """Test that expected DCs are in default conditions."""
        dc_names = {c["DCname"] for c in DEFAULT_ELECTROLYTE_CONDITIONS}

        # Should have key aqueous species
        assert "K+" in dc_names
        assert "SO4-2" in dc_names
        assert "Ca(SO4)@" in dc_names


# =============================================================================
# Config Dataclass Tests
# =============================================================================

class TestConfigDataclasses:
    """Tests for configuration dataclasses."""

    def test_environment_config_defaults(self):
        """Test EnvironmentConfig defaults."""
        config = EnvironmentConfig()

        assert config.temperature == 298.15
        assert config.reftemperature == 298.15
        assert config.saturated == 1
        assert len(config.electrolyte_conditions) == len(DEFAULT_ELECTROLYTE_CONDITIONS)

    def test_environment_config_custom(self):
        """Test EnvironmentConfig with custom values."""
        config = EnvironmentConfig(
            temperature=333.15,
            saturated=0
        )

        assert config.temperature == 333.15
        assert config.saturated == 0

    def test_time_config_defaults(self):
        """Test TimeConfig defaults."""
        config = TimeConfig()

        assert config.finaltime == 28.0
        assert len(config.outtimes) > 0
        assert 0.01 in config.outtimes

    def test_time_config_custom(self):
        """Test TimeConfig with custom values."""
        config = TimeConfig(
            finaltime=90.0,
            outtimes=[1, 7, 28, 56, 90]
        )

        assert config.finaltime == 90.0
        assert config.outtimes == [1, 7, 28, 56, 90]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

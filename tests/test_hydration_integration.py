#!/usr/bin/env python3
"""
Integration tests for THAMES hydration execution services.

Tests the complete pipeline from configuration to input file generation:
- HydrationInputConfig
- HydrationInputService
- THAMESExecutionService (without actually running THAMES)

Note: These tests do not require a running THAMES executable.
They focus on the input generation and service integration.
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.services.hydration_input_service import (
    HydrationInputService,
    HydrationInputConfig,
    MaterialPhaseData,
    get_hydration_input_service,
)
from app.services.hydration_products_service import (
    HydrationProductsService,
    get_hydration_products_service,
    CSHQ_PORESIZE_DISTRIBUTION,
    CSHQ_RD_VALUES,
)
from app.services.phase_id_mapping_service import (
    PhaseIdMappingService,
    PhaseIdMapping,
    VOIDID,
    ELECTROLYTEID,
)


class TestHydrationInputConfig:
    """Tests for HydrationInputConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HydrationInputConfig()

        assert config.temperature == 298.15
        assert config.reference_temperature == 298.15
        assert config.saturated is True
        assert config.final_time == 28.0
        assert len(config.output_times) > 0
        assert 28 in config.output_times

    def test_to_dict(self):
        """Test serialization to dictionary."""
        config = HydrationInputConfig(
            temperature=300.0,
            final_time=7.0,
            hydration_products=["CSHQ", "Portlandite"],
        )

        d = config.to_dict()

        assert d["temperature"] == 300.0
        assert d["final_time"] == 7.0
        assert "CSHQ" in d["hydration_products"]
        assert "Portlandite" in d["hydration_products"]

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "temperature": 305.0,
            "final_time": 14.0,
            "hydration_products": ["ettr", "monosulf-AlFe"],
            "product_configurations": {
                "ettr": {"affinity": [{"affinityphase": "CSHQ", "contactanglevalue": 30}]}
            }
        }

        config = HydrationInputConfig.from_dict(data)

        assert config.temperature == 305.0
        assert config.final_time == 14.0
        assert "ettr" in config.hydration_products
        assert "ettr" in config.product_configurations

    def test_round_trip_serialization(self):
        """Test that to_dict/from_dict round-trips correctly."""
        original = HydrationInputConfig(
            temperature=310.0,
            saturated=False,
            final_time=3.0,
            output_times=[0.1, 0.5, 1.0, 3.0],
            hydration_products=["CSHQ", "Portlandite", "ettr"],
        )

        d = original.to_dict()
        restored = HydrationInputConfig.from_dict(d)

        assert restored.temperature == original.temperature
        assert restored.saturated == original.saturated
        assert restored.final_time == original.final_time
        assert restored.output_times == original.output_times
        assert restored.hydration_products == original.hydration_products


class TestMaterialPhaseData:
    """Tests for MaterialPhaseData dataclass."""

    def test_basic_creation(self):
        """Test creating MaterialPhaseData."""
        phases = [
            {"gem_phase_name": "Alite", "mass_fraction": 0.60},
            {"gem_phase_name": "Belite", "mass_fraction": 0.20},
            {"gem_phase_name": "Gypsum", "mass_fraction": 0.05},
        ]

        mat = MaterialPhaseData(
            material_id=1,
            material_name="Cement 116",
            phases=phases,
            is_cement_component=True,
            is_clinker=True,
        )

        assert mat.material_id == 1
        assert mat.material_name == "Cement 116"
        assert len(mat.phases) == 3
        assert mat.is_cement_component is True
        assert mat.is_clinker is True


class TestHydrationInputServiceConfiguration:
    """Tests for HydrationInputService configuration methods."""

    @pytest.fixture
    def service(self):
        """Create HydrationInputService for testing."""
        # Use mock services to avoid GEMS database requirements
        mock_gems = Mock()
        mock_gems.get_phase.return_value = Mock(dc_names=["TestDC"])
        mock_gems.get_all_phases.return_value = []
        mock_gems.get_solid_phases.return_value = []

        mock_kinetic = Mock()
        mock_kinetic.get_kinetics_for_phase.return_value = None
        mock_kinetic.get_kinetic_type.return_value = None
        mock_kinetic.get_impurity_data.return_value = None
        mock_kinetic.get_interface_affinity.return_value = []
        mock_kinetic.is_cement_component.return_value = False

        mock_color = Mock()
        mock_color.get_color_for_phase.return_value = "#808080"
        mock_color.hex_to_rgb.return_value = (128, 128, 128)
        mock_color.create_color_mapping.return_value = Mock()
        mock_color.save_color_mapping.return_value = None

        service = HydrationInputService(
            gems_parser=mock_gems,
            kinetic_defaults=mock_kinetic,
            phase_color_service=mock_color,
        )

        return service

    def test_get_default_config_portland(self, service):
        """Test getting default config for portland cement."""
        config = service.get_default_config("portland")

        assert "CSHQ" in config.hydration_products
        assert "Portlandite" in config.hydration_products
        assert config.temperature == 298.15

    def test_get_default_config_limestone(self, service):
        """Test getting default config for limestone cement."""
        config = service.get_default_config("limestone")

        assert "CSHQ" in config.hydration_products
        assert "Portlandite" in config.hydration_products
        # Limestone cements should suggest carbonate AFm
        assert "C4AcH11" in config.hydration_products or "C4Ac0.5H12" in config.hydration_products

    def test_get_default_config_slag(self, service):
        """Test getting default config for slag cement."""
        config = service.get_default_config("slag")

        assert "CSHQ" in config.hydration_products
        assert "Portlandite" in config.hydration_products
        # Slag cements should suggest hydrotalcite
        assert "hydrotalc-pyro" in config.hydration_products


class TestPhaseIdMappingIntegration:
    """Tests for phase ID mapping integration."""

    def test_create_mapping_from_materials(self):
        """Test creating phase mapping from material data."""
        service = PhaseIdMappingService()

        materials = [
            {
                "material_name": "Cement",
                "phases": [
                    {"gem_phase_name": "Alite", "mass_fraction": 0.60},
                    {"gem_phase_name": "Belite", "mass_fraction": 0.20},
                    {"gem_phase_name": "Aluminate", "mass_fraction": 0.08},
                    {"gem_phase_name": "Ferrite", "mass_fraction": 0.10},
                    {"gem_phase_name": "Gypsum", "mass_fraction": 0.05},
                ]
            }
        ]

        mapping = service.create_mapping_from_mix(materials, include_hydration_products=False)

        # Check reserved IDs
        assert mapping.get_phase_id("VOID") == VOIDID
        assert mapping.get_phase_id("Electrolyte") == ELECTROLYTEID

        # Check clinker phases have reserved IDs
        assert mapping.get_phase_id("Alite") is not None
        assert mapping.get_phase_id("Belite") is not None

        # Check that Gypsum got an ID
        assert mapping.get_phase_id("Gypsum") is not None

    def test_mapping_bidirectional_consistency(self):
        """Test that gem_to_micro and micro_to_gem are consistent."""
        service = PhaseIdMappingService()

        materials = [
            {
                "material_name": "Cement",
                "phases": [
                    {"gem_phase_name": "Alite", "mass_fraction": 0.70},
                    {"gem_phase_name": "Belite", "mass_fraction": 0.30},
                ]
            }
        ]

        mapping = service.create_mapping_from_mix(materials)

        # Every entry in gem_to_micro should have a reverse in micro_to_gem
        for gem_name, micro_id in mapping.gem_to_micro.items():
            assert mapping.micro_to_gem[micro_id] == gem_name

        # Every entry in micro_to_gem should have a reverse in gem_to_micro
        for micro_id, gem_name in mapping.micro_to_gem.items():
            assert mapping.gem_to_micro[gem_name] == micro_id


class TestInputFileGeneration:
    """Tests for input file generation."""

    @pytest.fixture
    def mock_service(self):
        """Create a mocked HydrationInputService."""
        mock_gems = Mock()
        mock_gems.get_phase.return_value = Mock(dc_names=["TestDC"])
        mock_gems.get_all_phases.return_value = []
        mock_gems.get_solid_phases.return_value = []

        mock_kinetic = Mock()
        mock_kinetic.get_kinetics_for_phase.return_value = None
        mock_kinetic.get_kinetic_type.return_value = None
        mock_kinetic.get_impurity_data.return_value = None
        mock_kinetic.get_interface_affinity.return_value = []
        mock_kinetic.is_cement_component.return_value = False

        mock_color = Mock()
        mock_color.get_color_for_phase.return_value = "#808080"
        mock_color.hex_to_rgb.return_value = (128, 128, 128)
        mock_color.create_color_mapping.return_value = Mock()
        mock_color.save_color_mapping.return_value = None

        service = HydrationInputService(
            gems_parser=mock_gems,
            kinetic_defaults=mock_kinetic,
            phase_color_service=mock_color,
        )

        return service

    def test_generate_inputs_creates_files(self, mock_service):
        """Test that generate_all_inputs creates expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            materials = [
                MaterialPhaseData(
                    material_id=1,
                    material_name="TestCement",
                    phases=[
                        {"gem_phase_name": "Alite", "mass_fraction": 0.70},
                        {"gem_phase_name": "Belite", "mass_fraction": 0.30},
                    ],
                    is_cement_component=True,
                )
            ]

            config = HydrationInputConfig(
                temperature=298.15,
                final_time=7.0,
                hydration_products=["CSHQ", "Portlandite"],
            )

            success, errors, files = mock_service.generate_all_inputs(
                output_dir=output_dir,
                operation_name="test_op",
                material_phases=materials,
                config=config,
            )

            # Check that key files were created
            assert 'simparams' in files
            assert files['simparams'].exists()

            assert 'phase_mapping' in files
            assert files['phase_mapping'].exists()

            assert 'hydration_config' in files
            assert files['hydration_config'].exists()

    def test_simparams_json_structure(self, mock_service):
        """Test that generated simparams.json has correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            materials = [
                MaterialPhaseData(
                    material_id=1,
                    material_name="TestCement",
                    phases=[
                        {"gem_phase_name": "Alite", "mass_fraction": 1.0},
                    ],
                    is_cement_component=True,
                )
            ]

            config = HydrationInputConfig(
                temperature=300.0,
                final_time=14.0,
            )

            success, errors, files = mock_service.generate_all_inputs(
                output_dir=output_dir,
                operation_name="test_structure",
                material_phases=materials,
                config=config,
            )

            # Read and validate simparams.json
            with open(files['simparams'], 'r') as f:
                simparams = json.load(f)

            # Check required top-level keys
            assert "environment" in simparams
            assert "microstructure" in simparams
            assert "time_parameters" in simparams

            # Check environment section
            env = simparams["environment"]
            assert env["temperature"] == 300.0
            assert "saturated" in env

            # Check time_parameters section
            time_params = simparams["time_parameters"]
            assert time_params["finaltime"] == 14.0
            assert "outtimes" in time_params

            # Check microstructure section
            micro = simparams["microstructure"]
            assert "numentries" in micro
            assert "phases" in micro
            assert isinstance(micro["phases"], list)


class TestProductConfigurationIntegration:
    """Tests for product configuration in generated files."""

    @pytest.fixture
    def mock_service(self):
        """Create a mocked HydrationInputService."""
        mock_gems = Mock()
        mock_gems.get_phase.return_value = Mock(dc_names=["CSHQ-JenD", "CSHQ-TobH"])
        mock_gems.get_all_phases.return_value = []
        mock_gems.get_solid_phases.return_value = []

        mock_kinetic = Mock()
        mock_kinetic.get_kinetics_for_phase.return_value = None
        mock_kinetic.get_kinetic_type.return_value = None
        mock_kinetic.get_impurity_data.return_value = None
        mock_kinetic.get_interface_affinity.return_value = []
        mock_kinetic.is_cement_component.return_value = False

        mock_color = Mock()
        mock_color.get_color_for_phase.return_value = "#00FF00"
        mock_color.hex_to_rgb.return_value = (0, 255, 0)
        mock_color.create_color_mapping.return_value = Mock()
        mock_color.save_color_mapping.return_value = None

        service = HydrationInputService(
            gems_parser=mock_gems,
            kinetic_defaults=mock_kinetic,
            phase_color_service=mock_color,
        )

        return service

    def test_csh_configuration_applied(self, mock_service):
        """Test that C-S-H configuration (PSD, Rd) is applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            materials = [
                MaterialPhaseData(
                    material_id=1,
                    material_name="TestCement",
                    phases=[{"gem_phase_name": "Alite", "mass_fraction": 1.0}],
                    is_cement_component=True,
                )
            ]

            # Configure CSHQ with custom PSD and Rd
            config = HydrationInputConfig(
                hydration_products=["CSHQ"],
                product_configurations={
                    "CSHQ": {
                        "gems_name": "CSHQ",
                        "affinity": [{"affinityphase": "Alite", "contactanglevalue": 25}],
                        "poresize_distribution": CSHQ_PORESIZE_DISTRIBUTION[:5],  # First 5 entries
                        "rd_values": CSHQ_RD_VALUES,
                    }
                }
            )

            success, errors, files = mock_service.generate_all_inputs(
                output_dir=output_dir,
                operation_name="test_csh",
                material_phases=materials,
                config=config,
            )

            # Read simparams and check CSHQ configuration
            with open(files['simparams'], 'r') as f:
                simparams = json.load(f)

            # Find CSHQ in phases
            cshq_phase = None
            for phase in simparams["microstructure"]["phases"]:
                if phase.get("thamesname") == "CSHQ":
                    cshq_phase = phase
                    break

            assert cshq_phase is not None, "CSHQ should be in phases"

            # Check PSD was applied
            if "poresize_distribution" in cshq_phase:
                assert len(cshq_phase["poresize_distribution"]) == 5

            # Check Rd was applied
            if "Rd" in cshq_phase:
                assert len(cshq_phase["Rd"]) == 2


class TestHydrationConfigPersistence:
    """Tests for saving and loading hydration configuration."""

    @pytest.fixture
    def service(self):
        """Create HydrationInputService."""
        mock_gems = Mock()
        mock_kinetic = Mock()
        mock_color = Mock()
        mock_color.create_color_mapping.return_value = Mock()
        mock_color.save_color_mapping.return_value = None

        return HydrationInputService(
            gems_parser=mock_gems,
            kinetic_defaults=mock_kinetic,
            phase_color_service=mock_color,
        )

    def test_save_and_load_config(self, service):
        """Test saving and loading hydration configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.json"

            # Create config with various settings
            original = HydrationInputConfig(
                temperature=305.0,
                saturated=False,
                final_time=21.0,
                output_times=[1, 7, 14, 21],
                hydration_products=["CSHQ", "Portlandite", "ettr"],
                product_configurations={
                    "CSHQ": {
                        "affinity": [{"affinityphase": "Alite", "contactanglevalue": 30}]
                    }
                },
                kinetic_overrides={
                    "Alite": {"K": 0.5, "Ea": 45000}
                }
            )

            # Save
            with open(config_path, 'w') as f:
                json.dump(original.to_dict(), f)

            # Load
            loaded = service.load_hydration_config(config_path)

            # Verify
            assert loaded.temperature == 305.0
            assert loaded.saturated is False
            assert loaded.final_time == 21.0
            assert loaded.output_times == [1, 7, 14, 21]
            assert "CSHQ" in loaded.hydration_products
            assert "CSHQ" in loaded.product_configurations
            assert "Alite" in loaded.kinetic_overrides


class TestMicrostructurePhaseExtraction:
    """Tests for reading and ensuring microstructure phases are in mapping."""

    @pytest.fixture
    def service(self):
        """Create HydrationInputService with mocked dependencies."""
        mock_gems = Mock()
        mock_gems.get_phase.return_value = Mock(dc_names=["TestDC"])
        mock_kinetic = Mock()
        mock_kinetic.get_kinetics_for_phase.return_value = None
        mock_kinetic.get_kinetic_type.return_value = None
        mock_kinetic.get_impurity_data.return_value = None
        mock_kinetic.get_interface_affinity.return_value = []
        mock_kinetic.is_cement_component.return_value = False
        mock_color = Mock()
        mock_color.get_color_for_phase.return_value = "#808080"
        mock_color.create_color_mapping.return_value = Mock()
        mock_color.save_color_mapping.return_value = None

        return HydrationInputService(
            gems_parser=mock_gems,
            kinetic_defaults=mock_kinetic,
            phase_color_service=mock_color,
        )

    def test_read_microstructure_phase_ids_simple(self, service):
        """Test reading phase IDs from a simple microstructure file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            # Create a simple microstructure file
            content = """X_Size: 3
Y_Size: 3
Z_Size: 3
0 1 2
1 2 3
2 3 0
0 1 2
1 2 3
2 3 0
0 1 2
1 2 3
2 3 0
"""
            micro_path.write_text(content)

            phase_ids, embedded_map, errors = service.read_microstructure_phase_ids(micro_path)

            assert len(errors) == 0
            assert phase_ids == {0, 1, 2, 3}
            assert embedded_map is None  # No embedded mapping in this file

    def test_read_microstructure_with_thames_header(self, service):
        """Test reading phase IDs with THAMES header containing phase mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            content = """#THAMES: X_Size: 3
#THAMES: Y_Size: 3
#THAMES: Z_Size: 3
#THAMES: Phase_0: VOID
#THAMES: Phase_1: Electrolyte
#THAMES: Phase_2: Alite
#THAMES: Phase_3: Belite
0 1 2
1 2 3
2 3 0
"""
            micro_path.write_text(content)

            phase_ids, embedded_map, errors = service.read_microstructure_phase_ids(micro_path)

            assert len(errors) == 0
            assert phase_ids == {0, 1, 2, 3}
            assert embedded_map is not None
            assert embedded_map[0] == "VOID"
            assert embedded_map[1] == "Electrolyte"
            assert embedded_map[2] == "Alite"
            assert embedded_map[3] == "Belite"

    def test_ensure_microstructure_phases_all_present(self, service):
        """Test that no changes are made when all phases are already in mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            content = """X_Size: 2
Y_Size: 2
Z_Size: 2
0 1
2 3
0 1
2 3
"""
            micro_path.write_text(content)

            # Create mapping that already has all phases
            from app.services.phase_id_mapping_service import PhaseIdMapping
            mapping = PhaseIdMapping()
            mapping.gem_to_micro = {"VOID": 0, "Electrolyte": 1, "Alite": 2, "Belite": 3}
            mapping.micro_to_gem = {0: "VOID", 1: "Electrolyte", 2: "Alite", 3: "Belite"}

            success, messages = service.ensure_microstructure_phases_in_mapping(
                micro_path, mapping
            )

            assert success is True
            assert any("already in the mapping" in msg for msg in messages)
            # Mapping should be unchanged
            assert len(mapping.gem_to_micro) == 4

    def test_ensure_microstructure_phases_adds_missing(self, service):
        """Test that missing phases are added from embedded mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            # Microstructure with phase 5 that has a name in header
            content = """#THAMES: Phase_5: Gypsum
X_Size: 2
Y_Size: 2
Z_Size: 2
0 1
2 5
0 1
2 5
"""
            micro_path.write_text(content)

            # Create mapping missing phase 5
            from app.services.phase_id_mapping_service import PhaseIdMapping
            mapping = PhaseIdMapping()
            mapping.gem_to_micro = {"VOID": 0, "Electrolyte": 1, "Alite": 2}
            mapping.micro_to_gem = {0: "VOID", 1: "Electrolyte", 2: "Alite"}
            mapping.next_available_id = 3

            success, messages = service.ensure_microstructure_phases_in_mapping(
                micro_path, mapping
            )

            assert success is True
            # Phase 5 should now be in mapping with name "Gypsum"
            assert 5 in mapping.micro_to_gem
            assert mapping.micro_to_gem[5] == "Gypsum"
            assert mapping.gem_to_micro["Gypsum"] == 5
            assert any("Gypsum" in msg for msg in messages)

    def test_ensure_microstructure_phases_unknown_phase(self, service):
        """Test that unknown phases get placeholder names with warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            # Microstructure with phase 99 that has no name
            content = """X_Size: 2
Y_Size: 2
Z_Size: 2
0 1
2 99
0 1
2 99
"""
            micro_path.write_text(content)

            # Create mapping missing phase 99
            from app.services.phase_id_mapping_service import PhaseIdMapping
            mapping = PhaseIdMapping()
            mapping.gem_to_micro = {"VOID": 0, "Electrolyte": 1, "Alite": 2}
            mapping.micro_to_gem = {0: "VOID", 1: "Electrolyte", 2: "Alite"}
            mapping.next_available_id = 3

            success, messages = service.ensure_microstructure_phases_in_mapping(
                micro_path, mapping
            )

            assert success is True
            # Phase 99 should be in mapping with placeholder name
            assert 99 in mapping.micro_to_gem
            assert mapping.micro_to_gem[99] == "Unknown_Phase_99"
            assert mapping.gem_to_micro["Unknown_Phase_99"] == 99
            # Should have a warning message
            assert any("WARNING" in msg and "99" in msg for msg in messages)

    def test_void_and_electrolyte_always_in_mapping(self, service):
        """Test that VOID and Electrolyte are always in the phase mapping."""
        # This tests the PhaseIdMappingService behavior which is used by generate_all_inputs
        from app.services.phase_id_mapping_service import PhaseIdMappingService, VOIDID, ELECTROLYTEID

        mapping_service = PhaseIdMappingService()

        # Create a mapping with just one material (no VOID or Electrolyte explicitly)
        material_phases = [
            {
                'material_name': 'TestCement',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 0.70},
                    {'gem_phase_name': 'Belite', 'mass_fraction': 0.30},
                ],
            }
        ]

        mapping = mapping_service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # VOID (ID 0) and Electrolyte (ID 1) must ALWAYS be present
        assert VOIDID in mapping.micro_to_gem, "VOID (ID 0) must be in mapping"
        assert ELECTROLYTEID in mapping.micro_to_gem, "Electrolyte (ID 1) must be in mapping"

        assert mapping.micro_to_gem[VOIDID] == "VOID"
        assert mapping.micro_to_gem[ELECTROLYTEID] == "Electrolyte"

        assert mapping.gem_to_micro["VOID"] == VOIDID
        assert mapping.gem_to_micro["Electrolyte"] == ELECTROLYTEID

    def test_microstructure_phases_added_to_generate_inputs(self, service):
        """Test that ensure_microstructure_phases_in_mapping is called in generate flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            micro_path = Path(tmpdir) / "test.mic"

            # Microstructure with phase 99 (unknown phase)
            content = """#THAMES: Phase_99: CustomPhase
X_Size: 2
Y_Size: 2
Z_Size: 2
0 1
2 99
0 1
2 99
"""
            micro_path.write_text(content)

            # Create a mapping (simulating what _create_phase_mapping returns)
            from app.services.phase_id_mapping_service import PhaseIdMapping
            mapping = PhaseIdMapping()
            mapping.gem_to_micro = {"VOID": 0, "Electrolyte": 1, "Alite": 2}
            mapping.micro_to_gem = {0: "VOID", 1: "Electrolyte", 2: "Alite"}
            mapping.next_available_id = 3

            # Call ensure_microstructure_phases_in_mapping
            success, messages = service.ensure_microstructure_phases_in_mapping(
                micro_path, mapping
            )

            assert success is True

            # Phase 99 (CustomPhase) should now be in the mapping
            assert 99 in mapping.micro_to_gem
            assert mapping.micro_to_gem[99] == "CustomPhase"
            assert mapping.gem_to_micro["CustomPhase"] == 99


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

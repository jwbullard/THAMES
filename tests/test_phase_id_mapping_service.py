#!/usr/bin/env python3
"""
Tests for the Phase ID Mapping Service

This test suite verifies:
1. Correct assignment of reserved IDs (VOID=0, ELECTROLYTE=1)
2. Clinker phase detection and ID reservation (IDs 2-7)
3. Dynamic ID assignment for non-clinker phases
4. Mapping consistency (bidirectional lookups)
5. Mixes without clinker phases
6. Validation of mappings

Run with: python -m pytest tests/test_phase_id_mapping_service.py -v
Or simply: python tests/test_phase_id_mapping_service.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import unittest
from app.services.phase_id_mapping_service import (
    PhaseIdMappingService,
    PhaseIdMapping,
    VOIDID,
    ELECTROLYTEID,
    FIRST_SOLID,
    CLINKER_PHASES,
    NUM_CLINKER_PHASES,
)


class TestPhaseIdMappingService(unittest.TestCase):
    """Test cases for PhaseIdMappingService."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = PhaseIdMappingService()

    def test_reserved_ids_constants(self):
        """Test that reserved ID constants are correct."""
        self.assertEqual(VOIDID, 0, "VOID should be ID 0")
        self.assertEqual(ELECTROLYTEID, 1, "ELECTROLYTE should be ID 1")
        self.assertEqual(FIRST_SOLID, 2, "First solid should be ID 2")

    def test_clinker_phases_list(self):
        """Test that clinker phases list is complete."""
        expected = ["Alite", "Belite", "Aluminate", "Ferrite", "arcanite", "thenardite"]
        self.assertEqual(CLINKER_PHASES, expected)
        self.assertEqual(NUM_CLINKER_PHASES, 6)

    def test_portland_cement_mix(self):
        """Test mapping for a typical portland cement mix."""
        material_phases = [
            {
                'material_name': 'Cement 116',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 0.55},
                    {'gem_phase_name': 'Belite', 'mass_fraction': 0.18},
                    {'gem_phase_name': 'Aluminate', 'mass_fraction': 0.08},
                    {'gem_phase_name': 'Ferrite', 'mass_fraction': 0.10},
                    {'gem_phase_name': 'arcanite', 'mass_fraction': 0.01},
                    {'gem_phase_name': 'thenardite', 'mass_fraction': 0.01},
                    {'gem_phase_name': 'Gypsum', 'mass_fraction': 0.05},
                    {'gem_phase_name': 'hemihydrate', 'mass_fraction': 0.02},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Check that clinker was detected
        self.assertTrue(mapping.has_clinker, "Should detect clinker phases")

        # Check reserved IDs
        self.assertEqual(mapping.get_phase_id("VOID"), 0)
        self.assertEqual(mapping.get_phase_id("aq_gen"), 1)

        # Check clinker phase IDs (must be 2-7 in order)
        self.assertEqual(mapping.get_phase_id("Alite"), 2)
        self.assertEqual(mapping.get_phase_id("Belite"), 3)
        self.assertEqual(mapping.get_phase_id("Aluminate"), 4)
        self.assertEqual(mapping.get_phase_id("Ferrite"), 5)
        self.assertEqual(mapping.get_phase_id("arcanite"), 6)
        self.assertEqual(mapping.get_phase_id("thenardite"), 7)

        # Check non-clinker phases get IDs >= 8
        gypsum_id = mapping.get_phase_id("Gypsum")
        hemihydrate_id = mapping.get_phase_id("hemihydrate")
        self.assertGreaterEqual(gypsum_id, 8)
        self.assertGreaterEqual(hemihydrate_id, 8)

        print(f"✓ Portland cement mix test passed")
        print(f"  Clinker IDs: Alite=2, Belite=3, Aluminate=4, Ferrite=5, arcanite=6, thenardite=7")
        print(f"  Gypsum={gypsum_id}, hemihydrate={hemihydrate_id}")

    def test_pozzolanic_mix_without_clinker(self):
        """Test mapping for a mix without clinker phases."""
        material_phases = [
            {
                'material_name': 'Fly Ash',
                'phases': [
                    {'gem_phase_name': 'Quartz', 'mass_fraction': 0.50},
                    {'gem_phase_name': 'Mullite', 'mass_fraction': 0.30},
                    {'gem_phase_name': 'C2AS(am)', 'mass_fraction': 0.20},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Should NOT detect clinker
        self.assertFalse(mapping.has_clinker, "Should not detect clinker phases")

        # Check reserved IDs still present
        self.assertEqual(mapping.get_phase_id("VOID"), 0)
        self.assertEqual(mapping.get_phase_id("aq_gen"), 1)

        # Phases should start at ID 2 (no clinker reservation)
        quartz_id = mapping.get_phase_id("Quartz")
        mullite_id = mapping.get_phase_id("Mullite")
        c2as_id = mapping.get_phase_id("C2AS(am)")

        self.assertGreaterEqual(quartz_id, 2)
        self.assertGreaterEqual(mullite_id, 2)
        self.assertGreaterEqual(c2as_id, 2)

        # All IDs should be unique
        ids = [quartz_id, mullite_id, c2as_id]
        self.assertEqual(len(ids), len(set(ids)), "All IDs should be unique")

        print(f"✓ Pozzolanic mix (no clinker) test passed")
        print(f"  Quartz={quartz_id}, Mullite={mullite_id}, C2AS(am)={c2as_id}")

    def test_blended_cement_mix(self):
        """Test mapping for a blended cement with fly ash."""
        material_phases = [
            {
                'material_name': 'Portland Cement',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 0.60},
                    {'gem_phase_name': 'Belite', 'mass_fraction': 0.15},
                    {'gem_phase_name': 'Aluminate', 'mass_fraction': 0.08},
                    {'gem_phase_name': 'Ferrite', 'mass_fraction': 0.10},
                ]
            },
            {
                'material_name': 'Class F Fly Ash',
                'phases': [
                    {'gem_phase_name': 'Quartz', 'mass_fraction': 0.50},
                    {'gem_phase_name': 'Mullite', 'mass_fraction': 0.30},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Should detect clinker from the cement
        self.assertTrue(mapping.has_clinker)

        # Clinker phases should have reserved IDs
        self.assertEqual(mapping.get_phase_id("Alite"), 2)
        self.assertEqual(mapping.get_phase_id("Belite"), 3)
        self.assertEqual(mapping.get_phase_id("Aluminate"), 4)
        self.assertEqual(mapping.get_phase_id("Ferrite"), 5)

        # Fly ash phases should get IDs after clinker reservation
        quartz_id = mapping.get_phase_id("Quartz")
        mullite_id = mapping.get_phase_id("Mullite")
        self.assertGreaterEqual(quartz_id, 8)
        self.assertGreaterEqual(mullite_id, 8)

        print(f"✓ Blended cement mix test passed")
        print(f"  Clinker phases: IDs 2-7 reserved")
        print(f"  Pozzolan phases: Quartz={quartz_id}, Mullite={mullite_id}")

    def test_bidirectional_mapping_consistency(self):
        """Test that gem_to_micro and micro_to_gem are consistent."""
        material_phases = [
            {
                'material_name': 'Test Material',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 0.50},
                    {'gem_phase_name': 'Gypsum', 'mass_fraction': 0.50},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Check bidirectional consistency
        for phase_name, phase_id in mapping.gem_to_micro.items():
            reverse_name = mapping.get_phase_name(phase_id)
            self.assertEqual(
                phase_name, reverse_name,
                f"Mapping inconsistent: {phase_name} -> {phase_id} -> {reverse_name}"
            )

        print(f"✓ Bidirectional mapping consistency test passed")

    def test_validation(self):
        """Test the validation method."""
        material_phases = [
            {
                'material_name': 'Cement',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 1.0},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        is_valid, errors = self.service.validate_mapping(mapping)
        self.assertTrue(is_valid, f"Mapping should be valid, but got errors: {errors}")

        print(f"✓ Validation test passed")

    def test_hydration_products_included(self):
        """Test that hydration products are added when requested."""
        material_phases = [
            {
                'material_name': 'Cement',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 1.0},
                ]
            }
        ]

        # With hydration products
        mapping_with = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=True
        )

        # Without hydration products
        mapping_without = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Mapping with products should have more phases
        self.assertGreater(
            len(mapping_with.gem_to_micro),
            len(mapping_without.gem_to_micro),
            "Including hydration products should add more phases"
        )

        # Check some common hydration products are present
        self.assertIsNotNone(mapping_with.get_phase_id("CSHQ"))  # C-S-H
        self.assertIsNotNone(mapping_with.get_phase_id("Portite"))  # CH
        self.assertIsNotNone(mapping_with.get_phase_id("ettr"))  # Ettringite

        print(f"✓ Hydration products test passed")
        print(f"  Without products: {len(mapping_without.gem_to_micro)} phases")
        print(f"  With products: {len(mapping_with.gem_to_micro)} phases")

    def test_to_dict_serialization(self):
        """Test that mapping can be serialized to dict."""
        material_phases = [
            {
                'material_name': 'Cement',
                'phases': [
                    {'gem_phase_name': 'Alite', 'mass_fraction': 1.0},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        mapping_dict = mapping.to_dict()

        self.assertIn('gem_to_micro', mapping_dict)
        self.assertIn('micro_to_gem', mapping_dict)
        self.assertIn('has_clinker', mapping_dict)
        self.assertIn('clinker_phase_ids', mapping_dict)
        self.assertIn('next_available_id', mapping_dict)

        print(f"✓ Serialization test passed")

    def test_partial_clinker(self):
        """Test mapping when only some clinker phases are present."""
        material_phases = [
            {
                'material_name': 'Belite Cement',
                'phases': [
                    {'gem_phase_name': 'Belite', 'mass_fraction': 0.80},
                    {'gem_phase_name': 'Aluminate', 'mass_fraction': 0.10},
                    {'gem_phase_name': 'Gypsum', 'mass_fraction': 0.10},
                ]
            }
        ]

        mapping = self.service.create_mapping_from_mix(
            material_phases,
            include_hydration_products=False
        )

        # Should still detect clinker and reserve all 6 slots
        self.assertTrue(mapping.has_clinker)

        # All clinker phases should have reserved IDs even if not in mix
        self.assertEqual(mapping.get_phase_id("Alite"), 2)
        self.assertEqual(mapping.get_phase_id("Belite"), 3)
        self.assertEqual(mapping.get_phase_id("Aluminate"), 4)
        self.assertEqual(mapping.get_phase_id("Ferrite"), 5)
        self.assertEqual(mapping.get_phase_id("arcanite"), 6)
        self.assertEqual(mapping.get_phase_id("thenardite"), 7)

        # Gypsum should get ID >= 8
        gypsum_id = mapping.get_phase_id("Gypsum")
        self.assertGreaterEqual(gypsum_id, 8)

        print(f"✓ Partial clinker test passed")
        print(f"  Even with only Belite+Aluminate, all 6 clinker IDs reserved")
        print(f"  Gypsum={gypsum_id}")


def run_tests():
    """Run all tests with verbose output."""
    print("=" * 60)
    print("THAMES Phase ID Mapping Service Tests")
    print("=" * 60)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPhaseIdMappingService)

    # Run with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 60)
    if result.wasSuccessful():
        print("ALL TESTS PASSED ✓")
    else:
        print(f"TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

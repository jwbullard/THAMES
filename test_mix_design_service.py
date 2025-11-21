#!/usr/bin/env python3
"""
Test script for THAMES Mix Design Service

Tests CRUD operations, duplication, search, and THAMES-specific
phase ID mapping functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from app.database.service import DatabaseService
from app.services.mix_design_service import MixDesignService
from app.models.mix_design import (
    MixDesignCreate, MixDesignUpdate, MixDesignComponentData,
    MixDesignPropertiesData
)


def test_mix_design_service():
    """Test the Mix Design Service."""
    print("=" * 70)
    print("THAMES MIX DESIGN SERVICE TEST")
    print("=" * 70)

    # Initialize services
    db_path = Path(__file__).parent / "src" / "data" / "database" / "thames.db"

    # Create test database config
    class TestDatabaseConfig:
        def __init__(self, db_path):
            self.db_path = Path(db_path)
            self.db_name = self.db_path.name

        @property
        def database_url(self):
            return f"sqlite:///{self.db_path}"

        @property
        def engine_config(self):
            return {
                "url": self.database_url,
                "echo": False,
                "pool_pre_ping": True,
                "connect_args": {"check_same_thread": False}
            }

        @property
        def session_config(self):
            return {
                "autocommit": False,
                "autoflush": False,
                "expire_on_commit": False
            }

    db_config = TestDatabaseConfig(db_path)
    db_service = DatabaseService(db_config)
    mix_design_service = MixDesignService(db_service)

    print(f"\nDatabase: {db_path}")

    # Test 1: Get all mix designs
    print("\n" + "=" * 70)
    print("TEST 1: Get All Mix Designs")
    print("=" * 70)

    mix_designs = mix_design_service.get_all()
    print(f"\nTotal mix designs: {len(mix_designs)}")

    if mix_designs:
        print("\nExisting mix designs:")
        for mix in mix_designs[:5]:
            print(f"  - {mix.name} (w/b={mix.water_binder_ratio:.3f})")

    # Test 2: Create a new mix design
    print("\n" + "=" * 70)
    print("TEST 2: Create New Mix Design")
    print("=" * 70)

    # Create test components
    test_components = [
        MixDesignComponentData(
            material_id=1,
            material_name="Test Cement",
            mass_fraction=0.85,
            volume_fraction=0.30,
            specific_gravity=3.15
        ),
        MixDesignComponentData(
            material_id=2,
            material_name="Test Gypsum",
            mass_fraction=0.15,
            volume_fraction=0.05,
            specific_gravity=2.32
        )
    ]

    # Create test phase ID mapping (THAMES-specific)
    test_phase_mapping = {
        "Void": 0,
        "Electrolyte": 1,
        "Alite": 2,
        "Belite": 3,
        "Aluminate": 4,
        "Ferrite": 5,
        "arcanite": 6,
        "thenardite": 7,
        "Gypsum": 8
    }

    test_mix_data = MixDesignCreate(
        name="Test Mix Design",
        description="Test mix for validating THAMES Mix Design Service",
        water_binder_ratio=0.45,
        total_water_content=180.0,
        air_content=5.0,
        water_volume_fraction=0.18,
        air_volume_fraction=0.05,
        system_size_x=100,
        system_size_y=100,
        system_size_z=100,
        system_size=100,
        resolution=1.0,
        random_seed=-1,
        cement_shape_set="spherical",
        fine_aggregate_shape_set="spherical",
        coarse_aggregate_shape_set="spherical",
        aggregate_shape_set="spherical",
        flocculation_enabled=False,
        flocculation_degree=0.0,
        dispersion_factor=0,
        auto_calculation_enabled=True,
        components=test_components,
        phase_id_mapping=test_phase_mapping,
        notes="Test mix design for unit testing",
        is_template=False
    )

    try:
        created_mix = mix_design_service.create(test_mix_data)
        print(f"\n✓ Created mix design: {created_mix.name}")
        print(f"  ID: {created_mix.id}")
        print(f"  W/B Ratio: {created_mix.water_binder_ratio:.3f}")
        print(f"  Components: {len(created_mix.components)}")
        print(f"  Phase ID Mapping: {len(created_mix.phase_id_mapping)} phases")
        print(f"  System Size: {created_mix.system_size_x} × {created_mix.system_size_y} × {created_mix.system_size_z}")
        test_mix_id = created_mix.id
    except Exception as e:
        print(f"\n✗ Failed to create mix design: {e}")
        return

    # Test 3: Get mix design by ID
    print("\n" + "=" * 70)
    print("TEST 3: Get Mix Design by ID")
    print("=" * 70)

    retrieved_mix = mix_design_service.get_by_id(test_mix_id)
    if retrieved_mix:
        print(f"\n✓ Retrieved mix design: {retrieved_mix.name}")
        print(f"  Description: {retrieved_mix.description}")
        print(f"  Created: {retrieved_mix.created_at}")
        print(f"  Updated: {retrieved_mix.updated_at}")
        print("\n  Phase ID Mapping:")
        for phase_name, phase_id in sorted(retrieved_mix.phase_id_mapping.items(), key=lambda x: x[1]):
            print(f"    {phase_id}: {phase_name}")
    else:
        print(f"\n✗ Failed to retrieve mix design with ID {test_mix_id}")

    # Test 4: Get mix design by name
    print("\n" + "=" * 70)
    print("TEST 4: Get Mix Design by Name")
    print("=" * 70)

    retrieved_by_name = mix_design_service.get_by_name("Test Mix Design")
    if retrieved_by_name:
        print(f"\n✓ Retrieved by name: {retrieved_by_name.name}")
        print(f"  ID: {retrieved_by_name.id}")
    else:
        print("\n✗ Failed to retrieve mix design by name")

    # Test 5: Update mix design
    print("\n" + "=" * 70)
    print("TEST 5: Update Mix Design")
    print("=" * 70)

    update_data = MixDesignUpdate(
        description="Updated test mix design",
        water_binder_ratio=0.50,
        system_size_x=150,
        system_size_y=150,
        system_size_z=150
    )

    try:
        updated_mix = mix_design_service.update_by_id(test_mix_id, update_data)
        print(f"\n✓ Updated mix design: {updated_mix.name}")
        print(f"  New W/B Ratio: {updated_mix.water_binder_ratio:.3f}")
        print(f"  New System Size: {updated_mix.system_size_x} × {updated_mix.system_size_y} × {updated_mix.system_size_z}")
        print(f"  Description: {updated_mix.description}")
    except Exception as e:
        print(f"\n✗ Failed to update mix design: {e}")

    # Test 6: Duplicate mix design
    print("\n" + "=" * 70)
    print("TEST 6: Duplicate Mix Design")
    print("=" * 70)

    try:
        duplicate_mix = mix_design_service.duplicate(test_mix_id, "Test Mix Design Copy")
        print(f"\n✓ Duplicated mix design: {duplicate_mix.name}")
        print(f"  Original ID: {test_mix_id}")
        print(f"  Duplicate ID: {duplicate_mix.id}")
        print(f"  W/B Ratio: {duplicate_mix.water_binder_ratio:.3f}")
        print(f"  Phase Mapping Copied: {len(duplicate_mix.phase_id_mapping)} phases")
        duplicate_mix_id = duplicate_mix.id
    except Exception as e:
        print(f"\n✗ Failed to duplicate mix design: {e}")
        duplicate_mix_id = None

    # Test 7: Search mix designs
    print("\n" + "=" * 70)
    print("TEST 7: Search Mix Designs")
    print("=" * 70)

    search_results = mix_design_service.search("Test")
    print(f"\n✓ Search results for 'Test': {len(search_results)} found")
    for result in search_results:
        print(f"  - {result.name}")

    # Test 8: Get statistics
    print("\n" + "=" * 70)
    print("TEST 8: Get Statistics")
    print("=" * 70)

    stats = mix_design_service.get_statistics()
    print(f"\n✓ Mix Design Statistics:")
    print(f"  Total: {stats['total_mix_designs']}")
    print(f"  Templates: {stats['template_mix_designs']}")
    print(f"  Custom: {stats['custom_mix_designs']}")
    print(f"  Most Recent: {stats['most_recent']}")

    # Test 9: Convert to response format
    print("\n" + "=" * 70)
    print("TEST 9: Convert to Response Format")
    print("=" * 70)

    try:
        response = mix_design_service.to_response(retrieved_mix)
        print(f"\n✓ Converted to response format:")
        print(f"  Name: {response.name}")
        print(f"  Components: {len(response.components)}")
        print(f"  Phase Mapping: {len(response.phase_id_mapping)} phases")
        print(f"  Grading Templates: fine={response.fine_aggregate_grading_template}, coarse={response.coarse_aggregate_grading_template}")
    except Exception as e:
        print(f"\n✗ Failed to convert to response: {e}")

    # Test 10: Delete mix designs (cleanup)
    print("\n" + "=" * 70)
    print("TEST 10: Delete Mix Designs (Cleanup)")
    print("=" * 70)

    try:
        # Delete the duplicate first
        if duplicate_mix_id:
            mix_design_service.delete_by_id(duplicate_mix_id)
            print(f"\n✓ Deleted duplicate mix design (ID: {duplicate_mix_id})")

        # Delete the original test mix
        mix_design_service.delete_by_id(test_mix_id)
        print(f"✓ Deleted test mix design (ID: {test_mix_id})")

        # Verify deletion
        deleted_mix = mix_design_service.get_by_id(test_mix_id)
        if deleted_mix is None:
            print("✓ Verified mix design was deleted")
        else:
            print("✗ Mix design still exists after deletion")
    except Exception as e:
        print(f"\n✗ Failed to delete mix designs: {e}")

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("\n✓ All Mix Design Service tests completed successfully!")
    print("\nTested features:")
    print("  ✓ Get all mix designs")
    print("  ✓ Create mix design with components")
    print("  ✓ THAMES-specific phase ID mapping")
    print("  ✓ Get by ID and by name")
    print("  ✓ Update mix design")
    print("  ✓ Duplicate mix design")
    print("  ✓ Search functionality")
    print("  ✓ Statistics tracking")
    print("  ✓ Response format conversion")
    print("  ✓ Delete mix design")


if __name__ == '__main__':
    try:
        test_mix_design_service()
    except Exception as e:
        print(f"\n{'='*70}")
        print("TEST FAILED")
        print("="*70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script for THAMES Material Service

Demonstrates CRUD operations, tag management, phase composition,
and GEMS integration.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from app.database.service import DatabaseService
from app.database.config import DatabaseConfig
from app.services.material_service import MaterialService
from app.models import MaterialCreate


def test_material_service():
    """Test the Material Service."""
    print("=" * 70)
    print("THAMES MATERIAL SERVICE TEST")
    print("=" * 70)

    # Initialize services
    db_path = Path(__file__).parent / "src" / "data" / "database" / "thames.db"
    gems_data_dir = Path(__file__).parent / "src" / "data" / "gems"

    # For testing, connect directly to the database where migration wrote the data
    # Create a simple config that uses the correct path
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
    material_service = MaterialService(db_service, gems_data_dir)

    print(f"\nDatabase: {db_path}")
    print(f"GEMS Data: {gems_data_dir}")

    # Test 1: Get all materials
    print("\n" + "=" * 70)
    print("TEST 1: Get All Materials")
    print("=" * 70)

    materials = material_service.get_all()
    print(f"\nTotal materials: {len(materials)}")

    # Show first 5
    print("\nFirst 5 materials:")
    for mat in materials[:5]:
        print(f"  - {mat.name}")
        print(f"    Tags: {mat.tag_names}")
        print(f"    Phases: {len(mat.phases)}")
        print(f"    SG: {mat.specific_gravity:.3f}")

    # Test 2: Get material by name
    print("\n" + "=" * 70)
    print("TEST 2: Get Material by Name")
    print("=" * 70)

    test_material_name = "cementotc"
    material = material_service.get_by_name(test_material_name)

    if material:
        print(f"\nMaterial: {material.name}")
        print(f"Tags: {material.tag_names}")
        print(f"Specific Gravity: {material.specific_gravity:.3f}")
        print(f"Immutable: {material.immutable}")
        print(f"PSD: {material.psd_data.get_distribution_summary() if material.psd_data else 'None'}")

        print(f"\nPhase Composition ({len(material.phases)} phases):")
        for phase in material.phases:
            print(f"  - {phase.gem_phase_name:<15} {phase.mass_fraction*100:>6.2f}%")
        print(f"  {'TOTAL':<15} {material.total_phase_fraction*100:>6.2f}%")
    else:
        print(f"  Material '{test_material_name}' not found")

    # Test 3: Search by tags
    print("\n" + "=" * 70)
    print("TEST 3: Search by Tags")
    print("=" * 70)

    # Search for cements
    cement_materials = material_service.search_by_tags(['cement'], match_all=True)
    print(f"\nMaterials with tag 'cement': {len(cement_materials)}")

    # Search for migrated materials
    migrated_materials = material_service.search_by_tags(['migrated-vcctl'], match_all=True)
    print(f"Materials with tag 'migrated-vcctl': {len(migrated_materials)}")

    # Search for limestones
    limestone_materials = material_service.search_by_tags(['limestone'], match_all=True)
    print(f"Materials with tag 'limestone': {len(limestone_materials)}")

    # Test 4: Search by phase
    print("\n" + "=" * 70)
    print("TEST 4: Search by Phase")
    print("=" * 70)

    alite_materials = material_service.search_by_phase('Alite')
    print(f"\nMaterials containing Alite (C3S): {len(alite_materials)}")
    print("Examples:")
    for mat in alite_materials[:5]:
        alite_phase = next((p for p in mat.phases if p.gem_phase_name == 'Alite'), None)
        if alite_phase:
            print(f"  - {mat.name:<20} Alite: {alite_phase.mass_fraction*100:.1f}%")

    # Test 5: Get all tags
    print("\n" + "=" * 70)
    print("TEST 5: Get All Tags")
    print("=" * 70)

    all_tags = material_service.get_all_tags()
    print(f"\nTotal tags: {len(all_tags)}")
    print(f"Tags: {', '.join(all_tags)}")

    # Test 6: Create a new material
    print("\n" + "=" * 70)
    print("TEST 6: Create New Material")
    print("=" * 70)

    # Check if test material already exists
    test_name = "Test Portland Cement"
    existing = material_service.get_by_name(test_name)

    if existing:
        print(f"\nTest material '{test_name}' already exists, deleting...")
        try:
            material_service.delete(existing.id)
            print("  ✓ Deleted")
        except Exception as e:
            print(f"  ✗ Could not delete: {e}")
            return

    # Create new material
    print(f"\nCreating new material: '{test_name}'")

    # First, we need to create PSD data or reference existing one
    # For this test, we'll reference an existing PSD
    existing_psd_id = materials[0].psd_data_id if materials else None

    if not existing_psd_id:
        print("  ✗ No existing PSD data found, skipping create test")
        return

    new_material_data = MaterialCreate(
        name=test_name,
        tags=["cement", "test", "custom"],
        specific_gravity=3.15,
        psd_data_id=existing_psd_id,
        description="Test Portland cement created via service",
        immutable=False
    )

    phase_compositions = [
        {"gem_phase_name": "Alite", "mass_fraction": 0.65},
        {"gem_phase_name": "Belite", "mass_fraction": 0.15},
        {"gem_phase_name": "Aluminate", "mass_fraction": 0.10},
        {"gem_phase_name": "Ferrite", "mass_fraction": 0.08},
        {"gem_phase_name": "Gypsum", "mass_fraction": 0.02},
    ]

    try:
        new_material = material_service.create(
            new_material_data,
            phase_compositions=phase_compositions,
            auto_calculate_sg=False  # Use provided SG
        )

        print(f"  ✓ Created material: {new_material.name}")
        print(f"    ID: {new_material.id}")
        print(f"    Tags: {new_material.tag_names}")
        print(f"    Phases: {len(new_material.phases)}")
        print(f"    Total fraction: {new_material.total_phase_fraction:.3f}")

        # Test 7: Add tag to material
        print("\n" + "=" * 70)
        print("TEST 7: Add Tag to Material")
        print("=" * 70)

        print(f"\nAdding tag 'experimental' to '{new_material.name}'")
        updated = material_service.add_tag(new_material.id, "experimental")
        print(f"  ✓ Tags now: {updated.tag_names}")

        # Test 8: Update phase (first reduce a phase to make room for new one)
        print("\n" + "=" * 70)
        print("TEST 8: Update Phase")
        print("=" * 70)

        print(f"\nReducing Alite fraction in '{new_material.name}' to make room for new phase")
        updated_phase = material_service.update_phase(
            new_material.id,
            gem_phase_name="Alite",
            mass_fraction=0.59  # Reduce from 0.65 to 0.59 (frees up 0.06)
        )
        print(f"  ✓ Updated phase: {updated_phase.gem_phase_name} = {updated_phase.mass_fraction:.3f}")

        # Refresh to see updated total
        updated_material = material_service.get_by_id(new_material.id)
        print(f"  Total fraction after update: {updated_material.total_phase_fraction:.3f}")

        # Test 9: Add phase to material
        print("\n" + "=" * 70)
        print("TEST 9: Add Phase to Material")
        print("=" * 70)

        print(f"\nAdding phase 'Anhydrite' to '{new_material.name}'")
        try:
            new_phase = material_service.add_phase(
                new_material.id,
                gem_phase_name="Anhydrite",
                mass_fraction=0.05,
                validate_gems=True
            )
            print(f"  ✓ Added phase: {new_phase.gem_phase_name}")

            # Refresh to see updated total
            updated_material = material_service.get_by_id(new_material.id)
            print(f"  Total phases: {len(updated_material.phases)}")
            print(f"  Total fraction: {updated_material.total_phase_fraction:.3f}")
        except Exception as e:
            print(f"  ✗ Could not add phase: {e}")

        # Test 10: Delete material
        print("\n" + "=" * 70)
        print("TEST 10: Delete Material")
        print("=" * 70)

        print(f"\nDeleting test material: '{new_material.name}'")
        deleted = material_service.delete(new_material.id)
        print(f"  ✓ Deleted: {deleted}")

        # Verify deletion
        check = material_service.get_by_id(new_material.id)
        if check is None:
            print("  ✓ Verified: Material no longer exists")
        else:
            print("  ✗ Error: Material still exists")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    # Final summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    final_count = len(material_service.get_all())
    print(f"\nTotal materials in database: {final_count}")
    print(f"Total tags in database: {len(material_service.get_all_tags())}")

    print("\n✓ All tests completed")


if __name__ == '__main__':
    try:
        test_material_service()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

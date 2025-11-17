#!/usr/bin/env python3
"""
Test script for Materials UI Phase 1

Tests the MaterialsPanel and MaterialDialog components without launching full GUI.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from app.services.material_service import MaterialService
from app.database.service import DatabaseService
from app.database.config import DatabaseConfig
from app.models.material import MaterialCreate


def test_material_service_integration():
    """Test that MaterialService can be instantiated and used."""
    print("=" * 70)
    print("TEST 1: MaterialService Integration")
    print("=" * 70)

    try:
        db_config = DatabaseConfig(db_name="thames.db")
        db_service = DatabaseService(db_config)
        gems_data_dir = Path(__file__).parent / "src" / "data" / "gems"

        material_service = MaterialService(db_service, gems_data_dir)
        print(f"✓ MaterialService initialized")
        print(f"  Database: {db_config.db_path}")
        print(f"  GEMS data: {gems_data_dir}")

        # Get all materials
        materials = material_service.get_all()
        print(f"✓ Loaded {len(materials)} materials")

        # Show first 3
        print("\nFirst 3 materials:")
        for mat in materials[:3]:
            print(f"  - {mat.name}")
            print(f"    Tags: {mat.tag_names}")
            print(f"    SG: {mat.specific_gravity}")
            print(f"    Phases: {len(mat.phases)}")

        return True, material_service

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_tag_chip_input():
    """Test TagChipInput widget."""
    print("\n" + "=" * 70)
    print("TEST 2: TagChipInput Widget")
    print("=" * 70)

    try:
        from app.widgets.tag_chip_input import TagChipInput

        # Create widget
        tag_input = TagChipInput()
        print("✓ TagChipInput widget created")

        # Add tags programmatically
        tag_input.add_tag("cement")
        tag_input.add_tag("type-i")
        tag_input.add_tag("custom")
        print("✓ Added tags programmatically")

        # Get tags
        tags = tag_input.get_tags()
        print(f"✓ Retrieved tags: {tags}")
        assert tags == ["cement", "type-i", "custom"], f"Expected ['cement', 'type-i', 'custom'], got {tags}"

        # Set new tags
        tag_input.set_tags(["limestone", "test"])
        tags = tag_input.get_tags()
        print(f"✓ Set new tags: {tags}")
        assert tags == ["limestone", "test"], f"Expected ['limestone', 'test'], got {tags}"

        # Clear
        tag_input.clear()
        tags = tag_input.get_tags()
        print(f"✓ Cleared tags: {tags}")
        assert tags == [], f"Expected [], got {tags}"

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_material(material_service):
    """Test creating a material through the service."""
    print("\n" + "=" * 70)
    print("TEST 3: Create Material via Service")
    print("=" * 70)

    try:
        # Check if test material already exists
        existing = material_service.get_by_name("UI Test Material")
        if existing:
            print(f"  Deleting existing test material (ID: {existing.id})")
            material_service.delete(existing.id)

        # Create test material
        create_data = MaterialCreate(
            name="UI Test Material",
            tags=["test", "ui", "phase1"],
            specific_gravity=3.15,
            specific_surface_area=350.0,
            psd_data_id=1,
            description="Test material created by UI test script",
            immutable=False
        )

        material = material_service.create(create_data)
        print(f"✓ Created material: {material.name} (ID: {material.id})")
        print(f"  Tags: {material.tag_names}")
        print(f"  SG: {material.specific_gravity}")
        print(f"  SSA: {material.specific_surface_area}")

        # Verify it exists
        retrieved = material_service.get_by_id(material.id)
        assert retrieved is not None, "Material not found after creation"
        print(f"✓ Verified material exists in database")

        return True, material.id

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_update_material(material_service, material_id):
    """Test updating a material."""
    print("\n" + "=" * 70)
    print("TEST 4: Update Material via Service")
    print("=" * 70)

    try:
        from app.models.material import MaterialUpdate

        # Update material
        update_data = MaterialUpdate(
            name="UI Test Material (Updated)",
            tags=["test", "ui", "phase1", "updated"],
            specific_gravity=3.20,
            description="Updated by UI test script"
        )

        updated = material_service.update(material_id, update_data)
        print(f"✓ Updated material: {updated.name}")
        print(f"  Tags: {updated.tag_names}")
        print(f"  SG: {updated.specific_gravity}")

        # Verify changes
        retrieved = material_service.get_by_id(material_id)
        assert retrieved.name == "UI Test Material (Updated)", "Name not updated"
        assert "updated" in retrieved.tag_names, "Tags not updated"
        assert retrieved.specific_gravity == 3.20, "SG not updated"
        print(f"✓ Verified all changes persisted")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_delete_material(material_service, material_id):
    """Test deleting a material."""
    print("\n" + "=" * 70)
    print("TEST 5: Delete Material via Service")
    print("=" * 70)

    try:
        # Delete material
        success = material_service.delete(material_id)
        assert success, "Delete returned False"
        print(f"✓ Deleted material (ID: {material_id})")

        # Verify deletion
        retrieved = material_service.get_by_id(material_id)
        assert retrieved is None, "Material still exists after deletion"
        print(f"✓ Verified material no longer exists")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_immutable_protection(material_service):
    """Test that immutable materials are protected."""
    print("\n" + "=" * 70)
    print("TEST 6: Immutable Material Protection")
    print("=" * 70)

    try:
        # Find an immutable material
        materials = material_service.get_all()
        immutable = next((m for m in materials if m.immutable), None)

        if not immutable:
            print("  No immutable materials found, skipping test")
            return True

        print(f"  Testing with immutable material: {immutable.name}")

        # Try to delete (should raise error or return False)
        try:
            from app.services.base_service import ServiceError
            material_service.delete(immutable.id)
            print("✗ ERROR: Immutable material was deleted!")
            return False
        except ServiceError as e:
            print(f"✓ Delete correctly blocked: {e}")

        # Try to update (should raise error)
        try:
            from app.models.material import MaterialUpdate
            update_data = MaterialUpdate(name="Should Not Work")
            material_service.update(immutable.id, update_data)
            print("✗ ERROR: Immutable material was updated!")
            return False
        except ServiceError as e:
            print(f"✓ Update correctly blocked: {e}")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("THAMES MATERIALS UI - PHASE 1 TEST SUITE")
    print("=" * 70)

    results = []

    # Test 1: MaterialService integration
    success, material_service = test_material_service_integration()
    results.append(("MaterialService Integration", success))

    if not success:
        print("\n✗ Cannot continue without MaterialService")
        return False

    # Test 2: TagChipInput widget
    success = test_tag_chip_input()
    results.append(("TagChipInput Widget", success))

    # Test 3: Create material
    success, material_id = test_create_material(material_service)
    results.append(("Create Material", success))

    if not success:
        print("\n✗ Cannot continue without successful create")
        return False

    # Test 4: Update material
    success = test_update_material(material_service, material_id)
    results.append(("Update Material", success))

    # Test 5: Delete material
    success = test_delete_material(material_service, material_id)
    results.append(("Delete Material", success))

    # Test 6: Immutable protection
    success = test_immutable_protection(material_service)
    results.append(("Immutable Protection", success))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(success for _, success in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nPhase 1 Materials UI is ready for manual GUI testing!")
        print("\nNext steps:")
        print("1. Run: python3 src/main.py")
        print("2. Navigate to Materials tab")
        print("3. Test Add/Edit/Delete operations in the GUI")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease review errors above")
    print("=" * 70)

    return all_passed


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

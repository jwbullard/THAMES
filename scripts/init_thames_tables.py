#!/usr/bin/env python3
"""
Initialize THAMES Database Tables

Creates the THAMES database tables (material, tag, material_tags, material_phase,
clinker_extension, material_component, mix_design) in the existing database.

This script is idempotent - safe to run multiple times.

Usage:
    python scripts/init_thames_tables.py [--db-path PATH]
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine, inspect
from app.database.base import Base
from app.models import Material, Tag, MaterialPhase, PSDData, ClinkerExtension, MaterialComponent
from app.models.mix_design import MixDesign


def init_thames_tables(db_path: Path, force: bool = False) -> None:
    """
    Initialize THAMES material tables.

    Args:
        db_path: Path to database file
        force: If True, drop existing tables first (DANGEROUS!)
    """
    print("=" * 70)
    print("THAMES DATABASE TABLES INITIALIZATION")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")

    # Create engine
    engine = create_engine(f'sqlite:///{db_path}')

    # Check which tables already exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    thames_tables = ['material', 'tag', 'material_tags', 'material_phase', 'clinker_extension', 'material_component', 'mix_design']
    existing_thames_tables = [t for t in thames_tables if t in existing_tables]
    missing_tables = [t for t in thames_tables if t not in existing_tables]

    if existing_thames_tables:
        print(f"\nFound existing THAMES tables: {existing_thames_tables}")
        if force:
            print("\n⚠ WARNING: Force mode enabled - dropping existing tables!")
            # Drop tables in reverse order due to foreign keys
            ClinkerExtension.__table__.drop(engine, checkfirst=True)
            MaterialComponent.__table__.drop(engine, checkfirst=True)
            MaterialPhase.__table__.drop(engine, checkfirst=True)
            Material.__table__.drop(engine, checkfirst=True)
            Tag.__table__.drop(engine, checkfirst=True)
            print("  ✓ Dropped existing tables")
        elif not missing_tables:
            print("  ✓ All tables already exist")
            print("\nVerification:")
            for table in thames_tables:
                print(f"  ✓ {table}")
            print("\n" + "=" * 70)
            print("NO CHANGES NEEDED")
            print("=" * 70)
            return
        else:
            print(f"\nMissing tables to create: {missing_tables}")

    # Create tables
    print("\nCreating THAMES tables:")
    print("  - material")
    print("  - tag")
    print("  - material_tags (association table)")
    print("  - material_phase")
    print("  - clinker_extension")
    print("  - material_component")
    print("  - mix_design")

    # Get the specific tables we want to create from Base.metadata
    tables_to_create = [
        Base.metadata.tables['material'],
        Base.metadata.tables['tag'],
        Base.metadata.tables['material_tags'],
        Base.metadata.tables['material_phase'],
        Base.metadata.tables['clinker_extension'],
        Base.metadata.tables['material_component'],
        Base.metadata.tables['mix_design'],
    ]

    # Create the tables
    Base.metadata.create_all(engine, tables=tables_to_create, checkfirst=True)

    print("\n✓ Tables created successfully")

    # Verify
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print("\nVerification:")
    for table in thames_tables:
        if table in existing_tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ❌ {table} (MISSING!)")

    print("\n" + "=" * 70)
    print("INITIALIZATION COMPLETE")
    print("=" * 70)
    print("\nReady to run migration script:")
    print("  python scripts/migrate_vcctl_materials.py --dry-run")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize THAMES material database tables"
    )

    parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to database file (default: auto-detect)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Drop and recreate existing tables (WARNING: destroys data!)'
    )

    args = parser.parse_args()

    # Find database
    if args.db_path:
        db_path = args.db_path
    else:
        # Auto-detect
        possible_paths = [
            Path(__file__).parent.parent / "src" / "data" / "database" / "thames.db",
            Path.home() / "Software" / "THAMES" / "src" / "data" / "database" / "thames.db",
        ]

        db_path = None
        for path in possible_paths:
            if path.exists():
                db_path = path
                break

        if not db_path:
            # Use first path as default (will be created)
            db_path = possible_paths[0]

    if not db_path.parent.exists():
        print(f"❌ Database directory does not exist: {db_path.parent}")
        sys.exit(1)

    # Confirm if force mode
    if args.force:
        print("\n⚠ WARNING: Force mode enabled!")
        print("This will DROP and RECREATE all THAMES material tables.")
        print("ALL MATERIAL DATA will be LOST!")
        response = input("\nAre you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)

    # Run initialization
    init_thames_tables(db_path, force=args.force)


if __name__ == '__main__':
    main()

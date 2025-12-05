#!/usr/bin/env python3
"""
Fix phase names in THAMES database to match GEMS database.

Updates:
- arcanite -> Arcanite
- thenardite -> Thenardite
- hemihydrate -> Bassanite

Run from the THAMES project root:
    python scripts/fix_phase_names.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Phase name mappings (old -> new)
PHASE_NAME_FIXES = {
    'arcanite': 'Arcanite',
    'thenardite': 'Thenardite',
    'hemihydrate': 'Bassanite',
}


def get_database_path() -> Path:
    """Get the THAMES database path."""
    # Check THAMES location first
    thames_db = Path.home() / 'Library/Application Support/THAMES/database/thames.db'
    if thames_db.exists():
        return thames_db

    # Fall back to VCCTL location
    vcctl_db = Path.home() / 'Library/Application Support/VCCTL/database/thames.db'
    if vcctl_db.exists():
        return vcctl_db

    raise FileNotFoundError("Could not find thames.db database")


def fix_phase_names():
    """Update phase names in the database."""
    db_path = get_database_path()
    print(f"Database: {db_path}")

    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        total_updated = 0

        for old_name, new_name in PHASE_NAME_FIXES.items():
            # Count affected rows
            result = session.execute(
                text("SELECT COUNT(*) FROM material_phase WHERE gem_phase_name = :old_name"),
                {'old_name': old_name}
            )
            count = result.scalar()

            if count > 0:
                print(f"Updating '{old_name}' -> '{new_name}': {count} phases")

                # Update the phase names
                session.execute(
                    text("UPDATE material_phase SET gem_phase_name = :new_name WHERE gem_phase_name = :old_name"),
                    {'old_name': old_name, 'new_name': new_name}
                )
                total_updated += count
            else:
                print(f"No phases found with name '{old_name}'")

        if total_updated > 0:
            session.commit()
            print(f"\n✓ Updated {total_updated} phase entries")
        else:
            print("\n✓ No updates needed - all phase names are correct")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    fix_phase_names()

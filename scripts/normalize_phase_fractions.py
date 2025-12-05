#!/usr/bin/env python3
"""
Normalize phase mass fractions in THAMES database.

Ensures all material phase fractions sum to 1.0.

Run from the THAMES project root:
    python scripts/normalize_phase_fractions.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


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


def normalize_phase_fractions():
    """Normalize phase mass fractions to sum to 1.0."""
    db_path = get_database_path()
    print(f"Database: {db_path}")

    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find all materials with non-normalized fractions
        result = session.execute(text('''
            SELECT m.id, m.name, SUM(mp.mass_fraction) as total
            FROM material m
            JOIN material_phase mp ON m.id = mp.material_id
            GROUP BY m.id
            HAVING ABS(total - 1.0) > 0.001
            ORDER BY m.name
        '''))

        materials_to_fix = list(result)

        if not materials_to_fix:
            print("\n✓ All materials already have normalized fractions")
            return

        print(f"\nFound {len(materials_to_fix)} materials to normalize:\n")

        for material_id, name, total in materials_to_fix:
            print(f"  {name}: {total:.6f} -> 1.000000")

            # Update each phase fraction for this material
            session.execute(
                text('''
                    UPDATE material_phase
                    SET mass_fraction = mass_fraction / :total
                    WHERE material_id = :material_id
                '''),
                {'total': total, 'material_id': material_id}
            )

        session.commit()
        print(f"\n✓ Normalized {len(materials_to_fix)} materials")

        # Verify the fix
        result = session.execute(text('''
            SELECT m.name, SUM(mp.mass_fraction) as total
            FROM material m
            JOIN material_phase mp ON m.id = mp.material_id
            GROUP BY m.id
            HAVING ABS(total - 1.0) > 0.001
        '''))
        remaining = list(result)

        if remaining:
            print(f"\n⚠ Warning: {len(remaining)} materials still not normalized")
        else:
            print("✓ Verification passed - all fractions now sum to 1.0")

    except Exception as e:
        session.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    normalize_phase_fractions()

#!/usr/bin/env python3
"""
VCCTL to THAMES Material Migration Script

Migrates cement and limestone materials from VCCTL database to THAMES
tag-based material system.

This script:
1. Reads VCCTL cement and limestone tables
2. Applies phase name mappings (C3S → Alite, etc.)
3. Creates THAMES Material records with tags
4. Creates MaterialPhase entries for phase composition
5. Links to existing PSDData
6. Optionally calculates specific gravity from GEMS database
7. Marks materials as immutable (read-only migrated data)

Usage:
    python scripts/migrate_vcctl_materials.py [options]

Options:
    --vcctl-db PATH     Path to VCCTL database (default: auto-detect)
    --thames-db PATH    Path to THAMES database (default: auto-detect)
    --dry-run           Show what would be migrated without writing to database
    --recalc-sg         Recalculate specific gravity from GEMS (default: use VCCTL values)
    --skip-cements      Skip cement migration
    --skip-limestones   Skip limestone migration
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.base import Base
from app.models import (
    Cement as VCCTLCement,
    Limestone as VCCTLLimestone,
    Material,
    Tag,
    MaterialPhase,
    PSDData,
    ClinkerExtension
)
from app.config.phase_mappings import VCCTL_TO_GEMS_CEMENT
from app.services.gems_parser_service import GEMSParserService


class MaterialMigrator:
    """Migrates materials from VCCTL to THAMES database."""

    def __init__(
        self,
        vcctl_db_path: Path,
        thames_db_path: Path,
        gems_data_dir: Path,
        dry_run: bool = False,
        recalc_sg: bool = False
    ):
        """
        Initialize the migrator.

        Args:
            vcctl_db_path: Path to VCCTL database
            thames_db_path: Path to THAMES database
            gems_data_dir: Path to GEMS data directory
            dry_run: If True, don't write to database
            recalc_sg: If True, recalculate specific gravity from GEMS
        """
        self.vcctl_db_path = vcctl_db_path
        self.thames_db_path = thames_db_path
        self.gems_data_dir = gems_data_dir
        self.dry_run = dry_run
        self.recalc_sg = recalc_sg

        # Initialize GEMS parser for density calculations
        self.gems_parser = GEMSParserService(gems_data_dir)

        # Create database sessions
        self.vcctl_engine = create_engine(f'sqlite:///{vcctl_db_path}')
        self.thames_engine = create_engine(f'sqlite:///{thames_db_path}')

        VCCTLSession = sessionmaker(bind=self.vcctl_engine)
        THAMESSession = sessionmaker(bind=self.thames_engine)

        self.vcctl_session = VCCTLSession()
        self.thames_session = THAMESSession()

        # Statistics
        self.stats = {
            'cements_migrated': 0,
            'limestones_migrated': 0,
            'materials_created': 0,
            'tags_created': 0,
            'phases_created': 0,
            'clinkers_created': 0,
            'correlations_migrated': 0,
            'errors': []
        }

    def _get_or_create_tag(self, tag_name: str) -> Tag:
        """Get or create a tag."""
        tag = self.thames_session.query(Tag).filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            if not self.dry_run:
                self.thames_session.add(tag)
                self.stats['tags_created'] += 1
        return tag

    def _create_material_phases(
        self,
        material: Material,
        phase_fractions: Dict[str, float]
    ) -> List[MaterialPhase]:
        """
        Create MaterialPhase entries for a material.

        Args:
            material: Material instance
            phase_fractions: Dict of {gem_phase_name: mass_fraction}

        Returns:
            List of MaterialPhase instances
        """
        phases = []
        for gem_phase_name, mass_fraction in phase_fractions.items():
            if mass_fraction > 0:
                phase = MaterialPhase(
                    material=material,
                    gem_phase_name=gem_phase_name,
                    mass_fraction=mass_fraction
                )
                phases.append(phase)
                if not self.dry_run:
                    self.thames_session.add(phase)
                self.stats['phases_created'] += 1

        return phases

    def _create_clinker_extension(
        self,
        material: Material,
        vcctl_cement: VCCTLCement
    ) -> Optional[ClinkerExtension]:
        """
        Create ClinkerExtension for a cement material.

        Args:
            material: Material instance
            vcctl_cement: VCCTL Cement instance with surface fractions and correlations

        Returns:
            ClinkerExtension instance or None if no data
        """
        try:
            # Check if we have surface fractions or correlation data
            has_surface_fractions = any([
                vcctl_cement.c3s_surface_fraction,
                vcctl_cement.c2s_surface_fraction,
                vcctl_cement.c3a_surface_fraction,
                vcctl_cement.c4af_surface_fraction,
                vcctl_cement.k2so4_surface_fraction,
                vcctl_cement.na2so4_surface_fraction
            ])

            has_correlations = any([
                vcctl_cement.sil,
                vcctl_cement.c3s,
                vcctl_cement.alu,
                vcctl_cement.c3a,
                vcctl_cement.c4f,  # Note: VCCTL uses c4f
                vcctl_cement.k2o,
                vcctl_cement.n2o
            ])

            if not has_surface_fractions and not has_correlations:
                return None

            # Create clinker extension
            clinker_ext = ClinkerExtension(
                material_id=material.id,
                # Surface area fractions
                c3s_surface_fraction=vcctl_cement.c3s_surface_fraction,
                c2s_surface_fraction=vcctl_cement.c2s_surface_fraction,
                c3a_surface_fraction=vcctl_cement.c3a_surface_fraction,
                c4af_surface_fraction=vcctl_cement.c4af_surface_fraction,
                k2so4_surface_fraction=vcctl_cement.k2so4_surface_fraction,
                na2so4_surface_fraction=vcctl_cement.na2so4_surface_fraction,
                # Correlation functions (note: use correlation_ prefix)
                correlation_sil=vcctl_cement.sil,
                correlation_c3s=vcctl_cement.c3s,
                correlation_alu=vcctl_cement.alu,
                correlation_c3a=vcctl_cement.c3a,
                correlation_c4af=vcctl_cement.c4f,  # Map c4f to c4af
                correlation_k2o=vcctl_cement.k2o,
                correlation_n2o=vcctl_cement.n2o
            )

            if not self.dry_run:
                self.thames_session.add(clinker_ext)

            self.stats['clinkers_created'] += 1

            # Count correlations migrated
            correlation_count = sum([
                1 for corr in [vcctl_cement.sil, vcctl_cement.c3s, vcctl_cement.alu,
                               vcctl_cement.c3a, vcctl_cement.c4f, vcctl_cement.k2o,
                               vcctl_cement.n2o]
                if corr is not None
            ])
            self.stats['correlations_migrated'] += correlation_count

            print(f"    ✓ Clinker extension created: {correlation_count} correlations")

            return clinker_ext

        except Exception as e:
            error_msg = f"Error creating clinker extension for {material.name}: {e}"
            print(f"    ⚠ {error_msg}")
            self.stats['errors'].append(error_msg)
            return None

    def _calculate_specific_gravity(
        self,
        phase_fractions: Dict[str, float],
        vcctl_sg: Optional[float] = None
    ) -> float:
        """
        Calculate specific gravity for material.

        Args:
            phase_fractions: Dict of {gem_phase_name: mass_fraction}
            vcctl_sg: Original VCCTL specific gravity (fallback)

        Returns:
            Specific gravity value
        """
        if self.recalc_sg:
            # Calculate from GEMS database
            calculated_sg = self.gems_parser.calculate_material_specific_gravity(phase_fractions)
            if calculated_sg is not None:
                return calculated_sg

        # Use VCCTL value as fallback
        return vcctl_sg if vcctl_sg else 3.15

    def migrate_cement(self, vcctl_cement: VCCTLCement) -> Optional[Material]:
        """
        Migrate a single cement from VCCTL to THAMES.

        Args:
            vcctl_cement: VCCTL Cement instance

        Returns:
            THAMES Material instance, or None if migration fails
        """
        try:
            print(f"\n  Migrating cement: {vcctl_cement.name}")

            # Check if already exists
            existing = self.thames_session.query(Material).filter_by(
                name=vcctl_cement.name
            ).first()
            if existing:
                print(f"    ⚠ Already exists, skipping")
                return None

            # Build phase composition using phase mappings
            phase_fractions = {}

            # Main cement phases
            if vcctl_cement.c3s_mass_fraction:
                phase_fractions['Alite'] = vcctl_cement.c3s_mass_fraction
            if vcctl_cement.c2s_mass_fraction:
                phase_fractions['Belite'] = vcctl_cement.c2s_mass_fraction
            if vcctl_cement.c3a_mass_fraction:
                phase_fractions['Aluminate'] = vcctl_cement.c3a_mass_fraction
            if vcctl_cement.c4af_mass_fraction:
                phase_fractions['Ferrite'] = vcctl_cement.c4af_mass_fraction

            # Gypsum forms
            if vcctl_cement.dihyd:
                phase_fractions['Gypsum'] = vcctl_cement.dihyd
            if vcctl_cement.hemihyd:
                phase_fractions['hemihydrate'] = vcctl_cement.hemihyd
            if vcctl_cement.anhyd:
                phase_fractions['Anhydrite'] = vcctl_cement.anhyd

            # Sulfates
            if vcctl_cement.k2so4_mass_fraction:
                phase_fractions['arcanite'] = vcctl_cement.k2so4_mass_fraction
            if vcctl_cement.na2so4_mass_fraction:
                phase_fractions['thenardite'] = vcctl_cement.na2so4_mass_fraction

            if not phase_fractions:
                print(f"    ⚠ No phase data, skipping")
                return None

            # Calculate total phase fraction
            total_fraction = sum(phase_fractions.values())
            print(f"    Phase composition: {len(phase_fractions)} phases, total = {total_fraction:.3f}")

            # Calculate specific gravity
            specific_gravity = self._calculate_specific_gravity(
                phase_fractions,
                vcctl_cement.specific_gravity
            )
            print(f"    Specific gravity: {specific_gravity:.3f}")

            # Determine if material contains clinker phases based on actual composition
            # Only the four main clinker minerals define a material as containing clinker
            # (arcanite and thenardite are alkali sulfates that can appear but don't define clinker)
            clinker_phase_names = {'Alite', 'Belite', 'Aluminate', 'Ferrite'}
            has_clinker = bool(set(phase_fractions.keys()) & clinker_phase_names)
            print(f"    Has clinker phases: {has_clinker}")

            # Create Material
            material = Material(
                name=vcctl_cement.name,
                specific_gravity=specific_gravity,
                specific_surface_area=vcctl_cement.specific_surface_area,
                psd_data_id=vcctl_cement.psd_data_id,
                description=vcctl_cement.description,
                source=vcctl_cement.source,
                notes=vcctl_cement.notes,
                immutable=True,  # Mark as read-only migrated material
                is_clinker=False,  # Cement is NOT pure clinker
                has_clinker=has_clinker  # Determined by actual phase composition
            )

            # Add tags
            cement_tag = self._get_or_create_tag('cement')
            migrated_tag = self._get_or_create_tag('migrated-vcctl')
            material.tags = [cement_tag, migrated_tag]

            if not self.dry_run:
                self.thames_session.add(material)
                self.thames_session.flush()  # Get ID for phase creation

            # Create phase entries
            phases = self._create_material_phases(material, phase_fractions)
            print(f"    ✓ Created {len(phases)} phase entries")

            # Create clinker extension (surface fractions + correlations)
            clinker_ext = self._create_clinker_extension(material, vcctl_cement)

            self.stats['materials_created'] += 1
            self.stats['cements_migrated'] += 1

            return material

        except Exception as e:
            error_msg = f"Error migrating cement {vcctl_cement.name}: {e}"
            print(f"    ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return None

    def migrate_limestone(self, vcctl_limestone: VCCTLLimestone) -> Optional[Material]:
        """
        Migrate a single limestone from VCCTL to THAMES.

        Args:
            vcctl_limestone: VCCTL Limestone instance

        Returns:
            THAMES Material instance, or None if migration fails
        """
        try:
            print(f"\n  Migrating limestone: {vcctl_limestone.name}")

            # Check if already exists
            existing = self.thames_session.query(Material).filter_by(
                name=vcctl_limestone.name
            ).first()
            if existing:
                print(f"    ⚠ Already exists, skipping")
                return None

            # Limestone is pure Calcite phase
            phase_fractions = {
                'Calcite': 1.0
            }

            # Calculate specific gravity
            specific_gravity = self._calculate_specific_gravity(
                phase_fractions,
                vcctl_limestone.specific_gravity
            )
            print(f"    Specific gravity: {specific_gravity:.3f}")

            # Create Material
            material = Material(
                name=vcctl_limestone.name,
                specific_gravity=specific_gravity,
                specific_surface_area=vcctl_limestone.specific_surface_area,
                psd_data_id=vcctl_limestone.psd_data_id,
                description=vcctl_limestone.description,
                source=vcctl_limestone.source,
                notes=vcctl_limestone.notes,
                immutable=True
            )

            # Add tags
            limestone_tag = self._get_or_create_tag('limestone')
            migrated_tag = self._get_or_create_tag('migrated-vcctl')
            material.tags = [limestone_tag, migrated_tag]

            if not self.dry_run:
                self.thames_session.add(material)
                self.thames_session.flush()

            # Create phase entry
            phases = self._create_material_phases(material, phase_fractions)
            print(f"    ✓ Created {len(phases)} phase entry")

            self.stats['materials_created'] += 1
            self.stats['limestones_migrated'] += 1

            return material

        except Exception as e:
            error_msg = f"Error migrating limestone {vcctl_limestone.name}: {e}"
            print(f"    ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return None

    def migrate_all_cements(self) -> None:
        """Migrate all cements from VCCTL database."""
        print("\n" + "=" * 70)
        print("MIGRATING CEMENTS")
        print("=" * 70)

        cements = self.vcctl_session.query(VCCTLCement).all()
        print(f"\nFound {len(cements)} cements in VCCTL database")

        for cement in cements:
            self.migrate_cement(cement)

        print(f"\n✓ Migrated {self.stats['cements_migrated']} cements")

    def migrate_all_limestones(self) -> None:
        """Migrate all limestones from VCCTL database."""
        print("\n" + "=" * 70)
        print("MIGRATING LIMESTONES")
        print("=" * 70)

        limestones = self.vcctl_session.query(VCCTLLimestone).all()
        print(f"\nFound {len(limestones)} limestones in VCCTL database")

        for limestone in limestones:
            self.migrate_limestone(limestone)

        print(f"\n✓ Migrated {self.stats['limestones_migrated']} limestones")

    def run(self, skip_cements: bool = False, skip_limestones: bool = False) -> None:
        """
        Run the migration.

        Args:
            skip_cements: Skip cement migration
            skip_limestones: Skip limestone migration
        """
        print("\n" + "=" * 70)
        print("VCCTL TO THAMES MATERIAL MIGRATION")
        print("=" * 70)
        print(f"\nVCCTL Database:  {self.vcctl_db_path}")
        print(f"THAMES Database: {self.thames_db_path}")
        print(f"GEMS Data:       {self.gems_data_dir}")
        print(f"Dry Run:         {self.dry_run}")
        print(f"Recalculate SG:  {self.recalc_sg}")

        try:
            if not skip_cements:
                self.migrate_all_cements()

            if not skip_limestones:
                self.migrate_all_limestones()

            # Commit changes
            if not self.dry_run:
                self.thames_session.commit()
                print("\n✓ Changes committed to database")
            else:
                print("\n⚠ DRY RUN - No changes written to database")

            # Print summary
            self.print_summary()

        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            if not self.dry_run:
                self.thames_session.rollback()
            raise

        finally:
            self.vcctl_session.close()
            self.thames_session.close()

    def print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"\nMaterials created:      {self.stats['materials_created']}")
        print(f"  - Cements:            {self.stats['cements_migrated']}")
        print(f"  - Limestones:         {self.stats['limestones_migrated']}")
        print(f"Tags created:           {self.stats['tags_created']}")
        print(f"Phase entries created:  {self.stats['phases_created']}")
        print(f"Clinkers created:       {self.stats['clinkers_created']}")
        print(f"Correlations migrated:  {self.stats['correlations_migrated']}")

        if self.stats['errors']:
            print(f"\n⚠ Errors encountered:   {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")
        else:
            print(f"\n✓ No errors")


def find_vcctl_database() -> Optional[Path]:
    """Auto-detect VCCTL database path."""
    possible_paths = [
        Path.home() / "Software" / "vcctl-gtk" / "src" / "data" / "database" / "vcctl.db",
        Path.home() / "vcctl-gtk" / "src" / "data" / "database" / "vcctl.db",
        Path("/Users/jwbullard/Software/vcctl-gtk/src/data/database/vcctl.db"),
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def find_thames_database() -> Optional[Path]:
    """Auto-detect THAMES database path."""
    possible_paths = [
        Path.home() / "Software" / "THAMES" / "src" / "data" / "database" / "thames.db",
        Path.home() / "THAMES" / "src" / "data" / "database" / "thames.db",
        Path(__file__).parent.parent / "src" / "data" / "database" / "thames.db",
    ]

    for path in possible_paths:
        # Return path even if it doesn't exist (will be created)
        return path

    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate materials from VCCTL to THAMES database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--vcctl-db',
        type=Path,
        help='Path to VCCTL database (default: auto-detect)'
    )
    parser.add_argument(
        '--thames-db',
        type=Path,
        help='Path to THAMES database (default: auto-detect)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without writing to database'
    )
    parser.add_argument(
        '--recalc-sg',
        action='store_true',
        help='Recalculate specific gravity from GEMS (default: use VCCTL values)'
    )
    parser.add_argument(
        '--skip-cements',
        action='store_true',
        help='Skip cement migration'
    )
    parser.add_argument(
        '--skip-limestones',
        action='store_true',
        help='Skip limestone migration'
    )

    args = parser.parse_args()

    # Find databases
    vcctl_db = args.vcctl_db or find_vcctl_database()
    thames_db = args.thames_db or find_thames_database()

    if not vcctl_db or not vcctl_db.exists():
        print(f"❌ VCCTL database not found: {vcctl_db}")
        print("\nPlease specify path with --vcctl-db")
        sys.exit(1)

    if not thames_db:
        print(f"❌ THAMES database path not found")
        print("\nPlease specify path with --thames-db")
        sys.exit(1)

    # Find GEMS data directory
    gems_data_dir = Path(__file__).parent.parent / "src" / "data" / "gems"
    if not gems_data_dir.exists():
        print(f"❌ GEMS data directory not found: {gems_data_dir}")
        sys.exit(1)

    # Create migrator and run
    migrator = MaterialMigrator(
        vcctl_db_path=vcctl_db,
        thames_db_path=thames_db,
        gems_data_dir=gems_data_dir,
        dry_run=args.dry_run,
        recalc_sg=args.recalc_sg
    )

    migrator.run(
        skip_cements=args.skip_cements,
        skip_limestones=args.skip_limestones
    )


if __name__ == '__main__':
    main()

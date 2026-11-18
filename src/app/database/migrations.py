#!/usr/bin/env python3
"""
Database Migration Support for VCCTL

Provides database migration functionality for schema updates and data seeding.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.exc import SQLAlchemyError

from app.database.base import Base
from app.database.service import DatabaseService


class Migration(Base):
    """Model to track applied migrations."""
    
    __tablename__ = 'migrations'
    
    version = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    applied_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Migration(version='{self.version}', name='{self.name}')>"


class MigrationManager:
    """Manages database migrations and schema updates."""
    
    def __init__(self, db_service: DatabaseService):
        """Initialize the migration manager."""
        self.db_service = db_service
        self.logger = logging.getLogger('VCCTL.Migrations')
        # (Before alpha-4.3 this created an unused 'migration_scripts' folder
        # next to this file. Inside the app bundle that folder cannot be
        # created, so the constructor raised and no migration ever ran in a
        # packaged release.)
    
    def initialize_migration_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        try:
            # Create the migrations table
            Migration.__table__.create(bind=self.db_service.engine, checkfirst=True)
            self.logger.info("Migration tracking table initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize migration table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            with self.db_service.get_read_only_session() as session:
                migrations = session.query(Migration).order_by(Migration.applied_at).all()
                return [m.version for m in migrations]
        except Exception as e:
            self.logger.error(f"Failed to get applied migrations: {e}")
            return []
    
    def mark_migration_applied(self, version: str, name: str) -> None:
        """Mark a migration as applied."""
        try:
            with self.db_service.get_session() as session:
                migration = Migration(version=version, name=name)
                session.add(migration)
                session.commit()
                self.logger.info(f"Migration {version} marked as applied")
        except Exception as e:
            self.logger.error(f"Failed to mark migration {version} as applied: {e}")
            raise
    
    def create_initial_schema(self) -> None:
        """Create the initial database schema."""
        try:
            self.logger.info("Creating initial database schema...")
            
            # Create all tables
            self.db_service.create_all_tables()
            
            # Initialize migration table
            self.initialize_migration_table()
            
            # Mark initial schema as applied
            self.mark_migration_applied("001", "Initial schema")
            
            self.logger.info("Initial schema created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create initial schema: {e}")
            raise
    
    def run_sql_migration(self, sql_script: str, version: str, name: str) -> None:
        """Run a SQL migration script."""
        try:
            self.logger.info(f"Running migration {version}: {name}")
            
            with self.db_service.get_session() as session:
                # Split script into individual statements
                statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        session.execute(text(statement))
                
                # Mark migration as applied
                migration = Migration(version=version, name=name)
                session.add(migration)
                session.commit()
            
            self.logger.info(f"Migration {version} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Migration {version} failed: {e}")
            raise
    
    def seed_initial_data(self) -> None:
        """Seed the database with initial data."""
        try:
            self.logger.info("Seeding initial data...")
            
            # Check if data has already been seeded
            applied_migrations = self.get_applied_migrations()
            if "seed_001" in applied_migrations:
                self.logger.info("Initial data already seeded")
                return
            
            # Create seed data
            self._create_seed_data()
            
            # Mark seeding as completed
            self.mark_migration_applied("seed_001", "Initial data seeding")
            
            self.logger.info("Initial data seeding completed")
            
        except Exception as e:
            self.logger.error(f"Failed to seed initial data: {e}")
            raise
    
    def _create_seed_data(self) -> None:
        """Create basic seed data for the application."""
        seed_operations = [
            self._create_particle_shape_sets,
            self._create_basic_aggregates,
            self._create_basic_cements,
            self._create_basic_fly_ash,
            self._create_basic_slag,
            self._create_basic_fillers,
        ]
        
        for operation in seed_operations:
            try:
                operation()
            except Exception as e:
                self.logger.error(f"Failed to create seed data with {operation.__name__}: {e}")
    
    def _create_particle_shape_sets(self) -> None:
        """Create basic particle shape sets."""
        from app.models import ParticleShapeSet
        
        shapes = ['sphere', 'ellipsoid', 'cube', 'irregular', 'angular', 'rounded']
        
        with self.db_service.get_session() as session:
            for shape in shapes:
                existing = session.query(ParticleShapeSet).filter_by(name=shape).first()
                if not existing:
                    shape_set = ParticleShapeSet(name=shape)
                    session.add(shape_set)
    
    def _create_basic_aggregates(self) -> None:
        """Create basic aggregate materials."""
        from app.models import Aggregate
        
        aggregates = [
            {'display_name': 'standard_coarse', 'name': 'Standard Coarse Aggregate', 'type': 1, 'specific_gravity': 2.65},
            {'display_name': 'standard_fine', 'name': 'Standard Fine Aggregate', 'type': 2, 'specific_gravity': 2.60},
        ]
        
        with self.db_service.get_session() as session:
            for agg_data in aggregates:
                existing = session.query(Aggregate).filter_by(display_name=agg_data['display_name']).first()
                if not existing:
                    aggregate = Aggregate(**agg_data)
                    session.add(aggregate)
    
    def _create_basic_cements(self) -> None:
        """Create basic cement materials."""
        from app.models import Cement
        
        cements = [
            {'name': 'portland_cement_type_i', 'psd': 'cement141', 'alkali_file': 'lowalkali'},
            {'name': 'portland_cement_type_ii', 'psd': 'cement141', 'alkali_file': 'lowalkali'},
        ]
        
        with self.db_service.get_session() as session:
            for cement_data in cements:
                existing = session.query(Cement).filter_by(name=cement_data['name']).first()
                if not existing:
                    cement = Cement(**cement_data)
                    session.add(cement)
    
    def _create_basic_fly_ash(self) -> None:
        """Create basic fly ash materials."""
        from app.models import FlyAsh
        
        fly_ashes = [
            {'name': 'class_f_fly_ash', 'specific_gravity': 2.77, 'psd': 'cement141'},
            {'name': 'class_c_fly_ash', 'specific_gravity': 2.80, 'psd': 'cement141'},
        ]
        
        with self.db_service.get_session() as session:
            for fa_data in fly_ashes:
                existing = session.query(FlyAsh).filter_by(name=fa_data['name']).first()
                if not existing:
                    fly_ash = FlyAsh(**fa_data)
                    session.add(fly_ash)
    
    def _create_basic_slag(self) -> None:
        """Create basic slag materials."""
        from app.models import Slag
        
        slags = [
            {'name': 'ggbs_grade_80', 'specific_gravity': 2.87, 'psd': 'cement141'},
            {'name': 'ggbs_grade_100', 'specific_gravity': 2.90, 'psd': 'cement141'},
        ]
        
        with self.db_service.get_session() as session:
            for slag_data in slags:
                existing = session.query(Slag).filter_by(name=slag_data['name']).first()
                if not existing:
                    slag = Slag(**slag_data)
                    session.add(slag)
    
    def _create_basic_fillers(self) -> None:
        """Create basic inert filler materials."""
        from app.models import InertFiller
        
        fillers = [
            {'name': 'quartz', 'specific_gravity': 2.65, 'psd': 'cement141'},
            {'name': 'limestone', 'specific_gravity': 2.70, 'psd': 'cement141'},
        ]
        
        with self.db_service.get_session() as session:
            for filler_data in fillers:
                existing = session.query(InertFiller).filter_by(name=filler_data['name']).first()
                if not existing:
                    filler = InertFiller(**filler_data)
                    session.add(filler)
    
    def _apply_glass_phase_am_rename_migration(self) -> None:
        """Rename bare glass phases to (am) form in material_phase table.

        Session 59 renamed 5 glass phases (C2AS, CA2S, CAS, CAS2, K6A2S) to
        (am) suffix in GEMS DCH/DBR, ChemicalSystem.cc hardcoded initializers,
        and simparams_service.py::_get_thamesname, but did NOT write a matching
        migration for material_phase rows in existing users' DBs. Without this
        rename, any material composition referencing a bare glass name produces
        microstructure phases with empty gemphasename, and thames.exe fails at
        ChemicalSystem::parseMicroPhases (S59 Bug A resurfacing via a different
        trigger path).

        Idempotent: only rewrites rows that still have bare names; new installs
        already have the (am) form in the seed DB.
        """
        try:
            self.logger.info("Applying glass-phase (am) rename migration...")
            sql = """
            UPDATE material_phase SET gem_phase_name = 'C2AS(am)'  WHERE gem_phase_name = 'C2AS';
            UPDATE material_phase SET gem_phase_name = 'CA2S(am)'  WHERE gem_phase_name = 'CA2S';
            UPDATE material_phase SET gem_phase_name = 'CAS(am)'   WHERE gem_phase_name = 'CAS';
            UPDATE material_phase SET gem_phase_name = 'CAS2(am)'  WHERE gem_phase_name = 'CAS2';
            UPDATE material_phase SET gem_phase_name = 'K6A2S(am)' WHERE gem_phase_name = 'K6A2S';
            """
            self.run_sql_migration(
                sql,
                "20260824_01_glass_phase_am_rename",
                "Rename bare glass phases to (am) form in material_phase (S59 follow-up)"
            )
        except Exception as e:
            self.logger.error(f"Failed to apply glass-phase (am) rename migration: {e}")
            raise

    def _apply_clear_orphan_aggregate_names_migration(self) -> None:
        """Clear orphan aggregate name references in the mix_design table.

        Session 64 changed the Mix Design panel to default the fine/coarse
        aggregate dropdowns to the "-- Select --" placeholder instead of
        auto-selecting the last alphabetical entry. Every mix created under
        the old default silently persisted a real aggregate name
        (MA114F-3-fine, MA99BC-5-coarse) with mass = 0. That combination
        triggered the "aggregate specified but mass is zero" warning
        dialog on every Create Mix click, and produced Aggregate:8 entries
        in downstream phase mappings for Portland-only mixes.

        This migration clears the orphan aggregate names on existing
        databases so testers upgrading in place from alpha-2 / alpha-2.1
        don't keep hitting the dialog on their pre-existing mixes.

        Idempotent: the WHERE clause excludes rows that are already clean
        (empty or NULL name, or non-zero mass). Re-running is a no-op.

        Safety: intentional-concrete mixes are untouched because the
        `fine_aggregate_mass = 0.0` guard eliminates them; the surviving
        mixes with mass > 0 keep their aggregate name unchanged.
        """
        try:
            self.logger.info("Applying orphan-aggregate-name cleanup migration...")
            sql = """
            UPDATE mix_design
               SET fine_aggregate_name = ''
             WHERE fine_aggregate_name != ''
               AND fine_aggregate_name IS NOT NULL
               AND (fine_aggregate_mass IS NULL OR fine_aggregate_mass = 0.0);
            UPDATE mix_design
               SET coarse_aggregate_name = ''
             WHERE coarse_aggregate_name != ''
               AND coarse_aggregate_name IS NOT NULL
               AND (coarse_aggregate_mass IS NULL OR coarse_aggregate_mass = 0.0);
            """
            self.run_sql_migration(
                sql,
                "20260827_01_clear_orphan_aggregate_names",
                "Clear fine/coarse aggregate names when mass = 0 (S64 follow-up)"
            )
        except Exception as e:
            self.logger.error(f"Failed to apply orphan-aggregate cleanup migration: {e}")
            raise

    def _apply_mix_design_migration(self) -> None:
        """Apply migration to add mix_design table."""
        try:
            self.logger.info("Creating mix_design table...")
            
            # Create the SQL for mix_design table
            mix_design_sql = """
            CREATE TABLE IF NOT EXISTS mix_design (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL UNIQUE,
                description TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                water_binder_ratio REAL NOT NULL DEFAULT 0.0,
                total_water_content REAL NOT NULL DEFAULT 0.0,
                air_content REAL NOT NULL DEFAULT 0.0,
                water_volume_fraction REAL NOT NULL DEFAULT 0.0,
                air_volume_fraction REAL NOT NULL DEFAULT 0.0,
                system_size INTEGER NOT NULL DEFAULT 100,
                random_seed INTEGER NOT NULL DEFAULT -1,
                cement_shape_set VARCHAR(64) DEFAULT 'spherical',
                aggregate_shape_set VARCHAR(64) DEFAULT 'spherical',
                components TEXT NOT NULL DEFAULT '[]',
                calculated_properties TEXT DEFAULT '{}',
                notes TEXT,
                is_template BOOLEAN NOT NULL DEFAULT 0
            )
            """
            
            # Run the migration
            self.run_sql_migration(mix_design_sql, "002_add_mix_design_table", "Add mix_design table for saved mix designs")
            
            # Create some template mix designs
            self._seed_template_mix_designs()
            
            self.logger.info("mix_design table migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to apply mix_design migration: {e}")
            raise
    
    def _seed_template_mix_designs(self) -> None:
        """Create template mix designs for users."""
        try:
            self.logger.info("Seeding template mix designs...")
            
            template_designs = [
                {
                    'name': 'Standard Cement Paste (W/B=0.40)',
                    'description': 'Basic cement paste template with W/B ratio of 0.40',
                    'water_binder_ratio': 0.40,
                    'total_water_content': 400.0,
                    'air_content': 0.0,
                    'water_volume_fraction': 0.40,
                    'air_volume_fraction': 0.0,
                    'system_size': 100,
                    'random_seed': -1,
                    'cement_shape_set': 'spherical',
                    'aggregate_shape_set': 'spherical',
                    'components': '[{"material_name": "cement140", "material_type": "CEMENT", "mass_fraction": 1.0, "volume_fraction": 0.6, "specific_gravity": 3.15}]',
                    'calculated_properties': '{"paste_volume_fraction": 1.0, "powder_volume_fraction": 0.6, "aggregate_volume_fraction": 0.0, "binder_content": 1000.0, "water_content": 400.0}',
                    'notes': 'Template for cement paste studies and microstructure generation',
                    'is_template': 1
                },
                {
                    'name': 'High Performance Paste (W/B=0.30)',
                    'description': 'High performance cement paste with low W/B ratio',
                    'water_binder_ratio': 0.30,
                    'total_water_content': 300.0,
                    'air_content': 0.0,
                    'water_volume_fraction': 0.30,
                    'air_volume_fraction': 0.0,
                    'system_size': 100,
                    'random_seed': -1,
                    'cement_shape_set': 'spherical',
                    'aggregate_shape_set': 'spherical',
                    'components': '[{"material_name": "cement140", "material_type": "CEMENT", "mass_fraction": 1.0, "volume_fraction": 0.7, "specific_gravity": 3.15}]',
                    'calculated_properties': '{"paste_volume_fraction": 1.0, "powder_volume_fraction": 0.7, "aggregate_volume_fraction": 0.0, "binder_content": 1000.0, "water_content": 300.0}',
                    'notes': 'High performance paste for durability studies',
                    'is_template': 1
                },
                {
                    'name': 'Cement + Fly Ash Blend (W/B=0.45)',
                    'description': 'Binary paste with 20% fly ash replacement',
                    'water_binder_ratio': 0.45,
                    'total_water_content': 450.0,
                    'air_content': 0.0,
                    'water_volume_fraction': 0.45,
                    'air_volume_fraction': 0.0,
                    'system_size': 100,
                    'random_seed': -1,
                    'cement_shape_set': 'spherical',
                    'aggregate_shape_set': 'spherical',
                    'components': '[{"material_name": "cement140", "material_type": "CEMENT", "mass_fraction": 0.8, "volume_fraction": 0.48, "specific_gravity": 3.15}, {"material_name": "fa80", "material_type": "FLYASH", "mass_fraction": 0.2, "volume_fraction": 0.12, "specific_gravity": 2.2}]',
                    'calculated_properties': '{"paste_volume_fraction": 1.0, "powder_volume_fraction": 0.6, "aggregate_volume_fraction": 0.0, "binder_content": 1000.0, "water_content": 450.0}',
                    'notes': 'Binary paste for sustainability studies',
                    'is_template': 1
                }
            ]
            
            insert_statements = []
            for design in template_designs:
                values = []
                for key in ['name', 'description', 'water_binder_ratio', 'total_water_content', 'air_content', 
                           'water_volume_fraction', 'air_volume_fraction', 'system_size', 'random_seed',
                           'cement_shape_set', 'aggregate_shape_set', 'components', 'calculated_properties', 
                           'notes', 'is_template']:
                    value = design[key]
                    if isinstance(value, str):
                        # Escape single quotes in strings
                        value = value.replace("'", "''")
                        values.append(f"'{value}'")
                    elif value is None:
                        values.append('NULL')
                    else:
                        values.append(str(value))
                
                insert_sql = f"""
                INSERT OR IGNORE INTO mix_design 
                (name, description, water_binder_ratio, total_water_content, air_content, 
                 water_volume_fraction, air_volume_fraction, system_size, random_seed,
                 cement_shape_set, aggregate_shape_set, components, calculated_properties, 
                 notes, is_template, created_at, updated_at)
                VALUES ({', '.join(values)}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                insert_statements.append(insert_sql)
            
            # Execute all insert statements
            with self.db_service.get_session() as session:
                for statement in insert_statements:
                    try:
                        session.execute(text(statement))
                    except Exception as e:
                        self.logger.warning(f"Failed to insert template mix design: {e}")
                        # Continue with other templates
            
            self.logger.info("Template mix designs seeded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to seed template mix designs: {e}")
            # Don't raise - this is optional seeding
    
    def check_database_version(self) -> Dict[str, Any]:
        """Check the current database version and status."""
        version_info = {
            'initialized': False,
            'current_version': None,
            'applied_migrations': [],
            'schema_exists': False
        }
        
        try:
            # Check if migration table exists
            with self.db_service.get_read_only_session() as session:
                try:
                    result = session.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'"
                    ))
                    if result.fetchone():
                        version_info['schema_exists'] = True
                        version_info['initialized'] = True
                        
                        # Get applied migrations
                        applied_migrations = self.get_applied_migrations()
                        version_info['applied_migrations'] = applied_migrations
                        
                        if applied_migrations:
                            version_info['current_version'] = applied_migrations[-1]
                
                except Exception:
                    # Migration table doesn't exist
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to check database version: {e}")
        
        return version_info
    
    def _apply_grading_templates_percent_retained_migration(self) -> None:
        """Correct the shipped grading templates and delete two junk ones.

        Templates store individual % retained on each sieve (the editor shows
        cumulative % passing and converts).  Two shipped templates were wrong:

        - "ASTM C-33 Fine Aggregate" held the C 33 LOWER limits as cumulative
          % passing (summing to 262), so every consumer read most of the sand
          as sitting on the coarsest sieves.  Now the mid-band of the C 33
          limits as % retained; material passing 0.15 mm sits on 0.075 mm.
        - "ASTM #57 Stone" put all of the stone between 19 and 31.5 mm.  Now
          the mid-band of the C 33 #57 limits; material passing 2.36 mm sits
          on 1.18 mm, the finest row of the coarse table.

        "Manual Test Grading" (a test row) and "standard_fine_grading" (no
        data) are deleted unless a mix design names them.

        Idempotent: the updates write fixed values and the deletes match by
        name, so re-running is a no-op.
        """
        try:
            self.logger.info("Applying grading-template % retained migration...")
            sql = """
            UPDATE grading
               SET sieve_data = '[[4.75, 2.5], [2.36, 7.5], [1.18, 22.5], [0.6, 25.0], [0.3, 25.0], [0.15, 12.5], [0.075, 5.0]]',
                   max_diameter = 4.75,
                   is_standard = 1,
                   description = 'ASTM C 33 fine aggregate, mid-band of the grading limits',
                   updated_at = CURRENT_TIMESTAMP,
                   modified_at = CURRENT_TIMESTAMP
             WHERE name = 'ASTM C-33 Fine Aggregate' AND type = 'FINE';
            UPDATE grading
               SET sieve_data = '[[25.0, 2.5], [12.5, 55.0], [4.75, 37.5], [2.36, 2.5], [1.18, 2.5]]',
                   max_diameter = 25.0,
                   is_standard = 1,
                   description = 'ASTM C 33 size No. 57 coarse aggregate, mid-band of the grading limits',
                   updated_at = CURRENT_TIMESTAMP,
                   modified_at = CURRENT_TIMESTAMP
             WHERE name = 'ASTM #57 Stone' AND type = 'COARSE';
            DELETE FROM grading
             WHERE name IN ('Manual Test Grading', 'standard_fine_grading')
               AND name NOT IN (SELECT fine_aggregate_grading_template FROM mix_design
                                 WHERE fine_aggregate_grading_template IS NOT NULL)
               AND name NOT IN (SELECT coarse_aggregate_grading_template FROM mix_design
                                 WHERE coarse_aggregate_grading_template IS NOT NULL);
            """
            self.run_sql_migration(
                sql,
                "20261117_01_grading_templates_percent_retained",
                "Correct C-33 and #57 grading templates; delete junk templates (alpha-4.3)"
            )
        except Exception as e:
            self.logger.error(f"Failed to apply grading-template migration: {e}")
            raise

    def _apply_mix_design_grading_data_migration(self) -> None:
        """Add columns that store each mix's applied aggregate grading points.

        Until alpha-4.3 a mix kept only the grading template NAME; the points
        applied in the Grading dialog were lost on save, and Elastic re-read
        the template by name (falling back to unrelated templates when there
        was none), so hand-edited gradings never reached the calculation.

        Idempotent: each column is added only if it is missing.
        """
        try:
            self.logger.info("Applying mix-design grading-data migration...")
            with self.db_service.get_session() as session:
                existing = {row[1] for row in session.execute(
                    text("PRAGMA table_info(mix_design)")).fetchall()}
                for column in ("fine_aggregate_grading_data", "coarse_aggregate_grading_data"):
                    if column not in existing:
                        session.execute(text(f"ALTER TABLE mix_design ADD COLUMN {column} JSON"))
                session.add(Migration(
                    version="20261117_02_mix_design_grading_data",
                    name="Store applied aggregate grading points with each mix (alpha-4.3)"))
                session.commit()
        except Exception as e:
            self.logger.error(f"Failed to apply mix-design grading-data migration: {e}")
            raise

    def _apply_split_shared_psd_migration(self) -> None:
        """Give every material its own PSD record.

        Duplicating a material used to reuse the original's psd_data_id, so
        editing the copy's PSD also changed the original's, including the
        measured PSDs of immutable VCCTL cements (e.g. cement133 and
        "cement133 (Copy 1)"). For each shared record, the material with the
        lowest id keeps it and every other material gets a copy.

        Idempotent: once no record is shared, nothing changes.
        """
        try:
            self.logger.info("Applying split-shared-PSD migration...")
            columns = ("psd_reference, psd_custom_points, psd_mode, psd_d50, psd_n, psd_dmax, "
                       "psd_median, psd_spread, psd_exponent, diameter_percentile_10, "
                       "diameter_percentile_50, diameter_percentile_90, created_at, updated_at")
            with self.db_service.get_session() as session:
                shared = session.execute(text(
                    "SELECT psd_data_id FROM material WHERE psd_data_id IS NOT NULL "
                    "GROUP BY psd_data_id HAVING COUNT(*) > 1")).fetchall()
                for (psd_id,) in shared:
                    material_ids = [row[0] for row in session.execute(text(
                        "SELECT id FROM material WHERE psd_data_id = :psd ORDER BY id"),
                        {"psd": psd_id}).fetchall()]
                    for material_id in material_ids[1:]:
                        session.execute(text(
                            f"INSERT INTO psd_data ({columns}) SELECT {columns} FROM psd_data WHERE id = :psd"),
                            {"psd": psd_id})
                        new_id = session.execute(text("SELECT last_insert_rowid()")).scalar()
                        session.execute(text("UPDATE material SET psd_data_id = :new WHERE id = :mid"),
                                        {"new": new_id, "mid": material_id})
                        self.logger.info(f"Material {material_id}: own PSD record {new_id} (was shared {psd_id})")
                session.add(Migration(
                    version="20261117_03_split_shared_psd",
                    name="Give every material its own PSD record (alpha-4.3)"))
                session.commit()
        except Exception as e:
            self.logger.error(f"Failed to apply split-shared-PSD migration: {e}")
            raise

    def _apply_vcctl_measured_psd_migration(self) -> None:
        """Give four VCCTL cements their measured PSDs.

        Every cement migrated from VCCTL had a measured PSD, never a model.
        ustype1, cement116, cement168 and sacci-425 reached THAMES as a model
        (Log-Normal or Rosin-Rammler) or with no data at all, so their
        microstructures used a model or the default PSD. Their measured tables,
        recovered from VCCTL 9's Derby database, are in vcctl_psd_data.py.

        Each material's own psd_data row is set to Custom with the measured
        points; model parameters are cleared. Materials not present are
        skipped. Idempotent: the same values are written each time.
        """
        import json
        from app.database.vcctl_psd_data import VCCTL_MEASURED_PSD
        try:
            self.logger.info("Applying VCCTL measured-PSD migration...")
            with self.db_service.get_session() as session:
                for material_name, (reference, points) in VCCTL_MEASURED_PSD.items():
                    session.execute(text(
                        "UPDATE psd_data SET psd_mode = 'custom', psd_custom_points = :points, "
                        "psd_reference = :reference, psd_d50 = NULL, psd_n = NULL, psd_dmax = NULL, "
                        "psd_median = NULL, psd_spread = NULL, psd_exponent = NULL, "
                        "updated_at = CURRENT_TIMESTAMP "
                        "WHERE id = (SELECT psd_data_id FROM material WHERE name = :name)"),
                        {"points": json.dumps(points), "reference": reference, "name": material_name})
                session.add(Migration(
                    version="20261117_04_vcctl_measured_psd",
                    name="Measured VCCTL PSDs for ustype1, cement116, cement168, sacci-425 (alpha-4.3)"))
                session.commit()
        except Exception as e:
            self.logger.error(f"Failed to apply VCCTL measured-PSD migration: {e}")
            raise

    def upgrade_database(self) -> None:
        """Upgrade database to latest version."""
        try:
            version_info = self.check_database_version()
            
            if not version_info['initialized']:
                self.logger.info("Database not initialized, creating initial schema...")
                self.create_initial_schema()
                self.seed_initial_data()
            else:
                self.logger.info("Database already initialized")
                # Apply any new migrations
                applied_migrations = version_info['applied_migrations']
                
                # Check for mix_design table migration
                if "002_add_mix_design_table" not in applied_migrations:
                    self.logger.info("Applying mix_design table migration...")
                    self._apply_mix_design_migration()

                # Check for glass-phase (am) rename migration (S59 follow-up)
                if "20260824_01_glass_phase_am_rename" not in applied_migrations:
                    self._apply_glass_phase_am_rename_migration()

                # Check for orphan-aggregate cleanup migration (S64 follow-up)
                if "20260827_01_clear_orphan_aggregate_names" not in applied_migrations:
                    self._apply_clear_orphan_aggregate_names_migration()

                # Check for grading-template % retained migration (alpha-4.3)
                if "20261117_01_grading_templates_percent_retained" not in applied_migrations:
                    self._apply_grading_templates_percent_retained_migration()

                # Check for mix-design grading-data columns (alpha-4.3)
                if "20261117_02_mix_design_grading_data" not in applied_migrations:
                    self._apply_mix_design_grading_data_migration()

                # Split PSD records shared by duplicated materials (alpha-4.3); must
                # run before the measured-PSD migration, which edits records by material
                if "20261117_03_split_shared_psd" not in applied_migrations:
                    self._apply_split_shared_psd_migration()

                # Check for VCCTL measured-PSD migration (alpha-4.3)
                if "20261117_04_vcctl_measured_psd" not in applied_migrations:
                    self._apply_vcctl_measured_psd_migration()

                self.logger.info(f"Current version: {version_info['current_version']}")
                self.logger.info(f"Applied migrations: {version_info['applied_migrations']}")
            
        except Exception as e:
            self.logger.error(f"Failed to upgrade database: {e}")
            raise
    
    def reset_database(self) -> None:
        """Reset the database (drop all tables and recreate)."""
        try:
            self.logger.warning("Resetting database - all data will be lost!")
            
            # Drop all tables
            self.db_service.drop_all_tables()
            
            # Recreate schema
            self.create_initial_schema()
            
            # Seed initial data
            self.seed_initial_data()
            
            self.logger.info("Database reset completed")
            
        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            raise
    
    def migrate_from_h2_database(self, h2_db_path: Path) -> None:
        """
        Migrate data from H2 database to SQLite.
        
        This method extracts data from the original H2 database and
        converts it to SQLite format.
        """
        try:
            self.logger.info(f"Starting migration from H2 database: {h2_db_path}")
            
            # Check if migration has already been done
            applied_migrations = self.get_applied_migrations()
            if "h2_migration_001" in applied_migrations:
                self.logger.info("H2 migration already completed")
                return
            
            # This would require H2 database driver which is complex in Python
            # For now, we'll implement the Flyway script approach
            self.logger.warning("Direct H2 database migration not yet implemented")
            self.logger.info("Please use migrate_from_flyway_scripts() instead")
            
            # Mark as attempted
            self.mark_migration_applied("h2_migration_001", "H2 database migration (attempted)")
            
        except Exception as e:
            self.logger.error(f"Failed to migrate from H2 database: {e}")
            raise
    
    def migrate_from_flyway_scripts(self, flyway_scripts_dir: Path) -> None:
        """
        Migrate data from Flyway SQL scripts to SQLite.
        
        This method processes the original H2 Flyway scripts and converts
        the data to SQLite format.
        """
        try:
            self.logger.info(f"Starting migration from Flyway scripts: {flyway_scripts_dir}")
            
            # Check if migration has already been done
            applied_migrations = self.get_applied_migrations()
            if "flyway_migration_001" in applied_migrations:
                self.logger.info("Flyway migration already completed")
                return
            
            if not flyway_scripts_dir.exists():
                raise FileNotFoundError(f"Flyway scripts directory not found: {flyway_scripts_dir}")
            
            # Process data insertion scripts in order
            data_scripts = [
                "V7__Insert_data_aggregate.sql",
                "V8__Insert_data_cement.sql", 
                "V9__Insert_data_db_file.sql",
                "V10__Insert_data_fly_ash.sql",
                "V11__Insert_data_slag.sql",
                "V13__Insert_data_filler.sql",
                "V15__Insert_data_particle_shape_set.sql",
                "V17__Insert_data_aggregate_sieves.sql",
                "V19__Insert_grading_data.sql"
            ]
            
            for script_name in data_scripts:
                script_path = flyway_scripts_dir / script_name
                if script_path.exists():
                    self.logger.info(f"Processing script: {script_name}")
                    self._process_flyway_data_script(script_path)
                else:
                    self.logger.warning(f"Script not found: {script_name}")
            
            # Mark migration as completed
            self.mark_migration_applied("flyway_migration_001", "Flyway scripts migration")
            
            self.logger.info("Flyway migration completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to migrate from Flyway scripts: {e}")
            raise
    
    def _process_flyway_data_script(self, script_path: Path) -> None:
        """Process a single Flyway data insertion script."""
        try:
            with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Convert H2-specific syntax to SQLite
            sqlite_content = self._convert_h2_to_sqlite(content)
            
            # Execute the converted script in chunks to handle large files
            self._execute_large_sql_script(sqlite_content, script_path.name)
            
        except Exception as e:
            self.logger.error(f"Failed to process script {script_path.name}: {e}")
            # Don't re-raise to allow other scripts to continue
    
    def _convert_h2_to_sqlite(self, h2_sql: str) -> str:
        """Convert H2 SQL to SQLite-compatible SQL."""
        # Basic H2 to SQLite conversions
        conversions = [
            # Data types
            ('BINARY LARGE OBJECT', 'BLOB'),
            ('DOUBLE PRECISION', 'REAL'),
            ('INTEGER NOT NULL AUTO_INCREMENT', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
            ('TIMESTAMP', 'DATETIME'),
            
            # Functions and syntax
            ('CURRENT_TIMESTAMP()', 'CURRENT_TIMESTAMP'),
            ('TRUE', '1'),
            ('FALSE', '0'),
            
            # Binary data handling (H2 uses x'...' format which SQLite also supports)
            # No conversion needed for hexadecimal blob literals
            
            # Character data
            ('CHARACTER VARYING', 'VARCHAR'),
            ('CHARACTER LARGE OBJECT', 'TEXT'),
            
            # Remove or modify unsupported features
            ('SET REFERENTIAL_INTEGRITY', '-- SET REFERENTIAL_INTEGRITY'),
            ('SET AUTOCOMMIT', '-- SET AUTOCOMMIT'),
        ]
        
        sqlite_sql = h2_sql
        for h2_syntax, sqlite_syntax in conversions:
            sqlite_sql = sqlite_sql.replace(h2_syntax, sqlite_syntax)
        
        return sqlite_sql
    
    def _execute_large_sql_script(self, sql_content: str, script_name: str) -> None:
        """Execute large SQL scripts in manageable chunks."""
        try:
            # Split into statements
            statements = []
            current_statement = ""
            in_string = False
            escape_next = False
            
            for char in sql_content:
                if escape_next:
                    current_statement += char
                    escape_next = False
                    continue
                
                if char == '\\':
                    escape_next = True
                    current_statement += char
                    continue
                
                if char == "'" and not escape_next:
                    in_string = not in_string
                
                current_statement += char
                
                if char == ';' and not in_string:
                    stmt = current_statement.strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt[:-1])  # Remove the semicolon
                    current_statement = ""
            
            # Add any remaining statement
            if current_statement.strip():
                statements.append(current_statement.strip())
            
            self.logger.info(f"Executing {len(statements)} statements from {script_name}")
            
            # Execute in batches
            batch_size = 50  # Adjust based on performance
            for i in range(0, len(statements), batch_size):
                batch = statements[i:i+batch_size]
                self._execute_statement_batch(batch, script_name, i)
                
        except Exception as e:
            self.logger.error(f"Failed to execute large SQL script {script_name}: {e}")
            raise
    
    def _execute_statement_batch(self, statements: List[str], script_name: str, batch_start: int) -> None:
        """Execute a batch of SQL statements."""
        try:
            with self.db_service.get_session() as session:
                for i, statement in enumerate(statements):
                    try:
                        if statement.strip():
                            session.execute(text(statement))
                    except Exception as e:
                        stmt_num = batch_start + i + 1
                        self.logger.warning(f"Failed to execute statement {stmt_num} in {script_name}: {e}")
                        # Continue with next statement
                        
        except Exception as e:
            self.logger.error(f"Failed to execute batch from {script_name}: {e}")
            raise
    
    def validate_migration(self) -> Dict[str, Any]:
        """Validate the migrated data integrity."""
        validation_results = {
            'status': 'success',
            'errors': [],
            'warnings': [],
            'table_counts': {},
            'data_integrity': {}
        }
        
        try:
            with self.db_service.get_session() as session:
                # Check each table
                from app.models import get_all_models
                
                for model_class in get_all_models():
                    table_name = model_class.__tablename__
                    
                    try:
                        count = session.query(model_class).count()
                        validation_results['table_counts'][table_name] = count
                        
                        # Basic validation for each model
                        if hasattr(model_class, 'validate_gypsum_fractions'):
                            # Cement validation
                            invalid_count = 0
                            for item in session.query(model_class).all():
                                if not item.validate_gypsum_fractions():
                                    invalid_count += 1
                            if invalid_count > 0:
                                validation_results['warnings'].append(
                                    f"{table_name}: {invalid_count} items with invalid gypsum fractions"
                                )
                        
                        elif hasattr(model_class, 'validate_phase_fractions'):
                            # FlyAsh validation
                            invalid_count = 0
                            for item in session.query(model_class).all():
                                if not item.validate_phase_fractions():
                                    invalid_count += 1
                            if invalid_count > 0:
                                validation_results['warnings'].append(
                                    f"{table_name}: {invalid_count} items with invalid phase fractions"
                                )
                        
                        elif hasattr(model_class, 'validate_mechanical_properties'):
                            # Aggregate validation
                            invalid_count = 0
                            for item in session.query(model_class).all():
                                if not item.validate_mechanical_properties():
                                    invalid_count += 1
                            if invalid_count > 0:
                                validation_results['warnings'].append(
                                    f"{table_name}: {invalid_count} items with invalid mechanical properties"
                                )
                        
                    except Exception as e:
                        validation_results['errors'].append(f"Error validating {table_name}: {e}")
                
                if validation_results['errors']:
                    validation_results['status'] = 'error'
                elif validation_results['warnings']:
                    validation_results['status'] = 'warning'
                
        except Exception as e:
            validation_results['status'] = 'error'
            validation_results['errors'].append(f"General validation error: {e}")
        
        return validation_results


def create_migration_manager(db_service: DatabaseService = None) -> MigrationManager:
    """Create a migration manager instance."""
    from app.database.service import database_service
    return MigrationManager(db_service or database_service)
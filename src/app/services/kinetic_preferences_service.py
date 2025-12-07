#!/usr/bin/env python3
"""
Kinetic Preferences Service for THAMES

Manages user-configurable default kinetic parameters for GEM phases.
User preferences are stored in a JSON file and merged with built-in defaults.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List

from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
    KineticParameters,
)


class KineticPreferencesService:
    """
    Service for managing user-defined kinetic defaults.

    User preferences are stored in:
    ~/Library/Application Support/THAMES/preferences/kinetic_defaults.json (macOS)
    %LOCALAPPDATA%/THAMES/preferences/kinetic_defaults.json (Windows)
    ~/.local/share/THAMES/preferences/kinetic_defaults.json (Linux)

    Preferences override the built-in defaults in KineticDefaultsService.
    """

    PREFERENCES_FILENAME = "kinetic_defaults.json"

    def __init__(self, preferences_dir: Optional[Path] = None):
        """
        Initialize the KineticPreferencesService.

        Args:
            preferences_dir: Optional path to preferences directory.
                           If None, uses default user data directory.
        """
        self.logger = logging.getLogger('THAMES.KineticPreferencesService')

        if preferences_dir:
            self.preferences_dir = Path(preferences_dir)
        else:
            self.preferences_dir = self._get_default_preferences_dir()

        self.preferences_file = self.preferences_dir / self.PREFERENCES_FILENAME

        # Cache of user preferences: {phase_name: kinetic_dict}
        self._user_defaults: Dict[str, Dict[str, Any]] = {}

        # Load preferences on init
        self._load_preferences()

    def _get_default_preferences_dir(self) -> Path:
        """Get the default preferences directory based on platform."""
        import sys

        if sys.platform == 'darwin':
            # macOS
            base = Path.home() / "Library" / "Application Support" / "THAMES"
        elif sys.platform == 'win32':
            # Windows
            import os
            base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / "THAMES"
        else:
            # Linux and others
            base = Path.home() / ".local" / "share" / "THAMES"

        return base / "preferences"

    def _load_preferences(self) -> None:
        """Load user preferences from JSON file."""
        if not self.preferences_file.exists():
            self.logger.info(f"No user kinetic preferences file found at {self.preferences_file}")
            self._user_defaults = {}
            return

        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)

            self._user_defaults = data.get('kinetic_defaults', {})
            self.logger.info(f"Loaded {len(self._user_defaults)} user kinetic defaults")

        except Exception as e:
            self.logger.error(f"Error loading kinetic preferences: {e}")
            self._user_defaults = {}

    def _save_preferences(self) -> bool:
        """
        Save user preferences to JSON file.

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            self.preferences_dir.mkdir(parents=True, exist_ok=True)

            data = {
                'version': 1,
                'kinetic_defaults': self._user_defaults
            }

            with open(self.preferences_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Saved {len(self._user_defaults)} user kinetic defaults")
            return True

        except Exception as e:
            self.logger.error(f"Error saving kinetic preferences: {e}")
            return False

    def get_user_default(self, phase_name: str) -> Optional[Dict[str, Any]]:
        """
        Get user-defined default kinetics for a phase.

        Args:
            phase_name: GEM phase name

        Returns:
            Kinetic parameters dict if user has defined defaults, None otherwise
        """
        return self._user_defaults.get(phase_name)

    def set_user_default(self, phase_name: str, kinetics: Dict[str, Any]) -> bool:
        """
        Set user-defined default kinetics for a phase.

        Args:
            phase_name: GEM phase name
            kinetics: Kinetic parameters dict (must include 'type' field)

        Returns:
            True if saved successfully
        """
        if 'type' not in kinetics:
            self.logger.error(f"Kinetics dict must include 'type' field")
            return False

        self._user_defaults[phase_name] = kinetics
        self.logger.info(f"Set user default for {phase_name}: {kinetics.get('type')}")
        return self._save_preferences()

    def remove_user_default(self, phase_name: str) -> bool:
        """
        Remove user-defined default for a phase (revert to built-in default).

        Args:
            phase_name: GEM phase name

        Returns:
            True if removed and saved successfully
        """
        if phase_name in self._user_defaults:
            del self._user_defaults[phase_name]
            self.logger.info(f"Removed user default for {phase_name}")
            return self._save_preferences()
        return True

    def get_all_user_defaults(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all user-defined kinetic defaults.

        Returns:
            Dict mapping phase names to kinetic parameters
        """
        return dict(self._user_defaults)

    def has_user_default(self, phase_name: str) -> bool:
        """
        Check if a phase has a user-defined default.

        Args:
            phase_name: GEM phase name

        Returns:
            True if user has defined a default for this phase
        """
        return phase_name in self._user_defaults

    def get_phases_with_user_defaults(self) -> List[str]:
        """
        Get list of phase names that have user-defined defaults.

        Returns:
            List of phase names
        """
        return list(self._user_defaults.keys())

    def clear_all_user_defaults(self) -> bool:
        """
        Clear all user-defined defaults.

        Returns:
            True if cleared and saved successfully
        """
        self._user_defaults = {}
        return self._save_preferences()

    def export_to_file(self, export_path: Path) -> bool:
        """
        Export user preferences to a specified file.

        Args:
            export_path: Path to export file

        Returns:
            True if exported successfully
        """
        try:
            data = {
                'version': 1,
                'kinetic_defaults': self._user_defaults
            }

            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Exported kinetic preferences to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting kinetic preferences: {e}")
            return False

    def import_from_file(self, import_path: Path, merge: bool = True) -> bool:
        """
        Import user preferences from a file.

        Args:
            import_path: Path to import file
            merge: If True, merge with existing; if False, replace all

        Returns:
            True if imported successfully
        """
        try:
            with open(import_path, 'r') as f:
                data = json.load(f)

            imported_defaults = data.get('kinetic_defaults', {})

            if merge:
                self._user_defaults.update(imported_defaults)
            else:
                self._user_defaults = imported_defaults

            self.logger.info(f"Imported {len(imported_defaults)} kinetic defaults from {import_path}")
            return self._save_preferences()

        except Exception as e:
            self.logger.error(f"Error importing kinetic preferences: {e}")
            return False


# Module-level singleton
_kinetic_preferences_service: Optional[KineticPreferencesService] = None


def get_kinetic_preferences_service() -> KineticPreferencesService:
    """Get the singleton KineticPreferencesService instance."""
    global _kinetic_preferences_service
    if _kinetic_preferences_service is None:
        _kinetic_preferences_service = KineticPreferencesService()
    return _kinetic_preferences_service

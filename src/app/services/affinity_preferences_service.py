#!/usr/bin/env python3
"""
Affinity Preferences Service for THAMES

Manages user-configurable default interface affinity (contact angle) parameters
for GEM phases. User preferences are stored in a JSON file and merged with
built-in defaults from KineticDefaultsService.INTERFACE_AFFINITY_DEFAULTS.

Interface affinity controls where hydration products preferentially nucleate
and grow based on contact angles:
- 0° = maximum affinity (strong heterogeneous nucleation)
- 90° = neutral (no preference)
- 180° = no affinity (avoids nucleating on this substrate)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List


class AffinityPreferencesService:
    """
    Service for managing user-defined interface affinity defaults.

    User preferences are stored in:
    ~/Library/Application Support/THAMES/preferences/affinity_defaults.json (macOS)
    %LOCALAPPDATA%/THAMES/preferences/affinity_defaults.json (Windows)
    ~/.local/share/THAMES/preferences/affinity_defaults.json (Linux)

    Preferences override the built-in defaults in KineticDefaultsService.INTERFACE_AFFINITY_DEFAULTS.

    Affinity data format:
    {
        "phase_name": [
            {"affinityphase": "OtherPhase1", "contactanglevalue": 30},
            {"affinityphase": "OtherPhase2", "contactanglevalue": 180}
        ]
    }
    """

    PREFERENCES_FILENAME = "affinity_defaults.json"

    def __init__(self, preferences_dir: Optional[Path] = None):
        """
        Initialize the AffinityPreferencesService.

        Args:
            preferences_dir: Optional path to preferences directory.
                           If None, uses default user data directory.
        """
        self.logger = logging.getLogger('THAMES.AffinityPreferencesService')

        if preferences_dir:
            self.preferences_dir = Path(preferences_dir)
        else:
            self.preferences_dir = self._get_default_preferences_dir()

        self.preferences_file = self.preferences_dir / self.PREFERENCES_FILENAME

        # Cache of user preferences: {phase_name: [affinity_list]}
        self._user_defaults: Dict[str, List[Dict[str, Any]]] = {}

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
            self.logger.info(f"No user affinity preferences file found at {self.preferences_file}")
            self._user_defaults = {}
            return

        try:
            with open(self.preferences_file, 'r') as f:
                data = json.load(f)

            self._user_defaults = data.get('affinity_defaults', {})
            self.logger.info(f"Loaded {len(self._user_defaults)} user affinity defaults")

        except Exception as e:
            self.logger.error(f"Error loading affinity preferences: {e}")
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
                'affinity_defaults': self._user_defaults
            }

            with open(self.preferences_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Saved {len(self._user_defaults)} user affinity defaults")
            return True

        except Exception as e:
            self.logger.error(f"Error saving affinity preferences: {e}")
            return False

    def get_user_default(self, phase_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get user-defined default affinities for a phase.

        Args:
            phase_name: GEM phase name

        Returns:
            List of affinity dicts if user has defined defaults, None otherwise
        """
        return self._user_defaults.get(phase_name)

    def set_user_default(self, phase_name: str, affinities: List[Dict[str, Any]]) -> bool:
        """
        Set user-defined default affinities for a phase.

        Args:
            phase_name: GEM phase name
            affinities: List of affinity dicts, each with 'affinityphase' and 'contactanglevalue'

        Returns:
            True if saved successfully
        """
        # Validate format
        for aff in affinities:
            if 'affinityphase' not in aff or 'contactanglevalue' not in aff:
                self.logger.error(f"Invalid affinity format: {aff}")
                return False
            # Validate contact angle range
            angle = aff['contactanglevalue']
            if not (0 <= angle <= 180):
                self.logger.error(f"Contact angle must be 0-180, got {angle}")
                return False

        self._user_defaults[phase_name] = affinities
        self.logger.info(f"Set user affinity default for {phase_name}: {len(affinities)} entries")
        return self._save_preferences()

    def add_affinity_entry(
        self,
        phase_name: str,
        affinity_phase: str,
        contact_angle: float
    ) -> bool:
        """
        Add or update a single affinity entry for a phase.

        Args:
            phase_name: GEM phase name (the one that grows)
            affinity_phase: GEM phase name (the substrate)
            contact_angle: Contact angle in degrees (0-180)

        Returns:
            True if saved successfully
        """
        if not (0 <= contact_angle <= 180):
            self.logger.error(f"Contact angle must be 0-180, got {contact_angle}")
            return False

        # Get existing or create new list
        affinities = list(self._user_defaults.get(phase_name, []))

        # Update existing entry or add new one
        found = False
        for aff in affinities:
            if aff['affinityphase'] == affinity_phase:
                aff['contactanglevalue'] = contact_angle
                found = True
                break

        if not found:
            affinities.append({
                'affinityphase': affinity_phase,
                'contactanglevalue': contact_angle
            })

        self._user_defaults[phase_name] = affinities
        return self._save_preferences()

    def remove_affinity_entry(self, phase_name: str, affinity_phase: str) -> bool:
        """
        Remove a single affinity entry for a phase.

        Args:
            phase_name: GEM phase name
            affinity_phase: Substrate phase to remove

        Returns:
            True if removed and saved successfully
        """
        if phase_name not in self._user_defaults:
            return True

        affinities = self._user_defaults[phase_name]
        self._user_defaults[phase_name] = [
            aff for aff in affinities
            if aff['affinityphase'] != affinity_phase
        ]

        # Remove phase entirely if no affinities left
        if not self._user_defaults[phase_name]:
            del self._user_defaults[phase_name]

        return self._save_preferences()

    def remove_user_default(self, phase_name: str) -> bool:
        """
        Remove all user-defined affinities for a phase (revert to built-in default).

        Args:
            phase_name: GEM phase name

        Returns:
            True if removed and saved successfully
        """
        if phase_name in self._user_defaults:
            del self._user_defaults[phase_name]
            self.logger.info(f"Removed user affinity default for {phase_name}")
            return self._save_preferences()
        return True

    def get_all_user_defaults(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all user-defined affinity defaults.

        Returns:
            Dict mapping phase names to affinity lists
        """
        return dict(self._user_defaults)

    def has_user_default(self, phase_name: str) -> bool:
        """
        Check if a phase has a user-defined affinity default.

        Args:
            phase_name: GEM phase name

        Returns:
            True if user has defined affinities for this phase
        """
        return phase_name in self._user_defaults

    def get_phases_with_user_defaults(self) -> List[str]:
        """
        Get list of phase names that have user-defined affinity defaults.

        Returns:
            List of phase names
        """
        return list(self._user_defaults.keys())

    def clear_all_user_defaults(self) -> bool:
        """
        Clear all user-defined affinity defaults.

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
                'affinity_defaults': self._user_defaults
            }

            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(f"Exported affinity preferences to {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting affinity preferences: {e}")
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

            imported_defaults = data.get('affinity_defaults', {})

            if merge:
                self._user_defaults.update(imported_defaults)
            else:
                self._user_defaults = imported_defaults

            self.logger.info(f"Imported {len(imported_defaults)} affinity defaults from {import_path}")
            return self._save_preferences()

        except Exception as e:
            self.logger.error(f"Error importing affinity preferences: {e}")
            return False


# Module-level singleton
_affinity_preferences_service: Optional[AffinityPreferencesService] = None


def get_affinity_preferences_service() -> AffinityPreferencesService:
    """Get the singleton AffinityPreferencesService instance."""
    global _affinity_preferences_service
    if _affinity_preferences_service is None:
        _affinity_preferences_service = AffinityPreferencesService()
    return _affinity_preferences_service

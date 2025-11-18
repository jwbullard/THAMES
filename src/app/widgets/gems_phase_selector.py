#!/usr/bin/env python3
"""
GEMS Phase Selector Widget

Autocomplete entry widget for selecting GEMS phases from the thermodynamic database.
Filters phases as the user types and provides intelligent suggestions.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import logging
from typing import Optional, List, Callable

from app.services.gems_parser_service import GEMSParserService


class GEMSPhaseSelector(Gtk.Box):
    """
    Autocomplete entry widget for selecting GEMS phases.

    Features:
    - Autocomplete suggestions from GEMS database
    - Case-insensitive filtering
    - Optional filtering by phase type (solid, gas, solution)
    - Validation against GEMS database
    """

    __gsignals__ = {
        'phase-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'phase-cleared': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, gems_parser: GEMSParserService,
                 phase_filter: Optional[str] = None,
                 placeholder: str = "Type to search phases..."):
        """
        Initialize the GEMS phase selector.

        Args:
            gems_parser: GEMSParserService instance
            phase_filter: Optional filter - 'solid', 'gas', 'solution', or None for all
            placeholder: Placeholder text for the entry
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.gems_parser = gems_parser
        self.phase_filter = phase_filter
        self.logger = logging.getLogger('THAMES.GEMSPhaseSelector')

        # Get phase names based on filter
        self.available_phases = self._get_filtered_phases()
        self.logger.info(f"Loaded {len(self.available_phases)} phases from GEMS database")

        # Build UI
        self._build_ui(placeholder)

    def _get_filtered_phases(self) -> List[str]:
        """Get phase names based on the filter."""
        if self.phase_filter == 'solid':
            phases = self.gems_parser.get_solid_phases()
        elif self.phase_filter == 'gas':
            phases = self.gems_parser.get_gas_phases()
        elif self.phase_filter == 'solution':
            phases = self.gems_parser.get_solution_phases()
        else:
            phases = self.gems_parser.get_all_phases()

        # Return sorted phase names
        return sorted([p.name for p in phases])

    def _build_ui(self, placeholder: str):
        """Build the selector UI."""
        # Entry with completion
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(placeholder)
        self.entry.connect('changed', self._on_entry_changed)
        self.entry.connect('activate', self._on_entry_activated)

        # Setup autocomplete
        self.completion = Gtk.EntryCompletion()
        self.entry.set_completion(self.completion)

        # Create list store for completion
        self.completion_store = Gtk.ListStore(str)
        for phase in self.available_phases:
            self.completion_store.append([phase])

        self.completion.set_model(self.completion_store)
        self.completion.set_text_column(0)
        self.completion.set_inline_completion(True)
        self.completion.set_popup_completion(True)
        self.completion.set_match_func(self._match_func)
        self.completion.connect('match-selected', self._on_match_selected)

        # Add entry to box
        self.pack_start(self.entry, True, True, 0)

        # Optional: Add info label showing number of matches
        self.info_label = Gtk.Label()
        self.info_label.set_halign(Gtk.Align.START)
        self.info_label.set_markup(f'<small><i>{len(self.available_phases)} phases available</i></small>')
        self.pack_start(self.info_label, False, False, 0)

    def _match_func(self, completion, key, iter):
        """
        Custom match function for case-insensitive matching.

        Args:
            completion: The EntryCompletion
            key: The text to match
            iter: TreeIter pointing to row in model

        Returns:
            True if row matches, False otherwise
        """
        model = completion.get_model()
        phase_name = model[iter][0]

        # Case-insensitive substring match
        return key.lower() in phase_name.lower()

    def _on_entry_changed(self, entry):
        """Handle entry text changes."""
        text = entry.get_text()

        # Update info label with match count
        if text:
            matches = [p for p in self.available_phases if text.lower() in p.lower()]
            self.info_label.set_markup(f'<small><i>{len(matches)} matching phases</i></small>')
        else:
            self.info_label.set_markup(f'<small><i>{len(self.available_phases)} phases available</i></small>')

    def _on_entry_activated(self, entry):
        """Handle Enter key in entry."""
        phase_name = entry.get_text().strip()
        if self.is_valid_phase(phase_name):
            self.emit('phase-selected', phase_name)
        else:
            self.logger.warning(f"Invalid phase name: {phase_name}")

    def _on_match_selected(self, completion, model, iter):
        """Handle selection from completion popup."""
        phase_name = model[iter][0]
        self.emit('phase-selected', phase_name)
        return True

    def get_selected_phase(self) -> Optional[str]:
        """
        Get the currently entered phase name if valid.

        Returns:
            Phase name if valid, None otherwise
        """
        phase_name = self.entry.get_text().strip()
        if self.is_valid_phase(phase_name):
            return phase_name
        return None

    def set_phase(self, phase_name: str):
        """Set the entry to a specific phase name."""
        if phase_name in self.available_phases:
            self.entry.set_text(phase_name)
        else:
            self.logger.warning(f"Phase '{phase_name}' not in available phases")

    def clear(self):
        """Clear the entry."""
        self.entry.set_text("")
        self.emit('phase-cleared')

    def is_valid_phase(self, phase_name: str) -> bool:
        """
        Check if a phase name is valid.

        Args:
            phase_name: Phase name to validate

        Returns:
            True if phase exists in GEMS database
        """
        return phase_name in self.available_phases

    def set_sensitive(self, sensitive: bool):
        """Enable or disable the selector."""
        self.entry.set_sensitive(sensitive)


# Register the signal
GObject.type_register(GEMSPhaseSelector)

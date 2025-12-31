#!/usr/bin/env python3
"""
Microstructure Phases Editor Widget

GTK widget for displaying and editing kinetic parameters of phases
present in the input microstructure for THAMES-Hydration simulations.

These phases are read from the phase mapping JSON file generated during
microstructure creation. They represent the dissolving phases (clinker,
sulfates, pozzolans) that will react during hydration.

Key features:
- Phases cannot be removed (they're part of the microstructure)
- Kinetic parameters can be viewed and edited
- Default kinetics are loaded from KineticDefaultsService
"""

import gi
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango, Gdk
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.services.kinetic_defaults_service import (
    KineticDefaultsService,
    get_kinetic_defaults_service,
)
from app.widgets.kinetic_model_editor import KineticModelEditorDialog


class MicrostructurePhasesEditor(Gtk.Box):
    """
    Widget for viewing and editing kinetic parameters of microstructure phases.

    Shows all phases from the input microstructure (except VOID, Electrolyte,
    AGGREGATE) and allows users to edit their kinetic parameters.
    """

    __gsignals__ = {
        # Emitted when kinetic parameters change
        'kinetics-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    # Phases that should not be shown (not dissolving phases)
    # Note: Aggregate phases (e.g., Quartz) are now included so users can set kinetics
    EXCLUDED_PHASES = {'VOID', 'Electrolyte', 'aq_gen', 'gas_gen'}

    def __init__(self):
        """Initialize the microstructure phases editor."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.logger = logging.getLogger('THAMES.MicrostructurePhasesEditor')
        self.kinetic_defaults = get_kinetic_defaults_service()

        # Store phase data: {phase_name: {'kinetics': dict, 'phase_id': int}}
        self.phase_data: Dict[str, Dict[str, Any]] = {}

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the widget UI."""
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title = Gtk.Label()
        title.set_markup("<b>Microstructure Phases</b>")
        title.set_halign(Gtk.Align.START)
        header.pack_start(title, False, False, 0)

        header.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        # Info label
        self.info_label = Gtk.Label()
        self.info_label.set_markup(
            '<span size="small" foreground="gray">No microstructure selected</span>'
        )
        header.pack_end(self.info_label, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Instruction
        instruction = Gtk.Label()
        instruction.set_markup(
            '<span size="small">These phases are from the microstructure and cannot be removed. '
            'Double-click to edit kinetic parameters.</span>'
        )
        instruction.set_halign(Gtk.Align.START)
        instruction.set_line_wrap(True)
        instruction.get_style_context().add_class("dim-label")
        self.pack_start(instruction, False, False, 0)

        # Phase list in scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(150)
        scrolled.set_max_content_height(250)

        # TreeView: phase_name, kinetic_type, phase_id, has_kinetics (for icon)
        self.store = Gtk.ListStore(str, str, int, bool)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.connect('row-activated', self._on_row_activated)

        # Column 1: Phase Name
        renderer_name = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Phase", renderer_name, text=0)
        column_name.set_expand(True)
        column_name.set_sort_column_id(0)
        self.treeview.append_column(column_name)

        # Column 2: Kinetic Model Type
        renderer_type = Gtk.CellRendererText()
        renderer_type.set_property('foreground', 'gray')
        column_type = Gtk.TreeViewColumn("Kinetic Model", renderer_type, text=1)
        column_type.set_min_width(120)
        self.treeview.append_column(column_type)

        # Column 3: Phase ID
        renderer_id = Gtk.CellRendererText()
        renderer_id.set_property('foreground', 'gray')
        column_id = Gtk.TreeViewColumn("ID", renderer_id, text=2)
        column_id.set_min_width(40)
        self.treeview.append_column(column_id)

        # Column 4: Edit icon
        renderer_icon = Gtk.CellRendererPixbuf()
        column_icon = Gtk.TreeViewColumn("", renderer_icon)
        column_icon.set_cell_data_func(renderer_icon, self._icon_cell_data_func)
        column_icon.set_min_width(30)
        self.treeview.append_column(column_icon)

        scrolled.add(self.treeview)
        self.pack_start(scrolled, True, True, 0)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_margin_top(5)

        # Edit button
        self.edit_btn = Gtk.Button(label="Edit Kinetics...")
        self.edit_btn.set_tooltip_text("Edit kinetic parameters for selected phase")
        self.edit_btn.connect('clicked', self._on_edit_clicked)
        self.edit_btn.set_sensitive(False)
        toolbar.pack_start(self.edit_btn, False, False, 0)

        # Reset button
        self.reset_btn = Gtk.Button(label="Reset to Defaults")
        self.reset_btn.set_tooltip_text("Reset selected phase to default kinetic parameters")
        self.reset_btn.connect('clicked', self._on_reset_clicked)
        self.reset_btn.set_sensitive(False)
        toolbar.pack_start(self.reset_btn, False, False, 0)

        toolbar.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        # Reset all button
        self.reset_all_btn = Gtk.Button(label="Reset All")
        self.reset_all_btn.set_tooltip_text("Reset all phases to default kinetics")
        self.reset_all_btn.connect('clicked', self._on_reset_all_clicked)
        toolbar.pack_start(self.reset_all_btn, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

        # Connect selection changed
        self.treeview.get_selection().connect('changed', self._on_selection_changed)

    def _icon_cell_data_func(self, column, cell, model, iter, data) -> None:
        """Show edit icon for phases with kinetics."""
        has_kinetics = model.get_value(iter, 3)
        if has_kinetics:
            cell.set_property('icon-name', 'document-edit-symbolic')
        else:
            cell.set_property('icon-name', None)

    def _on_selection_changed(self, selection) -> None:
        """Handle selection change."""
        model, iter = selection.get_selected()
        if iter:
            phase_name = model.get_value(iter, 0)
            has_kinetics = model.get_value(iter, 3)
            self.edit_btn.set_sensitive(has_kinetics)
            self.reset_btn.set_sensitive(has_kinetics)
        else:
            self.edit_btn.set_sensitive(False)
            self.reset_btn.set_sensitive(False)

    def _on_row_activated(self, treeview, path, column) -> None:
        """Handle double-click on row."""
        iter = self.store.get_iter(path)
        phase_name = self.store.get_value(iter, 0)
        has_kinetics = self.store.get_value(iter, 3)

        if has_kinetics:
            self._edit_phase_kinetics(phase_name)

    def _on_edit_clicked(self, button: Gtk.Button) -> None:
        """Handle edit button click."""
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            phase_name = model.get_value(iter, 0)
            self._edit_phase_kinetics(phase_name)

    def _on_reset_clicked(self, button: Gtk.Button) -> None:
        """Handle reset button click."""
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            phase_name = model.get_value(iter, 0)
            self._reset_phase_to_defaults(phase_name)

    def _on_reset_all_clicked(self, button: Gtk.Button) -> None:
        """Handle reset all button click."""
        for phase_name in self.phase_data:
            self._reset_phase_to_defaults(phase_name)

    def _edit_phase_kinetics(self, phase_name: str) -> None:
        """Open dialog to edit kinetics for a phase."""
        current_params = self.phase_data.get(phase_name, {}).get('kinetics')

        # Get parent window
        parent = self.get_toplevel()
        if not isinstance(parent, Gtk.Window):
            parent = None

        dialog = KineticModelEditorDialog(parent, phase_name, current_params)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_params = dialog.get_kinetic_parameters()
            if new_params:
                self.phase_data[phase_name]['kinetics'] = new_params
                self.emit('kinetics-changed')
                self.logger.debug(f"Updated kinetics for {phase_name}")

        dialog.destroy()

    def _reset_phase_to_defaults(self, phase_name: str) -> None:
        """Reset a phase's kinetics to defaults."""
        defaults = self.kinetic_defaults.get_kinetics_for_phase(phase_name)
        if defaults:
            self.phase_data[phase_name]['kinetics'] = defaults.to_dict()
            self.emit('kinetics-changed')
            self.logger.debug(f"Reset kinetics for {phase_name} to defaults")

    def load_from_phase_mapping(self, phase_mapping_path: Path) -> None:
        """
        Load phases from a phase mapping JSON file.

        Args:
            phase_mapping_path: Path to the phase_mapping.json file
        """
        self.store.clear()
        self.phase_data.clear()

        if not phase_mapping_path.exists():
            self.info_label.set_markup(
                '<span size="small" foreground="orange">Phase mapping file not found</span>'
            )
            return

        try:
            with open(phase_mapping_path, 'r') as f:
                mapping = json.load(f)

            micro_to_gem = mapping.get('micro_to_gem', {})

            for phase_id_str, phase_name in micro_to_gem.items():
                # Skip excluded phases
                if phase_name in self.EXCLUDED_PHASES:
                    continue

                phase_id = int(phase_id_str)

                # Get kinetic type
                kinetic_type = self.kinetic_defaults.get_kinetic_type(phase_name)
                kinetic_type_display = kinetic_type if kinetic_type else "None"
                has_kinetics = kinetic_type is not None

                # Initialize with default kinetics
                defaults = self.kinetic_defaults.get_kinetics_for_phase(phase_name)
                kinetics_dict = defaults.to_dict() if defaults else None

                # Store phase data
                self.phase_data[phase_name] = {
                    'phase_id': phase_id,
                    'kinetics': kinetics_dict,
                }

                # Add to store
                self.store.append([phase_name, kinetic_type_display, phase_id, has_kinetics])

            # Update info label
            num_phases = len(self.phase_data)
            self.info_label.set_markup(
                f'<span size="small" foreground="green">{num_phases} phases loaded</span>'
            )
            self.logger.info(f"Loaded {num_phases} phases from {phase_mapping_path}")

        except Exception as e:
            self.logger.error(f"Error loading phase mapping: {e}")
            self.info_label.set_markup(
                f'<span size="small" foreground="red">Error loading phases</span>'
            )

    def load_phases_from_list(self, phases: List[Dict[str, Any]]) -> None:
        """
        Load phases from a list of phase dictionaries.

        Args:
            phases: List of dicts with 'gem_phase_name' and optionally 'kinetics'
        """
        self.store.clear()
        self.phase_data.clear()

        phase_id = 2  # Start at 2 (after VOID and Electrolyte)

        for phase_info in phases:
            phase_name = phase_info.get('gem_phase_name')
            if not phase_name or phase_name in self.EXCLUDED_PHASES:
                continue

            # Get kinetic type
            kinetic_type = self.kinetic_defaults.get_kinetic_type(phase_name)
            kinetic_type_display = kinetic_type if kinetic_type else "None"
            has_kinetics = kinetic_type is not None

            # Use provided kinetics or defaults
            if 'kinetics' in phase_info and phase_info['kinetics']:
                kinetics_dict = phase_info['kinetics']
            else:
                defaults = self.kinetic_defaults.get_kinetics_for_phase(phase_name)
                kinetics_dict = defaults.to_dict() if defaults else None

            # Store phase data
            self.phase_data[phase_name] = {
                'phase_id': phase_id,
                'kinetics': kinetics_dict,
            }

            # Add to store
            self.store.append([phase_name, kinetic_type_display, phase_id, has_kinetics])

            phase_id += 1

        # Update info label
        num_phases = len(self.phase_data)
        self.info_label.set_markup(
            f'<span size="small" foreground="green">{num_phases} phases</span>'
        )

    def clear(self) -> None:
        """Clear all phases."""
        self.store.clear()
        self.phase_data.clear()
        self.info_label.set_markup(
            '<span size="small" foreground="gray">No microstructure selected</span>'
        )

    def get_kinetic_overrides(self) -> Dict[str, Dict[str, Any]]:
        """
        Get kinetic parameter overrides for all phases.

        Returns:
            Dictionary mapping phase name to kinetic parameters
        """
        overrides = {}
        for phase_name, data in self.phase_data.items():
            if data.get('kinetics'):
                overrides[phase_name] = data['kinetics']
        return overrides

    def set_kinetic_overrides(self, overrides: Dict[str, Dict[str, Any]]) -> None:
        """
        Set kinetic parameter overrides for phases.

        Args:
            overrides: Dictionary mapping phase name to kinetic parameters
        """
        for phase_name, kinetics in overrides.items():
            if phase_name in self.phase_data:
                self.phase_data[phase_name]['kinetics'] = kinetics

    def get_phase_names(self) -> List[str]:
        """Get list of phase names in the microstructure."""
        return list(self.phase_data.keys())


# Register signals
GObject.type_register(MicrostructurePhasesEditor)

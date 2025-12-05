#!/usr/bin/env python3
"""
Phase Composition Editor Widget

Editable table for defining material phase compositions with mass fractions.
Integrates with GEMS database for phase validation and auto-density calculation.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
import logging
from typing import List, Dict, Optional, Tuple

from app.services.gems_parser_service import GEMSParserService
from app.widgets.gems_phase_selector import GEMSPhaseSelector
from app.services.material_service import MaterialService


class PhaseCompositionEditor(Gtk.Box):
    """
    Editor widget for material phase composition.

    Features:
    - Add/edit/remove phases with mass fractions
    - GEMS phase validation
    - Real-time mass fraction total calculation
    - Warning when total != 1.0
    - Duplicate phase detection
    - Auto-calculate SG from phase composition
    """

    __gsignals__ = {
        'composition-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'sg-calculated': (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        'clinker-source-added': (GObject.SignalFlags.RUN_FIRST, None, (int,)),  # clinker_material_id
    }

    def __init__(self, gems_parser: GEMSParserService, editable: bool = True,
                 material_service: MaterialService = None, exclude_material_id: int = None):
        """
        Initialize the phase composition editor.

        Args:
            gems_parser: GEMSParserService instance
            editable: Whether the editor is editable (False for read-only)
            material_service: MaterialService instance (optional, for "Add from Material" feature)
            exclude_material_id: Material ID to exclude from material list (the current material being edited)
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.gems_parser = gems_parser
        self.material_service = material_service
        self.exclude_material_id = exclude_material_id
        self.editable = editable
        self.logger = logging.getLogger('THAMES.PhaseCompositionEditor')

        # Phase data: List of {phase_name: str, mass_fraction: float}
        self.phases: List[Dict[str, float]] = []

        # Clinker tracking (set when phases from a clinker are added)
        self.clinker_source_id: Optional[int] = None
        self.clinker_source_name: Optional[str] = None
        self.clinker_phase_names: List[str] = []  # Names of the 6 clinker phases

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the editor UI."""
        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        toolbar.set_margin_bottom(5)

        add_btn = Gtk.Button(label="Add Phase")
        add_btn.connect('clicked', self._on_add_phase_clicked)
        toolbar.pack_start(add_btn, False, False, 0)

        # Add from Material button (only if material_service is available)
        add_material_btn = Gtk.Button(label="Add from Material")
        add_material_btn.set_tooltip_text("Add all phases from an existing material")
        add_material_btn.connect('clicked', self._on_add_from_material_clicked)
        toolbar.pack_start(add_material_btn, False, False, 0)
        if not self.material_service:
            add_material_btn.set_sensitive(False)
            add_material_btn.set_tooltip_text("Material service not available")

        remove_btn = Gtk.Button(label="Remove Phase")
        remove_btn.connect('clicked', self._on_remove_phase_clicked)
        toolbar.pack_start(remove_btn, False, False, 0)

        # Spacer
        toolbar.pack_start(Gtk.Label(), True, True, 0)

        # Auto-calculate SG button
        calc_sg_btn = Gtk.Button(label="Auto-Calculate SG")
        calc_sg_btn.set_tooltip_text("Calculate specific gravity from phase composition")
        calc_sg_btn.connect('clicked', self._on_calculate_sg_clicked)
        toolbar.pack_start(calc_sg_btn, False, False, 0)

        if not self.editable:
            add_btn.set_sensitive(False)
            add_material_btn.set_sensitive(False)
            remove_btn.set_sensitive(False)
            calc_sg_btn.set_sensitive(False)

        self.pack_start(toolbar, False, False, 0)

        # Clinker fraction editor (initially hidden)
        self.clinker_editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.clinker_editor.set_margin_top(5)
        self.clinker_editor.set_margin_bottom(5)

        clinker_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.clinker_label = Gtk.Label()
        self.clinker_label.set_markup("<b>Clinker from:</b> (none)")
        self.clinker_label.set_halign(Gtk.Align.START)
        clinker_header.pack_start(self.clinker_label, False, False, 0)

        # Spacer
        clinker_header.pack_start(Gtk.Label(), True, True, 0)

        fraction_label = Gtk.Label(label="Total Clinker Fraction:")
        clinker_header.pack_start(fraction_label, False, False, 0)

        self.clinker_fraction_spinner = Gtk.SpinButton()
        self.clinker_fraction_spinner.set_adjustment(
            Gtk.Adjustment(value=0.0, lower=0.0, upper=1.0, step_increment=0.01, page_increment=0.1)
        )
        self.clinker_fraction_spinner.set_digits(4)
        self.clinker_fraction_spinner.set_width_chars(10)
        self.clinker_fraction_spinner.set_tooltip_text(
            "Edit the total clinker mass fraction.\n"
            "All clinker phases will be scaled proportionally."
        )
        self.clinker_fraction_spinner.connect('value-changed', self._on_clinker_fraction_changed)
        if not self.editable:
            self.clinker_fraction_spinner.set_sensitive(False)
        clinker_header.pack_start(self.clinker_fraction_spinner, False, False, 0)

        self.clinker_editor.pack_start(clinker_header, False, False, 0)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.clinker_editor.pack_start(separator, False, False, 0)

        self.pack_start(self.clinker_editor, False, False, 0)

        # Initially hide clinker editor
        self.clinker_editor.set_no_show_all(True)
        self.clinker_editor.hide()

        # TreeView for phase list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(200)
        scrolled.set_can_focus(True)  # Enable keyboard navigation

        # ListStore: phase_name (str), mass_fraction (float)
        self.store = Gtk.ListStore(str, float)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        # Column 1: Phase Name
        renderer_text = Gtk.CellRendererText()
        column_phase = Gtk.TreeViewColumn("Phase Name", renderer_text, text=0)
        column_phase.set_sort_column_id(0)
        column_phase.set_expand(True)
        self.treeview.append_column(column_phase)

        # Column 2: Mass Fraction (editable)
        renderer_fraction = Gtk.CellRendererText()
        renderer_fraction.set_property('editable', self.editable)
        renderer_fraction.connect('edited', self._on_fraction_edited)
        column_fraction = Gtk.TreeViewColumn("Mass Fraction", renderer_fraction, text=1)
        column_fraction.set_sort_column_id(1)
        self.treeview.append_column(column_fraction)

        scrolled.add(self.treeview)
        self.pack_start(scrolled, True, True, 0)

        # Status bar with total mass fraction
        self.status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.status_bar.set_margin_top(5)

        self.total_label = Gtk.Label()
        self.total_label.set_halign(Gtk.Align.START)
        self._update_total_label()

        self.status_bar.pack_start(self.total_label, True, True, 0)

        self.pack_start(self.status_bar, False, False, 0)

    def _on_add_phase_clicked(self, button):
        """Handle add phase button click."""
        dialog = AddPhaseDialog(
            parent=self.get_toplevel(),
            gems_parser=self.gems_parser,
            existing_phases=[p['phase_name'] for p in self.phases]
        )
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            phase_name = dialog.get_phase_name()
            mass_fraction = dialog.get_mass_fraction()

            if phase_name and mass_fraction is not None:
                self.add_phase(phase_name, mass_fraction)

        dialog.destroy()

    def _on_add_from_material_clicked(self, button):
        """Handle add from material button click."""
        if not self.material_service:
            return

        dialog = AddFromMaterialDialog(
            parent=self.get_toplevel(),
            material_service=self.material_service,
            exclude_material_id=self.exclude_material_id,
            existing_phases=[p['phase_name'] for p in self.phases]
        )
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            material = dialog.get_selected_material()
            mass_fraction = dialog.get_mass_fraction()

            if material and mass_fraction is not None:
                self.add_phases_from_material(material, mass_fraction)

        dialog.destroy()

    def add_phases_from_material(self, material, mass_fraction: float):
        """
        Add all phases from a material, scaled by mass fraction.

        Args:
            material: Material object with phases
            mass_fraction: Mass fraction to scale phases by (0.0-1.0)
        """
        if not material.phases:
            self._show_error(f"Material '{material.name}' has no phases defined")
            return

        added_count = 0
        clinker_phase_names = []  # Track phases added from this clinker

        for phase in material.phases:
            scaled_fraction = phase.mass_fraction * mass_fraction
            phase_name = phase.gem_phase_name

            # Check if phase already exists - if so, add to existing fraction
            existing = next((p for p in self.phases if p['phase_name'] == phase_name), None)
            if existing:
                # Update existing phase fraction
                new_fraction = existing['mass_fraction'] + scaled_fraction
                existing['mass_fraction'] = new_fraction

                # Update store
                for row in self.store:
                    if row[0] == phase_name:
                        row[1] = new_fraction
                        break

                self.logger.info(f"Updated phase {phase_name}: +{scaled_fraction:.4f} = {new_fraction:.4f}")
            else:
                # Add new phase (skip validation since it's from an existing material)
                self.phases.append({
                    'phase_name': phase_name,
                    'mass_fraction': scaled_fraction
                })
                self.store.append([phase_name, scaled_fraction])
                self.logger.info(f"Added phase from material: {phase_name} ({scaled_fraction:.4f})")

            # Track clinker phases
            if material.is_clinker:
                clinker_phase_names.append(phase_name)

            added_count += 1

        self._update_total_label()
        self.emit('composition-changed')

        # If the material is a clinker, set up clinker tracking and show editor
        if material.is_clinker:
            # If this is the first clinker or a different clinker, set source
            if not self.clinker_source_id or self.clinker_source_id == material.id:
                self.clinker_source_id = material.id
                self.clinker_source_name = material.name

                # Add new clinker phases to tracking (avoid duplicates)
                for phase_name in clinker_phase_names:
                    if phase_name not in self.clinker_phase_names:
                        self.clinker_phase_names.append(phase_name)
            else:
                # Different clinker being added - warn user
                self.logger.warning(f"Adding phases from different clinker {material.name} - original was {self.clinker_source_name}")

            # Calculate total clinker fraction from all clinker phases
            total_clinker = sum(
                p['mass_fraction'] for p in self.phases
                if p['phase_name'] in self.clinker_phase_names
            )

            # Update clinker editor UI
            self.clinker_label.set_markup(f"<b>Clinker from:</b> {material.name}")
            self.clinker_fraction_spinner.set_value(total_clinker)

            # Show clinker editor (use show_all to show all children)
            self.clinker_editor.set_no_show_all(False)  # Allow show_all to work
            self.clinker_editor.show_all()

            # Emit the clinker-source-added signal
            self.emit('clinker-source-added', material.id)
            self.logger.info(f"Clinker source detected: {material.name} (id={material.id}, total={total_clinker:.4f})")

        self.logger.info(f"Added {added_count} phases from material '{material.name}'")

    def _on_remove_phase_clicked(self, button):
        """Handle remove phase button click."""
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter is not None:
            phase_name = model[treeiter][0]

            # Confirm deletion
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Remove phase '{phase_name}'?"
            )
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                self.remove_phase(phase_name)

    def _on_fraction_edited(self, renderer, path, new_text):
        """Handle mass fraction cell edit."""
        try:
            new_fraction = float(new_text)

            if new_fraction < 0.0 or new_fraction > 1.0:
                self._show_error("Mass fraction must be between 0.0 and 1.0")
                return

            # Update store
            self.store[path][1] = new_fraction

            # Update internal data
            phase_name = self.store[path][0]
            for phase in self.phases:
                if phase['phase_name'] == phase_name:
                    phase['mass_fraction'] = new_fraction
                    break

            # If this is a clinker phase, update the clinker total
            if self.clinker_source_id and phase_name in self.clinker_phase_names:
                self._update_clinker_total_from_phases()

            self._update_total_label()
            self.emit('composition-changed')

        except ValueError:
            self._show_error("Invalid number format")

    def _on_clinker_fraction_changed(self, spinner):
        """Handle clinker fraction spinner change - rescale all clinker phases."""
        if not self.clinker_source_id or not self.clinker_phase_names:
            return

        new_total = spinner.get_value()

        # Calculate current total of clinker phases
        current_total = sum(
            p['mass_fraction'] for p in self.phases
            if p['phase_name'] in self.clinker_phase_names
        )

        if current_total == 0:
            self.logger.warning("Cannot rescale clinker phases: current total is 0")
            return

        # Calculate scaling factor
        scale_factor = new_total / current_total

        # Update all clinker phases
        for phase in self.phases:
            if phase['phase_name'] in self.clinker_phase_names:
                phase['mass_fraction'] *= scale_factor

        # Update store
        for row in self.store:
            if row[0] in self.clinker_phase_names:
                row[1] *= scale_factor

        self._update_total_label()
        self.emit('composition-changed')

        self.logger.info(f"Rescaled clinker phases by {scale_factor:.4f} to total {new_total:.4f}")

    def _update_clinker_total_from_phases(self):
        """Update the clinker fraction spinner based on current phase fractions."""
        if not self.clinker_source_id or not self.clinker_phase_names:
            return

        # Block signal to prevent recursive updates
        self.clinker_fraction_spinner.handler_block_by_func(self._on_clinker_fraction_changed)

        # Calculate current total
        current_total = sum(
            p['mass_fraction'] for p in self.phases
            if p['phase_name'] in self.clinker_phase_names
        )

        self.clinker_fraction_spinner.set_value(current_total)

        # Unblock signal
        self.clinker_fraction_spinner.handler_unblock_by_func(self._on_clinker_fraction_changed)

    def _on_calculate_sg_clicked(self, button):
        """Handle auto-calculate SG button click."""
        if not self.phases:
            self._show_error("No phases defined. Add phases first.")
            return

        try:
            phase_composition = {p['phase_name']: p['mass_fraction'] for p in self.phases}
            sg = self.gems_parser.calculate_material_specific_gravity(phase_composition)

            if sg is None:
                self._show_error("Could not calculate SG. Check phase composition.")
                return

            # Show result dialog with Yes/No buttons
            dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text=f"Calculated Specific Gravity: {sg:.3f}"
            )
            dialog.format_secondary_text(
                "Update the material's SG field with this value?"
            )
            response = dialog.run()
            dialog.destroy()

            # Emit signal if user clicked Yes
            if response == Gtk.ResponseType.YES:
                self.emit('sg-calculated', sg)
                self.logger.info(f"Auto-calculated SG: {sg:.3f}")

        except Exception as e:
            self.logger.error(f"Error calculating SG: {e}")
            self._show_error(f"Error calculating SG: {str(e)}")

    def add_phase(self, phase_name: str, mass_fraction: float) -> bool:
        """
        Add a phase to the composition.

        Args:
            phase_name: Name of GEMS phase
            mass_fraction: Mass fraction (0.0-1.0)

        Returns:
            True if added successfully, False otherwise
        """
        # Validate phase exists in GEMS
        if not self.gems_parser.get_phase(phase_name):
            self._show_error(f"Phase '{phase_name}' not found in GEMS database")
            return False

        # Check for duplicates
        if any(p['phase_name'] == phase_name for p in self.phases):
            self._show_error(f"Phase '{phase_name}' already exists")
            return False

        # Validate fraction
        if mass_fraction < 0.0 or mass_fraction > 1.0:
            self._show_error("Mass fraction must be between 0.0 and 1.0")
            return False

        # Add to internal list
        self.phases.append({
            'phase_name': phase_name,
            'mass_fraction': mass_fraction
        })

        # Add to store
        self.store.append([phase_name, mass_fraction])

        self._update_total_label()
        self.emit('composition-changed')

        self.logger.info(f"Added phase: {phase_name} ({mass_fraction:.4f})")
        return True

    def remove_phase(self, phase_name: str) -> bool:
        """
        Remove a phase from the composition.

        Args:
            phase_name: Name of phase to remove

        Returns:
            True if removed, False if not found
        """
        # Remove from internal list
        original_len = len(self.phases)
        self.phases = [p for p in self.phases if p['phase_name'] != phase_name]

        if len(self.phases) == original_len:
            return False  # Not found

        # Remove from store
        for row in self.store:
            if row[0] == phase_name:
                self.store.remove(row.iter)
                break

        # If this was a clinker phase, remove from tracking
        if self.clinker_source_id and phase_name in self.clinker_phase_names:
            self.clinker_phase_names.remove(phase_name)

            # If all clinker phases are removed, hide the clinker editor
            if not self.clinker_phase_names:
                self._clear_clinker_tracking()
            else:
                # Update clinker total
                self._update_clinker_total_from_phases()

        self._update_total_label()
        self.emit('composition-changed')

        self.logger.info(f"Removed phase: {phase_name}")
        return True

    def get_composition(self) -> List[Dict[str, float]]:
        """
        Get the current phase composition.

        Returns:
            List of dicts with 'phase_name' and 'mass_fraction'
        """
        return self.phases.copy()

    def set_composition(self, phases: List[Dict[str, float]]):
        """
        Set the phase composition.

        Args:
            phases: List of dicts with 'phase_name' and 'mass_fraction'
        """
        self.clear()

        for phase in phases:
            self.add_phase(phase['phase_name'], phase['mass_fraction'])

    def clear(self):
        """Clear all phases."""
        self.phases = []
        self.store.clear()
        self._clear_clinker_tracking()
        self._update_total_label()
        self.emit('composition-changed')

    def _clear_clinker_tracking(self):
        """Clear clinker tracking and hide clinker editor."""
        self.clinker_source_id = None
        self.clinker_source_name = None
        self.clinker_phase_names = []

        # Hide clinker editor
        self.clinker_editor.hide()
        self.clinker_editor.set_no_show_all(True)  # Prevent show_all from showing it

        # Reset UI
        self.clinker_label.set_markup("<b>Clinker from:</b> (none)")
        self.clinker_fraction_spinner.set_value(0.0)

    def set_clinker_source(self, clinker_material_id: int, clinker_material_name: str,
                           clinker_phase_names: List[str]):
        """
        Set clinker source information for an existing material.

        This is used when loading a material that was created from a clinker source.

        Args:
            clinker_material_id: ID of the clinker material
            clinker_material_name: Name of the clinker material
            clinker_phase_names: List of phase names that came from the clinker
        """
        self.clinker_source_id = clinker_material_id
        self.clinker_source_name = clinker_material_name
        self.clinker_phase_names = clinker_phase_names

        # Calculate total clinker fraction
        clinker_total = sum(
            p['mass_fraction'] for p in self.phases
            if p['phase_name'] in clinker_phase_names
        )

        # Update UI
        self.clinker_label.set_markup(f"<b>Clinker from:</b> {clinker_material_name}")
        self.clinker_fraction_spinner.set_value(clinker_total)

        # Show clinker editor (use show_all to show all children)
        self.clinker_editor.set_no_show_all(False)  # Allow show_all to work
        self.clinker_editor.show_all()

        self.logger.info(f"Restored clinker tracking: {clinker_material_name} (total={clinker_total:.4f})")

    def get_total_mass_fraction(self) -> float:
        """Get the sum of all mass fractions."""
        return sum(p['mass_fraction'] for p in self.phases)

    def is_valid_composition(self) -> Tuple[bool, str]:
        """
        Validate the composition.

        Returns:
            (is_valid, message)
        """
        if not self.phases:
            return False, "No phases defined"

        total = self.get_total_mass_fraction()

        # Allow small tolerance for floating point
        if abs(total - 1.0) > 0.01:
            return False, f"Mass fractions sum to {total:.4f}, should be 1.0"

        return True, "Valid composition"

    def _update_total_label(self):
        """Update the total mass fraction label."""
        total = self.get_total_mass_fraction()

        if abs(total - 1.0) < 0.01:
            # Valid - green checkmark
            markup = f'<span foreground="green">✓ Total: {total:.4f}</span>'
        elif total > 0:
            # Invalid - orange warning
            markup = f'<span foreground="orange">⚠ Total: {total:.4f} (should be 1.0)</span>'
        else:
            # Empty
            markup = '<span foreground="gray">Total: 0.0000</span>'

        self.total_label.set_markup(markup)

    def _show_error(self, message: str):
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()


class AddPhaseDialog(Gtk.Dialog):
    """Dialog for adding a phase to the composition."""

    def __init__(self, parent, gems_parser: GEMSParserService, existing_phases: List[str]):
        super().__init__(title="Add Phase", transient_for=parent, flags=0)

        self.gems_parser = gems_parser
        self.existing_phases = existing_phases

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Add", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(400, 200)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_left(20)
        content.set_margin_right(20)

        # Phase selector
        phase_label = Gtk.Label(label="GEMS Phase:")
        phase_label.set_halign(Gtk.Align.START)
        content.pack_start(phase_label, False, False, 0)

        self.phase_selector = GEMSPhaseSelector(
            gems_parser=self.gems_parser,
            phase_filter=None,  # Show all phases (user will select appropriate ones)
            placeholder="Type to search GEMS phases..."
        )
        content.pack_start(self.phase_selector, False, False, 0)

        # Mass fraction
        fraction_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        fraction_label = Gtk.Label(label="Mass Fraction:")
        fraction_label.set_width_chars(15)
        fraction_label.set_halign(Gtk.Align.START)

        self.fraction_spinner = Gtk.SpinButton()
        self.fraction_spinner.set_adjustment(
            Gtk.Adjustment(value=0.0, lower=0.0, upper=1.0, step_increment=0.01, page_increment=0.1)
        )
        self.fraction_spinner.set_digits(4)

        fraction_box.pack_start(fraction_label, False, False, 0)
        fraction_box.pack_start(self.fraction_spinner, True, True, 0)
        content.pack_start(fraction_box, False, False, 0)

    def get_phase_name(self) -> Optional[str]:
        """Get the selected phase name."""
        return self.phase_selector.get_selected_phase()

    def get_mass_fraction(self) -> Optional[float]:
        """Get the entered mass fraction."""
        return self.fraction_spinner.get_value()


class AddFromMaterialDialog(Gtk.Dialog):
    """Dialog for adding phases from an existing material."""

    def __init__(self, parent, material_service: MaterialService,
                 exclude_material_id: int = None, existing_phases: List[str] = None):
        super().__init__(title="Add from Material", transient_for=parent, flags=0)

        self.material_service = material_service
        self.exclude_material_id = exclude_material_id
        self.existing_phases = existing_phases or []
        self.selected_material = None

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Add", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(500, 450)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_left(20)
        content.set_margin_right(20)

        # Instructions
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>Select a material to add all its phases.\n"
            "Phases will be scaled by the mass fraction you specify.</small>"
        )
        info_label.set_halign(Gtk.Align.START)
        content.pack_start(info_label, False, False, 0)

        # Material list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(250)
        scrolled.set_can_focus(True)  # Enable keyboard navigation

        # ListStore: id, name, is_clinker, phase_count
        self.store = Gtk.ListStore(int, str, bool, int)

        # Get all materials
        all_materials = self.material_service.get_all()
        for mat in all_materials:
            # Skip the material being edited
            if self.exclude_material_id and mat.id == self.exclude_material_id:
                continue
            # Skip materials with no phases
            if not mat.phases:
                continue
            self.store.append([mat.id, mat.name, mat.is_clinker, len(mat.phases)])

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self.treeview.get_selection().connect('changed', self._on_selection_changed)

        # Column: Name
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn("Material Name", name_renderer, text=1)
        name_column.set_expand(True)
        name_column.set_sort_column_id(1)
        self.treeview.append_column(name_column)

        # Column: Type (Clinker indicator)
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer)
        type_column.set_cell_data_func(type_renderer, self._type_cell_func)
        self.treeview.append_column(type_column)

        # Column: Phase count
        count_renderer = Gtk.CellRendererText()
        count_column = Gtk.TreeViewColumn("Phases", count_renderer, text=3)
        count_column.set_sort_column_id(3)
        self.treeview.append_column(count_column)

        scrolled.add(self.treeview)
        content.pack_start(scrolled, True, True, 0)

        # Mass fraction entry
        fraction_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        fraction_label = Gtk.Label(label="Mass Fraction:")
        fraction_label.set_width_chars(15)
        fraction_label.set_halign(Gtk.Align.START)

        self.fraction_spinner = Gtk.SpinButton()
        self.fraction_spinner.set_adjustment(
            Gtk.Adjustment(value=1.0, lower=0.001, upper=1.0, step_increment=0.01, page_increment=0.1)
        )
        self.fraction_spinner.set_digits(4)
        self.fraction_spinner.set_tooltip_text(
            "The material's phases will be scaled by this fraction.\n"
            "Use 1.0 to add phases at their original fractions."
        )

        fraction_box.pack_start(fraction_label, False, False, 0)
        fraction_box.pack_start(self.fraction_spinner, True, True, 0)
        content.pack_start(fraction_box, False, False, 0)

        # Preview label (shows selected material info)
        self.preview_label = Gtk.Label()
        self.preview_label.set_halign(Gtk.Align.START)
        self.preview_label.set_margin_top(10)
        content.pack_start(self.preview_label, False, False, 0)

    def _type_cell_func(self, column, cell, model, iter, data=None):
        """Format the type column."""
        is_clinker = model.get_value(iter, 2)
        if is_clinker:
            cell.set_property("text", "Clinker")
            cell.set_property("foreground", "blue")
        else:
            cell.set_property("text", "")
            cell.set_property("foreground", None)

    def _on_selection_changed(self, selection):
        """Handle material selection change."""
        model, treeiter = selection.get_selected()
        if treeiter:
            mat_id = model.get_value(treeiter, 0)
            mat_name = model.get_value(treeiter, 1)
            is_clinker = model.get_value(treeiter, 2)
            phase_count = model.get_value(treeiter, 3)

            # Get full material with phases
            self.selected_material = self.material_service.get_by_id(mat_id)

            # Update preview
            if self.selected_material and self.selected_material.phases:
                phase_names = [p.gem_phase_name for p in self.selected_material.phases]
                phases_text = ", ".join(phase_names[:5])
                if len(phase_names) > 5:
                    phases_text += f", ... (+{len(phase_names) - 5} more)"

                clinker_note = " (Clinker - will set as source)" if is_clinker else ""
                self.preview_label.set_markup(
                    f"<small><b>Phases:</b> {phases_text}{clinker_note}</small>"
                )
            else:
                self.preview_label.set_text("")
        else:
            self.selected_material = None
            self.preview_label.set_text("")

    def get_selected_material(self):
        """Get the selected material object."""
        return self.selected_material

    def get_mass_fraction(self) -> Optional[float]:
        """Get the entered mass fraction."""
        return self.fraction_spinner.get_value()


# Register signals
GObject.type_register(PhaseCompositionEditor)

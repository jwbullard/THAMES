#!/usr/bin/env python3
"""
Affinity Editor Dialog

Dialog for editing interface affinity (contact angles) between a hydration product
and other phases in the microstructure. Based on classical nucleation theory,
contact angles control where products prefer to nucleate.

Contact angle meanings:
- 0° = Maximum affinity (high nucleation probability)
- 90° = Neutral (no preference)
- 180° = No affinity (avoids this substrate)
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
import logging
from typing import List, Dict, Any, Optional

from app.services.hydration_products_service import (
    get_hydration_products_service,
    DEFAULT_CONTACT_ANGLE,
)


class AffinityEditorDialog(Gtk.Dialog):
    """
    Dialog for editing interface affinity data for a hydration product.

    Allows users to specify contact angles with various substrate phases,
    controlling where the product prefers to nucleate.
    """

    def __init__(self, parent: Gtk.Window, gems_name: str,
                 current_affinity: Optional[List[Dict[str, Any]]] = None,
                 available_phases: Optional[List[str]] = None):
        """
        Initialize the affinity editor dialog.

        Args:
            parent: Parent window
            gems_name: GEMS name of the product being configured
            current_affinity: Current affinity configuration (list of dicts)
            available_phases: List of available substrate phases (if None, uses defaults)
        """
        super().__init__(
            title=f"Interface Affinity - {gems_name}",
            transient_for=parent,
            flags=0
        )

        self.gems_name = gems_name
        self.logger = logging.getLogger('THAMES.AffinityEditorDialog')
        self.service = get_hydration_products_service()

        # Store current configuration
        self.affinity_data: List[Dict[str, Any]] = []
        if current_affinity:
            self.affinity_data = [dict(a) for a in current_affinity]  # Deep copy
        else:
            # Use defaults from service
            self.affinity_data = self.service.get_default_affinity(gems_name)

        # Available substrate phases
        if available_phases:
            self.available_phases = available_phases
        else:
            # Default set of common substrate phases
            self.available_phases = [
                # Clinker phases
                "Alite", "Belite", "Aluminate", "Ferrite",
                # Sulfate phases
                "Gypsum", "Bassanite", "Anhydite",
                "Arcanite", "Thenardite",
                # Common products
                "CSHQ", "Portlandite", "ettr", "ettr-AlFe",
                "monosulf-AlFe", "C4AsH12", "C4AsH14",
                "C3AH6", "C4AH13",
                # Carbonate phases
                "Calcite", "Dolomite-dis",
                # AFt/AFm phases
                "C6AsH13", "C6AsH9", "SO4_CO3_AFt",
                "C4AcH11", "C4Ac0.5H12",
                # Other
                "hydrotalc-pyro",
            ]

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(600, 500)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(15)
        content.set_margin_bottom(15)
        content.set_margin_start(15)
        content.set_margin_end(15)

        # Header with explanation
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        title_label = Gtk.Label()
        title_label.set_markup(
            f"<b>Interface Affinity for {self.service.get_display_name(self.gems_name)}</b>"
        )
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, False, False, 0)

        explanation = Gtk.Label()
        explanation.set_markup(
            "<small>Contact angles control where this product prefers to nucleate:\n"
            "• <b>0°</b> = Maximum affinity (prefers this substrate)\n"
            "• <b>90°</b> = Neutral (no preference)\n"
            "• <b>180°</b> = No affinity (avoids this substrate)</small>"
        )
        explanation.set_halign(Gtk.Align.START)
        explanation.set_line_wrap(True)
        header_box.pack_start(explanation, False, False, 0)

        content.pack_start(header_box, False, False, 0)

        # Separator
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        add_btn = Gtk.Button(label="Add Phase")
        add_btn.connect('clicked', self._on_add_clicked)
        toolbar.pack_start(add_btn, False, False, 0)

        remove_btn = Gtk.Button(label="Remove")
        remove_btn.connect('clicked', self._on_remove_clicked)
        toolbar.pack_start(remove_btn, False, False, 0)

        toolbar.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.set_tooltip_text("Reset to default affinity values")
        reset_btn.connect('clicked', self._on_reset_clicked)
        toolbar.pack_start(reset_btn, False, False, 0)

        content.pack_start(toolbar, False, False, 0)

        # Affinity list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(280)

        # ListStore: affinityphase (str), contactanglevalue (int), angle_display (str)
        self.store = Gtk.ListStore(str, int, str)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        # Column 1: Phase Name
        renderer_phase = Gtk.CellRendererText()
        column_phase = Gtk.TreeViewColumn("Substrate Phase", renderer_phase, text=0)
        column_phase.set_expand(True)
        column_phase.set_sort_column_id(0)
        self.treeview.append_column(column_phase)

        # Column 2: Contact Angle (editable spin)
        renderer_angle = Gtk.CellRendererSpin()
        renderer_angle.set_property('editable', True)
        renderer_angle.set_property('adjustment',
                                    Gtk.Adjustment(value=90, lower=0, upper=180,
                                                   step_increment=5, page_increment=30))
        renderer_angle.connect('edited', self._on_angle_edited)
        column_angle = Gtk.TreeViewColumn("Contact Angle (°)", renderer_angle, text=1)
        column_angle.set_min_width(120)
        column_angle.set_sort_column_id(1)
        self.treeview.append_column(column_angle)

        # Column 3: Affinity interpretation
        renderer_interp = Gtk.CellRendererText()
        renderer_interp.set_property('foreground', 'gray')
        column_interp = Gtk.TreeViewColumn("Interpretation", renderer_interp, text=2)
        column_interp.set_min_width(120)
        self.treeview.append_column(column_interp)

        scrolled.add(self.treeview)
        content.pack_start(scrolled, True, True, 0)

        # Info about default angle
        info_label = Gtk.Label()
        info_label.set_markup(
            f"<small><i>Phases not listed here use the default contact angle of "
            f"{DEFAULT_CONTACT_ANGLE}° (neutral).</i></small>"
        )
        info_label.set_halign(Gtk.Align.START)
        content.pack_start(info_label, False, False, 0)

        # Populate the store
        self._populate_store()

    def _get_angle_interpretation(self, angle: int) -> str:
        """Get human-readable interpretation of contact angle."""
        if angle == 0:
            return "Maximum affinity"
        elif angle < 30:
            return "High affinity"
        elif angle < 60:
            return "Good affinity"
        elif angle < 90:
            return "Slight affinity"
        elif angle == 90:
            return "Neutral"
        elif angle < 120:
            return "Slight avoidance"
        elif angle < 150:
            return "Avoidance"
        elif angle < 180:
            return "Strong avoidance"
        else:
            return "No affinity"

    def _populate_store(self):
        """Populate the store with current affinity data."""
        self.store.clear()

        for entry in self.affinity_data:
            phase = entry.get('affinityphase', '')
            angle = entry.get('contactanglevalue', DEFAULT_CONTACT_ANGLE)
            interpretation = self._get_angle_interpretation(angle)

            self.store.append([phase, angle, interpretation])

    def _on_angle_edited(self, renderer, path, new_text):
        """Handle contact angle edit."""
        try:
            new_angle = int(float(new_text))
            new_angle = max(0, min(180, new_angle))  # Clamp to 0-180

            self.store[path][1] = new_angle
            self.store[path][2] = self._get_angle_interpretation(new_angle)

            # Update internal data
            phase = self.store[path][0]
            for entry in self.affinity_data:
                if entry['affinityphase'] == phase:
                    entry['contactanglevalue'] = new_angle
                    break

            self.logger.debug(f"Updated contact angle for {phase}: {new_angle}°")

        except ValueError:
            self.logger.warning(f"Invalid angle value: {new_text}")

    def _on_add_clicked(self, button):
        """Add a new affinity entry."""
        # Show dialog to select phase
        dialog = AddAffinityDialog(
            self,
            self.available_phases,
            [entry['affinityphase'] for entry in self.affinity_data]
        )
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            phase = dialog.get_selected_phase()
            angle = dialog.get_contact_angle()

            if phase:
                # Add to data
                self.affinity_data.append({
                    'affinityphase': phase,
                    'contactanglevalue': angle
                })

                # Add to store
                self.store.append([phase, angle, self._get_angle_interpretation(angle)])
                self.logger.info(f"Added affinity: {phase} = {angle}°")

        dialog.destroy()

    def _on_remove_clicked(self, button):
        """Remove selected affinity entry."""
        selection = self.treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter:
            phase = model.get_value(treeiter, 0)

            # Remove from data
            self.affinity_data = [e for e in self.affinity_data
                                  if e['affinityphase'] != phase]

            # Remove from store
            model.remove(treeiter)
            self.logger.info(f"Removed affinity: {phase}")

    def _on_reset_clicked(self, button):
        """Reset to default affinity values."""
        confirm = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset to defaults?"
        )
        confirm.format_secondary_text(
            "This will replace all current affinity values with the defaults."
        )
        response = confirm.run()
        confirm.destroy()

        if response == Gtk.ResponseType.YES:
            self.affinity_data = self.service.get_default_affinity(self.gems_name)
            self._populate_store()
            self.logger.info(f"Reset affinity to defaults for {self.gems_name}")

    def get_affinity_data(self) -> List[Dict[str, Any]]:
        """
        Get the configured affinity data.

        Returns:
            List of dicts with 'affinityphase' and 'contactanglevalue'
        """
        return self.affinity_data


class AddAffinityDialog(Gtk.Dialog):
    """Dialog for adding a new affinity entry."""

    def __init__(self, parent: Gtk.Window, available_phases: List[str],
                 existing_phases: List[str]):
        super().__init__(
            title="Add Affinity Entry",
            transient_for=parent,
            flags=0
        )

        self.available_phases = available_phases
        self.existing_phases = existing_phases

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Add", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(350, 200)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(15)
        content.set_margin_top(20)
        content.set_margin_bottom(10)
        content.set_margin_start(20)
        content.set_margin_end(20)

        # Phase selector
        phase_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        phase_label = Gtk.Label(label="Substrate Phase:")
        phase_label.set_halign(Gtk.Align.START)
        phase_label.set_width_chars(15)

        self.phase_combo = Gtk.ComboBoxText()
        # Add phases not already in the list
        for phase in sorted(self.available_phases):
            if phase not in self.existing_phases:
                self.phase_combo.append_text(phase)
        self.phase_combo.set_active(0)

        phase_box.pack_start(phase_label, False, False, 0)
        phase_box.pack_start(self.phase_combo, True, True, 0)
        content.pack_start(phase_box, False, False, 0)

        # Contact angle
        angle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        angle_label = Gtk.Label(label="Contact Angle:")
        angle_label.set_halign(Gtk.Align.START)
        angle_label.set_width_chars(15)

        self.angle_spin = Gtk.SpinButton()
        self.angle_spin.set_adjustment(
            Gtk.Adjustment(value=90, lower=0, upper=180, step_increment=5, page_increment=30)
        )
        self.angle_spin.set_value(90)  # Default to neutral

        angle_unit = Gtk.Label(label="°")

        angle_box.pack_start(angle_label, False, False, 0)
        angle_box.pack_start(self.angle_spin, False, False, 0)
        angle_box.pack_start(angle_unit, False, False, 0)
        content.pack_start(angle_box, False, False, 0)

        # Quick preset buttons
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        preset_label = Gtk.Label(label="Presets:")
        preset_label.set_width_chars(15)
        preset_box.pack_start(preset_label, False, False, 0)

        for label, value in [("High (0°)", 0), ("Good (30°)", 30),
                             ("Neutral (90°)", 90), ("Avoid (180°)", 180)]:
            btn = Gtk.Button(label=label)
            btn.connect('clicked', self._on_preset_clicked, value)
            preset_box.pack_start(btn, False, False, 0)

        content.pack_start(preset_box, False, False, 0)

    def _on_preset_clicked(self, button, value):
        """Set angle to preset value."""
        self.angle_spin.set_value(value)

    def get_selected_phase(self) -> Optional[str]:
        """Get the selected phase."""
        return self.phase_combo.get_active_text()

    def get_contact_angle(self) -> int:
        """Get the contact angle."""
        return int(self.angle_spin.get_value())

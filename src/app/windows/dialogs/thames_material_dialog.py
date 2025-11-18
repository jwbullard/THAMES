#!/usr/bin/env python3
"""
THAMES Material Dialog - Tag-based material creation/editing with phase composition

Phase 3 implementation with clinker and composite material support.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import logging
from typing import Optional, List, Dict

from app.services.material_service import MaterialService
from app.models import MaterialCreate, MaterialUpdate
from app.widgets.phase_composition_editor import PhaseCompositionEditor


class MaterialDialog(Gtk.Dialog):
    """Simple dialog for creating/editing THAMES materials."""

    def __init__(self, parent, material_service: MaterialService, mode='create', material=None):
        """
        Initialize material dialog.

        Args:
            parent: Parent window
            material_service: MaterialService instance
            mode: 'create' or 'edit'
            material: Material object (for edit mode)
        """
        # Check if material is immutable (read-only)
        self.is_immutable = material.immutable if (material and hasattr(material, 'immutable')) else False

        if self.is_immutable:
            title = f"View Material: {material.name if material else ''} (Read-only)"
        else:
            title = "Add Material" if mode == 'create' else f"Edit Material: {material.name if material else ''}"

        super().__init__(title=title, transient_for=parent, flags=0)

        self.material_service = material_service
        self.mode = mode
        self.material = material
        self.material_name = None
        self.logger = logging.getLogger('THAMES.MaterialDialog')

        # Dialog buttons
        self.add_button("Cancel" if self.is_immutable else "Cancel", Gtk.ResponseType.CANCEL)
        if not self.is_immutable:
            self.add_button("Save", Gtk.ResponseType.OK)
            self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(700, 700)  # Larger to accommodate phase editor

        # Build UI
        self._build_ui()

        # Load material data if editing
        if mode == 'edit' and material:
            self._load_material_data(material)

        # Apply immutable protection
        if self.is_immutable:
            self._apply_immutable_protection()

        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_left(20)
        content.set_margin_right(20)

        # Name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        name_label = Gtk.Label(label="Name:")
        name_label.set_width_chars(20)
        name_label.set_halign(Gtk.Align.START)
        self.name_entry = Gtk.Entry()
        name_box.pack_start(name_label, False, False, 0)
        name_box.pack_start(self.name_entry, True, True, 0)
        content.pack_start(name_box, False, False, 0)

        # Tags (simple comma-separated entry)
        tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tags_label = Gtk.Label(label="Tags (comma-separated):")
        tags_label.set_width_chars(20)
        tags_label.set_halign(Gtk.Align.START)
        self.tags_entry = Gtk.Entry()
        self.tags_entry.set_placeholder_text("e.g., cement, type-i, portland")
        tags_box.pack_start(tags_label, False, False, 0)
        tags_box.pack_start(self.tags_entry, True, True, 0)
        content.pack_start(tags_box, False, False, 0)

        # Specific Gravity
        sg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        sg_label = Gtk.Label(label="Specific Gravity:")
        sg_label.set_width_chars(20)
        sg_label.set_halign(Gtk.Align.START)
        self.sg_spinner = Gtk.SpinButton()
        self.sg_spinner.set_adjustment(Gtk.Adjustment(value=3.15, lower=0.1, upper=10.0, step_increment=0.01, page_increment=0.1))
        self.sg_spinner.set_digits(3)
        sg_box.pack_start(sg_label, False, False, 0)
        sg_box.pack_start(self.sg_spinner, True, True, 0)
        content.pack_start(sg_box, False, False, 0)

        # Specific Surface Area
        ssa_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        ssa_label = Gtk.Label(label="Specific Surface Area:")
        ssa_label.set_width_chars(20)
        ssa_label.set_halign(Gtk.Align.START)
        self.ssa_spinner = Gtk.SpinButton()
        self.ssa_spinner.set_adjustment(Gtk.Adjustment(value=350.0, lower=0.0, upper=10000.0, step_increment=10.0, page_increment=100.0))
        self.ssa_spinner.set_digits(1)
        ssa_box.pack_start(ssa_label, False, False, 0)
        ssa_box.pack_start(self.ssa_spinner, True, True, 0)
        content.pack_start(ssa_box, False, False, 0)

        # PSD ID
        psd_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        psd_label = Gtk.Label(label="PSD Data ID:")
        psd_label.set_width_chars(20)
        psd_label.set_halign(Gtk.Align.START)
        self.psd_spinner = Gtk.SpinButton()
        self.psd_spinner.set_adjustment(Gtk.Adjustment(value=1, lower=1, upper=1000, step_increment=1, page_increment=10))
        self.psd_spinner.set_digits(0)
        psd_box.pack_start(psd_label, False, False, 0)
        psd_box.pack_start(self.psd_spinner, True, True, 0)
        content.pack_start(psd_box, False, False, 0)

        # Material Type Selector
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        type_label = Gtk.Label(label="Material Type:")
        type_label.set_width_chars(20)
        type_label.set_halign(Gtk.Align.START)

        self.type_combo = Gtk.ComboBoxText()
        self.type_combo.append("simple", "Simple Material")
        self.type_combo.append("clinker", "Clinker")
        self.type_combo.set_active_id("simple")
        self.type_combo.connect("changed", self._on_material_type_changed)

        type_box.pack_start(type_label, False, False, 0)
        type_box.pack_start(self.type_combo, True, True, 0)
        content.pack_start(type_box, False, False, 0)

        # Clinker Surface Fractions Section (hidden by default)
        self.clinker_frame = Gtk.Frame(label="Clinker Surface Area Fractions")
        clinker_grid = Gtk.Grid()
        clinker_grid.set_margin_top(10)
        clinker_grid.set_margin_bottom(10)
        clinker_grid.set_margin_left(15)
        clinker_grid.set_margin_right(15)
        clinker_grid.set_row_spacing(8)
        clinker_grid.set_column_spacing(10)

        # Create spinbuttons for 6 clinker phases
        self.clinker_spinners = {}
        clinker_phases = [
            ('c3s', 'C₃S (Alite)'),
            ('c2s', 'C₂S (Belite)'),
            ('c3a', 'C₃A (Aluminate)'),
            ('c4af', 'C₄AF (Ferrite)'),
            ('k2so4', 'K₂SO₄ (Arcanite)'),
            ('na2so4', 'Na₂SO₄ (Thenardite)')
        ]

        for i, (key, label_text) in enumerate(clinker_phases):
            label = Gtk.Label(label=f"{label_text}:")
            label.set_halign(Gtk.Align.END)

            spinner = Gtk.SpinButton()
            spinner.set_adjustment(Gtk.Adjustment(value=0.0, lower=0.0, upper=1.0, step_increment=0.01, page_increment=0.1))
            spinner.set_digits(4)
            spinner.connect("value-changed", self._on_clinker_fraction_changed)
            self.clinker_spinners[key] = spinner

            clinker_grid.attach(label, 0, i, 1, 1)
            clinker_grid.attach(spinner, 1, i, 1, 1)

        # Total label
        total_label = Gtk.Label(label="Total:")
        total_label.set_halign(Gtk.Align.END)
        total_label.get_style_context().add_class("bold")
        self.clinker_total_label = Gtk.Label(label="0.0000")
        self.clinker_total_label.set_halign(Gtk.Align.START)
        clinker_grid.attach(total_label, 0, len(clinker_phases), 1, 1)
        clinker_grid.attach(self.clinker_total_label, 1, len(clinker_phases), 1, 1)

        self.clinker_frame.add(clinker_grid)
        content.pack_start(self.clinker_frame, False, False, 0)
        self.clinker_frame.set_no_show_all(True)  # Hide by default

        # Description
        desc_label = Gtk.Label(label="Description:")
        desc_label.set_halign(Gtk.Align.START)
        content.pack_start(desc_label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 80)
        self.desc_textview = Gtk.TextView()
        self.desc_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(self.desc_textview)
        content.pack_start(scrolled, False, False, 0)

        # Track clinker source
        self.clinker_source_id = None
        if self.material:
            self.clinker_source_id = getattr(self.material, 'clinker_source_id', None)

        # Phase Composition Editor (in expander)
        expander = Gtk.Expander(label="Phase Composition")
        expander.set_expanded(True)  # Expanded by default

        # Create phase editor (get GEMS parser from material service)
        gems_parser = self.material_service.gems_parser
        exclude_id = self.material.id if self.material else None
        self.phase_editor = PhaseCompositionEditor(
            gems_parser=gems_parser,
            editable=not self.is_immutable,
            material_service=self.material_service,
            exclude_material_id=exclude_id
        )

        # Connect to sg-calculated signal
        self.phase_editor.connect('sg-calculated', self._on_sg_calculated)

        # Connect to clinker-source-added signal
        self.phase_editor.connect('clinker-source-added', self._on_clinker_source_added)

        expander.add(self.phase_editor)
        content.pack_start(expander, True, True, 0)

    def _load_material_data(self, material):
        """Load material data into form fields."""
        self.name_entry.set_text(material.name or "")
        if material.tag_names:
            self.tags_entry.set_text(", ".join(material.tag_names))
        if material.specific_gravity:
            self.sg_spinner.set_value(material.specific_gravity)
        if material.specific_surface_area:
            self.ssa_spinner.set_value(material.specific_surface_area)
        if material.psd_data_id:
            self.psd_spinner.set_value(material.psd_data_id)
        if material.description:
            buffer = self.desc_textview.get_buffer()
            buffer.set_text(material.description)

        # Load phase composition
        if material.phases:
            phases = [
                {'phase_name': p.gem_phase_name, 'mass_fraction': p.mass_fraction}
                for p in material.phases
            ]
            self.phase_editor.set_composition(phases)

        # Determine and set material type
        if material.is_clinker:
            self.type_combo.set_active_id("clinker")
            # Load clinker surface fractions
            fractions = self.material_service.get_clinker_surface_fractions(material.id)
            if fractions:
                for key, value in fractions.items():
                    if key in self.clinker_spinners:
                        self.clinker_spinners[key].set_value(value)
                self._on_clinker_fraction_changed(None)  # Update total
        else:
            self.type_combo.set_active_id("simple")

    def _on_sg_calculated(self, widget, sg_value):
        """Handle sg-calculated signal from phase editor."""
        self.sg_spinner.set_value(sg_value)
        self.logger.info(f"Updated SG field to calculated value: {sg_value:.3f}")

    def _on_clinker_source_added(self, widget, clinker_material_id):
        """Handle clinker-source-added signal from phase editor."""
        self.clinker_source_id = clinker_material_id
        clinker = self.material_service.get_by_id(clinker_material_id)
        clinker_name = clinker.name if clinker else f"ID {clinker_material_id}"
        self.logger.info(f"Clinker source set: {clinker_name} (id={clinker_material_id})")

    def _on_material_type_changed(self, combo):
        """Handle material type selection change."""
        material_type = combo.get_active_id()

        # Show/hide relevant sections
        if material_type == "clinker":
            self.clinker_frame.set_no_show_all(False)
            self.clinker_frame.show_all()
        else:  # simple
            self.clinker_frame.hide()

    def _on_clinker_fraction_changed(self, spinner):
        """Update total when clinker fraction changes."""
        total = sum(s.get_value() for s in self.clinker_spinners.values())
        self.clinker_total_label.set_text(f"{total:.4f}")

        # Color code: green if valid (~1.0), red if not
        if abs(total - 1.0) <= 0.01:
            self.clinker_total_label.set_markup(f'<span foreground="green">{total:.4f}</span>')
        else:
            self.clinker_total_label.set_markup(f'<span foreground="red">{total:.4f}</span>')

    def _apply_immutable_protection(self):
        """Disable all form fields for immutable materials."""
        # Add warning message at the top
        content = self.get_content_area()
        warning_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        warning_box.set_margin_bottom(10)

        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning", Gtk.IconSize.DIALOG)
        warning_box.pack_start(warning_icon, False, False, 0)

        warning_label = Gtk.Label()
        warning_label.set_markup(
            '<span foreground="orange"><b>Read-Only Material</b>\n'
            'This material was migrated from VCCTL and cannot be modified.</span>'
        )
        warning_label.set_halign(Gtk.Align.START)
        warning_box.pack_start(warning_label, True, True, 0)

        content.pack_start(warning_box, False, False, 0)
        content.reorder_child(warning_box, 0)  # Move to top

        # Disable all input fields
        self.name_entry.set_sensitive(False)
        self.tags_entry.set_sensitive(False)
        self.sg_spinner.set_sensitive(False)
        self.ssa_spinner.set_sensitive(False)
        self.psd_spinner.set_sensitive(False)
        self.type_combo.set_sensitive(False)
        self.desc_textview.set_editable(False)
        self.desc_textview.set_cursor_visible(False)

        # Disable clinker spinners
        for spinner in self.clinker_spinners.values():
            spinner.set_sensitive(False)

    def run(self):
        """Run the dialog and save if OK."""
        response = super().run()

        if response == Gtk.ResponseType.OK:
            if self._save_material():
                self.hide()  # Hide dialog after successful save
                return Gtk.ResponseType.OK
            else:
                # Keep dialog open on error
                return self.run()

        return response

    def _save_material(self) -> bool:
        """Save the material data."""
        try:
            # Get form data
            name = self.name_entry.get_text().strip()
            if not name:
                self._show_error("Name is required")
                return False

            tags_text = self.tags_entry.get_text().strip()
            tags = [t.strip() for t in tags_text.split(',') if t.strip()] if tags_text else []
            sg = self.sg_spinner.get_value()
            ssa = self.ssa_spinner.get_value()
            psd_id = int(self.psd_spinner.get_value())
            material_type = self.type_combo.get_active_id()

            buffer = self.desc_textview.get_buffer()
            desc = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

            # Get phase composition
            phase_composition = self.phase_editor.get_composition()

            # Validate phase composition if provided
            if phase_composition:
                is_valid, msg = self.phase_editor.is_valid_composition()
                if not is_valid:
                    self._show_error(f"Invalid phase composition: {msg}")
                    return False

                # Convert phase_name to gem_phase_name for service
                phase_compositions = [
                    {'gem_phase_name': p['phase_name'], 'mass_fraction': p['mass_fraction']}
                    for p in phase_composition
                ]
            else:
                phase_compositions = None

            # Validate clinker surface fractions
            if material_type == "clinker":
                total = sum(s.get_value() for s in self.clinker_spinners.values())
                if abs(total - 1.0) > 0.01:
                    self._show_error(f"Clinker surface fractions must sum to 1.0 (currently {total:.4f})")
                    return False

            if self.mode == 'create':
                if material_type == "clinker":
                    # Create clinker material
                    material_data = MaterialCreate(
                        name=name,
                        tags=tags,
                        specific_gravity=sg,
                        specific_surface_area=ssa if ssa > 0 else None,
                        psd_data_id=psd_id,
                        description=desc if desc else None,
                        is_clinker=True
                    )
                    surface_fractions = {
                        key: spinner.get_value()
                        for key, spinner in self.clinker_spinners.items()
                    }
                    created_material = self.material_service.create(
                        material_data,
                        phase_compositions=phase_compositions
                    )
                    self.material_service.set_clinker_surface_fractions(
                        created_material.id, surface_fractions
                    )
                    self.material_name = created_material.name
                else:
                    # Create simple material
                    # Determine if it has clinker (from phases added from a clinker material)
                    has_clinker = self.clinker_source_id is not None
                    material_data = MaterialCreate(
                        name=name,
                        tags=tags,
                        specific_gravity=sg,
                        specific_surface_area=ssa if ssa > 0 else None,
                        psd_data_id=psd_id,
                        description=desc if desc else None,
                        has_clinker=has_clinker,
                        clinker_source_id=self.clinker_source_id
                    )
                    created_material = self.material_service.create(
                        material_data,
                        phase_compositions=phase_compositions
                    )
                    self.material_name = created_material.name

                self.logger.info(f"Created {material_type} material: {self.material_name}")
            else:
                # Update existing material
                has_clinker = self.clinker_source_id is not None
                material_data = MaterialUpdate(
                    name=name,
                    tags=tags,
                    specific_gravity=sg,
                    specific_surface_area=ssa if ssa > 0 else None,
                    psd_data_id=psd_id,
                    description=desc if desc else None,
                    is_clinker=(material_type == "clinker"),
                    has_clinker=has_clinker,
                    clinker_source_id=self.clinker_source_id
                )
                updated_material = self.material_service.update(self.material.id, material_data)

                # Update phases separately (clear and re-add)
                if phase_compositions is not None:
                    # Remove all existing phases
                    for phase in self.material.phases:
                        self.material_service.remove_phase(self.material.id, phase.gem_phase_name)

                    # Add new phases
                    for phase_comp in phase_compositions:
                        self.material_service.add_phase(
                            self.material.id,
                            phase_comp['gem_phase_name'],
                            phase_comp['mass_fraction']
                        )

                # Update clinker surface fractions
                if material_type == "clinker":
                    surface_fractions = {
                        key: spinner.get_value()
                        for key, spinner in self.clinker_spinners.items()
                    }
                    self.material_service.set_clinker_surface_fractions(
                        self.material.id, surface_fractions
                    )

                self.material_name = updated_material.name
                self.logger.info(f"Updated {material_type} material: {self.material_name}")

            return True

        except Exception as e:
            self.logger.error(f"Error saving material: {e}")
            self._show_error(f"Error saving material: {str(e)}")
            return False

    def _show_error(self, message: str):
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()

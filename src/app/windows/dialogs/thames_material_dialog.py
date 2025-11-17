#!/usr/bin/env python3
"""
THAMES Material Dialog - Simple tag-based material creation/editing

This is a minimal implementation for Phase 1 testing.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import logging
from typing import Optional

from app.services.material_service import MaterialService
from app.models import MaterialCreate, MaterialUpdate


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
        self.set_default_size(500, 400)

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

        # Description
        desc_label = Gtk.Label(label="Description:")
        desc_label.set_halign(Gtk.Align.START)
        content.pack_start(desc_label, False, False, 0)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(-1, 100)
        self.desc_textview = Gtk.TextView()
        self.desc_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled.add(self.desc_textview)
        content.pack_start(scrolled, True, True, 0)

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
        self.desc_textview.set_editable(False)
        self.desc_textview.set_cursor_visible(False)

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

            buffer = self.desc_textview.get_buffer()
            desc = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

            if self.mode == 'create':
                # Create new material
                material_data = MaterialCreate(
                    name=name,
                    tags=tags,
                    specific_gravity=sg,
                    specific_surface_area=ssa if ssa > 0 else None,
                    psd_data_id=psd_id,
                    description=desc if desc else None
                )
                created_material = self.material_service.create(material_data)
                self.material_name = created_material.name
                self.logger.info(f"Created material: {self.material_name}")
            else:
                # Update existing material
                material_data = MaterialUpdate(
                    name=name,
                    tags=tags,
                    specific_gravity=sg,
                    specific_surface_area=ssa if ssa > 0 else None,
                    psd_data_id=psd_id,
                    description=desc if desc else None
                )
                updated_material = self.material_service.update(self.material.id, material_data)
                self.material_name = updated_material.name
                self.logger.info(f"Updated material: {self.material_name}")

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

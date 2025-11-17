#!/usr/bin/env python3
"""
Material Dialog for THAMES

Dialog for creating and editing materials with tag-based system.
Phase 1: Basic properties (name, tags, SG, description) - no phase editor yet.
"""

import gi
import logging
from typing import TYPE_CHECKING, Optional
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango

if TYPE_CHECKING:
    from app.windows.main_window import VCCTLMainWindow

from app.models.material import Material, MaterialCreate, MaterialUpdate
from app.widgets.tag_chip_input import TagChipInput


class MaterialDialog(Gtk.Dialog):
    """Dialog for creating/editing materials."""

    def __init__(self, parent: 'VCCTLMainWindow', material_data: Optional[Material] = None):
        """
        Initialize the material dialog.

        Args:
            parent: Parent window
            material_data: Material to edit (None for create)
        """
        self.material_data = material_data
        self.is_edit_mode = material_data is not None

        title = f"{'Edit' if self.is_edit_mode else 'Create'} Material"
        super().__init__(title=title, transient_for=parent, flags=0)

        self.parent_window = parent
        self.logger = logging.getLogger('THAMES.MaterialDialog')

        # Dialog configuration
        self.set_default_size(600, 500)
        self.set_resizable(True)
        self.set_modal(True)

        # Get material service
        self.material_service = None
        try:
            from app.services.material_service import MaterialService
            from app.database.service import DatabaseService
            from app.database.config import DatabaseConfig

            db_config = DatabaseConfig(db_name="thames.db")
            db_service = DatabaseService(db_config)
            gems_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "gems"
            self.material_service = MaterialService(db_service, gems_data_dir)
        except Exception as e:
            self.logger.error(f"Failed to initialize MaterialService: {e}")

        # Setup dialog
        self._setup_dialog()
        self._setup_ui()

        # Load data if editing
        if self.is_edit_mode:
            self._load_material_data()
            # Check if immutable
            if self.material_data.immutable:
                self._disable_editing()

    def _setup_dialog(self) -> None:
        """Setup dialog buttons."""
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.save_button = self.add_button("Save", Gtk.ResponseType.OK)
        self.save_button.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        content_area = self.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_start(20)
        content_area.set_margin_end(20)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)

        # Create form in scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        form_box.set_margin_start(5)
        form_box.set_margin_end(5)
        form_box.set_margin_top(10)
        form_box.set_margin_bottom(10)

        # Name field
        name_frame = Gtk.Frame(label="Material Name")
        name_grid = Gtk.Grid()
        name_grid.set_margin_start(15)
        name_grid.set_margin_end(15)
        name_grid.set_margin_top(10)
        name_grid.set_margin_bottom(10)
        name_grid.set_row_spacing(5)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_placeholder_text("Enter material name...")
        self.name_entry.set_hexpand(True)
        name_grid.attach(self.name_entry, 0, 0, 1, 1)

        name_frame.add(name_grid)
        form_box.pack_start(name_frame, False, False, 0)

        # Tags field
        tags_frame = Gtk.Frame(label="Tags")
        tags_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        tags_box.set_margin_start(15)
        tags_box.set_margin_end(15)
        tags_box.set_margin_top(10)
        tags_box.set_margin_bottom(10)

        help_label = Gtk.Label()
        help_label.set_markup('<span size="small">Enter tags to classify this material (e.g., cement, limestone, custom)</span>')
        help_label.set_halign(Gtk.Align.START)
        help_label.get_style_context().add_class('dim-label')
        tags_box.pack_start(help_label, False, False, 0)

        self.tag_input = TagChipInput()
        tags_box.pack_start(self.tag_input, True, True, 0)

        tags_frame.add(tags_box)
        form_box.pack_start(tags_frame, False, False, 0)

        # Properties grid
        props_frame = Gtk.Frame(label="Properties")
        props_grid = Gtk.Grid()
        props_grid.set_margin_start(15)
        props_grid.set_margin_end(15)
        props_grid.set_margin_top(10)
        props_grid.set_margin_bottom(10)
        props_grid.set_row_spacing(10)
        props_grid.set_column_spacing(15)

        # Specific Gravity
        sg_label = Gtk.Label("Specific Gravity:")
        sg_label.set_halign(Gtk.Align.END)
        props_grid.attach(sg_label, 0, 0, 1, 1)

        self.sg_spin = Gtk.SpinButton.new_with_range(0.1, 10.0, 0.01)
        self.sg_spin.set_value(3.15)  # Default
        self.sg_spin.set_digits(3)
        self.sg_spin.set_hexpand(True)
        props_grid.attach(self.sg_spin, 1, 0, 1, 1)

        sg_unit_label = Gtk.Label("g/cm³")
        sg_unit_label.set_halign(Gtk.Align.START)
        props_grid.attach(sg_unit_label, 2, 0, 1, 1)

        # Specific Surface Area (optional)
        ssa_label = Gtk.Label("Specific Surface Area:")
        ssa_label.set_halign(Gtk.Align.END)
        props_grid.attach(ssa_label, 0, 1, 1, 1)

        self.ssa_spin = Gtk.SpinButton.new_with_range(0.0, 10000.0, 10.0)
        self.ssa_spin.set_value(0.0)
        self.ssa_spin.set_digits(1)
        self.ssa_spin.set_hexpand(True)
        props_grid.attach(self.ssa_spin, 1, 1, 1, 1)

        ssa_unit_label = Gtk.Label("m²/kg (optional)")
        ssa_unit_label.set_halign(Gtk.Align.START)
        props_grid.attach(ssa_unit_label, 2, 1, 1, 1)

        # PSD Data ID (for Phase 1, just a number entry - will improve later)
        psd_label = Gtk.Label("PSD Data ID:")
        psd_label.set_halign(Gtk.Align.END)
        props_grid.attach(psd_label, 0, 2, 1, 1)

        self.psd_spin = Gtk.SpinButton.new_with_range(1, 1000000, 1)
        self.psd_spin.set_value(1)
        self.psd_spin.set_digits(0)
        self.psd_spin.set_hexpand(True)
        props_grid.attach(self.psd_spin, 1, 2, 1, 1)

        psd_help_label = Gtk.Label("(required)")
        psd_help_label.set_halign(Gtk.Align.START)
        psd_help_label.get_style_context().add_class('dim-label')
        props_grid.attach(psd_help_label, 2, 2, 1, 1)

        props_frame.add(props_grid)
        form_box.pack_start(props_frame, False, False, 0)

        # Description field
        desc_frame = Gtk.Frame(label="Description (optional)")
        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        desc_box.set_margin_start(15)
        desc_box.set_margin_end(15)
        desc_box.set_margin_top(10)
        desc_box.set_margin_bottom(10)

        desc_scrolled = Gtk.ScrolledWindow()
        desc_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        desc_scrolled.set_size_request(-1, 100)

        self.desc_textview = Gtk.TextView()
        self.desc_textview.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_scrolled.add(self.desc_textview)

        desc_box.pack_start(desc_scrolled, True, True, 0)
        desc_frame.add(desc_box)
        form_box.pack_start(desc_frame, True, True, 0)

        # Phase 1 notice
        notice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        notice_box.set_margin_top(10)

        notice_icon = Gtk.Image.new_from_icon_name('dialog-information-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        notice_box.pack_start(notice_icon, False, False, 0)

        notice_label = Gtk.Label()
        notice_label.set_markup('<span size="small"><i>Phase composition editing will be available in Phase 2</i></span>')
        notice_label.set_halign(Gtk.Align.START)
        notice_label.set_line_wrap(True)
        notice_box.pack_start(notice_label, True, True, 0)

        form_box.pack_start(notice_box, False, False, 0)

        scrolled.add(form_box)
        content_area.pack_start(scrolled, True, True, 0)

        # Validation message area
        self.validation_label = Gtk.Label()
        self.validation_label.set_halign(Gtk.Align.START)
        self.validation_label.set_line_wrap(True)
        self.validation_label.set_no_show_all(True)
        content_area.pack_start(self.validation_label, False, False, 0)

        content_area.show_all()

    def _load_material_data(self) -> None:
        """Load material data into the form (edit mode)."""
        if not self.material_data:
            return

        self.name_entry.set_text(self.material_data.name or "")

        if self.material_data.tag_names:
            self.tag_input.set_tags(self.material_data.tag_names)

        if self.material_data.specific_gravity:
            self.sg_spin.set_value(self.material_data.specific_gravity)

        if self.material_data.specific_surface_area:
            self.ssa_spin.set_value(self.material_data.specific_surface_area)

        if self.material_data.psd_data_id:
            self.psd_spin.set_value(self.material_data.psd_data_id)

        if self.material_data.description:
            buffer = self.desc_textview.get_buffer()
            buffer.set_text(self.material_data.description)

    def _disable_editing(self) -> None:
        """Disable editing for immutable materials."""
        self.name_entry.set_sensitive(False)
        self.tag_input.set_sensitive(False)
        self.sg_spin.set_sensitive(False)
        self.ssa_spin.set_sensitive(False)
        self.psd_spin.set_sensitive(False)
        self.desc_textview.set_sensitive(False)
        self.save_button.set_sensitive(False)

        # Show warning
        warning_label = Gtk.Label()
        warning_label.set_markup('<span color="orange">⚠ This material is read-only and cannot be edited</span>')
        warning_label.set_halign(Gtk.Align.START)
        warning_label.show()
        self.get_content_area().pack_start(warning_label, False, False, 5)

    def _validate(self) -> tuple[bool, str]:
        """
        Validate the form.

        Returns:
            (is_valid, error_message)
        """
        # Check name
        name = self.name_entry.get_text().strip()
        if not name:
            return False, "Material name is required"

        # Check PSD data ID
        psd_id = int(self.psd_spin.get_value())
        if psd_id < 1:
            return False, "PSD Data ID must be at least 1"

        return True, ""

    def run(self) -> int:
        """
        Run the dialog and handle save.

        Returns:
            Response type
        """
        while True:
            response = super().run()

            if response != Gtk.ResponseType.OK:
                return response

            # Validate
            is_valid, error_msg = self._validate()
            if not is_valid:
                self.validation_label.set_markup(f'<span color="red">Error: {error_msg}</span>')
                self.validation_label.show()
                continue

            # Try to save
            success, error_msg = self._save_material()
            if success:
                return response
            else:
                self.validation_label.set_markup(f'<span color="red">Save failed: {error_msg}</span>')
                self.validation_label.show()

    def _save_material(self) -> tuple[bool, str]:
        """
        Save the material.

        Returns:
            (success, error_message)
        """
        if not self.material_service:
            return False, "Material service not available"

        try:
            # Get form data
            name = self.name_entry.get_text().strip()
            tags = self.tag_input.get_tags()
            sg = self.sg_spin.get_value()
            ssa = self.ssa_spin.get_value()
            psd_id = int(self.psd_spin.get_value())

            buffer = self.desc_textview.get_buffer()
            description = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

            if self.is_edit_mode:
                # Update existing material
                update_data = MaterialUpdate(
                    name=name,
                    tags=tags,
                    specific_gravity=sg,
                    specific_surface_area=ssa if ssa > 0 else None,
                    psd_data_id=psd_id,
                    description=description if description else None
                )

                self.material_service.update(self.material_data.id, update_data)
                self.logger.info(f"Updated material: {name}")
            else:
                # Create new material
                create_data = MaterialCreate(
                    name=name,
                    tags=tags,
                    specific_gravity=sg,
                    specific_surface_area=ssa if ssa > 0 else None,
                    psd_data_id=psd_id,
                    description=description if description else None,
                    immutable=False
                )

                material = self.material_service.create(create_data)
                self.logger.info(f"Created material: {material.name} (ID: {material.id})")

            return True, ""

        except Exception as e:
            self.logger.error(f"Failed to save material: {e}")
            return False, str(e)

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
from app.services.psd_data_service import PSDDataService
from app.services.microstructure_service import MicrostructureService
from app.models import MaterialCreate, MaterialUpdate, PSDDataCreate
from app.widgets.phase_composition_editor import PhaseCompositionEditor
from app.widgets.unified_psd_widget import UnifiedPSDWidget


class MaterialDialog(Gtk.Dialog):
    """Simple dialog for creating/editing THAMES materials."""

    def __init__(self, parent, material_service: MaterialService, mode='create', material=None,
                 microstructure_service=None):
        """
        Initialize material dialog.

        Args:
            parent: Parent window
            material_service: MaterialService instance
            mode: 'create' or 'edit'
            material: Material object (for edit mode)
            microstructure_service: MicrostructureService instance (optional, for shape sets)
        """
        # Check if material is immutable (read-only)
        self.is_immutable = material.immutable if (material and hasattr(material, 'immutable')) else False

        if self.is_immutable:
            title = f"View Material: {material.name if material else ''} (Read-only)"
        else:
            title = "Add Material" if mode == 'create' else f"Edit Material: {material.name if material else ''}"

        super().__init__(title=title, transient_for=parent, flags=0)

        self.material_service = material_service
        self.psd_data_service = PSDDataService(material_service.db_service)
        # Use provided microstructure_service or create a fallback one
        self.microstructure_service = microstructure_service or MicrostructureService(material_service.db_service)
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
        content_area = self.get_content_area()

        # Create scrolled window for the form
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(400)
        scrolled.set_max_content_height(600)

        # Create box to hold all form fields
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_left(20)
        content.set_margin_right(20)

        scrolled.add(content)
        content_area.pack_start(scrolled, True, True, 0)

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

        # PSD Widget (UnifiedPSDWidget) - in collapsible expander
        psd_expander = Gtk.Expander(label="Particle Size Distribution")
        psd_expander.set_expanded(False)  # Collapsed by default to save space
        self.psd_widget = UnifiedPSDWidget('generic')
        self.psd_widget.set_change_callback(self._on_psd_changed)
        psd_expander.add(self.psd_widget)
        content.pack_start(psd_expander, False, False, 0)

        # Particle Shape Section
        shape_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        shape_label = Gtk.Label(label="Particle Shape:")
        shape_label.set_width_chars(20)
        shape_label.set_halign(Gtk.Align.START)

        self.shape_combo = Gtk.ComboBoxText()
        # Add "Spheres" as default option
        self.shape_combo.append("sphere", "Spheres")
        # Add available real-shape sets from microstructure service
        shape_sets = self.microstructure_service.get_supported_shape_sets()
        for shape_id, shape_desc in shape_sets.items():
            if shape_id.lower() not in ('sphere', 'spherical'):
                self.shape_combo.append(shape_id, f"Real Shapes: {shape_desc}")
        self.shape_combo.set_active(0)  # Default to spheres
        self.shape_combo.set_tooltip_text(
            "Select particle shape for microstructure generation.\n"
            "Spheres: Particles are spherical (fastest computation).\n"
            "Real Shapes: Uses spherical harmonic coefficients from shape database."
        )

        shape_box.pack_start(shape_label, False, False, 0)
        shape_box.pack_start(self.shape_combo, True, True, 0)
        content.pack_start(shape_box, False, False, 0)

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

        # Clinker Source field (hidden by default, shown for cement materials)
        self.clinker_source_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.clinker_source_box.set_margin_top(5)
        clinker_source_label = Gtk.Label(label="Clinker Source:")
        clinker_source_label.set_width_chars(15)
        clinker_source_label.set_halign(Gtk.Align.END)

        self.clinker_source_entry = Gtk.Entry()
        self.clinker_source_entry.set_editable(False)
        self.clinker_source_entry.set_can_focus(False)
        self.clinker_source_entry.set_placeholder_text("(not derived from clinker)")
        self.clinker_source_entry.get_style_context().add_class("read-only")

        self.clinker_source_box.pack_start(clinker_source_label, False, False, 0)
        self.clinker_source_box.pack_start(self.clinker_source_entry, True, True, 0)
        content.pack_start(self.clinker_source_box, False, False, 0)
        self.clinker_source_box.set_no_show_all(True)  # Hide by default

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

        # Correlation Functions Section (hidden by default, shown for clinker)
        self.correlation_frame = Gtk.Frame(label="Correlation Functions")
        correlation_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        correlation_box.set_margin_top(10)
        correlation_box.set_margin_bottom(10)
        correlation_box.set_margin_left(15)
        correlation_box.set_margin_right(15)

        # Info label
        info_label = Gtk.Label()
        info_label.set_markup("<small>Import correlation function files for two-point statistics</small>")
        info_label.set_halign(Gtk.Align.START)
        correlation_box.pack_start(info_label, False, False, 0)

        # Grid for correlation file browsers
        corr_grid = Gtk.Grid()
        corr_grid.set_row_spacing(6)
        corr_grid.set_column_spacing(8)
        corr_grid.set_margin_top(5)

        # Define correlation types
        self.correlation_types = [
            ('sil', 'SIL (Silicate)'),
            ('c3s', 'C3S (Alite)'),
            ('alu', 'ALU (Aluminate)'),
            ('c3a', 'C3A (Aluminate C3A)'),
            ('c4af', 'C4AF (Ferrite)'),
            ('k2o', 'K2O (Potassium)'),
            ('n2o', 'N2O (Sodium)')
        ]

        self.correlation_entries = {}
        self.correlation_status_labels = {}
        self.correlation_file_paths = {}  # Store loaded file paths

        for i, (key, label_text) in enumerate(self.correlation_types):
            # Label
            label = Gtk.Label(label=f"{label_text}:")
            label.set_halign(Gtk.Align.END)
            label.set_width_chars(20)
            corr_grid.attach(label, 0, i, 1, 1)

            # Entry showing file path or status
            entry = Gtk.Entry()
            entry.set_text("Not loaded")
            entry.set_editable(False)
            entry.set_width_chars(30)
            self.correlation_entries[key] = entry
            corr_grid.attach(entry, 1, i, 1, 1)

            # Browse button
            browse_btn = Gtk.Button(label="Browse...")
            browse_btn.connect('clicked', self._on_browse_correlation_clicked, key)
            corr_grid.attach(browse_btn, 2, i, 1, 1)

            # Status indicator
            status_label = Gtk.Label()
            status_label.set_markup('<span foreground="gray">○</span>')
            status_label.set_width_chars(2)
            self.correlation_status_labels[key] = status_label
            corr_grid.attach(status_label, 3, i, 1, 1)

            # Initialize file path storage
            self.correlation_file_paths[key] = None

        correlation_box.pack_start(corr_grid, False, False, 0)
        self.correlation_frame.add(correlation_box)
        content.pack_start(self.correlation_frame, False, False, 0)
        self.correlation_frame.set_no_show_all(True)  # Hide by default

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

        # Track last directory used for correlation files
        self.last_correlation_directory = None

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

        # Load PSD data into widget
        if material.psd_data:
            psd_dict = {
                'psd_mode': material.psd_data.psd_mode,
                'psd_d50': material.psd_data.psd_d50,
                'psd_n': material.psd_data.psd_n,
                'psd_dmax': material.psd_data.psd_dmax,
                'psd_median': material.psd_data.psd_median,
                'psd_spread': material.psd_data.psd_spread,
                'psd_exponent': material.psd_data.psd_exponent,
                'psd_custom_points': material.psd_data.psd_custom_points
            }
            self.psd_widget.load_from_material_data(psd_dict)

        # Load particle shape settings
        shape_type = getattr(material, 'particle_shape_type', 0) or 0
        shape_set = getattr(material, 'particle_shape_set', None)
        if shape_type == 1 and shape_set:
            # Real shapes - try to select the shape set in dropdown
            self.shape_combo.set_active_id(shape_set)
            if self.shape_combo.get_active_id() != shape_set:
                # Shape set not found in dropdown, add it
                self.shape_combo.append(shape_set, f"Real Shapes: {shape_set}")
                self.shape_combo.set_active_id(shape_set)
        else:
            # Spheres
            self.shape_combo.set_active_id("sphere")

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

        # Show clinker source if material has one
        if material.has_clinker and material.clinker_source_id:
            clinker = self.material_service.get_by_id(material.clinker_source_id)
            if clinker:
                self.clinker_source_entry.set_text(clinker.name)
                self.clinker_source_box.set_no_show_all(False)
                self.clinker_source_box.show_all()

                # Restore clinker tracking in phase editor
                clinker_phase_names = [p.gem_phase_name for p in clinker.phases]
                self.phase_editor.set_clinker_source(
                    clinker_material_id=clinker.id,
                    clinker_material_name=clinker.name,
                    clinker_phase_names=clinker_phase_names
                )
                self.logger.info(f"Restored clinker tracking for material: {clinker.name}")

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

            # Load correlation functions
            for corr_key in self.correlation_file_paths.keys():
                correlation_data = self.material_service.get_clinker_correlation(material.id, corr_key)
                if correlation_data:
                    # Store the data
                    self.correlation_file_paths[corr_key] = correlation_data
                    # Update UI
                    size_kb = len(correlation_data) / 1024
                    self.correlation_entries[corr_key].set_text(f"Loaded ({size_kb:.1f} KB)")
                    self.correlation_status_labels[corr_key].set_markup(
                        f'<span foreground="green">✓</span>'
                    )
                    self.logger.info(f"Loaded {corr_key} correlation from database ({len(correlation_data)} bytes)")
        else:
            self.type_combo.set_active_id("simple")

    def _on_sg_calculated(self, widget, sg_value):
        """Handle sg-calculated signal from phase editor."""
        self.sg_spinner.set_value(sg_value)
        self.logger.info(f"Updated SG field to calculated value: {sg_value:.3f}")

    def _on_psd_changed(self):
        """Handle PSD data changes from the PSD widget."""
        # PSD data will be saved when the material is saved
        self.logger.debug("PSD data changed")

    def _on_clinker_source_added(self, widget, clinker_material_id):
        """Handle clinker-source-added signal from phase editor."""
        self.clinker_source_id = clinker_material_id
        clinker = self.material_service.get_by_id(clinker_material_id)
        clinker_name = clinker.name if clinker else f"ID {clinker_material_id}"

        # Update clinker source display
        self.clinker_source_entry.set_text(clinker_name)
        self.clinker_source_box.set_no_show_all(False)
        self.clinker_source_box.show_all()

        self.logger.info(f"Clinker source set: {clinker_name} (id={clinker_material_id})")

    def _on_material_type_changed(self, combo):
        """Handle material type selection change."""
        material_type = combo.get_active_id()

        # Show/hide relevant sections
        if material_type == "clinker":
            self.clinker_frame.set_no_show_all(False)
            self.clinker_frame.show_all()
            self.correlation_frame.set_no_show_all(False)
            self.correlation_frame.show_all()
        else:  # simple
            self.clinker_frame.hide()
            self.correlation_frame.hide()

    def _on_clinker_fraction_changed(self, spinner):
        """Update total when clinker fraction changes."""
        total = sum(s.get_value() for s in self.clinker_spinners.values())
        self.clinker_total_label.set_text(f"{total:.4f}")

        # Color code: green if valid (~1.0), red if not
        if abs(total - 1.0) <= 0.01:
            self.clinker_total_label.set_markup(f'<span foreground="green">{total:.4f}</span>')
        else:
            self.clinker_total_label.set_markup(f'<span foreground="red">{total:.4f}</span>')

    def _on_browse_correlation_clicked(self, button, correlation_key):
        """Handle browse button click for correlation function."""
        dialog = Gtk.FileChooserDialog(
            title=f"Select {correlation_key.upper()} Correlation File",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Open", Gtk.ResponseType.OK)

        # Set current folder to last used directory if available
        if self.last_correlation_directory:
            dialog.set_current_folder(self.last_correlation_directory)

        # Add file filter
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Correlation files (*.dat, *.txt, *.*)")
        filter_text.add_pattern("*.dat")
        filter_text.add_pattern("*.txt")
        filter_text.add_pattern(f"*.{correlation_key}")
        filter_text.add_pattern("*")
        dialog.add_filter(filter_text)

        response = dialog.run()
        file_path = None
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()

        dialog.destroy()

        if file_path:
            try:
                # Read and validate correlation file
                with open(file_path, 'rb') as f:
                    correlation_data = f.read()

                # Basic validation - check if it's not empty
                if not correlation_data:
                    self._show_error("Correlation file is empty")
                    return

                # Store the data
                self.correlation_file_paths[correlation_key] = correlation_data

                # Remember the directory for next time
                import os
                file_directory = os.path.dirname(file_path)
                self.last_correlation_directory = file_directory
                self.logger.info(f"Remembered directory for future file selections: {file_directory}")

                # Update UI
                filename = os.path.basename(file_path)
                self.correlation_entries[correlation_key].set_text(filename)
                self.correlation_status_labels[correlation_key].set_markup(
                    f'<span foreground="green">✓</span>'
                )

                self.logger.info(f"Loaded {correlation_key} correlation: {filename} ({len(correlation_data)} bytes)")

            except Exception as e:
                self.logger.error(f"Error loading correlation file: {e}")
                self._show_error(f"Error loading correlation file: {str(e)}")

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
        self.psd_widget.set_sensitive(False)
        self.shape_combo.set_sensitive(False)
        self.type_combo.set_sensitive(False)
        self.desc_textview.set_editable(False)
        self.desc_textview.set_cursor_visible(False)

        # Disable clinker spinners
        for spinner in self.clinker_spinners.values():
            spinner.set_sensitive(False)

        # Disable correlation browse buttons (they're inside the correlation_frame)
        # Find all browse buttons in the correlation frame and disable them
        def disable_buttons(widget):
            if isinstance(widget, Gtk.Button):
                widget.set_sensitive(False)
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    disable_buttons(child)
        disable_buttons(self.correlation_frame)

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
            material_type = self.type_combo.get_active_id()

            # Save PSD data and get ID
            psd_dict = self.psd_widget.get_material_data_dict()
            psd_create = PSDDataCreate(**psd_dict)
            psd_response = self.psd_data_service.create_psd_data(psd_create)
            if not psd_response:
                self._show_error("Failed to save PSD data")
                return False
            psd_id = psd_response.id

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

            # Get particle shape settings
            shape_selection = self.shape_combo.get_active_id() or "sphere"
            if shape_selection.lower() in ('sphere', 'spherical'):
                particle_shape_type = 0  # SPHERES
                particle_shape_set = None
            else:
                particle_shape_type = 1  # REALSHAPE
                particle_shape_set = shape_selection

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
                        is_clinker=True,
                        particle_shape_type=particle_shape_type,
                        particle_shape_set=particle_shape_set
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

                    # Save correlation functions
                    for corr_key, corr_data in self.correlation_file_paths.items():
                        if corr_data:
                            self.material_service.set_clinker_correlation(
                                created_material.id, corr_key, corr_data
                            )
                            self.logger.info(f"Saved {corr_key} correlation ({len(corr_data)} bytes)")

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
                        clinker_source_id=self.clinker_source_id,
                        particle_shape_type=particle_shape_type,
                        particle_shape_set=particle_shape_set
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
                    clinker_source_id=self.clinker_source_id,
                    particle_shape_type=particle_shape_type,
                    particle_shape_set=particle_shape_set
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

                # Update clinker surface fractions and correlations
                if material_type == "clinker":
                    surface_fractions = {
                        key: spinner.get_value()
                        for key, spinner in self.clinker_spinners.items()
                    }
                    self.material_service.set_clinker_surface_fractions(
                        self.material.id, surface_fractions
                    )

                    # Update correlation functions
                    for corr_key, corr_data in self.correlation_file_paths.items():
                        if corr_data:
                            self.material_service.set_clinker_correlation(
                                self.material.id, corr_key, corr_data
                            )
                            self.logger.info(f"Updated {corr_key} correlation ({len(corr_data)} bytes)")

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

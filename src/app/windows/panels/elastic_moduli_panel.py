#!/usr/bin/env python3
"""
Elastic Moduli Panel for VCCTL

Provides interface for configuring and running elastic moduli calculations on hydrated microstructures.
This is the third stage in the VCCTL workflow: Microstructure → Hydration → Elastic Moduli
"""

import gi
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any, List

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Pango

if TYPE_CHECKING:
    from app.windows.main_window import VCCTLMainWindow

from app.services.service_container import get_service_container
from app.services.elastic_moduli_service import ElasticModuliService
from app.services.elastic_lineage_service import HydratedMicrostructure
from app.models.elastic_moduli_operation import ElasticModuliOperation
from app.models.operation import Operation, OperationStatus, OperationType
from app.utils.icon_utils import create_button_with_icon
from app.help.panel_help_button import create_panel_help_button


class ElasticModuliPanel(Gtk.Box):
    """Main panel for elastic moduli calculations.

    Supports two backends:
    - THAMES: Uses thames executable with -s 5 for elastic calculation on paste microstructures
    - VCCTL: Uses elastic.c for multi-scale concrete (with aggregates/ITZ via concelas)

    Currently THAMES is the default. THAMES will eventually support concelas for
    multi-scale concrete once the AppliedStrain class is extended.
    """

    def __init__(self, main_window: "VCCTLMainWindow"):
        """Initialize the elastic moduli panel."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.main_window = main_window
        self.logger = logging.getLogger("VCCTL.ElasticModuliPanel")
        self.service_container = get_service_container()
        self.elastic_moduli_service = ElasticModuliService(self.service_container)

        # Panel state
        self.current_operation = None
        self.available_hydration_operations = []
        self.available_microstructures = []  # Phase 2: Hydrated microstructures list
        self.resolved_lineage = None  # Phase 2: Cached lineage data

        # Backend mode detection
        self.thames_mode = self._is_thames_mode()
        self.backend_info_label = None

        # UI components
        self.hydration_combo = None
        self.microstructure_combo = None  # Phase 2: Microstructure time selection
        self.lineage_info_label = None  # Phase 2: Lineage information display
        self.operation_name_entry = None
        self.image_filename_entry = None
        self.output_dir_entry = None
        self.pimg_file_entry = None
        self.has_itz_check = None
        self.air_volume_spin = None

        # Fine aggregate controls
        self.fine_agg_check = None
        self.fine_volume_spin = None
        self.fine_grading_entry = None
        self.fine_bulk_spin = None
        self.fine_shear_spin = None

        # Coarse aggregate controls
        self.coarse_agg_check = None
        self.coarse_volume_spin = None
        self.coarse_grading_entry = None
        self.coarse_bulk_spin = None
        self.coarse_shear_spin = None

        # Setup UI
        self._setup_ui()

        # Load initial data
        self._load_available_hydration_operations()

        self.logger.info("Elastic Moduli panel initialized")

    def _setup_ui(self) -> None:
        """Setup the main UI components."""
        # Create header
        self._create_header()

        # Create main content area with scrolling
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(400)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content_box.set_margin_top(15)
        content_box.set_margin_bottom(15)
        content_box.set_margin_left(20)
        content_box.set_margin_right(20)

        # Create input sections
        self._create_operation_settings(content_box)
        self._create_microstructure_settings(content_box)
        self._create_aggregate_settings(content_box)
        self._create_air_settings(content_box)
        self._create_action_buttons(content_box)

        scrolled.add(content_box)
        self.pack_start(scrolled, True, True, 0)

    def _create_header(self) -> None:
        """Create the panel header."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        header_box.set_margin_top(15)
        header_box.set_margin_bottom(10)
        header_box.set_margin_left(20)
        header_box.set_margin_right(20)

        # Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_label = Gtk.Label()
        title_label.set_markup(
            '<span size="large" weight="bold">Elastic Moduli Calculations</span>'
        )
        title_label.set_halign(Gtk.Align.START)
        title_box.pack_start(title_label, False, False, 0)

        # Add context-specific help button
        help_button = create_panel_help_button("ElasticModuliPanel", self.main_window)
        title_box.pack_start(help_button, False, False, 5)

        header_box.pack_start(title_box, False, False, 0)

        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            '<span size="small">Calculate mechanical properties from hydrated microstructures</span>'
        )
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_line_wrap(True)
        header_box.pack_start(desc_label, False, False, 0)

        # Backend mode info box
        self._create_backend_info_box(header_box)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 5)

        self.pack_start(header_box, False, False, 0)

    def _create_backend_info_box(self, parent: Gtk.Box) -> None:
        """Create the backend mode information box."""
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        info_box.set_margin_top(5)

        # Backend mode indicator
        if self.thames_mode:
            backend_text = (
                '<span size="small" foreground="#2E7D32">● Backend: <b>THAMES</b></span>'
            )
            info_text = (
                '<span size="small" style="italic">'
                'FEM calculation on paste microstructures. '
                'Aggregate/ITZ support coming with concelas integration.'
                '</span>'
            )
        else:
            backend_text = (
                '<span size="small" foreground="#1565C0">● Backend: <b>VCCTL</b></span>'
            )
            info_text = (
                '<span size="small" style="italic">'
                'Multi-scale concrete with aggregate grading and ITZ.'
                '</span>'
            )

        backend_label = Gtk.Label()
        backend_label.set_markup(backend_text)
        backend_label.set_halign(Gtk.Align.START)
        info_box.pack_start(backend_label, False, False, 0)

        self.backend_info_label = Gtk.Label()
        self.backend_info_label.set_markup(info_text)
        self.backend_info_label.set_halign(Gtk.Align.START)
        self.backend_info_label.set_line_wrap(True)
        info_box.pack_start(self.backend_info_label, True, True, 0)

        parent.pack_start(info_box, False, False, 0)

    def _create_operation_settings(self, parent: Gtk.Box) -> None:
        """Create operation configuration section."""
        frame = Gtk.Frame(label="Operation Settings")
        frame.set_label_align(0.02, 0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(15)
        grid.set_margin_top(15)
        grid.set_margin_bottom(15)
        grid.set_margin_left(15)
        grid.set_margin_right(15)

        row = 0

        # Hydration operation selection
        label = Gtk.Label("Source Hydration Operation:")
        label.set_halign(Gtk.Align.START)
        label.set_tooltip_text(
            "Select the completed hydration operation to use as input"
        )
        grid.attach(label, 0, row, 1, 1)

        # Hydration combo with refresh button in a horizontal box
        hydration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.hydration_combo = Gtk.ComboBoxText()
        self.hydration_combo.set_tooltip_text(
            "Choose from completed hydration operations"
        )
        self.hydration_combo.connect("changed", self._on_hydration_selection_changed)
        self.hydration_combo.set_hexpand(True)
        hydration_box.pack_start(self.hydration_combo, True, True, 0)

        # Add refresh button
        refresh_button = create_button_with_icon("", "refresh", 16)
        refresh_button.set_tooltip_text("Refresh list of hydration operations")
        refresh_button.connect("clicked", self._on_refresh_hydration_operations)
        hydration_box.pack_start(refresh_button, False, False, 0)

        grid.attach(hydration_box, 1, row, 2, 1)

        row += 1

        # Microstructure time selection (Phase 2)
        label = Gtk.Label("Hydrated Microstructure:")
        label.set_halign(Gtk.Align.START)
        label.set_tooltip_text("Select which hydrated microstructure time step to use")
        grid.attach(label, 0, row, 1, 1)

        self.microstructure_combo = Gtk.ComboBoxText()
        self.microstructure_combo.set_tooltip_text(
            "Choose from available hydrated microstructures (final or intermediate times)"
        )
        self.microstructure_combo.connect(
            "changed", self._on_microstructure_selection_changed
        )
        self.microstructure_combo.set_sensitive(
            False
        )  # Initially disabled until hydration selected
        grid.attach(self.microstructure_combo, 1, row, 2, 1)

        row += 1

        # Lineage information display (Phase 2)
        self.lineage_info_label = Gtk.Label()
        self.lineage_info_label.set_markup(
            '<span size="small" style="italic">Select hydration operation to see lineage chain</span>'
        )
        self.lineage_info_label.set_halign(Gtk.Align.START)
        self.lineage_info_label.set_line_wrap(True)
        self.lineage_info_label.set_max_width_chars(80)
        grid.attach(self.lineage_info_label, 0, row, 3, 1)

        row += 1

        # Auto-generated operation name (read-only display)
        label = Gtk.Label("Operation Name:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        self.operation_name_entry = Gtk.Entry()
        self.operation_name_entry.set_placeholder_text(
            "← Select a microstructure above"
        )
        self.operation_name_entry.set_tooltip_text(
            "Auto-generated as: Elastic-{HydrationName}-{TimeStep}\n"
            "Will be populated when you select a hydrated microstructure."
        )
        self.operation_name_entry.set_sensitive(False)  # Make read-only
        grid.attach(self.operation_name_entry, 1, row, 2, 1)

        frame.add(grid)
        parent.pack_start(frame, False, False, 0)

    def _create_microstructure_settings(self, parent: Gtk.Box) -> None:
        """Create microstructure file settings section (collapsible)."""
        # Use Expander for collapsible section - collapsed by default since fields are auto-populated
        expander = Gtk.Expander(label="Microstructure Settings (auto-populated)")
        expander.set_expanded(False)  # Collapsed by default
        expander.set_margin_top(10)
        expander.set_margin_bottom(5)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_left(15)
        main_box.set_margin_right(15)

        # Info message
        info_label = Gtk.Label()
        info_label.set_markup(
            '<span size="small" foreground="#1976D2">'
            'ℹ These fields are auto-populated when you select a hydrated microstructure above.'
            '</span>'
        )
        info_label.set_halign(Gtk.Align.START)
        info_label.set_line_wrap(True)
        main_box.pack_start(info_label, False, False, 0)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(15)

        row = 0

        # Image filename
        label = Gtk.Label("Image Filename:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        self.image_filename_entry = Gtk.Entry()
        self.image_filename_entry.set_placeholder_text("Auto-populated from selection")
        self.image_filename_entry.set_tooltip_text("Hydrated microstructure image file (auto-populated)")
        self.image_filename_entry.set_sensitive(False)  # Read-only - auto-populated
        grid.attach(self.image_filename_entry, 1, row, 2, 1)

        row += 1

        # Output directory
        label = Gtk.Label("Output Directory:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.output_dir_entry = Gtk.Entry()
        self.output_dir_entry.set_placeholder_text("Auto-populated from selection")
        self.output_dir_entry.set_sensitive(False)  # Read-only - auto-populated
        dir_box.pack_start(self.output_dir_entry, True, True, 0)

        self.browse_output_button = Gtk.Button("Browse...")
        self.browse_output_button.connect("clicked", self._on_browse_output_dir)
        self.browse_output_button.set_sensitive(False)  # Disabled - auto-populated
        dir_box.pack_start(self.browse_output_button, False, False, 0)

        grid.attach(dir_box, 1, row, 2, 1)

        row += 1

        # Pimg file path - auto-populated from lineage
        label = Gtk.Label("Pimg File Path:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        pimg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.pimg_file_entry = Gtk.Entry()
        self.pimg_file_entry.set_placeholder_text("Auto-populated from microstructure lineage")
        self.pimg_file_entry.set_tooltip_text("Phase ID mapping file (.pimg) from original microstructure")
        self.pimg_file_entry.set_sensitive(False)  # Read-only - auto-populated
        pimg_box.pack_start(self.pimg_file_entry, True, True, 0)

        self.browse_pimg_button = Gtk.Button("Browse...")
        self.browse_pimg_button.connect("clicked", self._on_browse_pimg_file)
        self.browse_pimg_button.set_sensitive(False)  # Disabled - auto-populated
        pimg_box.pack_start(self.browse_pimg_button, False, False, 0)

        grid.attach(pimg_box, 1, row, 2, 1)

        row += 1

        # ITZ flag (only relevant in VCCTL mode with aggregates)
        self.has_itz_check = Gtk.CheckButton(
            "Include ITZ (Interfacial Transition Zone)"
        )
        self.has_itz_check.set_tooltip_text(
            "Include ITZ calculations for aggregate interfaces"
        )
        if self.thames_mode:
            self.has_itz_check.set_active(False)
            self.has_itz_check.set_sensitive(False)
            self.has_itz_check.set_visible(False)  # Hide in THAMES mode
        grid.attach(self.has_itz_check, 0, row, 3, 1)

        main_box.pack_start(grid, False, False, 0)
        expander.add(main_box)
        parent.pack_start(expander, False, False, 0)

    def _create_aggregate_settings(self, parent: Gtk.Box) -> None:
        """Create aggregate properties section."""
        frame = Gtk.Frame(label="Aggregate Properties")
        frame.set_label_align(0.02, 0.5)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        main_box.set_margin_top(15)
        main_box.set_margin_bottom(15)
        main_box.set_margin_left(15)
        main_box.set_margin_right(15)

        # THAMES mode notice - aggregate support requires concelas integration
        if self.thames_mode:
            notice_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            notice_box.set_margin_bottom(10)

            notice_label = Gtk.Label()
            notice_label.set_markup(
                '<span size="small" foreground="#F57C00">'
                '⚠ Aggregate support not yet available in THAMES mode. '
                'These settings will be enabled after concelas integration.'
                '</span>'
            )
            notice_label.set_halign(Gtk.Align.START)
            notice_label.set_line_wrap(True)
            notice_box.pack_start(notice_label, True, True, 0)

            main_box.pack_start(notice_box, False, False, 0)

        # Fine aggregate section
        fine_frame = Gtk.Frame(label="Fine Aggregate")
        fine_frame.set_label_align(0.02, 0.5)
        fine_grid = self._create_aggregate_grid("fine")
        fine_frame.add(fine_grid)
        main_box.pack_start(fine_frame, False, False, 0)

        # Coarse aggregate section
        coarse_frame = Gtk.Frame(label="Coarse Aggregate")
        coarse_frame.set_label_align(0.02, 0.5)
        coarse_grid = self._create_aggregate_grid("coarse")
        coarse_frame.add(coarse_grid)
        main_box.pack_start(coarse_frame, False, False, 0)

        frame.add(main_box)
        parent.pack_start(frame, False, False, 0)

        # Disable aggregate controls in THAMES mode
        if self.thames_mode:
            self._disable_aggregate_settings()

    def _create_aggregate_grid(self, agg_type: str) -> Gtk.Grid:
        """Create aggregate property grid for fine or coarse aggregate."""
        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(15)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_left(10)
        grid.set_margin_right(10)

        row = 0

        # Enable checkbox
        if agg_type == "fine":
            self.fine_agg_check = Gtk.CheckButton(f"Include {agg_type} aggregate")
            self.fine_agg_check.connect("toggled", self._on_fine_aggregate_toggled)
            check_widget = self.fine_agg_check
        else:
            self.coarse_agg_check = Gtk.CheckButton(f"Include {agg_type} aggregate")
            self.coarse_agg_check.connect("toggled", self._on_coarse_aggregate_toggled)
            check_widget = self.coarse_agg_check

        grid.attach(check_widget, 0, row, 3, 1)
        row += 1

        # Aggregate source label
        if agg_type == "fine":
            self.fine_agg_source_label = Gtk.Label()
            self.fine_agg_source_label.set_markup(
                '<span size="small" style="italic">Source: Not specified</span>'
            )
            self.fine_agg_source_label.set_halign(Gtk.Align.START)
            grid.attach(self.fine_agg_source_label, 0, row, 3, 1)
        else:
            self.coarse_agg_source_label = Gtk.Label()
            self.coarse_agg_source_label.set_markup(
                '<span size="small" style="italic">Source: Not specified</span>'
            )
            self.coarse_agg_source_label.set_halign(Gtk.Align.START)
            grid.attach(self.coarse_agg_source_label, 0, row, 3, 1)
        row += 1

        # Volume fraction
        label = Gtk.Label("Volume Fraction:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        if agg_type == "fine":
            self.fine_volume_spin = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.01)
            self.fine_volume_spin.set_digits(3)
            self.fine_volume_spin.set_value(0.0)
            self.fine_volume_spin.set_tooltip_text(
                "Volume fraction of fine aggregate (0.0-1.0)"
            )
            spin_widget = self.fine_volume_spin
        else:
            self.coarse_volume_spin = Gtk.SpinButton.new_with_range(0.0, 1.0, 0.01)
            self.coarse_volume_spin.set_digits(3)
            self.coarse_volume_spin.set_value(0.0)
            self.coarse_volume_spin.set_tooltip_text(
                "Volume fraction of coarse aggregate (0.0-1.0)"
            )
            spin_widget = self.coarse_volume_spin

        grid.attach(spin_widget, 1, row, 2, 1)
        row += 1

        # Grading information
        label = Gtk.Label("Grading:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        grading_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        # Path entry (auto-populated, but editable for advanced users)
        grading_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        if agg_type == "fine":
            self.fine_grading_entry = Gtk.Entry()
            self.fine_grading_entry.set_placeholder_text(
                "Auto-populated from mix design"
            )
            grading_hbox.pack_start(self.fine_grading_entry, True, True, 0)
            entry_widget = self.fine_grading_entry

            # Status label for fine aggregate
            self.fine_grading_status_label = Gtk.Label()
            self.fine_grading_status_label.set_markup(
                '<span size="small" style="italic">Auto-populated from database template</span>'
            )
            self.fine_grading_status_label.set_halign(Gtk.Align.START)
            status_label = self.fine_grading_status_label
        else:
            self.coarse_grading_entry = Gtk.Entry()
            self.coarse_grading_entry.set_placeholder_text(
                "Auto-populated from mix design"
            )
            grading_hbox.pack_start(self.coarse_grading_entry, True, True, 0)
            entry_widget = self.coarse_grading_entry

            # Status label for coarse aggregate
            self.coarse_grading_status_label = Gtk.Label()
            self.coarse_grading_status_label.set_markup(
                '<span size="small" style="italic">Auto-populated from database template</span>'
            )
            self.coarse_grading_status_label.set_halign(Gtk.Align.START)
            status_label = self.coarse_grading_status_label

        browse_button = Gtk.Button("Browse...")
        browse_button.connect("clicked", self._on_browse_grading_file, agg_type)
        browse_button.set_tooltip_text("Optional: Override with custom grading file")
        grading_hbox.pack_start(browse_button, False, False, 0)

        grading_vbox.pack_start(grading_hbox, False, False, 0)
        grading_vbox.pack_start(status_label, False, False, 0)

        grid.attach(grading_vbox, 1, row, 2, 1)
        row += 1

        # Bulk modulus
        label = Gtk.Label("Bulk Modulus (GPa):")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        if agg_type == "fine":
            self.fine_bulk_spin = Gtk.SpinButton.new_with_range(0.0, 1000.0, 0.1)
            self.fine_bulk_spin.set_digits(2)
            self.fine_bulk_spin.set_value(37.0)  # Typical quartz value
            self.fine_bulk_spin.set_tooltip_text(
                "Bulk modulus in GPa (typical: quartz ~37)"
            )
            spin_widget = self.fine_bulk_spin
        else:
            self.coarse_bulk_spin = Gtk.SpinButton.new_with_range(0.0, 1000.0, 0.1)
            self.coarse_bulk_spin.set_digits(2)
            self.coarse_bulk_spin.set_value(37.0)
            self.coarse_bulk_spin.set_tooltip_text(
                "Bulk modulus in GPa (typical: quartz ~37)"
            )
            spin_widget = self.coarse_bulk_spin

        grid.attach(spin_widget, 1, row, 2, 1)
        row += 1

        # Shear modulus
        label = Gtk.Label("Shear Modulus (GPa):")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, row, 1, 1)

        if agg_type == "fine":
            self.fine_shear_spin = Gtk.SpinButton.new_with_range(0.0, 1000.0, 0.1)
            self.fine_shear_spin.set_digits(2)
            self.fine_shear_spin.set_value(44.0)  # Typical quartz value
            self.fine_shear_spin.set_tooltip_text(
                "Shear modulus in GPa (typical: quartz ~44)"
            )
            spin_widget = self.fine_shear_spin
        else:
            self.coarse_shear_spin = Gtk.SpinButton.new_with_range(0.0, 1000.0, 0.1)
            self.coarse_shear_spin.set_digits(2)
            self.coarse_shear_spin.set_value(44.0)
            self.coarse_shear_spin.set_tooltip_text(
                "Shear modulus in GPa (typical: quartz ~44)"
            )
            spin_widget = self.coarse_shear_spin

        grid.attach(spin_widget, 1, row, 2, 1)

        # Initially disable all controls except checkbox
        self._set_aggregate_controls_sensitive(agg_type, False)

        return grid

    def _create_air_settings(self, parent: Gtk.Box) -> None:
        """Create air content settings section."""
        frame = Gtk.Frame(label="Air Content")
        frame.set_label_align(0.02, 0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(15)
        grid.set_margin_top(15)
        grid.set_margin_bottom(15)
        grid.set_margin_left(15)
        grid.set_margin_right(15)

        # Air volume fraction
        label = Gtk.Label("Air Volume Fraction:")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 0, 1, 1)

        self.air_volume_spin = Gtk.SpinButton.new_with_range(0.0, 0.5, 0.001)
        self.air_volume_spin.set_digits(3)
        self.air_volume_spin.set_value(0.0)
        self.air_volume_spin.set_tooltip_text(
            "Volume fraction of air/porosity (0.0-0.5)"
        )
        grid.attach(self.air_volume_spin, 1, 0, 1, 1)

        frame.add(grid)
        parent.pack_start(frame, False, False, 0)

    def _create_action_buttons(self, parent: Gtk.Box) -> None:
        """Create action buttons section."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)

        # Generate Input File button (Phase 2: Updated with microstructure selection)
        generate_button = create_button_with_icon("Generate Input File", "save")
        generate_button.connect("clicked", self._on_generate_input_file)
        generate_button.set_tooltip_text(
            "Generate elastic_input.txt file with lineage data"
        )
        button_box.pack_start(generate_button, False, False, 0)

        # Start Calculation button
        start_button = create_button_with_icon("Start Calculation", "play")
        start_button.connect("clicked", self._on_start_calculation)
        start_button.set_tooltip_text("Start elastic moduli calculation")
        button_box.pack_start(start_button, False, False, 0)

        # Clear Form button
        clear_button = create_button_with_icon("Clear Form", "erase")
        clear_button.connect("clicked", self._on_clear_form)
        clear_button.set_tooltip_text("Reset all form fields")
        button_box.pack_start(clear_button, False, False, 0)

        parent.pack_start(button_box, False, False, 0)

    def _load_available_hydration_operations(self) -> None:
        """Load available completed hydration operations by scanning filesystem."""
        try:
            import os
            from pathlib import Path

            # Clear combo box
            self.hydration_combo.remove_all()

            # Get operations directory from configuration
            operations_dir = self.service_container.directories_service.get_operations_path()
            self.logger.info(f"Scanning for hydration operations in: {operations_dir}")

            if not operations_dir.exists():
                self.logger.warning(f"Operations folder not found: {operations_dir}")
                self.hydration_combo.append("", "No completed hydration operations found")
                self.hydration_combo.set_sensitive(False)
                self.available_hydration_operations = []
                return

            # Scan filesystem for completed hydration operations
            hydration_operations = []

            for operation_path in operations_dir.iterdir():
                if not operation_path.is_dir():
                    continue

                operation_name = operation_path.name

                # Check for VCCTL hydration output files
                vcctl_csv_files = list(operation_path.glob("HydrationOf_*.csv"))
                vcctl_mov_files = list(operation_path.glob("HydrationOf_*.mov"))

                # Check for THAMES hydration output files
                # THAMES outputs to Result/ subdirectory
                result_dir = operation_path / "Result"
                thames_csv_files = []
                thames_img_files = []
                if result_dir.exists():
                    thames_csv_files = list(result_dir.glob("*_Microstructure.csv"))
                    thames_img_files = list(result_dir.glob("*.img"))

                # Also check for simparams.json (THAMES input file)
                simparams_file = operation_path / "simparams.json"
                progress_file = operation_path / "progress.json"

                # Count evidence of hydration operation
                files_found = 0

                # VCCTL evidence
                if vcctl_csv_files and any(f.stat().st_size > 0 for f in vcctl_csv_files):
                    files_found += 1
                if vcctl_mov_files and any(f.stat().st_size > 0 for f in vcctl_mov_files):
                    files_found += 1

                # THAMES evidence
                if thames_csv_files and any(f.stat().st_size > 0 for f in thames_csv_files):
                    files_found += 1
                if thames_img_files and any(f.stat().st_size > 0 for f in thames_img_files):
                    files_found += 1
                if simparams_file.exists() and simparams_file.stat().st_size > 0:
                    files_found += 1

                # Common evidence
                if progress_file.exists() and progress_file.stat().st_size > 0:
                    files_found += 1

                # Log what we found for debugging (use info level to ensure visibility)
                self.logger.info(
                    f"Checking {operation_name}: "
                    f"THAMES evidence: CSV={len(thames_csv_files)}, IMG={len(thames_img_files)}, "
                    f"simparams={simparams_file.exists()}, progress={progress_file.exists()}, "
                    f"total={files_found}"
                )

                # Consider it a hydration operation if it has at least 2 pieces of evidence
                if files_found >= 2:
                    # Get modification time for sorting
                    mtime = operation_path.stat().st_mtime
                    hydration_operations.append({
                        'name': operation_name,
                        'path': operation_path,
                        'mtime': mtime
                    })
                    self.logger.debug(f"Found completed hydration operation: {operation_name}")

            # Sort by modification time (most recent first)
            hydration_operations.sort(key=lambda x: x['mtime'], reverse=True)

            # Store for later use
            self.available_hydration_operations = hydration_operations

            # Populate combo box
            for op in hydration_operations:
                # Try to get timestamp from database for display, fallback to filesystem mtime
                from datetime import datetime
                timestamp_str = datetime.fromtimestamp(op['mtime']).strftime('%m/%d %H:%M')
                display_text = f"{op['name']} ({timestamp_str})"
                self.hydration_combo.append(op['name'], display_text)

            if not hydration_operations:
                self.hydration_combo.append("", "No completed hydration operations found")
                self.hydration_combo.set_sensitive(False)
                self.logger.info("No completed hydration operations found")
            else:
                self.hydration_combo.set_sensitive(True)
                self.logger.info(f"Found {len(hydration_operations)} hydration operations: {[op['name'] for op in hydration_operations]}")

        except Exception as e:
            self.logger.error(f"Error loading hydration operations: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.hydration_combo.append("", "Error loading operations")
            self.hydration_combo.set_sensitive(False)
            self.available_hydration_operations = []

    def _on_refresh_hydration_operations(self, button: Gtk.Button) -> None:
        """Refresh the list of available hydration operations."""
        self.logger.info("Refreshing hydration operations list...")

        # Store current selection to restore if possible
        current_selection = self.hydration_combo.get_active_id()

        # Reload operations
        self._load_available_hydration_operations()

        # Try to restore previous selection
        if current_selection:
            self.hydration_combo.set_active_id(current_selection)

        self.logger.info(
            f"Refreshed hydration operations - found {len(self.available_hydration_operations)} operations"
        )

    def _on_hydration_selection_changed(self, combo: Gtk.ComboBoxText) -> None:
        """Handle hydration operation selection change (Phase 2: Lineage-aware)."""
        active_id = combo.get_active_id()
        if not active_id or active_id == "":
            # Clear dependent fields
            self.microstructure_combo.set_sensitive(False)
            self.microstructure_combo.remove_all()
            self.resolved_lineage = None
            self._update_lineage_display(None)
            return

        try:
            # active_id is now the operation name (filesystem-based)
            operation_name = active_id
            hydration_operation = next(
                (
                    op
                    for op in self.available_hydration_operations
                    if op['name'] == operation_name
                ),
                None,
            )

            if hydration_operation:
                # Look up the operation in the database to get its ID for lineage
                from app.models.operation import Operation
                with self.service_container.database_service.get_session() as session:
                    db_operation = session.query(Operation).filter_by(name=operation_name).first()
                    hydration_id = db_operation.id if db_operation else None

                if hydration_id:
                    # Phase 2: Load lineage and microstructures
                    self._load_lineage_and_microstructures(hydration_id)
                else:
                    self.logger.warning(f"Hydration operation '{operation_name}' found on filesystem but not in database")
                    # Still allow selection, but without lineage
                    self.microstructure_combo.set_sensitive(True)

        except Exception as e:
            self.logger.error(f"Error handling hydration selection: {e}")
            self._show_error_dialog(f"Error loading hydration operation data: {str(e)}")

    def _load_lineage_and_microstructures(self, hydration_id: int) -> None:
        """Load lineage data and available microstructures (Phase 2).

        For THAMES mode, lineage resolution may fail if parent_operation_id
        is not set, but we should still try to discover microstructures.
        """
        # Store hydration ID for later re-resolution with output directory
        self._current_hydration_id = hydration_id

        # Try to resolve lineage chain (may fail for THAMES operations without proper linkage)
        try:
            self.resolved_lineage = (
                self.elastic_moduli_service.lineage_service.resolve_lineage_chain(
                    hydration_id
                )
            )
            self._update_lineage_display(self.resolved_lineage)
            self.logger.info("Successfully resolved lineage chain")
        except Exception as e:
            self.logger.warning(f"Could not resolve lineage chain: {e}")
            self.resolved_lineage = None
            if self.thames_mode:
                # In THAMES mode, lineage resolution may fail - show informational message
                self._update_lineage_display_thames_fallback(hydration_id)
            else:
                self._update_lineage_display(None)

        # Always try to discover microstructures, even if lineage resolution failed
        try:
            self.available_microstructures = (
                self.elastic_moduli_service.discover_hydrated_microstructures(
                    hydration_id
                )
            )
        except Exception as e:
            self.logger.error(f"Error discovering microstructures: {e}")
            self.available_microstructures = []

        # Populate microstructure combo
        self.microstructure_combo.remove_all()
        for i, microstructure in enumerate(self.available_microstructures):
            # For THAMES, time_label already includes "(Final)" for final, so check is_final
            if microstructure.is_final:
                display_text = microstructure.time_label
            else:
                display_text = microstructure.time_label
            self.microstructure_combo.append(str(i), display_text)

        if self.available_microstructures:
            # Don't auto-select any microstructure - let user choose
            self.microstructure_combo.set_active(-1)  # No selection
            self.microstructure_combo.set_sensitive(True)
            self.logger.info(
                f"Loaded {len(self.available_microstructures)} hydrated microstructures"
            )

            # Only populate lineage data if available
            if self.resolved_lineage:
                self._populate_from_resolved_lineage()
                self.logger.info(
                    "Populated UI fields from resolved lineage (waiting for user microstructure selection)"
                )
        else:
            self.microstructure_combo.append(
                "", "No hydrated microstructures found"
            )
            self.microstructure_combo.set_sensitive(False)
            self.logger.warning(
                f"No hydrated microstructures found for hydration operation {hydration_id}"
            )

    def _update_lineage_display_thames_fallback(self, hydration_id: int) -> None:
        """Update lineage display when lineage resolution fails in THAMES mode."""
        try:
            from app.models.operation import Operation
            with self.service_container.database_service.get_session() as session:
                hydration_op = session.query(Operation).filter_by(id=hydration_id).first()
                if hydration_op:
                    self.lineage_info_label.set_markup(
                        f'<span size="small">'
                        f'Hydration: <b>{hydration_op.name}</b>\n'
                        f'<span style="italic" foreground="#888888">'
                        f'(THAMES mode - lineage not available for aggregate properties)'
                        f'</span>'
                        f'</span>'
                    )
                else:
                    self.lineage_info_label.set_markup(
                        '<span size="small" style="italic">Lineage data not available</span>'
                    )
        except Exception as e:
            self.logger.error(f"Error updating THAMES fallback display: {e}")
            self.lineage_info_label.set_markup(
                '<span size="small" style="italic">Lineage data not available</span>'
            )

    def _update_lineage_display(self, lineage_data) -> None:
        """Update the lineage information display (Phase 2)."""
        if not lineage_data:
            self.lineage_info_label.set_markup(
                '<span size="small" style="italic">Select hydration operation to see lineage chain</span>'
            )
            return

        try:
            # Extract lineage information
            hydration_op = lineage_data.get("hydration_operation")
            microstructure_op = lineage_data.get("microstructure_operation")
            aggregate_props = lineage_data.get("aggregate_properties", {})
            volume_fractions = lineage_data.get("volume_fractions", {})

            # Build lineage chain display
            lineage_parts = []
            if microstructure_op:
                lineage_parts.append(f"Microstructure: <b>{microstructure_op.name}</b>")
            if hydration_op:
                lineage_parts.append(f"Hydration: <b>{hydration_op.name}</b>")

            lineage_chain = " → ".join(lineage_parts) + " → Elastic Moduli"

            # Add aggregate information
            agg_info = []
            fine_agg = aggregate_props.get("fine_aggregate")
            coarse_agg = aggregate_props.get("coarse_aggregate")

            if fine_agg:
                agg_info.append(
                    f"Fine: {fine_agg.name} (VF: {fine_agg.volume_fraction:.3f})"
                )
            if coarse_agg:
                agg_info.append(
                    f"Coarse: {coarse_agg.name} (VF: {coarse_agg.volume_fraction:.3f})"
                )

            air_vf = volume_fractions.get("air_volume_fraction", 0.0)
            if air_vf > 0:
                agg_info.append(f"Air: {air_vf:.3f}")

            agg_text = ", ".join(agg_info) if agg_info else "No aggregates"

            # Combine into display text
            display_text = f'<span size="small">Lineage: {lineage_chain}\nAggregates: {agg_text}</span>'
            self.lineage_info_label.set_markup(display_text)

            self.logger.info(
                f"Updated lineage display - Aggregates: {len(agg_info)} types"
            )

        except Exception as e:
            self.logger.error(f"Error updating lineage display: {e}")
            self.lineage_info_label.set_markup(
                '<span size="small" color="red">Error displaying lineage information</span>'
            )

    def _on_microstructure_selection_changed(self, combo: Gtk.ComboBoxText) -> None:
        """Handle microstructure time selection change (Phase 2)."""
        active_id = combo.get_active_id()
        if not active_id or active_id == "":
            return

        try:
            microstructure_index = int(active_id)
            if 0 <= microstructure_index < len(self.available_microstructures):
                selected_microstructure = self.available_microstructures[
                    microstructure_index
                ]
                self._populate_fields_from_selection(selected_microstructure)

        except Exception as e:
            self.logger.error(f"Error handling microstructure selection: {e}")

    def _populate_fields_from_selection(
        self, selected_microstructure: HydratedMicrostructure
    ) -> None:
        """Populate form fields based on selected microstructure with auto-generated names and relative paths.

        Works in both VCCTL mode (with full lineage) and THAMES mode (without lineage).
        """
        import re

        # Get hydration operation - either from lineage or directly from database
        hydration_op = None
        hydration_name = None

        if self.resolved_lineage:
            hydration_op = self.resolved_lineage.get("hydration_operation")
            if hydration_op:
                hydration_name = hydration_op.name

        # Fallback for THAMES mode: get hydration operation from database
        if not hydration_name and hasattr(self, "_current_hydration_id"):
            try:
                from app.models.operation import Operation
                with self.service_container.database_service.get_session() as session:
                    hydration_op = session.query(Operation).filter_by(
                        id=self._current_hydration_id
                    ).first()
                    if hydration_op:
                        hydration_name = hydration_op.name
            except Exception as e:
                self.logger.warning(f"Could not get hydration operation from database: {e}")

        if not hydration_name:
            self.logger.warning("No hydration operation available for populating fields")
            return

        # Auto-generate operation name: Elastic-{HydrationName}-{TimeStep}
        # Extract time step from microstructure time label
        time_step = selected_microstructure.time_label

        # Clean up time step for use in operation name
        # Handle THAMES format like "Final (30d)" or "7d" or "2h 24m"
        if "Final" in time_step:
            # Extract the time from "Final (30d)" format
            final_match = re.search(r"Final \((.+)\)", time_step)
            if final_match:
                time_step = f"Final-{final_match.group(1).replace(' ', '')}"
            else:
                time_step = "Final"
        else:
            # Clean up time step: replace spaces with nothing, keep alphanumeric
            time_step = time_step.replace(" ", "")

        operation_name = f"Elastic-{hydration_name}-{time_step}"
        self.operation_name_entry.set_text(operation_name)

        # Set image filename using selected microstructure path (relative)
        image_filename = os.path.basename(selected_microstructure.file_path)
        self.image_filename_entry.set_text(image_filename)

        # Set hierarchical output directory (absolute path)
        # Format: {OperationsDir}/{HydrationName}/{ElasticOperationName}
        operations_dir = self.service_container.directories_service.get_operations_path()
        output_dir = str(operations_dir / hydration_name / operation_name)
        self.output_dir_entry.set_text(output_dir)

        # Set PIMG file path (required for both THAMES and VCCTL elastic calculations)
        if selected_microstructure.pimg_path:
            # Use absolute path - consistent with output directory and works in PyInstaller
            pimg_absolute = Path(selected_microstructure.pimg_path)
            if pimg_absolute.exists():
                self.pimg_file_entry.set_text(str(pimg_absolute.resolve()))

        # Re-resolve lineage with output directory for accurate grading file paths (VCCTL mode only)
        if self.resolved_lineage and hasattr(self, "_current_hydration_id"):
            try:
                relative_output_dir = str(operations_dir / hydration_name / operation_name)
                self.resolved_lineage = (
                    self.elastic_moduli_service.lineage_service.resolve_lineage_chain(
                        self._current_hydration_id, relative_output_dir
                    )
                )
                self.logger.info(
                    f"Re-resolved lineage with output directory: {relative_output_dir}"
                )
            except Exception as e:
                self.logger.warning(
                    f"Error re-resolving lineage with output directory: {e}"
                )

        # Auto-populate from resolved lineage data (if available)
        if self.resolved_lineage:
            self._populate_from_resolved_lineage()

        self.logger.info(f"Auto-populated fields for operation: {operation_name}")

    def _populate_from_resolved_lineage(self) -> None:
        """Populate UI fields from resolved lineage data (Phase 2)."""
        if not self.resolved_lineage:
            return

        try:
            aggregate_props = self.resolved_lineage.get("aggregate_properties", {})
            volume_fractions = self.resolved_lineage.get("volume_fractions", {})

            # Set ITZ calculation based on aggregate presence
            has_itz = self.elastic_moduli_service.lineage_service.get_itz_detection(
                aggregate_props
            )
            self.has_itz_check.set_active(has_itz)

            # Set air volume fraction
            air_vf = volume_fractions.get("air_volume_fraction", 0.0)
            self.air_volume_spin.set_value(air_vf)

            # Set fine aggregate properties
            fine_agg = aggregate_props.get("fine_aggregate")
            if fine_agg:
                self.fine_agg_check.set_active(True)
                self._set_aggregate_controls_sensitive("fine", True)
                self.fine_volume_spin.set_value(fine_agg.volume_fraction)
                self.fine_bulk_spin.set_value(fine_agg.bulk_modulus)
                self.fine_shear_spin.set_value(fine_agg.shear_modulus)
                if fine_agg.grading_path:
                    # Show the file will be in the output directory, not Operations/
                    import os.path

                    filename = os.path.basename(fine_agg.grading_path)
                    self.fine_grading_entry.set_text(
                        f"./{filename}"
                    )  # Will be in output directory
                    # Update grading status to show template name if available
                    if (
                        hasattr(fine_agg, "grading_template_name")
                        and fine_agg.grading_template_name
                    ):
                        self.fine_grading_status_label.set_markup(
                            f'<span size="small" style="italic" color="green">✓ Template: <b>{fine_agg.grading_template_name}</b></span>'
                        )
                    else:
                        self.fine_grading_status_label.set_markup(
                            '<span size="small" style="italic" color="green">✓ Auto-populated from database template</span>'
                        )
                else:
                    self.fine_grading_status_label.set_markup(
                        '<span size="small" style="italic" color="orange">⚠ No grading template found</span>'
                    )
                # Update source label
                self.fine_agg_source_label.set_markup(
                    f'<span size="small" style="italic">Source: <b>{fine_agg.name}</b></span>'
                )
                self.logger.info(
                    f"Populated fine aggregate: {fine_agg.name} (VF: {fine_agg.volume_fraction:.3f})"
                )
            else:
                self.fine_agg_check.set_active(False)
                self._set_aggregate_controls_sensitive("fine", False)
                self.fine_agg_source_label.set_markup(
                    '<span size="small" style="italic">Source: Not specified</span>'
                )

            # Set coarse aggregate properties
            coarse_agg = aggregate_props.get("coarse_aggregate")
            if coarse_agg:
                self.coarse_agg_check.set_active(True)
                self._set_aggregate_controls_sensitive("coarse", True)
                self.coarse_volume_spin.set_value(coarse_agg.volume_fraction)
                self.coarse_bulk_spin.set_value(coarse_agg.bulk_modulus)
                self.coarse_shear_spin.set_value(coarse_agg.shear_modulus)
                if coarse_agg.grading_path:
                    # Show the file will be in the output directory, not Operations/
                    import os.path

                    filename = os.path.basename(coarse_agg.grading_path)
                    self.coarse_grading_entry.set_text(
                        f"./{filename}"
                    )  # Will be in output directory
                    # Update grading status to show template name if available
                    if (
                        hasattr(coarse_agg, "grading_template_name")
                        and coarse_agg.grading_template_name
                    ):
                        self.coarse_grading_status_label.set_markup(
                            f'<span size="small" style="italic" color="green">✓ Template: <b>{coarse_agg.grading_template_name}</b></span>'
                        )
                    else:
                        self.coarse_grading_status_label.set_markup(
                            '<span size="small" style="italic" color="green">✓ Auto-populated from database template</span>'
                        )
                else:
                    self.coarse_grading_status_label.set_markup(
                        '<span size="small" style="italic" color="orange">⚠ No grading template found</span>'
                    )
                # Update source label
                self.coarse_agg_source_label.set_markup(
                    f'<span size="small" style="italic">Source: <b>{coarse_agg.name}</b></span>'
                )
                self.logger.info(
                    f"Populated coarse aggregate: {coarse_agg.name} (VF: {coarse_agg.volume_fraction:.3f})"
                )
            else:
                self.coarse_agg_check.set_active(False)
                self._set_aggregate_controls_sensitive("coarse", False)
                self.coarse_agg_source_label.set_markup(
                    '<span size="small" style="italic">Source: Not specified</span>'
                )

            # Show success message
            populated_items = []
            if fine_agg:
                populated_items.append(f"fine aggregate ({fine_agg.name})")
            if coarse_agg:
                populated_items.append(f"coarse aggregate ({coarse_agg.name})")
            if air_vf > 0:
                populated_items.append(f"air content ({air_vf:.1%})")
            if has_itz:
                populated_items.append("ITZ calculations")

            if populated_items:
                message = f"Auto-populated from lineage: {', '.join(populated_items)}"
                self.logger.info(message)

        except Exception as e:
            self.logger.error(f"Error populating from resolved lineage: {e}")
            # Continue without auto-population - user can fill manually

    def _update_ui_from_operation(self, operation: ElasticModuliOperation) -> None:
        """Update UI fields with values from an ElasticModuliOperation object."""
        # Update ITZ checkbox
        self.has_itz_check.set_active(operation.has_itz or False)

        # Update air content
        self.air_volume_spin.set_value(operation.air_volume_fraction or 0.0)

        # Update fine aggregate properties
        if operation.has_fine_aggregate:
            self.fine_agg_check.set_active(True)
            self._set_aggregate_controls_sensitive("fine", True)

            if operation.fine_aggregate_volume_fraction is not None:
                self.fine_volume_spin.set_value(
                    operation.fine_aggregate_volume_fraction
                )
            if operation.fine_aggregate_grading_path:
                # Show the file will be in the output directory, not Operations/
                import os.path

                filename = os.path.basename(operation.fine_aggregate_grading_path)
                self.fine_grading_entry.set_text(
                    f"./{filename}"
                )  # Will be in output directory
            if operation.fine_aggregate_bulk_modulus is not None:
                self.fine_bulk_spin.set_value(operation.fine_aggregate_bulk_modulus)
            if operation.fine_aggregate_shear_modulus is not None:
                self.fine_shear_spin.set_value(operation.fine_aggregate_shear_modulus)

            self.logger.info(
                f"Updated fine aggregate UI: {operation.fine_aggregate_display_name} "
                f"(VF: {operation.fine_aggregate_volume_fraction:.3f})"
            )
        else:
            self.fine_agg_check.set_active(False)
            self._set_aggregate_controls_sensitive("fine", False)

        # Update coarse aggregate properties
        if operation.has_coarse_aggregate:
            self.coarse_agg_check.set_active(True)
            self._set_aggregate_controls_sensitive("coarse", True)

            if operation.coarse_aggregate_volume_fraction is not None:
                self.coarse_volume_spin.set_value(
                    operation.coarse_aggregate_volume_fraction
                )
            if operation.coarse_aggregate_grading_path:
                # Show the file will be in the output directory, not Operations/
                import os.path

                filename = os.path.basename(operation.coarse_aggregate_grading_path)
                self.coarse_grading_entry.set_text(
                    f"./{filename}"
                )  # Will be in output directory
            if operation.coarse_aggregate_bulk_modulus is not None:
                self.coarse_bulk_spin.set_value(operation.coarse_aggregate_bulk_modulus)
            if operation.coarse_aggregate_shear_modulus is not None:
                self.coarse_shear_spin.set_value(
                    operation.coarse_aggregate_shear_modulus
                )

            self.logger.info(
                f"Updated coarse aggregate UI: {operation.coarse_aggregate_display_name} "
                f"(VF: {operation.coarse_aggregate_volume_fraction:.3f})"
            )
        else:
            self.coarse_agg_check.set_active(False)
            self._set_aggregate_controls_sensitive("coarse", False)

        # Show a user-friendly message about what was auto-populated
        populated_items = []
        if operation.has_fine_aggregate:
            populated_items.append(
                f"fine aggregate ({operation.fine_aggregate_display_name})"
            )
        if operation.has_coarse_aggregate:
            populated_items.append(
                f"coarse aggregate ({operation.coarse_aggregate_display_name})"
            )
        if operation.air_volume_fraction and operation.air_volume_fraction > 0:
            populated_items.append(f"air content ({operation.air_volume_fraction:.1%})")
        if operation.has_itz:
            populated_items.append("ITZ calculations")

        if populated_items:
            message = (
                f"Auto-populated from microstructure: {', '.join(populated_items)}"
            )
            self.logger.info(message)
            # You could show this message to the user via a temporary info bar or status message

    def _set_aggregate_controls_sensitive(self, agg_type: str, sensitive: bool) -> None:
        """Enable/disable aggregate controls based on checkbox state."""
        if agg_type == "fine":
            controls = [
                self.fine_volume_spin,
                self.fine_grading_entry,
                self.fine_bulk_spin,
                self.fine_shear_spin,
            ]
        else:
            controls = [
                self.coarse_volume_spin,
                self.coarse_grading_entry,
                self.coarse_bulk_spin,
                self.coarse_shear_spin,
            ]

        for control in controls:
            if control:
                control.set_sensitive(sensitive)

    def _disable_aggregate_settings(self) -> None:
        """Disable all aggregate settings in THAMES mode.

        In THAMES mode, aggregate support is not yet available (requires concelas).
        This method greys out all aggregate-related controls.
        """
        # Disable fine aggregate controls
        if self.fine_agg_check:
            self.fine_agg_check.set_active(False)
            self.fine_agg_check.set_sensitive(False)
        self._set_aggregate_controls_sensitive("fine", False)

        # Disable coarse aggregate controls
        if self.coarse_agg_check:
            self.coarse_agg_check.set_active(False)
            self.coarse_agg_check.set_sensitive(False)
        self._set_aggregate_controls_sensitive("coarse", False)

        # Disable ITZ checkbox
        if self.has_itz_check:
            self.has_itz_check.set_active(False)
            self.has_itz_check.set_sensitive(False)

        self.logger.info("Aggregate settings disabled in THAMES mode")

    def _on_fine_aggregate_toggled(self, checkbox: Gtk.CheckButton) -> None:
        """Handle fine aggregate checkbox toggle."""
        self._set_aggregate_controls_sensitive("fine", checkbox.get_active())

    def _on_coarse_aggregate_toggled(self, checkbox: Gtk.CheckButton) -> None:
        """Handle coarse aggregate checkbox toggle."""
        self._set_aggregate_controls_sensitive("coarse", checkbox.get_active())

    def _on_browse_output_dir(self, button: Gtk.Button) -> None:
        """Handle output directory browse button."""
        dialog = Gtk.FileChooserDialog(
            title="Select Output Directory",
            parent=self.main_window,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SELECT,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.output_dir_entry.set_text(dialog.get_filename())

        dialog.destroy()

    def _on_browse_pimg_file(self, button: Gtk.Button) -> None:
        """Handle pimg file browse button."""
        dialog = Gtk.FileChooserDialog(
            title="Select Pimg File",
            parent=self.main_window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        # Add file filter
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Pimg files")
        file_filter.add_pattern("*.pimg")
        dialog.add_filter(file_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.pimg_file_entry.set_text(dialog.get_filename())

        dialog.destroy()

    def _on_browse_grading_file(self, button: Gtk.Button, agg_type: str) -> None:
        """Handle grading file browse button."""
        dialog = Gtk.FileChooserDialog(
            title=f"Select {agg_type.title()} Aggregate Grading File",
            parent=self.main_window,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if agg_type == "fine":
                self.fine_grading_entry.set_text(filename)
            else:
                self.coarse_grading_entry.set_text(filename)

        dialog.destroy()

    def _on_generate_input_file(self, button: Gtk.Button) -> None:
        """Handle generate input file button (Phase 2: Lineage-aware)."""
        try:
            # Validate selections
            if not self._validate_selections():
                return

            # Get selected microstructure
            selected_microstructure = self._get_selected_microstructure()
            if not selected_microstructure:
                self._show_error_dialog("Please select a hydrated microstructure")
                return

            # Create operation from form
            operation = self._create_operation_from_form()
            if not operation:
                return

            # Generate input file using Phase 1 services
            output_dir = self.output_dir_entry.get_text().strip()
            if not output_dir:
                self._show_error_dialog("Output directory is required")
                return

            input_file_path = self.elastic_moduli_service.generate_elastic_input_file(
                operation, selected_microstructure, output_dir
            )

            self._show_info_dialog(
                f"Input file generated successfully:\n{input_file_path}"
            )

        except Exception as e:
            self.logger.error(f"Error generating input file: {e}")
            self._show_error_dialog(f"Failed to generate input file:\n{str(e)}")

    def _on_start_calculation(self, button: Gtk.Button) -> None:
        """Handle start calculation button (Phase 3: Database operation with lineage tracking)."""
        try:
            # Phase 3: Enhanced validation
            if not self._validate_selections():
                return

            operation_name = self.operation_name_entry.get_text().strip()
            # Operation name is auto-generated, should always be present after validation

            # Get selected microstructure and hydration ID
            selected_microstructure = self._get_selected_microstructure()
            if not selected_microstructure:
                self._show_error_dialog("Please select a hydrated microstructure")
                return

            # Get hydration operation name from combo box (now stores names, not IDs)
            hydration_name = self.hydration_combo.get_active_id()
            if not hydration_name:
                self._show_error_dialog("Please select a hydration operation")
                return

            # Look up hydration operation ID in database
            from app.models.operation import Operation
            with self.service_container.database_service.get_session() as session:
                db_operation = session.query(Operation).filter_by(name=hydration_name).first()
                if not db_operation:
                    self._show_error_dialog(f"Hydration operation '{hydration_name}' not found in database")
                    return
                hydration_id = db_operation.id

            # Phase 3: Capture UI parameters for storage
            ui_parameters = self._capture_elastic_ui_parameters()
            ui_parameters["selected_microstructure"] = {
                "file_path": selected_microstructure.file_path,
                "pimg_path": selected_microstructure.pimg_path,
                "time_label": selected_microstructure.time_label,
                "is_final": selected_microstructure.is_final,
            }

            # Phase 3: Create ElasticModuliOperation with required image_filename
            # Extract filename and paths before creating database record
            image_filename = (
                os.path.basename(selected_microstructure.file_path)
                if selected_microstructure
                else "microstructure.img"
            )
            pimg_file_path = (
                selected_microstructure.pimg_path if selected_microstructure else None
            )

            # Create the operation with the required fields to avoid NOT NULL constraint
            elastic_operation, lineage_data = (
                self.elastic_moduli_service.create_operation_with_lineage(
                    name=operation_name,
                    hydration_operation_id=hydration_id,
                    description=f"Elastic moduli calculation using {selected_microstructure.time_label} microstructure",
                    image_filename=image_filename,
                    pimg_file_path=pimg_file_path,
                )
            )

            # Launch process through Operations panel (let it create database operation)
            operation_id = self._launch_elastic_process(
                operation_name=operation_name,
                hydration_id=hydration_id,  # For linking parent operation
                elastic_operation=elastic_operation,
                selected_microstructure=selected_microstructure,
                ui_parameters=ui_parameters,
            )

            success = operation_id is not None

            if success:
                self._show_info_dialog(
                    f"Elastic moduli operation '{operation_name}' launched successfully.\n\nUsing microstructure: {selected_microstructure.time_label}\nCheck the Operations panel to monitor progress."
                )
                self.logger.info(
                    f"Successfully launched elastic operation '{operation_name}' with database ID: {operation_id}"
                )
            else:
                self._show_error_dialog(
                    f"Failed to launch elastic moduli operation '{operation_name}'"
                )
                self.logger.error(
                    f"Failed to launch elastic operation '{operation_name}'"
                )

        except Exception as e:
            self.logger.error(f"Error starting calculation: {e}")
            self._show_error_dialog(f"Failed to start calculation:\n{str(e)}")

    def _on_clear_form(self, button: Gtk.Button) -> None:
        """Handle clear form button (Phase 2: Include microstructure selection)."""
        # Reset all form fields
        self.hydration_combo.set_active(-1)
        self.microstructure_combo.remove_all()  # Phase 2: Clear microstructure selection
        self.microstructure_combo.set_sensitive(False)
        self.operation_name_entry.set_text("")
        self.image_filename_entry.set_text("")
        self.output_dir_entry.set_text("")
        self.pimg_file_entry.set_text("")
        self.has_itz_check.set_active(False)
        self.air_volume_spin.set_value(0.0)

        # Reset aggregate controls
        self.fine_agg_check.set_active(False)
        self.fine_volume_spin.set_value(0.0)
        self.fine_grading_entry.set_text("")
        self.fine_bulk_spin.set_value(37.0)
        self.fine_shear_spin.set_value(44.0)

        self.coarse_agg_check.set_active(False)
        self.coarse_volume_spin.set_value(0.0)
        self.coarse_grading_entry.set_text("")
        self.coarse_bulk_spin.set_value(37.0)
        self.coarse_shear_spin.set_value(44.0)

        # Disable aggregate controls
        self._set_aggregate_controls_sensitive("fine", False)
        self._set_aggregate_controls_sensitive("coarse", False)

        # Phase 2: Reset lineage data
        self.resolved_lineage = None
        self.available_microstructures = []
        self._update_lineage_display(None)

    def _validate_selections(self) -> bool:
        """Validate that all required selections are made (Phase 2)."""
        # Check hydration operation selection
        if not self.hydration_combo.get_active_id():
            self._show_error_dialog("Please select a hydration operation")
            return False

        # Check microstructure selection
        if (
            not self.microstructure_combo.get_active_id()
            or not self.available_microstructures
        ):
            self._show_error_dialog("Please select a hydrated microstructure")
            return False

        # Check operation name (auto-generated, should always be present)
        if not self.operation_name_entry.get_text().strip():
            self._show_error_dialog(
                "Operation name not generated. Please select a microstructure first."
            )
            return False

        return True

    def _get_selected_microstructure(self) -> Optional[HydratedMicrostructure]:
        """Get the currently selected microstructure (Phase 2)."""
        active_id = self.microstructure_combo.get_active_id()
        if not active_id:
            return None

        try:
            index = int(active_id)
            if 0 <= index < len(self.available_microstructures):
                return self.available_microstructures[index]
        except (ValueError, IndexError):
            pass

        return None

    def _launch_elastic_process(
        self,
        operation_name: str,
        hydration_id: int,
        elastic_operation: ElasticModuliOperation,
        selected_microstructure,
        ui_parameters: Dict[str, Any],
    ) -> Optional[str]:
        """Launch elastic moduli process through Operations panel (Phase 3).

        Supports two backends:
        - THAMES: Uses thames executable with -s 5 (elastic calculation mode)
        - VCCTL: Uses elastic.c with generated input file
        """
        try:
            # Get operations panel reference
            operations_panel = getattr(self.main_window, "operations_panel", None)
            if not operations_panel:
                self.logger.error("Operations panel not found")
                return None

            # Get hydration operation name for output directory structure
            hydration_name = self._get_hydration_operation_name(hydration_id)
            operations_dir = self.service_container.directories_service.get_operations_path()

            if hydration_name:
                # Nest elastic operation inside hydration folder
                output_dir = operations_dir / hydration_name / operation_name
            else:
                # Fallback to flat structure if we can't find hydration name
                output_dir = operations_dir / operation_name
                self.logger.warning(
                    f"Could not find hydration operation name for ID {hydration_id}, using flat structure"
                )

            output_dir.mkdir(parents=True, exist_ok=True)

            from app.windows.panels.operations_monitoring_panel import OperationType

            if self.thames_mode:
                # =========================================================
                # THAMES Backend: Use thames executable with -s 5
                # =========================================================
                return self._launch_thames_elastic(
                    operation_name=operation_name,
                    hydration_id=hydration_id,
                    hydration_name=hydration_name,
                    output_dir=output_dir,
                    selected_microstructure=selected_microstructure,
                    ui_parameters=ui_parameters,
                    operations_panel=operations_panel,
                )
            else:
                # =========================================================
                # VCCTL Backend: Use elastic.c with generated input file
                # =========================================================
                return self._launch_vcctl_elastic(
                    operation_name=operation_name,
                    hydration_id=hydration_id,
                    output_dir=output_dir,
                    elastic_operation=elastic_operation,
                    selected_microstructure=selected_microstructure,
                    ui_parameters=ui_parameters,
                    operations_panel=operations_panel,
                )

        except Exception as e:
            self.logger.error(f"Error launching elastic process: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None

    def _launch_thames_elastic(
        self,
        operation_name: str,
        hydration_id: int,
        hydration_name: str,
        output_dir: Path,
        selected_microstructure,
        ui_parameters: Dict[str, Any],
        operations_panel,
    ) -> Optional[str]:
        """Launch THAMES elastic calculation using thames executable with -s 5.

        THAMES elastic calculation:
        - Reads phase elastic moduli from simparams.json
        - Performs FEM calculation on single microstructure
        - Outputs bulk modulus, shear modulus, Young's modulus, Poisson's ratio
        - Results written to elastic_results.txt

        Args:
            operation_name: Name for the operation
            hydration_id: Parent hydration operation ID
            hydration_name: Name of parent hydration operation
            output_dir: Directory for output files
            selected_microstructure: Selected microstructure from lineage
            ui_parameters: UI parameters for database storage
            operations_panel: Reference to operations monitoring panel

        Returns:
            Operation ID if successful, None otherwise
        """
        import sys

        # Get THAMES executable path
        thames_path = self._get_thames_executable_path()
        if not thames_path:
            self.logger.error("THAMES executable not found")
            self._show_error_dialog(
                "THAMES executable not found.\n\n"
                "Please ensure the thames executable is compiled and located in bin/"
            )
            return None

        # Get simparams.json path from hydration operation
        simparams_path = self._get_simparams_path(hydration_name)
        if not simparams_path:
            self.logger.error(f"simparams.json not found for hydration operation: {hydration_name}")
            self._show_error_dialog(
                f"simparams.json not found for hydration operation '{hydration_name}'.\n\n"
                "This file is required for THAMES elastic calculation as it contains "
                "the elastic moduli for each phase."
            )
            return None

        # Get microstructure file path
        mic_path = self._get_thames_microstructure_for_elastic(hydration_name, selected_microstructure)
        if not mic_path:
            self.logger.error(f"Microstructure file not found for: {hydration_name}")
            self._show_error_dialog(
                f"Microstructure file not found for hydration operation '{hydration_name}'.\n\n"
                "Please ensure the hydration simulation completed successfully and "
                "generated microstructure output files."
            )
            return None

        self.logger.info(f"THAMES elastic calculation:")
        self.logger.info(f"  Executable: {thames_path}")
        self.logger.info(f"  Simparams: {simparams_path}")
        self.logger.info(f"  Microstructure: {mic_path}")
        self.logger.info(f"  Output dir: {output_dir}")

        # Copy simparams.json to output directory if not already there
        output_simparams = output_dir / "simparams.json"
        if not output_simparams.exists():
            import shutil
            shutil.copy2(simparams_path, output_simparams)
            self.logger.info(f"Copied simparams.json to output directory")

        # Create Result subdirectory (THAMES expects this)
        result_dir = output_dir / "Result"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Copy microstructure to output directory (not Result - we run from output_dir)
        output_mic = output_dir / mic_path.name
        if not output_mic.exists():
            import shutil
            shutil.copy2(mic_path, output_mic)
            self.logger.info(f"Copied microstructure to: {output_mic}")

        # Copy GEMS database files to output directory
        hydration_dir = simparams_path.parent
        gems_files = ["thames-dat.lst", "thames-dch.dat", "thames-ipm.dat", "thames-dbr.dat"]
        for gems_file in gems_files:
            src = hydration_dir / gems_file
            dst = output_dir / gems_file
            if src.exists() and not dst.exists():
                import shutil
                shutil.copy2(src, dst)
                self.logger.info(f"Copied {gems_file} to output directory")

        # Create input.in file for THAMES
        # THAMES reads from stdin, so we create an input file with:
        # 1. Simulation type (5 = ELASTIC_CALC)
        # 2. GEM input file name (thames-dat.lst)
        # 3. Simulation parameter file name (simparams.json)
        # 4. Microstructure file name
        input_file = output_dir / "input.in"
        with open(input_file, 'w') as f:
            f.write("5\n")  # ELASTIC_CALC simulation type
            f.write("thames-dat.lst\n")  # GEM input file (relative path)
            f.write("simparams.json\n")  # Simulation parameters (relative path)
            f.write(f"{output_mic.name}\n")  # Microstructure file (relative path)
        self.logger.info(f"Created input file: {input_file}")

        # Build THAMES command with output folder option
        # THAMES elastic mode reads from stdin, use -o to specify output folder
        from app.windows.panels.operations_monitoring_panel import OperationType

        command = [
            str(thames_path),
            "-o", "Result",  # Output folder for results
        ]

        self.logger.info(f"THAMES command: {' '.join(command)}")
        self.logger.info(f"Input file contents: 5, thames-dat.lst, simparams.json, {output_mic.name}")

        # Read the input file content for stdin
        with open(input_file, 'r') as f:
            input_data = f.read()

        # Launch the process with stdin redirection
        operation_id = operations_panel.start_real_process_operation(
            name=operation_name,
            operation_type=OperationType.ELASTIC_MODULI_CALCULATION,
            command=command,
            working_dir=str(output_dir),
            input_data=input_data,  # THAMES reads from stdin
        )

        # Update database operation with UI parameters and parent linkage
        if operation_id:
            ui_parameters["backend"] = "THAMES"
            ui_parameters["simparams_path"] = str(simparams_path)
            ui_parameters["microstructure_path"] = str(mic_path)
            self._update_elastic_operation_metadata(
                operation_id=operation_id,
                ui_parameters=ui_parameters,
                parent_operation_id=hydration_id,
            )

        self.logger.info(
            f"Launched THAMES elastic operation '{operation_name}' with database ID: {operation_id}"
        )
        return operation_id

    def _launch_vcctl_elastic(
        self,
        operation_name: str,
        hydration_id: int,
        output_dir: Path,
        elastic_operation: ElasticModuliOperation,
        selected_microstructure,
        ui_parameters: Dict[str, Any],
        operations_panel,
    ) -> Optional[str]:
        """Launch VCCTL elastic calculation using elastic.c.

        VCCTL elastic calculation:
        - Uses generated elastic_input.txt file
        - Supports aggregates and ITZ via concelas
        - Multi-scale concrete calculation

        Args:
            operation_name: Name for the operation
            hydration_id: Parent hydration operation ID
            output_dir: Directory for output files
            elastic_operation: ElasticModuliOperation with parameters
            selected_microstructure: Selected microstructure from lineage
            ui_parameters: UI parameters for database storage
            operations_panel: Reference to operations monitoring panel

        Returns:
            Operation ID if successful, None otherwise
        """
        import sys

        # Get VCCTL elastic executable path
        elastic_path = self._get_vcctl_elastic_path()
        if not elastic_path:
            self.logger.error("VCCTL elastic executable not found")
            self._show_error_dialog(
                "VCCTL elastic executable not found.\n\n"
                "Please ensure elastic.c is compiled and located in bin/"
            )
            return None

        # Generate input file using existing service
        input_file_path = self.elastic_moduli_service.generate_elastic_input_file(
            elastic_operation, selected_microstructure, str(output_dir)
        )

        # Read input file content for stdin
        with open(input_file_path, "r") as f:
            input_content = f.read()

        from app.windows.panels.operations_monitoring_panel import OperationType

        progress_file = "elastic_progress.json"  # Relative to working directory

        operation_id = operations_panel.start_real_process_operation(
            name=operation_name,
            operation_type=OperationType.ELASTIC_MODULI_CALCULATION,
            command=[
                str(elastic_path),
                "-j",
                progress_file,  # Progress JSON file (relative path)
                "-w",
                ".",  # Working directory (current directory)
            ],
            working_dir=str(output_dir),
            input_data=input_content,  # Input provided via stdin
        )

        # Update database operation with UI parameters and parent linkage
        if operation_id:
            ui_parameters["backend"] = "VCCTL"
            self._update_elastic_operation_metadata(
                operation_id=operation_id,
                ui_parameters=ui_parameters,
                parent_operation_id=hydration_id,
            )

        self.logger.info(
            f"Launched VCCTL elastic operation '{operation_name}' with database ID: {operation_id}"
        )
        return operation_id

    def _get_hydration_operation_name(self, hydration_id: int) -> Optional[str]:
        """Get the name of a hydration operation by its ID."""
        try:
            from app.database.service import DatabaseService
            from app.models.operation import Operation

            db_service = DatabaseService()
            with db_service.get_session() as session:
                hydration_op = (
                    session.query(Operation).filter_by(id=hydration_id).first()
                )
                if hydration_op:
                    return hydration_op.name
            return None
        except Exception as e:
            self.logger.error(f"Error getting hydration operation name: {e}")
            return None

    def _update_elastic_operation_metadata(
        self, operation_id: str, ui_parameters: Dict[str, Any], parent_operation_id: int
    ) -> None:
        """Update the database operation with UI parameters and parent linkage (Phase 3)."""
        try:
            from app.database.service import DatabaseService
            from app.models.operation import Operation

            db_service = DatabaseService()
            with db_service.get_session() as session:
                # Convert operation_id to int if it's a string
                op_id = (
                    int(operation_id) if isinstance(operation_id, str) else operation_id
                )

                db_operation = session.query(Operation).filter_by(id=op_id).first()
                if db_operation:
                    # Update with UI parameters for reproducibility
                    db_operation.stored_ui_parameters = ui_parameters
                    # Link to parent hydration operation
                    db_operation.parent_operation_id = parent_operation_id
                    session.commit()
                    self.logger.info(
                        f"Updated elastic operation {operation_id} with metadata and parent linkage to {parent_operation_id}"
                    )
                else:
                    self.logger.warning(
                        f"Database operation {operation_id} not found for metadata update"
                    )

        except Exception as e:
            self.logger.error(f"Error updating elastic operation metadata: {e}")

    def _create_operation_from_form(self) -> Optional[ElasticModuliOperation]:
        """Create ElasticModuliOperation from form data."""
        # Validate required fields
        errors = []

        hydration_id = self.hydration_combo.get_active_id()
        if not hydration_id or hydration_id == "":
            errors.append("Please select a hydration operation")

        operation_name = self.operation_name_entry.get_text().strip()
        if not operation_name:
            errors.append(
                "Operation name not generated - please select a microstructure"
            )

        image_filename = self.image_filename_entry.get_text().strip()
        if not image_filename:
            errors.append("Image filename is required")

        output_directory = self.output_dir_entry.get_text().strip()
        if not output_directory:
            errors.append("Output directory is required")

        if errors:
            self._show_error_dialog(
                "Please fix the following errors:\n\n"
                + "\n".join(f"• {error}" for error in errors)
            )
            return None

        # Create operation object
        operation = ElasticModuliOperation(
            name=operation_name,
            hydration_operation_id=int(hydration_id),
            image_filename=image_filename,
            early_age_connection=1,
            has_itz=self.has_itz_check.get_active(),
            output_directory=output_directory,
            pimg_file_path=self.pimg_file_entry.get_text().strip() or None,
            # Fine aggregate
            has_fine_aggregate=self.fine_agg_check.get_active(),
            fine_aggregate_volume_fraction=self.fine_volume_spin.get_value()
            if self.fine_agg_check.get_active()
            else None,
            fine_aggregate_grading_path=self.fine_grading_entry.get_text().strip()
            or None
            if self.fine_agg_check.get_active()
            else None,
            fine_aggregate_bulk_modulus=self.fine_bulk_spin.get_value()
            if self.fine_agg_check.get_active()
            else None,
            fine_aggregate_shear_modulus=self.fine_shear_spin.get_value()
            if self.fine_agg_check.get_active()
            else None,
            # Coarse aggregate
            has_coarse_aggregate=self.coarse_agg_check.get_active(),
            coarse_aggregate_volume_fraction=self.coarse_volume_spin.get_value()
            if self.coarse_agg_check.get_active()
            else None,
            coarse_aggregate_grading_path=self.coarse_grading_entry.get_text().strip()
            or None
            if self.coarse_agg_check.get_active()
            else None,
            coarse_aggregate_bulk_modulus=self.coarse_bulk_spin.get_value()
            if self.coarse_agg_check.get_active()
            else None,
            coarse_aggregate_shear_modulus=self.coarse_shear_spin.get_value()
            if self.coarse_agg_check.get_active()
            else None,
            # Air content
            air_volume_fraction=self.air_volume_spin.get_value(),
        )

        # Validate the operation
        validation_errors = self.elastic_moduli_service.validate_operation_parameters(
            operation
        )
        if validation_errors:
            self._show_error_dialog(
                "Validation errors:\n\n"
                + "\n".join(f"• {error}" for error in validation_errors)
            )
            return None

        return operation

    def _show_error_dialog(self, message: str) -> None:
        """Show error dialog."""
        dialog = Gtk.MessageDialog(
            parent=self.main_window,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            message_format=message,
        )
        dialog.run()
        dialog.destroy()

    def _show_info_dialog(self, message: str) -> None:
        """Show information dialog."""
        dialog = Gtk.MessageDialog(
            parent=self.main_window,
            flags=Gtk.DialogFlags.MODAL,
            type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            message_format=message,
        )
        dialog.run()
        dialog.destroy()

    def refresh(self) -> None:
        """Refresh the panel data."""
        self._load_available_hydration_operations()

    def get_panel_name(self) -> str:
        """Get the panel name for tab display."""
        return "Elastic Moduli"

    # Phase 3: Clean Naming and Lineage Methods

    def _capture_elastic_ui_parameters(self) -> Dict[str, Any]:
        """Capture all UI parameters for storage with operation (Phase 3)."""
        try:
            # Get selected hydration operation details
            hydration_id = self.hydration_combo.get_active_id()
            hydration_name = ""
            if hydration_id:
                model = self.hydration_combo.get_model()
                iter = self.hydration_combo.get_active_iter()
                if iter:
                    hydration_name = model.get_value(
                        iter, 1
                    )  # Get operation name from combo

            ui_params = {
                # Basic operation information
                "operation_name": self.operation_name_entry.get_text().strip(),
                "hydration_operation_id": hydration_id,
                "hydration_operation_name": hydration_name,
                # File settings
                "image_filename": self.image_filename_entry.get_text().strip(),
                "output_directory": self.output_dir_entry.get_text().strip(),
                "pimg_file_path": self.pimg_file_entry.get_text().strip(),
                # Microstructure settings
                "has_itz": self.has_itz_check.get_active(),
                "air_volume_fraction": self.air_volume_spin.get_value(),
                # Fine aggregate settings
                "has_fine_aggregate": self.fine_agg_check.get_active(),
                "fine_aggregate_settings": {
                    "volume_fraction": self.fine_volume_spin.get_value(),
                    "grading_file": self.fine_grading_entry.get_text().strip(),
                    "bulk_modulus": self.fine_bulk_spin.get_value(),
                    "shear_modulus": self.fine_shear_spin.get_value(),
                }
                if self.fine_agg_check.get_active()
                else None,
                # Coarse aggregate settings
                "has_coarse_aggregate": self.coarse_agg_check.get_active(),
                "coarse_aggregate_settings": {
                    "volume_fraction": self.coarse_volume_spin.get_value(),
                    "grading_file": self.coarse_grading_entry.get_text().strip(),
                    "bulk_modulus": self.coarse_bulk_spin.get_value(),
                    "shear_modulus": self.coarse_shear_spin.get_value(),
                }
                if self.coarse_agg_check.get_active()
                else None,
                # Metadata
                "timestamp": datetime.now().isoformat(),
                "panel_version": "1.0",
            }

            return ui_params

        except Exception as e:
            self.logger.error(f"Error capturing UI parameters: {e}")
            return {}

    def _create_elastic_operation(
        self,
        operation_name: str,
        ui_parameters: Dict[str, Any],
        parent_operation_id: Optional[int],
    ) -> Optional["Operation"]:
        """Create elastic moduli operation in database with UI parameters and lineage (Phase 3)."""
        try:
            from app.database.service import DatabaseService
            from app.models.operation import Operation, OperationType, OperationStatus

            db_service = DatabaseService()
            with db_service.get_session() as session:
                # Create the general operation record with Phase 3 features
                operation = Operation(
                    name=operation_name,  # Clean user-defined name
                    operation_type=OperationType.ELASTIC_MODULI.value,
                    status=OperationStatus.QUEUED.value,
                    stored_ui_parameters=ui_parameters,  # Complete UI state for reproducibility
                    parent_operation_id=parent_operation_id,  # Phase 3: Lineage to hydration operation
                )

                session.add(operation)
                session.commit()
                session.refresh(operation)

                self.logger.info(
                    f"Phase 3: Created elastic operation: {operation_name} (ID: {operation.id})"
                )
                if parent_operation_id:
                    self.logger.info(
                        f"Phase 3: Linked to parent hydration operation ID: {parent_operation_id}"
                    )

                return operation

        except Exception as e:
            self.logger.error(f"Error creating elastic operation: {e}")
            return None

    def _get_parent_microstructure_name(
        self, hydration_operation: Operation
    ) -> Optional[str]:
        """Get the parent microstructure operation name through lineage chain."""
        try:
            from app.database.service import DatabaseService
            from app.models.operation import Operation, OperationType

            db_service = DatabaseService()
            with db_service.get_session() as session:
                # Get the parent of the hydration operation (should be microstructure)
                if hydration_operation.parent_operation_id:
                    parent_op = (
                        session.query(Operation)
                        .filter_by(id=hydration_operation.parent_operation_id)
                        .first()
                    )

                    if (
                        parent_op
                        and parent_op.operation_type
                        == OperationType.MICROSTRUCTURE.value
                    ):
                        return parent_op.name
                    else:
                        self.logger.warning(
                            f"Parent operation {hydration_operation.parent_operation_id} is not a microstructure operation"
                        )
                else:
                    # Fallback: Try to extract from stored UI parameters if available
                    if hydration_operation.stored_ui_parameters:
                        params = hydration_operation.stored_ui_parameters
                        if "source_microstructure" in params:
                            return params["source_microstructure"].get("name")

            return None

        except Exception as e:
            self.logger.error(f"Error getting parent microstructure name: {e}")
            return None

    # =========================================================================
    # THAMES Backend Detection and Support Methods
    # =========================================================================

    def _is_thames_mode(self) -> bool:
        """
        Detect if THAMES backend should be used for elastic calculations.

        THAMES mode is used when:
        1. The thames executable exists in bin/
        2. We're running the THAMES application (not VCCTL)

        Returns:
            True if THAMES backend should be used, False for VCCTL elastic.c
        """
        import sys

        # Check for THAMES executable
        thames_path = self._get_thames_executable_path()
        if thames_path and thames_path.exists():
            self.logger.info(f"THAMES mode enabled - found executable at: {thames_path}")
            return True

        # Fallback: check for VCCTL elastic executable
        elastic_path = self._get_vcctl_elastic_path()
        if elastic_path and elastic_path.exists():
            self.logger.info(f"VCCTL mode - using elastic.c at: {elastic_path}")
            return False

        # Default to THAMES mode if neither found (will show error at runtime)
        self.logger.warning("No elastic calculation executable found - defaulting to THAMES mode")
        return True

    def _get_thames_executable_path(self) -> Optional[Path]:
        """
        Get the path to the THAMES executable.

        Returns:
            Path to thames executable, or None if not found
        """
        import sys

        # Platform-specific executable name
        exe_name = 'thames.exe' if sys.platform == 'win32' else 'thames'

        # Detect if running in PyInstaller bundle
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            bin_dir = Path(sys._MEIPASS) / "bin"
            thames_path = bin_dir / exe_name
            if thames_path.exists():
                return thames_path
        else:
            # Running in development - check multiple locations
            project_root = Path(__file__).parent.parent.parent.parent.parent

            # Primary location: top-level bin/
            thames_path = project_root / "bin" / exe_name
            if thames_path.exists():
                return thames_path

            # Fallback: backend/bin/
            fallback_path = project_root / "backend" / "bin" / exe_name
            if fallback_path.exists():
                return fallback_path

            # Fallback: backend/thames-hydration/bin/
            alt_path = project_root / "backend" / "thames-hydration" / "bin" / exe_name
            if alt_path.exists():
                return alt_path

        return None

    def _get_vcctl_elastic_path(self) -> Optional[Path]:
        """
        Get the path to the VCCTL elastic executable.

        Returns:
            Path to elastic executable, or None if not found
        """
        import sys

        # Platform-specific executable name
        elastic_exe = 'elastic.exe' if sys.platform == 'win32' else 'elastic'

        # Detect if running in PyInstaller bundle
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            bin_dir = Path(sys._MEIPASS) / "bin"
            elastic_path = bin_dir / elastic_exe
            if elastic_path.exists():
                return elastic_path
        else:
            project_root = Path(__file__).parent.parent.parent.parent.parent

            # Primary location: top-level bin/
            elastic_path = project_root / "bin" / elastic_exe
            if elastic_path.exists():
                return elastic_path

            # Fallback: backend/bin/
            fallback_path = project_root / "backend" / "bin" / elastic_exe
            if fallback_path.exists():
                return fallback_path

        return None

    def _get_simparams_path(self, hydration_name: str) -> Optional[Path]:
        """
        Get the path to simparams.json for a hydration operation.

        THAMES elastic calculations require the simparams.json file from
        the hydration operation to get phase elastic moduli.

        Args:
            hydration_name: Name of the hydration operation

        Returns:
            Path to simparams.json, or None if not found
        """
        operations_dir = self.service_container.directories_service.get_operations_path()
        simparams_path = operations_dir / hydration_name / "simparams.json"

        if simparams_path.exists():
            return simparams_path

        # Also check in Result subdirectory
        result_simparams = operations_dir / hydration_name / "Result" / "simparams.json"
        if result_simparams.exists():
            return result_simparams

        return None

    def _get_thames_microstructure_for_elastic(
        self, hydration_name: str, selected_microstructure: HydratedMicrostructure
    ) -> Optional[Path]:
        """
        Get the microstructure file path for THAMES elastic calculation.

        THAMES elastic calculation needs the full path to the .img file.

        Args:
            hydration_name: Name of the hydration operation
            selected_microstructure: Selected microstructure from lineage service

        Returns:
            Path to microstructure file, or None if not found
        """
        if selected_microstructure and selected_microstructure.file_path:
            mic_path = Path(selected_microstructure.file_path)
            if mic_path.exists():
                return mic_path

        # Fallback: look in hydration operation directory
        operations_dir = self.service_container.directories_service.get_operations_path()
        hydration_dir = operations_dir / hydration_name

        # Try Result subdirectory first (THAMES output location)
        result_dir = hydration_dir / "Result"
        if result_dir.exists():
            img_files = list(result_dir.glob("*.img"))
            if img_files:
                # Return the most recently modified
                return max(img_files, key=lambda f: f.stat().st_mtime)

        # Try hydration directory directly
        img_files = list(hydration_dir.glob("*.img"))
        if img_files:
            return max(img_files, key=lambda f: f.stat().st_mtime)

        return None


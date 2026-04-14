#!/usr/bin/env python3
"""
THAMES Hydration Panel

Provides the UI for configuring and running THAMES-Hydration simulations.
This panel uses the THAMES-Hydration C++ engine (not VCCTL's disrealnew).

Key features:
- Select input microstructure from completed operations
- Configure hydration products with interface affinities
- Set time and temperature parameters
- Run and monitor THAMES-Hydration simulations
"""

import gi
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any, List

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib

if TYPE_CHECKING:
    from app.windows.main_window import VCCTLMainWindow

from app.services.service_container import get_service_container
from app.utils.icon_utils import create_button_with_icon
from app.help.panel_help_button import create_panel_help_button
from app.widgets.hydration_product_selector import HydrationProductSelectorWidget
from app.widgets.electrolyte_composition_editor import ElectrolyteCompositionEditor
from app.widgets.kinetic_model_editor import KineticModelEditorDialog
from app.windows.dialogs.affinity_editor_dialog import AffinityEditorDialog
from app.windows.dialogs.csh_config_dialog import CSHConfigDialog
from app.windows.dialogs.phase_config_dialog import PhaseConfigurationDialog
from app.services.hydration_input_service import (
    HydrationInputService,
    HydrationInputConfig,
    MaterialPhaseData,
    get_hydration_input_service,
)
from app.services.thames_execution_service import (
    THAMESExecutionService,
    THAMESSimulationStatus,
    get_thames_execution_service,
)
from app.services.hydration_products_service import get_hydration_products_service
from app.services.phase_id_mapping_service import normalize_phase_name
from app.services.time_generator_service import (
    get_time_generator_service,
    TimeUnit,
    ExponentialBase,
    TimeGenerationResult,
)


class THAMESHydrationPanel(Gtk.Box):
    """
    THAMES Hydration simulation panel.

    Allows users to:
    1. Select an input microstructure from completed operations
    2. Configure hydration products and their interface affinities
    3. Set simulation time and temperature parameters
    4. Run THAMES-Hydration and monitor progress
    """

    def __init__(self, main_window: 'VCCTLMainWindow'):
        """Initialize the THAMES hydration panel."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.main_window = main_window
        self.logger = logging.getLogger('THAMES.HydrationPanel')
        self.service_container = get_service_container()

        # Services
        self.hydration_input_service = get_hydration_input_service()
        self.execution_service = get_thames_execution_service()
        self.products_service = get_hydration_products_service()

        # Panel state
        self.selected_microstructure_path: Optional[Path] = None
        self.selected_operation_name: Optional[str] = None
        self.current_config: Optional[HydrationInputConfig] = None
        self.simulation_running = False
        self.progress_timeout_id = None

        # Setup UI
        self._setup_ui()
        self._connect_signals()

        # Load available microstructures
        self._refresh_microstructure_list()

        self.logger.info("THAMES Hydration panel initialized")

    def _setup_ui(self) -> None:
        """Setup the panel UI."""
        # Create header
        self._create_header()

        # Create main content in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_can_focus(True)  # Enable keyboard navigation

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content_box.set_margin_start(15)
        content_box.set_margin_end(15)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(15)

        # Section 1: Microstructure Selection
        self._create_microstructure_section(content_box)

        # Section 2: Phases (unified list of microstructure phases + hydration products)
        self._create_products_section(content_box)

        # Section 3: Electrolyte Composition
        self._create_electrolyte_section(content_box)

        # Section 4: Time & Temperature
        self._create_time_temp_section(content_box)

        # Section 5: Simulation Controls
        self._create_simulation_controls(content_box)

        scrolled.add(content_box)
        self.pack_start(scrolled, True, True, 0)

    def _create_header(self) -> None:
        """Create the panel header."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        header_box.set_margin_top(10)
        header_box.set_margin_bottom(10)
        header_box.set_margin_start(15)
        header_box.set_margin_end(15)

        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title_label = Gtk.Label()
        title_label.set_markup('<span size="large" weight="bold">THAMES Hydration Simulation</span>')
        title_label.set_halign(Gtk.Align.START)
        title_row.pack_start(title_label, False, False, 0)

        # Help button
        help_button = create_panel_help_button('THAMESHydrationPanel', self.main_window)
        title_row.pack_start(help_button, False, False, 5)

        # Status indicator
        self.status_label = Gtk.Label("Ready")
        self.status_label.set_halign(Gtk.Align.END)
        self.status_label.get_style_context().add_class("dim-label")
        title_row.pack_end(self.status_label, False, False, 0)

        header_box.pack_start(title_row, False, False, 0)

        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup(
            '<span size="small">Configure and run THAMES-Hydration simulations. '
            'Select a microstructure, configure hydration products, and set simulation parameters.</span>'
        )
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_line_wrap(True)
        desc_label.get_style_context().add_class("dim-label")
        header_box.pack_start(desc_label, False, False, 0)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        header_box.pack_start(separator, False, False, 5)

        self.pack_start(header_box, False, False, 0)

    def _create_microstructure_section(self, parent: Gtk.Box) -> None:
        """Create the microstructure selection section with option to load a previous operation."""
        frame = Gtk.Frame()
        frame.set_label("  Input  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Option 1: New simulation from microstructure
        self.input_new_radio = Gtk.RadioButton.new_with_label(
            None, "New simulation from microstructure"
        )
        self.input_new_radio.set_tooltip_text(
            "Start a new hydration simulation by selecting a completed microstructure"
        )
        self.input_new_radio.connect("toggled", self._on_input_mode_toggled)
        content.pack_start(self.input_new_radio, False, False, 0)

        # Microstructure combo box with refresh button (indented under radio)
        self.micro_combo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.micro_combo_box.set_margin_start(24)

        combo_label = Gtk.Label("Microstructure:")
        combo_label.set_size_request(120, -1)
        combo_label.set_halign(Gtk.Align.START)
        self.micro_combo_box.pack_start(combo_label, False, False, 0)

        # ComboBox for microstructures
        self.microstructure_store = Gtk.ListStore(str, str)  # display_name, path
        self.microstructure_combo = Gtk.ComboBox.new_with_model(self.microstructure_store)
        renderer = Gtk.CellRendererText()
        self.microstructure_combo.pack_start(renderer, True)
        self.microstructure_combo.add_attribute(renderer, "text", 0)
        self.microstructure_combo.set_hexpand(True)
        self.micro_combo_box.pack_start(self.microstructure_combo, True, True, 0)

        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_image(Gtk.Image.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON))
        refresh_btn.set_tooltip_text("Refresh microstructure list")
        refresh_btn.connect("clicked", lambda b: self._refresh_microstructure_list())
        self.micro_combo_box.pack_start(refresh_btn, False, False, 0)

        content.pack_start(self.micro_combo_box, False, False, 0)

        # Info about selected microstructure
        self.micro_info_label = Gtk.Label()
        self.micro_info_label.set_halign(Gtk.Align.START)
        self.micro_info_label.set_margin_start(24)
        self.micro_info_label.set_line_wrap(True)
        self.micro_info_label.get_style_context().add_class("dim-label")
        content.pack_start(self.micro_info_label, False, False, 0)

        # Separator
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # Option 2: Load from previous hydration operation
        self.input_load_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.input_new_radio, "Load from previous hydration operation"
        )
        self.input_load_radio.set_tooltip_text(
            "Load all parameters from a previous hydration run, then tweak and re-run"
        )
        self.input_load_radio.connect("toggled", self._on_input_mode_toggled)
        content.pack_start(self.input_load_radio, False, False, 0)

        # Load operation combo (indented under radio)
        self.load_op_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.load_op_box.set_margin_start(24)

        load_label = Gtk.Label("Operation:")
        load_label.set_size_request(120, -1)
        load_label.set_halign(Gtk.Align.START)
        self.load_op_box.pack_start(load_label, False, False, 0)

        # ComboBox for previous hydration operations
        self.load_operation_store = Gtk.ListStore(str, str)  # display_name, config_path
        self.load_operation_combo = Gtk.ComboBox.new_with_model(self.load_operation_store)
        load_renderer = Gtk.CellRendererText()
        self.load_operation_combo.pack_start(load_renderer, True)
        self.load_operation_combo.add_attribute(load_renderer, "text", 0)
        self.load_operation_combo.set_hexpand(True)
        self.load_operation_combo.set_sensitive(False)
        self.load_operation_combo.connect("changed", self._on_load_operation_selected)
        self.load_op_box.pack_start(self.load_operation_combo, True, True, 0)

        # Refresh button for operation list
        load_refresh_btn = Gtk.Button()
        load_refresh_btn.set_image(Gtk.Image.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON))
        load_refresh_btn.set_tooltip_text("Refresh previous operations list")
        load_refresh_btn.connect("clicked", lambda b: self._refresh_load_operation_list())
        self.load_op_box.pack_start(load_refresh_btn, False, False, 0)

        content.pack_start(self.load_op_box, False, False, 0)

        frame.add(content)
        parent.pack_start(frame, False, False, 0)

    def _create_products_section(self, parent: Gtk.Box) -> None:
        """Create the phases selection section (microstructure phases + hydration products)."""
        frame = Gtk.Frame()
        frame.set_label("  Phases  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Instruction label
        instruction = Gtk.Label()
        instruction.set_markup(
            '<span size="small">Microstructure phases (blue, locked) cannot be removed. '
            'Select additional hydration products and edit kinetic parameters as needed.</span>'
        )
        instruction.set_halign(Gtk.Align.START)
        instruction.set_line_wrap(True)
        content.pack_start(instruction, False, False, 0)

        # Phase selector widget (includes microstructure phases + hydration products)
        self.product_selector = HydrationProductSelectorWidget()
        self.product_selector.set_size_request(-1, 350)
        self.product_selector.connect('configure-kinetics', self._on_configure_kinetics)
        content.pack_start(self.product_selector, True, True, 0)

        frame.add(content)
        parent.pack_start(frame, True, True, 0)

    def _create_electrolyte_section(self, parent: Gtk.Box) -> None:
        """Create the electrolyte composition section."""
        frame = Gtk.Frame()
        frame.set_label("  Electrolyte Composition  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Instruction label
        instruction = Gtk.Label()
        instruction.set_markup(
            '<span size="small">Set initial or fixed concentrations of aqueous species. '
            'The charge balance should be zero.</span>'
        )
        instruction.set_halign(Gtk.Align.START)
        instruction.set_line_wrap(True)
        content.pack_start(instruction, False, False, 0)

        # Get GEMS parser for available DCs
        gems_parser = None
        try:
            from pathlib import Path
            gems_data_dir = Path(__file__).parent.parent.parent.parent / "data" / "gems"
            from app.services.gems_parser_service import GEMSParserService
            gems_parser = GEMSParserService(gems_data_dir)
        except Exception as e:
            self.logger.warning(f"Could not get GEMS parser for electrolyte editor: {e}")

        # Electrolyte composition editor widget
        self.electrolyte_editor = ElectrolyteCompositionEditor(gems_parser)
        content.pack_start(self.electrolyte_editor, True, True, 0)

        frame.add(content)
        parent.pack_start(frame, False, False, 0)

    def _create_time_temp_section(self, parent: Gtk.Box) -> None:
        """Create the time and temperature settings section."""
        frame = Gtk.Frame()
        frame.set_label("  Simulation Parameters  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Grid()
        content.set_row_spacing(10)
        content.set_column_spacing(15)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        row = 0

        # Resolution (micrometers per voxel)
        resolution_label = Gtk.Label("Resolution (μm/voxel):")
        resolution_label.set_halign(Gtk.Align.START)
        content.attach(resolution_label, 0, row, 1, 1)

        self.resolution_spin = Gtk.SpinButton.new_with_range(0.1, 10.0, 0.1)
        self.resolution_spin.set_value(1.0)
        self.resolution_spin.set_digits(2)
        self.resolution_spin.set_tooltip_text(
            "Microstructure resolution in micrometers per voxel. "
            "This should match the resolution used when generating the microstructure."
        )
        content.attach(self.resolution_spin, 1, row, 1, 1)

        row += 1

        # Temperature
        temp_label = Gtk.Label("Temperature (°C):")
        temp_label.set_halign(Gtk.Align.START)
        content.attach(temp_label, 0, row, 1, 1)

        self.temperature_spin = Gtk.SpinButton.new_with_range(0, 100, 1)
        self.temperature_spin.set_value(25)
        self.temperature_spin.set_tooltip_text("Simulation temperature in degrees Celsius")
        content.attach(self.temperature_spin, 1, row, 1, 1)

        row += 1

        # Moisture conditions heading
        moisture_heading = Gtk.Label()
        moisture_heading.set_markup("<b>Moisture Conditions</b>")
        moisture_heading.set_halign(Gtk.Align.START)
        moisture_heading.set_margin_top(10)
        content.attach(moisture_heading, 0, row, 2, 1)

        row += 1

        # Saturated radio button
        self.saturated_radio = Gtk.RadioButton.new_with_label(None, "Saturated")
        self.saturated_radio.set_tooltip_text(
            "Water is continuously available to maintain saturation"
        )
        content.attach(self.saturated_radio, 0, row, 1, 1)

        # Sealed radio button (same group as saturated)
        self.sealed_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.saturated_radio, "Sealed"
        )
        self.sealed_radio.set_tooltip_text(
            "No external water; system uses only the initial water content"
        )
        content.attach(self.sealed_radio, 1, row, 1, 1)

        # Default to saturated
        self.saturated_radio.set_active(True)

        row += 1

        # Time parameters heading
        time_heading = Gtk.Label()
        time_heading.set_markup("<b>Time Parameters</b>")
        time_heading.set_halign(Gtk.Align.START)
        time_heading.set_margin_top(10)
        content.attach(time_heading, 0, row, 2, 1)

        row += 1

        # Final time with unit selector
        time_label = Gtk.Label("Final Time:")
        time_label.set_halign(Gtk.Align.START)
        content.attach(time_label, 0, row, 1, 1)

        final_time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.final_time_spin = Gtk.SpinButton.new_with_range(0.1, 365, 0.1)
        self.final_time_spin.set_value(28)
        self.final_time_spin.set_digits(2)
        self.final_time_spin.set_tooltip_text("Total simulation time")
        self.final_time_spin.connect("value-changed", self._on_time_param_changed)
        final_time_box.pack_start(self.final_time_spin, True, True, 0)

        self.final_time_unit_combo = Gtk.ComboBoxText()
        self.final_time_unit_combo.append("s", "seconds")
        self.final_time_unit_combo.append("min", "minutes")
        self.final_time_unit_combo.append("hr", "hours")
        self.final_time_unit_combo.append("d", "days")
        self.final_time_unit_combo.set_active_id("d")
        self.final_time_unit_combo.set_tooltip_text("Unit for final time")
        self.final_time_unit_combo.connect("changed", self._on_final_time_unit_changed)
        final_time_box.pack_start(self.final_time_unit_combo, False, False, 0)
        content.attach(final_time_box, 1, row, 1, 1)

        row += 1

        # Output time model selector
        model_label = Gtk.Label("Output Time Model:")
        model_label.set_halign(Gtk.Align.START)
        content.attach(model_label, 0, row, 1, 1)

        self.output_model_combo = Gtk.ComboBoxText()
        self.output_model_combo.append("custom", "Custom List")
        self.output_model_combo.append("linear_count", "Linear (by count)")
        self.output_model_combo.append("linear_spacing", "Linear (by spacing)")
        self.output_model_combo.append("exponential", "Exponential")
        self.output_model_combo.set_active_id("custom")
        self.output_model_combo.set_tooltip_text("Method for generating output times")
        self.output_model_combo.connect("changed", self._on_output_model_changed)
        content.attach(self.output_model_combo, 1, row, 1, 1)

        row += 1

        # Stack for model-specific parameters
        self.time_model_stack = Gtk.Stack()
        self.time_model_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content.attach(self.time_model_stack, 0, row, 2, 1)

        # Custom model UI
        custom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        custom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        custom_label = Gtk.Label("Times:")
        custom_label.set_halign(Gtk.Align.START)
        custom_label.set_size_request(100, -1)
        custom_row.pack_start(custom_label, False, False, 0)

        self.custom_times_entry = Gtk.Entry()
        self.custom_times_entry.set_text("0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28")
        self.custom_times_entry.set_tooltip_text("Comma-separated list of output times")
        self.custom_times_entry.set_hexpand(True)
        self.custom_times_entry.connect("changed", self._on_time_param_changed)
        custom_row.pack_start(self.custom_times_entry, True, True, 0)

        self.custom_times_unit_combo = Gtk.ComboBoxText()
        self.custom_times_unit_combo.append("s", "s")
        self.custom_times_unit_combo.append("min", "min")
        self.custom_times_unit_combo.append("hr", "hr")
        self.custom_times_unit_combo.append("d", "d")
        self.custom_times_unit_combo.set_active_id("d")
        self.custom_times_unit_combo.connect("changed", self._on_time_param_changed)
        custom_row.pack_start(self.custom_times_unit_combo, False, False, 0)
        custom_box.pack_start(custom_row, False, False, 0)
        self.time_model_stack.add_named(custom_box, "custom")

        # Linear by count UI
        linear_count_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        linear_count_label = Gtk.Label("Number of outputs:")
        linear_count_label.set_halign(Gtk.Align.START)
        linear_count_label.set_size_request(100, -1)
        linear_count_box.pack_start(linear_count_label, False, False, 0)

        self.linear_count_spin = Gtk.SpinButton.new_with_range(2, 100, 1)
        self.linear_count_spin.set_value(10)
        self.linear_count_spin.set_tooltip_text("Number of evenly-spaced output times (2-100)")
        self.linear_count_spin.connect("value-changed", self._on_time_param_changed)
        linear_count_box.pack_start(self.linear_count_spin, False, False, 0)

        linear_count_note = Gtk.Label("(includes start and end)")
        linear_count_note.get_style_context().add_class("dim-label")
        linear_count_box.pack_start(linear_count_note, False, False, 5)
        self.time_model_stack.add_named(linear_count_box, "linear_count")

        # Linear by spacing UI
        linear_spacing_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        linear_spacing_label = Gtk.Label("Time spacing:")
        linear_spacing_label.set_halign(Gtk.Align.START)
        linear_spacing_label.set_size_request(100, -1)
        linear_spacing_box.pack_start(linear_spacing_label, False, False, 0)

        self.linear_spacing_spin = Gtk.SpinButton.new_with_range(0.001, 100, 0.1)
        self.linear_spacing_spin.set_value(1.0)
        self.linear_spacing_spin.set_digits(3)
        self.linear_spacing_spin.set_tooltip_text("Time between outputs (max 100 outputs)")
        self.linear_spacing_spin.connect("value-changed", self._on_time_param_changed)
        linear_spacing_box.pack_start(self.linear_spacing_spin, False, False, 0)

        self.linear_spacing_unit_combo = Gtk.ComboBoxText()
        self.linear_spacing_unit_combo.append("s", "s")
        self.linear_spacing_unit_combo.append("min", "min")
        self.linear_spacing_unit_combo.append("hr", "hr")
        self.linear_spacing_unit_combo.append("d", "d")
        self.linear_spacing_unit_combo.set_active_id("d")
        self.linear_spacing_unit_combo.connect("changed", self._on_time_param_changed)
        linear_spacing_box.pack_start(self.linear_spacing_unit_combo, False, False, 0)
        self.time_model_stack.add_named(linear_spacing_box, "linear_spacing")

        # Exponential UI
        exp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)

        # t0 row
        exp_t0_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        exp_t0_label = Gtk.Label("t₀ (start time):")
        exp_t0_label.set_halign(Gtk.Align.START)
        exp_t0_label.set_size_request(100, -1)
        exp_t0_row.pack_start(exp_t0_label, False, False, 0)

        self.exp_t0_spin = Gtk.SpinButton.new_with_range(0.0001, 10, 0.001)
        self.exp_t0_spin.set_value(0.01)
        self.exp_t0_spin.set_digits(4)
        self.exp_t0_spin.set_tooltip_text("Starting time (t = t₀ × base^(a×i))")
        self.exp_t0_spin.connect("value-changed", self._on_time_param_changed)
        exp_t0_row.pack_start(self.exp_t0_spin, False, False, 0)

        self.exp_t0_unit_combo = Gtk.ComboBoxText()
        self.exp_t0_unit_combo.append("s", "s")
        self.exp_t0_unit_combo.append("min", "min")
        self.exp_t0_unit_combo.append("hr", "hr")
        self.exp_t0_unit_combo.append("d", "d")
        self.exp_t0_unit_combo.set_active_id("d")
        self.exp_t0_unit_combo.connect("changed", self._on_time_param_changed)
        exp_t0_row.pack_start(self.exp_t0_unit_combo, False, False, 0)
        exp_box.pack_start(exp_t0_row, False, False, 0)

        # Strength and steps row
        exp_params_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        exp_a_label = Gtk.Label("Strength (a):")
        exp_a_label.set_halign(Gtk.Align.START)
        exp_a_label.set_size_request(100, -1)
        exp_params_row.pack_start(exp_a_label, False, False, 0)

        self.exp_strength_spin = Gtk.SpinButton.new_with_range(0.001, 1.0, 0.01)
        self.exp_strength_spin.set_value(0.1)
        self.exp_strength_spin.set_digits(3)
        self.exp_strength_spin.set_tooltip_text("Strength parameter (0 < a ≤ 1.0)")
        self.exp_strength_spin.connect("value-changed", self._on_time_param_changed)
        exp_params_row.pack_start(self.exp_strength_spin, False, False, 0)

        exp_steps_label = Gtk.Label("   Steps:")
        exp_params_row.pack_start(exp_steps_label, False, False, 0)

        self.exp_steps_spin = Gtk.SpinButton.new_with_range(2, 100, 1)
        self.exp_steps_spin.set_value(20)
        self.exp_steps_spin.set_tooltip_text("Number of time steps (max 100)")
        self.exp_steps_spin.connect("value-changed", self._on_time_param_changed)
        exp_params_row.pack_start(self.exp_steps_spin, False, False, 0)
        exp_box.pack_start(exp_params_row, False, False, 0)

        # Base row
        exp_base_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        exp_base_label = Gtk.Label("Base:")
        exp_base_label.set_halign(Gtk.Align.START)
        exp_base_label.set_size_request(100, -1)
        exp_base_row.pack_start(exp_base_label, False, False, 0)

        self.exp_base_e_radio = Gtk.RadioButton.new_with_label(None, "e (natural)")
        self.exp_base_e_radio.connect("toggled", self._on_time_param_changed)
        exp_base_row.pack_start(self.exp_base_e_radio, False, False, 0)

        self.exp_base_10_radio = Gtk.RadioButton.new_with_label_from_widget(
            self.exp_base_e_radio, "10"
        )
        self.exp_base_10_radio.connect("toggled", self._on_time_param_changed)
        exp_base_row.pack_start(self.exp_base_10_radio, False, False, 10)
        exp_box.pack_start(exp_base_row, False, False, 0)

        self.time_model_stack.add_named(exp_box, "exponential")

        # Show initial model
        self.time_model_stack.set_visible_child_name("custom")

        row += 1

        # Additional exact times
        exact_label = Gtk.Label("Additional Exact Times:")
        exact_label.set_halign(Gtk.Align.START)
        exact_label.set_tooltip_text("Extra times to include (merged with model output)")
        content.attach(exact_label, 0, row, 1, 1)

        exact_times_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.exact_times_entry = Gtk.Entry()
        self.exact_times_entry.set_placeholder_text("e.g., 0.5, 7, 28")
        self.exact_times_entry.set_tooltip_text(
            "Comma-separated times to add to the model sequence (optional)"
        )
        self.exact_times_entry.set_hexpand(True)
        self.exact_times_entry.connect("changed", self._on_time_param_changed)
        exact_times_box.pack_start(self.exact_times_entry, True, True, 0)

        self.exact_times_unit_combo = Gtk.ComboBoxText()
        self.exact_times_unit_combo.append("s", "s")
        self.exact_times_unit_combo.append("min", "min")
        self.exact_times_unit_combo.append("hr", "hr")
        self.exact_times_unit_combo.append("d", "d")
        self.exact_times_unit_combo.set_active_id("d")
        self.exact_times_unit_combo.connect("changed", self._on_time_param_changed)
        exact_times_box.pack_start(self.exact_times_unit_combo, False, False, 0)
        content.attach(exact_times_box, 1, row, 1, 1)

        row += 1

        # Preview area
        preview_label = Gtk.Label("Preview:")
        preview_label.set_halign(Gtk.Align.START)
        preview_label.set_valign(Gtk.Align.START)
        preview_label.set_margin_top(5)
        content.attach(preview_label, 0, row, 1, 1)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        # Preview text (scrollable)
        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        preview_scroll.set_min_content_height(60)
        preview_scroll.set_max_content_height(80)

        self.time_preview_text = Gtk.TextView()
        self.time_preview_text.set_editable(False)
        self.time_preview_text.set_cursor_visible(False)
        self.time_preview_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.time_preview_text.get_buffer().set_text(
            "0.01 d, 0.1 d, 0.25 d, 0.5 d, 1 d, 3 d, 7 d, 14 d, 21 d, 28 d"
        )
        preview_scroll.add(self.time_preview_text)
        preview_box.pack_start(preview_scroll, True, True, 0)

        # Count and validation label
        self.time_count_label = Gtk.Label()
        self.time_count_label.set_halign(Gtk.Align.START)
        self.time_count_label.set_markup("<small>10 output times</small>")
        preview_box.pack_start(self.time_count_label, False, False, 0)

        content.attach(preview_box, 1, row, 1, 1)

        row += 1

        # Adaptive time stepping heading
        adaptive_heading = Gtk.Label()
        adaptive_heading.set_markup("<b>Adaptive Time Stepping</b>")
        adaptive_heading.set_halign(Gtk.Align.START)
        adaptive_heading.set_margin_top(10)
        content.attach(adaptive_heading, 0, row, 2, 1)

        row += 1

        # Enable checkbox
        self.adaptive_enabled_check = Gtk.CheckButton.new_with_label(
            "Enable adaptive time stepping"
        )
        self.adaptive_enabled_check.set_active(True)
        self.adaptive_enabled_check.set_tooltip_text(
            "When enabled, the simulation dynamically adjusts time step size based on "
            "GEMS solver performance. When disabled, uses pre-generated fixed time steps."
        )
        self.adaptive_enabled_check.connect("toggled", self._on_adaptive_enabled_toggled)
        content.attach(self.adaptive_enabled_check, 0, row, 2, 1)

        row += 1

        # Expander for detailed parameters (collapsed by default)
        self.adaptive_expander = Gtk.Expander(label="Advanced Parameters")
        self.adaptive_expander.set_expanded(False)
        self.adaptive_expander.set_margin_start(20)

        adaptive_grid = Gtk.Grid()
        adaptive_grid.set_row_spacing(8)
        adaptive_grid.set_column_spacing(15)
        adaptive_grid.set_margin_top(8)
        adaptive_grid.set_margin_bottom(5)

        arow = 0

        # dt_initial
        dt_init_label = Gtk.Label("Initial time step:")
        dt_init_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(dt_init_label, 0, arow, 1, 1)

        dt_init_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.adaptive_dt_initial_spin = Gtk.SpinButton.new_with_range(0.001, 3600.0, 0.1)
        self.adaptive_dt_initial_spin.set_value(3.6)
        self.adaptive_dt_initial_spin.set_digits(4)
        self.adaptive_dt_initial_spin.set_tooltip_text(
            "Starting time step size. Default: 3.6 seconds (0.001 hours). "
            "May be overridden by kinetics-based estimate at startup."
        )
        dt_init_box.pack_start(self.adaptive_dt_initial_spin, True, True, 0)

        self.adaptive_dt_initial_unit_combo = Gtk.ComboBoxText()
        self.adaptive_dt_initial_unit_combo.append("s", "seconds")
        self.adaptive_dt_initial_unit_combo.append("min", "minutes")
        self.adaptive_dt_initial_unit_combo.append("hr", "hours")
        self.adaptive_dt_initial_unit_combo.set_active_id("s")
        self.adaptive_dt_initial_unit_combo.connect(
            "changed", self._on_adaptive_dt_unit_changed, "initial"
        )
        dt_init_box.pack_start(self.adaptive_dt_initial_unit_combo, False, False, 0)
        adaptive_grid.attach(dt_init_box, 1, arow, 1, 1)

        arow += 1

        # dt_max
        dt_max_label = Gtk.Label("Maximum time step:")
        dt_max_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(dt_max_label, 0, arow, 1, 1)

        dt_max_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.adaptive_dt_max_spin = Gtk.SpinButton.new_with_range(0.1, 48.0, 0.5)
        self.adaptive_dt_max_spin.set_value(4.0)
        self.adaptive_dt_max_spin.set_digits(4)
        self.adaptive_dt_max_spin.set_tooltip_text(
            "Maximum allowed time step. Default: 4.0 hours."
        )
        dt_max_box.pack_start(self.adaptive_dt_max_spin, True, True, 0)

        self.adaptive_dt_max_unit_combo = Gtk.ComboBoxText()
        self.adaptive_dt_max_unit_combo.append("s", "seconds")
        self.adaptive_dt_max_unit_combo.append("min", "minutes")
        self.adaptive_dt_max_unit_combo.append("hr", "hours")
        self.adaptive_dt_max_unit_combo.set_active_id("hr")
        self.adaptive_dt_max_unit_combo.connect(
            "changed", self._on_adaptive_dt_unit_changed, "max"
        )
        dt_max_box.pack_start(self.adaptive_dt_max_unit_combo, False, False, 0)
        adaptive_grid.attach(dt_max_box, 1, arow, 1, 1)

        arow += 1

        # growth_factor
        growth_label = Gtk.Label("Growth factor:")
        growth_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(growth_label, 0, arow, 1, 1)

        self.adaptive_growth_spin = Gtk.SpinButton.new_with_range(1.01, 5.0, 0.1)
        self.adaptive_growth_spin.set_value(1.5)
        self.adaptive_growth_spin.set_digits(4)
        self.adaptive_growth_spin.set_tooltip_text(
            "Time step multiplier after consecutive successes. Default: 1.5 (50% growth)."
        )
        adaptive_grid.attach(self.adaptive_growth_spin, 1, arow, 1, 1)

        arow += 1

        # shrink_factor
        shrink_label = Gtk.Label("Shrink factor:")
        shrink_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(shrink_label, 0, arow, 1, 1)

        self.adaptive_shrink_spin = Gtk.SpinButton.new_with_range(0.01, 0.99, 0.05)
        self.adaptive_shrink_spin.set_value(0.5)
        self.adaptive_shrink_spin.set_digits(4)
        self.adaptive_shrink_spin.set_tooltip_text(
            "Time step multiplier after GEMS failure. Default: 0.5 (halve time step)."
        )
        adaptive_grid.attach(self.adaptive_shrink_spin, 1, arow, 1, 1)

        arow += 1

        # successes_for_growth
        successes_label = Gtk.Label("Successes before growth:")
        successes_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(successes_label, 0, arow, 1, 1)

        self.adaptive_successes_spin = Gtk.SpinButton.new_with_range(1, 20, 1)
        self.adaptive_successes_spin.set_value(2)
        self.adaptive_successes_spin.set_digits(0)
        self.adaptive_successes_spin.set_tooltip_text(
            "Number of consecutive GEMS successes required before growing time step. Default: 2."
        )
        adaptive_grid.attach(self.adaptive_successes_spin, 1, arow, 1, 1)

        arow += 1

        # max_consecutive_failures
        failures_label = Gtk.Label("Max consecutive failures:")
        failures_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(failures_label, 0, arow, 1, 1)

        self.adaptive_max_failures_spin = Gtk.SpinButton.new_with_range(5, 500, 5)
        self.adaptive_max_failures_spin.set_value(50)
        self.adaptive_max_failures_spin.set_digits(0)
        self.adaptive_max_failures_spin.set_tooltip_text(
            "Simulation terminates after this many consecutive GEMS failures. Default: 50."
        )
        adaptive_grid.attach(self.adaptive_max_failures_spin, 1, arow, 1, 1)

        arow += 1

        # max_relative_change
        max_change_label = Gtk.Label("Max relative change per step:")
        max_change_label.set_halign(Gtk.Align.START)
        adaptive_grid.attach(max_change_label, 0, arow, 1, 1)

        self.adaptive_max_change_spin = Gtk.SpinButton.new_with_range(0.001, 0.5, 0.01)
        self.adaptive_max_change_spin.set_value(0.05)
        self.adaptive_max_change_spin.set_digits(4)
        self.adaptive_max_change_spin.set_tooltip_text(
            "Maximum fractional change in DC moles per time step (kinetics constraint). "
            "Default: 0.05 (5%). Lower values are more conservative."
        )
        adaptive_grid.attach(self.adaptive_max_change_spin, 1, arow, 1, 1)

        self.adaptive_expander.add(adaptive_grid)
        content.attach(self.adaptive_expander, 0, row, 2, 1)

        # Store all adaptive SpinButtons for sensitivity toggling
        self._adaptive_spin_buttons = [
            self.adaptive_dt_initial_spin,
            self.adaptive_dt_max_spin,
            self.adaptive_growth_spin,
            self.adaptive_shrink_spin,
            self.adaptive_successes_spin,
            self.adaptive_max_failures_spin,
            self.adaptive_max_change_spin,
        ]

        row += 1

        # Output options heading
        output_heading = Gtk.Label()
        output_heading.set_markup("<b>Output Options</b>")
        output_heading.set_halign(Gtk.Align.START)
        output_heading.set_margin_top(10)
        content.attach(output_heading, 0, row, 2, 1)

        row += 1

        # Create XYZ files checkbox (for Ovito visualization)
        self.create_xyz_check = Gtk.CheckButton.new_with_label(
            "Create 3D visualization files (Ovito)"
        )
        self.create_xyz_check.set_tooltip_text(
            "Generate XYZ files for 3D visualization in Ovito or similar software"
        )
        content.attach(self.create_xyz_check, 0, row, 2, 1)

        row += 1

        # Verbose output checkbox
        self.verbose_check = Gtk.CheckButton.new_with_label("Verbose output")
        self.verbose_check.set_tooltip_text(
            "Produce detailed output during simulation (useful for debugging)"
        )
        content.attach(self.verbose_check, 0, row, 1, 1)

        # Suppress warnings checkbox
        self.suppress_warnings_check = Gtk.CheckButton.new_with_label("Suppress warnings")
        self.suppress_warnings_check.set_tooltip_text(
            "Suppress warning messages during simulation"
        )
        content.attach(self.suppress_warnings_check, 1, row, 1, 1)

        frame.add(content)
        parent.pack_start(frame, False, False, 0)

    def _create_simulation_controls(self, parent: Gtk.Box) -> None:
        """Create the simulation control buttons and progress area."""
        frame = Gtk.Frame()
        frame.set_label("  Simulation  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Operation name
        name_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        name_label = Gtk.Label("Operation Name:")
        name_label.set_size_request(120, -1)
        name_label.set_halign(Gtk.Align.START)
        name_row.pack_start(name_label, False, False, 0)

        self.operation_name_entry = Gtk.Entry()
        self.operation_name_entry.set_placeholder_text("Enter operation name...")
        self.operation_name_entry.set_hexpand(True)
        name_row.pack_start(self.operation_name_entry, True, True, 0)

        content.pack_start(name_row, False, False, 0)

        # Microstructure reference label (shows selected microstructure name for easy reference)
        micro_ref_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        spacer_label = Gtk.Label("")
        spacer_label.set_size_request(120, -1)  # Match the "Operation Name:" label width
        micro_ref_row.pack_start(spacer_label, False, False, 0)

        self.microstructure_ref_label = Gtk.Label("")
        self.microstructure_ref_label.set_halign(Gtk.Align.START)
        self.microstructure_ref_label.get_style_context().add_class("dim-label")
        micro_ref_row.pack_start(self.microstructure_ref_label, True, True, 0)

        content.pack_start(micro_ref_row, False, False, 0)

        # Control buttons
        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_row.set_halign(Gtk.Align.CENTER)

        self.validate_btn = Gtk.Button.new_with_label("Validate")
        self.validate_btn.set_tooltip_text("Validate configuration before running")
        self.validate_btn.connect("clicked", self._on_validate_clicked)
        button_row.pack_start(self.validate_btn, False, False, 0)

        self.run_btn = Gtk.Button.new_with_label("Run Simulation")
        self.run_btn.get_style_context().add_class("suggested-action")
        self.run_btn.set_tooltip_text("Start the hydration simulation")
        self.run_btn.connect("clicked", self._on_run_clicked)
        button_row.pack_start(self.run_btn, False, False, 0)

        self.cancel_btn = Gtk.Button.new_with_label("Cancel")
        self.cancel_btn.get_style_context().add_class("destructive-action")
        self.cancel_btn.set_tooltip_text("Cancel the running simulation")
        self.cancel_btn.connect("clicked", self._on_cancel_clicked)
        self.cancel_btn.set_sensitive(False)
        button_row.pack_start(self.cancel_btn, False, False, 0)

        content.pack_start(button_row, False, False, 0)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Ready")
        content.pack_start(self.progress_bar, False, False, 0)

        # Log/status area
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        log_scroll.set_size_request(-1, 100)
        log_scroll.set_can_focus(True)  # Enable keyboard navigation

        self.log_buffer = Gtk.TextBuffer()
        self.log_view = Gtk.TextView.new_with_buffer(self.log_buffer)
        self.log_view.set_editable(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.set_monospace(True)
        log_scroll.add(self.log_view)

        content.pack_start(log_scroll, True, True, 0)

        frame.add(content)
        parent.pack_start(frame, False, False, 0)

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.microstructure_combo.connect("changed", self._on_microstructure_changed)
        self.product_selector.connect("configure-phase", self._on_configure_phase)
        self.product_selector.connect("configure-affinity", self._on_configure_affinity)
        self.product_selector.connect("configure-csh", self._on_configure_csh)

    def _refresh_microstructure_list(self) -> None:
        """Refresh the list of available microstructures."""
        self.microstructure_store.clear()

        try:
            # Get operations directory
            ops_dir = self.service_container.directories_service.get_operations_path()

            if not ops_dir.exists():
                self.logger.warning(f"Operations directory does not exist: {ops_dir}")
                return

            # Find completed microstructure operations
            # Look for both THAMES (.thames.img) and VCCTL (.img) formats
            found_files = set()  # Track to avoid duplicates

            for op_dir in ops_dir.iterdir():
                if not op_dir.is_dir():
                    continue

                # Pattern 1: THAMES format - {name}.thames.img
                for mic_file in op_dir.glob("*.thames.img"):
                    if str(mic_file) not in found_files:
                        display_name = f"{op_dir.name} / {mic_file.name}"
                        self.microstructure_store.append([display_name, str(mic_file)])
                        found_files.add(str(mic_file))
                        self.logger.debug(f"Found THAMES microstructure: {display_name}")

                # Pattern 2: VCCTL format - {name}.img (but not .thames.img)
                for mic_file in op_dir.glob("*.img"):
                    # Skip if it's a THAMES file (already found) or a time-series file
                    if ".thames.img" in mic_file.name:
                        continue
                    # Skip hydration output files (contain 'h.' pattern like .img.25h.100)
                    if "h." in mic_file.name or "HydrationOf_" in mic_file.name:
                        continue
                    if str(mic_file) not in found_files:
                        display_name = f"{op_dir.name} / {mic_file.name}"
                        self.microstructure_store.append([display_name, str(mic_file)])
                        found_files.add(str(mic_file))
                        self.logger.debug(f"Found VCCTL microstructure: {display_name}")

            if len(self.microstructure_store) == 0:
                self._log_message("No microstructure files found. Generate a microstructure first.")
            else:
                self._log_message(f"Found {len(self.microstructure_store)} microstructure(s)")

        except Exception as e:
            self.logger.error(f"Error refreshing microstructure list: {e}")
            self._log_message(f"Error: {e}")

    # =========================================================================
    # Time Parameter Handlers
    # =========================================================================

    def _get_unit_from_combo_id(self, combo_id: str) -> TimeUnit:
        """Convert combo box ID to TimeUnit enum."""
        unit_map = {
            "s": TimeUnit.SECONDS,
            "min": TimeUnit.MINUTES,
            "hr": TimeUnit.HOURS,
            "d": TimeUnit.DAYS,
        }
        return unit_map.get(combo_id, TimeUnit.DAYS)

    def _convert_to_hours(self, value: float, unit_combo_id: str) -> float:
        """Convert a time value from the given unit to hours."""
        conversions = {"s": 1.0 / 3600, "min": 1.0 / 60, "hr": 1.0}
        return value * conversions.get(unit_combo_id, 1.0)

    def _on_adaptive_dt_unit_changed(self, combo, which):
        """Update SpinButton range/value when adaptive dt unit changes."""
        unit_id = combo.get_active_id()
        if which == "initial":
            spin = self.adaptive_dt_initial_spin
            # Default value in each unit: 0.001 hours = 0.06 min = 3.6 sec
            defaults = {"s": (0.001, 3600.0, 0.1, 4, 3.6),
                        "min": (0.001, 60.0, 0.01, 4, 0.06),
                        "hr": (0.00001, 1.0, 0.0001, 5, 0.001)}
        else:
            spin = self.adaptive_dt_max_spin
            # Default value in each unit: 4.0 hours = 240 min = 14400 sec
            defaults = {"s": (0.001, 172800.0, 10.0, 4, 14400.0),
                        "min": (0.1, 2880.0, 1.0, 4, 240.0),
                        "hr": (0.1, 48.0, 0.5, 4, 4.0)}
        if unit_id in defaults:
            lo, hi, step, digits, default = defaults[unit_id]
            spin.set_range(lo, hi)
            spin.set_increments(step, step * 10)
            spin.set_digits(digits)
            spin.set_value(default)

    def _on_output_model_changed(self, combo: Gtk.ComboBoxText) -> None:
        """Handle output time model selection change."""
        model_id = combo.get_active_id()
        if model_id:
            self.time_model_stack.set_visible_child_name(model_id)
            self._update_time_preview()

    def _on_time_param_changed(self, widget) -> None:
        """Handle any time parameter change - update preview."""
        # Debounce rapid changes using idle_add
        if hasattr(self, '_time_update_pending') and self._time_update_pending:
            return
        self._time_update_pending = True
        GLib.idle_add(self._do_time_preview_update)

    def _on_final_time_unit_changed(self, widget) -> None:
        """Handle final time unit change - sync spacing unit and update preview."""
        # Sync linear spacing unit to match final time unit
        new_unit_id = self.final_time_unit_combo.get_active_id()
        if new_unit_id and hasattr(self, 'linear_spacing_unit_combo'):
            self.linear_spacing_unit_combo.set_active_id(new_unit_id)
        # Then update preview
        self._on_time_param_changed(widget)

    def _on_adaptive_enabled_toggled(self, check_button: Gtk.CheckButton) -> None:
        """Handle adaptive time stepping enable/disable toggle."""
        enabled = check_button.get_active()
        self.adaptive_expander.set_sensitive(enabled)

    def _do_time_preview_update(self) -> bool:
        """Actually perform the preview update (called from idle)."""
        self._time_update_pending = False
        self._update_time_preview()
        return False  # Don't repeat

    def _get_final_time_days(self) -> float:
        """Get final time converted to days."""
        value = self.final_time_spin.get_value()
        unit_id = self.final_time_unit_combo.get_active_id()
        unit = self._get_unit_from_combo_id(unit_id)
        service = get_time_generator_service()
        return service.convert_to_days(value, unit)

    def _generate_output_times(self) -> TimeGenerationResult:
        """Generate output times based on current UI settings."""
        service = get_time_generator_service()
        model = self.output_model_combo.get_active_id() or "custom"
        final_time_days = self._get_final_time_days()

        # Parse additional exact times
        exact_times_days = []
        exact_text = self.exact_times_entry.get_text().strip()
        if exact_text:
            exact_unit_id = self.exact_times_unit_combo.get_active_id()
            exact_unit = self._get_unit_from_combo_id(exact_unit_id)
            exact_times_days, _ = service.parse_custom_times(exact_text, exact_unit)

        # Generate based on model
        if model == "custom":
            custom_text = self.custom_times_entry.get_text()
            custom_unit_id = self.custom_times_unit_combo.get_active_id()
            custom_unit = self._get_unit_from_combo_id(custom_unit_id)
            custom_times, error = service.parse_custom_times(custom_text, custom_unit)
            if error:
                return TimeGenerationResult(
                    times_days=[], model_times_days=[], exact_times_days=[],
                    exact_time_indices=[], warnings=[], error=error
                )
            return service.generate_output_times(
                model="custom",
                final_time_days=final_time_days,
                exact_times_days=exact_times_days,
                custom_times_days=custom_times,
            )

        elif model == "linear_count":
            num_outputs = int(self.linear_count_spin.get_value())
            return service.generate_output_times(
                model="linear_count",
                final_time_days=final_time_days,
                exact_times_days=exact_times_days,
                linear_count=num_outputs,
            )

        elif model == "linear_spacing":
            spacing_value = self.linear_spacing_spin.get_value()
            spacing_unit_id = self.linear_spacing_unit_combo.get_active_id()
            spacing_unit = self._get_unit_from_combo_id(spacing_unit_id)
            spacing_days = service.convert_to_days(spacing_value, spacing_unit)
            return service.generate_output_times(
                model="linear_spacing",
                final_time_days=final_time_days,
                exact_times_days=exact_times_days,
                linear_spacing_days=spacing_days,
            )

        elif model == "exponential":
            t0_value = self.exp_t0_spin.get_value()
            t0_unit_id = self.exp_t0_unit_combo.get_active_id()
            t0_unit = self._get_unit_from_combo_id(t0_unit_id)
            t0_days = service.convert_to_days(t0_value, t0_unit)

            strength = self.exp_strength_spin.get_value()
            num_steps = int(self.exp_steps_spin.get_value())
            base = ExponentialBase.E if self.exp_base_e_radio.get_active() else ExponentialBase.TEN

            return service.generate_output_times(
                model="exponential",
                final_time_days=final_time_days,
                exact_times_days=exact_times_days,
                exp_t0_days=t0_days,
                exp_strength=strength,
                exp_num_steps=num_steps,
                exp_base=base,
            )

        # Fallback
        return TimeGenerationResult(
            times_days=[], model_times_days=[], exact_times_days=[],
            exact_time_indices=[], warnings=[], error=f"Unknown model: {model}"
        )

    def _update_time_preview(self) -> None:
        """Update the time preview display based on current UI settings."""
        service = get_time_generator_service()
        result = self._generate_output_times()

        # Update preview text
        if result.error:
            preview_text = f"Error: {result.error}"
            count_text = "<small><span foreground='red'>Invalid configuration</span></small>"
        else:
            preview_text = service.format_times_for_preview(
                result.times_days,
                result.exact_time_indices,
                max_display=25
            )
            count = len(result.times_days)

            # Format count with appropriate styling
            if count > 200:
                count_text = f"<small><span foreground='red'>{count} output times (exceeds maximum of 200)</span></small>"
            elif count > 100:
                count_text = f"<small><span foreground='orange'>{count} output times (warning: large number may slow simulation)</span></small>"
            else:
                count_text = f"<small>{count} output times</small>"

            # Add warning for exact times
            if result.exact_time_indices:
                count_text += f" <small>(* = exact times)</small>"

        self.time_preview_text.get_buffer().set_text(preview_text)
        self.time_count_label.set_markup(count_text)

    def _on_input_mode_toggled(self, radio: Gtk.RadioButton) -> None:
        """Handle input mode radio button toggle."""
        new_sim = self.input_new_radio.get_active()
        # Enable/disable the microstructure combo vs load operation combo
        self.micro_combo_box.set_sensitive(new_sim)
        self.load_operation_combo.set_sensitive(not new_sim)
        if not new_sim:
            self._refresh_load_operation_list()

    def _on_microstructure_changed(self, combo: Gtk.ComboBox) -> None:
        """Handle microstructure selection change."""
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            self.selected_microstructure_path = None
            self.selected_operation_name = None
            self.micro_info_label.set_text("")
            self.microstructure_ref_label.set_text("")
            # Clear microstructure phases from product selector
            self.product_selector.clear_microstructure_phases()
            return

        model = combo.get_model()
        display_name = model[tree_iter][0]
        path_str = model[tree_iter][1]

        self.selected_microstructure_path = Path(path_str)
        self.selected_operation_name = self.selected_microstructure_path.parent.name

        # Update reference label with microstructure operation name
        self.microstructure_ref_label.set_markup(
            f"<small>Microstructure: {self.selected_operation_name}</small>"
        )

        # Show info about selected microstructure
        try:
            size = self.selected_microstructure_path.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"
            self.micro_info_label.set_text(f"Selected: {self.selected_microstructure_path.name} ({size_str})")

            # Try to load phase mapping if available
            phase_mapping_path = self.selected_microstructure_path.parent / f"{self.selected_operation_name}_phase_mapping.json"
            if phase_mapping_path.exists():
                with open(phase_mapping_path, 'r') as f:
                    mapping = json.load(f)

                # Extract phase names from the mapping (excluding VOID and Electrolyte)
                # Handle nested structure: phase_id_mapping.micro_to_gem
                phase_id_mapping = mapping.get('phase_id_mapping', mapping)
                micro_to_gem = phase_id_mapping.get('micro_to_gem', {})
                # Note: Aggregate phases (e.g., Quartz) are now included so users can set kinetics
                excluded = {'VOID', 'Electrolyte', 'aq_gen', 'gas_gen'}
                # Normalize phase names to handle case variations (arcanite -> Arcanite)
                # and use a set to remove duplicates that result from normalization
                phase_set = set()
                for phase_name in micro_to_gem.values():
                    if phase_name not in excluded:
                        phase_set.add(normalize_phase_name(phase_name))
                microstructure_phases = list(phase_set)

                num_phases = len(microstructure_phases)
                self.micro_info_label.set_text(
                    f"Selected: {self.selected_microstructure_path.name} ({size_str}, {num_phases} phases)"
                )

                # Load phases into the product selector
                self.product_selector.set_microstructure_phases(microstructure_phases)
                self._log_message(f"Loaded {num_phases} microstructure phases")
            else:
                # No phase mapping - clear microstructure phases
                self.product_selector.clear_microstructure_phases()
                self._log_message("Note: No phase mapping file found for this microstructure")
        except Exception as e:
            self.logger.warning(f"Error getting microstructure info: {e}")
            self.product_selector.clear_microstructure_phases()

        self._log_message(f"Selected microstructure: {display_name}")

    def _on_configure_phase(self, widget: HydrationProductSelectorWidget, gems_name: str, has_csh: bool) -> None:
        """Open combined phase configuration dialog (kinetics + affinity + C-S-H)."""
        # Get current configurations
        current_kinetics = self.product_selector.get_kinetic_configuration(gems_name)
        product_config = self.product_selector.get_product_configuration(gems_name)

        current_affinity = None
        current_psd = None
        current_rd = None

        if product_config:
            current_affinity = product_config.get('affinity')
            current_psd = product_config.get('poresize_distribution')
            current_rd = product_config.get('rd_values')

        # Get available phases for affinity targets
        available_phases = self._get_available_phases()

        dialog = PhaseConfigurationDialog(
            self.main_window,
            gems_name,
            current_kinetics=current_kinetics,
            current_affinity=current_affinity,
            current_psd=current_psd,
            current_rd=current_rd,
            available_phases=available_phases,
            has_csh_data=has_csh,
            initial_tab="kinetics"  # Default to kinetics tab
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            # Save kinetics
            new_kinetics = dialog.get_kinetics_data()
            if new_kinetics:
                self.product_selector.set_kinetic_configuration(gems_name, new_kinetics)
                self._log_message(f"Updated kinetics for {gems_name}: {new_kinetics.get('type')}")
            else:
                # Thermodynamic (no kinetics)
                self.product_selector.remove_kinetic_configuration(gems_name)
                self._log_message(f"Set {gems_name} to thermodynamic control")

            # Save affinity
            new_affinity = dialog.get_affinity_data()
            self.product_selector.set_product_affinity(gems_name, new_affinity)

            # Save C-S-H if applicable
            if has_csh:
                csh_data = dialog.get_csh_data()
                self.product_selector.set_csh_parameters(
                    gems_name,
                    csh_data.get('poresize_distribution'),
                    csh_data.get('rd_values')
                )
                self._log_message(f"Updated C-S-H parameters for {gems_name}")

        dialog.destroy()

    def _on_configure_affinity(self, widget: HydrationProductSelectorWidget, gems_name: str) -> None:
        """Open affinity editor dialog for a product."""
        # Get current affinity data
        config = self.product_selector.get_product_configuration(gems_name)
        current_affinity = config.get('affinity', []) if config else None

        # Get available phases for affinity targets
        available_phases = self._get_available_phases()

        dialog = AffinityEditorDialog(
            self.main_window,
            gems_name,
            current_affinity=current_affinity,
            available_phases=available_phases
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_affinity = dialog.get_affinity_data()
            self.product_selector.set_product_affinity(gems_name, new_affinity)
            self._log_message(f"Updated affinity for {gems_name}")

        dialog.destroy()

    def _on_configure_kinetics(self, widget: HydrationProductSelectorWidget, gems_name: str) -> None:
        """Open kinetic model editor dialog for a phase."""
        # Get current kinetic configuration
        current_kinetics = self.product_selector.get_kinetic_configuration(gems_name)

        dialog = KineticModelEditorDialog(
            self.main_window,
            gems_name,
            current_params=current_kinetics
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_kinetics = dialog.get_kinetic_parameters()
            if new_kinetics:
                # User selected a kinetic model
                self.product_selector.set_kinetic_configuration(gems_name, new_kinetics)
                self._log_message(f"Updated kinetics for {gems_name}: {new_kinetics.get('type')}")
            else:
                # User selected "Thermodynamic" (no kinetics) - remove any existing configuration
                self.product_selector.remove_kinetic_configuration(gems_name)
                self._log_message(f"Removed kinetics for {gems_name} (now thermodynamic)")

        dialog.destroy()

    def _on_configure_csh(self, widget: HydrationProductSelectorWidget, gems_name: str) -> None:
        """Open C-S-H configuration dialog."""
        # Get current CSH data
        config = self.product_selector.get_product_configuration(gems_name)
        current_psd = config.get('poresize_distribution') if config else None
        current_rd = config.get('rd_values') if config else None

        dialog = CSHConfigDialog(
            self.main_window,
            gems_name,
            current_psd=current_psd,
            current_rd=current_rd
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_psd = dialog.get_poresize_distribution()
            new_rd = dialog.get_rd_values()
            self.product_selector.set_csh_parameters(gems_name, new_psd, new_rd)
            self._log_message(f"Updated C-S-H parameters for {gems_name}")

        dialog.destroy()

    def _get_available_phases(self) -> List[str]:
        """Get list of available phases for affinity targets."""
        phases = [
            "VOID", "Electrolyte",
            "Alite", "Belite", "Aluminate", "Ferrite",
            "Arcanite", "Thenardite",
            "Gypsum", "Bassanite", "Anhydrite",
            "CSHQ", "Portlandite", "ettr", "monosulf-AlFe",
        ]

        # Add selected hydration products
        selected = self.product_selector.get_selected_products()
        for product in selected:
            if product not in phases:
                phases.append(product)

        return phases

    def _build_config(self) -> HydrationInputConfig:
        """Build HydrationInputConfig from current UI state."""
        # Generate output times using the time generation system
        result = self._generate_output_times()
        if result.error or not result.times_days:
            # Fallback to defaults if generation fails
            output_times = [0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28]
        else:
            output_times = result.times_days  # Already in days

        # Get final time in days
        final_time_days = self._get_final_time_days()

        # Get temperature in Kelvin
        temp_celsius = self.temperature_spin.get_value()
        temp_kelvin = temp_celsius + 273.15

        # Get selected products and their configurations
        selected_products = self.product_selector.get_selected_products()
        product_configs = self.product_selector.get_all_configurations()

        # Get electrolyte conditions
        electrolyte_conditions = self.electrolyte_editor.get_electrolyte_conditions()

        # Get kinetic overrides from the product selector
        kinetic_overrides = self.product_selector.get_all_kinetic_configurations()

        # Adaptive time stepping configuration (convert to hours for C++ backend)
        dt_init_unit = self.adaptive_dt_initial_unit_combo.get_active_id() or "s"
        dt_max_unit = self.adaptive_dt_max_unit_combo.get_active_id() or "hr"
        adaptive_stepping = {
            'enabled': self.adaptive_enabled_check.get_active(),
            'dt_initial': self._convert_to_hours(
                self.adaptive_dt_initial_spin.get_value(), dt_init_unit
            ),
            'dt_max': self._convert_to_hours(
                self.adaptive_dt_max_spin.get_value(), dt_max_unit
            ),
            'growth_factor': self.adaptive_growth_spin.get_value(),
            'shrink_factor': self.adaptive_shrink_spin.get_value(),
            'successes_for_growth': int(self.adaptive_successes_spin.get_value()),
            'max_consecutive_failures': int(self.adaptive_max_failures_spin.get_value()),
            'max_relative_change': self.adaptive_max_change_spin.get_value(),
        }

        config = HydrationInputConfig(
            resolution=self.resolution_spin.get_value(),
            temperature=temp_kelvin,
            reference_temperature=298.15,
            saturated=self.saturated_radio.get_active(),
            final_time=final_time_days,
            output_times=output_times,
            hydration_products=selected_products,
            product_configurations=product_configs,
            electrolyte_conditions=electrolyte_conditions,
            kinetic_overrides=kinetic_overrides,
            adaptive_stepping=adaptive_stepping,
            # Runtime options
            verbose=self.verbose_check.get_active(),
            suppress_warnings=self.suppress_warnings_check.get_active(),
            create_xyz_files=self.create_xyz_check.get_active(),
        )

        return config

    def _on_validate_clicked(self, button: Gtk.Button) -> None:
        """Validate the current configuration."""
        self._log_message("Validating configuration...")

        errors = []

        # Check microstructure selection
        if self.selected_microstructure_path is None:
            errors.append("No microstructure selected")
        elif not self.selected_microstructure_path.exists():
            errors.append(f"Microstructure file not found: {self.selected_microstructure_path}")

        # Check operation name
        op_name = self.operation_name_entry.get_text().strip()
        if not op_name:
            errors.append("Operation name is required")

        # Check hydration products
        selected_products = self.product_selector.get_selected_products()
        if len(selected_products) == 0:
            errors.append("No hydration products selected")

        # Check output times using the time generation system
        time_result = self._generate_output_times()
        if time_result.error:
            errors.append(f"Output times error: {time_result.error}")
        elif len(time_result.times_days) == 0:
            errors.append("At least one output time is required")
        elif len(time_result.times_days) > 200:
            errors.append(f"Too many output times ({len(time_result.times_days)}). Maximum is 200.")

        # Log warnings from time generation
        for warning in time_result.warnings:
            self._log_message(f"WARNING: {warning}")

        # Check electrolyte charge balance (warning, not error)
        if not self.electrolyte_editor.is_charge_balanced():
            self._log_message("WARNING: Electrolyte charge is not balanced")

        # Report results
        if errors:
            self._log_message("Validation FAILED:")
            for error in errors:
                self._log_message(f"  - {error}")
            self.status_label.set_text("Validation Failed")
        else:
            # Get phase info
            micro_phases = self.product_selector.get_microstructure_phases()
            all_phases = self.product_selector.get_all_phases()
            self._log_message("Validation PASSED")
            self._log_message(f"  - Microstructure: {self.selected_microstructure_path.name}")
            self._log_message(f"  - Operation: {op_name}")
            self._log_message(f"  - Microstructure phases: {len(micro_phases)}")
            self._log_message(f"  - Total phases: {len(all_phases)}")
            self._log_message(f"  - Resolution: {self.resolution_spin.get_value()} μm/voxel")
            self._log_message(f"  - Temperature: {self.temperature_spin.get_value()}°C")
            time_unit = self.final_time_unit_combo.get_active_text()
            self._log_message(f"  - Final time: {self.final_time_spin.get_value()} {time_unit}")
            self.status_label.set_text("Validated")

    def _on_run_clicked(self, button: Gtk.Button) -> None:
        """Start the hydration simulation."""
        # Validate first
        if self.selected_microstructure_path is None:
            self._log_message("ERROR: No microstructure selected")
            return

        op_name = self.operation_name_entry.get_text().strip()
        if not op_name:
            self._log_message("ERROR: Operation name is required")
            return

        self._log_message(f"Starting hydration simulation: {op_name}")

        # Build configuration
        config = self._build_config()

        # Get material phases from the microstructure's phase mapping
        material_phases = self._get_material_phases_from_microstructure()

        # Update UI state
        self.simulation_running = True
        self.run_btn.set_sensitive(False)
        self.cancel_btn.set_sensitive(True)
        self.validate_btn.set_sensitive(False)
        self.status_label.set_text("Running...")
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("Starting...")

        # Start simulation in background
        def run_simulation():
            try:
                started, errors = self.execution_service.start_simulation(
                    operation_name=op_name,
                    material_phases=material_phases,
                    config=config,
                    microstructure_path=self.selected_microstructure_path,
                    source_microstructure_operation=self.selected_operation_name,
                    progress_callback=self._on_progress_update
                )

                if not started:
                    # Failed to start - report error immediately
                    GLib.idle_add(self._on_simulation_complete, False, errors)
                else:
                    # Successfully started - update UI to show running state
                    # The simulation will complete later via polling
                    GLib.idle_add(self._on_simulation_started)

            except Exception as e:
                self.logger.error(f"Simulation error: {e}")
                GLib.idle_add(self._on_simulation_complete, False, [str(e)])

        import threading
        thread = threading.Thread(target=run_simulation, daemon=True)
        thread.start()

    def _get_material_phases_from_microstructure(self) -> List[MaterialPhaseData]:
        """Get material phase data from the microstructure's phase mapping."""
        material_phases = []

        if self.selected_microstructure_path is None:
            return material_phases

        # Try to load phase mapping - check multiple possible locations
        phase_mapping_path = None
        possible_paths = [
            self.selected_microstructure_path.parent / f"{self.selected_operation_name}_phase_mapping.json",
            self.selected_microstructure_path.parent / "phase_mapping.json",
        ]

        for path in possible_paths:
            if path.exists():
                phase_mapping_path = path
                break

        if phase_mapping_path is not None:
            try:
                with open(phase_mapping_path, 'r') as f:
                    mapping = json.load(f)

                # Create a single MaterialPhaseData with all phases from the mapping
                # Note: Aggregate phases (e.g., Quartz) are now included so users can set kinetics
                phases = []
                for phase_id_str, phase_name in mapping.get('micro_to_gem', {}).items():
                    if phase_name not in ["VOID", "Electrolyte"]:
                        phases.append({
                            'gem_phase_name': phase_name,
                            'mass_fraction': 0.0,  # Unknown from microstructure
                        })

                if phases:
                    material_phases.append(MaterialPhaseData(
                        material_id=0,
                        material_name="Microstructure phases",
                        phases=phases,
                        is_cement_component=True,
                    ))

                self._log_message(f"Loaded phase mapping with {len(phases)} phases")

            except Exception as e:
                self.logger.warning(f"Error loading phase mapping: {e}")
                self._log_message(f"Warning: Could not load phase mapping: {e}")
        else:
            # No phase mapping file found - phases will be read from microstructure
            self._log_message(
                "Note: No phase mapping file found. Phases will be extracted from microstructure file."
            )

        return material_phases

    def _on_progress_update(self, operation_name: str, progress: Any) -> None:
        """Handle progress update from simulation."""
        GLib.idle_add(self._update_progress_ui, progress)

    def _update_progress_ui(self, progress: Any) -> None:
        """Update progress UI (must be called from main thread)."""
        if progress is None:
            return

        fraction = progress.percent_complete / 100.0
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(f"{progress.percent_complete:.1f}% - Time: {progress.current_time:.2f} days")

    def _poll_progress(self) -> bool:
        """Poll for simulation progress."""
        if not self.simulation_running:
            return False

        op_name = self.operation_name_entry.get_text().strip()
        progress = self.execution_service.get_simulation_progress(op_name)

        if progress:
            self._update_progress_ui(progress)

            # Check if simulation has completed
            if progress.percent_complete >= 100.0:
                self._on_simulation_complete(True, [])
                return False

        # Check if simulation is no longer active (may have failed or been cancelled)
        if op_name not in self.execution_service.active_simulations:
            # Simulation ended - check if it was successful by looking at progress
            if progress and progress.percent_complete >= 95.0:
                self._on_simulation_complete(True, [])
            else:
                self._on_simulation_complete(False, ["Simulation ended unexpectedly"])
            return False

        return self.simulation_running

    def _on_simulation_started(self) -> None:
        """Handle successful simulation start."""
        self._log_message("Simulation started successfully - monitoring progress...")
        self.status_label.set_text("Running")
        # Start progress polling only after the simulation is confirmed running
        self.progress_timeout_id = GLib.timeout_add(2000, self._poll_progress)

    def _on_simulation_complete(self, success: bool, errors: List[str]) -> None:
        """Handle simulation completion."""
        self.simulation_running = False
        self.run_btn.set_sensitive(True)
        self.cancel_btn.set_sensitive(False)
        self.validate_btn.set_sensitive(True)

        if self.progress_timeout_id:
            GLib.source_remove(self.progress_timeout_id)
            self.progress_timeout_id = None

        if success:
            self.status_label.set_text("Completed")
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("Complete")
            self._log_message("Simulation completed successfully!")
        else:
            self.status_label.set_text("Failed")
            self.progress_bar.set_text("Failed")
            self._log_message("Simulation FAILED:")
            for error in errors:
                self._log_message(f"  - {error}")

    def _on_cancel_clicked(self, button: Gtk.Button) -> None:
        """Cancel the running simulation."""
        op_name = self.operation_name_entry.get_text().strip()

        if self.execution_service.cancel_simulation(op_name):
            self._log_message("Simulation cancelled")
            self.simulation_running = False
            self.status_label.set_text("Cancelled")
            self.progress_bar.set_text("Cancelled")
            self.run_btn.set_sensitive(True)
            self.cancel_btn.set_sensitive(False)
            self.validate_btn.set_sensitive(True)
        else:
            self._log_message("Failed to cancel simulation")

    # ------------------------------------------------------------------
    # Load Operation feature
    # ------------------------------------------------------------------

    def _refresh_load_operation_list(self) -> None:
        """Populate the load operation combo with previous hydration operations."""
        self.load_operation_combo.handler_block_by_func(self._on_load_operation_selected)
        self.load_operation_store.clear()
        ops_dir = self.service_container.directories_service.get_operations_path()
        if not ops_dir.exists():
            return

        configs = []
        for op_dir in ops_dir.iterdir():
            if not op_dir.is_dir():
                continue
            for config_file in op_dir.glob("*_hydration_config.json"):
                try:
                    mtime = config_file.stat().st_mtime
                    configs.append((op_dir.name, str(config_file), mtime))
                except OSError:
                    continue

        # Sort newest first
        configs.sort(key=lambda x: x[2], reverse=True)
        for op_name, config_path, _ in configs:
            self.load_operation_store.append([op_name, config_path])
        self.load_operation_combo.handler_unblock_by_func(self._on_load_operation_selected)

    def _on_load_operation_selected(self, combo: Gtk.ComboBox) -> None:
        """Handle selection of a previous hydration operation from the combo."""
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            return
        model = combo.get_model()
        op_name = model[tree_iter][0]
        config_path = Path(model[tree_iter][1])
        self._load_from_operation(op_name, config_path)

    def _load_from_operation(self, operation_name: str, config_path: Path) -> None:
        """Load a hydration config file and populate the UI."""
        try:
            config = self.hydration_input_service.load_hydration_config(config_path)
            self._load_hydration_config(config, operation_name)
            self._log_message(f"Loaded configuration from: {operation_name}")
            self._log_message("Note: Select the desired input microstructure before running.")
        except Exception as e:
            self.logger.error(f"Failed to load hydration config: {e}")
            self._log_message(f"ERROR: Failed to load configuration: {e}")

    def _load_hydration_config(self, config, operation_name: str) -> None:
        """Populate all UI widgets from a HydrationInputConfig."""

        # Operation name: append -01, -02, etc. to make unique
        new_name = self._generate_incremented_name(operation_name)
        self.operation_name_entry.set_text(new_name)

        # Resolution
        self.resolution_spin.set_value(config.resolution)

        # Temperature (config stores Kelvin, UI shows Celsius)
        self.temperature_spin.set_value(config.temperature - 273.15)

        # Moisture condition
        if config.saturated:
            self.saturated_radio.set_active(True)
        else:
            self.sealed_radio.set_active(True)

        # Final time (config stores days)
        self.final_time_unit_combo.set_active_id("d")
        self.final_time_spin.set_value(config.final_time)

        # Output times as Custom List (config stores list of days)
        self.output_model_combo.set_active_id("custom")
        self.custom_times_unit_combo.set_active_id("d")
        if config.output_times:
            # Format times: use enough precision but trim trailing zeros
            times_strs = []
            for t in config.output_times:
                if t == 0:
                    times_strs.append("0")
                else:
                    times_strs.append(f"{t:.8g}")
            self.custom_times_entry.set_text(", ".join(times_strs))
        self.exact_times_entry.set_text("")

        # Electrolyte conditions
        if config.electrolyte_conditions:
            self.electrolyte_editor.set_electrolyte_conditions(
                config.electrolyte_conditions
            )

        # Hydration products and configurations
        if config.hydration_products:
            self.product_selector.set_selected_products(config.hydration_products)

        if config.product_configurations:
            for gems_name, prod_config in config.product_configurations.items():
                self.product_selector.set_product_configuration(
                    gems_name, prod_config
                )

        if config.kinetic_overrides:
            for phase_name, kinetics in config.kinetic_overrides.items():
                self.product_selector.set_kinetic_configuration(
                    phase_name, kinetics
                )

        # Adaptive time stepping
        adaptive = config.adaptive_stepping
        if adaptive:
            self.adaptive_enabled_check.set_active(
                adaptive.get("enabled", True)
            )

            # dt_initial: stored in hours, display in seconds
            dt_init_hours = adaptive.get("dt_initial", 0.001)
            self.adaptive_dt_initial_unit_combo.set_active_id("s")
            self.adaptive_dt_initial_spin.set_value(dt_init_hours * 3600.0)

            # dt_max: stored in hours, display in hours
            self.adaptive_dt_max_unit_combo.set_active_id("hr")
            self.adaptive_dt_max_spin.set_value(adaptive.get("dt_max", 4.0))

            self.adaptive_growth_spin.set_value(
                adaptive.get("growth_factor", 1.5)
            )
            self.adaptive_shrink_spin.set_value(
                adaptive.get("shrink_factor", 0.5)
            )
            self.adaptive_successes_spin.set_value(
                adaptive.get("successes_for_growth", 2)
            )
            self.adaptive_max_failures_spin.set_value(
                adaptive.get("max_consecutive_failures", 50)
            )
            self.adaptive_max_change_spin.set_value(
                adaptive.get("max_relative_change", 0.05)
            )

        # Runtime options
        self.verbose_check.set_active(config.verbose)
        self.suppress_warnings_check.set_active(config.suppress_warnings)
        self.create_xyz_check.set_active(config.create_xyz_files)

        # Refresh the time preview
        self._update_time_preview()

    def _generate_incremented_name(self, base_name: str) -> str:
        """Generate an incremented operation name like '{base}-01'."""
        ops_dir = self.service_container.directories_service.get_operations_path()
        for i in range(1, 100):
            candidate = f"{base_name}-{i:02d}"
            if not (ops_dir / candidate).exists():
                return candidate
        return f"{base_name}-copy"

    def _log_message(self, message: str) -> None:
        """Add a message to the log view."""
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, f"{message}\n")

        # Scroll to end
        mark = self.log_buffer.create_mark(None, end_iter, False)
        self.log_view.scroll_to_mark(mark, 0, False, 0, 0)
        self.log_buffer.delete_mark(mark)

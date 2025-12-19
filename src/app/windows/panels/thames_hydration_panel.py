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
        """Create the microstructure selection section."""
        frame = Gtk.Frame()
        frame.set_label("  Input Microstructure  ")
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Instruction label
        instruction = Gtk.Label()
        instruction.set_markup(
            '<span size="small">Select a completed microstructure operation to use as input for hydration.</span>'
        )
        instruction.set_halign(Gtk.Align.START)
        instruction.set_line_wrap(True)
        content.pack_start(instruction, False, False, 0)

        # Microstructure combo box with refresh button
        combo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        combo_label = Gtk.Label("Microstructure:")
        combo_label.set_size_request(120, -1)
        combo_label.set_halign(Gtk.Align.START)
        combo_row.pack_start(combo_label, False, False, 0)

        # ComboBox for microstructures
        self.microstructure_store = Gtk.ListStore(str, str)  # display_name, path
        self.microstructure_combo = Gtk.ComboBox.new_with_model(self.microstructure_store)
        renderer = Gtk.CellRendererText()
        self.microstructure_combo.pack_start(renderer, True)
        self.microstructure_combo.add_attribute(renderer, "text", 0)
        self.microstructure_combo.set_hexpand(True)
        combo_row.pack_start(self.microstructure_combo, True, True, 0)

        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_image(Gtk.Image.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON))
        refresh_btn.set_tooltip_text("Refresh microstructure list")
        refresh_btn.connect("clicked", lambda b: self._refresh_microstructure_list())
        combo_row.pack_start(refresh_btn, False, False, 0)

        content.pack_start(combo_row, False, False, 0)

        # Info about selected microstructure
        self.micro_info_label = Gtk.Label()
        self.micro_info_label.set_halign(Gtk.Align.START)
        self.micro_info_label.set_line_wrap(True)
        self.micro_info_label.get_style_context().add_class("dim-label")
        content.pack_start(self.micro_info_label, False, False, 0)

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

        # Final time
        time_label = Gtk.Label("Final Time (days):")
        time_label.set_halign(Gtk.Align.START)
        content.attach(time_label, 0, row, 1, 1)

        self.final_time_spin = Gtk.SpinButton.new_with_range(0.1, 365, 0.1)
        self.final_time_spin.set_value(28)
        self.final_time_spin.set_digits(1)
        self.final_time_spin.set_tooltip_text("Total simulation time in days")
        content.attach(self.final_time_spin, 1, row, 1, 1)

        row += 1

        # Output times
        times_label = Gtk.Label("Output Times (days):")
        times_label.set_halign(Gtk.Align.START)
        times_label.set_valign(Gtk.Align.START)
        content.attach(times_label, 0, row, 1, 1)

        self.output_times_entry = Gtk.Entry()
        self.output_times_entry.set_text("0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28")
        self.output_times_entry.set_tooltip_text("Comma-separated list of times to output results")
        self.output_times_entry.set_hexpand(True)
        content.attach(self.output_times_entry, 1, row, 1, 1)

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

    def _on_microstructure_changed(self, combo: Gtk.ComboBox) -> None:
        """Handle microstructure selection change."""
        tree_iter = combo.get_active_iter()
        if tree_iter is None:
            self.selected_microstructure_path = None
            self.selected_operation_name = None
            self.micro_info_label.set_text("")
            # Clear microstructure phases from product selector
            self.product_selector.clear_microstructure_phases()
            return

        model = combo.get_model()
        display_name = model[tree_iter][0]
        path_str = model[tree_iter][1]

        self.selected_microstructure_path = Path(path_str)
        self.selected_operation_name = self.selected_microstructure_path.parent.name

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
        # Parse output times
        times_text = self.output_times_entry.get_text()
        try:
            output_times = [float(t.strip()) for t in times_text.split(",") if t.strip()]
        except ValueError:
            output_times = [0.01, 0.1, 0.25, 0.5, 1, 3, 7, 14, 21, 28]

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

        config = HydrationInputConfig(
            resolution=self.resolution_spin.get_value(),
            temperature=temp_kelvin,
            reference_temperature=298.15,
            saturated=self.saturated_radio.get_active(),
            final_time=self.final_time_spin.get_value(),
            output_times=output_times,
            hydration_products=selected_products,
            product_configurations=product_configs,
            electrolyte_conditions=electrolyte_conditions,
            kinetic_overrides=kinetic_overrides,
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

        # Check output times
        times_text = self.output_times_entry.get_text()
        try:
            output_times = [float(t.strip()) for t in times_text.split(",") if t.strip()]
            if len(output_times) == 0:
                errors.append("At least one output time is required")
        except ValueError:
            errors.append("Invalid output times format (use comma-separated numbers)")

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
            self._log_message(f"  - Final time: {self.final_time_spin.get_value()} days")
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

        # Start progress polling
        self.progress_timeout_id = GLib.timeout_add(1000, self._poll_progress)

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

    def _log_message(self, message: str) -> None:
        """Add a message to the log view."""
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, f"{message}\n")

        # Scroll to end
        mark = self.log_buffer.create_mark(None, end_iter, False)
        self.log_view.scroll_to_mark(mark, 0, False, 0, 0)
        self.log_buffer.delete_mark(mark)

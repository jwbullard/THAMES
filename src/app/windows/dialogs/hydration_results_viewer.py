#!/usr/bin/env python3
"""
Hydration Results Viewer Dialog

Comprehensive viewer for THAMES hydration simulation results including:
- Tab 1: 3D microstructure evolution visualization (PyVista)
- Tab 2: Time-series data plots (matplotlib) for CSV output files

CSV output files displayed:
- Microstructure.csv - Phase volume fractions over time
- Solution.csv - Aqueous species concentrations over time
- SI.csv - Saturation indices over time
- SurfaceAreas.csv - Phase surface areas over time
- Enthalpy.csv - Enthalpy over time
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
import re

# Import matplotlib for data plotting
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import the existing VTK-based 3D viewer
try:
    from app.visualization.pyvista_3d_viewer import PyVistaViewer3D
    PYVISTA_AVAILABLE = True
    print("SUCCESS: PyVistaViewer3D imported successfully")
except ImportError as e:
    PyVistaViewer3D = None
    PYVISTA_AVAILABLE = False
    print(f"ERROR: Failed to import PyVistaViewer3D: {e}")
    import traceback
    traceback.print_exc()

# Import phase color service for THAMES dynamic phase mappings
try:
    from app.services.phase_color_service import PhaseColorService
    PHASE_COLOR_SERVICE_AVAILABLE = True
except ImportError:
    PhaseColorService = None
    PHASE_COLOR_SERVICE_AVAILABLE = False


class HydrationResultsViewer(Gtk.Dialog):
    """Dialog for viewing hydration simulation results (3D visualization + time-series plots)."""

    def __init__(self, parent=None, operation=None):
        super().__init__(
            title="Hydration Results Viewer",
            transient_for=parent,
            flags=0
        )

        self.operation = operation
        self.logger = logging.getLogger(__name__)

        # Initialize phase color service for THAMES mappings
        self.phase_color_service = PhaseColorService() if PHASE_COLOR_SERVICE_AVAILABLE else None

        # Time-series data (3D viewer)
        self.microstructure_files: List[Tuple[float, str]] = []  # (time_hours, filepath)
        self.current_time_index = 0

        # Cache colors to avoid re-reading CSV file every time
        self.cached_phase_mapping = None
        self.cached_phase_colors = None

        # THAMES-specific phase mapping (loaded from operation folder)
        self.thames_color_mapping = None  # PhaseColorMapping from operation folder

        # Cache microstructure data for fast time navigation
        self.cached_voxel_data: Dict[int, np.ndarray] = {}  # index -> voxel_data
        self.cached_phase_meshes: Dict[int, Any] = {}  # index -> pre-built phase meshes
        self.preloading_complete = False

        # Cleanup flag to prevent double cleanup
        self.cleanup_performed = False

        # Track when dialog was hidden for automatic memory cleanup
        self.hidden_time = None
        self.auto_cleanup_timer = None

        # 3D viewer UI components
        self.pyvista_viewer = None
        self.time_slider = None
        self.time_label = None
        self.info_label = None

        # Data plots UI components (Tab 2)
        self.csv_files: Dict[str, Path] = {}  # {display_name: filepath}
        self.current_csv_data: Optional[pd.DataFrame] = None
        self.plot_figure = None
        self.plot_canvas = None
        self.data_file_combo = None
        self.y_liststore = None
        self.y_treeview = None
        self.output_path: Optional[Path] = None  # Cache operation output path

        # Dialog setup - use reasonable default that fits most screens
        self.set_default_size(1000, 650)
        self.set_resizable(True)
        self.set_modal(True)

        # Add standard dialog buttons
        self.add_button("Close", Gtk.ResponseType.CLOSE)

        # Connect cleanup handlers to prevent segfault
        self.connect('delete-event', self._on_delete_event)
        self.connect('response', self._on_response)

        # Initialize UI
        self._setup_ui()
        self._load_microstructure_files()
    
    def show_all(self):
        """Override show_all to cancel auto cleanup timer when dialog becomes visible."""
        self._cancel_auto_cleanup_timer()
        super().show_all()
        
        # Only load if not already loaded
        if not hasattr(self, '_initial_loaded') or not self._initial_loaded:
            self._load_initial_microstructure()
            # Start preloading other microstructures in background
            self._start_preloading()
            self._initial_loaded = True
        
    def _setup_ui(self) -> None:
        """Set up the user interface with tabs for 3D viewer and data plots."""
        content_area = self.get_content_area()
        content_area.set_spacing(5)
        content_area.set_margin_left(10)
        content_area.set_margin_right(10)
        content_area.set_margin_top(5)
        content_area.set_margin_bottom(5)

        # Create notebook for tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)
        content_area.pack_start(self.notebook, True, True, 0)

        # Tab 1: 3D Microstructure Evolution
        self._create_3d_viewer_tab()

        # Tab 2: Time-Series Data Plots
        self._create_data_plots_tab()

        # Ensure notebook and tabs are visible
        self.notebook.show_all()

    def _create_3d_viewer_tab(self) -> None:
        """Create the 3D microstructure viewer tab."""
        tab_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        tab_vbox.set_margin_left(5)
        tab_vbox.set_margin_right(5)
        tab_vbox.set_margin_top(5)
        tab_vbox.set_margin_bottom(5)

        # Info label at top
        self.info_label = Gtk.Label()
        self.info_label.set_markup("<b>Hydration Simulation Results</b>")
        self.info_label.set_halign(Gtk.Align.START)
        tab_vbox.pack_start(self.info_label, False, False, 0)

        # Create 3D viewer frame
        viewer_frame = Gtk.Frame(label="3D Microstructure Evolution")
        viewer_frame.set_size_request(-1, 380)
        tab_vbox.pack_start(viewer_frame, True, True, 0)

        # Add PyVista viewer if available
        if PYVISTA_AVAILABLE and PyVistaViewer3D is not None:
            self.pyvista_viewer = PyVistaViewer3D()
            viewer_frame.add(self.pyvista_viewer)
            self.pyvista_viewer.show_all()
        else:
            unavailable_label = Gtk.Label()
            unavailable_label.set_markup(
                "<b>3D Visualization Not Available</b>\n\n"
                "PyVista is required for 3D microstructure visualization.\n"
                "Install PyVista to enable this feature."
            )
            unavailable_label.set_justify(Gtk.Justification.CENTER)
            viewer_frame.add(unavailable_label)

        # Create time controls frame
        controls_frame = Gtk.Frame(label="Time Controls")
        tab_vbox.pack_start(controls_frame, False, False, 0)

        controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        controls_vbox.set_margin_left(10)
        controls_vbox.set_margin_right(10)
        controls_vbox.set_margin_top(5)
        controls_vbox.set_margin_bottom(10)
        controls_frame.add(controls_vbox)

        # Time display label
        self.time_label = Gtk.Label()
        self.time_label.set_markup("<b>Time: 0.0 hours</b>")
        self.time_label.set_halign(Gtk.Align.CENTER)
        controls_vbox.pack_start(self.time_label, False, False, 0)

        # Time slider
        self.time_slider = Gtk.Scale.new_with_range(
            orientation=Gtk.Orientation.HORIZONTAL,
            min=0,
            max=100,
            step=1
        )
        self.time_slider.set_hexpand(True)
        self.time_slider.set_value(0)
        self.time_slider.connect('value-changed', self._on_time_changed)
        controls_vbox.pack_start(self.time_slider, False, False, 5)

        # Time navigation buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        button_box.set_halign(Gtk.Align.CENTER)
        controls_vbox.pack_start(button_box, False, False, 5)

        prev_button = Gtk.Button(label="← Previous")
        prev_button.connect('clicked', self._on_previous_clicked)
        button_box.pack_start(prev_button, False, False, 0)

        next_button = Gtk.Button(label="Next →")
        next_button.connect('clicked', self._on_next_clicked)
        button_box.pack_start(next_button, False, False, 0)

        # Add tab to notebook
        tab_label = Gtk.Label(label="3D Visualization")
        tab_vbox.show_all()
        self.notebook.append_page(tab_vbox, tab_label)

    def _create_data_plots_tab(self) -> None:
        """Create the time-series data plots tab."""
        if not MATPLOTLIB_AVAILABLE:
            # Show message that matplotlib is not available
            unavailable_label = Gtk.Label()
            unavailable_label.set_markup(
                "<b>Data Plotting Not Available</b>\n\n"
                "Matplotlib is required for time-series data plots.\n"
                "Install matplotlib to enable this feature."
            )
            unavailable_label.set_justify(Gtk.Justification.CENTER)
            tab_label = Gtk.Label(label="Data Plots")
            unavailable_label.show_all()
            self.notebook.append_page(unavailable_label, tab_label)
            return

        # Main horizontal layout: controls on left, plot on right
        main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        main_paned.set_wide_handle(True)
        main_paned.set_position(260)

        # Left side: Controls panel (scrollable)
        controls_frame = Gtk.Frame(label="Plot Controls")
        controls_frame.set_size_request(260, -1)

        # Make controls scrollable for smaller screens
        controls_scroll = Gtk.ScrolledWindow()
        controls_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        controls_vbox.set_margin_left(6)
        controls_vbox.set_margin_right(6)
        controls_vbox.set_margin_top(6)
        controls_vbox.set_margin_bottom(6)
        controls_scroll.add(controls_vbox)
        controls_frame.add(controls_scroll)

        # Data file selection
        file_label = Gtk.Label()
        file_label.set_markup("<b>Data Category:</b>")
        file_label.set_halign(Gtk.Align.START)
        controls_vbox.pack_start(file_label, False, False, 0)

        self.data_file_combo = Gtk.ComboBoxText()
        self.data_file_combo.connect('changed', self._on_data_file_changed)
        controls_vbox.pack_start(self.data_file_combo, False, False, 0)

        # Y-axis variables (multi-select)
        y_label = Gtk.Label()
        y_label.set_markup("<b>Variables to Plot:</b>")
        y_label.set_halign(Gtk.Align.START)
        controls_vbox.pack_start(y_label, False, False, 5)

        # Scrolled window for Y variables list
        y_scrolled = Gtk.ScrolledWindow()
        y_scrolled.set_size_request(-1, 150)
        y_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        controls_vbox.pack_start(y_scrolled, True, True, 0)

        # List store: selected, display_name, column_name
        self.y_liststore = Gtk.ListStore(bool, str, str)
        self.y_treeview = Gtk.TreeView(model=self.y_liststore)

        # Checkbox column
        checkbox_renderer = Gtk.CellRendererToggle()
        checkbox_renderer.connect("toggled", self._on_plot_variable_toggled)
        checkbox_column = Gtk.TreeViewColumn("", checkbox_renderer, active=0)
        self.y_treeview.append_column(checkbox_column)

        # Variable name column
        text_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn("Variable", text_renderer, text=1)
        self.y_treeview.append_column(name_column)

        y_scrolled.add(self.y_treeview)

        # Select/deselect buttons
        select_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        controls_vbox.pack_start(select_button_box, False, False, 0)

        select_all_btn = Gtk.Button(label="Select All")
        select_all_btn.connect('clicked', self._on_select_all_clicked)
        select_button_box.pack_start(select_all_btn, True, True, 0)

        deselect_all_btn = Gtk.Button(label="Deselect All")
        deselect_all_btn.connect('clicked', self._on_deselect_all_clicked)
        select_button_box.pack_start(deselect_all_btn, True, True, 0)

        # Plot options
        options_label = Gtk.Label()
        options_label.set_markup("<b>Plot Options:</b>")
        options_label.set_halign(Gtk.Align.START)
        controls_vbox.pack_start(options_label, False, False, 5)

        # Log scale checkboxes
        self.log_x_check = Gtk.CheckButton(label="Logarithmic X-axis")
        controls_vbox.pack_start(self.log_x_check, False, False, 0)

        self.log_y_check = Gtk.CheckButton(label="Logarithmic Y-axis")
        controls_vbox.pack_start(self.log_y_check, False, False, 0)

        # Line width selection
        line_width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        line_width_label = Gtk.Label(label="Line Width:")
        line_width_box.pack_start(line_width_label, False, False, 0)
        self.line_width_spin = Gtk.SpinButton.new_with_range(0.5, 5.0, 0.5)
        self.line_width_spin.set_value(1.5)
        self.line_width_spin.set_digits(1)
        line_width_box.pack_start(self.line_width_spin, False, False, 0)
        controls_vbox.pack_start(line_width_box, False, False, 2)

        # Color scheme selection
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        color_label = Gtk.Label(label="Color Scheme:")
        color_box.pack_start(color_label, False, False, 0)
        self.color_scheme_combo = Gtk.ComboBoxText()
        color_schemes = ["Tab10 (Default)", "Set1", "Dark2", "Paired", "Pastel1", "Single Color"]
        for scheme in color_schemes:
            self.color_scheme_combo.append_text(scheme)
        self.color_scheme_combo.set_active(0)
        color_box.pack_start(self.color_scheme_combo, True, True, 0)
        controls_vbox.pack_start(color_box, False, False, 2)

        # Axis range controls
        range_label = Gtk.Label()
        range_label.set_markup("<b>Axis Ranges:</b> <small>(leave blank for auto)</small>")
        range_label.set_halign(Gtk.Align.START)
        controls_vbox.pack_start(range_label, False, False, 5)

        # X-axis range
        x_range_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        x_range_label = Gtk.Label(label="X:")
        x_range_label.set_size_request(20, -1)
        x_range_box.pack_start(x_range_label, False, False, 0)
        self.x_min_entry = Gtk.Entry()
        self.x_min_entry.set_placeholder_text("min")
        self.x_min_entry.set_width_chars(6)
        x_range_box.pack_start(self.x_min_entry, True, True, 0)
        x_to_label = Gtk.Label(label="to")
        x_range_box.pack_start(x_to_label, False, False, 0)
        self.x_max_entry = Gtk.Entry()
        self.x_max_entry.set_placeholder_text("max")
        self.x_max_entry.set_width_chars(6)
        x_range_box.pack_start(self.x_max_entry, True, True, 0)
        controls_vbox.pack_start(x_range_box, False, False, 0)

        # Y-axis range
        y_range_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        y_range_label = Gtk.Label(label="Y:")
        y_range_label.set_size_request(20, -1)
        y_range_box.pack_start(y_range_label, False, False, 0)
        self.y_min_entry = Gtk.Entry()
        self.y_min_entry.set_placeholder_text("min")
        self.y_min_entry.set_width_chars(6)
        y_range_box.pack_start(self.y_min_entry, True, True, 0)
        y_to_label = Gtk.Label(label="to")
        y_range_box.pack_start(y_to_label, False, False, 0)
        self.y_max_entry = Gtk.Entry()
        self.y_max_entry.set_placeholder_text("max")
        self.y_max_entry.set_width_chars(6)
        y_range_box.pack_start(self.y_max_entry, True, True, 0)
        controls_vbox.pack_start(y_range_box, False, False, 0)

        # Action buttons
        action_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        controls_vbox.pack_start(action_box, False, False, 10)

        plot_button = Gtk.Button(label="Create Plot")
        plot_button.get_style_context().add_class("suggested-action")
        plot_button.connect('clicked', self._on_create_data_plot_clicked)
        action_box.pack_start(plot_button, False, False, 0)

        export_plot_btn = Gtk.Button(label="Export Plot")
        export_plot_btn.connect('clicked', self._on_export_data_plot_clicked)
        action_box.pack_start(export_plot_btn, False, False, 0)

        main_paned.pack1(controls_frame, False, False)

        # Right side: Plot area
        plot_frame = Gtk.Frame(label="Time-Series Plot")

        self.plot_figure = Figure(figsize=(8, 6), dpi=100)
        self.plot_canvas = FigureCanvas(self.plot_figure)
        self.plot_canvas.set_size_request(500, 400)
        plot_frame.add(self.plot_canvas)

        # Initial placeholder plot
        ax = self.plot_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Select a data category and variables,\nthen click "Create Plot"',
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])

        main_paned.pack2(plot_frame, True, True)

        # Add tab to notebook - show_all ensures all widgets are visible
        tab_label = Gtk.Label(label="Data Plots")
        main_paned.show_all()
        self.notebook.append_page(main_paned, tab_label)
        
    def _load_microstructure_files(self) -> None:
        """Load and sort all time-series microstructure files."""
        try:
            if not self.operation:
                self.logger.error("No operation specified")
                return

            # Get output directory from operation metadata
            output_dir = None
            if hasattr(self.operation, 'output_dir') and self.operation.output_dir:
                output_dir = self.operation.output_dir
            elif hasattr(self.operation, 'metadata') and self.operation.metadata:
                output_dir = self.operation.metadata.get('output_directory')
                if not output_dir:
                    output_dir = self.operation.metadata.get('output_dir')

            if not output_dir:
                # Try to construct from operation name using configured operations directory
                from app.services.service_container import get_service_container
                service_container = get_service_container()
                operations_dir = service_container.directories_service.get_operations_path()
                potential_folder = operations_dir / self.operation.name
                if potential_folder.exists():
                    output_dir = str(potential_folder)

            if not output_dir:
                self.logger.error("No output directory found for operation")
                return

            output_path = Path(output_dir)
            if not output_path.exists():
                self.logger.error(f"Output directory does not exist: {output_path}")
                return

            # Check for Result/ subdirectory (THAMES hydration output location)
            result_path = output_path / "Result"
            if result_path.exists():
                self.logger.info(f"Found Result/ subdirectory, searching there for hydration outputs")
                search_path = result_path
            else:
                search_path = output_path

            # Find all .img files in the search path (Result/ or operation root)
            all_img_files = list(search_path.glob("*.img"))
            self.logger.info(f"Found {len(all_img_files)} .img files in {search_path}")

            # THAMES time-series format: JobRoot.YYYyDDDdHHhMMm.TTTK.img
            # Example: HydOf-Cem152-Neat.000y000d02h24m.298K.img
            thames_time_pattern = re.compile(r'\.(\d+)y(\d+)d(\d+)h(\d+)m\.(\d+)K\.img$')

            # Also support VCCTL format: *.img.XXX.XXh.XX.XXX
            vcctl_time_pattern = re.compile(r'\.img\..*?(\d+\.?\d*)h\.')

            # Track which files we've already added (by path) to avoid duplicates
            added_files = set()

            for file_path in all_img_files:
                filename = file_path.name
                file_str = str(file_path)

                # Skip if already added
                if file_str in added_files:
                    continue

                # Try THAMES time-series format first
                thames_match = thames_time_pattern.search(filename)
                if thames_match:
                    years = int(thames_match.group(1))
                    days = int(thames_match.group(2))
                    hours = int(thames_match.group(3))
                    minutes = int(thames_match.group(4))

                    # Convert to total hours
                    time_hours = years * 365 * 24 + days * 24 + hours + minutes / 60.0
                    self.microstructure_files.append((time_hours, file_str))
                    added_files.add(file_str)
                    self.logger.info(f"Found THAMES time-series file: {filename} at {time_hours:.2f}h")
                    continue

                # Try VCCTL format
                vcctl_match = vcctl_time_pattern.search(filename)
                if vcctl_match:
                    time_hours = float(vcctl_match.group(1))
                    self.microstructure_files.append((time_hours, file_str))
                    added_files.add(file_str)
                    self.logger.info(f"Found VCCTL time-series file: {filename} at {time_hours}h")
                    continue

                # No time pattern matched - this is an initial microstructure
                # Use -0.001 hours so it sorts before t=0 time-series files
                self.microstructure_files.append((-0.001, file_str))
                added_files.add(file_str)
                self.logger.info(f"Found initial microstructure: {filename}")
            
            # Sort by time
            self.microstructure_files.sort(key=lambda x: x[0])

            # Update slider range
            if len(self.microstructure_files) > 1:
                self.time_slider.set_range(0, len(self.microstructure_files) - 1)
                self.time_slider.set_increments(1, 1)

            self.logger.info(f"Loaded {len(self.microstructure_files)} microstructure files")

            # Try to load THAMES phase mapping from operation folder
            thames_loaded = self._load_thames_phase_mapping(output_path)
            mapping_source = "THAMES" if thames_loaded else "VCCTL"

            # Cache output path and load CSV files for data plots tab
            self.output_path = output_path
            self._load_csv_files()

            # Update info label
            if self.microstructure_files:
                self.info_label.set_markup(
                    f"<b>Operation:</b> {self.operation.name}\n"
                    f"<b>Microstructures:</b> {len(self.microstructure_files)} time points\n"
                    f"<b>Phase Colors:</b> {mapping_source}\n"
                    f"<b>Status:</b> <span color='orange'>Preloading data...</span>"
                )

        except Exception as e:
            self.logger.error(f"Error loading microstructure files: {e}")

    def _load_thames_phase_mapping(self, output_path: Path) -> bool:
        """
        Try to load THAMES phase mapping and colors from operation folder.

        Args:
            output_path: Path to operation output directory

        Returns:
            True if THAMES mapping was loaded successfully, False otherwise
        """
        if not self.phase_color_service:
            self.logger.debug("PhaseColorService not available, skipping THAMES mapping")
            return False

        try:
            # Look for THAMES phase color mapping files
            # Pattern: <operation_name>_phase_colors.json
            color_files = list(output_path.glob("*_phase_colors.json"))

            if not color_files:
                self.logger.debug(f"No THAMES phase color mapping found in {output_path}")
                return False

            # Load the first color mapping file found
            color_file = color_files[0]
            self.logger.info(f"Loading THAMES phase color mapping from: {color_file}")

            self.thames_color_mapping = self.phase_color_service.load_color_mapping(color_file)

            if self.thames_color_mapping:
                self.logger.info(
                    f"Loaded THAMES mapping: {len(self.thames_color_mapping.phase_id_to_name)} phases"
                )
                return True
            else:
                self.logger.warning(f"Failed to load color mapping from {color_file}")
                return False

        except Exception as e:
            self.logger.error(f"Error loading THAMES phase mapping: {e}")
            return False

    def _get_phase_mapping(self, use_cache: bool = True) -> Tuple[Dict[int, str], Dict[int, Tuple[float, float, float]]]:
        """
        Get phase mapping and colors - tries THAMES mapping first, falls back to VCCTL.

        This is the unified method for getting phase information that supports
        both THAMES dynamic phase IDs and legacy VCCTL fixed phase IDs.

        Returns:
            Tuple of (phase_mapping dict, phase_colors dict)
            - phase_mapping: {phase_id: phase_name}
            - phase_colors: {phase_id: (r, g, b)} normalized 0-1
        """
        # Return cached colors if available and requested
        if use_cache and self.cached_phase_mapping is not None and self.cached_phase_colors is not None:
            return self.cached_phase_mapping, self.cached_phase_colors

        # Try THAMES mapping first
        if self.thames_color_mapping:
            self.logger.info("Using THAMES phase mapping")
            phase_mapping = dict(self.thames_color_mapping.phase_id_to_name)
            phase_colors = {}

            # Convert hex colors to normalized RGB tuples
            for phase_id, hex_color in self.thames_color_mapping.phase_id_to_color.items():
                if self.phase_color_service:
                    rgb = self.phase_color_service.hex_to_rgb_normalized(hex_color)
                    phase_colors[phase_id] = rgb
                else:
                    # Manual conversion if service not available
                    hex_color = hex_color.lstrip('#')
                    r = int(hex_color[0:2], 16) / 255.0
                    g = int(hex_color[2:4], 16) / 255.0
                    b = int(hex_color[4:6], 16) / 255.0
                    phase_colors[phase_id] = (r, g, b)

            # Always ensure VOID (phase ID 0) is in the mapping
            if 0 not in phase_mapping:
                phase_mapping[0] = "VOID"
                phase_colors[0] = (0.0, 0.0, 0.0)  # Black
                self.logger.info("Added VOID (phase 0) to phase mapping")

            # Cache the results
            self.cached_phase_mapping = phase_mapping
            self.cached_phase_colors = phase_colors

            self.logger.info(f"Loaded {len(phase_mapping)} THAMES phase colors")
            return phase_mapping, phase_colors

        # Fall back to THAMES default mapping (no longer use VCCTL colors.csv)
        self.logger.info("THAMES JSON mapping not found, using THAMES default colors")
        phase_mapping, phase_colors = self._get_default_phase_mapping()

        # Cache the results
        self.cached_phase_mapping = phase_mapping
        self.cached_phase_colors = phase_colors

        return phase_mapping, phase_colors

    def _load_initial_microstructure(self) -> None:
        """Load the initial microstructure in the 3D viewer."""
        if not self.microstructure_files:
            self.logger.warning("No microstructure files available")
            self._show_diagnostic_message("No Microstructure Files", "No microstructure files were found for this operation.")
            return

        try:
            # Load the first microstructure (time=0)
            self.current_time_index = 0
            time_hours, file_path = self.microstructure_files[0]

            print(f"\n=== 3D VIEWER DIAGNOSTIC ===")
            print(f"Loading file: {file_path}")

            # Read microstructure file and load into PyVista viewer
            if self.pyvista_viewer:
                voxel_data = self._read_microstructure_file(file_path)
                print(f"Voxel data loaded: {voxel_data is not None}")
                if voxel_data is not None:
                    print(f"Voxel shape: {voxel_data.shape}, unique phases: {np.unique(voxel_data)}")

                    # Get phase mapping - tries THAMES first, falls back to VCCTL
                    phase_mapping, phase_colors = self._get_phase_mapping()
                    print(f"Phase mapping loaded: {len(phase_mapping)} phases, {len(phase_colors)} colors")
                    mapping_type = "THAMES" if self.thames_color_mapping else "VCCTL"
                    self.logger.info(f"Loading {len(phase_colors)} colors ({mapping_type}) for initial load")

                    # Debug: log what phases and colors we actually loaded
                    for phase_id, phase_name in phase_mapping.items():
                        if phase_id in phase_colors:
                            color = phase_colors[phase_id]
                            self.logger.info(f"Phase {phase_id}: {phase_name} = RGB({color[0]*255:.0f}, {color[1]*255:.0f}, {color[2]*255:.0f})")

                    # Clear any existing phase colors in PyVista viewer
                    if hasattr(self.pyvista_viewer, 'phase_colors'):
                        self.pyvista_viewer.phase_colors.clear()

                    # Pre-set colors in PyVista viewer before loading data
                    for phase_id, rgb_color in phase_colors.items():
                        r = int(rgb_color[0] * 255)
                        g = int(rgb_color[1] * 255)
                        b = int(rgb_color[2] * 255)
                        hex_color = f"#{r:02x}{g:02x}{b:02x}"
                        if hasattr(self.pyvista_viewer, 'set_phase_color'):
                            self.pyvista_viewer.set_phase_color(phase_id, hex_color)
                            self.logger.debug(f"Set PyVista color for phase {phase_id}: {hex_color}")

                    print(f"Calling load_voxel_data...")
                    self.logger.info(f"Loading voxel data into PyVista viewer...")
                    success = self.pyvista_viewer.load_voxel_data(voxel_data, phase_mapping)
                    print(f"load_voxel_data returned: {success}")
                    self.logger.info(f"PyVista load_voxel_data returned: {success}")

                    if not success:
                        self._show_diagnostic_message("3D Load Failed",
                            f"PyVista failed to load the microstructure data.\n\n"
                            f"File: {file_path}\n"
                            f"Shape: {voxel_data.shape}\n"
                            f"Phases: {np.unique(voxel_data)}\n\n"
                            f"Check console output for details.")

                    print(f"=== END DIAGNOSTIC ===\n")
                    self._update_time_display()
                else:
                    self.logger.error("Failed to read microstructure file data")
                    self._show_diagnostic_message("File Read Failed",
                        f"Failed to read microstructure file:\n{file_path}\n\nCheck that the file exists and is a valid .img file.")
            else:
                print("ERROR: pyvista_viewer is None!")
                self._show_diagnostic_message("No 3D Viewer", "VTK 3D viewer widget was not initialized.")

        except Exception as e:
            self.logger.error(f"Error loading initial microstructure: {e}")
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR loading microstructure:\n{error_details}")
            self._show_diagnostic_message("Load Error", f"Error loading microstructure:\n\n{str(e)}\n\nSee console for full traceback.")

    def _show_diagnostic_message(self, title: str, message: str):
        """Show a diagnostic message dialog to the user."""
        try:
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=title
            )
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
        except Exception as e:
            print(f"Failed to show diagnostic dialog: {e}")
    
    def _start_preloading(self) -> None:
        """Start background preloading of all microstructure data."""
        try:
            import threading
            
            if len(self.microstructure_files) > 1:
                self.logger.info(f"Starting background preloading of {len(self.microstructure_files)} microstructures...")
                
                # Start preloading in background thread
                preload_thread = threading.Thread(target=self._preload_all_microstructures, daemon=True)
                preload_thread.start()
            else:
                self.preloading_complete = True
                # For single microstructures, update status immediately
                self._update_preloading_status_complete()
                
        except Exception as e:
            self.logger.error(f"Error starting preloading: {e}")
    
    def _preload_all_microstructures(self) -> None:
        """Background thread to preload all microstructure data."""
        try:
            # Cache the first one (already loaded) 
            if self.current_time_index == 0 and len(self.microstructure_files) > 0:
                time_hours, file_path = self.microstructure_files[0]
                if file_path not in [str(fp) for _, fp in self.microstructure_files if _ in self.cached_voxel_data]:
                    voxel_data = self._read_microstructure_file(file_path)
                    if voxel_data is not None:
                        self.cached_voxel_data[0] = voxel_data
            
            # Preload remaining microstructures
            for index, (time_hours, file_path) in enumerate(self.microstructure_files):
                if index == self.current_time_index:
                    continue  # Skip currently loaded one
                    
                self.logger.info(f"Preloading microstructure {index + 1}/{len(self.microstructure_files)}: {time_hours}h")
                voxel_data = self._read_microstructure_file(file_path)
                
                if voxel_data is not None:
                    self.cached_voxel_data[index] = voxel_data
                else:
                    self.logger.warning(f"Failed to preload microstructure at index {index}")
            
            self.preloading_complete = True
            self.logger.info(f"Preloading complete! Cached {len(self.cached_voxel_data)} microstructures")
            
            # Update UI status on main thread
            from gi.repository import GLib
            GLib.idle_add(self._update_preloading_status_complete)
            
        except Exception as e:
            self.logger.error(f"Error during preloading: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _update_preloading_status_complete(self) -> bool:
        """Update UI to show preloading is complete (called on main thread)."""
        try:
            if self.info_label and self.operation:
                mapping_source = "THAMES" if self.thames_color_mapping else "VCCTL"
                self.info_label.set_markup(
                    f"<b>Operation:</b> {self.operation.name}\n"
                    f"<b>Microstructures:</b> {len(self.microstructure_files)} time points\n"
                    f"<b>Phase Colors:</b> {mapping_source}\n"
                    f"<b>Status:</b> <span color='green'>Ready - All data cached</span>\n"
                    f"<i>Note: 3D visualization rebuilding takes ~2 seconds per time point</i>"
                )
        except Exception as e:
            self.logger.error(f"Error updating preloading status: {e}")
        
        return False  # Don't repeat this idle callback
    
    def _read_microstructure_file(self, file_path: str) -> Optional[np.ndarray]:
        """Read a VCCTL or THAMES microstructure file and return voxel data.

        Supports both formats:
        - VCCTL: Header lines like "X_Size: 100"
        - THAMES: Header lines like "#THAMES: X_Size: 100"
        """
        try:
            from pathlib import Path

            file_path = Path(file_path)
            self.logger.info(f"Reading microstructure file: {file_path}")

            with open(file_path, 'r') as f:
                lines = f.readlines()

            # Parse header to get dimensions
            # Support both VCCTL format (e.g., "X_Size: 100")
            # and THAMES format (e.g., "#THAMES: X_Size: 100")
            x_size = y_size = z_size = None
            header_end = 0
            is_thames_format = False

            for i, line in enumerate(lines):
                line = line.strip()

                # Check for THAMES format and strip prefix if present
                if line.startswith('#THAMES:'):
                    is_thames_format = True
                    line = line[8:].strip()  # Remove "#THAMES:" prefix

                if line.startswith('X_Size:'):
                    x_size = int(line.split(':')[1].strip())
                elif line.startswith('Y_Size:'):
                    y_size = int(line.split(':')[1].strip())
                elif line.startswith('Z_Size:'):
                    z_size = int(line.split(':')[1].strip())
                elif line.startswith('Image_Resolution:'):
                    # This is typically the last header line
                    header_end = i + 1
                    break

            if is_thames_format:
                self.logger.info("Detected THAMES microstructure format")
                    
            if not all([x_size, y_size, z_size]):
                self.logger.error(f"Could not parse dimensions from {file_path}")
                return None
                
            # Read voxel data (skip header lines)
            data_lines = lines[header_end:]
            
            # Parse the voxel data - each line can contain multiple integers
            voxel_data = []
            for line_num, line in enumerate(data_lines):
                line = line.strip()
                if line and not line.startswith('#'):  # Skip comments and empty lines
                    try:
                        # Split line and convert to integers
                        values = [int(x) for x in line.split()]
                        voxel_data.extend(values)
                    except ValueError as e:
                        self.logger.warning(f"Could not parse line {header_end + line_num + 1}: {line[:50]}... Error: {e}")
                        continue
            
            # Reshape to 3D array
            total_voxels = x_size * y_size * z_size
            self.logger.info(f"Expected {total_voxels} voxels, got {len(voxel_data)} values")
            
            if len(voxel_data) >= total_voxels:
                voxel_array = np.array(voxel_data[:total_voxels]).reshape((z_size, y_size, x_size))
                self.logger.info(f"Successfully loaded microstructure: {x_size}x{y_size}x{z_size}")
                self.logger.info(f"Unique phases in data: {np.unique(voxel_array)}")
                return voxel_array
            else:
                self.logger.error(f"Insufficient data: got {len(voxel_data)}, expected {total_voxels}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error reading microstructure file {file_path}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def _get_vcctl_phase_mapping(self, use_cache: bool = True) -> Tuple[Dict[int, str], Dict[int, Tuple[float, float, float]]]:
        """Get VCCTL phase mapping and colors from colors.csv."""
        try:
            # Return cached colors if available and requested
            if use_cache and self.cached_phase_mapping is not None and self.cached_phase_colors is not None:
                return self.cached_phase_mapping, self.cached_phase_colors

            # Import pandas here to avoid dependency issues
            import pandas as pd
            import sys

            # Get path to colors.csv - handle both development and packaged app
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # PyInstaller packaged app
                colors_file = Path(sys._MEIPASS) / "colors" / "colors.csv"
            else:
                # Development environment
                colors_file = Path(__file__).parent.parent.parent.parent.parent / "colors" / "colors.csv"

            if not colors_file.exists():
                self.logger.warning(f"Colors file not found: {colors_file}")
                return self._get_default_phase_mapping()
            
            # Read colors CSV - skip malformed header and use manual parsing
            with open(colors_file, 'r') as f:
                lines = f.readlines()
            
            phase_mapping = {}
            phase_colors = {}
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                if not line or line.startswith('Phase,id') or line.startswith('#'):
                    continue
                    
                try:
                    # Split by comma and clean up values
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) < 4:
                        continue
                        
                    phase_id = int(parts[0])
                    phase_name = parts[1] if parts[1] else f"Phase_{phase_id}"
                    
                    # Handle RGB values - fix common typos
                    red_str = parts[2].replace('o', '0')  # Fix 'o' -> '0' typo
                    green_str = parts[3].replace('.', ',') if '.' in parts[3] and ',' not in parts[3] else parts[3]
                    blue_str = parts[4] if len(parts) > 4 else '0'
                    
                    # Parse RGB values
                    red = float(red_str.split(',')[0]) if ',' in red_str else float(red_str)
                    green = float(green_str.split(',')[-1]) if ',' in green_str else float(green_str)
                    blue = float(blue_str)
                    
                    # Normalize RGB (0-255) to (0-1) for PyVista
                    red_norm = red / 255.0
                    green_norm = green / 255.0
                    blue_norm = blue / 255.0
                    
                    phase_mapping[phase_id] = phase_name
                    phase_colors[phase_id] = (red_norm, green_norm, blue_norm)
                    
                    self.logger.debug(f"Loaded phase {phase_id}: {phase_name} = RGB({red}, {green}, {blue})")
                    
                except (ValueError, TypeError, IndexError) as e:
                    self.logger.warning(f"Skipping invalid line {line_num + 1} in colors.csv: '{line}' - Error: {e}")
            
            self.logger.info(f"Loaded {len(phase_mapping)} VCCTL phase colors")
            
            # Cache the results for future use
            self.cached_phase_mapping = phase_mapping
            self.cached_phase_colors = phase_colors
            
            return phase_mapping, phase_colors
            
        except Exception as e:
            self.logger.error(f"Error loading VCCTL colors: {e}")
            return self._get_default_phase_mapping()
    
    def _get_default_phase_mapping(self) -> Tuple[Dict[int, str], Dict[int, Tuple[float, float, float]]]:
        """Fallback phase mapping with THAMES default colors and naming."""
        # THAMES phase ID conventions (from phase_id_mapping_service.py):
        # ID 0: VOID (empty pores)
        # ID 1: Electrolyte (aqueous solution)
        # ID 2-7: Clinker phases (Alite, Belite, Aluminate, Ferrite, Arcanite, Thenardite)
        # ID 8: Aggregate
        # ID 9+: Other phases
        phase_mapping = {
            0: "VOID",
            1: "Electrolyte",
            2: "Alite",
            3: "Belite",
            4: "Aluminate",
            5: "Ferrite",
            6: "Arcanite",
            7: "Thenardite",
            8: "Aggregate",
            9: "Gypsum",
            10: "Bassanite",
            11: "Anhydrite",
            12: "Calcite",
        }

        # Default colors using THAMES conventions (RGB normalized 0-1)
        phase_colors = {
            0: (0.0, 0.0, 0.0),       # Black for VOID
            1: (0.0, 0.078, 0.098),   # Dark blue for Electrolyte (0,20,25)
            2: (0.165, 0.165, 0.824), # Blue for Alite (42,42,210)
            3: (0.545, 0.31, 0.075),  # Brown for Belite (139,79,19)
            4: (0.698, 0.698, 0.698), # Light gray for Aluminate (178,178,178)
            5: (0.992, 0.992, 0.992), # White for Ferrite (253,253,253)
            6: (1.0, 0.0, 0.0),       # Red for Arcanite (255,0,0)
            7: (1.0, 0.078, 0.0),     # Red-orange for Thenardite (255,20,0)
            8: (1.0, 0.753, 0.255),   # Gold for Aggregate (255,192,65)
            9: (1.0, 1.0, 0.0),       # Yellow for Gypsum
            10: (1.0, 0.94, 0.34),    # Light yellow for Bassanite
            11: (1.0, 1.0, 0.5),      # Pale yellow for Anhydrite
            12: (0.0, 0.8, 0.0),      # Green for Calcite
        }

        return phase_mapping, phase_colors
    
    def _apply_vcctl_colors(self, phase_colors: Dict[int, Tuple[float, float, float]]) -> None:
        """Apply VCCTL colors to the PyVista viewer."""
        try:
            # Convert RGB tuples to hex strings and apply to PyVista viewer
            for phase_id, rgb_color in phase_colors.items():
                # Convert normalized RGB (0-1) to 8-bit RGB (0-255) and then to hex
                r = int(rgb_color[0] * 255)
                g = int(rgb_color[1] * 255) 
                b = int(rgb_color[2] * 255)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
                
                # Use PyVista viewer's set_phase_color method
                if hasattr(self.pyvista_viewer, 'set_phase_color'):
                    self.pyvista_viewer.set_phase_color(phase_id, hex_color)
                    self.logger.debug(f"Applied VCCTL color {hex_color} to phase {phase_id}")
            
            # Don't call _create_phase_meshes() as it can hang - colors will be applied on next load
            self.logger.info(f"Set {len(phase_colors)} VCCTL phase colors for future use")
                    
        except Exception as e:
            self.logger.warning(f"Could not apply VCCTL colors: {e}")
            import traceback
            self.logger.warning(traceback.format_exc())
    
    def _load_microstructure_at_index(self, index: int) -> None:
        """Load microstructure at specific time index."""
        try:
            if 0 <= index < len(self.microstructure_files):
                time_hours, file_path = self.microstructure_files[index]
                self.logger.info(f"_load_microstructure_at_index({index}): Loading {file_path} at {time_hours}h")
                
                # Get microstructure data (cached if available, otherwise read from file)
                voxel_data = None
                if index in self.cached_voxel_data:
                    voxel_data = self.cached_voxel_data[index]
                    self.logger.info(f"Using cached voxel data for index {index}")
                else:
                    self.logger.info(f"Reading voxel data from file for index {index}")
                    voxel_data = self._read_microstructure_file(file_path)
                    # Cache it for future use
                    if voxel_data is not None:
                        self.cached_voxel_data[index] = voxel_data
                
                if voxel_data is not None and self.pyvista_viewer:
                    # Use cached phase mapping and colors for speed (THAMES or VCCTL)
                    phase_mapping, phase_colors = self._get_phase_mapping(use_cache=True)
                    
                    # Update time display immediately to show user we're responding
                    self.current_time_index = index
                    self._update_time_display_with_status("Loading 3D visualization...")
                    
                    self.logger.info(f"Calling PyVista load_voxel_data for index {index}...")
                    success = self.pyvista_viewer.load_voxel_data(voxel_data, phase_mapping)
                    self.logger.info(f"PyVista load_voxel_data returned: {success}")
                    
                    # Update display again to remove loading status
                    self._update_time_display()
                    self.logger.info(f"Successfully loaded microstructure at index {index}")
                else:
                    if voxel_data is None:
                        self.logger.error(f"Failed to read voxel data for index {index}")
                    if not self.pyvista_viewer:
                        self.logger.error(f"PyVista viewer is None for index {index}")
            else:
                self.logger.error(f"Index {index} out of range (0-{len(self.microstructure_files)-1})")
                    
        except Exception as e:
            self.logger.error(f"Error loading microstructure at index {index}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _on_time_changed(self, slider) -> None:
        """Handle time slider value change."""
        try:
            new_index = int(slider.get_value())
            self.logger.info(f"Time slider changed to index {new_index} (was {self.current_time_index})")
            
            if 0 <= new_index < len(self.microstructure_files):
                if new_index != self.current_time_index:  # Only load if actually changed
                    self.current_time_index = new_index
                    time_hours, file_path = self.microstructure_files[new_index]
                    self.logger.info(f"Loading microstructure at {time_hours}h: {file_path}")
                    self._load_microstructure_at_index(new_index)
                else:
                    self.logger.debug(f"Time slider at same index {new_index}, skipping reload")
            else:
                self.logger.warning(f"Time slider index {new_index} out of range (0-{len(self.microstructure_files)-1})")
                
        except Exception as e:
            self.logger.error(f"Error handling time change: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _on_previous_clicked(self, button) -> None:
        """Handle previous button click."""
        if self.current_time_index > 0:
            self.current_time_index -= 1
            self.time_slider.set_value(self.current_time_index)
            self._load_microstructure_at_index(self.current_time_index)
    
    def _on_next_clicked(self, button) -> None:
        """Handle next button click."""
        if self.current_time_index < len(self.microstructure_files) - 1:
            self.current_time_index += 1
            self.time_slider.set_value(self.current_time_index)
            self._load_microstructure_at_index(self.current_time_index)
    
    
    def _update_time_display(self) -> None:
        """Update the time display label."""
        if 0 <= self.current_time_index < len(self.microstructure_files):
            time_hours, file_path = self.microstructure_files[self.current_time_index]

            if time_hours < 0:  # Initial microstructure (before hydration)
                time_text = "Initial (before hydration)"
            elif time_hours >= 999999:  # Final microstructure
                time_text = "Final Hydrated State"
            elif time_hours < 1:
                time_text = f"{time_hours * 60:.1f} minutes"
            elif time_hours < 24:
                time_text = f"{time_hours:.2f} hours"
            else:
                days = time_hours / 24.0
                time_text = f"{days:.2f} days ({time_hours:.1f} hours)"

            self.time_label.set_markup(f"<b>Time: {time_text}</b>")
    
    def _update_time_display_with_status(self, status: str) -> None:
        """Update the time display label with a status message."""
        if 0 <= self.current_time_index < len(self.microstructure_files):
            time_hours, file_path = self.microstructure_files[self.current_time_index]

            if time_hours < 0:  # Initial microstructure (before hydration)
                time_text = "Initial (before hydration)"
            elif time_hours >= 999999:  # Final microstructure
                time_text = "Final Hydrated State"
            elif time_hours < 1:
                time_text = f"{time_hours * 60:.1f} minutes"
            elif time_hours < 24:
                time_text = f"{time_hours:.2f} hours"
            else:
                days = time_hours / 24.0
                time_text = f"{days:.2f} days ({time_hours:.1f} hours)"

            self.time_label.set_markup(f"<b>Time: {time_text}</b> - <span color='orange'>{status}</span>")
    
    def _on_export_clicked(self, button) -> None:
        """Handle export view button click."""
        try:
            if self.pyvista_viewer:
                # Use the PyVista viewer's export functionality
                self.pyvista_viewer._save_screenshot()
                
        except Exception as e:
            self.logger.error(f"Error exporting view: {e}")
            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Export Error"
            )
            dialog.format_secondary_text(f"Failed to export view: {e}")
            dialog.run()
            dialog.destroy()
    
    # ==================== Data Plots Tab Methods ====================

    def _load_csv_files(self) -> None:
        """Load CSV files from the Result/ subdirectory for the data plots tab."""
        try:
            self.logger.info(f"_load_csv_files called, output_path={self.output_path}")

            if not self.output_path:
                self.logger.warning("No output path available for CSV loading")
                return

            # Check for Result/ subdirectory (THAMES hydration output location)
            result_path = self.output_path / "Result"
            self.logger.info(f"Looking for Result/ at: {result_path}, exists={result_path.exists()}")

            if not result_path.exists():
                self.logger.info(f"No Result/ subdirectory found in {self.output_path}")
                return

            # Define the expected CSV files with user-friendly display names
            csv_file_mappings = {
                "Phase Volumes": "Microstructure.csv",
                "Solution Chemistry": "Solution.csv",
                "Saturation Indices": "SI.csv",
                "Surface Areas": "SurfaceAreas.csv",
                "Enthalpy": "Enthalpy.csv",
            }

            # Find CSV files matching the expected names
            self.csv_files.clear()
            for display_name, filename in csv_file_mappings.items():
                # Look for files with the operation name prefix
                pattern = f"*_{filename}"
                matches = list(result_path.glob(pattern))
                if matches:
                    self.csv_files[display_name] = matches[0]
                    self.logger.info(f"Found CSV file: {display_name} -> {matches[0].name}")
                else:
                    # Try without prefix
                    direct_match = result_path / filename
                    if direct_match.exists():
                        self.csv_files[display_name] = direct_match
                        self.logger.info(f"Found CSV file: {display_name} -> {filename}")

            # Populate the combo box
            self.logger.info(f"Found {len(self.csv_files)} CSV files, data_file_combo exists: {self.data_file_combo is not None}")

            if self.data_file_combo:
                self.data_file_combo.remove_all()
                for display_name in self.csv_files.keys():
                    self.data_file_combo.append_text(display_name)
                    self.logger.info(f"Added to combo: {display_name}")

                if self.csv_files:
                    self.data_file_combo.set_active(0)
                    self.logger.info(f"Loaded {len(self.csv_files)} CSV files for data plots, set active=0")
                else:
                    self.logger.info("No CSV files found in Result/ directory")
            else:
                self.logger.warning("data_file_combo is None - cannot populate")

        except Exception as e:
            self.logger.error(f"Error loading CSV files: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def _on_data_file_changed(self, combo) -> None:
        """Handle data file selection change."""
        try:
            selected_text = combo.get_active_text()
            if not selected_text or selected_text not in self.csv_files:
                return

            filepath = self.csv_files[selected_text]
            self._load_csv_data(filepath)

        except Exception as e:
            self.logger.error(f"Error handling data file change: {e}")

    def _load_csv_data(self, filepath: Path) -> None:
        """Load CSV data and populate the variables list."""
        try:
            self.current_csv_data = pd.read_csv(filepath)
            columns = list(self.current_csv_data.columns)

            # Clear and populate variables list
            self.y_liststore.clear()

            # Find the time column (should be first column)
            time_col = None
            for col in columns:
                if col.lower() in ['time(h)', 'time', 'time_h', 'time_hours']:
                    time_col = col
                    break

            # Add non-time columns as plottable variables
            for column in columns:
                if column != time_col:
                    # Create cleaner display name
                    display_name = column
                    self.y_liststore.append([False, display_name, column])

            # Auto-select first few variables for convenience
            iter_var = self.y_liststore.get_iter_first()
            selected_count = 0
            while iter_var and selected_count < 3:
                self.y_liststore.set_value(iter_var, 0, True)
                iter_var = self.y_liststore.iter_next(iter_var)
                selected_count += 1

            self.logger.info(f"Loaded {len(columns)} columns from {filepath.name}")

        except Exception as e:
            self.logger.error(f"Error loading CSV data from {filepath}: {e}")
            self._show_plot_error(f"Failed to load data: {e}")

    def _on_plot_variable_toggled(self, renderer, path) -> None:
        """Handle variable checkbox toggle."""
        try:
            iter_var = self.y_liststore.get_iter(path)
            current_value = self.y_liststore.get_value(iter_var, 0)
            self.y_liststore.set_value(iter_var, 0, not current_value)
        except Exception as e:
            self.logger.error(f"Error toggling variable: {e}")

    def _on_select_all_clicked(self, button) -> None:
        """Select all variables."""
        try:
            iter_var = self.y_liststore.get_iter_first()
            while iter_var:
                self.y_liststore.set_value(iter_var, 0, True)
                iter_var = self.y_liststore.iter_next(iter_var)
        except Exception as e:
            self.logger.error(f"Error selecting all: {e}")

    def _on_deselect_all_clicked(self, button) -> None:
        """Deselect all variables."""
        try:
            iter_var = self.y_liststore.get_iter_first()
            while iter_var:
                self.y_liststore.set_value(iter_var, 0, False)
                iter_var = self.y_liststore.iter_next(iter_var)
        except Exception as e:
            self.logger.error(f"Error deselecting all: {e}")

    def _get_selected_variables(self) -> List[str]:
        """Get list of selected variable column names."""
        selected = []
        try:
            iter_var = self.y_liststore.get_iter_first()
            while iter_var:
                if self.y_liststore.get_value(iter_var, 0):  # If selected
                    col_name = self.y_liststore.get_value(iter_var, 2)
                    selected.append(col_name)
                iter_var = self.y_liststore.iter_next(iter_var)
        except Exception as e:
            self.logger.error(f"Error getting selected variables: {e}")
        return selected

    def _on_create_data_plot_clicked(self, button) -> None:
        """Create the data plot based on current selections."""
        try:
            if self.current_csv_data is None:
                self._show_plot_error("No data loaded. Please select a data category.")
                return

            selected_vars = self._get_selected_variables()
            if not selected_vars:
                self._show_plot_error("Please select at least one variable to plot.")
                return

            # Find time column
            time_col = None
            for col in self.current_csv_data.columns:
                if col.lower() in ['time(h)', 'time', 'time_h', 'time_hours']:
                    time_col = col
                    break

            if time_col is None:
                self._show_plot_error("No time column found in data.")
                return

            # Get time data and convert to days for better readability
            time_data = self.current_csv_data[time_col]
            time_days = time_data / 24.0  # Convert hours to days

            # Clear and create new plot
            self.plot_figure.clear()
            ax = self.plot_figure.add_subplot(111)

            # Get line width
            line_width = self.line_width_spin.get_value() if hasattr(self, 'line_width_spin') else 1.5

            # Get color scheme
            color_scheme = self.color_scheme_combo.get_active_text() if hasattr(self, 'color_scheme_combo') else "Tab10 (Default)"
            colors = self._get_color_palette(color_scheme, len(selected_vars))

            # Plot each selected variable
            for i, var in enumerate(selected_vars):
                y_data = self.current_csv_data[var]
                color = colors[i % len(colors)]
                ax.plot(time_days, y_data, linewidth=line_width, color=color, label=var)

            # Set log scale if requested
            if hasattr(self, 'log_x_check') and self.log_x_check.get_active():
                ax.set_xscale('log')

            if hasattr(self, 'log_y_check') and self.log_y_check.get_active():
                ax.set_yscale('log')

            # Apply custom axis ranges if specified
            x_min, x_max = self._parse_range(self.x_min_entry, self.x_max_entry)
            y_min, y_max = self._parse_range(self.y_min_entry, self.y_max_entry)

            if x_min is not None or x_max is not None:
                current_xlim = ax.get_xlim()
                ax.set_xlim(
                    x_min if x_min is not None else current_xlim[0],
                    x_max if x_max is not None else current_xlim[1]
                )

            if y_min is not None or y_max is not None:
                current_ylim = ax.get_ylim()
                ax.set_ylim(
                    y_min if y_min is not None else current_ylim[0],
                    y_max if y_max is not None else current_ylim[1]
                )

            # Configure plot
            ax.set_xlabel("Time (days)", fontsize=10)
            ax.set_ylabel("Value", fontsize=10)
            ax.grid(True, alpha=0.3)

            # Get category name for title
            category = self.data_file_combo.get_active_text() or "Data"
            ax.set_title(f"{category} vs Time", fontsize=11, fontweight='bold')

            # Add legend (outside plot if many variables)
            if len(selected_vars) <= 6:
                ax.legend(loc='best', fontsize=8)
            else:
                ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=7)

            # Adjust layout
            self.plot_figure.tight_layout()
            self.plot_canvas.draw()

            self.logger.info(f"Created plot with {len(selected_vars)} variables")

        except Exception as e:
            self.logger.error(f"Error creating plot: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self._show_plot_error(f"Failed to create plot: {e}")

    def _on_export_data_plot_clicked(self, button) -> None:
        """Export the current data plot to a file."""
        try:
            if self.plot_figure is None:
                self._show_plot_error("No plot to export.")
                return

            # Create file chooser dialog
            dialog = Gtk.FileChooserDialog(
                title="Export Plot",
                parent=self,
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )

            # Add file filters
            filter_png = Gtk.FileFilter()
            filter_png.set_name("PNG images")
            filter_png.add_pattern("*.png")
            dialog.add_filter(filter_png)

            filter_pdf = Gtk.FileFilter()
            filter_pdf.set_name("PDF files")
            filter_pdf.add_pattern("*.pdf")
            dialog.add_filter(filter_pdf)

            filter_svg = Gtk.FileFilter()
            filter_svg.set_name("SVG files")
            filter_svg.add_pattern("*.svg")
            dialog.add_filter(filter_svg)

            # Set default filename
            category = self.data_file_combo.get_active_text() or "plot"
            category_safe = category.replace(" ", "_").lower()
            if self.operation:
                dialog.set_current_name(f"{self.operation.name}_{category_safe}.png")
            else:
                dialog.set_current_name(f"{category_safe}.png")

            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename()
                self.plot_figure.savefig(filename, dpi=300, bbox_inches='tight')
                self.logger.info(f"Plot exported to: {filename}")

                # Show success message
                success_dialog = Gtk.MessageDialog(
                    transient_for=self,
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Export Successful"
                )
                success_dialog.format_secondary_text(f"Plot saved to:\n{filename}")
                success_dialog.run()
                success_dialog.destroy()

            dialog.destroy()

        except Exception as e:
            self.logger.error(f"Error exporting plot: {e}")
            self._show_plot_error(f"Failed to export plot: {e}")

    def _get_color_palette(self, scheme_name: str, num_colors: int) -> List:
        """Get a color palette based on the selected scheme."""
        scheme_map = {
            "Tab10 (Default)": plt.cm.tab10,
            "Set1": plt.cm.Set1,
            "Dark2": plt.cm.Dark2,
            "Paired": plt.cm.Paired,
            "Pastel1": plt.cm.Pastel1,
        }

        if scheme_name == "Single Color":
            # Return a single blue color repeated
            return [(0.2, 0.4, 0.8, 1.0)] * num_colors

        cmap = scheme_map.get(scheme_name, plt.cm.tab10)
        return [cmap(i / max(num_colors - 1, 1)) for i in range(num_colors)]

    def _parse_range(self, min_entry: Gtk.Entry, max_entry: Gtk.Entry) -> Tuple[Optional[float], Optional[float]]:
        """Parse min/max range from entry widgets."""
        min_val = None
        max_val = None

        try:
            min_text = min_entry.get_text().strip()
            if min_text:
                min_val = float(min_text)
        except ValueError:
            pass  # Invalid input, use auto

        try:
            max_text = max_entry.get_text().strip()
            if max_text:
                max_val = float(max_text)
        except ValueError:
            pass  # Invalid input, use auto

        return min_val, max_val

    def _show_plot_error(self, message: str) -> None:
        """Show an error dialog for plot-related errors."""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Plot Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    # ==================== Dialog Lifecycle Methods ====================

    def _on_delete_event(self, widget, event):
        """Handle window close event - hide instead of destroy to avoid PyVista segfault."""
        try:
            self.logger.info("Window close requested - hiding dialog instead of destroying")
            self.hide()
            self._start_auto_cleanup_timer()
            # Return True to prevent default destroy behavior
            return True
        except Exception as e:
            self.logger.error(f"Error in delete event handler: {e}")
            # If hiding fails, allow destruction to prevent hanging
            return False
    
    def _on_response(self, dialog, response_id):
        """Handle dialog response (Close button clicked)."""
        if response_id == Gtk.ResponseType.CLOSE:
            self.logger.info("Close button clicked - hiding dialog instead of destroying")
            self.hide()
            self._start_auto_cleanup_timer()
            # Don't let default response handling proceed to avoid destruction
    
    def _cleanup_pyvista(self):
        """Clean up VTK 3D viewer to prevent segfaults."""
        # Prevent double cleanup
        if self.cleanup_performed:
            self.logger.info("VTK 3D viewer cleanup already performed, skipping")
            return

        try:
            self.cleanup_performed = True
            self.logger.info("Starting VTK 3D viewer cleanup...")

            # First disable all UI interactions to prevent further calls to VTK viewer
            if hasattr(self, 'time_slider') and self.time_slider:
                self.time_slider.set_sensitive(False)
            
            # Clear cached data first to free memory
            if hasattr(self, 'cached_voxel_data'):
                self.cached_voxel_data.clear()
            if hasattr(self, 'cached_phase_meshes'):
                self.cached_phase_meshes.clear()
            
            # Now try to cleanup VTK viewer safely with minimum operations
            if hasattr(self, 'pyvista_viewer') and self.pyvista_viewer:
                try:
                    # Try to clear any active plots/meshes first
                    if hasattr(self.pyvista_viewer, 'renderer') and self.pyvista_viewer.renderer:
                        self.pyvista_viewer.renderer.RemoveAllViewProps()

                    # Try to call cleanup if it exists
                    if hasattr(self.pyvista_viewer, 'cleanup'):
                        self.pyvista_viewer.cleanup()

                except Exception as cleanup_error:
                    # Don't let VTK cleanup errors stop us
                    self.logger.warning(f"VTK cleanup method failed (continuing anyway): {cleanup_error}")

                # Clear reference regardless of cleanup success/failure
                self.pyvista_viewer = None
                self.logger.info("VTK 3D viewer reference cleared")

            self.logger.info("VTK 3D viewer cleanup completed")
                
        except Exception as e:
            # If cleanup fails, just log it and continue - don't let it crash the app
            self.logger.warning(f"Error during VTK 3D viewer cleanup (ignoring): {e}")
            # Still mark as performed to prevent retry
            self.cleanup_performed = True
    
    def _start_auto_cleanup_timer(self):
        """Start timer for automatic memory cleanup of hidden dialogs."""
        try:
            import time
            from gi.repository import GLib
            
            self.hidden_time = time.time()
            
            # Cancel existing timer if any
            if self.auto_cleanup_timer:
                GLib.source_remove(self.auto_cleanup_timer)
            
            # Start timer for 5 minutes (300 seconds)
            self.auto_cleanup_timer = GLib.timeout_add_seconds(
                300,  # 5 minutes
                self._auto_cleanup_memory
            )
            
            self.logger.info("Started automatic memory cleanup timer (5 minutes)")
            
        except Exception as e:
            self.logger.warning(f"Failed to start auto cleanup timer: {e}")
    
    def _auto_cleanup_memory(self):
        """Automatically clean up memory from hidden dialogs (safe cleanup only)."""
        try:
            self.logger.info("Starting automatic memory cleanup for hidden dialog...")
            
            # Only clear cached data - this is safe and frees the most memory
            cache_cleared = False
            
            if hasattr(self, 'cached_voxel_data') and self.cached_voxel_data:
                data_count = len(self.cached_voxel_data)
                self.cached_voxel_data.clear()
                self.logger.info(f"Cleared {data_count} cached voxel datasets")
                cache_cleared = True
            
            if hasattr(self, 'cached_phase_meshes') and self.cached_phase_meshes:
                mesh_count = len(self.cached_phase_meshes)
                self.cached_phase_meshes.clear()
                self.logger.info(f"Cleared {mesh_count} cached phase meshes")
                cache_cleared = True
            
            if cache_cleared:
                self.logger.info("Automatic memory cleanup completed - cached data cleared")
            else:
                self.logger.info("Automatic memory cleanup - no cached data to clear")
            
            # Clear the timer reference
            self.auto_cleanup_timer = None
            
            # Return False to stop the timer from repeating
            return False
            
        except Exception as e:
            self.logger.warning(f"Error during automatic memory cleanup: {e}")
            # Clear timer reference even if cleanup failed
            self.auto_cleanup_timer = None
            return False
    
    def _cancel_auto_cleanup_timer(self):
        """Cancel the automatic cleanup timer if dialog is shown again."""
        try:
            if self.auto_cleanup_timer:
                from gi.repository import GLib
                GLib.source_remove(self.auto_cleanup_timer)
                self.auto_cleanup_timer = None
                self.logger.info("Cancelled automatic memory cleanup timer")
        except Exception as e:
            self.logger.warning(f"Error cancelling auto cleanup timer: {e}")
    


# Register the widget
GObject.type_register(HydrationResultsViewer)
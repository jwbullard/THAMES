#!/usr/bin/env python3
"""
Hydration Product Selector Widget

GTK widget for selecting which phases to include in a THAMES simulation.
Shows phases grouped by category with checkboxes, and allows users to configure
kinetic models, affinity, and C-S-H special parameters.

Phases include:
- Microstructure phases (from the input microstructure - always selected, non-removable)
- Hydration products (user-selectable products that can form during hydration)

All phases can have kinetic models edited (or set to "Thermodynamic" for no kinetics).
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject, Pango, GdkPixbuf
import logging
from typing import List, Dict, Optional, Any, Set

from app.services.hydration_products_service import (
    HydrationProductsService,
    HydrationProductData,
    ProductCategory,
    get_hydration_products_service,
    DEFAULT_CONTACT_ANGLE,
)
from app.services.kinetic_defaults_service import (
    KineticDefaultsService,
    get_kinetic_defaults_service,
)
from app.utils.icon_utils import load_carbon_icon


class HydrationProductSelectorWidget(Gtk.Box):
    """
    Widget for selecting phases for THAMES hydration simulation.

    Features:
    - Microstructure phases shown at top (always selected, non-removable)
    - Hydration products grouped by category (C-S-H, CH, AFt, AFm, etc.)
    - Checkbox selection with suggested products pre-selected
    - Kinetic model display and editing for all phases
    - Double-click or button to configure affinity
    - Special configuration for C-S-H (PSD, Rd values)
    - Search/filter functionality
    """

    __gsignals__ = {
        # Emitted when selection changes
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        # Emitted when user double-clicks a phase to configure it (opens combined dialog)
        'configure-phase': (GObject.SignalFlags.RUN_FIRST, None, (str, bool)),  # gems_name, has_csh_data
        # Emitted when user wants to configure a product's affinity (button click)
        'configure-affinity': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # gems_name
        # Emitted when user wants to configure C-S-H special data (button click)
        'configure-csh': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # gems_name
        # Emitted when user wants to configure kinetic model (button click)
        'configure-kinetics': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # gems_name
    }

    def __init__(self, cement_type: str = "portland"):
        """
        Initialize the product selector.

        Args:
            cement_type: Initial cement type for suggested products
                        ('portland', 'blended', 'pozzolanic', 'limestone', 'slag')
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.cement_type = cement_type
        self.logger = logging.getLogger('THAMES.HydrationProductSelector')
        self.service = get_hydration_products_service()
        self.kinetic_defaults = get_kinetic_defaults_service()

        # Track selected products and their configurations
        self.selected_products: Set[str] = set()
        self.product_configurations: Dict[str, Dict[str, Any]] = {}

        # Track microstructure phases (always selected, non-removable)
        self.microstructure_phases: Set[str] = set()

        # Track kinetic configurations for all phases
        self.kinetic_configurations: Dict[str, Dict[str, Any]] = {}

        # Load Carbon edit icon for the config column
        self.edit_icon_pixbuf: Optional[GdkPixbuf.Pixbuf] = load_carbon_icon("edit", 16)

        # Build UI
        self._build_ui()

        # Initialize with suggested products
        self._select_suggested_products()

    def _build_ui(self):
        """Build the widget UI."""
        # Header with cement type selector (on the left)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_bottom(5)

        # Cement type selector for suggested products
        cement_label = Gtk.Label(label="Cement Type:")
        header.pack_start(cement_label, False, False, 0)

        self.cement_combo = Gtk.ComboBoxText()
        cement_types = ["portland", "blended", "pozzolanic", "limestone", "slag"]
        for ct in cement_types:
            self.cement_combo.append_text(ct.capitalize())
        self.cement_combo.set_active(cement_types.index(self.cement_type.lower())
                                      if self.cement_type.lower() in cement_types else 0)
        self.cement_combo.connect('changed', self._on_cement_type_changed)
        self.cement_combo.set_tooltip_text("Select cement type to get suggested products")
        header.pack_start(self.cement_combo, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Search/filter entry
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        search_icon = Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        search_box.pack_start(search_icon, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Filter phases...")
        self.search_entry.connect('changed', self._on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)

        # Select suggested button
        suggest_btn = Gtk.Button(label="Select Suggested")
        suggest_btn.set_tooltip_text("Select products commonly needed for this cement type")
        suggest_btn.connect('clicked', self._on_select_suggested_clicked)
        search_box.pack_start(suggest_btn, False, False, 0)

        # Clear selection button
        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.set_tooltip_text("Deselect all products")
        clear_btn.connect('clicked', self._on_clear_all_clicked)
        search_box.pack_start(clear_btn, False, False, 0)

        self.pack_start(search_box, False, False, 0)

        # Main product list in a scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(350)
        scrolled.set_can_focus(True)  # Enable keyboard navigation

        # TreeView with checkboxes
        # Columns: selected (bool), gems_name (str), display_name (str),
        #          category (str), description (str), has_csh_data (bool), is_suggested (bool),
        #          kinetic_type (str), is_from_microstructure (bool)
        self.store = Gtk.TreeStore(bool, str, str, str, str, bool, bool, str, bool)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(2)  # Search by display name
        self.treeview.connect('row-activated', self._on_row_activated)

        # Column 1: Checkbox
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect('toggled', self._on_product_toggled)
        column_select = Gtk.TreeViewColumn("", renderer_toggle, active=0)
        column_select.set_cell_data_func(renderer_toggle, self._checkbox_cell_data_func)
        column_select.set_min_width(30)
        self.treeview.append_column(column_select)

        # Column 2: Display Name (with bold for suggested, italic for microstructure)
        renderer_name = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Phase", renderer_name, text=2)
        column_name.set_cell_data_func(renderer_name, self._name_cell_data_func)
        column_name.set_expand(True)
        column_name.set_sort_column_id(2)
        self.treeview.append_column(column_name)

        # Column 3: Kinetic Model Type
        renderer_kinetic = Gtk.CellRendererText()
        column_kinetic = Gtk.TreeViewColumn("Kinetics", renderer_kinetic, text=7)
        column_kinetic.set_cell_data_func(renderer_kinetic, self._kinetic_cell_data_func)
        column_kinetic.set_min_width(100)
        self.treeview.append_column(column_kinetic)

        # Column 4: GEMS Name
        renderer_gems = Gtk.CellRendererText()
        renderer_gems.set_property('foreground', 'gray')
        renderer_gems.set_property('style', Pango.Style.ITALIC)
        column_gems = Gtk.TreeViewColumn("GEMS Name", renderer_gems, text=1)
        column_gems.set_sort_column_id(1)
        self.treeview.append_column(column_gems)

        # Column 5: Configure button (icon) — clickable; opens phase config dialog
        renderer_config = Gtk.CellRendererPixbuf()
        self.column_config = Gtk.TreeViewColumn("", renderer_config)
        self.column_config.set_cell_data_func(renderer_config, self._config_cell_data_func)
        self.column_config.set_min_width(30)
        self.treeview.append_column(self.column_config)

        # Single-click on the pencil icon column opens the phase configuration
        # dialog for that row (matches what users expect from a clickable icon).
        self.treeview.connect('button-press-event', self._on_treeview_button_press)

        scrolled.add(self.treeview)
        self.pack_start(scrolled, True, True, 0)

        # Populate the tree with products grouped by category
        self._populate_product_tree()

        # Bottom toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_margin_top(5)

        # Selection count label
        self.count_label = Gtk.Label()
        self.count_label.set_halign(Gtk.Align.START)
        self._update_count_label()
        toolbar.pack_start(self.count_label, False, False, 0)

        toolbar.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        # Configure kinetics button
        self.config_kinetics_btn = Gtk.Button(label="Edit Kinetics...")
        self.config_kinetics_btn.set_tooltip_text("Edit kinetic model parameters for selected phase")
        self.config_kinetics_btn.connect('clicked', self._on_configure_kinetics_clicked)
        self.config_kinetics_btn.set_sensitive(False)
        toolbar.pack_start(self.config_kinetics_btn, False, False, 0)

        # Configure affinity button
        self.config_affinity_btn = Gtk.Button(label="Edit Affinity...")
        self.config_affinity_btn.set_tooltip_text("Edit contact angles for selected phase")
        self.config_affinity_btn.connect('clicked', self._on_configure_affinity_clicked)
        self.config_affinity_btn.set_sensitive(False)
        toolbar.pack_start(self.config_affinity_btn, False, False, 0)

        # Configure C-S-H button
        self.config_csh_btn = Gtk.Button(label="Edit C-S-H...")
        self.config_csh_btn.set_tooltip_text("Edit C-S-H poresize distribution and Rd values")
        self.config_csh_btn.connect('clicked', self._on_configure_csh_clicked)
        self.config_csh_btn.set_sensitive(False)
        toolbar.pack_start(self.config_csh_btn, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

        # Connect selection changed
        self.treeview.get_selection().connect('changed', self._on_selection_changed)

    def _populate_product_tree(self):
        """Populate the tree with phases grouped by category."""
        self.store.clear()

        # Get products by category
        products_by_category = self.service.get_products_by_category()
        suggested = set(self.service.get_suggested_products_for_cement_type(self.cement_type))

        self.category_iters = {}  # Store category row iters for filtering

        # First, add microstructure phases if any (always at top)
        if self.microstructure_phases:
            micro_iter = self.store.append(None, [
                False,  # category not selectable
                "",     # no gems_name
                "Microstructure Phases",  # category name
                "",     # no category column for parent
                "",     # no description
                False,  # no csh data
                False,  # not suggested
                "",     # no kinetic type for category
                False,  # not from microstructure (it's a category row)
            ])
            self.category_iters['microstructure'] = micro_iter

            for gems_name in sorted(self.microstructure_phases):
                kinetic_type = self.kinetic_defaults.get_kinetic_type(gems_name) or "Thermodynamic"
                has_csh = self.service.has_special_csh_data(gems_name)

                # Get display name from service or use GEMS name
                data = self.service.get_product_data(gems_name)
                display_name = data.display_name if data else gems_name
                description = data.description if data else "Phase from microstructure"

                self.store.append(micro_iter, [
                    True,   # always selected (from microstructure)
                    gems_name,
                    display_name,
                    "Microstructure",
                    description,
                    has_csh,
                    False,  # not suggested (it's required)
                    kinetic_type,
                    True,   # is from microstructure
                ])

        # Sort categories for consistent ordering
        category_order = [
            ProductCategory.CALCIUM_SILICATE_HYDRATE,
            ProductCategory.CALCIUM_HYDROXIDE,
            ProductCategory.AFT,
            ProductCategory.AFM,
            ProductCategory.CARBONATE_AFM,
            ProductCategory.ALUMINATE_HYDRATE,
            ProductCategory.FERRITE_HYDRATE,
            ProductCategory.HYDROTALCITE,
            ProductCategory.ZEOLITE,
            ProductCategory.OTHER,
        ]

        for category in category_order:
            if category not in products_by_category:
                continue

            products = products_by_category[category]
            if not products:
                continue

            # Skip category if all its products are already microstructure phases
            non_micro_products = [p for p in products if p not in self.microstructure_phases]
            if not non_micro_products:
                continue

            # Add category row (parent)
            category_iter = self.store.append(None, [
                False,  # not selectable
                "",     # no gems_name
                category.value,  # display as category name
                "",     # no category column for parent
                "",     # no description
                False,  # no csh data
                False,  # not suggested
                "",     # no kinetic type for category
                False,  # not from microstructure
            ])
            self.category_iters[category] = category_iter

            # Add products as children
            for gems_name in sorted(products):
                # Skip if already in microstructure phases
                if gems_name in self.microstructure_phases:
                    continue

                data = self.service.get_product_data(gems_name)
                if data:
                    is_suggested = gems_name in suggested
                    has_csh = self.service.has_special_csh_data(gems_name)
                    kinetic_type = self.kinetic_defaults.get_kinetic_type(gems_name) or "Thermodynamic"

                    self.store.append(category_iter, [
                        gems_name in self.selected_products,  # selected
                        gems_name,
                        data.display_name,
                        category.value,
                        data.description,
                        has_csh,
                        is_suggested,
                        kinetic_type,
                        False,  # not from microstructure
                    ])

        # Expand all categories
        self.treeview.expand_all()

    def _checkbox_cell_data_func(self, column, cell, model, iter, data):
        """Make checkbox insensitive for microstructure phases (can't be deselected)."""
        gems_name = model.get_value(iter, 1)
        is_from_micro = model.get_value(iter, 8) if gems_name else False

        # Microstructure phases can't be deselected
        cell.set_property('activatable', not is_from_micro)
        # Dim the checkbox for microstructure phases to indicate it's locked
        if is_from_micro:
            cell.set_property('sensitive', False)
        else:
            cell.set_property('sensitive', True)

    def _name_cell_data_func(self, column, cell, model, iter, data):
        """Format the name column - bold for suggested, colored for microstructure."""
        is_suggested = model.get_value(iter, 6)
        gems_name = model.get_value(iter, 1)
        is_from_micro = model.get_value(iter, 8) if gems_name else False

        # Category rows have no gems_name
        if not gems_name:
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', None)
        elif is_from_micro:
            # Microstructure phases shown in blue/bold
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', '#2060A0')
        elif is_suggested:
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', None)
        else:
            cell.set_property('weight', Pango.Weight.NORMAL)
            cell.set_property('foreground', None)

    def _kinetic_cell_data_func(self, column, cell, model, iter, data):
        """Format the kinetic type column."""
        gems_name = model.get_value(iter, 1)
        kinetic_type = model.get_value(iter, 7)

        if not gems_name:
            # Category row
            cell.set_property('text', '')
        elif kinetic_type == "Thermodynamic":
            cell.set_property('foreground', 'gray')
            cell.set_property('style', Pango.Style.ITALIC)
        else:
            cell.set_property('foreground', None)
            cell.set_property('style', Pango.Style.NORMAL)

    def _config_cell_data_func(self, column, cell, model, iter, data):
        """Show configure icon for selected phases using Carbon icon."""
        gems_name = model.get_value(iter, 1)
        is_selected = model.get_value(iter, 0)

        if gems_name and is_selected and self.edit_icon_pixbuf:
            cell.set_property('pixbuf', self.edit_icon_pixbuf)
        else:
            cell.set_property('pixbuf', None)

    def _on_product_toggled(self, renderer, path):
        """Handle product checkbox toggle."""
        iter = self.store.get_iter(path)
        gems_name = self.store.get_value(iter, 1)

        # Handle category rows (no gems_name) - toggle all children
        if not gems_name:
            self._toggle_category(iter)
            return

        # Don't allow toggling microstructure phases
        is_from_micro = self.store.get_value(iter, 8)
        if is_from_micro:
            self.logger.debug(f"Cannot toggle microstructure phase: {gems_name}")
            return

        # Toggle individual product selection
        current = self.store.get_value(iter, 0)
        new_value = not current
        self.store.set_value(iter, 0, new_value)

        if new_value:
            self.selected_products.add(gems_name)
            # Initialize configuration with defaults
            if gems_name not in self.product_configurations:
                self._init_product_configuration(gems_name)
        else:
            self.selected_products.discard(gems_name)
            # Keep configuration in case re-selected

        # Update category checkbox state based on children
        parent_iter = self.store.iter_parent(iter)
        if parent_iter:
            self._update_category_checkbox(parent_iter)

        self._update_count_label()
        self.emit('selection-changed')
        self.logger.debug(f"{'Selected' if new_value else 'Deselected'} product: {gems_name}")

    def _toggle_category(self, category_iter) -> None:
        """Toggle all products in a category."""
        # Determine if we should select or deselect all
        # If any child is not selected, select all; otherwise deselect all
        all_selected = True
        child_iter = self.store.iter_children(category_iter)
        while child_iter:
            if not self.store.get_value(child_iter, 0):
                all_selected = False
                break
            child_iter = self.store.iter_next(child_iter)

        new_value = not all_selected

        # Apply to all children
        child_iter = self.store.iter_children(category_iter)
        while child_iter:
            gems_name = self.store.get_value(child_iter, 1)
            self.store.set_value(child_iter, 0, new_value)

            if new_value:
                self.selected_products.add(gems_name)
                if gems_name not in self.product_configurations:
                    self._init_product_configuration(gems_name)
            else:
                self.selected_products.discard(gems_name)

            child_iter = self.store.iter_next(child_iter)

        # Update category checkbox
        self.store.set_value(category_iter, 0, new_value)

        self._update_count_label()
        self.emit('selection-changed')

        category_name = self.store.get_value(category_iter, 2)
        self.logger.debug(f"{'Selected' if new_value else 'Deselected'} all products in {category_name}")

    def _update_category_checkbox(self, category_iter) -> None:
        """Update category checkbox based on child selection states."""
        all_selected = True
        any_selected = False

        child_iter = self.store.iter_children(category_iter)
        while child_iter:
            if self.store.get_value(child_iter, 0):
                any_selected = True
            else:
                all_selected = False
            child_iter = self.store.iter_next(child_iter)

        # Set category checkbox to match (checked if all selected)
        self.store.set_value(category_iter, 0, all_selected)

    def _init_product_configuration(self, gems_name: str):
        """Initialize default configuration for a product.

        Checks user affinity preferences first, then falls back to built-in defaults.
        """
        data = self.service.get_product_data(gems_name)

        # Check user affinity preferences first
        affinity = self._get_affinity_with_user_prefs(gems_name, data)

        config = {
            'gems_name': gems_name,
            'affinity': affinity,
        }

        # Add C-S-H special data if applicable
        if data and data.poresize_distribution:
            config['poresize_distribution'] = list(data.poresize_distribution)
        if data and data.rd_values:
            config['rd_values'] = list(data.rd_values)

        self.product_configurations[gems_name] = config

    def _get_affinity_with_user_prefs(self, gems_name: str, data) -> List[Dict[str, Any]]:
        """Get affinity data, checking user preferences first.

        Args:
            gems_name: GEM phase name
            data: HydrationProduct data from service (may be None)

        Returns:
            List of affinity dicts
        """
        try:
            from app.services.affinity_preferences_service import get_affinity_preferences_service
            prefs_service = get_affinity_preferences_service()

            # Check user preferences first
            user_affinity = prefs_service.get_user_default(gems_name)
            if user_affinity is not None:
                return list(user_affinity)
        except Exception as e:
            self.logger.debug(f"Could not load affinity preferences for {gems_name}: {e}")

        # Fall back to built-in defaults
        if data and data.default_affinity:
            return list(data.default_affinity)

        return []

    def _on_row_activated(self, treeview, path, column):
        """Handle double-click on a row - opens combined phase configuration dialog."""
        iter = self.store.get_iter(path)
        gems_name = self.store.get_value(iter, 1)

        # Skip category rows
        if not gems_name:
            return

        # If not selected, select it first
        if gems_name not in self.selected_products:
            # Only add to selected_products if not a microstructure phase (those are always selected)
            is_from_micro = self.store.get_value(iter, 8)
            if not is_from_micro:
                self.store.set_value(iter, 0, True)
                self.selected_products.add(gems_name)
                self._init_product_configuration(gems_name)
                self._update_count_label()
                self.emit('selection-changed')

        # Emit configure-phase signal with has_csh_data info for the combined dialog
        has_csh = self.store.get_value(iter, 5)
        self.emit('configure-phase', gems_name, has_csh)

    def _on_treeview_button_press(self, treeview, event):
        """Open the phase configuration dialog when the pencil-icon column is clicked.

        The icon is only rendered for selected, non-category phase rows
        (see _config_cell_data_func), so clicks on rows without an icon are
        ignored. Other clicks (checkbox, name, kinetics, GEMS columns) fall
        through to default tree handling.
        """
        # Only handle primary single-click; let double-click fall through to row-activated.
        if event.button != 1 or event.type != Gdk.EventType.BUTTON_PRESS:
            return False

        hit = treeview.get_path_at_pos(int(event.x), int(event.y))
        if hit is None:
            return False
        path, column, _cell_x, _cell_y = hit
        if column is not self.column_config:
            return False

        iter = self.store.get_iter(path)
        gems_name = self.store.get_value(iter, 1)
        is_selected = self.store.get_value(iter, 0)
        if not gems_name or not is_selected:
            # Category row, or unselected row that has no icon — nothing to configure.
            return False

        has_csh = self.store.get_value(iter, 5)
        self.emit('configure-phase', gems_name, has_csh)
        return True

    def _on_selection_changed(self, selection):
        """Handle tree selection change."""
        model, iter = selection.get_selected()
        if iter:
            gems_name = model.get_value(iter, 1)
            is_selected = model.get_value(iter, 0)
            has_csh = model.get_value(iter, 5)
            kinetic_type = model.get_value(iter, 7)

            # Enable configure buttons if a phase row is selected
            # Allow editing kinetics for ANY selected phase (users can add kinetics to any phase)
            self.config_kinetics_btn.set_sensitive(bool(gems_name) and is_selected)
            self.config_affinity_btn.set_sensitive(bool(gems_name) and is_selected)
            self.config_csh_btn.set_sensitive(bool(gems_name) and is_selected and has_csh)
        else:
            self.config_kinetics_btn.set_sensitive(False)
            self.config_affinity_btn.set_sensitive(False)
            self.config_csh_btn.set_sensitive(False)

    def _on_cement_type_changed(self, combo):
        """Handle cement type selection change."""
        index = combo.get_active()
        cement_types = ["portland", "blended", "pozzolanic", "limestone", "slag"]
        self.cement_type = cement_types[index]
        # Re-populate to update suggested highlighting
        self._populate_product_tree()
        # Auto-select suggested products for the new cement type
        self._select_suggested_products()
        self.logger.info(f"Cement type changed to: {self.cement_type}")

    def _on_search_changed(self, entry):
        """Handle search/filter text change."""
        search_text = entry.get_text().lower().strip()

        if not search_text:
            # Show all and expand
            self._populate_product_tree()
            # Re-apply selections
            self._apply_selections_to_store()
            return

        # Filter products
        self.store.clear()
        products_by_category = self.service.get_products_by_category()
        suggested = set(self.service.get_suggested_products_for_cement_type(self.cement_type))

        category_order = [
            ProductCategory.CALCIUM_SILICATE_HYDRATE,
            ProductCategory.CALCIUM_HYDROXIDE,
            ProductCategory.AFT,
            ProductCategory.AFM,
            ProductCategory.CARBONATE_AFM,
            ProductCategory.ALUMINATE_HYDRATE,
            ProductCategory.FERRITE_HYDRATE,
            ProductCategory.HYDROTALCITE,
            ProductCategory.ZEOLITE,
            ProductCategory.OTHER,
        ]

        for category in category_order:
            if category not in products_by_category:
                continue

            # Filter products in this category
            matching_products = []
            for gems_name in products_by_category[category]:
                data = self.service.get_product_data(gems_name)
                if data:
                    # Search in gems_name, display_name, and description
                    if (search_text in gems_name.lower() or
                        search_text in data.display_name.lower() or
                        search_text in data.description.lower()):
                        matching_products.append(gems_name)

            if not matching_products:
                continue

            # Add category
            category_iter = self.store.append(None, [
                False, "", category.value, "", "", False, False, "", False
            ])

            # Add matching products
            for gems_name in sorted(matching_products):
                data = self.service.get_product_data(gems_name)
                is_suggested = gems_name in suggested
                has_csh = self.service.has_special_csh_data(gems_name)
                kinetic_type = self.kinetic_defaults.get_kinetic_type(gems_name) or "Thermodynamic"

                self.store.append(category_iter, [
                    gems_name in self.selected_products,
                    gems_name,
                    data.display_name,
                    category.value,
                    data.description,
                    has_csh,
                    is_suggested,
                    kinetic_type,
                    False,  # not from microstructure
                ])

        self.treeview.expand_all()

    def _apply_selections_to_store(self):
        """Apply current selections to the store after repopulating."""

        def apply_to_iter(model, path, iter, data):
            gems_name = model.get_value(iter, 1)
            if gems_name and gems_name in self.selected_products:
                model.set_value(iter, 0, True)

        self.store.foreach(apply_to_iter, None)

    def _on_select_suggested_clicked(self, button):
        """Select suggested products for current cement type."""
        self._select_suggested_products()

    def _select_suggested_products(self):
        """Select the suggested products for the current cement type."""
        suggested = self.service.get_suggested_products_for_cement_type(self.cement_type)

        # Add suggested to selected set
        for gems_name in suggested:
            self.selected_products.add(gems_name)
            if gems_name not in self.product_configurations:
                self._init_product_configuration(gems_name)

        # Update store
        self._apply_selections_to_store()
        self._update_count_label()
        self.emit('selection-changed')
        self.logger.info(f"Selected {len(suggested)} suggested products for {self.cement_type}")

    def _on_clear_all_clicked(self, button):
        """Clear all selections."""
        self.selected_products.clear()

        # Update store

        def clear_selections(model, path, iter, data):
            model.set_value(iter, 0, False)

        self.store.foreach(clear_selections, None)

        self._update_count_label()
        self.emit('selection-changed')
        self.logger.info("Cleared all product selections")

    def _on_configure_affinity_clicked(self, button):
        """Open affinity configuration for selected product."""
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            gems_name = model.get_value(iter, 1)
            if gems_name:
                self.emit('configure-affinity', gems_name)

    def _on_configure_csh_clicked(self, button):
        """Open C-S-H configuration for selected product."""
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            gems_name = model.get_value(iter, 1)
            if gems_name:
                self.emit('configure-csh', gems_name)

    def _on_configure_kinetics_clicked(self, button):
        """Open kinetics configuration for selected phase."""
        selection = self.treeview.get_selection()
        model, iter = selection.get_selected()
        if iter:
            gems_name = model.get_value(iter, 1)
            if gems_name:
                self.emit('configure-kinetics', gems_name)

    def _update_count_label(self):
        """Update the selection count label."""
        count = len(self.selected_products)
        if count == 0:
            self.count_label.set_markup('<span foreground="gray">No products selected</span>')
        elif count == 1:
            self.count_label.set_markup('<span foreground="green">1 product selected</span>')
        else:
            self.count_label.set_markup(f'<span foreground="green">{count} products selected</span>')

    # =========================================================================
    # Public API
    # =========================================================================

    def get_selected_products(self) -> List[str]:
        """
        Get list of selected product GEMS names.

        Returns:
            List of GEMS phase names
        """
        return list(self.selected_products)

    def set_selected_products(self, products: List[str]):
        """
        Set the selected products.

        Args:
            products: List of GEMS phase names to select
        """
        self.selected_products = set(products)

        # Initialize configurations for any new products
        for gems_name in products:
            if gems_name not in self.product_configurations:
                self._init_product_configuration(gems_name)

        # Re-populate and apply
        self._populate_product_tree()
        self._apply_selections_to_store()
        self._update_count_label()

    def get_product_configuration(self, gems_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration for a specific product.

        Args:
            gems_name: GEMS phase name

        Returns:
            Configuration dict or None
        """
        return self.product_configurations.get(gems_name)

    def set_product_configuration(self, gems_name: str, config: Dict[str, Any]):
        """
        Set the configuration for a product.

        Args:
            gems_name: GEMS phase name
            config: Configuration dict with 'affinity', 'poresize_distribution', 'rd_values'
        """
        self.product_configurations[gems_name] = config

    def get_all_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configurations for all selected products.

        Returns:
            Dict mapping GEMS name to configuration
        """
        return {name: self.product_configurations.get(name, {})
                for name in self.selected_products
                if name in self.product_configurations}

    def set_cement_type(self, cement_type: str):
        """
        Set the cement type (updates suggested product highlighting).

        Args:
            cement_type: 'portland', 'blended', 'pozzolanic', 'limestone', 'slag'
        """
        cement_types = ["portland", "blended", "pozzolanic", "limestone", "slag"]
        if cement_type.lower() in cement_types:
            self.cement_type = cement_type.lower()
            index = cement_types.index(self.cement_type)
            self.cement_combo.set_active(index)
            # _on_cement_type_changed will be triggered by set_active

    def set_product_affinity(self, gems_name: str, affinity: List[Dict[str, Any]]):
        """
        Set the interface affinity for a product.

        Args:
            gems_name: GEMS phase name
            affinity: List of affinity entries with 'affinityphase' and 'contactanglevalue'
        """
        if gems_name not in self.product_configurations:
            self.product_configurations[gems_name] = {}
        self.product_configurations[gems_name]['affinity'] = affinity
        self.logger.debug(f"Set affinity for {gems_name}: {len(affinity)} entries")

    def set_csh_parameters(
        self,
        gems_name: str,
        poresize_distribution: Optional[List[Dict[str, float]]] = None,
        rd_values: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Set C-S-H special parameters for a product.

        Args:
            gems_name: GEMS phase name
            poresize_distribution: List of PSD entries with 'diameter' and 'volumefraction'
            rd_values: List of Rd entries with 'Rdelement' and 'Rdvalue'
        """
        if gems_name not in self.product_configurations:
            self.product_configurations[gems_name] = {}

        if poresize_distribution is not None:
            self.product_configurations[gems_name]['poresize_distribution'] = poresize_distribution

        if rd_values is not None:
            self.product_configurations[gems_name]['rd_values'] = rd_values

        self.logger.debug(f"Set C-S-H parameters for {gems_name}")

    # =========================================================================
    # Microstructure Phases API
    # =========================================================================

    def set_microstructure_phases(self, phases: List[str]) -> None:
        """
        Set the phases from the input microstructure.

        These phases will be shown at the top of the list, always selected,
        and cannot be deselected (they're required).

        Args:
            phases: List of GEMS phase names from the microstructure
        """
        self.microstructure_phases = set(phases)

        # Initialize kinetic configurations with defaults for microstructure phases
        for phase_name in phases:
            if phase_name not in self.kinetic_configurations:
                defaults = self.kinetic_defaults.get_kinetics_for_phase(phase_name)
                if defaults:
                    self.kinetic_configurations[phase_name] = defaults.to_dict()

        # Re-populate tree to show microstructure phases section
        self._populate_product_tree()
        self._apply_selections_to_store()
        self._update_count_label()

        self.logger.info(f"Set {len(phases)} microstructure phases")

    def get_microstructure_phases(self) -> List[str]:
        """
        Get the microstructure phase names.

        Returns:
            List of GEMS phase names from the microstructure
        """
        return list(self.microstructure_phases)

    def clear_microstructure_phases(self) -> None:
        """Clear all microstructure phases."""
        self.microstructure_phases.clear()
        self._populate_product_tree()
        self._apply_selections_to_store()
        self._update_count_label()

    # =========================================================================
    # Kinetics Configuration API
    # =========================================================================

    def get_kinetic_configuration(self, gems_name: str) -> Optional[Dict[str, Any]]:
        """
        Get kinetic parameters for a phase.

        Args:
            gems_name: GEMS phase name

        Returns:
            Kinetic parameters dict with 'type' field, or None
        """
        return self.kinetic_configurations.get(gems_name)

    def set_kinetic_configuration(self, gems_name: str, kinetics: Dict[str, Any]) -> None:
        """
        Set kinetic parameters for a phase.

        Args:
            gems_name: GEMS phase name
            kinetics: Kinetic parameters dict with 'type' field
        """
        self.kinetic_configurations[gems_name] = kinetics
        # Update the TreeStore to reflect the new kinetic type
        self._update_kinetic_type_in_store(gems_name, kinetics.get('type', 'Unknown'))
        self.logger.debug(f"Set kinetics for {gems_name}: {kinetics.get('type')}")

    def remove_kinetic_configuration(self, gems_name: str) -> None:
        """
        Set a phase to thermodynamic control (no kinetic model).

        This explicitly stores {"type": "Thermodynamic"} rather than deleting
        the entry, so that user preferences are properly overridden.

        Args:
            gems_name: GEMS phase name
        """
        # Store explicit Thermodynamic type to override any user preferences
        self.kinetic_configurations[gems_name] = {"type": "Thermodynamic"}
        # Update the TreeStore to show "Thermodynamic"
        self._update_kinetic_type_in_store(gems_name, "Thermodynamic")
        self.logger.debug(f"Set kinetics for {gems_name} to Thermodynamic (no kinetic model)")

    def _update_kinetic_type_in_store(self, gems_name: str, kinetic_type: str) -> None:
        """Update the kinetic type display in the TreeStore for a phase."""
        def update_iter(model, path, iter, data):
            if model.get_value(iter, 1) == gems_name:
                model.set_value(iter, 7, kinetic_type)
                return True  # Stop iteration
            return False

        self.store.foreach(update_iter, None)

    def get_all_kinetic_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get kinetic configurations for all phases (microstructure + selected products).

        Returns:
            Dict mapping GEMS name to kinetic parameters
        """
        # Include both microstructure phases and selected products that have kinetics
        all_phases = self.microstructure_phases | self.selected_products
        return {name: self.kinetic_configurations[name]
                for name in all_phases
                if name in self.kinetic_configurations}

    def get_all_phases(self) -> List[str]:
        """
        Get all phase names (microstructure + selected products).

        Returns:
            List of all active GEMS phase names
        """
        return list(self.microstructure_phases | self.selected_products)


# Register the signals
GObject.type_register(HydrationProductSelectorWidget)

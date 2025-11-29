#!/usr/bin/env python3
"""
Hydration Product Selector Widget

GTK widget for selecting which hydration products to include in a THAMES simulation.
Shows products grouped by category with checkboxes, and allows users to configure
affinity and C-S-H special parameters.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
import logging
from typing import List, Dict, Optional, Any, Set

from app.services.hydration_products_service import (
    HydrationProductsService,
    HydrationProductData,
    ProductCategory,
    get_hydration_products_service,
    DEFAULT_CONTACT_ANGLE,
)


class HydrationProductSelectorWidget(Gtk.Box):
    """
    Widget for selecting hydration products for simulation.

    Features:
    - Products grouped by category (C-S-H, CH, AFt, AFm, etc.)
    - Checkbox selection with suggested products pre-selected
    - Double-click or button to configure affinity
    - Special configuration for C-S-H (PSD, Rd values)
    - Search/filter functionality
    """

    __gsignals__ = {
        # Emitted when selection changes
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        # Emitted when user wants to configure a product's affinity
        'configure-affinity': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # gems_name
        # Emitted when user wants to configure C-S-H special data
        'configure-csh': (GObject.SignalFlags.RUN_FIRST, None, (str,)),  # gems_name
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

        # Track selected products and their configurations
        self.selected_products: Set[str] = set()
        self.product_configurations: Dict[str, Dict[str, Any]] = {}

        # Build UI
        self._build_ui()

        # Initialize with suggested products
        self._select_suggested_products()

    def _build_ui(self):
        """Build the widget UI."""
        # Header with title and cement type selector
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.set_margin_bottom(5)

        title_label = Gtk.Label()
        title_label.set_markup("<b>Hydration Products</b>")
        title_label.set_halign(Gtk.Align.START)
        header.pack_start(title_label, False, False, 0)

        # Cement type selector for suggested products
        header.pack_start(Gtk.Label(), True, True, 0)  # Spacer

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
        self.search_entry.set_placeholder_text("Filter products...")
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

        # TreeView with checkboxes
        # Columns: selected (bool), gems_name (str), display_name (str),
        #          category (str), description (str), has_csh_data (bool), is_suggested (bool)
        self.store = Gtk.TreeStore(bool, str, str, str, str, bool, bool)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)
        self.treeview.set_enable_search(True)
        self.treeview.set_search_column(2)  # Search by display name
        self.treeview.connect('row-activated', self._on_row_activated)

        # Column 1: Checkbox
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect('toggled', self._on_product_toggled)
        column_select = Gtk.TreeViewColumn("", renderer_toggle, active=0)
        column_select.set_min_width(30)
        self.treeview.append_column(column_select)

        # Column 2: Display Name (with bold for suggested)
        renderer_name = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Product", renderer_name, text=2)
        column_name.set_cell_data_func(renderer_name, self._name_cell_data_func)
        column_name.set_expand(True)
        column_name.set_sort_column_id(2)
        self.treeview.append_column(column_name)

        # Column 3: GEMS Name
        renderer_gems = Gtk.CellRendererText()
        renderer_gems.set_property('foreground', 'gray')
        renderer_gems.set_property('style', Pango.Style.ITALIC)
        column_gems = Gtk.TreeViewColumn("GEMS Name", renderer_gems, text=1)
        column_gems.set_sort_column_id(1)
        self.treeview.append_column(column_gems)

        # Column 4: Description
        renderer_desc = Gtk.CellRendererText()
        renderer_desc.set_property('ellipsize', Pango.EllipsizeMode.END)
        column_desc = Gtk.TreeViewColumn("Description", renderer_desc, text=4)
        column_desc.set_min_width(200)
        self.treeview.append_column(column_desc)

        # Column 5: Configure button (icon)
        renderer_config = Gtk.CellRendererPixbuf()
        column_config = Gtk.TreeViewColumn("", renderer_config)
        column_config.set_cell_data_func(renderer_config, self._config_cell_data_func)
        column_config.set_min_width(30)
        self.treeview.append_column(column_config)

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

        # Configure affinity button
        self.config_affinity_btn = Gtk.Button(label="Configure Affinity...")
        self.config_affinity_btn.set_tooltip_text("Edit contact angles for selected product")
        self.config_affinity_btn.connect('clicked', self._on_configure_affinity_clicked)
        self.config_affinity_btn.set_sensitive(False)
        toolbar.pack_start(self.config_affinity_btn, False, False, 0)

        # Configure C-S-H button
        self.config_csh_btn = Gtk.Button(label="Configure C-S-H...")
        self.config_csh_btn.set_tooltip_text("Edit C-S-H poresize distribution and Rd values")
        self.config_csh_btn.connect('clicked', self._on_configure_csh_clicked)
        self.config_csh_btn.set_sensitive(False)
        toolbar.pack_start(self.config_csh_btn, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

        # Connect selection changed
        self.treeview.get_selection().connect('changed', self._on_selection_changed)

    def _populate_product_tree(self):
        """Populate the tree with products grouped by category."""
        self.store.clear()

        # Get products by category
        products_by_category = self.service.get_products_by_category()
        suggested = set(self.service.get_suggested_products_for_cement_type(self.cement_type))

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

        self.category_iters = {}  # Store category row iters for filtering

        for category in category_order:
            if category not in products_by_category:
                continue

            products = products_by_category[category]
            if not products:
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
            ])
            self.category_iters[category] = category_iter

            # Add products as children
            for gems_name in sorted(products):
                data = self.service.get_product_data(gems_name)
                if data:
                    is_suggested = gems_name in suggested
                    has_csh = self.service.has_special_csh_data(gems_name)

                    self.store.append(category_iter, [
                        gems_name in self.selected_products,  # selected
                        gems_name,
                        data.display_name,
                        category.value,
                        data.description,
                        has_csh,
                        is_suggested,
                    ])

        # Expand all categories
        self.treeview.expand_all()

    def _name_cell_data_func(self, column, cell, model, iter, data):
        """Format the name column - bold for suggested products."""
        is_suggested = model.get_value(iter, 6)
        display_name = model.get_value(iter, 2)
        gems_name = model.get_value(iter, 1)

        # Category rows have no gems_name
        if not gems_name:
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', None)
        elif is_suggested:
            cell.set_property('weight', Pango.Weight.BOLD)
            cell.set_property('foreground', None)
        else:
            cell.set_property('weight', Pango.Weight.NORMAL)
            cell.set_property('foreground', None)

    def _config_cell_data_func(self, column, cell, model, iter, data):
        """Show configure icon for selected products with C-S-H data."""
        gems_name = model.get_value(iter, 1)
        is_selected = model.get_value(iter, 0)
        has_csh = model.get_value(iter, 5)

        if gems_name and is_selected and has_csh:
            cell.set_property('icon-name', 'preferences-system-symbolic')
        else:
            cell.set_property('icon-name', None)

    def _on_product_toggled(self, renderer, path):
        """Handle product checkbox toggle."""
        iter = self.store.get_iter(path)
        gems_name = self.store.get_value(iter, 1)

        # Handle category rows (no gems_name) - toggle all children
        if not gems_name:
            self._toggle_category(iter)
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
        """Initialize default configuration for a product."""
        data = self.service.get_product_data(gems_name)

        config = {
            'gems_name': gems_name,
            'affinity': list(data.default_affinity) if data else [],
        }

        # Add C-S-H special data if applicable
        if data and data.poresize_distribution:
            config['poresize_distribution'] = list(data.poresize_distribution)
        if data and data.rd_values:
            config['rd_values'] = list(data.rd_values)

        self.product_configurations[gems_name] = config

    def _on_row_activated(self, treeview, path, column):
        """Handle double-click on a row."""
        iter = self.store.get_iter(path)
        gems_name = self.store.get_value(iter, 1)

        # Skip category rows
        if not gems_name:
            return

        # If not selected, select it first
        if gems_name not in self.selected_products:
            self.store.set_value(iter, 0, True)
            self.selected_products.add(gems_name)
            self._init_product_configuration(gems_name)
            self._update_count_label()
            self.emit('selection-changed')

        # Emit configure signal
        has_csh = self.store.get_value(iter, 5)
        if has_csh:
            self.emit('configure-csh', gems_name)
        else:
            self.emit('configure-affinity', gems_name)

    def _on_selection_changed(self, selection):
        """Handle tree selection change."""
        model, iter = selection.get_selected()
        if iter:
            gems_name = model.get_value(iter, 1)
            is_selected = model.get_value(iter, 0)
            has_csh = model.get_value(iter, 5)

            # Enable configure buttons if a product row is selected
            self.config_affinity_btn.set_sensitive(bool(gems_name) and is_selected)
            self.config_csh_btn.set_sensitive(bool(gems_name) and is_selected and has_csh)
        else:
            self.config_affinity_btn.set_sensitive(False)
            self.config_csh_btn.set_sensitive(False)

    def _on_cement_type_changed(self, combo):
        """Handle cement type selection change."""
        index = combo.get_active()
        cement_types = ["portland", "blended", "pozzolanic", "limestone", "slag"]
        self.cement_type = cement_types[index]
        # Re-populate to update suggested highlighting
        self._populate_product_tree()
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
                False, "", category.value, "", "", False, False
            ])

            # Add matching products
            for gems_name in sorted(matching_products):
                data = self.service.get_product_data(gems_name)
                is_suggested = gems_name in suggested
                has_csh = self.service.has_special_csh_data(gems_name)

                self.store.append(category_iter, [
                    gems_name in self.selected_products,
                    gems_name,
                    data.display_name,
                    category.value,
                    data.description,
                    has_csh,
                    is_suggested,
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


# Register the signals
GObject.type_register(HydrationProductSelectorWidget)

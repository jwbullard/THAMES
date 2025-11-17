#!/usr/bin/env python3
"""
Materials Management Panel for THAMES

Tag-based materials management interface with unified view for all material types.
Phase 1: Basic list view with create/delete functionality.
"""

import gi
import logging
from typing import TYPE_CHECKING, Optional, List
from pathlib import Path

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango

if TYPE_CHECKING:
    from app.windows.main_window import VCCTLMainWindow

from app.services.service_container import get_service_container
from app.models.material import Material


class MaterialsPanel(Gtk.Box):
    """Tag-based materials management panel for THAMES."""

    def __init__(self, main_window: 'VCCTLMainWindow'):
        """Initialize the materials panel."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.main_window = main_window
        self.logger = logging.getLogger('THAMES.MaterialsPanel')
        self.service_container = get_service_container()

        # Get material service
        try:
            from app.services.material_service import MaterialService
            from app.services.gems_parser_service import GEMSParserService
            from app.database.service import DatabaseService
            from app.database.config import DatabaseConfig

            # Initialize services
            db_config = DatabaseConfig(db_name="thames.db")
            db_service = DatabaseService(db_config)

            # Get GEMS data directory
            gems_data_dir = Path(__file__).parent.parent.parent.parent / "data" / "gems"

            self.material_service = MaterialService(db_service, gems_data_dir)
            self.logger.info(f"MaterialService initialized with GEMS data: {gems_data_dir}")
        except Exception as e:
            self.logger.error(f"Failed to initialize MaterialService: {e}")
            self.material_service = None

        # Panel state
        self.materials: List[Material] = []
        self.selected_material: Optional[Material] = None

        # Setup UI
        self._setup_ui()

        # Load initial data
        self._load_materials()

        self.logger.info("Materials panel initialized (Phase 1)")

    def _setup_ui(self) -> None:
        """Setup the materials panel UI."""
        # Create header
        self._create_header()

        # Create toolbar
        self._create_toolbar()

        # Create materials list
        self._create_materials_list()

        # Create status bar
        self._create_status_bar()

    def _create_header(self) -> None:
        """Create the panel header."""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_top(10)
        header_box.set_margin_bottom(10)
        header_box.set_margin_start(15)
        header_box.set_margin_end(15)

        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="large" weight="bold">Materials</span>')
        title_label.set_halign(Gtk.Align.START)
        header_box.pack_start(title_label, False, False, 0)

        # Subtitle
        subtitle_label = Gtk.Label()
        subtitle_label.set_markup('<span size="small">Tag-based material library</span>')
        subtitle_label.set_halign(Gtk.Align.START)
        subtitle_label.get_style_context().add_class('dim-label')
        header_box.pack_start(subtitle_label, False, False, 0)

        # Material count (will be updated)
        self.count_label = Gtk.Label()
        self.count_label.set_halign(Gtk.Align.END)
        header_box.pack_end(self.count_label, False, False, 0)

        self.pack_start(header_box, False, False, 0)

    def _create_toolbar(self) -> None:
        """Create the toolbar with action buttons."""
        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.BOTH)
        toolbar.get_style_context().add_class('inline-toolbar')

        # Add material button
        add_button = Gtk.ToolButton()
        add_button.set_icon_name('list-add-symbolic')
        add_button.set_label('Add Material')
        add_button.set_tooltip_text('Create a new material')
        add_button.connect('clicked', self._on_add_material)
        toolbar.insert(add_button, -1)

        # Delete material button
        self.delete_button = Gtk.ToolButton()
        self.delete_button.set_icon_name('list-remove-symbolic')
        self.delete_button.set_label('Delete')
        self.delete_button.set_tooltip_text('Delete selected material')
        self.delete_button.set_sensitive(False)
        self.delete_button.connect('clicked', self._on_delete_material)
        toolbar.insert(self.delete_button, -1)

        # Separator
        separator = Gtk.SeparatorToolItem()
        toolbar.insert(separator, -1)

        # Refresh button
        refresh_button = Gtk.ToolButton()
        refresh_button.set_icon_name('view-refresh-symbolic')
        refresh_button.set_label('Refresh')
        refresh_button.set_tooltip_text('Reload materials from database')
        refresh_button.connect('clicked', self._on_refresh)
        toolbar.insert(refresh_button, -1)

        self.pack_start(toolbar, False, False, 0)

    def _create_materials_list(self) -> None:
        """Create the materials list view."""
        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Create list store: name, tags, SG, phase_count, immutable, id
        self.list_store = Gtk.ListStore(str, str, float, int, bool, int)

        # Create tree view
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.set_enable_search(True)
        self.tree_view.set_search_column(0)

        # Name column
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn('Name', name_renderer, text=0)
        name_column.set_resizable(True)
        name_column.set_sort_column_id(0)
        name_column.set_min_width(200)
        self.tree_view.append_column(name_column)

        # Tags column
        tags_renderer = Gtk.CellRendererText()
        tags_renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        tags_column = Gtk.TreeViewColumn('Tags', tags_renderer, text=1)
        tags_column.set_resizable(True)
        tags_column.set_sort_column_id(1)
        tags_column.set_min_width(150)
        self.tree_view.append_column(tags_column)

        # Specific Gravity column
        sg_renderer = Gtk.CellRendererText()
        sg_column = Gtk.TreeViewColumn('SG', sg_renderer, text=2)
        sg_column.set_resizable(True)
        sg_column.set_sort_column_id(2)
        sg_column.set_min_width(80)
        self.tree_view.append_column(sg_column)

        # Phase Count column
        phase_renderer = Gtk.CellRendererText()
        phase_column = Gtk.TreeViewColumn('Phases', phase_renderer, text=3)
        phase_column.set_resizable(True)
        phase_column.set_sort_column_id(3)
        phase_column.set_min_width(80)
        self.tree_view.append_column(phase_column)

        # Immutable column (readonly indicator)
        immutable_renderer = Gtk.CellRendererToggle()
        immutable_renderer.set_property('activatable', False)
        immutable_column = Gtk.TreeViewColumn('Read-only', immutable_renderer, active=4)
        immutable_column.set_resizable(True)
        immutable_column.set_min_width(100)
        self.tree_view.append_column(immutable_column)

        # Connect selection signal
        selection = self.tree_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect('changed', self._on_selection_changed)

        # Connect double-click to edit
        self.tree_view.connect('row-activated', self._on_row_activated)

        scrolled.add(self.tree_view)
        self.pack_start(scrolled, True, True, 0)

    def _create_status_bar(self) -> None:
        """Create the status bar."""
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status_box.set_margin_top(5)
        status_box.set_margin_bottom(5)
        status_box.set_margin_start(15)
        status_box.set_margin_end(15)
        status_box.get_style_context().add_class('statusbar')

        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_text('Ready')
        status_box.pack_start(self.status_label, True, True, 0)

        self.pack_start(status_box, False, False, 0)

    def _load_materials(self) -> None:
        """Load materials from the database."""
        if not self.material_service:
            self._set_status('Error: Material service not available', error=True)
            return

        try:
            self._set_status('Loading materials...')
            self.materials = self.material_service.get_all()
            self._populate_list()
            self._update_count()
            self._set_status(f'Loaded {len(self.materials)} materials')
            self.logger.info(f"Loaded {len(self.materials)} materials")
        except Exception as e:
            self.logger.error(f"Failed to load materials: {e}")
            self._set_status(f'Error loading materials: {e}', error=True)
            self.materials = []

    def _populate_list(self) -> None:
        """Populate the list store with materials."""
        self.list_store.clear()

        for material in self.materials:
            # Format tags as comma-separated list
            tags_str = ', '.join(material.tag_names) if material.tag_names else '(no tags)'

            # Get phase count
            phase_count = len(material.phases) if material.phases else 0

            # Get SG, default to 3.15 if None
            sg = material.specific_gravity if material.specific_gravity is not None else 3.15

            self.list_store.append([
                material.name,
                tags_str,
                sg,
                phase_count,
                material.immutable,
                material.id
            ])

    def _update_count(self) -> None:
        """Update the material count label."""
        count = len(self.materials)
        self.count_label.set_markup(f'<span size="small">{count} material{"s" if count != 1 else ""}</span>')

    def _set_status(self, message: str, error: bool = False) -> None:
        """Set the status bar message."""
        if error:
            self.status_label.set_markup(f'<span color="red">{message}</span>')
        else:
            self.status_label.set_text(message)

    def _on_selection_changed(self, selection: Gtk.TreeSelection) -> None:
        """Handle selection changed."""
        model, tree_iter = selection.get_selected()

        if tree_iter:
            material_id = model[tree_iter][5]
            self.selected_material = next((m for m in self.materials if m.id == material_id), None)
            self.delete_button.set_sensitive(True)
        else:
            self.selected_material = None
            self.delete_button.set_sensitive(False)

    def _on_row_activated(self, tree_view: Gtk.TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn) -> None:
        """Handle row double-click (edit material)."""
        model = tree_view.get_model()
        tree_iter = model.get_iter(path)
        material_id = model[tree_iter][5]

        material = next((m for m in self.materials if m.id == material_id), None)
        if material:
            self._show_edit_dialog(material)

    def _on_add_material(self, button: Gtk.ToolButton) -> None:
        """Handle add material button click."""
        self._show_add_dialog()

    def _on_delete_material(self, button: Gtk.ToolButton) -> None:
        """Handle delete material button click."""
        if not self.selected_material:
            return

        # Check if immutable
        if self.selected_material.immutable:
            dialog = Gtk.MessageDialog(
                transient_for=self.main_window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Cannot Delete Material"
            )
            dialog.format_secondary_text(
                f"The material '{self.selected_material.name}' is marked as read-only "
                f"(likely migrated from VCCTL) and cannot be deleted."
            )
            dialog.run()
            dialog.destroy()
            return

        # Confirm deletion
        dialog = Gtk.MessageDialog(
            transient_for=self.main_window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete '{self.selected_material.name}'?"
        )
        dialog.format_secondary_text(
            "This will permanently delete the material from the database. "
            "This action cannot be undone."
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self._delete_material(self.selected_material)

    def _delete_material(self, material: Material) -> None:
        """Delete a material."""
        try:
            self._set_status(f'Deleting {material.name}...')
            success = self.material_service.delete(material.id)

            if success:
                self.logger.info(f"Deleted material: {material.name}")
                self._load_materials()  # Reload list
                self._set_status(f'Deleted {material.name}')
            else:
                raise Exception("Delete operation returned False")

        except Exception as e:
            self.logger.error(f"Failed to delete material: {e}")
            self._set_status(f'Error deleting material: {e}', error=True)

            # Show error dialog
            dialog = Gtk.MessageDialog(
                transient_for=self.main_window,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Delete Failed"
            )
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()

    def _on_refresh(self, button: Gtk.ToolButton) -> None:
        """Handle refresh button click."""
        self._load_materials()

    def _show_add_dialog(self) -> None:
        """Show the add material dialog."""
        # Import here to avoid circular dependency
        from app.windows.dialogs.material_dialog import MaterialDialog

        dialog = MaterialDialog(self.main_window, material_data=None)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # Reload materials list
            self._load_materials()

        dialog.destroy()

    def _show_edit_dialog(self, material: Material) -> None:
        """Show the edit material dialog."""
        # Import here to avoid circular dependency
        from app.windows.dialogs.material_dialog import MaterialDialog

        dialog = MaterialDialog(self.main_window, material_data=material)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # Reload materials list
            self._load_materials()

        dialog.destroy()

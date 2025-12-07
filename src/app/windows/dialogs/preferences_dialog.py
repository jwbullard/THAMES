#!/usr/bin/env python3
"""
Preferences Dialog for THAMES

Allows users to configure application settings including:
- General settings (auto-save, confirmations)
- Performance settings (threads, memory)
- Kinetic Defaults for GEM phases
"""

import gi
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


class PreferencesDialog(Gtk.Dialog):
    """Dialog for editing application preferences."""

    def __init__(self, parent, config_manager=None):
        """Initialize the preferences dialog."""
        super().__init__(
            title="Preferences",
            parent=parent,
            flags=0
        )

        self.logger = logging.getLogger('THAMES.PreferencesDialog')
        self.config_manager = config_manager

        # Store original values for cancel
        # Note: app_directory is now fixed per platform, not user-configurable

        # Dialog setup
        self.set_default_size(800, 600)
        self.set_border_width(10)

        # Add buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.APPLY)
        self.add_button("OK", Gtk.ResponseType.OK)

        # Create UI
        self._setup_ui()

        # Load current settings
        self._load_settings()

    def _setup_ui(self):
        """Setup the preferences UI."""
        content_area = self.get_content_area()
        content_area.set_spacing(10)

        # Create notebook for different preference categories
        self.notebook = Gtk.Notebook()
        self.notebook.set_border_width(10)
        content_area.pack_start(self.notebook, True, True, 0)

        # General preferences page
        general_page = self._create_general_page()
        self.notebook.append_page(general_page, Gtk.Label(label="General"))

        # Performance preferences page
        performance_page = self._create_performance_page()
        self.notebook.append_page(performance_page, Gtk.Label(label="Performance"))

        # Kinetic Defaults page (THAMES-specific)
        kinetic_page = KineticDefaultsTab()
        self.notebook.append_page(kinetic_page, Gtk.Label(label="Kinetic Defaults"))

        self.show_all()

    def _create_general_page(self):
        """Create the general preferences page."""
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(20)
        grid.set_margin_bottom(20)
        grid.set_margin_left(20)
        grid.set_margin_right(20)

        row = 0

        # Auto-save setting
        self.auto_save_check = Gtk.CheckButton(label="Enable auto-save")
        grid.attach(self.auto_save_check, 0, row, 3, 1)
        row += 1

        # Confirm destructive actions
        self.confirm_actions_check = Gtk.CheckButton(label="Confirm before destructive actions")
        grid.attach(self.confirm_actions_check, 0, row, 3, 1)
        row += 1

        return grid

    def _create_performance_page(self):
        """Create the performance preferences page."""
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(20)
        grid.set_margin_bottom(20)
        grid.set_margin_left(20)
        grid.set_margin_right(20)

        row = 0

        # Worker threads
        label = Gtk.Label(label="Maximum Worker Threads:")
        label.set_halign(Gtk.Align.END)
        grid.attach(label, 0, row, 1, 1)

        self.threads_spin = Gtk.SpinButton()
        self.threads_spin.set_range(1, 32)
        self.threads_spin.set_increments(1, 4)
        self.threads_spin.set_digits(0)
        grid.attach(self.threads_spin, 1, row, 1, 1)
        row += 1

        # Memory limit
        label = Gtk.Label(label="Memory Limit (MB):")
        label.set_halign(Gtk.Align.END)
        grid.attach(label, 0, row, 1, 1)

        self.memory_spin = Gtk.SpinButton()
        self.memory_spin.set_range(512, 65536)
        self.memory_spin.set_increments(512, 2048)
        self.memory_spin.set_digits(0)
        grid.attach(self.memory_spin, 1, row, 1, 1)
        row += 1

        # Cache enabled
        self.cache_check = Gtk.CheckButton(label="Enable caching")
        grid.attach(self.cache_check, 0, row, 2, 1)
        row += 1

        return grid

    def _load_settings(self):
        """Load current settings into the UI."""
        if not self.config_manager:
            return

        # General settings
        self.auto_save_check.set_active(self.config_manager.user.auto_save_enabled)
        self.confirm_actions_check.set_active(self.config_manager.user.confirm_destructive_actions)

        # Performance settings
        self.threads_spin.set_value(self.config_manager.user.max_worker_threads)
        self.memory_spin.set_value(self.config_manager.user.memory_limit_mb)
        self.cache_check.set_active(self.config_manager.user.cache_enabled)


    def apply_settings(self):
        """Apply the settings from the dialog."""
        if not self.config_manager:
            # Kinetic preferences are auto-saved, no action needed
            return True

        # Update configuration
        self.config_manager.user.auto_save_enabled = self.auto_save_check.get_active()
        self.config_manager.user.confirm_destructive_actions = self.confirm_actions_check.get_active()
        self.config_manager.user.max_worker_threads = int(self.threads_spin.get_value())
        self.config_manager.user.memory_limit_mb = int(self.memory_spin.get_value())
        self.config_manager.user.cache_enabled = self.cache_check.get_active()

        # Save to file
        try:
            self.config_manager.save_configuration()
            self.logger.info("Preferences saved successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save preferences: {e}")

            # Show error dialog
            error_dialog = Gtk.MessageDialog(
                transient_for=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to Save Preferences"
            )
            error_dialog.format_secondary_text(f"Error: {str(e)}")
            error_dialog.run()
            error_dialog.destroy()
            return False

    def has_changed(self):
        """Check if settings have changed."""
        # Since app_directory is now fixed, just return False
        # (settings can still be saved, but no restart warning needed)
        return False

    def run_dialog(self):
        """Run the dialog and handle responses."""
        while True:
            response = self.run()

            if response == Gtk.ResponseType.APPLY:
                # Apply without closing
                if self.apply_settings():
                    if self.has_changed():
                        # Show restart warning
                        warning = Gtk.MessageDialog(
                            transient_for=self,
                            flags=0,
                            message_type=Gtk.MessageType.INFO,
                            buttons=Gtk.ButtonsType.OK,
                            text="Restart Required"
                        )
                        warning.format_secondary_text(
                            "Project directory has changed. Please restart the application for changes to take effect."
                        )
                        warning.run()
                        warning.destroy()
                continue

            elif response == Gtk.ResponseType.OK:
                # Apply and close
                if self.apply_settings():
                    if self.has_changed():
                        # Show restart warning
                        warning = Gtk.MessageDialog(
                            transient_for=self,
                            flags=0,
                            message_type=Gtk.MessageType.INFO,
                            buttons=Gtk.ButtonsType.OK,
                            text="Restart Required"
                        )
                        warning.format_secondary_text(
                            "Project directory has changed. Please restart the application for changes to take effect."
                        )
                        warning.run()
                        warning.destroy()
                break

            else:  # Cancel
                break

        self.destroy()


class KineticDefaultsTab(Gtk.Box):
    """Tab for managing user-defined kinetic defaults for GEM phases."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.logger = logging.getLogger('THAMES.KineticDefaultsTab')

        # Services
        self._init_services()

        # Build UI
        self._setup_ui()

        # Load phase data
        self._load_phases()

    def _init_services(self) -> None:
        """Initialize required services."""
        try:
            from app.services.kinetic_preferences_service import get_kinetic_preferences_service
            from app.services.kinetic_defaults_service import get_kinetic_defaults_service
            from app.services.gems_parser_service import GEMSParserService

            self.prefs_service = get_kinetic_preferences_service()
            self.defaults_service = get_kinetic_defaults_service()

            # Get GEMS parser for phase list
            gems_dir = Path(__file__).parent.parent.parent.parent / "data" / "gems"
            self.gems_parser = GEMSParserService(gems_dir)

        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            self.prefs_service = None
            self.defaults_service = None
            self.gems_parser = None

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        # Header with description
        header_label = Gtk.Label()
        header_label.set_markup(
            "<b>Kinetic Defaults for GEM Phases</b>\n"
            "<small>Configure default kinetic models for phases. "
            "User-defined defaults override built-in values.</small>"
        )
        header_label.set_halign(Gtk.Align.START)
        header_label.set_line_wrap(True)
        self.pack_start(header_label, False, False, 0)

        # Filter controls
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.pack_start(filter_box, False, False, 5)

        # Search entry
        search_label = Gtk.Label(label="Search:")
        filter_box.pack_start(search_label, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Filter phases...")
        self.search_entry.connect('changed', self._on_search_changed)
        filter_box.pack_start(self.search_entry, True, True, 0)

        # Filter dropdown
        filter_label = Gtk.Label(label="Show:")
        filter_box.pack_start(filter_label, False, False, 10)

        self.filter_combo = Gtk.ComboBoxText()
        self.filter_combo.append("all", "All Phases")
        self.filter_combo.append("with_kinetics", "Phases with Kinetics")
        self.filter_combo.append("user_defined", "User-Defined Only")
        self.filter_combo.append("no_kinetics", "Thermodynamic Only")
        self.filter_combo.set_active_id("all")
        self.filter_combo.connect('changed', self._on_filter_changed)
        filter_box.pack_start(self.filter_combo, False, False, 0)

        # Phase list
        self._create_phase_list()

        # Button bar
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        self.pack_start(button_box, False, False, 5)

        # Edit button
        self.edit_button = Gtk.Button(label="Edit Kinetics...")
        self.edit_button.connect('clicked', self._on_edit_clicked)
        self.edit_button.set_sensitive(False)
        button_box.pack_start(self.edit_button, False, False, 0)

        # Reset to built-in button
        self.reset_button = Gtk.Button(label="Reset to Built-in")
        self.reset_button.connect('clicked', self._on_reset_clicked)
        self.reset_button.set_sensitive(False)
        button_box.pack_start(self.reset_button, False, False, 0)

        # Export/Import buttons
        export_button = Gtk.Button(label="Export...")
        export_button.connect('clicked', self._on_export_clicked)
        button_box.pack_start(export_button, False, False, 20)

        import_button = Gtk.Button(label="Import...")
        import_button.connect('clicked', self._on_import_clicked)
        button_box.pack_start(import_button, False, False, 0)

    def _create_phase_list(self) -> None:
        """Create the phase list TreeView."""
        # ScrolledWindow for the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.pack_start(scrolled, True, True, 0)

        # ListStore: phase_name, kinetic_type, source, is_user_defined
        self.phase_store = Gtk.ListStore(str, str, str, bool)

        # Filter model
        self.filter_model = self.phase_store.filter_new()
        self.filter_model.set_visible_func(self._filter_visible_func)

        # TreeView
        self.phase_tree = Gtk.TreeView(model=self.filter_model)
        self.phase_tree.set_headers_visible(True)
        self.phase_tree.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self.phase_tree.get_selection().connect('changed', self._on_selection_changed)
        self.phase_tree.connect('row-activated', self._on_row_activated)
        scrolled.add(self.phase_tree)

        # Column: Phase Name
        renderer_name = Gtk.CellRendererText()
        column_name = Gtk.TreeViewColumn("Phase Name", renderer_name, text=0)
        column_name.set_sort_column_id(0)
        column_name.set_resizable(True)
        column_name.set_min_width(200)
        self.phase_tree.append_column(column_name)

        # Column: Kinetic Type
        renderer_type = Gtk.CellRendererText()
        column_type = Gtk.TreeViewColumn("Kinetic Model", renderer_type, text=1)
        column_type.set_sort_column_id(1)
        column_type.set_resizable(True)
        column_type.set_min_width(150)
        self.phase_tree.append_column(column_type)

        # Column: Source (Built-in / User-Defined)
        renderer_source = Gtk.CellRendererText()
        column_source = Gtk.TreeViewColumn("Source", renderer_source, text=2)
        column_source.set_sort_column_id(2)
        column_source.set_resizable(True)
        column_source.set_min_width(120)
        self.phase_tree.append_column(column_source)

    def _load_phases(self) -> None:
        """Load all GEM phases into the list."""
        if not self.gems_parser:
            self.logger.error("GEMS parser not available")
            return

        self.phase_store.clear()

        try:
            phases = self.gems_parser.get_all_phases()

            for phase in phases:
                phase_name = phase.name

                # Skip Electrolyte (aqueous phase) - no kinetics applicable
                if phase_name in ['Electrolyte', 'aq_gen', 'Das']:
                    continue

                # Get kinetic type and source
                kinetic_type = self.defaults_service.get_kinetic_type(phase_name)
                is_user_defined = self.defaults_service.has_user_override(phase_name)

                if kinetic_type:
                    type_display = kinetic_type
                else:
                    type_display = "Thermodynamic"

                if is_user_defined:
                    source = "User-Defined"
                elif kinetic_type:
                    source = "Built-in"
                else:
                    source = "-"

                self.phase_store.append([phase_name, type_display, source, is_user_defined])

            self.logger.info(f"Loaded {len(self.phase_store)} phases")

        except Exception as e:
            self.logger.error(f"Error loading phases: {e}")

    def _filter_visible_func(self, model, iter, data) -> bool:
        """Filter function for the phase list."""
        phase_name = model[iter][0]
        kinetic_type = model[iter][1]
        is_user_defined = model[iter][3]

        # Search filter
        search_text = self.search_entry.get_text().lower()
        if search_text and search_text not in phase_name.lower():
            return False

        # Category filter
        filter_id = self.filter_combo.get_active_id()
        if filter_id == "with_kinetics":
            return kinetic_type != "Thermodynamic"
        elif filter_id == "user_defined":
            return is_user_defined
        elif filter_id == "no_kinetics":
            return kinetic_type == "Thermodynamic"

        return True

    def _on_search_changed(self, entry) -> None:
        """Handle search entry change."""
        self.filter_model.refilter()

    def _on_filter_changed(self, combo) -> None:
        """Handle filter combo change."""
        self.filter_model.refilter()

    def _on_selection_changed(self, selection) -> None:
        """Handle tree selection change."""
        model, tree_iter = selection.get_selected()
        has_selection = tree_iter is not None

        self.edit_button.set_sensitive(has_selection)

        # Reset button only enabled for user-defined phases
        if has_selection:
            is_user_defined = model[tree_iter][3]
            self.reset_button.set_sensitive(is_user_defined)
        else:
            self.reset_button.set_sensitive(False)

    def _on_row_activated(self, tree, path, column) -> None:
        """Handle double-click on row."""
        self._on_edit_clicked(None)

    def _on_edit_clicked(self, button) -> None:
        """Handle Edit Kinetics button click."""
        selection = self.phase_tree.get_selection()
        model, tree_iter = selection.get_selected()

        if not tree_iter:
            return

        # Get the underlying store iter (not filter iter)
        filter_path = model.get_path(tree_iter)
        store_path = self.filter_model.convert_path_to_child_path(filter_path)
        store_iter = self.phase_store.get_iter(store_path)

        phase_name = self.phase_store[store_iter][0]

        self.logger.info(f"Editing kinetics for {phase_name}")

        # Open the kinetic model editor dialog
        try:
            from app.widgets.kinetic_model_editor import KineticModelEditorDialog

            # Get current kinetics (user or built-in)
            current_kinetics = None
            if self.prefs_service.has_user_default(phase_name):
                current_kinetics = self.prefs_service.get_user_default(phase_name)
            else:
                kinetics_obj = self.defaults_service._get_builtin_kinetics(phase_name)
                if kinetics_obj:
                    current_kinetics = kinetics_obj.to_dict()

            dialog = KineticModelEditorDialog(
                parent=self.get_toplevel(),
                phase_name=phase_name,
                current_params=current_kinetics
            )

            response = dialog.run()

            if response == Gtk.ResponseType.OK:
                new_kinetics = dialog.get_kinetic_parameters()

                if new_kinetics is None:
                    # User selected Thermodynamic - save as explicit preference
                    self.prefs_service.set_user_default(phase_name, {'type': 'Thermodynamic'})
                else:
                    # Save new kinetics
                    self.prefs_service.set_user_default(phase_name, new_kinetics)

                # Refresh the list
                self._refresh_phase(store_iter, phase_name)

            dialog.destroy()

        except Exception as e:
            self.logger.error(f"Error opening kinetic editor: {e}")
            self._show_error(f"Error opening kinetic editor:\n{e}")

    def _on_reset_clicked(self, button) -> None:
        """Handle Reset to Built-in button click."""
        selection = self.phase_tree.get_selection()
        model, tree_iter = selection.get_selected()

        if not tree_iter:
            return

        # Get the underlying store iter
        filter_path = model.get_path(tree_iter)
        store_path = self.filter_model.convert_path_to_child_path(filter_path)
        store_iter = self.phase_store.get_iter(store_path)

        phase_name = self.phase_store[store_iter][0]

        # Confirm reset
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Reset {phase_name} to built-in default?"
        )
        dialog.format_secondary_text(
            "This will remove your custom kinetic settings for this phase."
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.prefs_service.remove_user_default(phase_name)
            self._refresh_phase(store_iter, phase_name)
            self.reset_button.set_sensitive(False)

    def _refresh_phase(self, store_iter, phase_name: str) -> None:
        """Refresh a single phase row after editing."""
        kinetic_type = self.defaults_service.get_kinetic_type(phase_name)
        is_user_defined = self.defaults_service.has_user_override(phase_name)

        if kinetic_type:
            type_display = kinetic_type
        else:
            type_display = "Thermodynamic"

        if is_user_defined:
            source = "User-Defined"
        elif kinetic_type:
            source = "Built-in"
        else:
            source = "-"

        self.phase_store[store_iter] = [phase_name, type_display, source, is_user_defined]

    def _on_export_clicked(self, button) -> None:
        """Handle Export button click."""
        dialog = Gtk.FileChooserDialog(
            title="Export Kinetic Preferences",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("kinetic_defaults.json")

        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            export_path = Path(dialog.get_filename())
            if self.prefs_service.export_to_file(export_path):
                self._show_info(f"Exported preferences to:\n{export_path}")
            else:
                self._show_error("Failed to export preferences")

        dialog.destroy()

    def _on_import_clicked(self, button) -> None:
        """Handle Import button click."""
        dialog = Gtk.FileChooserDialog(
            title="Import Kinetic Preferences",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        # Add JSON filter
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON files")
        filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)

        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            import_path = Path(dialog.get_filename())

            # Ask about merge vs replace
            merge_dialog = Gtk.MessageDialog(
                transient_for=self.get_toplevel(),
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="How should imported settings be applied?"
            )
            merge_dialog.add_button("Merge with Existing", 1)
            merge_dialog.add_button("Replace All", 2)
            merge_dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)

            merge_response = merge_dialog.run()
            merge_dialog.destroy()

            if merge_response in [1, 2]:
                merge = (merge_response == 1)
                if self.prefs_service.import_from_file(import_path, merge=merge):
                    self._load_phases()  # Reload all
                    self._show_info(f"Imported preferences from:\n{import_path}")
                else:
                    self._show_error("Failed to import preferences")

        dialog.destroy()

    def _show_error(self, message: str) -> None:
        """Show an error dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _show_info(self, message: str) -> None:
        """Show an info dialog."""
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Success"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

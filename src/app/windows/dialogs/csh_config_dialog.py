#!/usr/bin/env python3
"""
C-S-H Configuration Dialog

Dialog for configuring special C-S-H (calcium silicate hydrate) parameters:
- Poresize distribution (gel porosity model)
- Rd values (alkali distribution coefficients for K and Na)

These parameters are specific to C-S-H phases like CSHQ and control
how the gel pore structure and alkali uptake are modeled.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
import logging
from typing import List, Dict, Any, Optional
import json

from app.services.hydration_products_service import (
    get_hydration_products_service,
    CSHQ_PORESIZE_DISTRIBUTION,
    CSHQ_RD_VALUES,
)


class CSHConfigDialog(Gtk.Dialog):
    """
    Dialog for configuring C-S-H special parameters.

    Allows users to view and edit:
    - Poresize distribution (diameter vs volume fraction)
    - Rd values (alkali distribution coefficients)
    """

    def __init__(self, parent: Gtk.Window, gems_name: str,
                 current_psd: Optional[List[Dict[str, float]]] = None,
                 current_rd: Optional[List[Dict[str, Any]]] = None):
        """
        Initialize the C-S-H configuration dialog.

        Args:
            parent: Parent window
            gems_name: GEMS name of the C-S-H phase
            current_psd: Current poresize distribution data
            current_rd: Current Rd values
        """
        super().__init__(
            title=f"C-S-H Configuration - {gems_name}",
            transient_for=parent,
            flags=0
        )

        self.gems_name = gems_name
        self.logger = logging.getLogger('THAMES.CSHConfigDialog')
        self.service = get_hydration_products_service()

        # Store current configuration
        if current_psd:
            self.psd_data = [dict(p) for p in current_psd]
        else:
            self.psd_data = list(CSHQ_PORESIZE_DISTRIBUTION)

        if current_rd:
            self.rd_data = [dict(r) for r in current_rd]
        else:
            self.rd_data = list(CSHQ_RD_VALUES)

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(700, 550)

        self._build_ui()
        self.show_all()

    def _build_ui(self):
        """Build the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(15)
        content.set_margin_bottom(15)
        content.set_margin_start(15)
        content.set_margin_end(15)

        # Header
        header_label = Gtk.Label()
        header_label.set_markup(
            f"<b>Special Parameters for {self.service.get_display_name(self.gems_name)}</b>"
        )
        header_label.set_halign(Gtk.Align.START)
        content.pack_start(header_label, False, False, 0)

        # Use a notebook for tabs
        notebook = Gtk.Notebook()

        # Tab 1: Poresize Distribution
        psd_page = self._build_psd_page()
        notebook.append_page(psd_page, Gtk.Label(label="Poresize Distribution"))

        # Tab 2: Rd Values
        rd_page = self._build_rd_page()
        notebook.append_page(rd_page, Gtk.Label(label="Rd Values (Alkali Uptake)"))

        content.pack_start(notebook, True, True, 0)

    def _build_psd_page(self) -> Gtk.Box:
        """Build the poresize distribution tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)

        # Explanation
        explanation = Gtk.Label()
        explanation.set_markup(
            "<small>The poresize distribution defines the gel pore structure of C-S-H.\n"
            "Each entry specifies a pore diameter (nm) and its volume fraction.\n"
            "Volume fractions should sum to 1.0.</small>"
        )
        explanation.set_halign(Gtk.Align.START)
        explanation.set_line_wrap(True)
        page.pack_start(explanation, False, False, 0)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        add_btn = Gtk.Button(label="Add Entry")
        add_btn.connect('clicked', self._on_psd_add_clicked)
        toolbar.pack_start(add_btn, False, False, 0)

        remove_btn = Gtk.Button(label="Remove")
        remove_btn.connect('clicked', self._on_psd_remove_clicked)
        toolbar.pack_start(remove_btn, False, False, 0)

        toolbar.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        import_btn = Gtk.Button(label="Import CSV...")
        import_btn.set_tooltip_text("Import poresize distribution from CSV file")
        import_btn.connect('clicked', self._on_psd_import_clicked)
        toolbar.pack_start(import_btn, False, False, 0)

        export_btn = Gtk.Button(label="Export CSV...")
        export_btn.set_tooltip_text("Export poresize distribution to CSV file")
        export_btn.connect('clicked', self._on_psd_export_clicked)
        toolbar.pack_start(export_btn, False, False, 0)

        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.connect('clicked', self._on_psd_reset_clicked)
        toolbar.pack_start(reset_btn, False, False, 0)

        page.pack_start(toolbar, False, False, 0)

        # PSD table
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(300)

        # ListStore: diameter (float), volumefraction (float)
        self.psd_store = Gtk.ListStore(float, float)

        self.psd_treeview = Gtk.TreeView(model=self.psd_store)
        self.psd_treeview.set_headers_visible(True)

        # Column 1: Diameter
        renderer_diam = Gtk.CellRendererText()
        renderer_diam.set_property('editable', True)
        renderer_diam.connect('edited', self._on_psd_diameter_edited)
        column_diam = Gtk.TreeViewColumn("Diameter (nm)", renderer_diam)
        column_diam.set_cell_data_func(renderer_diam, self._format_float_cell, 0)
        column_diam.set_min_width(120)
        column_diam.set_sort_column_id(0)
        self.psd_treeview.append_column(column_diam)

        # Column 2: Volume Fraction
        renderer_vf = Gtk.CellRendererText()
        renderer_vf.set_property('editable', True)
        renderer_vf.connect('edited', self._on_psd_volumefraction_edited)
        column_vf = Gtk.TreeViewColumn("Volume Fraction", renderer_vf)
        column_vf.set_cell_data_func(renderer_vf, self._format_float_cell, 1)
        column_vf.set_min_width(150)
        column_vf.set_sort_column_id(1)
        self.psd_treeview.append_column(column_vf)

        scrolled.add(self.psd_treeview)
        page.pack_start(scrolled, True, True, 0)

        # Summary line
        self.psd_summary_label = Gtk.Label()
        self.psd_summary_label.set_halign(Gtk.Align.START)
        page.pack_start(self.psd_summary_label, False, False, 0)

        # Populate
        self._populate_psd_store()

        return page

    def _format_float_cell(self, column, cell, model, iter, col_index):
        """Format float values for display."""
        value = model.get_value(iter, col_index)
        if col_index == 0:  # Diameter
            cell.set_property('text', f"{value:.5f}")
        else:  # Volume fraction
            cell.set_property('text', f"{value:.8f}")

    def _populate_psd_store(self):
        """Populate the PSD store from data."""
        self.psd_store.clear()
        for entry in self.psd_data:
            self.psd_store.append([entry['diameter'], entry['volumefraction']])
        self._update_psd_summary()

    def _update_psd_summary(self):
        """Update the PSD summary label."""
        total_vf = sum(entry['volumefraction'] for entry in self.psd_data)
        count = len(self.psd_data)

        if abs(total_vf - 1.0) < 0.01:
            color = "green"
            status = "✓"
        else:
            color = "orange"
            status = "⚠"

        self.psd_summary_label.set_markup(
            f'<span foreground="{color}">{status} {count} entries, '
            f'total volume fraction: {total_vf:.6f}</span>'
        )

    def _on_psd_diameter_edited(self, renderer, path, new_text):
        """Handle diameter cell edit."""
        try:
            value = float(new_text)
            if value <= 0:
                self._show_error("Diameter must be positive")
                return

            self.psd_store[path][0] = value
            self.psd_data[int(path)]['diameter'] = value

        except ValueError:
            self._show_error("Invalid number format")

    def _on_psd_volumefraction_edited(self, renderer, path, new_text):
        """Handle volume fraction cell edit."""
        try:
            value = float(new_text)
            if value < 0:
                self._show_error("Volume fraction cannot be negative")
                return

            self.psd_store[path][1] = value
            self.psd_data[int(path)]['volumefraction'] = value
            self._update_psd_summary()

        except ValueError:
            self._show_error("Invalid number format")

    def _on_psd_add_clicked(self, button):
        """Add a new PSD entry."""
        # Add at the end with default values
        new_entry = {'diameter': 1.0, 'volumefraction': 0.0}
        self.psd_data.append(new_entry)
        self.psd_store.append([new_entry['diameter'], new_entry['volumefraction']])
        self._update_psd_summary()

    def _on_psd_remove_clicked(self, button):
        """Remove selected PSD entry."""
        selection = self.psd_treeview.get_selection()
        model, treeiter = selection.get_selected()

        if treeiter:
            path = model.get_path(treeiter)
            index = path.get_indices()[0]

            del self.psd_data[index]
            model.remove(treeiter)
            self._update_psd_summary()

    def _on_psd_import_clicked(self, button):
        """Import PSD from CSV file."""
        dialog = Gtk.FileChooserDialog(
            title="Import Poresize Distribution",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            try:
                self._import_psd_csv(filepath)
                self.logger.info(f"Imported PSD from {filepath}")
            except Exception as e:
                self._show_error(f"Failed to import: {str(e)}")
                self.logger.error(f"PSD import error: {e}")

        dialog.destroy()

    def _import_psd_csv(self, filepath: str):
        """Import PSD data from CSV file."""
        import csv

        new_data = []
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header

            for row in reader:
                if len(row) >= 2:
                    diameter = float(row[0])
                    volumefraction = float(row[1])
                    new_data.append({
                        'diameter': diameter,
                        'volumefraction': volumefraction
                    })

        if new_data:
            self.psd_data = new_data
            self._populate_psd_store()

    def _on_psd_export_clicked(self, button):
        """Export PSD to CSV file."""
        dialog = Gtk.FileChooserDialog(
            title="Export Poresize Distribution",
            parent=self,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK
        )
        dialog.set_current_name("poresize_distribution.csv")
        dialog.set_do_overwrite_confirmation(True)

        filter_csv = Gtk.FileFilter()
        filter_csv.set_name("CSV files")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            try:
                self._export_psd_csv(filepath)
                self.logger.info(f"Exported PSD to {filepath}")
            except Exception as e:
                self._show_error(f"Failed to export: {str(e)}")
                self.logger.error(f"PSD export error: {e}")

        dialog.destroy()

    def _export_psd_csv(self, filepath: str):
        """Export PSD data to CSV file."""
        import csv

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['diameter', 'volumefraction'])
            for entry in self.psd_data:
                writer.writerow([entry['diameter'], entry['volumefraction']])

    def _on_psd_reset_clicked(self, button):
        """Reset PSD to defaults."""
        confirm = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset to defaults?"
        )
        confirm.format_secondary_text(
            "This will replace the current poresize distribution with the defaults."
        )
        response = confirm.run()
        confirm.destroy()

        if response == Gtk.ResponseType.YES:
            self.psd_data = [dict(p) for p in CSHQ_PORESIZE_DISTRIBUTION]
            self._populate_psd_store()
            self.logger.info("Reset PSD to defaults")

    def _build_rd_page(self) -> Gtk.Box:
        """Build the Rd values tab."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.set_margin_top(10)
        page.set_margin_bottom(10)
        page.set_margin_start(10)
        page.set_margin_end(10)

        # Explanation
        explanation = Gtk.Label()
        explanation.set_markup(
            "<small>Rd (distribution coefficient) values control how alkalis (K, Na) "
            "are partitioned between C-S-H and the pore solution.\n"
            "Higher Rd values mean more alkali is bound in C-S-H.\n"
            "Typical values for C-S-H are around 0.4-0.5 for both K and Na.</small>"
        )
        explanation.set_halign(Gtk.Align.START)
        explanation.set_line_wrap(True)
        page.pack_start(explanation, False, False, 0)

        # Rd value editors
        rd_frame = Gtk.Frame(label=" Alkali Distribution Coefficients ")
        rd_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        rd_box.set_margin_top(15)
        rd_box.set_margin_bottom(15)
        rd_box.set_margin_start(15)
        rd_box.set_margin_end(15)

        # Find K and Na values
        k_value = 0.42
        na_value = 0.42
        for entry in self.rd_data:
            if entry['Rdelement'] == 'K':
                k_value = entry['Rdvalue']
            elif entry['Rdelement'] == 'Na':
                na_value = entry['Rdvalue']

        # K entry
        k_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        k_label = Gtk.Label(label="Rd (Potassium, K):")
        k_label.set_halign(Gtk.Align.START)
        k_label.set_width_chars(20)

        self.k_spin = Gtk.SpinButton()
        self.k_spin.set_adjustment(
            Gtk.Adjustment(value=k_value, lower=0.0, upper=2.0,
                          step_increment=0.01, page_increment=0.1)
        )
        self.k_spin.set_digits(3)
        self.k_spin.connect('value-changed', self._on_rd_changed)

        k_box.pack_start(k_label, False, False, 0)
        k_box.pack_start(self.k_spin, False, False, 0)
        rd_box.pack_start(k_box, False, False, 0)

        # Na entry
        na_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        na_label = Gtk.Label(label="Rd (Sodium, Na):")
        na_label.set_halign(Gtk.Align.START)
        na_label.set_width_chars(20)

        self.na_spin = Gtk.SpinButton()
        self.na_spin.set_adjustment(
            Gtk.Adjustment(value=na_value, lower=0.0, upper=2.0,
                          step_increment=0.01, page_increment=0.1)
        )
        self.na_spin.set_digits(3)
        self.na_spin.connect('value-changed', self._on_rd_changed)

        na_box.pack_start(na_label, False, False, 0)
        na_box.pack_start(self.na_spin, False, False, 0)
        rd_box.pack_start(na_box, False, False, 0)

        rd_frame.add(rd_box)
        page.pack_start(rd_frame, False, False, 0)

        # Reset button
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        reset_box.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.connect('clicked', self._on_rd_reset_clicked)
        reset_box.pack_start(reset_btn, False, False, 0)

        page.pack_start(reset_box, False, False, 0)

        # Info about typical values
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small><i>Default values (Rd = 0.42) are based on experimental data "
            "for portland cement hydration.</i></small>"
        )
        info_label.set_halign(Gtk.Align.START)
        page.pack_start(info_label, False, False, 0)

        return page

    def _on_rd_changed(self, spin):
        """Handle Rd value change."""
        # Update internal data
        k_value = self.k_spin.get_value()
        na_value = self.na_spin.get_value()

        self.rd_data = [
            {'Rdelement': 'K', 'Rdvalue': k_value},
            {'Rdelement': 'Na', 'Rdvalue': na_value}
        ]

    def _on_rd_reset_clicked(self, button):
        """Reset Rd values to defaults."""
        self.k_spin.set_value(0.42)
        self.na_spin.set_value(0.42)
        self.rd_data = list(CSHQ_RD_VALUES)
        self.logger.info("Reset Rd values to defaults")

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

    def get_poresize_distribution(self) -> List[Dict[str, float]]:
        """
        Get the configured poresize distribution.

        Returns:
            List of dicts with 'diameter' and 'volumefraction'
        """
        return self.psd_data

    def get_rd_values(self) -> List[Dict[str, Any]]:
        """
        Get the configured Rd values.

        Returns:
            List of dicts with 'Rdelement' and 'Rdvalue'
        """
        return self.rd_data

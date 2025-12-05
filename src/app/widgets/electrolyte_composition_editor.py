#!/usr/bin/env python3
"""
Electrolyte Composition Editor Widget

GTK widget for editing the initial concentrations of aqueous species (DCs)
in the electrolyte phase for THAMES simulations.

Each DC can have:
- condition: "initial" or "fixed"
- concentration: molal concentration (mol/kg water)

The editor validates that the overall charge balance is zero.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.gems_parser_service import GEMSParserService, DependentComponent


# Common aqueous ions with their charges for charge balance calculation
DC_CHARGES: Dict[str, int] = {
    # Cations
    "H+": 1,
    "Ca+2": 2,
    "CaOH+": 1,
    "Mg+2": 2,
    "MgOH+": 1,
    "K+": 1,
    "Na+": 1,
    "Al+3": 3,
    "AlO+": 1,
    "AlOH+2": 2,
    "AlHSiO3+2": 2,
    "Fe+2": 2,
    "FeOH+": 1,
    "Fe+3": 3,
    "FeOH+2": 2,
    "FeO+": 1,
    "FeHSiO3+2": 2,
    "Fe2(OH)2+4": 4,
    "Fe3(OH)4+5": 5,
    "Ca(HCO3)+": 1,
    "Ca(HSiO3)+": 1,
    "Mg(HCO3)+": 1,
    "Mg(HSiO3)+": 1,
    "Fe(HCO3)+": 1,
    "Fe(HSO4)+": 1,
    "Fe(SO4)+": 1,
    "Fe(HSO4)+2": 2,
    "Al(SO4)+": 1,

    # Anions
    "OH-": -1,
    "Cl-": -1,
    "CO3-2": -2,
    "HCO3-": -1,
    "SO4-2": -2,
    "HSO4-": -1,
    "HSO3-": -1,
    "SO3-2": -2,
    "S2O3-2": -2,
    "HS-": -1,
    "S-2": -2,
    "HSiO3-": -1,
    "SiO3-2": -2,
    "AlO2-": -1,
    "AlSiO5-3": -3,
    "FeO2-": -1,
    "Na(CO3)-": -1,
    "Na(SO4)-": -1,
    "K(SO4)-": -1,
    "Al(SO4)2-": -1,
    "Fe(SO4)2-": -1,

    # Neutral species (charge = 0)
    "H2O@": 0,
    "CO2@": 0,
    "CH4@": 0,
    "H2@": 0,
    "N2@": 0,
    "O2@": 0,
    "H2S@": 0,
    "SiO2@": 0,
    "Ca(CO3)@": 0,
    "Ca(SO4)@": 0,
    "CaSiO3@": 0,
    "Mg(CO3)@": 0,
    "MgSO4@": 0,
    "MgSiO3@": 0,
    "Fe(CO3)@": 0,
    "Fe(SO4)@": 0,
    "KOH@": 0,
    "NaOH@": 0,
    "Na(HCO3)@": 0,
    "AlO2H@": 0,
    "FeO2H@": 0,
}


@dataclass
class ElectrolyteCondition:
    """Represents a single electrolyte condition."""
    dc_name: str
    condition: str  # "initial" or "fixed"
    concentration: float  # molal concentration


class ElectrolyteCompositionEditor(Gtk.Box):
    """
    Widget for editing electrolyte composition (DC concentrations).

    Features:
    - List of DCs with condition type and concentration
    - Add/Remove DC entries
    - Charge balance validation
    - Default values for common cement pore solutions
    """

    __gsignals__ = {
        'composition-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, gems_parser: Optional[GEMSParserService] = None):
        """
        Initialize the electrolyte composition editor.

        Args:
            gems_parser: GEMS parser service for getting available DCs
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.logger = logging.getLogger('THAMES.ElectrolyteEditor')
        self.gems_parser = gems_parser

        # Get available aqueous DCs if parser provided
        self.available_dcs: List[str] = []
        if gems_parser:
            try:
                electrolyte_phase = gems_parser.get_phase("Electrolyte")
                if electrolyte_phase:
                    self.available_dcs = electrolyte_phase.dc_names
                else:
                    # Try aq_gen (legacy name)
                    electrolyte_phase = gems_parser.get_phase("aq_gen")
                    if electrolyte_phase:
                        self.available_dcs = electrolyte_phase.dc_names
            except Exception as e:
                self.logger.warning(f"Could not get electrolyte DCs: {e}")

        # If still empty, use hardcoded list of common DCs
        if not self.available_dcs:
            self.available_dcs = list(DC_CHARGES.keys())

        # Current conditions
        self.conditions: List[ElectrolyteCondition] = []

        # Build UI
        self._build_ui()

        # Load default conditions
        self._load_defaults()

    def _build_ui(self):
        """Build the widget UI."""
        # Header with title and buttons
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        title_label = Gtk.Label()
        title_label.set_markup("<b>Electrolyte Composition</b>")
        title_label.set_halign(Gtk.Align.START)
        header.pack_start(title_label, False, False, 0)

        header.pack_start(Gtk.Label(), True, True, 0)  # Spacer

        # Add DC button
        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        add_btn.set_tooltip_text("Add a species to the electrolyte")
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_start(add_btn, False, False, 0)

        # Load defaults button
        defaults_btn = Gtk.Button.new_with_label("Defaults")
        defaults_btn.set_tooltip_text("Load default cement pore solution composition")
        defaults_btn.connect("clicked", self._on_defaults_clicked)
        header.pack_start(defaults_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Scrolled window for the list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(150)
        scrolled.set_max_content_height(250)
        scrolled.set_can_focus(True)  # Enable keyboard navigation

        # ListBox for conditions
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(self.listbox)

        self.pack_start(scrolled, True, True, 0)

        # Charge balance status
        self.charge_label = Gtk.Label()
        self.charge_label.set_halign(Gtk.Align.START)
        self.pack_start(self.charge_label, False, False, 0)

        self._update_charge_balance()

    def _create_condition_row(self, condition: ElectrolyteCondition) -> Gtk.ListBoxRow:
        """Create a row widget for a condition."""
        row = Gtk.ListBoxRow()
        row.condition = condition

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_margin_start(5)
        hbox.set_margin_end(5)
        hbox.set_margin_top(3)
        hbox.set_margin_bottom(3)

        # DC name combo
        dc_combo = Gtk.ComboBoxText()
        dc_combo.set_tooltip_text("Dependent component (aqueous species)")
        for dc_name in sorted(self.available_dcs):
            dc_combo.append_text(dc_name)

        # Set current value
        if condition.dc_name in self.available_dcs:
            dc_combo.set_active(sorted(self.available_dcs).index(condition.dc_name))
        else:
            # Add custom entry
            dc_combo.append_text(condition.dc_name)
            dc_combo.set_active(len(self.available_dcs))

        dc_combo.connect("changed", self._on_dc_changed, row)
        hbox.pack_start(dc_combo, False, False, 0)
        row.dc_combo = dc_combo

        # Condition type combo
        type_combo = Gtk.ComboBoxText()
        type_combo.append("initial", "Initial")
        type_combo.append("fixed", "Fixed")
        type_combo.set_active_id(condition.condition)
        type_combo.set_tooltip_text("Initial: starting concentration; Fixed: maintained throughout")
        type_combo.connect("changed", self._on_type_changed, row)
        hbox.pack_start(type_combo, False, False, 0)
        row.type_combo = type_combo

        # Concentration entry with scientific notation support
        conc_entry = Gtk.Entry()
        conc_entry.set_width_chars(12)
        conc_entry.set_text(f"{condition.concentration:.2e}")
        conc_entry.set_tooltip_text("Molal concentration (mol/kg water)")
        conc_entry.connect("changed", self._on_concentration_changed, row)
        hbox.pack_start(conc_entry, False, False, 0)
        row.conc_entry = conc_entry

        # Units label
        units_label = Gtk.Label("mol/kg")
        units_label.get_style_context().add_class("dim-label")
        hbox.pack_start(units_label, False, False, 0)

        # Charge indicator
        charge = DC_CHARGES.get(condition.dc_name, 0)
        charge_label = Gtk.Label()
        if charge > 0:
            charge_label.set_markup(f'<span foreground="blue">+{charge}</span>')
        elif charge < 0:
            charge_label.set_markup(f'<span foreground="red">{charge}</span>')
        else:
            charge_label.set_markup('<span foreground="gray">0</span>')
        charge_label.set_width_chars(4)
        hbox.pack_start(charge_label, False, False, 0)
        row.charge_label = charge_label

        # Remove button
        remove_btn = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        remove_btn.set_tooltip_text("Remove this species")
        remove_btn.connect("clicked", self._on_remove_clicked, row)
        hbox.pack_start(remove_btn, False, False, 0)

        row.add(hbox)
        return row

    def _on_dc_changed(self, combo: Gtk.ComboBoxText, row: Gtk.ListBoxRow):
        """Handle DC selection change."""
        new_dc = combo.get_active_text()
        if new_dc:
            row.condition.dc_name = new_dc

            # Update charge indicator
            charge = DC_CHARGES.get(new_dc, 0)
            if charge > 0:
                row.charge_label.set_markup(f'<span foreground="blue">+{charge}</span>')
            elif charge < 0:
                row.charge_label.set_markup(f'<span foreground="red">{charge}</span>')
            else:
                row.charge_label.set_markup('<span foreground="gray">0</span>')

            self._update_charge_balance()
            self.emit('composition-changed')

    def _on_type_changed(self, combo: Gtk.ComboBoxText, row: Gtk.ListBoxRow):
        """Handle condition type change."""
        new_type = combo.get_active_id()
        if new_type:
            row.condition.condition = new_type
            self.emit('composition-changed')

    def _on_concentration_changed(self, entry: Gtk.Entry, row: Gtk.ListBoxRow):
        """Handle concentration value change."""
        try:
            new_conc = float(entry.get_text())
            if new_conc >= 0:
                row.condition.concentration = new_conc
                entry.get_style_context().remove_class("error")
                self._update_charge_balance()
                self.emit('composition-changed')
            else:
                entry.get_style_context().add_class("error")
        except ValueError:
            entry.get_style_context().add_class("error")

    def _on_add_clicked(self, button: Gtk.Button):
        """Add a new DC entry."""
        # Find a DC not yet used
        used_dcs = {c.dc_name for c in self.conditions}
        available = [dc for dc in self.available_dcs if dc not in used_dcs]

        if available:
            new_dc = available[0]
        else:
            new_dc = self.available_dcs[0] if self.available_dcs else "K+"

        condition = ElectrolyteCondition(
            dc_name=new_dc,
            condition="initial",
            concentration=1.0e-6
        )
        self.conditions.append(condition)

        row = self._create_condition_row(condition)
        self.listbox.add(row)
        row.show_all()

        self._update_charge_balance()
        self.emit('composition-changed')

    def _on_remove_clicked(self, button: Gtk.Button, row: Gtk.ListBoxRow):
        """Remove a DC entry."""
        self.conditions.remove(row.condition)
        self.listbox.remove(row)

        self._update_charge_balance()
        self.emit('composition-changed')

    def _on_defaults_clicked(self, button: Gtk.Button):
        """Load default electrolyte composition."""
        self._load_defaults()
        self.emit('composition-changed')

    def _load_defaults(self):
        """Load default cement pore solution composition."""
        from app.services.simparams_service import DEFAULT_ELECTROLYTE_CONDITIONS

        # Clear current
        self.conditions.clear()
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        # Add defaults
        for entry in DEFAULT_ELECTROLYTE_CONDITIONS:
            condition = ElectrolyteCondition(
                dc_name=entry["DCname"],
                condition=entry["condition"],
                concentration=entry["concentration"]
            )
            self.conditions.append(condition)

            row = self._create_condition_row(condition)
            self.listbox.add(row)

        self.listbox.show_all()
        self._update_charge_balance()

    def _update_charge_balance(self):
        """Calculate and display charge balance."""
        total_positive = 0.0
        total_negative = 0.0

        for condition in self.conditions:
            charge = DC_CHARGES.get(condition.dc_name, 0)
            contribution = charge * condition.concentration

            if contribution > 0:
                total_positive += contribution
            else:
                total_negative += abs(contribution)

        net_charge = total_positive - total_negative

        # Display status
        if abs(net_charge) < 1e-10:
            self.charge_label.set_markup(
                '<span foreground="green">Charge balance: OK (net = 0)</span>'
            )
        else:
            if net_charge > 0:
                self.charge_label.set_markup(
                    f'<span foreground="orange">Charge balance: +{net_charge:.2e} '
                    f'(add anions or reduce cations)</span>'
                )
            else:
                self.charge_label.set_markup(
                    f'<span foreground="orange">Charge balance: {net_charge:.2e} '
                    f'(add cations or reduce anions)</span>'
                )

    # =========================================================================
    # Public API
    # =========================================================================

    def get_electrolyte_conditions(self) -> List[Dict[str, Any]]:
        """
        Get the current electrolyte conditions in simparams.json format.

        Returns:
            List of dicts with DCname, condition, concentration keys
        """
        return [
            {
                "DCname": c.dc_name,
                "condition": c.condition,
                "concentration": c.concentration
            }
            for c in self.conditions
        ]

    def set_electrolyte_conditions(self, conditions: List[Dict[str, Any]]):
        """
        Set the electrolyte conditions.

        Args:
            conditions: List of dicts with DCname, condition, concentration keys
        """
        # Clear current
        self.conditions.clear()
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        # Add new conditions
        for entry in conditions:
            condition = ElectrolyteCondition(
                dc_name=entry.get("DCname", "K+"),
                condition=entry.get("condition", "initial"),
                concentration=entry.get("concentration", 1.0e-6)
            )
            self.conditions.append(condition)

            row = self._create_condition_row(condition)
            self.listbox.add(row)

        self.listbox.show_all()
        self._update_charge_balance()

    def is_charge_balanced(self) -> bool:
        """
        Check if the current composition is charge balanced.

        Returns:
            True if net charge is approximately zero
        """
        total_charge = 0.0
        for condition in self.conditions:
            charge = DC_CHARGES.get(condition.dc_name, 0)
            total_charge += charge * condition.concentration

        return abs(total_charge) < 1e-10


# Register the signals
GObject.type_register(ElectrolyteCompositionEditor)

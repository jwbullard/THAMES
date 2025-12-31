#!/usr/bin/env python3
"""
Phase Configuration Dialog

Combined tabbed dialog for configuring all aspects of a phase:
- Kinetics (kinetic model parameters)
- Affinity (contact angles for nucleation)
- C-S-H (poresize distribution and Rd values, for C-S-H phases only)

This provides a unified interface for phase configuration, accessible via
double-click on any phase in the hydration product selector.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import logging
from typing import Dict, Any, Optional, List

from app.services.kinetic_defaults_service import get_kinetic_defaults_service
from app.services.hydration_products_service import (
    get_hydration_products_service,
    DEFAULT_CONTACT_ANGLE,
    CSHQ_PORESIZE_DISTRIBUTION,
    CSHQ_RD_VALUES,
)
from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
)


class PhaseConfigurationDialog(Gtk.Dialog):
    """
    Combined dialog for configuring kinetics and affinity of a phase.

    Provides tabs for:
    - Kinetics: Edit kinetic model and parameters
    - Affinity: Edit contact angles with substrate phases
    - C-S-H: Edit poresize distribution and Rd values (C-S-H phases only)
    """

    KINETIC_TYPES = [
        ("Thermodynamic", "No kinetic model - thermodynamically controlled"),
        ("ParrotKilloh", "Clinker phases (Alite, Belite, Aluminate, Ferrite)"),
        ("Standard", "Sulfate phases (Gypsum, Bassanite, Anhydrite)"),
        ("Pozzolanic", "Pozzolanic phases (Quartz, Fly ash, Silica fume)"),
    ]

    def __init__(
        self,
        parent: Gtk.Window,
        phase_name: str,
        current_kinetics: Optional[Dict[str, Any]] = None,
        current_affinity: Optional[List[Dict[str, Any]]] = None,
        current_psd: Optional[List[Dict[str, float]]] = None,
        current_rd: Optional[List[Dict[str, Any]]] = None,
        available_phases: Optional[List[str]] = None,
        has_csh_data: bool = False,
        initial_tab: str = "kinetics"
    ):
        """
        Initialize the phase configuration dialog.

        Args:
            parent: Parent window
            phase_name: GEMS phase name
            current_kinetics: Current kinetic parameters (or None for defaults)
            current_affinity: Current affinity configuration
            current_psd: Current C-S-H poresize distribution
            current_rd: Current C-S-H Rd values
            available_phases: List of available substrate phases for affinity
            has_csh_data: Whether this phase has C-S-H special data
            initial_tab: Which tab to show initially ("kinetics", "affinity", "csh")
        """
        super().__init__(
            title=f"Configure Phase: {phase_name}",
            transient_for=parent,
            flags=0
        )

        self.phase_name = phase_name
        self.has_csh_data = has_csh_data
        self.logger = logging.getLogger('THAMES.PhaseConfigDialog')
        self.kinetic_defaults = get_kinetic_defaults_service()
        self.products_service = get_hydration_products_service()

        # Store current configurations
        self.current_kinetics = current_kinetics
        self.current_affinity = current_affinity or []
        self.current_psd = current_psd
        self.current_rd = current_rd
        self.available_phases = available_phases or self._get_default_phases()

        # Widgets storage
        self.kinetic_widgets: Dict[str, Gtk.SpinButton] = {}
        self.affinity_widgets: Dict[str, Gtk.SpinButton] = {}
        self.psd_widgets: List[Dict[str, Gtk.SpinButton]] = []
        self.rd_widgets: Dict[str, Gtk.SpinButton] = {}
        self.current_kinetic_type: Optional[str] = None

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        self.set_default_size(500, 550)

        # Content area
        content = self.get_content_area()
        content.set_margin_start(10)
        content.set_margin_end(10)
        content.set_margin_top(10)
        content.set_margin_bottom(10)

        # Phase header
        header = Gtk.Label()
        header.set_markup(f"<b>{phase_name}</b>")
        header.set_halign(Gtk.Align.START)
        header.set_margin_bottom(10)
        content.pack_start(header, False, False, 0)

        # Create notebook with tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_vexpand(True)

        # Kinetics tab
        kinetics_page = self._create_kinetics_tab()
        self.notebook.append_page(kinetics_page, Gtk.Label(label="Kinetics"))

        # Affinity tab
        affinity_page = self._create_affinity_tab()
        self.notebook.append_page(affinity_page, Gtk.Label(label="Affinity"))

        # C-S-H tab (only if applicable)
        if has_csh_data:
            csh_page = self._create_csh_tab()
            self.notebook.append_page(csh_page, Gtk.Label(label="C-S-H"))

        content.pack_start(self.notebook, True, True, 0)

        # Set initial tab
        if initial_tab == "affinity":
            self.notebook.set_current_page(1)
        elif initial_tab == "csh" and has_csh_data:
            self.notebook.set_current_page(2)

        self.show_all()

    def _get_default_phases(self) -> List[str]:
        """Get default substrate phases for affinity."""
        return [
            "Alite", "Belite", "Aluminate", "Ferrite",
            "Gypsum", "Bassanite", "Anhydrite",
            "Arcanite", "Thenardite",
            "CSHQ", "Portlandite", "ettr",
        ]

    # =========================================================================
    # KINETICS TAB
    # =========================================================================

    def _create_kinetics_tab(self) -> Gtk.Widget:
        """Create the kinetics configuration tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Kinetic type selector
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        type_label = Gtk.Label("Kinetic Model:")
        type_label.set_halign(Gtk.Align.START)
        type_box.pack_start(type_label, False, False, 0)

        self.type_combo = Gtk.ComboBoxText()
        for type_name, description in self.KINETIC_TYPES:
            self.type_combo.append(type_name, type_name)
        self.type_combo.connect('changed', self._on_kinetic_type_changed)
        type_box.pack_start(self.type_combo, True, True, 0)

        box.pack_start(type_box, False, False, 0)

        # Type description
        self.type_description = Gtk.Label()
        self.type_description.set_halign(Gtk.Align.START)
        self.type_description.set_line_wrap(True)
        self.type_description.get_style_context().add_class("dim-label")
        box.pack_start(self.type_description, False, False, 0)

        # Separator
        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

        # Scrolled window for parameters
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.kinetics_params_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(self.kinetics_params_box)
        box.pack_start(scrolled, True, True, 0)

        # Reset button
        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.connect('clicked', self._on_reset_kinetics)
        reset_btn.set_halign(Gtk.Align.END)
        box.pack_start(reset_btn, False, False, 0)

        # Determine initial type
        if self.current_kinetics and 'type' in self.current_kinetics:
            initial_type = self.current_kinetics['type']
        else:
            initial_type = self.kinetic_defaults.get_kinetic_type(self.phase_name) or "Thermodynamic"

        self.type_combo.set_active_id(initial_type)

        # Apply current params if any
        if self.current_kinetics:
            self._set_kinetic_parameters(self.current_kinetics)

        return box

    def _on_kinetic_type_changed(self, combo: Gtk.ComboBoxText) -> None:
        """Handle kinetic type change."""
        type_id = combo.get_active_id()
        if type_id == self.current_kinetic_type:
            return

        self.current_kinetic_type = type_id

        # Update description
        for type_name, description in self.KINETIC_TYPES:
            if type_name == type_id:
                self.type_description.set_markup(f'<span size="small">{description}</span>')
                break

        # Rebuild parameters UI
        self._build_kinetics_ui(type_id)

    def _build_kinetics_ui(self, kinetic_type: str) -> None:
        """Build the kinetics parameters UI."""
        # Clear existing widgets
        for child in self.kinetics_params_box.get_children():
            self.kinetics_params_box.remove(child)
        self.kinetic_widgets.clear()

        if kinetic_type == "Thermodynamic":
            label = Gtk.Label()
            label.set_markup(
                '<span foreground="gray">No kinetic parameters.\n\n'
                'Phase dissolution/precipitation will be controlled\n'
                'purely by thermodynamic equilibrium.</span>'
            )
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            self.kinetics_params_box.pack_start(label, True, True, 20)
        else:
            defaults = self._get_kinetic_defaults(kinetic_type)
            if defaults:
                grid = Gtk.Grid()
                grid.set_row_spacing(5)
                grid.set_column_spacing(10)

                if kinetic_type == "ParrotKilloh":
                    self._create_parrot_killoh_fields(grid, defaults)
                elif kinetic_type == "Standard":
                    self._create_standard_fields(grid, defaults)
                elif kinetic_type == "Pozzolanic":
                    self._create_pozzolanic_fields(grid, defaults)

                self.kinetics_params_box.pack_start(grid, False, False, 0)

        self.kinetics_params_box.show_all()

    def _get_kinetic_defaults(self, kinetic_type: str):
        """Get default parameters for a kinetic type."""
        defaults = self.kinetic_defaults.get_kinetics_for_phase(self.phase_name)
        if defaults and defaults.to_dict().get('type') == kinetic_type:
            return defaults

        if kinetic_type == "ParrotKilloh":
            return self.kinetic_defaults.PARROT_KILLOH_DEFAULTS.get("Alite")
        elif kinetic_type == "Standard":
            return self.kinetic_defaults.STANDARD_DEFAULTS.get("Gypsum")
        elif kinetic_type == "Pozzolanic":
            return self.kinetic_defaults.POZZOLANIC_DEFAULTS.get("Quartz")
        return None

    def _create_spin_button(self, value: float, min_val: float, max_val: float,
                            step: float, digits: int) -> Gtk.SpinButton:
        """Create a spin button."""
        spin = Gtk.SpinButton.new_with_range(min_val, max_val, step)
        spin.set_value(value)
        spin.set_digits(digits)
        spin.set_width_chars(12)
        return spin

    def _add_kinetic_row(self, grid: Gtk.Grid, row: int, label_text: str,
                         tooltip: str, spin: Gtk.SpinButton, param_key: str) -> None:
        """Add a kinetic parameter row."""
        label = Gtk.Label(label_text)
        label.set_halign(Gtk.Align.END)
        label.set_tooltip_text(tooltip)
        grid.attach(label, 0, row, 1, 1)

        spin.set_tooltip_text(tooltip)
        grid.attach(spin, 1, row, 1, 1)

        self.kinetic_widgets[param_key] = spin

    def _create_parrot_killoh_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create Parrot-Killoh kinetic fields."""
        row = 0
        self._add_kinetic_row(grid, row, "k1:", "Nucleation/growth rate constant",
                              self._create_spin_button(defaults.k1, 0, 10, 0.01, 3), "k1")
        row += 1
        self._add_kinetic_row(grid, row, "k2:", "Early diffusion rate constant",
                              self._create_spin_button(defaults.k2, 0, 1, 0.001, 4), "k2")
        row += 1
        self._add_kinetic_row(grid, row, "k3:", "Late diffusion rate constant",
                              self._create_spin_button(defaults.k3, 0, 10, 0.01, 3), "k3")
        row += 1
        self._add_kinetic_row(grid, row, "n1:", "Nucleation/growth exponent",
                              self._create_spin_button(defaults.n1, 0, 5, 0.01, 3), "n1")
        row += 1
        self._add_kinetic_row(grid, row, "n3:", "Late diffusion exponent",
                              self._create_spin_button(defaults.n3, 0, 10, 0.1, 2), "n3")
        row += 1
        self._add_kinetic_row(grid, row, "dorHcoeff:", "Lothenbach-Kulik H coefficient",
                              self._create_spin_button(defaults.dorHcoeff, 0, 5, 0.01, 3), "dorHcoeff")
        row += 1
        self._add_kinetic_row(grid, row, "Ea (J/mol):", "Activation energy",
                              self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_kinetic_row(grid, row, "LOI:", "Loss on ignition",
                              self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _create_standard_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create Standard kinetic fields (rate constants in μmol/m²/s)."""
        row = 0
        self._add_kinetic_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant",
                              self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.1, 4), "dissolutionRateConst")
        row += 1
        self._add_kinetic_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant",
                              self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.1, 4), "diffusionRateConstEarly")
        row += 1
        self._add_kinetic_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant",
                              self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.1, 4), "diffusionRateConstLate")
        row += 1
        self._add_kinetic_row(grid, row, "Diss. units:", "Number of DC units per dissolution",
                              self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0), "dissolvedUnits")
        row += 1
        self._add_kinetic_row(grid, row, "SI exp:", "Saturation index exponent",
                              self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2), "siexp")
        row += 1
        self._add_kinetic_row(grid, row, "DF exp:", "Driving force exponent",
                              self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2), "dfexp")
        row += 1
        self._add_kinetic_row(grid, row, "DOR exp:", "Degree of reaction exponent",
                              self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2), "dorexp")
        row += 1
        self._add_kinetic_row(grid, row, "Ea (J/mol):", "Activation energy",
                              self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_kinetic_row(grid, row, "LOI:", "Loss on ignition",
                              self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _create_pozzolanic_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create Pozzolanic kinetic fields (rate constants in μmol/m²/s)."""
        row = 0
        self._add_kinetic_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant",
                              self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.0001, 6), "dissolutionRateConst")
        row += 1
        self._add_kinetic_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant",
                              self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.0001, 6), "diffusionRateConstEarly")
        row += 1
        self._add_kinetic_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant",
                              self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.0001, 6), "diffusionRateConstLate")
        row += 1
        self._add_kinetic_row(grid, row, "Diss. units:", "Number of DC units per dissolution",
                              self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0), "dissolvedUnits")
        row += 1
        self._add_kinetic_row(grid, row, "SI exp:", "Saturation index exponent",
                              self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2), "siexp")
        row += 1
        self._add_kinetic_row(grid, row, "DF exp:", "Driving force exponent",
                              self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2), "dfexp")
        row += 1
        self._add_kinetic_row(grid, row, "DOR exp:", "Degree of reaction exponent",
                              self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2), "dorexp")
        row += 1
        self._add_kinetic_row(grid, row, "OH exp:", "Hydroxyl ion activity exponent",
                              self._create_spin_button(defaults.ohexp, 0, 5, 0.1, 2), "ohexp")
        row += 1
        self._add_kinetic_row(grid, row, "SiO₂:", "SiO₂ content (mass fraction)",
                              self._create_spin_button(defaults.sio2, 0, 1, 0.01, 3), "sio2")
        row += 1
        self._add_kinetic_row(grid, row, "Ea (J/mol):", "Activation energy",
                              self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_kinetic_row(grid, row, "LOI:", "Loss on ignition",
                              self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _set_kinetic_parameters(self, params: Dict[str, Any]) -> None:
        """Set kinetic parameter values from a dictionary."""
        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        for key, value in params.items():
            if key in self.kinetic_widgets:
                display_value = float(value)
                if key in rate_const_fields and self.current_kinetic_type in ('Standard', 'Pozzolanic'):
                    display_value = display_value * 1e6
                self.kinetic_widgets[key].set_value(display_value)

    def _on_reset_kinetics(self, button: Gtk.Button) -> None:
        """Reset kinetics to defaults."""
        default_type = self.kinetic_defaults.get_kinetic_type(self.phase_name) or "Thermodynamic"
        self.current_kinetic_type = None
        self.type_combo.set_active_id(default_type)

    def get_kinetics_data(self) -> Optional[Dict[str, Any]]:
        """Get the current kinetic parameters."""
        if self.current_kinetic_type == "Thermodynamic":
            return None

        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        params = {'type': self.current_kinetic_type}
        for key, spin in self.kinetic_widgets.items():
            value = spin.get_value()
            if key == 'dissolvedUnits':
                value = int(value)
            elif key in rate_const_fields and self.current_kinetic_type in ('Standard', 'Pozzolanic'):
                value = value * 1e-6
            params[key] = value

        return params

    # =========================================================================
    # AFFINITY TAB
    # =========================================================================

    def _create_affinity_tab(self) -> Gtk.Widget:
        """Create the affinity configuration tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Description
        desc = Gtk.Label()
        desc.set_markup(
            '<span size="small">Contact angles control nucleation preference.\n'
            '0° = high affinity, 90° = neutral, 180° = avoids substrate.</span>'
        )
        desc.set_halign(Gtk.Align.START)
        desc.set_line_wrap(True)
        box.pack_start(desc, False, False, 0)

        # Scrolled window for affinity entries
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(10)

        # Header
        header_phase = Gtk.Label()
        header_phase.set_markup("<b>Substrate Phase</b>")
        header_phase.set_halign(Gtk.Align.START)
        grid.attach(header_phase, 0, 0, 1, 1)

        header_angle = Gtk.Label()
        header_angle.set_markup("<b>Contact Angle (°)</b>")
        grid.attach(header_angle, 1, 0, 1, 1)

        # Build affinity lookup (handles 'affinityphase'/'contactanglevalue' format)
        affinity_lookup = {
            a.get('affinityphase', a.get('phase', '')): a.get('contactanglevalue', a.get('contactAngle', DEFAULT_CONTACT_ANGLE))
            for a in self.current_affinity
        }

        # Add rows for each available phase
        row = 1
        for phase in self.available_phases:
            label = Gtk.Label(phase)
            label.set_halign(Gtk.Align.START)
            grid.attach(label, 0, row, 1, 1)

            angle = affinity_lookup.get(phase, DEFAULT_CONTACT_ANGLE)
            spin = Gtk.SpinButton.new_with_range(0, 180, 1)
            spin.set_value(angle)
            spin.set_digits(0)
            spin.set_width_chars(6)
            grid.attach(spin, 1, row, 1, 1)

            self.affinity_widgets[phase] = spin
            row += 1

        scrolled.add(grid)
        box.pack_start(scrolled, True, True, 0)

        # Reset button
        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.connect('clicked', self._on_reset_affinity)
        reset_btn.set_halign(Gtk.Align.END)
        box.pack_start(reset_btn, False, False, 0)

        return box

    def _on_reset_affinity(self, button: Gtk.Button) -> None:
        """Reset affinity to defaults."""
        default_affinity = self.products_service.get_default_affinity(self.phase_name)
        affinity_lookup = {
            a.get('affinityphase', a.get('phase', '')): a.get('contactanglevalue', a.get('contactAngle', DEFAULT_CONTACT_ANGLE))
            for a in default_affinity
        }

        for phase, spin in self.affinity_widgets.items():
            spin.set_value(affinity_lookup.get(phase, DEFAULT_CONTACT_ANGLE))

    def get_affinity_data(self) -> List[Dict[str, Any]]:
        """Get the current affinity configuration (uses THAMES format keys)."""
        result = []
        for phase, spin in self.affinity_widgets.items():
            result.append({
                'affinityphase': phase,
                'contactanglevalue': int(spin.get_value())
            })
        return result

    # =========================================================================
    # C-S-H TAB
    # =========================================================================

    def _create_csh_tab(self) -> Gtk.Widget:
        """Create the C-S-H configuration tab."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)

        # Poresize distribution section
        psd_label = Gtk.Label()
        psd_label.set_markup("<b>Poresize Distribution</b>")
        psd_label.set_halign(Gtk.Align.START)
        box.pack_start(psd_label, False, False, 0)

        psd_desc = Gtk.Label()
        psd_desc.set_markup('<span size="small">Gel porosity model: diameter (nm) vs volume fraction</span>')
        psd_desc.set_halign(Gtk.Align.START)
        box.pack_start(psd_desc, False, False, 0)

        # TODO: Implement C-S-H poresize distribution editor
        # =====================================================
        # This section needs a table/grid editor for the PSD data.
        # Data format: List of {'diameter': float (nm), 'volumefraction': float}
        # Default values are in CSHQ_PORESIZE_DISTRIBUTION (hydration_products_service.py)
        #
        # Required components:
        # 1. Gtk.ListStore with columns: diameter (float), volumefraction (float)
        # 2. Gtk.TreeView with editable CellRendererSpin for both columns
        # 3. Add/Remove row buttons
        # 4. Validation: volume fractions should sum to ~1.0 (with tolerance)
        # 5. Store widgets in self.psd_widgets for get_csh_data() to retrieve
        # 6. Update get_csh_data() to read from widgets instead of returning current_psd
        #
        # The psd data is used in THAMES-Hydration to model gel porosity in C-S-H.
        # =====================================================
        psd_note = Gtk.Label("(Poresize distribution editing not yet implemented)")
        psd_note.get_style_context().add_class("dim-label")
        box.pack_start(psd_note, False, False, 10)

        # Separator
        box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

        # Rd values section
        rd_label = Gtk.Label()
        rd_label.set_markup("<b>Rd Values (Alkali Distribution)</b>")
        rd_label.set_halign(Gtk.Align.START)
        box.pack_start(rd_label, False, False, 0)

        rd_grid = Gtk.Grid()
        rd_grid.set_row_spacing(5)
        rd_grid.set_column_spacing(10)

        # Use current values or defaults
        rd_data = self.current_rd or CSHQ_RD_VALUES

        row = 0
        for entry in rd_data:
            # Handle both key formats: 'Rdelement'/'Rdvalue' (THAMES) or 'element'/'Rd'
            element = entry.get('Rdelement', entry.get('element', ''))
            rd_value = entry.get('Rdvalue', entry.get('Rd', 0.42))

            label = Gtk.Label(f"{element} Rd:")
            label.set_halign(Gtk.Align.END)
            rd_grid.attach(label, 0, row, 1, 1)

            spin = Gtk.SpinButton.new_with_range(0, 10, 0.01)
            spin.set_value(rd_value)
            spin.set_digits(3)
            spin.set_width_chars(8)
            rd_grid.attach(spin, 1, row, 1, 1)

            self.rd_widgets[element] = spin
            row += 1

        box.pack_start(rd_grid, False, False, 0)

        return box

    def get_csh_data(self) -> Dict[str, Any]:
        """Get the current C-S-H configuration (uses THAMES format keys)."""
        # PSD not implemented yet, return current
        psd = self.current_psd or CSHQ_PORESIZE_DISTRIBUTION

        # Get Rd values from widgets (use THAMES format keys)
        rd = []
        for element, spin in self.rd_widgets.items():
            rd.append({
                'Rdelement': element,
                'Rdvalue': spin.get_value()
            })

        return {
            'poresize_distribution': psd,
            'rd_values': rd
        }

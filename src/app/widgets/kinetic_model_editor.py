#!/usr/bin/env python3
"""
Kinetic Model Editor Widget

GTK widget for viewing and editing kinetic model parameters for dissolving phases
in THAMES-Hydration simulations.

Supports three kinetic model types:
- ParrotKilloh: For clinker phases (Alite, Belite, Aluminate, Ferrite)
- Standard: For sulfate phases (Gypsum, Bassanite, Anhydrite)
- Pozzolanic: For pozzolanic phases (Quartz, Mullite, fly ash glasses)
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, Pango
import logging
from typing import Dict, Any, Optional, List

from app.models.kinetic_parameters import (
    ParrotKillohKinetics,
    StandardKinetics,
    PozzolanicKinetics,
    KineticParameters,
    kinetics_from_dict,
)
from app.services.kinetic_defaults_service import (
    KineticDefaultsService,
    get_kinetic_defaults_service,
)


class KineticModelEditor(Gtk.Box):
    """
    Widget for editing kinetic model parameters for a single phase.

    Shows the appropriate parameter fields based on the kinetic model type,
    with defaults from the KineticDefaultsService.
    """

    __gsignals__ = {
        'parameters-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, phase_name: str = "", editable: bool = True):
        """
        Initialize the kinetic model editor.

        Args:
            phase_name: GEMS phase name (determines kinetic model type)
            editable: Whether parameters can be edited
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.phase_name = phase_name
        self.editable = editable
        self.logger = logging.getLogger('THAMES.KineticModelEditor')
        self.kinetic_defaults = get_kinetic_defaults_service()

        # Store parameter widgets
        self.param_widgets: Dict[str, Gtk.SpinButton] = {}
        self.kinetic_type: Optional[str] = None

        # Build UI based on phase
        if phase_name:
            self._setup_for_phase(phase_name)

    def _setup_for_phase(self, phase_name: str) -> None:
        """Setup the editor for a specific phase."""
        self.phase_name = phase_name
        self.kinetic_type = self.kinetic_defaults.get_kinetic_type(phase_name)

        # Clear existing widgets
        for child in self.get_children():
            self.remove(child)
        self.param_widgets.clear()

        if self.kinetic_type is None:
            # No kinetic model for this phase
            label = Gtk.Label("No kinetic model for this phase")
            label.get_style_context().add_class("dim-label")
            self.pack_start(label, False, False, 0)
            self.show_all()
            return

        # Get defaults
        defaults = self.kinetic_defaults.get_kinetics_for_phase(phase_name)

        # Create header
        header = Gtk.Label()
        header.set_markup(f"<b>{self.kinetic_type} Kinetics</b>")
        header.set_halign(Gtk.Align.START)
        self.pack_start(header, False, False, 0)

        # Create parameter grid
        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(10)
        grid.set_margin_start(10)

        if self.kinetic_type == 'ParrotKilloh':
            self._create_parrot_killoh_fields(grid, defaults)
        elif self.kinetic_type == 'Standard':
            self._create_standard_fields(grid, defaults)
        elif self.kinetic_type == 'Pozzolanic':
            self._create_pozzolanic_fields(grid, defaults)

        self.pack_start(grid, False, False, 0)
        self.show_all()

    def _create_spin_button(
        self,
        value: float,
        min_val: float,
        max_val: float,
        step: float,
        digits: int
    ) -> Gtk.SpinButton:
        """Create a spin button with specified parameters."""
        spin = Gtk.SpinButton.new_with_range(min_val, max_val, step)
        spin.set_value(value)
        spin.set_digits(digits)
        spin.set_sensitive(self.editable)
        spin.set_width_chars(12)
        spin.connect('value-changed', self._on_value_changed)
        return spin

    def _add_param_row(
        self,
        grid: Gtk.Grid,
        row: int,
        label_text: str,
        tooltip: str,
        spin: Gtk.SpinButton,
        param_key: str
    ) -> None:
        """Add a parameter row to the grid."""
        label = Gtk.Label(label_text)
        label.set_halign(Gtk.Align.END)
        label.set_tooltip_text(tooltip)
        grid.attach(label, 0, row, 1, 1)

        spin.set_tooltip_text(tooltip)
        grid.attach(spin, 1, row, 1, 1)

        self.param_widgets[param_key] = spin

    def _create_parrot_killoh_fields(
        self,
        grid: Gtk.Grid,
        defaults: ParrotKillohKinetics
    ) -> None:
        """Create fields for Parrot-Killoh kinetics."""
        row = 0

        # k1 - nucleation/growth rate constant
        spin = self._create_spin_button(defaults.k1, 0, 10, 0.01, 3)
        self._add_param_row(grid, row, "k1:", "Nucleation/growth rate constant", spin, "k1")
        row += 1

        # k2 - early diffusion rate constant
        spin = self._create_spin_button(defaults.k2, 0, 1, 0.001, 4)
        self._add_param_row(grid, row, "k2:", "Early diffusion rate constant", spin, "k2")
        row += 1

        # k3 - late diffusion rate constant
        spin = self._create_spin_button(defaults.k3, 0, 10, 0.01, 3)
        self._add_param_row(grid, row, "k3:", "Late diffusion rate constant", spin, "k3")
        row += 1

        # n1 - nucleation/growth exponent
        spin = self._create_spin_button(defaults.n1, 0, 5, 0.01, 3)
        self._add_param_row(grid, row, "n1:", "Nucleation/growth exponent", spin, "n1")
        row += 1

        # n3 - late diffusion exponent
        spin = self._create_spin_button(defaults.n3, 0, 10, 0.1, 2)
        self._add_param_row(grid, row, "n3:", "Late diffusion exponent", spin, "n3")
        row += 1

        # dorHcoeff - Lothenbach-Kulik H coefficient
        spin = self._create_spin_button(defaults.dorHcoeff, 0, 5, 0.01, 3)
        self._add_param_row(grid, row, "dorHcoeff:", "Lothenbach-Kulik H coefficient", spin, "dorHcoeff")
        row += 1

        # Activation energy
        spin = self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0)
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy", spin, "activationEnergy")
        row += 1

        # LOI
        spin = self._create_spin_button(defaults.loi, 0, 1, 0.001, 4)
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)", spin, "loi")

    def _create_standard_fields(
        self,
        grid: Gtk.Grid,
        defaults: StandardKinetics
    ) -> None:
        """Create fields for Standard kinetics."""
        # Rate constants displayed in μmol/m²/s (multiply by 1e6 for display)
        row = 0

        # Dissolution rate constant
        spin = self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.1, 4)
        self._add_param_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant", spin, "dissolutionRateConst")
        row += 1

        # Early diffusion rate constant
        spin = self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.1, 4)
        self._add_param_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant", spin, "diffusionRateConstEarly")
        row += 1

        # Late diffusion rate constant
        spin = self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.1, 4)
        self._add_param_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant", spin, "diffusionRateConstLate")
        row += 1

        # Dissolved units
        spin = self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0)
        self._add_param_row(grid, row, "Diss. units:", "Number of DC units per dissolution event", spin, "dissolvedUnits")
        row += 1

        # siexp
        spin = self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "SI exp:", "Saturation index exponent", spin, "siexp")
        row += 1

        # dfexp
        spin = self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "DF exp:", "Driving force exponent", spin, "dfexp")
        row += 1

        # dorexp
        spin = self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "DOR exp:", "Degree of reaction exponent", spin, "dorexp")
        row += 1

        # Activation energy
        spin = self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0)
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy", spin, "activationEnergy")
        row += 1

        # LOI
        spin = self._create_spin_button(defaults.loi, 0, 1, 0.001, 4)
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)", spin, "loi")

    def _create_pozzolanic_fields(
        self,
        grid: Gtk.Grid,
        defaults: PozzolanicKinetics
    ) -> None:
        """Create fields for Pozzolanic kinetics."""
        # Rate constants displayed in μmol/m²/s (multiply by 1e6 for display)
        row = 0

        # Dissolution rate constant
        spin = self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.0001, 6)
        self._add_param_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant", spin, "dissolutionRateConst")
        row += 1

        # Early diffusion rate constant
        spin = self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.0001, 6)
        self._add_param_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant", spin, "diffusionRateConstEarly")
        row += 1

        # Late diffusion rate constant
        spin = self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.0001, 6)
        self._add_param_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant", spin, "diffusionRateConstLate")
        row += 1

        # Dissolved units
        spin = self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0)
        self._add_param_row(grid, row, "Diss. units:", "Number of DC units per dissolution event", spin, "dissolvedUnits")
        row += 1

        # siexp
        spin = self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "SI exp:", "Saturation index exponent", spin, "siexp")
        row += 1

        # dfexp
        spin = self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "DF exp:", "Driving force exponent", spin, "dfexp")
        row += 1

        # dorexp
        spin = self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "DOR exp:", "Degree of reaction exponent", spin, "dorexp")
        row += 1

        # ohexp (pozzolanic-specific)
        spin = self._create_spin_button(defaults.ohexp, 0, 5, 0.1, 2)
        self._add_param_row(grid, row, "OH exp:", "Hydroxyl ion activity exponent", spin, "ohexp")
        row += 1

        # sio2 (pozzolanic-specific)
        spin = self._create_spin_button(defaults.sio2, 0, 1, 0.01, 3)
        self._add_param_row(grid, row, "SiO₂:", "SiO₂ content (mass fraction)", spin, "sio2")
        row += 1

        # Activation energy
        spin = self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0)
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy", spin, "activationEnergy")
        row += 1

        # LOI
        spin = self._create_spin_button(defaults.loi, 0, 1, 0.001, 4)
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)", spin, "loi")

    def _on_value_changed(self, spin: Gtk.SpinButton) -> None:
        """Handle parameter value change."""
        self.emit('parameters-changed')

    def get_kinetic_parameters(self) -> Optional[Dict[str, Any]]:
        """
        Get the current kinetic parameters as a dictionary.

        Returns:
            Dictionary with kinetic parameters including 'type' field,
            or None if no kinetic model
        """
        if self.kinetic_type is None:
            return None

        # Rate constant fields displayed in μmol/m²/s, need to convert back to mol/m²/s
        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        params = {'type': self.kinetic_type}
        for key, spin in self.param_widgets.items():
            value = spin.get_value()
            # Convert dissolvedUnits to int
            if key == 'dissolvedUnits':
                value = int(value)
            # Convert rate constants from μmol/m²/s back to mol/m²/s
            elif key in rate_const_fields and self.kinetic_type in ('Standard', 'Pozzolanic'):
                value = value * 1e-6
            params[key] = value

        return params

    def set_kinetic_parameters(self, params: Dict[str, Any]) -> None:
        """
        Set kinetic parameters from a dictionary.

        Args:
            params: Dictionary with kinetic parameters
        """
        # Rate constant fields stored in mol/m²/s, displayed in μmol/m²/s
        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        for key, value in params.items():
            if key in self.param_widgets:
                display_value = float(value)
                # Convert rate constants from mol/m²/s to μmol/m²/s for display
                if key in rate_const_fields and self.kinetic_type in ('Standard', 'Pozzolanic'):
                    display_value = display_value * 1e6
                self.param_widgets[key].set_value(display_value)

    def reset_to_defaults(self) -> None:
        """Reset all parameters to their default values."""
        if not self.phase_name or self.kinetic_type is None:
            return

        defaults = self.kinetic_defaults.get_kinetics_for_phase(self.phase_name)
        if defaults:
            params = defaults.to_dict()
            self.set_kinetic_parameters(params)

    def set_phase(self, phase_name: str) -> None:
        """
        Set the phase and rebuild the editor.

        Args:
            phase_name: GEMS phase name
        """
        self._setup_for_phase(phase_name)

    def set_editable(self, editable: bool) -> None:
        """
        Set whether parameters can be edited.

        Args:
            editable: True to allow editing
        """
        self.editable = editable
        for spin in self.param_widgets.values():
            spin.set_sensitive(editable)


class KineticModelEditorDialog(Gtk.Dialog):
    """
    Dialog for editing kinetic parameters of a phase.

    Allows user to:
    - Choose kinetic model type (Thermodynamic, ParrotKilloh, Standard, Pozzolanic)
    - Edit parameters for the selected type
    - Remove kinetics by selecting "Thermodynamic"
    """

    # Kinetic type options
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
        current_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the dialog.

        Args:
            parent: Parent window
            phase_name: GEMS phase name
            current_params: Current kinetic parameters (or None for defaults)
        """
        super().__init__(
            title=f"Edit Kinetics: {phase_name}",
            transient_for=parent,
            flags=0
        )

        self.phase_name = phase_name
        self.kinetic_defaults = get_kinetic_defaults_service()
        self.current_kinetic_type: Optional[str] = None

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Reset to Defaults", Gtk.ResponseType.REJECT)
        self.add_button("OK", Gtk.ResponseType.OK)

        self.set_default_size(400, 500)

        # Content area
        content = self.get_content_area()
        content.set_margin_start(15)
        content.set_margin_end(15)
        content.set_margin_top(15)
        content.set_margin_bottom(15)
        content.set_spacing(10)

        # Phase name header
        header = Gtk.Label()
        header.set_markup(f"<b>Phase: {phase_name}</b>")
        header.set_halign(Gtk.Align.START)
        content.pack_start(header, False, False, 0)

        # Kinetic type selector
        type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        type_label = Gtk.Label("Kinetic Model:")
        type_label.set_halign(Gtk.Align.START)
        type_box.pack_start(type_label, False, False, 0)

        self.type_combo = Gtk.ComboBoxText()
        for type_name, description in self.KINETIC_TYPES:
            self.type_combo.append(type_name, type_name)
        self.type_combo.connect('changed', self._on_type_changed)
        type_box.pack_start(self.type_combo, True, True, 0)

        content.pack_start(type_box, False, False, 0)

        # Type description
        self.type_description = Gtk.Label()
        self.type_description.set_halign(Gtk.Align.START)
        self.type_description.set_line_wrap(True)
        self.type_description.get_style_context().add_class("dim-label")
        content.pack_start(self.type_description, False, False, 0)

        # Separator
        content.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)

        # Scrolled window for parameters
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        # Parameters container (will be repopulated when type changes)
        self.params_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scrolled.add(self.params_box)
        content.pack_start(scrolled, True, True, 0)

        # Store for parameter widgets
        self.param_widgets: Dict[str, Gtk.SpinButton] = {}

        # Determine initial type
        if current_params and 'type' in current_params:
            initial_type = current_params['type']
        else:
            # Use default type for this phase, or Thermodynamic if none
            initial_type = self.kinetic_defaults.get_kinetic_type(phase_name) or "Thermodynamic"

        # Set initial type (this will populate parameters)
        self.type_combo.set_active_id(initial_type)

        # If we have current params, apply them
        if current_params:
            self._set_parameters(current_params)

        # Connect reset button
        self.connect('response', self._on_response)

        self.show_all()

    def _on_type_changed(self, combo: Gtk.ComboBoxText) -> None:
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
        self._build_parameters_ui(type_id)

    def _build_parameters_ui(self, kinetic_type: str) -> None:
        """Build the parameters UI for the given kinetic type."""
        # Clear existing widgets
        for child in self.params_box.get_children():
            self.params_box.remove(child)
        self.param_widgets.clear()

        if kinetic_type == "Thermodynamic":
            # No parameters needed
            label = Gtk.Label()
            label.set_markup(
                '<span foreground="gray">No kinetic parameters.\n\n'
                'Phase dissolution/precipitation will be controlled\n'
                'purely by thermodynamic equilibrium.</span>'
            )
            label.set_halign(Gtk.Align.CENTER)
            label.set_valign(Gtk.Align.CENTER)
            self.params_box.pack_start(label, True, True, 20)
        else:
            # Get defaults for this type
            defaults = self._get_defaults_for_type(kinetic_type)
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

                self.params_box.pack_start(grid, False, False, 0)

        self.params_box.show_all()

    def _get_defaults_for_type(self, kinetic_type: str) -> Optional[Any]:
        """Get default parameters for a kinetic type."""
        # First try to get defaults for the specific phase
        defaults = self.kinetic_defaults.get_kinetics_for_phase(self.phase_name)
        if defaults and defaults.to_dict().get('type') == kinetic_type:
            return defaults

        # Otherwise use generic defaults for the type
        if kinetic_type == "ParrotKilloh":
            return self.kinetic_defaults.PARROT_KILLOH_DEFAULTS.get("Alite")
        elif kinetic_type == "Standard":
            return self.kinetic_defaults.STANDARD_DEFAULTS.get("Gypsum")
        elif kinetic_type == "Pozzolanic":
            return self.kinetic_defaults.POZZOLANIC_DEFAULTS.get("Quartz")
        return None

    def _create_spin_button(
        self,
        value: float,
        min_val: float,
        max_val: float,
        step: float,
        digits: int
    ) -> Gtk.SpinButton:
        """Create a spin button with specified parameters."""
        spin = Gtk.SpinButton.new_with_range(min_val, max_val, step)
        spin.set_digits(digits)
        spin.set_width_chars(12)
        spin.set_value(value)
        return spin

    def _add_param_row(
        self,
        grid: Gtk.Grid,
        row: int,
        label_text: str,
        tooltip: str,
        spin: Gtk.SpinButton,
        param_key: str
    ) -> None:
        """Add a parameter row to the grid."""
        label = Gtk.Label(label_text)
        label.set_halign(Gtk.Align.END)
        label.set_tooltip_text(tooltip)
        grid.attach(label, 0, row, 1, 1)

        spin.set_tooltip_text(tooltip)
        grid.attach(spin, 1, row, 1, 1)

        self.param_widgets[param_key] = spin

    def _create_parrot_killoh_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create fields for Parrot-Killoh kinetics."""
        row = 0
        self._add_param_row(grid, row, "k1:", "Nucleation/growth rate constant",
                           self._create_spin_button(defaults.k1, 0, 10, 0.01, 3), "k1")
        row += 1
        self._add_param_row(grid, row, "k2:", "Early diffusion rate constant",
                           self._create_spin_button(defaults.k2, 0, 1, 0.001, 4), "k2")
        row += 1
        self._add_param_row(grid, row, "k3:", "Late diffusion rate constant",
                           self._create_spin_button(defaults.k3, 0, 10, 0.01, 3), "k3")
        row += 1
        self._add_param_row(grid, row, "n1:", "Nucleation/growth exponent",
                           self._create_spin_button(defaults.n1, 0, 5, 0.01, 3), "n1")
        row += 1
        self._add_param_row(grid, row, "n3:", "Late diffusion exponent",
                           self._create_spin_button(defaults.n3, 0, 10, 0.1, 2), "n3")
        row += 1
        self._add_param_row(grid, row, "dorHcoeff:", "Lothenbach-Kulik H coefficient",
                           self._create_spin_button(defaults.dorHcoeff, 0, 5, 0.01, 3), "dorHcoeff")
        row += 1
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy",
                           self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)",
                           self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _create_standard_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create fields for Standard kinetics."""
        # Rate constants displayed in μmol/m²/s (multiply by 1e6 for display)
        row = 0
        self._add_param_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant",
                           self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.1, 4), "dissolutionRateConst")
        row += 1
        self._add_param_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant",
                           self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.1, 4), "diffusionRateConstEarly")
        row += 1
        self._add_param_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant",
                           self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.1, 4), "diffusionRateConstLate")
        row += 1
        self._add_param_row(grid, row, "Diss. units:", "Number of DC units per dissolution event",
                           self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0), "dissolvedUnits")
        row += 1
        self._add_param_row(grid, row, "SI exp:", "Saturation index exponent",
                           self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2), "siexp")
        row += 1
        self._add_param_row(grid, row, "DF exp:", "Driving force exponent",
                           self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2), "dfexp")
        row += 1
        self._add_param_row(grid, row, "DOR exp:", "Degree of reaction exponent",
                           self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2), "dorexp")
        row += 1
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy",
                           self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)",
                           self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _create_pozzolanic_fields(self, grid: Gtk.Grid, defaults) -> None:
        """Create fields for Pozzolanic kinetics."""
        # Rate constants displayed in μmol/m²/s (multiply by 1e6 for display)
        row = 0
        self._add_param_row(grid, row, "Diss. rate (μmol/m²/s):", "Dissolution rate constant",
                           self._create_spin_button(defaults.dissolutionRateConst * 1e6, 0, 1000, 0.0001, 6), "dissolutionRateConst")
        row += 1
        self._add_param_row(grid, row, "Diff. early (μmol/m²/s):", "Early diffusion rate constant",
                           self._create_spin_button(defaults.diffusionRateConstEarly * 1e6, 0, 1000, 0.0001, 6), "diffusionRateConstEarly")
        row += 1
        self._add_param_row(grid, row, "Diff. late (μmol/m²/s):", "Late diffusion rate constant",
                           self._create_spin_button(defaults.diffusionRateConstLate * 1e6, 0, 1000, 0.0001, 6), "diffusionRateConstLate")
        row += 1
        self._add_param_row(grid, row, "Diss. units:", "Number of DC units per dissolution event",
                           self._create_spin_button(defaults.dissolvedUnits, 1, 20, 1, 0), "dissolvedUnits")
        row += 1
        self._add_param_row(grid, row, "SI exp:", "Saturation index exponent",
                           self._create_spin_button(defaults.siexp, 0, 5, 0.1, 2), "siexp")
        row += 1
        self._add_param_row(grid, row, "DF exp:", "Driving force exponent",
                           self._create_spin_button(defaults.dfexp, 0, 5, 0.1, 2), "dfexp")
        row += 1
        self._add_param_row(grid, row, "DOR exp:", "Degree of reaction exponent",
                           self._create_spin_button(defaults.dorexp, 0, 5, 0.1, 2), "dorexp")
        row += 1
        self._add_param_row(grid, row, "OH exp:", "Hydroxyl ion activity exponent",
                           self._create_spin_button(defaults.ohexp, 0, 5, 0.1, 2), "ohexp")
        row += 1
        self._add_param_row(grid, row, "SiO₂:", "SiO₂ content (mass fraction)",
                           self._create_spin_button(defaults.sio2, 0, 1, 0.01, 3), "sio2")
        row += 1
        self._add_param_row(grid, row, "Ea (J/mol):", "Activation energy",
                           self._create_spin_button(defaults.activationEnergy, 0, 100000, 100, 0), "activationEnergy")
        row += 1
        self._add_param_row(grid, row, "LOI:", "Loss on ignition (mass fraction)",
                           self._create_spin_button(defaults.loi, 0, 1, 0.001, 4), "loi")

    def _set_parameters(self, params: Dict[str, Any]) -> None:
        """Set parameter values from a dictionary."""
        # Rate constant fields stored in mol/m²/s, displayed in μmol/m²/s
        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        for key, value in params.items():
            if key in self.param_widgets:
                display_value = float(value)
                # Convert rate constants from mol/m²/s to μmol/m²/s for display
                if key in rate_const_fields and self.current_kinetic_type in ('Standard', 'Pozzolanic'):
                    display_value = display_value * 1e6
                self.param_widgets[key].set_value(display_value)

    def _on_response(self, dialog: Gtk.Dialog, response_id: int) -> None:
        """Handle dialog response."""
        if response_id == Gtk.ResponseType.REJECT:
            # Reset to defaults for this phase
            default_type = self.kinetic_defaults.get_kinetic_type(self.phase_name) or "Thermodynamic"

            # Force rebuild by clearing current type first
            self.current_kinetic_type = None
            self.type_combo.set_active_id(default_type)

            # If type combo didn't trigger rebuild (same type), force it
            if self.current_kinetic_type != default_type:
                self.current_kinetic_type = default_type
                self._build_parameters_ui(default_type)

            # Don't close the dialog
            self.stop_emission_by_name('response')

    def get_kinetic_parameters(self) -> Optional[Dict[str, Any]]:
        """
        Get the edited kinetic parameters.

        Returns:
            Dictionary with kinetic parameters including 'type' field,
            or None if "Thermodynamic" (no kinetics) is selected
        """
        if self.current_kinetic_type == "Thermodynamic":
            return None

        # Rate constant fields displayed in μmol/m²/s, need to convert back to mol/m²/s
        rate_const_fields = {'dissolutionRateConst', 'diffusionRateConstEarly', 'diffusionRateConstLate'}

        params = {'type': self.current_kinetic_type}
        for key, spin in self.param_widgets.items():
            value = spin.get_value()
            # Convert dissolvedUnits to int
            if key == 'dissolvedUnits':
                value = int(value)
            # Convert rate constants from μmol/m²/s back to mol/m²/s
            elif key in rate_const_fields and self.current_kinetic_type in ('Standard', 'Pozzolanic'):
                value = value * 1e-6
            params[key] = value

        return params


# Register signals
GObject.type_register(KineticModelEditor)

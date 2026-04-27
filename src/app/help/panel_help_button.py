#!/usr/bin/env python3
"""
Panel Help Button

Reusable help button widget that opens context-specific documentation for each panel.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from typing import Optional
import logging

from app.utils.icon_utils import create_icon_image
from app.help.documentation_viewer import get_documentation_viewer

logger = logging.getLogger(__name__)


# Mapping of panel class names to USER_MANUAL.md section anchor slugs.
# The slugs match the heading IDs the Python-Markdown TOC extension generates
# from the corresponding "## N. Heading" lines in docs/USER_MANUAL.md (see
# documentation_viewer._render_manual_html). Keep this map in sync with the
# manual's section numbering. Previously these were defunct MkDocs URLs
# (`user-guide/.../index.html`) that the rewritten viewer's legacy
# `open_documentation` alias silently routed back to the top of the manual,
# which is why every panel's info icon looked broken.
PANEL_DOCUMENTATION_MAP = {
    'MaterialsPanel':            '4-materials-management',
    'MixDesignPanel':            '5-mix-design',
    'MicrostructurePanel':       '5-mix-design',          # Microstructure is part of mix design
    'HydrationPanel':            '6-hydration-simulation',
    'THAMESHydrationPanel':      '6-hydration-simulation',  # Active panel class on Hydration page
    'ElasticModuliPanel':        '7-elastic-properties',
    'ResultsPanel':              '9-results-analysis',
    'OperationsMonitoringPanel': '8-operations-monitoring',
    'FileManagementPanel':       '2-getting-started',     # File management covered in getting started
    'AggregatePanel':            '4-materials-management', # Aggregates part of materials
}


def create_panel_help_button(panel_name: str, parent_window: Optional[Gtk.Window] = None) -> Gtk.Button:
    """
    Create a context-specific help button for a panel.

    Args:
        panel_name: Name of the panel class (e.g., 'MaterialsPanel')
        parent_window: Parent window for error dialogs

    Returns:
        Configured help button
    """
    button = Gtk.Button()
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.set_can_focus(False)

    # Create help icon
    help_icon = create_icon_image("help-about", 16)
    button.set_image(help_icon)

    # Set tooltip
    panel_display_name = _get_panel_display_name(panel_name)
    button.set_tooltip_text(f"Open {panel_display_name} documentation")

    # Connect click handler
    button.connect('clicked', lambda w: _on_help_button_clicked(panel_name, parent_window))

    # Add CSS class for styling
    button.get_style_context().add_class('panel-help-button')

    return button


def _get_panel_display_name(panel_name: str) -> str:
    """
    Get user-friendly display name for a panel.

    Args:
        panel_name: Panel class name

    Returns:
        Display name for UI
    """
    display_names = {
        'MaterialsPanel': 'Materials Management',
        'MixDesignPanel': 'Mix Design',
        'MicrostructurePanel': 'Microstructure Generation',
        'HydrationPanel': 'Hydration Simulation',
        'THAMESHydrationPanel': 'Hydration Simulation',
        'ElasticModuliPanel': 'Elastic Calculations',
        'ResultsPanel': 'Results Visualization',
        'OperationsMonitoringPanel': 'Operations Monitoring',
        'FileManagementPanel': 'File Management',
        'AggregatePanel': 'Aggregate Management',
    }

    return display_names.get(panel_name, panel_name.replace('Panel', ''))


def _on_help_button_clicked(panel_name: str, parent_window: Optional[Gtk.Window]):
    """
    Handle help button click - open the User Manual at this panel's section.

    Args:
        panel_name: Panel class name
        parent_window: Parent window for error dialogs
    """
    anchor = PANEL_DOCUMENTATION_MAP.get(panel_name)
    doc_viewer = get_documentation_viewer()

    if anchor:
        # Route through open_section so the rendered manual scrolls to the
        # right heading. (Going through open_documentation discards the
        # target and lands at the top of the manual.)
        doc_viewer.open_section(anchor, parent_window)
        logger.info(f"Opened User Manual section '{anchor}' for {panel_name}")
    else:
        logger.warning(f"No User Manual section mapped for panel: {panel_name}; opening manual at top")
        doc_viewer.open_user_guide(parent_window=parent_window)


def get_panel_documentation_url(panel_name: str) -> Optional[str]:
    """
    Get documentation URL for a specific panel.

    Args:
        panel_name: Panel class name

    Returns:
        Documentation URL or None if not found
    """
    return PANEL_DOCUMENTATION_MAP.get(panel_name)


def add_help_button_to_header(title_box: Gtk.Box, panel_name: str, parent_window: Optional[Gtk.Window] = None):
    """
    Convenience function to add help button to a panel's title box.

    Args:
        title_box: The horizontal box containing the panel title
        panel_name: Panel class name
        parent_window: Parent window for error dialogs
    """
    help_button = create_panel_help_button(panel_name, parent_window)
    title_box.pack_end(help_button, False, False, 0)
    logger.debug(f"Added help button to {panel_name} header")

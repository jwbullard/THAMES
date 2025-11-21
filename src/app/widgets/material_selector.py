#!/usr/bin/env python3
"""
Material Selector Widget for THAMES

Autocomplete entry widget for selecting materials from the THAMES database.
Supports tag-based filtering and type-ahead search.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import logging
from typing import Optional, List, Dict, Any

from app.services.material_service import MaterialService


class MaterialSelector(Gtk.Box):
    """
    Autocomplete entry widget for selecting THAMES materials.

    Features:
    - Autocomplete suggestions from materials database
    - Case-insensitive filtering
    - Optional tag-based filtering dropdown
    - Shows material count and specific gravity
    """

    __gsignals__ = {
        'material-selected': (GObject.SignalFlags.RUN_FIRST, None, (int, str, float)),
        'material-cleared': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, material_service: MaterialService,
                 show_tag_filter: bool = True,
                 placeholder: str = "Type to search materials..."):
        """
        Initialize the material selector.

        Args:
            material_service: MaterialService instance
            show_tag_filter: Whether to show the tag filter dropdown
            placeholder: Placeholder text for the entry
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.material_service = material_service
        self.show_tag_filter = show_tag_filter
        self.logger = logging.getLogger('THAMES.MaterialSelector')

        # Cache all materials and tags
        self._all_materials: List[Any] = []
        self._filtered_materials: List[Any] = []
        self._all_tags: List[str] = []
        self._selected_material_id: Optional[int] = None

        # Load data
        self._load_data()

        # Build UI
        self._build_ui(placeholder)

    def _load_data(self):
        """Load materials and tags from database."""
        try:
            self._all_materials = self.material_service.get_all()
            self._filtered_materials = self._all_materials.copy()
            # get_all_tags() returns List[str] directly, not Tag objects
            self._all_tags = self.material_service.get_all_tags()
            self.logger.info(f"Loaded {len(self._all_materials)} materials and {len(self._all_tags)} tags")
        except Exception as e:
            self.logger.error(f"Failed to load materials: {e}")
            self._all_materials = []
            self._filtered_materials = []
            self._all_tags = []

    def _build_ui(self, placeholder: str):
        """Build the selector UI."""
        # Tag filter dropdown (optional)
        if self.show_tag_filter:
            self.tag_combo = Gtk.ComboBoxText()
            self.tag_combo.set_size_request(100, -1)
            self.tag_combo.append("", "All")
            for tag in sorted(self._all_tags):
                self.tag_combo.append(tag, tag.title())
            self.tag_combo.set_active(0)
            self.tag_combo.set_tooltip_text("Filter by tag")
            self.tag_combo.connect('changed', self._on_tag_filter_changed)
            self.pack_start(self.tag_combo, False, False, 0)

        # Entry with completion
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(placeholder)
        self.entry.set_size_request(200, -1)
        self.entry.connect('changed', self._on_entry_changed)
        self.entry.connect('activate', self._on_entry_activated)
        self.entry.connect('focus-out-event', self._on_focus_out)

        # Setup autocomplete
        self.completion = Gtk.EntryCompletion()
        self.entry.set_completion(self.completion)

        # Create list store for completion (id, name, sg)
        self.completion_store = Gtk.ListStore(int, str, float)
        self._populate_completion_store()

        self.completion.set_model(self.completion_store)
        self.completion.set_text_column(1)  # Display name column
        self.completion.set_inline_completion(True)
        self.completion.set_popup_completion(True)
        self.completion.set_match_func(self._match_func)
        self.completion.connect('match-selected', self._on_match_selected)

        self.pack_start(self.entry, True, True, 0)

        # SG display label
        self.sg_label = Gtk.Label("SG: --")
        self.sg_label.set_size_request(80, -1)
        self.sg_label.get_style_context().add_class("dim-label")
        self.sg_label.set_tooltip_text("Specific Gravity")
        self.pack_start(self.sg_label, False, False, 0)

    def _populate_completion_store(self):
        """Populate the completion store with filtered materials."""
        self.completion_store.clear()
        for material in sorted(self._filtered_materials, key=lambda m: m.name.lower()):
            sg = material.specific_gravity or 0.0
            self.completion_store.append([material.id, material.name, sg])

    def _on_tag_filter_changed(self, combo):
        """Handle tag filter change."""
        tag = combo.get_active_id()

        if tag:
            # Filter materials by tag
            self._filtered_materials = [
                m for m in self._all_materials
                if any(t.name == tag for t in m.tags)
            ]
        else:
            # Show all materials
            self._filtered_materials = self._all_materials.copy()

        # Update completion store
        self._populate_completion_store()

        # Clear current selection if it's no longer in filtered list
        current_text = self.entry.get_text()
        if current_text and not any(m.name == current_text for m in self._filtered_materials):
            self.entry.set_text("")
            self._selected_material_id = None
            self.sg_label.set_text("SG: --")
            self.emit('material-cleared')

        self.logger.debug(f"Tag filter '{tag}': {len(self._filtered_materials)} materials")

    def _match_func(self, completion, key, iter):
        """
        Custom match function for case-insensitive matching.

        Args:
            completion: The EntryCompletion
            key: The text to match
            iter: TreeIter pointing to row in model

        Returns:
            True if row matches, False otherwise
        """
        model = completion.get_model()
        material_name = model[iter][1]

        # Case-insensitive substring match
        return key.lower() in material_name.lower()

    def _on_entry_changed(self, entry):
        """Handle entry text changes."""
        text = entry.get_text().strip()

        # Check if text exactly matches a material
        matching_material = None
        for material in self._filtered_materials:
            if material.name == text:
                matching_material = material
                break

        if matching_material:
            self._select_material(matching_material)
        else:
            # Clear selection if text doesn't match
            if self._selected_material_id is not None:
                self._selected_material_id = None
                self.sg_label.set_text("SG: --")

    def _on_entry_activated(self, entry):
        """Handle Enter key in entry."""
        text = entry.get_text().strip()

        # Find exact match
        for material in self._filtered_materials:
            if material.name.lower() == text.lower():
                self._select_material(material)
                # Fix case if needed
                if material.name != text:
                    entry.set_text(material.name)
                return

        self.logger.warning(f"No matching material: {text}")

    def _on_focus_out(self, entry, event):
        """Handle focus out - validate selection."""
        text = entry.get_text().strip()

        if text:
            # Try to find a match
            for material in self._filtered_materials:
                if material.name.lower() == text.lower():
                    entry.set_text(material.name)
                    self._select_material(material)
                    return False

            # No match - clear
            entry.set_text("")
            self._selected_material_id = None
            self.sg_label.set_text("SG: --")
            self.emit('material-cleared')

        return False

    def _on_match_selected(self, completion, model, iter):
        """Handle selection from completion popup."""
        material_id = model[iter][0]
        material_name = model[iter][1]
        sg = model[iter][2]

        self._selected_material_id = material_id
        self.sg_label.set_text(f"SG: {sg:.3f}" if sg else "SG: --")
        self.emit('material-selected', material_id, material_name, sg)
        return True

    def _select_material(self, material):
        """Select a material and update UI."""
        self._selected_material_id = material.id
        sg = material.specific_gravity or 0.0
        self.sg_label.set_text(f"SG: {sg:.3f}" if sg else "SG: --")
        self.emit('material-selected', material.id, material.name, sg)

    def get_selected_material_id(self) -> Optional[int]:
        """Get the currently selected material ID."""
        return self._selected_material_id

    def get_selected_material_name(self) -> Optional[str]:
        """Get the currently selected material name."""
        if self._selected_material_id:
            return self.entry.get_text().strip()
        return None

    def set_material_by_id(self, material_id: int):
        """Set the selector to a specific material by ID."""
        for material in self._all_materials:
            if material.id == material_id:
                self.entry.set_text(material.name)
                self._select_material(material)

                # Update tag filter if needed
                if self.show_tag_filter and material.tags:
                    # Set filter to first tag
                    tag = material.tags[0].name
                    model = self.tag_combo.get_model()
                    for i, row in enumerate(model):
                        if row[0] == tag:
                            self.tag_combo.set_active(i)
                            break
                return

        self.logger.warning(f"Material ID {material_id} not found")

    def set_material_by_name(self, material_name: str):
        """Set the selector to a specific material by name."""
        for material in self._all_materials:
            if material.name == material_name:
                self.entry.set_text(material.name)
                self._select_material(material)
                return

        self.logger.warning(f"Material '{material_name}' not found")

    def clear(self):
        """Clear the selector."""
        self.entry.set_text("")
        self._selected_material_id = None
        self.sg_label.set_text("SG: --")
        if self.show_tag_filter:
            self.tag_combo.set_active(0)
        self.emit('material-cleared')

    def refresh(self):
        """Refresh the material list from database."""
        self._load_data()
        self._populate_completion_store()


# Register the signal
GObject.type_register(MaterialSelector)

#!/usr/bin/env python3
"""
Tag Chip Input Widget for THAMES

Simple widget for entering and displaying tags as chips.
Phase 1: Basic text entry with chip display.
"""

import gi
from typing import List, Callable, Optional

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk


class TagChipInput(Gtk.Box):
    """Widget for entering tags as chips."""

    def __init__(self, on_changed: Optional[Callable[[], None]] = None):
        """
        Initialize the tag chip input.

        Args:
            on_changed: Callback when tags change
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        self.tags: List[str] = []
        self.on_changed_callback = on_changed

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the UI."""
        # Chips display area
        self.chips_box = Gtk.FlowBox()
        self.chips_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.chips_box.set_homogeneous(False)
        self.chips_box.set_column_spacing(5)
        self.chips_box.set_row_spacing(5)
        self.chips_box.set_margin_start(5)
        self.chips_box.set_margin_end(5)
        self.chips_box.set_margin_top(5)
        self.chips_box.set_margin_bottom(5)

        # Scrolled window for chips
        chips_scrolled = Gtk.ScrolledWindow()
        chips_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        chips_scrolled.set_size_request(-1, 80)
        chips_scrolled.add(self.chips_box)

        self.pack_start(chips_scrolled, True, True, 0)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)

        self.tag_entry = Gtk.Entry()
        self.tag_entry.set_placeholder_text('Enter tag and press Enter...')
        self.tag_entry.connect('activate', self._on_entry_activate)
        self.tag_entry.connect('key-press-event', self._on_entry_key_press)
        input_box.pack_start(self.tag_entry, True, True, 0)

        add_button = Gtk.Button.new_with_label('Add Tag')
        add_button.connect('clicked', self._on_add_button_clicked)
        input_box.pack_start(add_button, False, False, 0)

        self.pack_start(input_box, False, False, 0)

    def _create_chip(self, tag: str) -> Gtk.Box:
        """
        Create a chip widget for a tag.

        Args:
            tag: The tag text

        Returns:
            Chip widget
        """
        chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        chip_box.get_style_context().add_class('tag-chip')
        chip_box.set_margin_start(2)
        chip_box.set_margin_end(2)
        chip_box.set_margin_top(2)
        chip_box.set_margin_bottom(2)

        # Tag label
        tag_label = Gtk.Label(tag)
        tag_label.set_margin_start(8)
        tag_label.set_margin_end(3)
        tag_label.set_margin_top(4)
        tag_label.set_margin_bottom(4)
        chip_box.pack_start(tag_label, False, False, 0)

        # Remove button
        remove_button = Gtk.Button.new_from_icon_name('window-close-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
        remove_button.set_relief(Gtk.ReliefStyle.NONE)
        remove_button.set_margin_end(4)
        remove_button.set_tooltip_text(f'Remove tag "{tag}"')
        remove_button.connect('clicked', lambda btn: self._remove_tag(tag))
        chip_box.pack_start(remove_button, False, False, 0)

        chip_box.show_all()
        return chip_box

    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        """Handle Enter key in entry."""
        self._add_tag_from_entry()

    def _on_entry_key_press(self, entry: Gtk.Entry, event: Gdk.EventKey) -> bool:
        """Handle key press in entry."""
        # Handle comma as tag separator
        if event.keyval == Gdk.KEY_comma:
            self._add_tag_from_entry()
            return True  # Stop propagation
        return False

    def _on_add_button_clicked(self, button: Gtk.Button) -> None:
        """Handle add button clicked."""
        self._add_tag_from_entry()

    def _add_tag_from_entry(self) -> None:
        """Add tag from entry field."""
        tag_text = self.tag_entry.get_text().strip()

        if not tag_text:
            return

        # Remove trailing comma if present
        if tag_text.endswith(','):
            tag_text = tag_text[:-1].strip()

        if not tag_text:
            return

        # Convert to lowercase and validate
        tag_text = tag_text.lower()

        # Check for duplicates
        if tag_text in self.tags:
            # Show brief error feedback
            self.tag_entry.get_style_context().add_class('error')
            return

        # Add tag
        self.add_tag(tag_text)

        # Clear entry
        self.tag_entry.set_text('')
        self.tag_entry.get_style_context().remove_class('error')

    def add_tag(self, tag: str) -> None:
        """
        Add a tag programmatically.

        Args:
            tag: Tag to add
        """
        if tag and tag not in self.tags:
            self.tags.append(tag)
            chip = self._create_chip(tag)
            self.chips_box.add(chip)
            self._notify_changed()

    def _remove_tag(self, tag: str) -> None:
        """
        Remove a tag.

        Args:
            tag: Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)

            # Remove chip from display
            for child in self.chips_box.get_children():
                # Get the label from the chip box
                label = child.get_child().get_children()[0]
                if isinstance(label, Gtk.Label) and label.get_text() == tag:
                    self.chips_box.remove(child)
                    break

            self._notify_changed()

    def get_tags(self) -> List[str]:
        """
        Get the current list of tags.

        Returns:
            List of tags
        """
        return self.tags.copy()

    def set_tags(self, tags: List[str]) -> None:
        """
        Set the tags (replaces current tags).

        Args:
            tags: List of tags to set
        """
        # Clear existing
        self.clear()

        # Add new tags
        for tag in tags:
            self.add_tag(tag)

    def clear(self) -> None:
        """Clear all tags."""
        self.tags.clear()

        # Remove all chips
        for child in list(self.chips_box.get_children()):
            self.chips_box.remove(child)

        self._notify_changed()

    def _notify_changed(self) -> None:
        """Notify that tags have changed."""
        if self.on_changed_callback:
            self.on_changed_callback()

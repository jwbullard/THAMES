"""
App-wide guard against scroll-wheel edits of value widgets.

GTK3 spin buttons and combo boxes change their value when the pointer
rests on them and the user scrolls, even without a click. Scrolling a page
that holds such fields silently edits inputs (seen with Parrot-Killoh k2:
0.0500 -> 0.0480 while scrolling past the Edit Kinetics dialog; also
reported by a user).

`install()` replaces GDK's event handler once at startup. A scroll event
whose target is, or sits inside, a Gtk.SpinButton or Gtk.ComboBox is sent
to the nearest Gtk.ScrolledWindow ancestor instead, so the page scrolls and
the value does not change. With no scrolled ancestor the event is dropped.
Every other event goes to GTK unchanged. This covers every panel, dialog,
tree-view cell editor and widget added later without per-widget code.
Values still change by typing, the arrow buttons, the arrow keys, or the
drop-down menu.
"""

import logging

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

_GUARDED = (Gtk.SpinButton, Gtk.ComboBox)
_installed = False


def _guarded_ancestor(widget):
    """Return the first SpinButton/ComboBox at or above `widget`, else None."""
    while widget is not None:
        if isinstance(widget, _GUARDED):
            return widget
        widget = widget.get_parent()
    return None


def _scrolled_ancestor(widget):
    """Return the nearest Gtk.ScrolledWindow above `widget`, else None."""
    widget = widget.get_parent()
    while widget is not None:
        if isinstance(widget, Gtk.ScrolledWindow):
            return widget
        widget = widget.get_parent()
    return None


def _handle_event(event, _data=None):
    if event.type == Gdk.EventType.SCROLL:
        target = Gtk.get_event_widget(event)
        guarded = _guarded_ancestor(target) if target is not None else None
        if guarded is not None:
            scroller = _scrolled_ancestor(guarded)
            if scroller is not None:
                Gtk.propagate_event(scroller, event)
            return
    Gtk.main_do_event(event)


def install() -> None:
    """Install the guard. Call once, after GTK is initialized; idempotent."""
    global _installed
    if _installed:
        return
    Gdk.event_handler_set(_handle_event, None)
    _installed = True
    logging.getLogger('THAMES.ScrollGuard').info(
        "Scroll guard installed: spin buttons and combo boxes ignore the scroll wheel")

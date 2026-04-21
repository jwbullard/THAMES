#!/usr/bin/env python3
"""
Documentation Viewer

Renders ``docs/USER_MANUAL.md`` to a single-file HTML document and opens it in
the user's default web browser. The HTML is cached in a temporary file and
regenerated whenever the source markdown changes, so internal TOC links use
browser-generated anchors that actually work (the previous implementation
shelled out to whatever external app was registered for .md files, where
anchor support varied wildly by viewer).

Falls back to an error dialog if the manual file is missing.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from pathlib import Path
import logging
import tempfile
import webbrowser
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Minimal CSS applied to the rendered manual so it reads well in a plain
# browser. Deliberately narrow in scope — we don't want to reinvent a docs
# site, just make the single-file output legible.
_MANUAL_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 900px; margin: 2em auto; padding: 0 1.5em; line-height: 1.55;
       color: #222; background: #fafafa; }
h1, h2, h3, h4 { color: #1a1a1a; margin-top: 1.6em; margin-bottom: 0.4em; }
h1 { border-bottom: 2px solid #2E7D32; padding-bottom: 0.25em; }
h2 { border-bottom: 1px solid #bbb; padding-bottom: 0.2em; }
code { background: #eee; padding: 0.1em 0.3em; border-radius: 3px;
       font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 0.92em; }
pre { background: #f4f4f4; padding: 0.8em; border-radius: 4px; overflow-x: auto;
      border: 1px solid #ddd; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; margin: 1em 0; width: 100%; }
th, td { border: 1px solid #bbb; padding: 0.4em 0.7em; text-align: left; }
th { background: #e8f0e8; }
a { color: #1565C0; text-decoration: none; }
a:hover { text-decoration: underline; }
blockquote { border-left: 4px solid #ccc; margin: 1em 0; padding: 0.2em 1em;
             color: #555; background: #f0f0f0; }
img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 3px;
      margin: 0.5em 0; }
/* Anchor target offset so clicks from the TOC don't bury the heading under
   the top of the browser viewport */
h1[id], h2[id], h3[id], h4[id] { scroll-margin-top: 1em; }
"""


class DocumentationViewer:
    """Renders and displays the THAMES User Manual in the default browser."""

    def __init__(self, docs_path: Optional[Path] = None):
        """
        Args:
            docs_path: Path to the directory containing USER_MANUAL.md and
                the ``images/`` subfolder. If None, searches standard
                locations.
        """
        self.docs_path = docs_path
        if self.docs_path is None:
            self.docs_path = self._find_documentation()

        # Cached state for rendering. We keep one HTML file per target
        # section (keyed by anchor slug, or None for "top of document"),
        # because URL fragments are unreliable through the macOS
        # osascript -> browser pipeline. Instead, each target gets its own
        # rendered file with the destination baked in as a JavaScript
        # constant; the URL passed to the browser has no hash.
        self._cached_html_paths: Dict[str, Path] = {}
        self._cached_md_mtime: Optional[float] = None

    # ------------------------------------------------------------------
    # Documentation location
    # ------------------------------------------------------------------

    def _find_documentation(self) -> Optional[Path]:
        """Find the docs directory in standard locations."""
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        docs_dir = project_root / "docs"
        if docs_dir.exists() and docs_dir.is_dir():
            logger.info(f"Found documentation at: {docs_dir}")
            return docs_dir

        # Packaged (PyInstaller) location
        import sys
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys._MEIPASS)
            packaged_docs = bundle_dir / "docs"
            if packaged_docs.exists():
                logger.info(f"Found packaged documentation at: {packaged_docs}")
                return packaged_docs

        logger.warning("Documentation not found in standard locations")
        return None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_manual_html(self, target_section: Optional[str] = None) -> Optional[Path]:
        """Convert USER_MANUAL.md to a cached HTML file and return its path.

        Each distinct ``target_section`` gets its own cached file with the
        anchor slug baked into a JavaScript constant. On load, a small script
        scrolls to that element. This avoids URL fragments, which are
        unreliably handled by the macOS osascript -> browser pipeline.

        Regenerates only when the source markdown has changed since the last
        render. Returns None if the manual is missing or the markdown
        library is unavailable.
        """
        if self.docs_path is None or not self.docs_path.exists():
            logger.warning("No docs_path; cannot render manual")
            return None
        manual_md = self.docs_path / "USER_MANUAL.md"
        if not manual_md.exists():
            logger.warning(f"USER_MANUAL.md not found at {manual_md}")
            return None

        try:
            import markdown
        except ImportError:
            logger.error(
                "Python markdown package is not installed. "
                "Install it via: pip install 'markdown>=3.4.0'"
            )
            return None

        cache_key = target_section or ""
        current_mtime = manual_md.stat().st_mtime
        cached = self._cached_html_paths.get(cache_key)
        if (cached is not None
                and cached.exists()
                and self._cached_md_mtime == current_mtime):
            return cached

        # Read source
        md_text = manual_md.read_text(encoding="utf-8")

        # The `toc` extension generates id="..." attributes on headings whose
        # slugs match GitHub's convention (lowercase, spaces->dashes, strip
        # punctuation), which is what the manual's TOC links already assume.
        # `tables` and `fenced_code` handle the pipe tables and ```...```
        # blocks used throughout the manual.
        html_body = markdown.markdown(
            md_text,
            extensions=["toc", "tables", "fenced_code"],
            output_format="html5",
        )

        # Rewrite relative image references (src="images/...") to absolute
        # file:// URIs so they load from the docs/images directory regardless
        # of where the rendered HTML is stored. Deliberately avoid a <base>
        # tag here — that would also rebase the manual's fragment-only TOC
        # links (href="#..."), turning them into docs/#... and sending the
        # browser to a directory listing instead of scrolling within the page.
        import re
        images_uri = (self.docs_path / "images").as_uri().rstrip("/") + "/"
        html_body = re.sub(
            r'(<img[^>]*\ssrc=["\'])images/',
            r'\1' + images_uri,
            html_body,
        )

        # The target anchor is baked into the HTML as a JS constant rather
        # than passed through a URL fragment. Rationale: on macOS the
        # webbrowser -> osascript -> browser path is inconsistent with
        # fragment preservation (some combinations strip the hash; others
        # let the browser's scroll-restoration override the hash jump).
        # A baked-in constant is fully under our control and survives any
        # URL-handoff quirks.
        import json as _json
        target_js_literal = _json.dumps(target_section) if target_section else "null"
        boot_script = (
            "<script>"
            f"window.__THAMES_TARGET_SECTION={target_js_literal};"
            "(function(){"
            "if(window.history&&'scrollRestoration' in window.history){"
            "window.history.scrollRestoration='manual';"
            "}"
            "function jumpToTarget(){"
            "var t=window.__THAMES_TARGET_SECTION;"
            "if(!t) return;"
            "var el=document.getElementById(t);"
            "if(el){el.scrollIntoView({block:'start'});}"
            "}"
            "if(document.readyState==='complete'||document.readyState==='interactive'){"
            "setTimeout(jumpToTarget,0);"
            "}else{"
            "document.addEventListener('DOMContentLoaded',function(){setTimeout(jumpToTarget,0);});"
            "}"
            "window.addEventListener('load',function(){setTimeout(jumpToTarget,0);});"
            "})();"
            "</script>"
        )

        html_doc = (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "<meta charset=\"utf-8\">\n"
            "<title>THAMES User Manual</title>\n"
            f"<style>{_MANUAL_CSS}</style>\n"
            f"{boot_script}\n"
            "</head>\n"
            "<body>\n"
            f"{html_body}\n"
            "</body>\n"
            "</html>\n"
        )

        # Write to a stable per-process, per-section temp file so repeat
        # opens don't leak new files and the browser can keep the tab open.
        if cached is None:
            suffix_hint = f"_{cache_key}" if cache_key else ""
            fd, path_str = tempfile.mkstemp(
                prefix=f"thames_user_manual{suffix_hint}_", suffix=".html"
            )
            import os as _os
            _os.close(fd)
            cached = Path(path_str)
            self._cached_html_paths[cache_key] = cached

        cached.write_text(html_doc, encoding="utf-8")
        self._cached_md_mtime = current_mtime
        logger.info(
            f"Rendered user manual to {cached}"
            f"{' (target=' + cache_key + ')' if cache_key else ''}"
        )
        return cached

    # ------------------------------------------------------------------
    # Public API used by the Help menu
    # ------------------------------------------------------------------

    def open_user_guide(self, section: str = None, parent_window: Optional[Gtk.Window] = None):
        """Open the full THAMES User Manual in the default browser.

        Args:
            section: Optional anchor (e.g., ``"7-elastic-properties"``)
                to jump to a specific section. Pass the slug matching the
                heading's ``id``. If None, opens at the top.
            parent_window: Parent window for error dialogs.
        """
        html_path = self._render_manual_html(target_section=section)
        if html_path is None:
            self._show_documentation_not_found_dialog(parent_window)
            return

        # No URL fragment — the target section is baked into the rendered
        # HTML as a JS constant and handled by an in-page script.
        self._open_in_browser(html_path.as_uri(), parent_window)

    def open_getting_started(self, parent_window: Optional[Gtk.Window] = None):
        """Open the Getting Started section of the User Manual."""
        # The TOC links to ``#2-getting-started`` and the `toc` extension
        # generates the matching id on the ``## 2. Getting Started`` heading.
        self.open_user_guide(section="2-getting-started", parent_window=parent_window)

    def open_section(self, anchor: str, parent_window: Optional[Gtk.Window] = None):
        """Open the User Manual at an arbitrary anchor."""
        self.open_user_guide(section=anchor, parent_window=parent_window)

    # Legacy entry points kept for callers still using the old signature.
    # All routes now converge on the single-file HTML render.

    def open_documentation(self, page: str = "index.html",
                            parent_window: Optional[Gtk.Window] = None):
        """Legacy alias — routes to the rendered manual regardless of page."""
        self.open_user_guide(parent_window=parent_window)

    def open_reference(self, topic: str = None,
                       parent_window: Optional[Gtk.Window] = None):
        """Legacy alias — there is no separate reference site, so open the
        manual's appendix section if a known topic is requested."""
        # Manual has an "12. Appendices" section; route there as the closest
        # equivalent.
        self.open_user_guide(section="12-appendices", parent_window=parent_window)

    # ------------------------------------------------------------------
    # Browser launch + error dialogs
    # ------------------------------------------------------------------

    def _open_in_browser(self, url: str, parent_window: Optional[Gtk.Window]):
        logger.info(f"Opening documentation: {url}")
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"Failed to open documentation in browser: {e}")
            self._show_browser_error_dialog(parent_window, str(e))

    def _show_documentation_not_found_dialog(self, parent_window: Optional[Gtk.Window]):
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Documentation Not Found"
        )
        dialog.format_secondary_text(
            "The THAMES User Manual could not be rendered.\n\n"
            "Expected file:\n"
            "  docs/USER_MANUAL.md\n\n"
            "If you built from source, ensure the docs/ folder is present.\n"
            "If the markdown library is missing, install it with:\n"
            "  pip install markdown"
        )
        dialog.run()
        dialog.destroy()

    def _show_browser_error_dialog(self, parent_window: Optional[Gtk.Window],
                                    error_message: str):
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Failed to Open Browser"
        )
        dialog.format_secondary_text(
            f"Could not open documentation in your default browser.\n\n"
            f"Error: {error_message}\n\n"
            f"Rendered manual is at:\n{self._cached_html_path}"
        )
        dialog.run()
        dialog.destroy()


# Singleton instance
_documentation_viewer = None


def get_documentation_viewer() -> DocumentationViewer:
    """Return the singleton documentation viewer."""
    global _documentation_viewer
    if _documentation_viewer is None:
        _documentation_viewer = DocumentationViewer()
    return _documentation_viewer

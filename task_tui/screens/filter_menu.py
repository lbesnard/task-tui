from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.screen import ModalScreen


class FilterMenuScreen(ModalScreen):
    """Route the user to a project or tag filter.

    Dismisses with ``"project"`` or ``"tag"`` so the caller can push the
    appropriate ``MultiSelectFilterScreen``, or ``None`` on cancel.
    """

    def compose(self) -> ComposeResult:
        yield Static("🔍 FILTER: [[p]] Project · [[t]] Tag · [[Esc]] Cancel", id="context_bar", classes="visible")

    def on_key(self, event) -> None:
        key = event.key.lower()
        event.stop()
        if key == "escape":
            self.dismiss(None)
        elif key == "p":
            self.dismiss("project")
        elif key == "t":
            self.dismiss("tag")

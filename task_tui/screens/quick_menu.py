from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.screen import ModalScreen


class QuickMenuScreen(ModalScreen):
    """Keyboard-driven quick-action menu.

    Dismisses with:
    - A date string (``"today"``, ``"tomorrow"``, ``"eow"``, ``"eom"``, ``"eoy"``)
      when used as a date picker.
    - A priority letter (``"H"``, ``"M"``, ``"L"``, ``""``) when used as a
      priority picker.
    - ``"end_of"`` to signal the caller should push the end-of submenu.
    - ``None`` on cancel.
    """

    def __init__(self, menu_type: str) -> None:
        super().__init__()
        self.menu_type = menu_type

    def compose(self) -> ComposeResult:
        text = {
            "main": "📅 SET DUE: [[n]] Today | [[t]] Tomorrow | [[e]] End of... | [[Esc]] Cancel",
            "end_of": "📅 END OF: [[w]] Week | [[m]] Month | [[y]] Year | [[Esc]] Back",
            "priority": "⚡ SET PRIO: [[h]] High | [[m]] Mid | [[l]] Low | [[x]] Clear | [[Esc]] Cancel",
        }.get(self.menu_type, "")
        yield Static(text, id="context_bar", classes="visible")

    def on_key(self, event) -> None:
        key = event.key.lower()
        event.stop()

        if key == "escape":
            self.dismiss("back_to_main" if self.menu_type == "end_of" else None)
            return

        if self.menu_type == "main":
            if key == "n":
                self.dismiss("today")
            elif key == "t":
                self.dismiss("tomorrow")
            elif key == "e":
                self.dismiss("end_of")

        elif self.menu_type == "end_of":
            if key == "w":
                self.dismiss("eow")
            elif key == "m":
                self.dismiss("eom")
            elif key == "y":
                self.dismiss("eoy")

        elif self.menu_type == "priority":
            if key == "h":
                self.dismiss("H")
            elif key == "m":
                self.dismiss("M")
            elif key == "l":
                self.dismiss("L")
            elif key == "x":
                self.dismiss("")

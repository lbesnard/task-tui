from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class ConfirmScreen(ModalScreen):
    """Yes/no confirmation. Dismisses with True on ``y``/Enter, False otherwise."""

    CSS = """
    #confirm_container { background: $surface; border: thick $warning; width: 60%; height: auto; max-height: 80%; padding: 1 2; align: center middle; }
    #confirm_title { text-align: center; text-style: bold; color: $warning; margin-bottom: 1; }
    #confirm_body { margin-bottom: 1; }
    #confirm_hint { text-align: center; color: $text-muted; }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self.title_text = title
        self.body_text = body

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_container"):
            yield Label(self.title_text, id="confirm_title")
            yield Static(self.body_text, id="confirm_body")
            yield Label("[b]y[/b]/[b]Enter[/b] confirm | [b]n[/b]/[b]Esc[/b] cancel", id="confirm_hint")

    def on_key(self, event) -> None:
        event.stop()
        if event.key in ("y", "enter"):
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)

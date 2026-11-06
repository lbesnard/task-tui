from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static


class AnnotateScreen(ModalScreen):
    """Prompt for annotation text. Dismisses with the text, or None on cancel."""

    CSS = """
    #annotate_container { background: $surface; border: thick $primary; width: 70%; height: auto; padding: 1 2; align: center middle; }
    #annotate_title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="annotate_container"):
            yield Label("📝 ADD NOTE", id="annotate_title")
            yield Input(placeholder="Annotation text, Enter to save, Esc to cancel", id="annotate_input")

    def on_mount(self) -> None:
        self.query_one("#annotate_input").focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        self.dismiss(text or None)


class DenotateScreen(ModalScreen):
    """Pick one annotation to remove. Dismisses with its text, or None."""

    CSS = """
    #denotate_container { background: $surface; border: thick $error; width: 70%; height: auto; max-height: 70%; padding: 1 2; align: center middle; }
    #denotate_title { text-align: center; text-style: bold; color: $error; margin-bottom: 1; }
    """

    def __init__(self, annotations: list[dict]) -> None:
        super().__init__()
        self.annotations = annotations

    def compose(self) -> ComposeResult:
        with Vertical(id="denotate_container"):
            yield Label("🗑  REMOVE NOTE  (Enter to remove, Esc to cancel)", id="denotate_title")
            yield ListView(id="denotate_list")

    def on_mount(self) -> None:
        lv = self.query_one("#denotate_list")
        for note in self.annotations:
            item = ListItem(Static(note.get("description", "")))
            item.note_text = note.get("description", "")  # type: ignore[attr-defined]
            lv.append(item)
        lv.index = 0
        lv.focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            event.stop()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.note_text)  # type: ignore[attr-defined]

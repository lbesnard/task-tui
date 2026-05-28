from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static, Label, Input, ListView, ListItem
from textual.containers import Vertical
from textual.screen import ModalScreen


class FuzzySearchScreen(ModalScreen):
    """Fuzzy task search modal.

    Receives RawTasks from the caller — no subprocess call.
    Dismisses with the selected task UUID, or None on cancel.
    """

    def __init__(self, tasks: list[dict[str, Any]]) -> None:
        super().__init__()
        self.all_tasks = tasks

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy_container"):
            yield Label("🔍 TASK SEARCH", id="fuzzy_header")
            yield Label(
                "Type to filter | [b]Enter[/b] to select | [b]Esc[/b] to cancel",
                id="fuzzy_help",
            )
            yield Input(placeholder="Search description or project...", id="fuzzy_input")
            yield ListView(id="fuzzy_list")

    def on_mount(self) -> None:
        self.update_list("")
        self.query_one("#fuzzy_input").focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            return
        lv = self.query_one("#fuzzy_list")
        if event.key == "j":
            lv.action_cursor_down()
            event.stop()
        elif event.key == "k":
            lv.action_cursor_up()
            event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.update_list(event.value.lower())

    def update_list(self, search_term: str) -> None:
        lv = self.query_one("#fuzzy_list")
        lv.clear()
        for t in self.all_tasks:
            desc = t.get("description", "")
            proj = t.get("project", "")
            if search_term in desc.lower() or search_term in proj.lower():
                item = ListItem(Static(f"{t.get('id')} - {desc} [dim]({proj})[/dim]"))
                item.uuid = t.get("uuid")  # type: ignore[attr-defined]
                lv.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.uuid)  # type: ignore[attr-defined]

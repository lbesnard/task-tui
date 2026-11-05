from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

from ..models.task import Report

ALL_PENDING = "__all_pending__"


class ReportPickerScreen(ModalScreen):
    """Pick a Taskwarrior report to display.

    Dismisses with the chosen report name, ``ALL_PENDING`` for the plain
    pending list, or None on cancel.
    """

    def __init__(self, reports: list[Report], current: str | None) -> None:
        super().__init__()
        self.reports = reports
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy_container"):
            yield Label("📊 SWITCH REPORT", id="fuzzy_header")
            yield Label(
                "Type to filter | [b]Enter[/b] to select | [b]Esc[/b] to cancel",
                id="fuzzy_help",
            )
            yield Input(placeholder="Report name...", id="fuzzy_input")
            yield ListView(id="fuzzy_list")

    def on_mount(self) -> None:
        self.update_list("")
        self.query_one("#fuzzy_input").focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
            return
        lv = self.query_one("#fuzzy_list")
        if event.key in ("down", "ctrl+n"):
            lv.action_cursor_down()
            event.stop()
        elif event.key in ("up", "ctrl+p"):
            lv.action_cursor_up()
            event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.update_list(event.value.lower())

    def update_list(self, term: str) -> None:
        lv = self.query_one("#fuzzy_list")
        lv.clear()
        entries = [(ALL_PENDING, "all pending", "every pending task")]
        entries += [(r.name, r.name, r.filter) for r in self.reports]
        for value, label, detail in entries:
            if term not in label.lower():
                continue
            marker = "●" if value == (self.current or ALL_PENDING) else " "
            item = ListItem(Static(f"{marker} {label:<14} [dim]{detail}[/dim]"))
            item.report_name = value  # type: ignore[attr-defined]
            lv.append(item)
        if lv.children:
            lv.index = 0

    def on_input_submitted(self, event: Input.Submitted) -> None:
        lv = self.query_one("#fuzzy_list")
        if lv.highlighted_child is not None:
            self.dismiss(lv.highlighted_child.report_name)  # type: ignore[attr-defined]

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.report_name)  # type: ignore[attr-defined]

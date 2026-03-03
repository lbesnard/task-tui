import json
import subprocess
from textual.app import ComposeResult
from textual.widgets import Static, Label, Input, ListView, ListItem
from textual.containers import Vertical
from textual.screen import ModalScreen


class FuzzySearchScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy_container"):
            yield Label("🔍 TASK SEARCH", id="fuzzy_header")
            yield Label(
                "Type to filter | [b]Enter[/b] to select | [b]Esc[/b] to cancel",
                id="fuzzy_help",
            )
            yield Input(
                placeholder="Search description or project...", id="fuzzy_input"
            )
            yield ListView(id="fuzzy_list")

    def on_mount(self) -> None:
        self.all_tasks = self.load_tasks()
        self.update_list("")
        self.query_one("#fuzzy_input").focus()

    def on_key(self, event) -> None:
        list_view = self.query_one("#fuzzy_list")

        if event.key == "j":
            list_view.action_cursor_down()
            event.stop()
        elif event.key == "k":
            list_view.action_cursor_up()
            event.stop()
        elif event.key == "escape":
            self.dismiss(None)

    def load_tasks(self):
        res = subprocess.run(
            ["task", "status:pending", "export", "rc.json.array=on"],
            capture_output=True,
            text=True,
        )
        try:
            return json.loads(res.stdout)
        except:
            return []

    def on_input_changed(self, event: Input.Changed) -> None:
        self.update_list(event.value.lower())

    def update_list(self, search_term: str) -> None:
        list_view = self.query_one("#fuzzy_list")
        list_view.clear()
        for t in self.all_tasks:
            desc = t.get("description", "")
            proj = t.get("project", "")
            if search_term in desc.lower() or search_term in proj.lower():
                item = ListItem(Static(f"{t.get('id')} - {desc} [dim]({proj})[/dim]"))
                item.uuid = t.get("uuid")
                list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.uuid)

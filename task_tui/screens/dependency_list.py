from textual.app import ComposeResult
from textual.widgets import Static, Label, ListView, ListItem
from textual.containers import Vertical
from textual.screen import ModalScreen


class DependencyListScreen(ModalScreen):
    def __init__(self, dependencies, all_tasks):
        super().__init__()
        self.dependencies = dependencies
        self.all_tasks = all_tasks

    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy_container"):
            yield Label("🔗 DEPENDENCY LIST", id="fuzzy_header")
            yield Label(
                "[b]Enter[/b] to jump to task | [b]Esc[/b] to close", id="fuzzy_help"
            )
            yield ListView(id="dep_list")

    def on_mount(self) -> None:
        list_view = self.query_one("#dep_list")
        dep_set = {str(d) for d in self.dependencies}
        found = False
        for t in self.all_tasks:
            if str(t.get("id")) in dep_set or t.get("uuid") in dep_set:
                item = ListItem(
                    Static(
                        f"{t.get('id')} - {t.get('description')} [dim]({t.get('project', '')})[/dim]"
                    )
                )
                item.uuid = t.get("uuid")
                list_view.append(item)
                found = True
        if not found:
            list_view.append(ListItem(Static("No active dependencies found.")))
        list_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if hasattr(event.item, "uuid"):
            self.dismiss(event.item.uuid)
        else:
            self.dismiss(None)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)

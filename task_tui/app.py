import json
import subprocess
import re
import os
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Input,
    Label,
    Select,
    TextArea,
    ListItem,
    ListView,
)
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.screen import ModalScreen


# --- FUZZY SEARCH MODAL ---
class FuzzySearchScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        with Vertical(id="fuzzy_container"):
            yield Label("🔍 FUZZY SEARCH", id="fuzzy_header")
            yield Label(
                "Type to filter | [b]Tab[/b] or [b]⇅[/b] to navigate | [b]Enter[/b] to select",
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
                item = ListItem(Static(f"{desc} [dim]({proj})[/dim]"))
                item.uuid = t.get("uuid")
                list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.uuid)

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


# --- MAIN APP ---
class TaskProApp(App):
    CSS = """
    #fuzzy_container {
        background: $surface;
        border: thick $primary;
        width: 70%;
        height: 70%;
        align: center middle;
        padding: 1;
    }
    #fuzzy_header { text-align: center; text-style: bold; color: $accent; }
    #fuzzy_help { text-align: center; color: $text-muted; margin-bottom: 1; }
    #fuzzy_list { height: 1fr; margin-top: 1; border: solid $accent; }
    
    Screen { layout: vertical; }
    #workspace { height: 75%; layout: horizontal; }
    #list_panel { width: 60%; border: tall $accent; }
    #editor_panel { width: 40%; border: tall $primary; padding: 1; overflow-y: auto; }
    #debug_panel { height: 6; border: double $warning; background: $surface; color: $warning; padding: 1; }
    .metadata { color: #888888; text-style: bold; margin-top: 1; }
    Input, Select, TextArea { border: tall $primary; margin-bottom: 0; }
    TextArea { height: 5; }
    """

    BINDINGS = [
        Binding("f", "fuzzy_find", "Search"),
        Binding("m", "edit_mode", "Modify"),
        Binding("n", "new_task", "New"),
        Binding("s", "save_task", "Save"),
        Binding("d", "mark_done", "Done"),
        Binding("r", "refresh_tasks", "Refresh"),
        Binding("ctrl+z", "cancel_edit", "Back to List"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.active_uuid = None
        self.original_annotations = []
        self.is_modifying = False
        # Column sorting state: (column_index, descending_boolean)
        self.sort_state = {"index": 0, "reverse": False}
        self.raw_tasks = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="workspace"):
            yield DataTable(id="list_panel", cursor_type="row")
            with Vertical(id="editor_panel"):
                yield Label("DESCRIPTION", classes="metadata")
                yield Input(id="inp_desc")
                yield Label("PROJECT", classes="metadata")
                yield Input(id="inp_proj")
                yield Label("DUE (YYYYMMDD, eod, tomorrow)", classes="metadata")
                yield Input(id="inp_due")
                yield Label("TAGS (Space separated)", classes="metadata")
                yield Input(id="inp_tags")
                yield Label("PRIORITY", classes="metadata")
                yield Select(
                    [("High", "H"), ("Medium", "M"), ("Low", "L"), ("None", "X")],
                    id="sel_prio",
                    value="X",
                )
                yield Label("ANNOTATIONS (One per line)", classes="metadata")
                yield TextArea(id="inp_ann")
                yield Label("ACTIVE UUID", classes="metadata")
                yield Static("None", id="uuid_display")
        yield Static("DEBUG LOG: Click headers to sort", id="debug_panel")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_tasks()

    def action_refresh_tasks(self) -> None:
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        res = subprocess.run(
            ["task", "status:pending", "export", "rc.json.array=on"],
            capture_output=True,
            text=True,
        )
        try:
            self.raw_tasks = json.loads(res.stdout)
            self.update_table_view()
        except:
            pass

    def update_table_view(self) -> None:
        table = self.query_one(DataTable)
        table.clear(columns=True)

        # Define Columns and mapping keys
        cols = [
            ("ID", "id"),
            ("Project", "project"),
            ("Prio", "priority"),
            ("Due", "due"),
            ("Tags", "tags"),
            ("Description", "description"),
        ]

        # Add columns with sorting indicator
        for i, (label, _) in enumerate(cols):
            if i == self.sort_state["index"]:
                icon = " ↓" if self.sort_state["reverse"] else " ↑"
                table.add_column(f"[b][yellow]{label}{icon}[/][/b]", key=label)
            else:
                table.add_column(label, key=label)

        # Sort data
        sort_key = cols[self.sort_state["index"]][1]

        def get_sort_val(t):
            val = t.get(sort_key, "")
            if isinstance(val, list):
                return ",".join(val)
            return str(val).lower()

        sorted_data = sorted(
            self.raw_tasks, key=get_sort_val, reverse=self.sort_state["reverse"]
        )

        # Populate rows
        for t in sorted_data:
            prio = t.get("priority", "X")
            prio_color = {"H": "red", "M": "yellow", "L": "green", "X": "white"}.get(
                prio, "white"
            )
            table.add_row(
                str(t.get("id", "-")),
                t.get("project", ""),
                f"[{prio_color}]{prio}[/]",
                (t.get("due", "") or "")[:8],
                ",".join(t.get("tags", [])),
                t.get("description", ""),
                key=t.get("uuid"),
            )

    # --- CLICK TO SORT HANDLER ---
    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Fires when a column header is clicked."""
        if self.sort_state["index"] == event.column_index:
            # Toggle direction if clicking the same column
            self.sort_state["reverse"] = not self.sort_state["reverse"]
        else:
            # New column clicked
            self.sort_state["index"] = event.column_index
            self.sort_state["reverse"] = False

        self.update_table_view()
        self.notify(f"Sorting by {event.column_key.value}")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not self.is_modifying and event.row_key and event.row_key.value:
            self.load_task_by_uuid(event.row_key.value, focus=False)

    def load_task_by_uuid(self, uuid: str, focus: bool = True):
        res = subprocess.run(
            ["task", uuid, "export", "rc.json.array=on"], capture_output=True, text=True
        )
        try:
            task = json.loads(res.stdout)[0]
        except:
            return

        self.active_uuid = uuid
        self.query_one("#uuid_display").update(uuid)
        self.query_one("#inp_desc").value = task.get("description", "")
        self.query_one("#inp_proj").value = task.get("project", "")
        self.query_one("#inp_due").value = (task.get("due", "") or "").replace("Z", "")[
            :13
        ]
        self.query_one("#inp_tags").value = " ".join(task.get("tags", []))
        self.query_one("#sel_prio").value = task.get("priority", "X")

        anns = [a["description"] for a in task.get("annotations", [])]
        self.original_annotations = anns.copy()
        self.query_one("#inp_ann").text = "\n".join(anns)

        if focus:
            self.is_modifying = True
            self.query_one("#inp_desc").focus()
            self.query_one("#debug_panel").update(
                f"EDITING: {task.get('description')[:30]}"
            )
        else:
            self.query_one("#debug_panel").update(
                f"VIEWING: {task.get('description')[:30]}"
            )

    def action_edit_mode(self):
        try:
            row_key, _ = self.query_one(DataTable).coordinate_to_cell_key(
                self.query_one(DataTable).cursor_coordinate
            )
            self.load_task_by_uuid(row_key.value, focus=True)
        except:
            pass

    def action_save_task(self):
        desc = self.query_one("#inp_desc").value
        if not desc or not self.active_uuid:
            return
        is_new = self.active_uuid == "NEW"
        cmd = [
            "task",
            "add" if is_new else self.active_uuid,
            "modify" if not is_new else "",
            desc,
        ]
        if is_new:
            cmd.remove("")
        cmd.extend(
            [
                f"project:{self.query_one('#inp_proj').value}",
                f"due:{self.query_one('#inp_due').value}",
                f"priority:{self.query_one('#sel_prio').value if self.query_one('#sel_prio').value != 'X' else ''}",
                f"tags.set:{self.query_one('#inp_tags').value.replace(' ', ',')}"
                if self.query_one("#inp_tags").value
                else "tags.set:",
            ]
        )
        save_res = subprocess.run(cmd, capture_output=True, text=True)
        target_id = self.active_uuid
        if is_new:
            match = re.search(r"Created task (\d+)", save_res.stdout)
            target_id = match.group(1) if match else "+LATEST"
        current_anns = [
            line.strip()
            for line in self.query_one("#inp_ann").text.split("\n")
            if line.strip()
        ]
        if not is_new:
            for ann in self.original_annotations:
                subprocess.run(
                    ["task", target_id, "denotate", ann], capture_output=True
                )
        for ann in current_anns:
            subprocess.run(["task", target_id, "annotate", ann], capture_output=True)
        self.is_modifying = False
        self.refresh_tasks()
        self.action_cancel_edit()
        self.notify("Saved!")

    def action_cancel_edit(self):
        self.is_modifying = False
        self.query_one(DataTable).focus()
        self.query_one("#debug_panel").update("NAVIGATING: Click headers to sort")

    def action_new_task(self):
        self.is_modifying = True
        self.active_uuid = "NEW"
        for field in ["#inp_desc", "#inp_proj", "#inp_due", "#inp_tags"]:
            self.query_one(field).value = ""
        self.query_one("#inp_ann").text = ""
        self.query_one("#uuid_display").update("NEW TASK")
        self.query_one("#inp_desc").focus()

    def action_fuzzy_find(self) -> None:
        def on_select(uuid):
            if uuid:
                self.load_task_by_uuid(uuid, focus=False)

        self.push_screen(FuzzySearchScreen(), on_select)

    def action_mark_done(self):
        try:
            row_key, _ = self.query_one(DataTable).coordinate_to_cell_key(
                self.query_one(DataTable).cursor_coordinate
            )
            subprocess.run(["task", row_key.value, "done"])
            self.refresh_tasks()
            self.notify("Task Done!")
        except:
            pass

    def on_unmount(self) -> None:
        os.system("clear")
        print("Finalizing... Syncing with Taskwarrior server.")
        try:
            subprocess.run(["task", "sync"], check=True)
            print("Done!")
        except:
            print("Sync skipped.")


def run():
    TaskProApp().run()


if __name__ == "__main__":
    run()

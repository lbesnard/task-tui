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


# --- QUICK MENU MODAL ---
class QuickMenuScreen(ModalScreen):
    def __init__(self, menu_type, app_ref):
        super().__init__()
        self.menu_type = menu_type
        self.app_ref = app_ref

    def compose(self) -> ComposeResult:
        # We reuse your CSS context_bar look
        text = ""
        if self.menu_type == "main":
            text = "📅 SET DUE: [[n]] Today | [[t]] Tomorrow | [[e]] End of... | [[Esc]] Cancel"
        elif self.menu_type == "end_of":
            text = "📅 END OF: [[w]] Week | [[m]] Month | [[y]] Year | [[Esc]] Back"
        elif self.menu_type == "priority":
            text = "⚡ SET PRIO: [[h]] High | [[m]] Mid | [[l]] Low | [[x]] Clear | [[Esc]] Cancel"

        yield Static(text, id="context_bar", classes="visible")

    def on_key(self, event) -> None:
        key = event.key.lower()

        if key == "escape":
            if self.menu_type == "end_of":
                # Go back to main date menu
                self.dismiss("back_to_main")
            else:
                self.dismiss(None)

        # Main Date Logic
        elif self.menu_type == "main":
            if key == "n":
                self.app_ref.apply_quick_date("today")
                self.dismiss(None)
            elif key == "t":
                self.app_ref.apply_quick_date("tomorrow")
                self.dismiss(None)
            elif key == "e":
                self.dismiss("go_to_end_of")

        # End Of Logic
        elif self.menu_type == "end_of":
            if key == "w":
                self.app_ref.apply_quick_date("eow")
            elif key == "m":
                self.app_ref.apply_quick_date("eom")
            elif key == "y":
                self.app_ref.apply_quick_date("eoy")
            if key in ["w", "m", "y"]:
                self.dismiss(None)

        # Priority Logic
        elif self.menu_type == "priority":
            if key == "h":
                self.app_ref.apply_quick_prio("H")
            elif key == "m":
                self.app_ref.apply_quick_prio("M")
            elif key == "l":
                self.app_ref.apply_quick_prio("L")
            elif key == "x":
                self.app_ref.apply_quick_prio("")
            if key in ["h", "m", "l", "x"]:
                self.dismiss(None)

        event.stop()  # CRITICAL: This kills the key so it never hits the main app


# --- DEPENDENCY LIST SCREEN ---
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


# --- FUZZY SEARCH MODAL ---
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
        """Handle Vim-like navigation in the search results."""
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


# --- MAIN APP ---
class TaskProApp(App):
    CSS = """
    #fuzzy_container { background: $surface; border: thick $primary; width: 70%; height: 70%; align: center middle; padding: 1; }
    #fuzzy_header { text-align: center; text-style: bold; color: $accent; }
    #fuzzy_help { text-align: center; color: $text-muted; margin-bottom: 1; }
    #fuzzy_list, #dep_list { height: 1fr; margin-top: 1; border: solid $accent; }
    
    Screen { layout: vertical; }
    #workspace { height: 75%; layout: horizontal; }
    #list_panel { width: 60%; border: tall $accent; }
    
    #editor_panel { width: 40%; border: tall $primary; padding: 1; overflow-y: auto; }
    #editor_panel.view_mode { background: #002b36; border: tall #268bd2; }
    #editor_panel.edit_mode { background: #3b1010; border: tall #dc322f; }
    
    #mode_indicator { text-align: center; text-style: bold; margin-bottom: 1; }
    .metadata { color: #888888; text-style: bold; margin-top: 1; }
    Input, Select, TextArea { border: tall $primary; margin-bottom: 0; }
    
    #context_bar { background: $accent; color: white; content-align: center middle; text-style: bold; display: none; height: 1; width: 100%; padding: 0 1; }
    .visible { display: block !important; }
    """

    BINDINGS = [
        Binding("/", "fuzzy_find", "Search"),
        Binding("v", "view_dependencies", "ViewDeps"),
        Binding("u", "undo", "Undo"),
        Binding("space", "toggle_selection", "Select"),
        Binding("t", "date_mode", "SetDate"),
        Binding("p", "prio_mode", "SetPrio"),
        Binding("i", "edit_mode", "Modify/Edit"),
        Binding("n", "new_task", "New"),
        Binding("x", "save_task", "Save"),
        Binding("s", "toggle_start", "Start/Stop"),
        Binding("d", "mark_done", "Done"),
        Binding("r", "refresh_tasks", "Refresh"),
        Binding("ctrl+z", "cancel_edit", "Back"),
        Binding("q", "quit", "Quit"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("h", "cursor_left", "Left", show=False),
        Binding("l", "cursor_right", "Right", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    is_dirty = False  # Track if changes exist

    def __init__(self):
        super().__init__()
        self.active_uuid = None
        self.selected_uuids = set()
        self.is_modifying = False
        self.sort_state = {"index": 5, "reverse": True}
        self.raw_tasks = []
        self.date_context = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="context_bar")
        with Horizontal(id="workspace"):
            yield DataTable(id="list_panel", cursor_type="row")
            with Vertical(id="editor_panel", classes="view_mode"):
                yield Static("🔒 VIEWING", id="mode_indicator")
                yield Label("DESCRIPTION", classes="metadata")
                yield Input(id="inp_desc", disabled=True)  # Add read_only=True
                yield Label("PROJECT", classes="metadata")
                yield Input(id="inp_proj", disabled=True)
                yield Label(
                    "DUE (YYYYMMDD or e.g. 'tomorrow', 'eo[d,m,y]')",
                    classes="metadata",
                )
                yield Input(id="inp_due", disabled=True)
                yield Label("DEPENDS ON (Ctrl+F to pick tasks)", classes="metadata")
                yield Input(id="inp_dep", disabled=True)
                yield Label("TAGS", classes="metadata")
                yield Input(id="inp_tags", disabled=True)
                yield Label("PRIORITY", classes="metadata")
                yield Select(
                    [("High", "H"), ("Mid", "M"), ("Low", "L"), ("None", "X")],
                    id="sel_prio",
                    value="X",
                    disabled=True,  # Start disabled
                )
                yield Label("UUID", classes="metadata")
                yield Static("None", id="uuid_display")
        yield Static("DEBUG LOG", id="debug_panel")
        yield Footer()

    #
    # def compose(self) -> ComposeResult:
    #     yield Header()
    #     yield Static("", id="context_bar")
    #     with Horizontal(id="workspace"):
    #         yield DataTable(id="list_panel", cursor_type="row")
    #         with Vertical(id="editor_panel", classes="view_mode"):
    #             yield Static("🔒 VIEWING", id="mode_indicator")
    #             yield Label("DESCRIPTION", classes="metadata")
    #             yield Input(id="inp_desc")
    #             yield Label("PROJECT", classes="metadata")
    #             yield Input(id="inp_proj")
    #             yield Label("DUE (YYYYMMDD or e.g. 'tomorrow')", classes="metadata")
    #             yield Input(id="inp_due")
    #             yield Label("DEPENDS ON (Ctrl+F to pick tasks)", classes="metadata")
    #             yield Input(id="inp_dep")
    #             yield Label("TAGS", classes="metadata")
    #             yield Input(id="inp_tags")
    #             yield Label("PRIORITY", classes="metadata")
    #             yield Select(
    #                 [("High", "H"), ("Mid", "M"), ("Low", "L"), ("None", "X")],
    #                 id="sel_prio",
    #                 value="X",
    #             )
    #             yield Label("UUID", classes="metadata")
    #             yield Static("None", id="uuid_display")
    #     yield Static("DEBUG LOG", id="debug_panel")
    #     yield Footer()

    def on_mount(self) -> None:
        self.refresh_tasks()

    def on_key(self, event) -> None:
        # # 1. Handle Context Modes (Date/Priority) first to "trap" keys
        # if self.date_context:
        #     key = event.key.lower()
        #
        #     # Special case: Always allow Escape to get out
        #     if key == "escape":
        #         if self.date_context == "end_of":
        #             self.date_context = "main"
        #             self.update_context_bar()
        #         else:
        #             self.exit_context_mode()
        #         event.stop()
        #         return
        #
        #     # Main Date Menu
        #     if self.date_context == "main":
        #         if key == "n":
        #             self.apply_quick_date("today")
        #         elif key == "t":
        #             self.apply_quick_date("tomorrow")
        #         elif key == "e":
        #             self.date_context = "end_of"
        #             self.update_context_bar()
        #         event.stop()  # Prevents 'n' from creating a New Task
        #         return
        #
        #     # End Of Menu
        #     elif self.date_context == "end_of":
        #         if key == "w":
        #             self.apply_quick_date("eow")
        #         elif key == "m":
        #             self.apply_quick_date("eom")
        #         elif key == "y":
        #             self.apply_quick_date("eoy")
        #         event.stop()
        #         return
        #
        #     # Priority Menu
        #     elif self.date_context == "priority":
        #         if key == "h":
        #             self.apply_quick_prio("H")
        #         elif key == "m":
        #             self.apply_quick_prio("M")
        #         elif key == "l":
        #             self.apply_quick_prio("L")
        #         elif key == "x":
        #             self.apply_quick_prio("")
        #         event.stop()  # Prevents 'x' from Saving or Marking Done
        #         return
        #
        # 2. Existing Global Guards (Locked Interface)
        if not self.is_modifying and len(event.character or "") == 1:
            is_bound = any(binding.key == event.key for binding in self.BINDINGS)
            if not is_bound:
                self.notify("Press [b]i[/b] to enter Edit Mode", severity="warning")
                event.stop()
                return

        # 3. Specific Bound Actions (Shift+S, etc.)
        if event.key == "S":
            self.action_save_task()
            event.stop()
            return

        if self.is_modifying and event.key == "ctrl+f" and self.focused.id == "inp_dep":
            self.action_fuzzy_find_dep()

    # def on_key(self, event) -> None:
    #     # Force Save even when inside an Input field
    #     if event.key == "S":  # Shift+S
    #         self.action_save_task()
    #         event.stop()
    #         return
    #     # Detect if a user is trying to type (any single character) while locked
    #     if not self.is_modifying and len(event.character or "") == 1:
    #         # Check if the key is actually bound to a command first
    #         # We allow bound keys like 'j', 'k', '/', etc.
    #         is_bound = any(binding.key == event.key for binding in self.BINDINGS)
    #
    #         if not is_bound:
    #             self.notify("Press [b]i[/b] to enter Edit Mode", severity="warning")
    #             self.query_one("#debug_panel").update(
    #                 "⚠️ Interface locked: Enter Edit Mode (i) to modify fields."
    #             )
    #             event.stop()
    #             return
    #
    #     if self.date_context:
    #         key = event.key.lower()
    #         if self.date_context == "main":
    #             if key == "n":
    #                 self.apply_quick_date("today")
    #             elif key == "t":
    #                 self.apply_quick_date("tomorrow")
    #             elif key == "e":
    #                 self.date_context = "end_of"
    #                 self.update_context_bar()
    #             elif key == "escape":
    #                 self.exit_context_mode()
    #             event.stop()
    #         elif self.date_context == "end_of":
    #             if key == "w":
    #                 self.apply_quick_date("eow")
    #             elif key == "m":
    #                 self.apply_quick_date("eom")
    #             elif key == "y":
    #                 self.apply_quick_date("eoy")
    #             elif key == "escape":
    #                 self.date_context = "main"
    #                 self.update_context_bar()
    #             event.stop()
    #         elif self.date_context == "priority":
    #             if key == "h":
    #                 self.apply_quick_prio("H")
    #             elif key == "m":
    #                 self.apply_quick_prio("M")
    #             elif key == "l":
    #                 self.apply_quick_prio("L")
    #             elif key == "x":
    #                 self.apply_quick_prio("")
    #             elif key == "escape":
    #                 self.exit_context_mode()
    #             event.stop()
    #
    #     if self.is_modifying and event.key == "ctrl+f" and self.focused.id == "inp_dep":
    #         self.action_fuzzy_find_dep()
    #     #
    #     # if event.key == "tab" and self.is_modifying and self.is_dirty:
    #     #     self.notify(
    #     #         "You have unsaved changes! Press x to save or Ctrl+Z to discard.",
    #     #         severity="error",
    #     #     )
    #     #     event.stop()  # Prevents shifting focus back to the table
    #     #     return
    #
    def action_quit(self) -> None:
        if self.is_dirty:
            self.notify(
                "⚠️ UNSAVED CHANGES! Save with x or discard with Ctrl+Z before quitting.",
                severity="error",
            )
        else:
            self.exit()

    # def on_descendant_focus(self, event) -> None:
    #     """Fires whenever a widget inside the app gets focus."""
    #     # If the user goes back to the list while dirty
    #     if isinstance(event.control, DataTable) and self.is_dirty:
    #         self.notify(
    #             "⚠️ UNSAVED CHANGES in editor! Save (x)  or Discard (Ctrl+Z) before switching tasks.",
    #             severity="warning",
    #             timeout=3,
    #         )
    #         # We DON'T event.stop() and DON'T force focus back.
    #         # This allows you to press 'x' on the list.
    #
    def on_descendant_focus(self, event) -> None:
        """Fires whenever a widget inside the app gets focus."""
        if isinstance(event.control, DataTable) and self.is_dirty:
            self.notify(
                "⚠️ UNSAVED CHANGES! Press 'x' to save or 'Ctrl+Z' to discard.",
                severity="warning",
                timeout=3,
            )
            # We allow focus to stay on the DataTable so 'x' works.
            #

    def on_input_changed(self) -> None:
        if self.is_modifying:
            self.is_dirty = True
            # self.query_one("#mode_indicator").update(
            #     "✏️ MODIFYING [b][yellow](UNSAVED)[/][/]"
            # )
            self.query_one("#mode_indicator").update(
                "✏️ MODIFYING [b][blink][yellow](UNSAVED)[/][/][/]"
            )

    def on_select_changed(self) -> None:
        if self.is_modifying:
            self.is_dirty = True

    # def update_context_bar(self):
    #     bar = self.query_one("#context_bar")
    #     bar.add_class("visible")
    #     if self.date_context == "main":
    #         bar.update(
    #             "📅  SET DUE: [[n]] Today | [[t]] Tomorrow | [[e]] End of... | [[Esc]] Cancel"
    #         )
    #     elif self.date_context == "end_of":
    #         bar.update(
    #             "📅  END OF: [[w]] Week | [[m]] Month | [[y]] Year | [[Esc]] Back"
    #         )
    #     elif self.date_context == "priority":
    #         bar.update(
    #             "⚡  SET PRIO: [[h]] High | [[m]] Mid | [[l]] Low | [[x]] Clear | [[Esc]] Cancel"
    #         )
    #
    # --- ACTIONS ---
    def action_cursor_down(self):
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self):
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_left(self):
        self.query_one(DataTable).action_cursor_left()

    def action_cursor_right(self):
        self.query_one(DataTable).action_cursor_right()

    def action_scroll_top(self):
        self.query_one(DataTable).scroll_home()
        self.query_one(DataTable).move_cursor(row=0)

    def action_scroll_bottom(self):
        self.query_one(DataTable).scroll_end()
        self.query_one(DataTable).move_cursor(row=len(self.raw_tasks) - 1)

    def action_undo(self):
        subprocess.run(["task", "rc.confirmation=off", "undo"])
        self.refresh_tasks()
        self.notify("Last action undone")

    def action_view_dependencies(self):
        if not self.active_uuid or self.active_uuid == "NEW":
            return
        task = next((t for t in self.raw_tasks if t["uuid"] == self.active_uuid), None)
        if task and "depends" in task:

            def on_jump_to(uuid):
                if uuid:
                    table = self.query_one(DataTable)
                    for idx, row_key in enumerate(table.rows):
                        if row_key.value == uuid:
                            table.move_cursor(row=idx)
                            break

            self.push_screen(
                DependencyListScreen(task["depends"], self.raw_tasks), on_jump_to
            )

    def action_new_task(self):
        self.set_modify_mode(True)
        self.active_uuid = "NEW"
        for field in ["#inp_desc", "#inp_proj", "#inp_due", "#inp_dep", "#inp_tags"]:
            self.query_one(field).value = ""
        self.query_one("#uuid_display").update("NEW TASK")
        self.query_one("#inp_desc").focus()

    def action_toggle_start(self):
        if not self.active_uuid or self.active_uuid == "NEW":
            return
        task = next((t for t in self.raw_tasks if t["uuid"] == self.active_uuid), None)
        if task:
            cmd = "stop" if task.get("start") else "start"
            subprocess.run(["task", self.active_uuid, cmd])
            self.refresh_tasks()

    def action_mark_done(self):
        # 1. Determine which tasks to complete
        targets = (
            list(self.selected_uuids) if self.selected_uuids else [self.active_uuid]
        )

        # 2. Guard against empty selection or "NEW" task
        targets = [uid for uid in targets if uid and uid != "NEW"]

        if not targets:
            return

        # 3. Execute 'done' for each task
        for uid in targets:
            subprocess.run(["task", uid, "done"])

        # 4. Cleanup
        self.selected_uuids.clear()  # Clear selection after action
        self.refresh_tasks()
        self.notify(f"Completed {len(targets)} task(s)!")

    #
    # def action_mark_done(self):
    #     if not self.active_uuid or self.active_uuid == "NEW":
    #         return
    #     subprocess.run(["task", self.active_uuid, "done"])
    #     self.refresh_tasks()
    #     self.notify("Task completed!")

    def action_fuzzy_find(self):
        def on_select(uuid):
            if uuid:
                self.load_task_by_uuid(uuid, focus=False)
                table = self.query_one(DataTable)
                for idx, row_key in enumerate(table.rows):
                    if row_key.value == uuid:
                        table.move_cursor(row=idx)
                        break

        self.push_screen(FuzzySearchScreen(), on_select)

    def action_fuzzy_find_dep(self):
        def on_select(selected_uuid):
            if selected_uuid:
                current = self.query_one("#inp_dep").value
                # Append the new UUID to the list
                new_val = f"{current}, {selected_uuid}" if current else selected_uuid
                self.query_one("#inp_dep").value = new_val.strip(", ")

        self.push_screen(FuzzySearchScreen(), on_select)

    def action_toggle_selection(self):
        if self.active_uuid and self.active_uuid != "NEW":
            if self.active_uuid in self.selected_uuids:
                self.selected_uuids.remove(self.active_uuid)
            else:
                self.selected_uuids.add(self.active_uuid)
            self.update_table_view()

    def action_date_mode(self):
        def check_result(result):
            if result == "go_to_end_of":
                self.push_screen(QuickMenuScreen("end_of", self), check_result)
            elif result == "back_to_main":
                self.push_screen(QuickMenuScreen("main", self), check_result)

        self.push_screen(QuickMenuScreen("main", self), check_result)

    def action_prio_mode(self):
        self.push_screen(QuickMenuScreen("priority", self))

    # def action_date_mode(self):
    #     self.date_context = "main"
    #     self.update_context_bar()
    #
    #
    # def action_prio_mode(self):
    #     self.date_context = "priority"
    #     self.update_context_bar()
    #
    # def exit_context_mode(self):
    #     self.date_context = None
    #     self.query_one("#context_bar").remove_class("visible")
    #
    def apply_quick_date(self, date_str):
        targets = (
            list(self.selected_uuids) if self.selected_uuids else [self.active_uuid]
        )
        for uid in targets:
            if uid != "NEW":
                subprocess.run(["task", uid, "modify", f"due:{date_str}"])
        self.refresh_tasks()
        # self.exit_context_mode()

    def apply_quick_prio(self, level):
        targets = (
            list(self.selected_uuids) if self.selected_uuids else [self.active_uuid]
        )
        for uid in targets:
            if uid != "NEW":
                subprocess.run(["task", uid, "modify", f"priority:{level}"])
        self.refresh_tasks()
        # self.exit_context_mode()

    # --- DATA & TABLE ---
    def refresh_tasks(self) -> None:
        table = self.query_one(DataTable)
        saved_row_key = None
        if table.row_count > 0:
            try:
                saved_row_key = table.get_row_at(table.cursor_row).key
            except:
                pass

        res = subprocess.run(
            ["task", "status:pending", "export", "rc.json.array=on"],
            capture_output=True,
            text=True,
        )
        try:
            self.raw_tasks = json.loads(res.stdout)
            self.update_table_view()
            if saved_row_key:
                for idx, row_key in enumerate(table.rows):
                    if row_key == saved_row_key:
                        table.move_cursor(row=idx)
                        break
        except:
            pass

    def update_table_view(self) -> None:
        table = self.query_one(DataTable)
        # --- SAVE CURSOR POSITION ---
        # We save the row index so we can jump back to it after the refresh
        saved_cursor_row = table.cursor_row
        saved_scroll_x, saved_scroll_y = table.scroll_offset

        table.clear(columns=True)
        cols = [
            ("ID", "id"),
            ("Proj.", "project"),
            ("P.", "priority"),
            ("Due", "due"),
            ("Tags", "tags"),
            ("Urg.", "urgency"),
            ("Desc.", "description"),
        ]
        for i, (label, _) in enumerate(cols):
            icon = (
                " 🔽"
                if i == self.sort_state["index"] and self.sort_state["reverse"]
                else " 🔼"
                if i == self.sort_state["index"]
                else ""
            )
            table.add_column(f"{label}{icon}", key=cols[i][1])

        # --- PROJECT COLOR HASHING ---
        def get_project_color(project_name):
            if not project_name:
                return "white"
            # Standard ANSI/Xterm colors (avoiding very dark ones)
            # This provides a palette of ~200 distinct colors
            colors = [
                "green",
                "yellow",
                "blue",
                "magenta",
                "cyan",
                "white",
                "bright_black",
                "bright_red",
                "bright_green",
                "bright_yellow",
                "bright_blue",
                "bright_magenta",
                "bright_cyan",
                "bright_white",
                "orange1",
                "orange_red1",
                "orchid",
                "pale_green1",
                "pale_turquoise1",
                "hot_pink",
                "indian_red",
                "khaki1",
                "light_coral",
                "light_pink1",
                "light_salmon1",
                "light_sea_green",
                "light_skyblue1",
                "light_slate_blue",
                "light_steel_blue1",
                "medium_orchid1",
                "medium_purple1",
                "medium_spring_green",
            ]
            # Use a simple hash to pick a consistent color for the project name
            idx = sum(ord(c) for c in project_name) % len(colors)
            return colors[idx]

        sort_key = cols[self.sort_state["index"]][1]

        def sort_logic(t):
            val = t.get(sort_key, "")
            if sort_key == "urgency":
                try:
                    return float(val)
                except:
                    return 0.0
            # Custom Priority Weighting
            if sort_key == "priority":
                # Assign numeric weights so H (3) > M (2) > L (1) > None (0)
                weights = {"H": 3, "M": 2, "L": 1, "X": 0, "": 0}
                return weights.get(val, 0)

            return str(val).lower()

        # Sort with reverse=True so higher weights (H) appear at the top
        sorted_data = sorted(
            self.raw_tasks,
            key=sort_logic,
            reverse=True if sort_key == "priority" else self.sort_state["reverse"],
        )
        # sorted_data = sorted(
        #     self.raw_tasks, key=sort_logic, reverse=self.sort_state["reverse"]
        # )

        for t in sorted_data:
            uuid = t.get("uuid")
            prio = t.get("priority", "X")
            prio_color = {"H": "red", "M": "yellow", "L": "green"}.get(prio, "white")

            # Get the color for the project
            proj_name = t.get("project", "")
            proj_color = get_project_color(proj_name)
            # 2. Urgency Color Logic
            urgency_val = t.get("urgency", 0)
            # If urgency is above 20, wrap it in a red bold tag
            urgency_str = f"{urgency_val:.1f}"
            if urgency_val > 20:
                urgency_display = f"[b][red]{urgency_str}[/][/]"
            else:
                urgency_display = urgency_str

            is_active = "▸ " if t.get("start") else "  "
            prefix = "⭐ " if uuid in self.selected_uuids else is_active
            dep_icon = "🔗 " if "depends" in t and t["depends"] else ""

            table.add_row(
                f"{prefix}{t.get('id')}",
                f"[{proj_color}]{proj_name}[/]",  # Apply the project color here
                # t.get("project", ""),
                f"[{prio_color}]{prio}[/]",
                (t.get("due", "") or "")[:8],
                ",".join(t.get("tags", [])),
                # f"{t.get('urgency', 0):.1f}",
                urgency_display,  # Use the conditionally styled urgency here
                f"{dep_icon}{t.get('description', '')}",
                key=uuid,
            )
            # --- RESTORE CURSOR POSITION ---
            if table.row_count > 0:
                # Ensure the saved index isn't out of bounds if the list shrank
                new_row = min(saved_cursor_row, table.row_count - 1)
                table.move_cursor(row=new_row)
                # Restore the scroll position so the view doesn't jump
                table.scroll_to(x=saved_scroll_x, y=saved_scroll_y, animate=False)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        if self.sort_state["index"] == event.column_index:
            self.sort_state["reverse"] = not self.sort_state["reverse"]
        else:
            self.sort_state["index"] = event.column_index
            self.sort_state["reverse"] = False
        self.update_table_view()

    #
    # def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
    #     if not self.is_modifying and event.row_key:
    #         self.load_task_by_uuid(event.row_key.value, focus=False)
    #
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when Enter is pressed on a row."""
        if self.is_dirty:
            self.notify(
                "⚠️ Save (x) or Discard (Ctrl+Z) before switching tasks!",
                severity="error",
            )
            return

        if event.row_key:
            # Load the task and enter edit mode automatically
            self.load_task_by_uuid(event.row_key.value, focus=True)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # NEW GUARD: If we have unsaved changes, don't update the editor fields
        if self.is_dirty:
            return

        if not self.is_modifying and event.row_key:
            self.load_task_by_uuid(event.row_key.value, focus=False)

    def load_task_by_uuid(self, uuid: str, focus: bool = True):
        task = next((t for t in self.raw_tasks if t["uuid"] == uuid), None)
        if not task:
            return
        self.active_uuid = uuid
        self.query_one("#uuid_display").update(uuid)
        self.query_one("#inp_desc").value = task.get("description", "")
        self.query_one("#inp_proj").value = task.get("project", "")
        # Clean the date to YYYYMMDD format for the input field
        due_date = (task.get("due", "") or "").replace("Z", "")[:8]
        self.query_one("#inp_due").value = due_date
        self.query_one("#inp_tags").value = ",".join(task.get("tags", []))
        self.query_one("#inp_dep").value = ", ".join(map(str, task.get("depends", [])))
        self.query_one("#sel_prio").value = task.get("priority", "X")
        if focus:
            self.set_modify_mode(True)
            self.query_one("#inp_desc").focus()
        else:
            self.set_modify_mode(False)

    def set_modify_mode(self, active: bool):
        self.is_modifying = active
        self.is_dirty = False  # Reset flag whenever we switch modes
        panel = self.query_one("#editor_panel")
        indicator = self.query_one("#mode_indicator")

        # Select all input-capable widgets
        inputs = self.query("Input, Select, TextArea")

        if active:
            panel.remove_class("view_mode")
            panel.add_class("edit_mode")
            indicator.update("✏️ MODIFYING")
            for node in inputs:
                node.disabled = False  # Ensure they are interactable
                if hasattr(node, "read_only"):
                    node.read_only = False
        else:
            panel.remove_class("edit_mode")
            panel.add_class("view_mode")
            indicator.update("🔒 VIEWING")
            for node in inputs:
                node.disabled = True
                # # Setting read_only keeps them readable but prevents typing
                # if hasattr(node, "read_only"):
                #     node.read_only = True
                # # Select widgets don't have read_only, so we disable them
                # elif isinstance(node, Select):
                #     node.disabled = True
                #
                # --- CRITICAL FIX START ---
                # Force focus back to the list so keys like 'j', 'k', and 'i'
                # are captured by the app/table again instead of the disabled input.
                self.query_one(DataTable).focus()
                # --- CRITICAL FIX END ---
        if not active:
            self.query_one("#mode_indicator").update("🔒 VIEWING")
            self.query_one(DataTable).focus()

    #
    # def set_modify_mode(self, active: bool):
    #     self.is_modifying = active
    #     panel = self.query_one("#editor_panel")
    #     indicator = self.query_one("#mode_indicator")
    #     if active:
    #         panel.remove_class("view_mode")
    #         panel.add_class("edit_mode")
    #         indicator.update("✏️ MODIFYING")
    #     else:
    #         panel.remove_class("edit_mode")
    #         panel.add_class("view_mode")
    #         indicator.update("🔒 VIEWING")
    #
    def action_edit_mode(self):
        if self.active_uuid:
            self.load_task_by_uuid(self.active_uuid, focus=True)

    def action_save_task(self):
        if not self.active_uuid:
            return

        # Clean the dependency string:
        # 1. Remove all spaces
        # 2. Ensure it's a clean comma-separated list of UUIDs/IDs
        dep_raw = self.query_one("#inp_dep").value.strip()
        dep_val = ",".join([d.strip() for d in dep_raw.split(",") if d.strip()])

        target = "add" if self.active_uuid == "NEW" else self.active_uuid
        cmd = ["task", target]
        if self.active_uuid != "NEW":
            cmd.append("modify")
        # Fix the date format before sending to Taskwarrior
        due_val = self.query_one("#inp_due").value.strip()
        if due_val.isdigit() and len(due_val) == 8:
            due_val += "T000000"  # Convert YYYYMMDD to YYYYMMDDT000000

        cmd.extend(
            [
                f"description:{self.query_one('#inp_desc').value}",
                f"project:{self.query_one('#inp_proj').value}",
                f"due:{due_val}",  # Use the corrected date value here
                f"tags:{self.query_one('#inp_tags').value}",
                f"depends:{dep_val}",
                f"priority:{self.query_one('#sel_prio').value if self.query_one('#sel_prio').value != 'X' else ''}",
            ]
        )

        # IMPROVED EXECUTION: Capture errors for the debug log
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # If Taskwarrior complains, we finally see why in the debug panel
            error_msg = result.stderr.strip() or result.stdout.strip()
            self.query_one("#debug_panel").update(f"❌ ERROR: {error_msg}")
            self.notify("Save Failed! Check Debug Log.", severity="error")
        else:
            self.query_one("#debug_panel").update(f"✅ Saved successfully: {target}")
            self.set_modify_mode(False)
            self.refresh_tasks()
            self.query_one(DataTable).focus()
            self.notify("Saved!")

    #
    # def action_save_task(self):
    #     if not self.active_uuid:
    #         return
    #
    #     # Clean the dependency string: remove spaces and ensure it's a clean comma-separated list
    #     dep_val = self.query_one("#inp_dep").value.strip().replace(" ", "")
    #
    #     target = "add" if self.active_uuid == "NEW" else self.active_uuid
    #     cmd = ["task", target]
    #     if self.active_uuid != "NEW":
    #         cmd.append("modify")
    #
    #     cmd.extend(
    #         [
    #             f"description:{self.query_one('#inp_desc').value}",
    #             f"project:{self.query_one('#inp_proj').value}",
    #             f"due:{self.query_one('#inp_due').value}",
    #             f"tags:{self.query_one('#inp_tags').value}",
    #             f"depends:{dep_val}",  # Taskwarrior handles UUIDs here perfectly
    #             f"priority:{self.query_one('#sel_prio').value if self.query_one('#sel_prio').value != 'X' else ''}",
    #         ]
    #     )
    #
    #     # Execute and refresh
    #     subprocess.run(cmd)
    #     self.set_modify_mode(False)
    #     self.refresh_tasks()
    #     self.query_one(DataTable).focus()
    #
    def action_cancel_edit(self):
        self.set_modify_mode(False)
        self.query_one(DataTable).focus()


def run():
    TaskProApp().run()


if __name__ == "__main__":
    run()

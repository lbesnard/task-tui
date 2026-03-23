import json
import subprocess
import re
import os
import sys
import argparse
from copy import deepcopy
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Input,
    Label,
    Select,
)
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from .screens import QuickMenuScreen, DependencyListScreen, FuzzySearchScreen
from .utils import get_project_color, get_priority_color, format_urgency
from .models import load_pending_tasks, sync_tasks
from .config import DEFAULT_CONFIG, load_app_config


def check_taskwarrior_installed() -> bool:
    """Check if Taskwarrior is installed and accessible."""
    try:
        subprocess.run(["task", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


class DependsInput(Input):
    def on_key(self, event) -> None:
        app = getattr(self, "app", None)
        if (
            app
            and getattr(self, "id", "") == "inp_dep"
            and getattr(app, "is_modifying", False)
            and hasattr(app, "_is_dependency_search_key")
            and app._is_dependency_search_key(event.key, event.character or "")
        ):
            app.action_fuzzy_find_dep()
            event.stop()
            return


class PrioritySelect(Select):
    """Select widget that accepts h/m/l/x as quick-pick keys in edit mode."""

    _KEY_MAP = {"h": "H", "m": "M", "l": "L", "x": "X"}

    def on_key(self, event) -> None:
        app = getattr(self, "app", None)
        if app and getattr(app, "is_modifying", False):
            value = self._KEY_MAP.get(event.key)
            if value is not None:
                self.value = value
                event.stop()


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

    KEY_BINDING_META = [
        ("global_search", "fuzzy_find", "Search", True),
        ("view_dependencies", "view_dependencies", "ViewDeps", True),
        ("undo", "undo", "Undo", True),
        ("toggle_selection", "toggle_selection", "Select", True),
        ("date_mode", "date_mode", "SetDate", True),
        ("prio_mode", "prio_mode", "SetPrio", True),
        ("edit_mode", "edit_mode", "Modify/Edit", True),
        ("new_task", "new_task", "New", True),
        ("save_task", "save_task", "Save", True),
        ("toggle_start", "toggle_start", "Start/Stop", True),
        ("mark_done", "mark_done", "Done", True),
        ("refresh_tasks", "refresh_tasks", "Refresh", True),
        ("cancel_edit", "cancel_edit", "Back", True),
        ("quit", "quit", "Quit", True),
        ("cursor_down", "cursor_down", "Down", False),
        ("cursor_up", "cursor_up", "Up", False),
        ("cursor_left", "cursor_left", "Left", False),
        ("cursor_right", "cursor_right", "Right", False),
        ("scroll_top", "scroll_top", "Top", False),
        ("scroll_bottom", "scroll_bottom", "Bottom", False),
    ]
    BINDINGS = []

    is_dirty = False

    def __init__(self, config=None):
        self.config = config or deepcopy(DEFAULT_CONFIG)
        self.shortcuts = self.config.get("shortcuts", {})
        self.BINDINGS = self._build_bindings()
        super().__init__()
        self.active_uuid = None
        self.selected_uuids = set()
        self.is_modifying = False
        self.sort_state = {"index": 5, "reverse": True}
        self.raw_tasks = []
        self.no_sync = False
        self.date_context = None

    def _build_bindings(self):
        default_shortcuts = DEFAULT_CONFIG.get("shortcuts", {})
        bindings = []
        for shortcut_key, action, label, show in self.KEY_BINDING_META:
            key = self.shortcuts.get(shortcut_key, default_shortcuts.get(shortcut_key))
            if key:
                bindings.append(Binding(key, action, label, show=show))
        return bindings

    def _dependency_search_keys(self):
        keys = self.shortcuts.get("dependency_search", ["/"])
        if isinstance(keys, str):
            return [keys]
        if isinstance(keys, list):
            return keys
        return ["/"]

    def _is_dependency_search_key(self, key: str, character: str = "") -> bool:
        configured = {str(k).strip().lower() for k in self._dependency_search_keys()}
        candidates = {str(key).strip().lower()}
        if character:
            candidates.add(str(character).strip().lower())
        if key == "slash":
            candidates.add("/")
        return any(candidate in configured for candidate in candidates)

    def _register_dynamic_bindings(self) -> None:
        for binding in self.BINDINGS:
            self.bind(binding.key, binding.action, description=binding.description, show=binding.show)
        self.refresh_bindings()

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
                yield Label("DEPENDS ON (/ to pick tasks)", classes="metadata")
                yield DependsInput(id="inp_dep", disabled=True)
                yield Label("TAGS", classes="metadata")
                yield Input(id="inp_tags", disabled=True)
                yield Label("PRIORITY  (h=High · m=Mid · l=Low · x=None)", classes="metadata")
                yield PrioritySelect(
                    [("High", "H"), ("Mid", "M"), ("Low", "L"), ("None", "X")],
                    id="sel_prio",
                    value="X",
                    disabled=True,  # Start disabled
                )
                yield Label("UUID", classes="metadata")
                yield Static("None", id="uuid_display")
        yield Static("DEBUG LOG", id="debug_panel")
        yield Footer()

    def on_mount(self) -> None:
        self._register_dynamic_bindings()
        if not self.config.get("ui", {}).get("show_debug_panel", True):
            self.query_one("#debug_panel").display = False
        self.refresh_tasks()

    def on_unmount(self) -> None:
        os.system("clear")
        if self.no_sync:
            print("✓ Task-TUI closed (sync skipped).")
            return
            
        print("Finalizing... Syncing with Taskwarrior server.")
        if sync_tasks():
            print("✅ Sync Done!")
        else:
            print("⚠️ Sync timed out or failed. Your changes are saved locally.")

    def on_key(self, event) -> None:
        focused_id = getattr(getattr(self, "focused", None), "id", None)
        if (
            self.is_modifying
            and focused_id == "inp_dep"
            and self._is_dependency_search_key(event.key, event.character or "")
        ):
            self.action_fuzzy_find_dep()
            event.stop()
            return

        if not self.is_modifying and len(event.character or "") == 1:
            matched = next(
                (b for b in self.BINDINGS
                 if b.key == event.key or b.key == (event.character or "")),
                None,
            )
            if matched is None:
                self.notify("Press [b]i[/b] to enter Edit Mode", severity="warning")
                event.stop()
                return
            # Textual dispatches bindings by event.key name (e.g. "slash"), but
            # config-defined keys are stored as characters (e.g. "/").  When they
            # differ we must call the action ourselves — Textual's dispatcher
            # won't find a match.
            if matched.key != event.key:
                action_method = getattr(self, f"action_{matched.action}", None)
                if action_method:
                    action_method()
                event.stop()
                return

        # 3. Specific Bound Actions (Shift+S, etc.)
        if event.key == "S":
            self.action_save_task()
            event.stop()
            return

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
            self.query_one("#mode_indicator").update(
                "✏️ MODIFYING [b][blink][yellow](UNSAVED)[/][/][/]"
            )

    def on_select_changed(self) -> None:
        if self.is_modifying:
            self.is_dirty = True

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
        try:
            result = subprocess.run(
                ["task", "rc.confirmation=off", "undo"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.refresh_tasks()
                self.notify("Last action undone")
            else:
                self.notify("No action to undo", severity="warning")
        except Exception as e:
            self.notify(f"Undo failed: {e}", severity="error")

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
            try:
                subprocess.run(["task", self.active_uuid, cmd], check=True)
                self.refresh_tasks()
                self.notify(f"Task {cmd}ped")
            except subprocess.CalledProcessError as e:
                self.notify(f"Failed to {cmd} task", severity="error")

    def action_mark_done(self):
        targets = (
            list(self.selected_uuids) if self.selected_uuids else [self.active_uuid]
        )
        targets = [uid for uid in targets if uid and uid != "NEW"]

        if not targets:
            return

        failed = []
        for uid in targets:
            try:
                subprocess.run(["task", uid, "done"], check=True)
            except subprocess.CalledProcessError:
                failed.append(uid)

        self.selected_uuids.clear()
        self.refresh_tasks()
        
        if not failed:
            self.notify(f"Completed {len(targets)} task(s)!")
        else:
            self.notify(
                f"Completed {len(targets) - len(failed)}/{len(targets)} tasks",
                severity="warning"
            )

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
                values = [
                    item.strip()
                    for item in current.split(",")
                    if item.strip() and item.strip() != "/"
                ]
                if selected_uuid not in values:
                    values.append(selected_uuid)
                self.query_one("#inp_dep").value = ", ".join(values)

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
        failed = []
        for uid in targets:
            if uid != "NEW":
                try:
                    subprocess.run(
                        ["task", uid, "modify", f"due:{date_str}"],
                        check=True,
                        capture_output=True
                    )
                except subprocess.CalledProcessError:
                    failed.append(uid)
        
        self.refresh_tasks()
        if failed:
            self.notify(f"Failed to update {len(failed)} task(s)", severity="warning")

    def apply_quick_prio(self, level):
        targets = (
            list(self.selected_uuids) if self.selected_uuids else [self.active_uuid]
        )
        failed = []
        for uid in targets:
            if uid != "NEW":
                try:
                    subprocess.run(
                        ["task", uid, "modify", f"priority:{level}"],
                        check=True,
                        capture_output=True
                    )
                except subprocess.CalledProcessError:
                    failed.append(uid)
        
        self.refresh_tasks()
        if failed:
            self.notify(f"Failed to update {len(failed)} task(s)", severity="warning")

    # --- DATA & TABLE ---
    def refresh_tasks(self) -> None:
        target_uuid = self.active_uuid
        self.raw_tasks = load_pending_tasks()
        self.update_table_view()
        if target_uuid and target_uuid != "NEW":
            table = self.query_one(DataTable)
            for idx, row_key in enumerate(table.rows):
                if row_key.value == target_uuid:
                    table.move_cursor(row=idx)
                    break

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

        for t in sorted_data:
            uuid = t.get("uuid")
            prio = t.get("priority", "X")
            prio_color = get_priority_color(prio)

            proj_name = t.get("project", "")
            proj_color = get_project_color(proj_name)
            urgency_val = t.get("urgency", 0)
            urgency_display = format_urgency(urgency_val)

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

    def action_cancel_edit(self):
        self.set_modify_mode(False)
        self.query_one(DataTable).focus()


def run():
    parser = argparse.ArgumentParser(
        description="Task-TUI: A modern TUI for Taskwarrior",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="For more information, visit: https://github.com/lbesnard/task-tui"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="task-tui 0.1.0"
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip automatic sync on startup and exit"
    )
    
    args = parser.parse_args()
    
    if not check_taskwarrior_installed():
        print("❌ Error: Taskwarrior is not installed or not in PATH.")
        print("Please install Taskwarrior: https://taskwarrior.org/download/")
        sys.exit(1)
    
    try:
        app_config = load_app_config()
        app = TaskProApp(config=app_config)
        app.no_sync = args.no_sync

        if not args.no_sync:
            print("Syncing with Taskwarrior server...")
            if sync_tasks():
                print("✅ Sync Done!")
            else:
                print("⚠️ Sync timed out or failed. Starting with local data.")

        app.run()
    except KeyboardInterrupt:
        print("\n✓ Task-TUI closed.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()

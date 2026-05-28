from __future__ import annotations

import argparse
import importlib.metadata
import os
import subprocess
import sys
from copy import deepcopy
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
)

from .config import DEFAULT_CONFIG, load_app_config
from .models import load_pending_tasks, sync_tasks
from .screens import (
    DependencyListScreen,
    ErrorModalScreen,
    FilterMenuScreen,
    FuzzySearchScreen,
    QuickMenuScreen,
)
from .screens.multi_select_filter import MultiSelectFilterScreen
from .state import AppState
from .utils import format_urgency, get_priority_color, get_project_color


def check_taskwarrior_installed() -> bool:
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
        ("filter_mode", "filter_mode", "Filter", True),
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
    BINDINGS: list[Binding] = []

    is_dirty = False

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or deepcopy(DEFAULT_CONFIG)
        self.shortcuts = self.config.get("shortcuts", {})
        self.BINDINGS = self._build_bindings()
        super().__init__()
        self.state = AppState()
        self.is_modifying = False
        self.no_sync = False

    # ------------------------------------------------------------------ #
    # State property shims (delegate to AppState for backward compat)
    # ------------------------------------------------------------------ #

    @property
    def raw_tasks(self) -> list[dict[str, Any]]:
        return self.state.raw_tasks

    @raw_tasks.setter
    def raw_tasks(self, value: list[dict[str, Any]]) -> None:
        self.state.raw_tasks = value

    @property
    def active_uuid(self) -> str | None:
        return self.state.active_uuid

    @active_uuid.setter
    def active_uuid(self, value: str | None) -> None:
        self.state.active_uuid = value

    @property
    def selected_uuids(self) -> set[str]:
        return self.state.selected_uuids

    @selected_uuids.setter
    def selected_uuids(self, value: set[str]) -> None:
        self.state.selected_uuids = value

    # ------------------------------------------------------------------ #
    # Bindings
    # ------------------------------------------------------------------ #

    def _build_bindings(self) -> list[Binding]:
        defaults = DEFAULT_CONFIG.get("shortcuts", {})
        return [
            Binding(
                self.shortcuts.get(sk, defaults.get(sk)),
                action,
                label,
                show=show,
            )
            for sk, action, label, show in self.KEY_BINDING_META
            if self.shortcuts.get(sk, defaults.get(sk))
        ]

    def _dependency_search_keys(self) -> list[str]:
        keys = self.shortcuts.get("dependency_search", ["/"])
        if isinstance(keys, str):
            return [keys]
        return list(keys) if isinstance(keys, list) else ["/"]

    def _is_dependency_search_key(self, key: str, character: str = "") -> bool:
        configured = {str(k).strip().lower() for k in self._dependency_search_keys()}
        candidates = {str(key).strip().lower()}
        if character:
            candidates.add(str(character).strip().lower())
        if key == "slash":
            candidates.add("/")
        return bool(candidates & configured)

    def _register_dynamic_bindings(self) -> None:
        for b in self.BINDINGS:
            self.bind(b.key, b.action, description=b.description, show=b.show)
        self.refresh_bindings()

    # ------------------------------------------------------------------ #
    # Compose & lifecycle
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="context_bar")
        with Horizontal(id="workspace"):
            yield DataTable(id="list_panel", cursor_type="row")
            with Vertical(id="editor_panel", classes="view_mode"):
                yield Static("🔒 VIEWING", id="mode_indicator")
                yield Label("DESCRIPTION", classes="metadata")
                yield Input(id="inp_desc", disabled=True)
                yield Label("PROJECT", classes="metadata")
                yield Input(id="inp_proj", disabled=True)
                yield Label(
                    "DUE (YYYYMMDD or e.g. 'tomorrow', 'eo[d,m,y]')", classes="metadata"
                )
                yield Input(id="inp_due", disabled=True)
                yield Label("DEPENDS ON (/ to pick tasks)", classes="metadata")
                yield DependsInput(id="inp_dep", disabled=True)
                yield Label("TAGS", classes="metadata")
                yield Input(id="inp_tags", disabled=True)
                yield Label(
                    "PRIORITY  (h=High · m=Mid · l=Low · x=None)", classes="metadata"
                )
                yield PrioritySelect(
                    [("High", "H"), ("Mid", "M"), ("Low", "L"), ("None", "X")],
                    id="sel_prio",
                    value="X",
                    disabled=True,
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

    # ------------------------------------------------------------------ #
    # Key handling
    # ------------------------------------------------------------------ #

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
                (b for b in self.BINDINGS if b.key in (event.key, event.character or "")),
                None,
            )
            if matched is None:
                self.notify("Press [b]i[/b] to enter Edit Mode", severity="warning")
                event.stop()
                return
            if matched.key != event.key:
                action_method = getattr(self, f"action_{matched.action}", None)
                if action_method:
                    action_method()
                event.stop()
                return

        if event.key == "S":
            self.action_save_task()
            event.stop()

    # ------------------------------------------------------------------ #
    # App actions
    # ------------------------------------------------------------------ #

    def action_quit(self) -> None:
        if self.is_dirty:
            self.notify(
                "⚠️ UNSAVED CHANGES! Save with x or discard with Ctrl+Z before quitting.",
                severity="error",
            )
        else:
            self.exit()

    def action_refresh_tasks(self) -> None:
        self.refresh_tasks()

    def action_undo(self) -> None:
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

    # ------------------------------------------------------------------ #
    # Cursor actions
    # ------------------------------------------------------------------ #

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_cursor_left(self) -> None:
        self.query_one(DataTable).action_cursor_left()

    def action_cursor_right(self) -> None:
        self.query_one(DataTable).action_cursor_right()

    def action_scroll_top(self) -> None:
        table = self.query_one(DataTable)
        table.scroll_home()
        table.move_cursor(row=0)

    def action_scroll_bottom(self) -> None:
        table = self.query_one(DataTable)
        table.scroll_end()
        table.move_cursor(row=len(self.state.raw_tasks) - 1)

    # ------------------------------------------------------------------ #
    # Task actions
    # ------------------------------------------------------------------ #

    def action_view_dependencies(self) -> None:
        uuid = self.state.active_uuid
        if not uuid or uuid == "NEW":
            return
        task = self.state.get_task_by_uuid(uuid)
        if task and "depends" in task:
            def on_jump(uuid: str | None) -> None:
                if uuid:
                    self._move_cursor_to_uuid(uuid)

            self.push_screen(
                DependencyListScreen(task["depends"], self.state.raw_tasks), on_jump
            )

    def action_new_task(self) -> None:
        self.set_modify_mode(True)
        self.state.active_uuid = "NEW"
        for field in ["#inp_desc", "#inp_proj", "#inp_due", "#inp_dep", "#inp_tags"]:
            self.query_one(field).value = ""
        self.query_one("#uuid_display").update("NEW TASK")
        self.query_one("#inp_desc").focus()

    def action_toggle_start(self) -> None:
        uuid = self.state.active_uuid
        if not uuid or uuid == "NEW":
            return
        task = self.state.get_task_by_uuid(uuid)
        if task:
            cmd = "stop" if task.get("start") else "start"
            try:
                subprocess.run(["task", uuid, cmd], check=True)
                self.refresh_tasks()
                self.notify(f"Task {cmd}ped")
            except subprocess.CalledProcessError:
                self.notify(f"Failed to {cmd} task", severity="error")

    def action_mark_done(self) -> None:
        targets = (
            list(self.state.selected_uuids)
            if self.state.selected_uuids
            else [self.state.active_uuid]
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

        self.state.selected_uuids.clear()
        self.refresh_tasks()
        if failed:
            self.notify(
                f"Completed {len(targets) - len(failed)}/{len(targets)} tasks",
                severity="warning",
            )
        else:
            self.notify(f"Completed {len(targets)} task(s)!")

    def action_toggle_selection(self) -> None:
        uuid = self.state.active_uuid
        if uuid and uuid != "NEW":
            if uuid in self.state.selected_uuids:
                self.state.selected_uuids.discard(uuid)
            else:
                self.state.selected_uuids.add(uuid)
            self.update_table_view()

    # ------------------------------------------------------------------ #
    # Fuzzy search
    # ------------------------------------------------------------------ #

    def action_fuzzy_find(self) -> None:
        def on_select(uuid: str | None) -> None:
            if uuid:
                self.load_task_by_uuid(uuid, focus=False)
                self._move_cursor_to_uuid(uuid)

        self.push_screen(FuzzySearchScreen(self.state.raw_tasks), on_select)

    def action_fuzzy_find_dep(self) -> None:
        def on_select(selected_uuid: str | None) -> None:
            if selected_uuid:
                current = self.query_one("#inp_dep").value
                values = [
                    v.strip()
                    for v in current.split(",")
                    if v.strip() and v.strip() != "/"
                ]
                if selected_uuid not in values:
                    values.append(selected_uuid)
                self.query_one("#inp_dep").value = ", ".join(values)

        self.push_screen(FuzzySearchScreen(self.state.raw_tasks), on_select)

    # ------------------------------------------------------------------ #
    # Date / priority quick menus
    # ------------------------------------------------------------------ #

    def action_date_mode(self) -> None:
        def handle(result: str | None) -> None:
            if result == "end_of":
                def handle_end_of(r: str | None) -> None:
                    if r == "back_to_main":
                        self.action_date_mode()
                    elif r is not None:
                        self.apply_quick_date(r)
                self.push_screen(QuickMenuScreen("end_of"), handle_end_of)
            elif result is not None:
                self.apply_quick_date(result)

        self.push_screen(QuickMenuScreen("main"), handle)

    def action_prio_mode(self) -> None:
        def handle(result: str | None) -> None:
            if result is not None:
                self.apply_quick_prio(result)

        self.push_screen(QuickMenuScreen("priority"), handle)

    def action_filter_mode(self) -> None:
        def handle(result: str | None) -> None:
            if result == "project":
                self._open_project_filter()
            elif result == "tag":
                self._open_tag_filter()

        self.push_screen(FilterMenuScreen(), handle)

    def _open_project_filter(self) -> None:
        all_projects = self.state.get_all_projects()
        if not all_projects:
            self.notify("No projects found in tasks", severity="warning")
            return
        current = self.state.project_filter or all_projects
        selected = set(current)
        if self.state.show_unassigned_tasks:
            selected.add("__unassigned__")

        def on_done(result: set[str] | None) -> None:
            if result is not None:
                self.state.set_project_filter(result)
                self.update_table_view()

        self.push_screen(
            MultiSelectFilterScreen(
                title="FILTER BY PROJECT",
                all_items=sorted(all_projects),
                selected_items=selected,
                sentinel_key="__unassigned__",
                sentinel_label="Unassigned",
            ),
            on_done,
        )

    def _open_tag_filter(self) -> None:
        all_tags = self.state.get_all_tags()
        if not all_tags:
            self.notify("No tags found in tasks", severity="warning")
            return
        current = self.state.tag_filter or all_tags
        selected = set(current)
        if self.state.show_untagged_tasks:
            selected.add("__untagged__")

        def on_done(result: set[str] | None) -> None:
            if result is not None:
                self.state.set_tag_filter(result)
                self.update_table_view()

        self.push_screen(
            MultiSelectFilterScreen(
                title="FILTER BY TAG",
                all_items=sorted(all_tags),
                selected_items=selected,
                sentinel_key="__untagged__",
                sentinel_label="Untagged",
            ),
            on_done,
        )

    def apply_quick_date(self, date_str: str) -> None:
        targets = (
            list(self.state.selected_uuids)
            if self.state.selected_uuids
            else [self.state.active_uuid]
        )
        failed = []
        for uid in targets:
            if uid and uid != "NEW":
                try:
                    subprocess.run(
                        ["task", uid, "modify", f"due:{date_str}"],
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    failed.append(uid)
        self.refresh_tasks()
        if failed:
            self.notify(f"Failed to update {len(failed)} task(s)", severity="warning")

    def apply_quick_prio(self, level: str) -> None:
        targets = (
            list(self.state.selected_uuids)
            if self.state.selected_uuids
            else [self.state.active_uuid]
        )
        failed = []
        for uid in targets:
            if uid and uid != "NEW":
                try:
                    subprocess.run(
                        ["task", uid, "modify", f"priority:{level}"],
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    failed.append(uid)
        self.refresh_tasks()
        if failed:
            self.notify(f"Failed to update {len(failed)} task(s)", severity="warning")

    # ------------------------------------------------------------------ #
    # Data & table
    # ------------------------------------------------------------------ #

    def refresh_tasks(self) -> None:
        target_uuid = self.state.active_uuid
        self.state.raw_tasks = load_pending_tasks()
        self.state.init_filters_if_empty()
        self.update_table_view()
        if target_uuid and target_uuid != "NEW":
            self._move_cursor_to_uuid(target_uuid)

    def update_table_view(self) -> None:
        table = self.query_one(DataTable)
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
        sort_idx = self.state.sort_state["index"]
        sort_rev = self.state.sort_state["reverse"]
        for i, (label, _) in enumerate(cols):
            icon = " 🔽" if i == sort_idx and sort_rev else " 🔼" if i == sort_idx else ""
            table.add_column(f"{label}{icon}", key=cols[i][1])

        for t in self.state.get_visible_tasks():
            uuid = t.get("uuid")
            prio = t.get("priority", "X")
            proj_name = t.get("project", "")
            urgency_val = t.get("urgency", 0)

            is_active = "▸ " if t.get("start") else "  "
            prefix = "⭐ " if uuid in self.state.selected_uuids else is_active
            dep_icon = "🔗 " if t.get("depends") else ""

            table.add_row(
                f"{prefix}{t.get('id')}",
                f"[{get_project_color(proj_name)}]{proj_name}[/]",
                f"[{get_priority_color(prio)}]{prio}[/]",
                (t.get("due", "") or "")[:8],
                ",".join(t.get("tags") or []),
                format_urgency(urgency_val),
                f"{dep_icon}{t.get('description', '')}",
                key=uuid,
            )

        if table.row_count > 0:
            new_row = min(saved_cursor_row, table.row_count - 1)
            table.move_cursor(row=new_row)
            table.scroll_to(x=saved_scroll_x, y=saved_scroll_y, animate=False)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        if self.state.sort_state["index"] == event.column_index:
            self.state.sort_state["reverse"] = not self.state.sort_state["reverse"]
        else:
            self.state.sort_state["index"] = event.column_index
            self.state.sort_state["reverse"] = False
        self.update_table_view()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if self.is_dirty:
            self.notify(
                "⚠️ Save (x) or Discard (Ctrl+Z) before switching tasks!",
                severity="error",
            )
            return
        if event.row_key:
            self.load_task_by_uuid(event.row_key.value, focus=True)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self.is_dirty:
            return
        if not self.is_modifying and event.row_key:
            self.load_task_by_uuid(event.row_key.value, focus=False)

    def on_descendant_focus(self, event) -> None:
        if isinstance(event.control, DataTable) and self.is_dirty:
            self.notify(
                "⚠️ UNSAVED CHANGES! Press 'x' to save or 'Ctrl+Z' to discard.",
                severity="warning",
                timeout=3,
            )

    def on_input_changed(self) -> None:
        if self.is_modifying:
            self.is_dirty = True
            self.query_one("#mode_indicator").update(
                "✏️ MODIFYING [b][blink][yellow](UNSAVED)[/][/][/]"
            )

    def on_select_changed(self) -> None:
        if self.is_modifying:
            self.is_dirty = True

    # ------------------------------------------------------------------ #
    # Edit mode
    # ------------------------------------------------------------------ #

    def load_task_by_uuid(self, uuid: str, focus: bool = True) -> None:
        task = self.state.get_task_by_uuid(uuid)
        if not task:
            return
        self.state.active_uuid = uuid
        self.query_one("#uuid_display").update(uuid)
        self.query_one("#inp_desc").value = task.get("description", "")
        self.query_one("#inp_proj").value = task.get("project", "")
        due_date = (task.get("due", "") or "").replace("Z", "")[:8]
        self.query_one("#inp_due").value = due_date
        self.query_one("#inp_tags").value = ",".join(task.get("tags") or [])
        self.query_one("#inp_dep").value = ", ".join(map(str, task.get("depends") or []))
        self.query_one("#sel_prio").value = task.get("priority", "X")
        if focus:
            self.set_modify_mode(True)
            self.query_one("#inp_desc").focus()
        else:
            self.set_modify_mode(False)

    def set_modify_mode(self, active: bool) -> None:
        self.is_modifying = active
        self.is_dirty = False
        panel = self.query_one("#editor_panel")
        indicator = self.query_one("#mode_indicator")

        for node in self.query("Input, Select, TextArea"):
            node.disabled = not active
            if active and hasattr(node, "read_only"):
                node.read_only = False

        if active:
            panel.remove_class("view_mode")
            panel.add_class("edit_mode")
            indicator.update("✏️ MODIFYING")
        else:
            panel.remove_class("edit_mode")
            panel.add_class("view_mode")
            indicator.update("🔒 VIEWING")
            self.query_one(DataTable).focus()

    def action_edit_mode(self) -> None:
        if self.state.active_uuid:
            self.load_task_by_uuid(self.state.active_uuid, focus=True)

    def action_save_task(self) -> None:
        if not self.state.active_uuid:
            return

        dep_raw = self.query_one("#inp_dep").value.strip()
        dep_val = ",".join(d.strip() for d in dep_raw.split(",") if d.strip())

        target = "add" if self.state.active_uuid == "NEW" else self.state.active_uuid
        cmd = ["task", target]
        if self.state.active_uuid != "NEW":
            cmd.append("modify")

        due_val = self.query_one("#inp_due").value.strip()
        if due_val.isdigit() and len(due_val) == 8:
            due_val += "T000000"

        prio_widget = self.query_one("#sel_prio")
        prio_val = prio_widget.value if prio_widget.value != "X" else ""

        cmd.extend([
            f"description:{self.query_one('#inp_desc').value}",
            f"project:{self.query_one('#inp_proj').value}",
            f"due:{due_val}",
            f"tags:{self.query_one('#inp_tags').value}",
            f"depends:{dep_val}",
            f"priority:{prio_val}",
        ])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            self.query_one("#debug_panel").update(f"❌ ERROR: {error_msg}")
            self.push_screen(ErrorModalScreen(error_msg))
        else:
            self.query_one("#debug_panel").update(f"✅ Saved: {target}")
            self.set_modify_mode(False)
            self.refresh_tasks()
            self.query_one(DataTable).focus()
            self.notify("Saved!")

    def action_cancel_edit(self) -> None:
        self.set_modify_mode(False)
        self.query_one(DataTable).focus()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _move_cursor_to_uuid(self, uuid: str) -> None:
        table = self.query_one(DataTable)
        for idx, row_key in enumerate(table.rows):
            if row_key.value == uuid:
                table.move_cursor(row=idx)
                break


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #

def run() -> None:
    parser = argparse.ArgumentParser(
        description="Task-TUI: A modern TUI for Taskwarrior",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="For more information, visit: https://github.com/lbesnard/task-tui",
    )
    try:
        version = importlib.metadata.version("task-tui")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    parser.add_argument("--version", action="version", version=f"task-tui {version}")
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip automatic sync on startup and exit",
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

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, Select, Static


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


class TaskEditor(Vertical):
    """Layout of the task edit panel; field ids are queried by TaskProApp."""

    def compose(self) -> ComposeResult:
        yield Static("🔒 VIEWING", id="mode_indicator")
        yield Label("DESCRIPTION", classes="metadata")
        yield Input(id="inp_desc", disabled=True)
        yield Label("PROJECT", classes="metadata")
        yield Input(id="inp_proj", disabled=True)
        yield Label("DUE (YYYYMMDD or e.g. 'tomorrow', 'eo[d,m,y]')", classes="metadata")
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
            disabled=True,
        )
        yield Label("UUID", classes="metadata")
        yield Static("None", id="uuid_display")

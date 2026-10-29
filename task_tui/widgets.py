from __future__ import annotations

from textual.widgets import Input, Select


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

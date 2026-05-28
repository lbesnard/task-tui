from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AppState:
    """Owns RawTasks and all derived view state.

    Call get_visible_tasks() to obtain the sorted and filtered list of Tasks
    ready to render — the single pipeline that was previously inlined inside
    update_table_view().
    """

    raw_tasks: list[dict[str, Any]] = field(default_factory=list)
    active_uuid: str | None = None
    selected_uuids: set[str] = field(default_factory=set)
    sort_state: dict[str, Any] = field(default_factory=lambda: {"index": 5, "reverse": True})

    # Filter state
    project_filter: set[str] = field(default_factory=set)
    tag_filter: set[str] = field(default_factory=set)
    is_project_filter_active: bool = False
    is_tag_filter_active: bool = False
    show_unassigned_tasks: bool = False
    show_untagged_tasks: bool = False

    # ------------------------------------------------------------------ #
    # Derived data helpers
    # ------------------------------------------------------------------ #

    def get_all_projects(self) -> set[str]:
        """Return every unique project name present in RawTasks."""
        return {t.get("project", "") for t in self.raw_tasks if t.get("project")}

    def get_all_tags(self) -> set[str]:
        """Return every unique tag present in RawTasks."""
        tags: set[str] = set()
        for t in self.raw_tasks:
            tags.update(t.get("tags") or [])
        return tags

    def get_task_by_uuid(self, uuid: str) -> dict[str, Any] | None:
        return next((t for t in self.raw_tasks if t.get("uuid") == uuid), None)

    # ------------------------------------------------------------------ #
    # Filter mutators
    # ------------------------------------------------------------------ #

    def set_project_filter(self, selected: set[str]) -> None:
        """Apply a project filter selection returned by MultiSelectFilterScreen."""
        self.show_unassigned_tasks = "__unassigned__" in selected
        real = {p for p in selected if not p.startswith("__")}
        if real:
            self.project_filter = self._expand_projects_hierarchically(real)
        else:
            self.project_filter = set()
        self.is_project_filter_active = True

    def set_tag_filter(self, selected: set[str]) -> None:
        """Apply a tag filter selection returned by MultiSelectFilterScreen."""
        self.show_untagged_tasks = "__untagged__" in selected
        self.tag_filter = {t for t in selected if not t.startswith("__")}
        self.is_tag_filter_active = True

    def clear_filters(self) -> None:
        self.project_filter = set()
        self.tag_filter = set()
        self.is_project_filter_active = False
        self.is_tag_filter_active = False
        self.show_unassigned_tasks = False
        self.show_untagged_tasks = False

    # ------------------------------------------------------------------ #
    # Initialise filter sets from current RawTasks (called after load)
    # ------------------------------------------------------------------ #

    def init_filters_if_empty(self) -> None:
        """Seed filter sets from RawTasks on first load without activating them."""
        if not self.project_filter:
            self.project_filter = self.get_all_projects()
            self.is_project_filter_active = False
        if not self.tag_filter:
            self.tag_filter = self.get_all_tags()
            self.is_tag_filter_active = False

    # ------------------------------------------------------------------ #
    # VisibleTasks pipeline
    # ------------------------------------------------------------------ #

    def get_visible_tasks(self) -> list[dict[str, Any]]:
        """Return the sorted and filtered subset of RawTasks to render."""
        cols = [
            ("id", "id"),
            ("Proj.", "project"),
            ("P.", "priority"),
            ("Due", "due"),
            ("Tags", "tags"),
            ("Urg.", "urgency"),
            ("Desc.", "description"),
        ]
        sort_key = cols[self.sort_state["index"]][1]

        sorted_tasks = sorted(
            self.raw_tasks,
            key=lambda t: self._sort_value(t, sort_key),
            reverse=True if sort_key == "priority" else self.sort_state["reverse"],
        )

        if self.is_project_filter_active:
            sorted_tasks = [
                t for t in sorted_tasks if self._passes_project_filter(t)
            ]

        if self.is_tag_filter_active:
            sorted_tasks = [
                t for t in sorted_tasks if self._passes_tag_filter(t)
            ]

        return sorted_tasks

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _sort_value(self, task: dict[str, Any], sort_key: str) -> Any:
        val = task.get(sort_key, "")
        if sort_key == "urgency":
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0
        if sort_key == "priority":
            return {"H": 3, "M": 2, "L": 1, "X": 0, "": 0}.get(val, 0)
        return str(val).lower()

    def _passes_project_filter(self, task: dict[str, Any]) -> bool:
        project = task.get("project") or ""
        if not project:
            return self.show_unassigned_tasks
        return project in self.project_filter

    def _passes_tag_filter(self, task: dict[str, Any]) -> bool:
        task_tags = set(task.get("tags") or [])
        if not task_tags:
            return self.show_untagged_tasks
        return bool(task_tags & self.tag_filter)

    def _expand_projects_hierarchically(self, selected: set[str]) -> set[str]:
        """Add all child projects (e.g. 'Work.BAU') for each selected parent."""
        all_projects = self.get_all_projects()
        expanded = set(selected)
        for project in selected:
            prefix = project + "."
            expanded.update(p for p in all_projects if p.startswith(prefix))
        return expanded

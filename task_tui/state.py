from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .columns import COLUMN_LABELS, COUNT_COLUMNS, DEFAULT_COLUMNS
from .models.task import Report

# (header label, task field) for the default table columns, in display order
COLUMNS: list[tuple[str, str]] = [(COLUMN_LABELS[k], k) for k in DEFAULT_COLUMNS]


def sort_state_from_report(
    sort_spec: str, columns: list[tuple[str, str]] | None = None
) -> dict[str, Any] | None:
    """Translate the first key of a Taskwarrior sort spec (e.g. ``urgency-``).

    Returns None when the key is not one of the displayed ``columns`` (default:
    the default columns), so the current sort is kept. ``-`` means descending,
    which is ``reverse=True`` here.
    """
    first = sort_spec.split(",")[0].strip().rstrip("/")
    if not first or first[-1] not in "+-":
        return None
    keys = [key for _, key in (columns or COLUMNS)]
    name = first[:-1]
    if name not in keys:
        return None
    return {"index": keys.index(name), "reverse": first[-1] == "-"}


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
    columns: list[tuple[str, str]] = field(default_factory=lambda: list(COLUMNS))

    # Active Taskwarrior report; None means "all pending tasks"
    report: Report | None = None

    # Filter state
    project_filter: set[str] = field(default_factory=set)
    tag_filter: set[str] = field(default_factory=set)
    is_project_filter_active: bool = False
    is_tag_filter_active: bool = False
    show_unassigned_tasks: bool = False
    show_untagged_tasks: bool = False

    def set_columns(self, keys: list[str]) -> None:
        """Choose the displayed columns, keeping the current sort column if shown.

        If the sorted column is no longer displayed, falls back to the first one.
        """
        old_key = self.columns[self.sort_state["index"]][1]
        self.columns = [(COLUMN_LABELS[k], k) for k in keys]
        names = [k for k in keys]
        if old_key in names:
            self.sort_state["index"] = names.index(old_key)
        else:
            self.sort_state = {"index": 0, "reverse": False}

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
        sort_key = self.columns[self.sort_state["index"]][1]

        # Priority ranks High first by default, so its direction is inverted
        reverse = self.sort_state["reverse"]
        if sort_key == "priority":
            reverse = not reverse

        sorted_tasks = sorted(
            self.raw_tasks,
            key=lambda t: self._sort_value(t, sort_key),
            reverse=reverse,
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
        if sort_key in COUNT_COLUMNS:
            return len(val) if val else 0
        if sort_key in ("urgency", "id"):
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

"""Table columns that can be shown in the task list."""

from __future__ import annotations

from typing import Any

# column key (a Taskwarrior attribute, or a derived value) -> header label
COLUMN_LABELS: dict[str, str] = {
    "id": "ID",
    "project": "Proj.",
    "priority": "P.",
    "due": "Due",
    "tags": "Tags",
    "urgency": "Urg.",
    "description": "Desc.",
    "scheduled": "Sched.",
    "wait": "Wait",
    "entry": "Added",
    "modified": "Modified",
    "start": "Started",
    "recur": "Recur",
    "annotations": "Notes",
    "depends": "Deps",
    "status": "Status",
}

DEFAULT_COLUMNS: list[str] = [
    "id",
    "project",
    "priority",
    "due",
    "tags",
    "urgency",
    "description",
]

DATE_COLUMNS = {"due", "scheduled", "wait", "entry", "modified", "start"}
COUNT_COLUMNS = {"annotations", "depends"}


def normalize_columns(value: Any) -> list[str]:
    """Validate a ``ui.columns`` setting.

    Unknown and repeated names are dropped, order is kept, and an empty or
    invalid setting falls back to the default columns.
    """
    if not isinstance(value, list):
        return list(DEFAULT_COLUMNS)
    seen: list[str] = []
    for item in value:
        name = str(item).strip().lower()
        if name in COLUMN_LABELS and name not in seen:
            seen.append(name)
    return seen or list(DEFAULT_COLUMNS)


def cell_text(task: dict[str, Any], key: str) -> str:
    """Plain-text value of a task for the given column (no markup)."""
    value = task.get(key)
    if key in DATE_COLUMNS:
        return (value or "")[:8]
    if key == "tags":
        return ",".join(value or [])
    if key in COUNT_COLUMNS:
        return str(len(value)) if value else ""
    if value is None:
        return ""
    return str(value)

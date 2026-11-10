"""Table columns that can be shown in the task list."""

from __future__ import annotations

from datetime import datetime, timezone
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


def local_stamp(value: str | None, keep_time: bool = False) -> str:
    """Taskwarrior UTC stamp (``YYYYMMDDTHHMMSSZ``) -> local ``YYYYMMDD``.

    Taskwarrior exports dates in UTC; cutting the stamp shows the UTC day,
    which east of Greenwich is one day early for local midnight. With
    ``keep_time`` a time other than local midnight is kept
    (``YYYYMMDDTHHMMSS``, local) so a form round trip does not move it.
    Anything unparsable falls back to the first eight characters.
    """
    if not value:
        return ""
    try:
        local = (
            datetime.strptime(value, "%Y%m%dT%H%M%SZ")
            .replace(tzinfo=timezone.utc)
            .astimezone()
        )
    except ValueError:
        return value.replace("Z", "")[:8]
    if keep_time and (local.hour, local.minute, local.second) != (0, 0, 0):
        return local.strftime("%Y%m%dT%H%M%S")
    return local.strftime("%Y%m%d")


def cell_text(task: dict[str, Any], key: str) -> str:
    """Plain-text value of a task for the given column (no markup)."""
    value = task.get(key)
    if key in DATE_COLUMNS:
        return local_stamp(value)
    if key == "tags":
        return ",".join(value or [])
    if key in COUNT_COLUMNS:
        return str(len(value)) if value else ""
    if value is None:
        return ""
    return str(value)

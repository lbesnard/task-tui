"""Pure helpers that turn edit-panel input into Taskwarrior field values."""

from __future__ import annotations


def normalize_due(raw: str) -> str:
    """Expand a bare YYYYMMDD into Taskwarrior's YYYYMMDDT000000; pass anything else through."""
    due = raw.strip()
    if due.isdigit() and len(due) == 8:
        return due + "T000000"
    return due


def split_dependencies(raw: str) -> list[str]:
    """Parse a comma-separated depends field, ignoring blanks and a stray '/'."""
    return [v.strip() for v in raw.split(",") if v.strip() and v.strip() != "/"]


def add_dependency(current: str, uuid: str) -> str:
    """Append ``uuid`` to a comma-separated depends field unless already present."""
    values = split_dependencies(current)
    if uuid not in values:
        values.append(uuid)
    return ", ".join(values)


def build_task_fields(
    *,
    description: str,
    project: str,
    due: str,
    tags: str,
    depends: str,
    priority: str,
) -> dict[str, str]:
    """Map raw edit-panel values to ``attr -> value`` for ``task add/modify``.

    The 'X' (None) priority maps to an empty value, which clears it.
    """
    return {
        "description": description,
        "project": project,
        "due": normalize_due(due),
        "tags": tags,
        "depends": ",".join(d.strip() for d in depends.split(",") if d.strip()),
        "priority": "" if priority == "X" else priority,
    }

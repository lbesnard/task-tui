"""Pure helpers that turn edit-panel input into Taskwarrior field values."""

from __future__ import annotations


# (menu label, Taskwarrior recurrence value) shown after ticking "Recurring"
RECUR_PRESETS: list[tuple[str, str]] = [
    ("Daily", "daily"),
    ("Weekdays (Mon-Fri)", "weekdays"),
    ("Weekly", "weekly"),
    ("Every 2 weeks", "biweekly"),
    ("Monthly", "monthly"),
    ("Quarterly", "quarterly"),
    ("Every 6 months", "semiannual"),
    ("Yearly", "yearly"),
    ("Custom...", "__custom__"),
]
CUSTOM_RECUR = "__custom__"
DEFAULT_RECUR = "weekly"


def resolve_recur(enabled: bool, preset: str, custom: str) -> str:
    """Turn the recurrence widgets into a ``recur`` value ('' = not recurring)."""
    if not enabled:
        return ""
    if preset == CUSTOM_RECUR:
        return custom.strip()
    return preset


def split_recur(value: str | None) -> tuple[bool, str, str]:
    """Inverse of resolve_recur: returns (enabled, preset, custom_text)."""
    value = (value or "").strip()
    if not value:
        return False, DEFAULT_RECUR, ""
    if value in {v for _, v in RECUR_PRESETS if v != CUSTOM_RECUR}:
        return True, value, ""
    return True, CUSTOM_RECUR, value


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
    wait: str = "",
    recur: str | None = None,
) -> dict[str, str]:
    """Map raw edit-panel values to ``attr -> value`` for ``task add/modify``.

    The 'X' (None) priority maps to an empty value, which clears it.
    """
    fields = {
        "description": description,
        "project": project,
        "due": normalize_due(due),
        "tags": tags,
        "depends": ",".join(d.strip() for d in depends.split(",") if d.strip()),
        "priority": "" if priority == "X" else priority,
        "wait": normalize_due(wait),
    }
    # Only sent when the caller decided it changed: Taskwarrior refuses to
    # clear (or sometimes even re-set) the recurrence of a recurring task.
    if recur is not None:
        fields["recur"] = recur
    return fields


def format_annotations(annotations: list[dict] | None) -> str:
    """Render a task's annotations as one ``YYYY-MM-DD  text`` line each."""
    lines = []
    for note in annotations or []:
        entry = str(note.get("entry", ""))
        date = f"{entry[:4]}-{entry[4:6]}-{entry[6:8]}" if len(entry) >= 8 else "          "
        lines.append(f"{date}  {note.get('description', '')}")
    return "\n".join(lines) if lines else "(none)"

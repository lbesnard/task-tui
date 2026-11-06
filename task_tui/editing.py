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


def _flat(text: str) -> str:
    """Collapse whitespace/newlines so a multi-line note fits on one line."""
    return " ".join(str(text).split())


def annotation_lines(annotations: list[dict] | None) -> str:
    """Notes as editable text: one note per line, oldest first."""
    return "\n".join(_flat(n.get("description", "")) for n in annotations or [])


def diff_annotations(
    annotations: list[dict] | None, edited: str
) -> tuple[list[str], list[str]]:
    """Work out which notes to remove and add after the notes field was edited.

    Taskwarrior cannot edit a note in place, so a changed line is a removal of
    the old text plus an addition of the new one. Unchanged lines are left
    alone, which keeps their original timestamps.

    Returns ``(to_remove, to_add)``. ``to_remove`` holds the notes' original
    stored text (needed to denotate multi-line notes); ``to_add`` holds new text.
    """
    originals: dict[str, list[str]] = {}
    for note in annotations or []:
        text = note.get("description", "")
        originals.setdefault(_flat(text), []).append(text)

    wanted: dict[str, int] = {}
    order: list[str] = []
    for line in edited.splitlines():
        line = _flat(line)
        if line:
            wanted[line] = wanted.get(line, 0) + 1
            order.append(line)

    to_remove: list[str] = []
    for flat, texts in originals.items():
        surplus = len(texts) - wanted.get(flat, 0)
        if surplus > 0:
            to_remove.extend(texts[:surplus])

    to_add: list[str] = []
    for line in order:
        have = len(originals.get(line, []))
        if have > 0:
            originals[line] = originals[line][1:]
        else:
            to_add.append(line)
    return to_remove, to_add

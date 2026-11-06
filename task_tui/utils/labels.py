from __future__ import annotations

from typing import Any


def format_task_label(task: dict[str, Any]) -> str:
    """One-line 'id - description (project)' label used by task picker screens."""
    return (
        f"{task.get('id')} - {task.get('description', '')} "
        f"[dim]({task.get('project', '')})[/dim]"
    )


def is_waiting(task: dict, now: str | None = None) -> bool:
    """True when the task is hidden until a wait date that has not passed yet.

    Dates are Taskwarrior UTC stamps (``YYYYMMDDTHHMMSSZ``), which sort
    correctly as strings. ``now`` can be passed in for testing.
    """
    from datetime import datetime, timezone

    wait = task.get("wait")
    if not wait:
        return False
    current = now or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return str(wait) > current

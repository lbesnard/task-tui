from __future__ import annotations

from typing import Any


def format_task_label(task: dict[str, Any]) -> str:
    """One-line 'id - description (project)' label used by task picker screens."""
    return (
        f"{task.get('id')} - {task.get('description', '')} "
        f"[dim]({task.get('project', '')})[/dim]"
    )

"""Taskwarrior write commands.

Every function here shells out to the ``task`` CLI with TASK_TIMEOUT. The
helpers that report success/failure treat a timeout like any other failure.
"""

from __future__ import annotations

import subprocess
from typing import Mapping

from .task import TASK_TIMEOUT

TASK_FAILURES = (subprocess.CalledProcessError, subprocess.TimeoutExpired)


def undo_last_action() -> bool:
    """Run ``task undo``. Returns False when there was nothing to undo."""
    result = subprocess.run(
        ["task", "rc.confirmation=off", "undo"],
        capture_output=True,
        text=True,
        timeout=TASK_TIMEOUT,
    )
    return result.returncode == 0


def start_or_stop(uuid: str, stop: bool) -> None:
    """Start or stop a task. Raises one of TASK_FAILURES on failure."""
    subprocess.run(
        ["task", uuid, "stop" if stop else "start"], check=True, timeout=TASK_TIMEOUT
    )


def mark_done(uuid: str) -> None:
    """Complete a task. Raises one of TASK_FAILURES on failure."""
    subprocess.run(["task", uuid, "done"], check=True, timeout=TASK_TIMEOUT)


def modify_task(uuid: str, modification: str) -> None:
    """Apply a single ``attr:value`` modification. Raises one of TASK_FAILURES."""
    subprocess.run(
        ["task", uuid, "modify", modification],
        check=True,
        capture_output=True,
        timeout=TASK_TIMEOUT,
    )


def save_task(
    uuid: str | None, fields: Mapping[str, str]
) -> subprocess.CompletedProcess:
    """Add a new task (uuid=None) or modify an existing one with ``fields``.

    Never raises on failure: a non-zero returncode and the error text in
    stderr are returned instead, including for timeouts.
    """
    cmd = ["task", uuid or "add"]
    if uuid:
        cmd.append("modify")
    cmd.extend(f"{name}:{value}" for name, value in fields.items())

    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=TASK_TIMEOUT)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            cmd, 1, "", f"task timed out after {TASK_TIMEOUT}s"
        )

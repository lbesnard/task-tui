"""Taskwarrior write commands.

Every function here shells out to the ``task`` CLI with TASK_TIMEOUT. The
helpers that report success/failure treat a timeout like any other failure.
"""

from __future__ import annotations

import os
import subprocess
from typing import Mapping, Sequence

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


def delete_task(uuid: str) -> None:
    """Delete a task without the interactive prompt. Raises one of TASK_FAILURES."""
    subprocess.run(
        ["task", "rc.confirmation=off", uuid, "delete"],
        check=True,
        capture_output=True,
        timeout=TASK_TIMEOUT,
    )


def annotate_task(uuid: str, text: str) -> None:
    """Add an annotation. ``--`` keeps text like ``due:friday`` literal."""
    subprocess.run(
        ["task", uuid, "annotate", "--", text],
        check=True,
        capture_output=True,
        timeout=TASK_TIMEOUT,
    )


def denotate_task(uuid: str, text: str) -> None:
    """Remove the annotation with exactly this text. Raises one of TASK_FAILURES."""
    subprocess.run(
        ["task", "rc.confirmation=off", uuid, "denotate", "--", text],
        check=True,
        capture_output=True,
        timeout=TASK_TIMEOUT,
    )


def edit_in_editor(uuid: str, editor: str | None = None) -> int:
    """Run ``task <uuid> edit`` attached to the terminal; returns its exit code.

    ``editor`` overrides ``$VISUAL``/``$EDITOR`` for this call only. There is
    deliberately no timeout: the user is typing in the editor. The caller must
    hand the terminal over first (e.g. ``App.suspend``).
    """
    env = os.environ.copy()
    if editor:
        env["VISUAL"] = editor
        env["EDITOR"] = editor
    try:
        return subprocess.run(["task", uuid, "edit"], env=env).returncode
    except OSError:
        return 1


def modify_task(uuid: str, modification: str) -> None:
    """Apply a single ``attr:value`` modification. Raises one of TASK_FAILURES."""
    subprocess.run(
        ["task", uuid, "modify", modification],
        check=True,
        capture_output=True,
        timeout=TASK_TIMEOUT,
    )


def save_task(
    uuid: str | None,
    fields: Mapping[str, str],
    rc_overrides: Sequence[str] = (),
) -> subprocess.CompletedProcess:
    """Add a new task (uuid=None) or modify an existing one with ``fields``.

    ``rc_overrides`` are ``rc.name=value`` settings placed before the command.
    Never raises on failure: a non-zero returncode and the error text in
    stderr are returned instead, including for timeouts.
    """
    cmd = ["task", *rc_overrides, uuid or "add"]
    if uuid:
        cmd.append("modify")
    cmd.extend(f"{name}:{value}" for name, value in fields.items())

    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=TASK_TIMEOUT)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            cmd, 1, "", f"task timed out after {TASK_TIMEOUT}s"
        )

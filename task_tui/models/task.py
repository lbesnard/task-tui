from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

TASK_TIMEOUT = 30


@dataclass(frozen=True)
class Report:
    """A Taskwarrior report: a named filter + sort definition."""

    name: str
    filter: str = ""
    sort: str = ""


def list_reports() -> List[Report]:
    """Return the task-list reports defined in the user's Taskwarrior config.

    Only reports that define columns are returned, which excludes graphical
    reports such as ``burndown``. Returns [] if ``task`` cannot be queried.
    """
    try:
        res = subprocess.run(
            ["task", "_show"],
            capture_output=True,
            text=True,
            check=True,
            timeout=TASK_TIMEOUT,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return []

    settings: Dict[str, Dict[str, str]] = {}
    for line in res.stdout.splitlines():
        key, sep, value = line.partition("=")
        parts = key.split(".")
        if not sep or len(parts) != 3 or parts[0] != "report":
            continue
        settings.setdefault(parts[1], {})[parts[2]] = value.strip()

    return [
        Report(name, cfg.get("filter", ""), cfg.get("sort", ""))
        for name, cfg in sorted(settings.items())
        if "columns" in cfg
    ]


def report_filter_args(report_filter: str) -> List[str]:
    """Split a report filter into CLI args, dropping ``limit:`` terms.

    ``limit:page`` is meaningful for a terminal printout but not for a
    scrolling TUI list.
    """
    try:
        args = shlex.split(report_filter)
    except ValueError:
        args = report_filter.split()
    return [a for a in args if not a.startswith("limit:")]


def load_pending_tasks(
    on_error: Callable[[str], None] | None = None,
    report: Report | None = None,
) -> List[Dict[str, Any]]:
    """Load tasks from Taskwarrior.

    By default loads all pending tasks. When ``report`` is given, loads the
    tasks matched by that report's filter instead.

    Returns [] on failure; the reason is passed to ``on_error`` when given so
    callers can surface it instead of showing a silently empty list.
    """
    if report is None:
        cmd = ["task", "status:pending", "export", "rc.json.array=on"]
    else:
        cmd = ["task", *report_filter_args(report.filter), "export", "rc.json.array=on"]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=TASK_TIMEOUT,
        )
        return json.loads(res.stdout) if res.stdout else []
    except subprocess.CalledProcessError as e:
        reason = (e.stderr or "").strip() or f"task exited with status {e.returncode}"
    except subprocess.TimeoutExpired:
        reason = f"task export timed out after {TASK_TIMEOUT}s"
    except json.JSONDecodeError as e:
        reason = f"could not parse task export: {e}"
    except Exception as e:
        reason = str(e)
    if on_error:
        on_error(reason)
    return []


def sync_tasks(timeout: int = 10, capture: bool = False) -> bool:
    """Sync with Taskwarrior server. Returns True on success.

    ``capture=True`` swallows ``task sync`` output; use it while the TUI owns
    the screen so the output cannot be drawn over the interface.
    """
    try:
        extra = {"capture_output": True} if capture else {}
        subprocess.run(["task", "sync"], check=True, timeout=timeout, **extra)
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
        return False

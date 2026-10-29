from __future__ import annotations

import json
import subprocess
from typing import Any, Callable, Dict, List

TASK_TIMEOUT = 30


def load_pending_tasks(
    on_error: Callable[[str], None] | None = None,
) -> List[Dict[str, Any]]:
    """Load all pending tasks from Taskwarrior.

    Returns [] on failure; the reason is passed to ``on_error`` when given so
    callers can surface it instead of showing a silently empty list.
    """
    try:
        res = subprocess.run(
            ["task", "status:pending", "export", "rc.json.array=on"],
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


def sync_tasks(timeout: int = 10) -> bool:
    """Sync with Taskwarrior server. Returns True on success."""
    try:
        subprocess.run(["task", "sync"], check=True, timeout=timeout)
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False

import json
import subprocess
from typing import List, Dict, Any


def load_pending_tasks() -> List[Dict[str, Any]]:
    """Load all pending tasks from Taskwarrior."""
    try:
        res = subprocess.run(
            ["task", "status:pending", "export", "rc.json.array=on"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(res.stdout) if res.stdout else []
    except subprocess.CalledProcessError:
        return []
    except json.JSONDecodeError:
        return []
    except Exception:
        return []


def sync_tasks(timeout: int = 10) -> bool:
    """Sync with Taskwarrior server. Returns True on success."""
    try:
        subprocess.run(["task", "sync"], check=True, timeout=timeout)
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False

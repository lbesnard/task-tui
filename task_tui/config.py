import json
import os
from copy import deepcopy
from pathlib import Path


DEFAULT_CONFIG = {
    "shortcuts": {
        "global_search": "/",
        "dependency_search": "/",
        "view_dependencies": "v",
        "undo": "u",
        "toggle_selection": "space",
        "date_mode": "t",
        "prio_mode": "p",
        "edit_mode": "i",
        "new_task": "n",
        "save_task": "x",
        "toggle_start": "s",
        "mark_done": "d",
        "refresh_tasks": "r",
        "cancel_edit": "ctrl+z",
        "quit": "q",
        "cursor_down": "j",
        "cursor_up": "k",
        "cursor_left": "h",
        "cursor_right": "l",
        "scroll_top": "g",
        "scroll_bottom": "G",
    },
    "ui": {"show_debug_panel": True},
}


VALIDATED_SHORTCUT_KEYS = [
    "global_search",
    "view_dependencies",
    "undo",
    "toggle_selection",
    "date_mode",
    "prio_mode",
    "edit_mode",
    "new_task",
    "save_task",
    "toggle_start",
    "mark_done",
    "refresh_tasks",
    "cancel_edit",
    "quit",
    "cursor_down",
    "cursor_up",
    "cursor_left",
    "cursor_right",
    "scroll_top",
    "scroll_bottom",
]


def get_default_config_dir() -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "task-tui"
    return Path("~/.local/share/task-tui").expanduser()


def get_default_config_path() -> Path:
    return get_default_config_dir() / "config.json"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "YAML config requires PyYAML. Install it or use JSON config."
        ) from exc

    with path.open("r", encoding="utf-8") as f:
        loaded = yaml.safe_load(f)
    return loaded if isinstance(loaded, dict) else {}


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    return loaded if isinstance(loaded, dict) else {}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_config(config: dict) -> dict:
    normalized = deepcopy(config)
    shortcuts = normalized.get("shortcuts", {})
    dep_search = shortcuts.get("dependency_search", "/")

    if isinstance(dep_search, str):
        dep_search = [dep_search]
    if not isinstance(dep_search, list):
        dep_search = ["/"]

    dep_search = [str(key).strip() for key in dep_search if str(key).strip()]
    if not dep_search:
        dep_search = ["/"]
    shortcuts["dependency_search"] = dep_search
    normalized["shortcuts"] = shortcuts
    return normalized


def _validate_shortcut_duplicates(config: dict) -> None:
    shortcuts = config.get("shortcuts", {})
    seen = {}
    duplicates = {}

    for action in VALIDATED_SHORTCUT_KEYS:
        key = shortcuts.get(action)
        if not isinstance(key, str) or not key.strip():
            continue
        normalized_key = key.strip()
        if normalized_key in seen:
            duplicates.setdefault(normalized_key, [seen[normalized_key]]).append(action)
        else:
            seen[normalized_key] = action

    dep_search = shortcuts.get("dependency_search", [])
    if isinstance(dep_search, list):
        normalized_dep_keys = [str(k).strip() for k in dep_search if str(k).strip()]
        if len(set(normalized_dep_keys)) != len(normalized_dep_keys):
            raise ValueError("Duplicate keys found in shortcuts.dependency_search list.")

    if duplicates:
        details = "; ".join(
            f"'{key}' used by {', '.join(actions)}" for key, actions in sorted(duplicates.items())
        )
        raise ValueError(f"Duplicate shortcut keys are not allowed: {details}")


def _resolve_config_path() -> Path:
    explicit = os.environ.get("TASK_TUI_CONFIG")
    if explicit:
        return Path(explicit).expanduser()

    config_dir = get_default_config_dir()
    for name in ("config.yaml", "config.yml", "config.json"):
        candidate = config_dir / name
        if candidate.exists():
            return candidate
    return get_default_config_path()


def ensure_default_config() -> Path:
    config_path = _resolve_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
            f.write("\n")
    return config_path


def load_app_config() -> dict:
    config_path = ensure_default_config()
    if config_path.suffix in (".yaml", ".yml"):
        loaded = _load_yaml(config_path)
    else:
        loaded = _load_json(config_path)
    merged = _deep_merge(DEFAULT_CONFIG, loaded)
    normalized = _normalize_config(merged)
    _validate_shortcut_duplicates(normalized)

    if config_path.suffix == ".json" and loaded != normalized:
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2)
            f.write("\n")

    return normalized

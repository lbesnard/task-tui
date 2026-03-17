"""Tests for application config loading and defaults."""

import json

import pytest

from task_tui.config import (
    DEFAULT_CONFIG,
    ensure_default_config,
    get_default_config_path,
    load_app_config,
)


@pytest.mark.unit
class TestConfigLoading:
    def test_default_config_is_created(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

        config_path = ensure_default_config()

        assert config_path == get_default_config_path()
        assert config_path.exists()
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        assert loaded["shortcuts"]["global_search"] == DEFAULT_CONFIG["shortcuts"]["global_search"]
        assert loaded["shortcuts"]["cursor_up"] == "k"
        assert loaded["shortcuts"]["cursor_right"] == "l"

    def test_load_app_config_merges_user_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        config_path = get_default_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({"shortcuts": {"global_search": "ctrl+g", "dependency_search": "ctrl+f"}}),
            encoding="utf-8",
        )

        config = load_app_config()

        assert config["shortcuts"]["global_search"] == "ctrl+g"
        assert config["shortcuts"]["dependency_search"] == ["ctrl+f"]

    def test_load_app_config_backfills_missing_default_shortcuts(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        config_path = get_default_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"shortcuts": {"global_search": "ctrl+g"}}), encoding="utf-8")

        load_app_config()
        loaded = json.loads(config_path.read_text(encoding="utf-8"))

        assert loaded["shortcuts"]["cursor_up"] == "k"
        assert loaded["shortcuts"]["cursor_right"] == "l"

    def test_load_app_config_rejects_duplicate_shortcut_keys(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        config_path = get_default_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({"shortcuts": {"edit_mode": "i", "save_task": "i"}}),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Duplicate shortcut keys"):
            load_app_config()

"""Tests for configurable table columns."""
import json
from unittest.mock import Mock

import pytest

from task_tui.columns import (
    COLUMN_LABELS,
    DEFAULT_COLUMNS,
    cell_text,
    normalize_columns,
)
from task_tui.config import load_app_config
from task_tui.state import COLUMNS, AppState, sort_state_from_report


class TestNormalize:
    def test_valid_list_kept_in_order(self):
        assert normalize_columns(["description", "id"]) == ["description", "id"]

    def test_unknown_and_duplicates_dropped(self):
        assert normalize_columns(["id", "nope", "ID", "id", " due "]) == ["id", "due"]

    @pytest.mark.parametrize("bad", [None, [], ["nope"], "id", 5, {"a": 1}])
    def test_invalid_falls_back_to_default(self, bad):
        assert normalize_columns(bad) == DEFAULT_COLUMNS

    def test_default_is_a_copy(self):
        normalize_columns(None).append("x")
        assert "x" not in DEFAULT_COLUMNS

    def test_default_columns_are_known(self):
        assert all(k in COLUMN_LABELS for k in DEFAULT_COLUMNS)


class TestCellText:
    def test_dates_truncated(self):
        assert cell_text({"wait": "20261112T234433Z"}, "wait") == "20261112"
        assert cell_text({}, "due") == ""

    def test_tags_joined(self):
        assert cell_text({"tags": ["a", "b"]}, "tags") == "a,b"

    def test_counts(self):
        assert cell_text({"annotations": [{}, {}]}, "annotations") == "2"
        assert cell_text({"depends": ["u1"]}, "depends") == "1"
        assert cell_text({}, "annotations") == ""

    def test_plain_values(self):
        assert cell_text({"id": 7}, "id") == "7"
        assert cell_text({"recur": "weekly"}, "recur") == "weekly"
        assert cell_text({}, "status") == ""


class TestState:
    def test_default_columns_unchanged(self):
        assert [k for _, k in AppState().columns] == DEFAULT_COLUMNS
        assert [k for _, k in COLUMNS] == DEFAULT_COLUMNS

    def test_sort_follows_column_when_reordered(self):
        state = AppState()  # sorted by urgency, descending
        state.set_columns(["description", "urgency", "wait"])
        assert state.sort_state == {"index": 1, "reverse": True}

    def test_sort_resets_when_column_hidden(self):
        state = AppState()
        state.set_columns(["id", "description"])
        assert state.sort_state == {"index": 0, "reverse": False}

    def test_sorts_by_new_column(self):
        state = AppState(raw_tasks=[
            {"id": 1, "annotations": [{}]},
            {"id": 2, "annotations": [{}, {}, {}]},
            {"id": 3},
        ])
        state.set_columns(["id", "annotations"])
        state.sort_state = {"index": 1, "reverse": True}
        assert [t["id"] for t in state.get_visible_tasks()] == [2, 1, 3]

    def test_report_sort_uses_displayed_columns(self):
        columns = [(COLUMN_LABELS[k], k) for k in ["id", "entry"]]
        assert sort_state_from_report("entry-", columns) == {"index": 1, "reverse": True}
        assert sort_state_from_report("urgency-", columns) is None


class TestConfig:
    def _load(self, monkeypatch, tmp_path, ui):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"ui": ui}), encoding="utf-8")
        monkeypatch.setenv("TASK_TUI_CONFIG", str(path))
        return load_app_config(), path

    def test_default_in_config(self, monkeypatch, tmp_path):
        config, _ = self._load(monkeypatch, tmp_path, {})
        assert config["ui"]["columns"] == DEFAULT_COLUMNS

    def test_custom_columns_loaded_and_cleaned(self, monkeypatch, tmp_path):
        config, path = self._load(monkeypatch, tmp_path, {"columns": ["id", "bogus", "recur"]})
        assert config["ui"]["columns"] == ["id", "recur"]
        assert json.loads(path.read_text())["ui"]["columns"] == ["id", "recur"]


class TestTableRendering:
    def test_app_uses_configured_columns(self):
        from task_tui.app import TaskProApp

        app = TaskProApp(config={"shortcuts": {}, "ui": {"columns": ["description", "wait"]}})
        assert [k for _, k in app.state.columns] == ["description", "wait"]

    def test_render_cell_escapes_markup(self, sample_app):
        assert sample_app._render_cell({"description": "fix [bold]x"}, "description") == "fix \\[bold]x"
        assert sample_app._render_cell({"tags": ["[a]"]}, "tags") == "\\[a]"

    def test_render_cell_icons(self, sample_app):
        task = {"description": "d", "depends": ["u"], "recur": "weekly"}
        assert sample_app._render_cell(task, "description") == "🔗 🔁 d"

    def test_render_cell_priority_and_urgency(self, sample_app):
        assert "H" in sample_app._render_cell({"priority": "H"}, "priority")
        assert sample_app._render_cell({"urgency": 25}, "urgency")

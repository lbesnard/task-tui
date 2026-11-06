"""Tests for the pin-to-top (+next tag) action."""
from unittest.mock import Mock

import pytest


@pytest.fixture
def app(sample_app):
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    return sample_app


def _modifications(mock_run):
    return [c.args[0] for c in mock_run.call_args_list]


def test_pins_untagged_task(mock_subprocess_app, app):
    app.action_toggle_next()
    assert _modifications(mock_subprocess_app) == [["task", "abc-123", "modify", "+next"]]
    app.refresh_tasks.assert_called_once()
    assert "Pinned" in app.notify.call_args.args[0]


def test_unpins_task_that_has_the_tag(mock_subprocess_app, app):
    app.raw_tasks[0]["tags"] = ["work", "next"]
    app.action_toggle_next()
    assert _modifications(mock_subprocess_app) == [["task", "abc-123", "modify", "-next"]]
    assert app.notify.call_args.args[0] == "Unpinned"


def test_mixed_selection_pins_all(mock_subprocess_app, app):
    app.raw_tasks[0]["tags"] = ["next"]
    app.selected_uuids = {"abc-123", "def-456"}
    app.action_toggle_next()
    calls = _modifications(mock_subprocess_app)
    assert len(calls) == 2
    assert all(c[-1] == "+next" for c in calls)


def test_fully_pinned_selection_unpins_all(mock_subprocess_app, app):
    for t in app.raw_tasks:
        t["tags"] = ["next"]
    app.selected_uuids = {"abc-123", "def-456"}
    app.action_toggle_next()
    assert all(c[-1] == "-next" for c in _modifications(mock_subprocess_app))


@pytest.mark.parametrize("uuid", [None, "NEW"])
def test_no_target_is_noop(mock_subprocess_app, app, uuid):
    app.active_uuid = uuid
    app.action_toggle_next()
    mock_subprocess_app.assert_not_called()


def test_failure_warns(mock_subprocess_app, app):
    import subprocess

    mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
    app.action_toggle_next()
    assert app.notify.call_args.kwargs.get("severity") == "warning"


def test_pin_icon_shown(app):
    assert "📌" in app._render_cell({"description": "d", "tags": ["next"]}, "description")
    assert "📌" not in app._render_cell({"description": "d", "tags": ["x"]}, "description")

"""Tests for the manual sync action."""
import subprocess
from unittest.mock import Mock

import pytest


@pytest.fixture
def app(sample_app):
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    return sample_app


def test_sync_success_refreshes(mock_subprocess_app, app):
    app.action_sync()
    assert mock_subprocess_app.call_args.args[0] == ["task", "sync"]
    assert mock_subprocess_app.call_args.kwargs["timeout"] == 30
    app.refresh_tasks.assert_called_once()
    assert mock_subprocess_app.call_args.kwargs["capture_output"] is True
    assert app.notify.call_args.args[0] == "Sync done"


def test_sync_failure_reports_error(mock_subprocess_app, app):
    mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
    app.action_sync()
    app.refresh_tasks.assert_not_called()
    assert app.notify.call_args.kwargs.get("severity") == "error"


def test_sync_timeout_reports_error(mock_subprocess_app, app):
    mock_subprocess_app.side_effect = subprocess.TimeoutExpired("task", 30)
    app.action_sync()
    assert app.notify.call_args.kwargs.get("severity") == "error"


def test_sync_blocked_while_editing(mock_subprocess_app, app):
    app.is_dirty = True
    app.action_sync()
    mock_subprocess_app.assert_not_called()
    assert app.notify.call_args.kwargs.get("severity") == "warning"


def test_missing_binary_is_a_failed_sync(mock_subprocess):
    from task_tui.models.task import sync_tasks

    mock_subprocess.side_effect = FileNotFoundError
    assert sync_tasks() is False


def test_exit_sync_still_shows_output(mock_subprocess):
    from task_tui.models.task import sync_tasks

    sync_tasks()
    assert "capture_output" not in mock_subprocess.call_args.kwargs

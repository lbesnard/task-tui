"""Tests for the delete-task feature."""
import subprocess
from unittest.mock import Mock

import pytest

from task_tui.models import commands


def _confirm(app, answer):
    """Make push_screen immediately answer the confirmation modal."""
    app.push_screen = Mock(side_effect=lambda screen, cb: cb(answer))


class TestDeleteCommand:
    def test_command_line(self, mock_subprocess):
        commands.delete_task("abc-123")
        mock_subprocess.assert_called_once_with(
            ["task", "rc.confirmation=off", "abc-123", "delete"],
            check=True,
            capture_output=True,
            timeout=30,
        )

    def test_failure_raises(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        with pytest.raises(subprocess.CalledProcessError):
            commands.delete_task("abc-123")


class TestDeleteAction:
    @pytest.fixture
    def app(self, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        return sample_app

    def test_confirmed_deletes_active_task(self, mock_subprocess_app, app):
        _confirm(app, True)
        app.action_delete_task()
        mock_subprocess_app.assert_called_once()
        assert mock_subprocess_app.call_args.args[0] == [
            "task", "rc.confirmation=off", "abc-123", "delete",
        ]
        app.refresh_tasks.assert_called_once()

    def test_cancelled_does_nothing(self, mock_subprocess_app, app):
        _confirm(app, False)
        app.action_delete_task()
        mock_subprocess_app.assert_not_called()
        app.refresh_tasks.assert_not_called()

    def test_deletes_all_selected(self, mock_subprocess_app, app):
        app.selected_uuids = {"abc-123", "def-456"}
        _confirm(app, True)
        app.action_delete_task()
        deleted = {c.args[0][2] for c in mock_subprocess_app.call_args_list}
        assert deleted == {"abc-123", "def-456"}
        assert app.selected_uuids == set()

    def test_confirmation_lists_task_names(self, mock_subprocess_app, app):
        _confirm(app, False)
        app.action_delete_task()
        screen = app.push_screen.call_args.args[0]
        assert "Test task 1" in screen.body_text

    @pytest.mark.parametrize("uuid", [None, "NEW"])
    def test_no_target_skips_prompt(self, mock_subprocess_app, app, uuid):
        app.active_uuid = uuid
        _confirm(app, True)
        app.action_delete_task()
        app.push_screen.assert_not_called()
        mock_subprocess_app.assert_not_called()

    def test_failure_warns(self, mock_subprocess_app, app):
        mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
        _confirm(app, True)
        app.action_delete_task()
        assert app.notify.call_args.kwargs.get("severity") == "warning"

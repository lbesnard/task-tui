"""Tests for opening a task in $EDITOR."""
import os
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from task_tui.models import commands


class TestCommand:
    def test_no_override_keeps_environment(self, mock_subprocess, monkeypatch):
        monkeypatch.setenv("EDITOR", "vim")
        monkeypatch.delenv("VISUAL", raising=False)
        mock_subprocess.return_value = Mock(returncode=0)
        assert commands.edit_in_editor("abc") == 0
        assert mock_subprocess.call_args.args[0] == ["task", "abc", "edit"]
        env = mock_subprocess.call_args.kwargs["env"]
        assert env["EDITOR"] == "vim" and "VISUAL" not in env

    def test_override_sets_both_variables(self, mock_subprocess, monkeypatch):
        monkeypatch.setenv("VISUAL", "emacs")
        mock_subprocess.return_value = Mock(returncode=0)
        commands.edit_in_editor("abc", "nvim")
        env = mock_subprocess.call_args.kwargs["env"]
        assert env["VISUAL"] == "nvim" and env["EDITOR"] == "nvim"

    def test_does_not_leak_into_process_environment(self, mock_subprocess, monkeypatch):
        monkeypatch.setenv("EDITOR", "vim")
        mock_subprocess.return_value = Mock(returncode=0)
        commands.edit_in_editor("abc", "nvim")
        assert os.environ["EDITOR"] == "vim"

    def test_no_timeout_and_terminal_attached(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0)
        commands.edit_in_editor("abc")
        assert "timeout" not in mock_subprocess.call_args.kwargs
        assert "capture_output" not in mock_subprocess.call_args.kwargs

    def test_nonzero_exit_code_returned(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=3)
        assert commands.edit_in_editor("abc") == 3

    def test_missing_task_binary(self, mock_subprocess):
        mock_subprocess.side_effect = FileNotFoundError
        assert commands.edit_in_editor("abc") == 1


class TestAction:
    @pytest.fixture
    def app(self, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        order = []
        sample_app._order = order

        @contextmanager
        def suspend():
            order.append("suspend")
            yield
            order.append("resume")

        sample_app.suspend = suspend
        return sample_app

    def test_edits_active_task_then_refreshes(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0)
        app.action_edit_external()
        assert mock_subprocess_app.call_args.args[0] == ["task", "abc-123", "edit"]
        assert app._order == ["suspend", "resume"]
        app.refresh_tasks.assert_called_once()
        app.notify.assert_not_called()

    def test_config_editor_is_used(self, mock_subprocess_app, app):
        app.config = {"ui": {"editor": "nano"}}
        mock_subprocess_app.return_value = Mock(returncode=0)
        app.action_edit_external()
        assert mock_subprocess_app.call_args.kwargs["env"]["EDITOR"] == "nano"

    def test_error_exit_warns(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=1)
        app.action_edit_external()
        assert app.notify.call_args.kwargs.get("severity") == "warning"
        app.refresh_tasks.assert_called_once()

    def test_suspend_unsupported_reports_error(self, mock_subprocess_app, app):
        @contextmanager
        def broken():
            raise RuntimeError("no terminal")
            yield

        app.suspend = broken
        app.action_edit_external()
        mock_subprocess_app.assert_not_called()
        assert app.notify.call_args.kwargs.get("severity") == "error"

    @pytest.mark.parametrize("uuid", [None, "NEW"])
    def test_no_task_is_noop(self, mock_subprocess_app, app, uuid):
        app.active_uuid = uuid
        app.action_edit_external()
        mock_subprocess_app.assert_not_called()
        assert app._order == []

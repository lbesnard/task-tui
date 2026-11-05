"""Tests for annotation support."""
import subprocess
from unittest.mock import Mock

import pytest

from task_tui.editing import format_annotations
from task_tui.models import commands


class TestFormat:
    def test_empty(self):
        assert format_annotations(None) == "(none)"
        assert format_annotations([]) == "(none)"

    def test_lines(self):
        notes = [
            {"entry": "20261105T234313Z", "description": "first"},
            {"entry": "20261106T000000Z", "description": "second"},
        ]
        assert format_annotations(notes) == "2026-11-05  first\n2026-11-06  second"

    def test_missing_entry(self):
        assert format_annotations([{"description": "x"}]).endswith("x")


class TestCommands:
    def test_annotate_uses_literal_separator(self, mock_subprocess):
        commands.annotate_task("abc-123", "due:friday call")
        assert mock_subprocess.call_args.args[0] == [
            "task", "abc-123", "annotate", "--", "due:friday call",
        ]

    def test_denotate(self, mock_subprocess):
        commands.denotate_task("abc-123", "old")
        assert mock_subprocess.call_args.args[0] == [
            "task", "rc.confirmation=off", "abc-123", "denotate", "--", "old",
        ]

    def test_failure_raises(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        with pytest.raises(subprocess.CalledProcessError):
            commands.annotate_task("abc-123", "x")


class TestActions:
    @pytest.fixture
    def app(self, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        sample_app.raw_tasks[0]["annotations"] = [
            {"entry": "20261105T234313Z", "description": "keep"},
            {"entry": "20261105T234314Z", "description": "drop"},
        ]
        return sample_app

    def test_annotate_adds_note(self, mock_subprocess_app, app):
        app.push_screen = Mock(side_effect=lambda screen, cb: cb("remember this"))
        app.action_annotate()
        assert mock_subprocess_app.call_args.args[0] == [
            "task", "abc-123", "annotate", "--", "remember this",
        ]
        app.refresh_tasks.assert_called_once()

    def test_annotate_cancel(self, mock_subprocess_app, app):
        app.push_screen = Mock(side_effect=lambda screen, cb: cb(None))
        app.action_annotate()
        mock_subprocess_app.assert_not_called()

    @pytest.mark.parametrize("uuid", [None, "NEW"])
    def test_annotate_without_task(self, mock_subprocess_app, app, uuid):
        app.active_uuid = uuid
        app.push_screen = Mock()
        app.action_annotate()
        app.push_screen.assert_not_called()

    def test_denotate_removes_chosen_note(self, mock_subprocess_app, app):
        app.push_screen = Mock(side_effect=lambda screen, cb: cb("drop"))
        app.action_denotate()
        assert mock_subprocess_app.call_args.args[0][-1] == "drop"
        assert "denotate" in mock_subprocess_app.call_args.args[0]

    def test_denotate_without_notes_warns(self, mock_subprocess_app, app):
        app.active_uuid = "def-456"
        app.push_screen = Mock()
        app.action_denotate()
        app.push_screen.assert_not_called()
        assert app.notify.call_args.kwargs.get("severity") == "warning"

    def test_failure_reports_error(self, mock_subprocess_app, app):
        mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
        app.push_screen = Mock(side_effect=lambda screen, cb: cb("x"))
        app.action_annotate()
        assert app.notify.call_args.kwargs.get("severity") == "error"
        app.refresh_tasks.assert_not_called()

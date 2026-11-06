"""Tests for wait/snooze support."""
from unittest.mock import Mock

import pytest

from task_tui.editing import build_task_fields
from task_tui.screens.quick_menu import QuickMenuScreen
from task_tui.utils import is_waiting

FIELDS = dict(description="d", project="", due="", tags="", depends="", priority="X")


class TestIsWaiting:
    def test_future_wait(self):
        assert is_waiting({"wait": "20270101T000000Z"}, now="20261106T000000Z")

    def test_past_wait(self):
        assert not is_waiting({"wait": "20200101T000000Z"}, now="20261106T000000Z")

    def test_no_wait(self):
        assert not is_waiting({})
        assert not is_waiting({"wait": ""})

    def test_uses_current_time_by_default(self):
        assert is_waiting({"wait": "29990101T000000Z"})
        assert not is_waiting({"wait": "20000101T000000Z"})


class TestBuildFields:
    def test_wait_normalised_like_due(self):
        assert build_task_fields(**FIELDS, wait="20261110")["wait"] == "20261110T000000"

    def test_wait_relative_passes_through(self):
        assert build_task_fields(**FIELDS, wait="tomorrow")["wait"] == "tomorrow"

    def test_empty_wait_clears(self):
        assert build_task_fields(**FIELDS)["wait"] == ""


class TestSnoozeMenu:
    @pytest.mark.parametrize(
        "key,expected",
        [("t", "tomorrow"), ("m", "monday"), ("w", "1w"), ("e", "eom"), ("x", "")],
    )
    def test_keys(self, key, expected):
        screen = QuickMenuScreen("wait")
        screen.dismiss = Mock()
        screen.on_key(Mock(key=key))
        screen.dismiss.assert_called_once_with(expected)

    def test_escape_cancels(self):
        screen = QuickMenuScreen("wait")
        screen.dismiss = Mock()
        screen.on_key(Mock(key="escape"))
        screen.dismiss.assert_called_once_with(None)

    def test_unknown_key_ignored(self):
        screen = QuickMenuScreen("wait")
        screen.dismiss = Mock()
        screen.on_key(Mock(key="z"))
        screen.dismiss.assert_not_called()


class TestAction:
    def test_snooze_modifies_targets(self, mock_subprocess_app, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        sample_app.selected_uuids = {"abc-123"}
        sample_app.push_screen = Mock(side_effect=lambda screen, cb: cb("monday"))
        sample_app.action_wait_mode()
        assert mock_subprocess_app.call_args.args[0] == [
            "task", "abc-123", "modify", "wait:monday",
        ]

    def test_cancel_does_nothing(self, mock_subprocess_app, sample_app):
        sample_app.push_screen = Mock(side_effect=lambda screen, cb: cb(None))
        sample_app.action_wait_mode()
        mock_subprocess_app.assert_not_called()

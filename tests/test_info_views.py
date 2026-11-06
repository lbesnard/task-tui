"""Tests for the info/overview screen."""
import subprocess
from unittest.mock import Mock

import pytest

from task_tui.models import commands
from task_tui.screens.info_view import VIEWS, InfoViewScreen, views_bar


class TestRunInfoView:
    def test_command_line(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0, stdout="data\n", stderr="")
        assert commands.run_info_view("stats", 90) == "data"
        assert mock_subprocess.call_args.args[0] == [
            "task", "rc.color=off", "rc.defaultwidth=90", "rc.detection=off", "stats",
        ]
        assert mock_subprocess.call_args.kwargs["timeout"] == 30

    def test_strips_ansi_codes(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="\x1b[4mYear\x1b[0m Month\n", stderr=""
        )
        assert commands.run_info_view("history.monthly") == "Year Month"

    def test_error_text_when_no_output(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="boom\n")
        assert commands.run_info_view("stats") == "boom"

    def test_empty_output_message(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        assert "no output" in commands.run_info_view("tags")

    @pytest.mark.parametrize(
        "exc", [subprocess.TimeoutExpired("task", 30), FileNotFoundError("task")]
    )
    def test_failures_become_text(self, mock_subprocess, exc):
        mock_subprocess.side_effect = exc
        assert commands.run_info_view("stats").startswith("Could not run 'task stats'")


class TestScreen:
    def test_views_bar_marks_active(self):
        bar = views_bar("c")
        assert "[reverse] [b]c[/b] Calendar [/reverse]" in bar
        assert bar.count("[reverse]") == 1

    def test_every_view_key_is_in_bar(self):
        bar = views_bar("s")
        assert all(label in bar for label, _ in VIEWS.values())

    @pytest.fixture
    def screen(self):
        screen = InfoViewScreen()
        screen.load = Mock()
        screen.dismiss = Mock()
        screen.query_one = Mock()
        return screen

    @pytest.mark.parametrize("key", list(VIEWS))
    def test_view_keys_load(self, screen, key):
        screen.on_key(Mock(key=key))
        screen.load.assert_called_once_with(key)

    @pytest.mark.parametrize("key", ["escape", "q"])
    def test_close_keys(self, screen, key):
        screen.on_key(Mock(key=key))
        screen.dismiss.assert_called_once_with(None)

    def test_other_keys_pass_through(self, screen):
        event = Mock(key="z")
        screen.on_key(event)
        event.stop.assert_not_called()

    def test_stale_result_is_ignored(self, screen):
        screen.active = "m"
        screen._show("s", "old text")
        screen.query_one.assert_not_called()


def test_action_opens_screen(sample_app):
    sample_app.push_screen = Mock()
    sample_app.action_info_views()
    assert isinstance(sample_app.push_screen.call_args.args[0], InfoViewScreen)

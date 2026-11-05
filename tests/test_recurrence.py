"""Tests for recurrence support."""
from unittest.mock import Mock

import pytest

from task_tui.editing import (
    CUSTOM_RECUR,
    RECUR_PRESETS,
    build_task_fields,
    resolve_recur,
    split_recur,
)
from task_tui.models import commands

BASE = dict(description="d", project="", due="", tags="", depends="", priority="X")


class TestHelpers:
    def test_resolve_disabled(self):
        assert resolve_recur(False, "weekly", "") == ""

    def test_resolve_preset(self):
        assert resolve_recur(True, "monthly", "ignored") == "monthly"

    def test_resolve_custom(self):
        assert resolve_recur(True, CUSTOM_RECUR, " 3d ") == "3d"

    @pytest.mark.parametrize("value", [v for _, v in RECUR_PRESETS if v != CUSTOM_RECUR])
    def test_presets_round_trip(self, value):
        enabled, preset, custom = split_recur(value)
        assert (enabled, preset, custom) == (True, value, "")
        assert resolve_recur(enabled, preset, custom) == value

    def test_custom_round_trip(self):
        enabled, preset, custom = split_recur("3d")
        assert (enabled, preset, custom) == (True, CUSTOM_RECUR, "3d")
        assert resolve_recur(enabled, preset, custom) == "3d"

    @pytest.mark.parametrize("value", [None, "", "  "])
    def test_split_empty(self, value):
        assert split_recur(value)[0] is False

    def test_fields_omit_recur_by_default(self):
        assert "recur" not in build_task_fields(**BASE)

    def test_fields_include_recur_when_given(self):
        assert build_task_fields(**BASE, recur="weekly")["recur"] == "weekly"
        assert build_task_fields(**BASE, recur="")["recur"] == ""


class TestSaveCommand:
    def test_rc_overrides_precede_task(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0)
        commands.save_task("abc", {"recur": "daily"}, ["rc.recurrence.confirmation=yes"])
        assert mock_subprocess.call_args.args[0] == [
            "task", "rc.recurrence.confirmation=yes", "abc", "modify", "recur:daily",
        ]

    def test_no_overrides_unchanged(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0)
        commands.save_task(None, {"description": "x"})
        assert mock_subprocess.call_args.args[0] == ["task", "add", "description:x"]


class TestSaveAction:
    @pytest.fixture
    def app(self, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        sample_app.exit = Mock()
        sample_app.set_modify_mode = Mock()
        widgets = {
            "#inp_desc": Mock(value="d"), "#inp_proj": Mock(value=""),
            "#inp_due": Mock(value="20261110"), "#inp_wait": Mock(value=""),
            "#inp_dep": Mock(value=""), "#inp_tags": Mock(value=""),
            "#sel_prio": Mock(value="X"),
            "#chk_recur": Mock(value=False), "#sel_recur": Mock(value="weekly"),
            "#inp_recur": Mock(value=""),
            "#debug_panel": Mock(), "#mode_indicator": Mock(),
            "#editor_panel": Mock(), "#uuid_display": Mock(),
        }
        sample_app.query_one = Mock(side_effect=lambda sel: widgets.get(str(sel), Mock()))
        sample_app._widgets = widgets
        return sample_app

    def _cmd(self, mock_run):
        return mock_run.call_args.args[0]

    def test_new_recurring_task(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app.active_uuid = "NEW"
        app._widgets["#chk_recur"].value = True
        app.action_save_task()
        cmd = self._cmd(mock_subprocess_app)
        assert "recur:weekly" in cmd
        assert not any(a.startswith("rc.recurrence") for a in cmd)

    def test_new_non_recurring_omits_recur(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app.active_uuid = "NEW"
        app.action_save_task()
        assert not any(a.startswith("recur:") for a in self._cmd(mock_subprocess_app))

    def test_unchanged_recur_not_resent(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app.raw_tasks[0]["recur"] = "weekly"
        app._widgets["#chk_recur"].value = True
        app.action_save_task()
        assert not any(a.startswith("recur:") for a in self._cmd(mock_subprocess_app))

    def test_changed_recur_confirms_all_recurrences(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app.raw_tasks[0]["recur"] = "weekly"
        app._widgets["#chk_recur"].value = True
        app._widgets["#sel_recur"].value = "daily"
        app.action_save_task()
        cmd = self._cmd(mock_subprocess_app)
        assert "recur:daily" in cmd
        assert "rc.recurrence.confirmation=yes" in cmd

    def test_custom_recur(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app._widgets["#chk_recur"].value = True
        app._widgets["#sel_recur"].value = CUSTOM_RECUR
        app._widgets["#inp_recur"].value = "3d"
        app.action_save_task()
        assert "recur:3d" in self._cmd(mock_subprocess_app)

    def test_make_existing_task_recurring(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app._widgets["#chk_recur"].value = True
        app.action_save_task()
        assert "recur:weekly" in self._cmd(mock_subprocess_app)

    def test_cannot_remove_recurrence_of_recurring_task(self, mock_subprocess_app, app):
        app.raw_tasks[0].update(recur="weekly", parent="p-1")
        app.action_save_task()
        mock_subprocess_app.assert_not_called()
        assert app.notify.call_args.kwargs.get("severity") == "error"

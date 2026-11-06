"""Tests for annotation support."""
import subprocess
from unittest.mock import Mock

import pytest

from task_tui.editing import annotation_lines, diff_annotations
from task_tui.models import commands


class TestNoteLines:
    def test_empty(self):
        assert annotation_lines(None) == ""
        assert annotation_lines([]) == ""

    def test_one_note_per_line(self):
        notes = [{"description": "first"}, {"description": "second"}]
        assert annotation_lines(notes) == "first\nsecond"

    def test_multiline_note_is_flattened(self):
        assert annotation_lines([{"description": "a\n  b"}]) == "a b"


class TestDiff:
    NOTES = [{"description": "one"}, {"description": "two"}]

    def test_unchanged(self):
        assert diff_annotations(self.NOTES, "one\ntwo") == ([], [])

    def test_add(self):
        assert diff_annotations(self.NOTES, "one\ntwo\nthree") == ([], ["three"])

    def test_remove(self):
        assert diff_annotations(self.NOTES, "two") == (["one"], [])

    def test_edit_is_remove_plus_add(self):
        assert diff_annotations(self.NOTES, "one\ntwo!") == (["two"], ["two!"])

    def test_blank_lines_and_spaces_ignored(self):
        assert diff_annotations(self.NOTES, "\n one \n\n two  \n") == ([], [])

    def test_clear_all(self):
        assert diff_annotations(self.NOTES, "") == (["one", "two"], [])

    def test_new_task_has_no_existing_notes(self):
        assert diff_annotations(None, "a\nb") == ([], ["a", "b"])

    def test_duplicates_are_counted(self):
        notes = [{"description": "x"}, {"description": "x"}]
        assert diff_annotations(notes, "x") == (["x"], [])
        assert diff_annotations(notes, "x\nx\nx") == ([], ["x"])

    def test_multiline_note_unchanged_is_untouched(self):
        notes = [{"description": "a\nb"}]
        assert diff_annotations(notes, "a b") == ([], [])

    def test_multiline_note_removed_uses_original_text(self):
        notes = [{"description": "a\nb"}]
        assert diff_annotations(notes, "") == (["a\nb"], [])


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


class TestNotesOnSave:
    @pytest.fixture
    def app(self, sample_app):
        sample_app.refresh_tasks = Mock()
        sample_app.notify = Mock()
        sample_app.exit = Mock()
        sample_app.set_modify_mode = Mock()
        sample_app.raw_tasks[0]["annotations"] = [
            {"entry": "20261105T234313Z", "description": "keep"},
            {"entry": "20261105T234314Z", "description": "old"},
        ]
        widgets = {
            "#inp_desc": Mock(value="d"), "#inp_proj": Mock(value=""),
            "#inp_due": Mock(value=""), "#inp_wait": Mock(value=""),
            "#inp_dep": Mock(value=""), "#inp_tags": Mock(value=""),
            "#sel_prio": Mock(value="X"),
            "#chk_recur": Mock(value=False), "#sel_recur": Mock(value="weekly"),
            "#inp_recur": Mock(value=""),
            "#txt_notes": Mock(text="keep\nold"),
            "#debug_panel": Mock(), "#mode_indicator": Mock(),
            "#editor_panel": Mock(), "#uuid_display": Mock(),
        }
        sample_app.query_one = Mock(side_effect=lambda sel: widgets.get(str(sel), Mock()))
        sample_app._widgets = widgets
        return sample_app

    @staticmethod
    def _calls(mock_run):
        return [c.args[0] for c in mock_run.call_args_list]

    def test_unchanged_notes_cause_no_extra_commands(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app.action_save_task()
        assert len(mock_subprocess_app.call_args_list) == 1

    def test_edited_notes_are_applied_after_modify(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")
        app._widgets["#txt_notes"].text = "keep\nnew one"
        app.action_save_task()
        calls = self._calls(mock_subprocess_app)
        assert calls[0][:3] == ["task", "abc-123", "modify"]
        assert calls[1] == ["task", "rc.confirmation=off", "abc-123", "denotate", "--", "old"]
        assert calls[2] == ["task", "abc-123", "annotate", "--", "new one"]
        app.refresh_tasks.assert_called_once()

    def test_new_task_notes_go_to_latest_task(self, mock_subprocess_app, app):
        app.active_uuid = "NEW"
        app._widgets["#txt_notes"].text = "first note"

        def fake_run(cmd, **kwargs):
            if "_uuids" in cmd:
                return Mock(returncode=0, stdout="new-uuid\n", stderr="")
            return Mock(returncode=0, stdout="", stderr="")

        mock_subprocess_app.side_effect = fake_run
        app.action_save_task()
        calls = self._calls(mock_subprocess_app)
        assert calls[0][:2] == ["task", "add"]
        assert ["task", "rc.verbose=nothing", "+LATEST", "_uuids"] in calls
        assert calls[-1] == ["task", "new-uuid", "annotate", "--", "first note"]

    def test_modify_failure_skips_notes(self, mock_subprocess_app, app):
        mock_subprocess_app.return_value = Mock(returncode=1, stdout="", stderr="bad")
        app._widgets["#txt_notes"].text = "something else"
        app.push_screen = Mock()
        app.action_save_task()
        assert len(mock_subprocess_app.call_args_list) == 1
        app.push_screen.assert_called_once()

    def test_note_failure_opens_error_modal(self, mock_subprocess_app, app):
        def fake_run(cmd, **kwargs):
            if "annotate" in cmd:
                raise subprocess.CalledProcessError(1, "task")
            return Mock(returncode=0, stdout="", stderr="")

        mock_subprocess_app.side_effect = fake_run
        app._widgets["#txt_notes"].text = "keep\nold\nadded"
        app.push_screen = Mock()
        app.action_save_task()
        app.push_screen.assert_called_once()
        assert "notes failed" in app.push_screen.call_args.args[0].error_message


class TestLatestUuid:
    def test_returns_first_uuid(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0, stdout="u-1\n", stderr="")
        assert commands.latest_uuid() == "u-1"

    def test_none_when_empty_or_failing(self, mock_subprocess):
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")
        assert commands.latest_uuid() is None
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        assert commands.latest_uuid() is None

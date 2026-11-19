"""Changes to recurring tasks: ask in the TUI, never let ``task`` wait for input.

Taskwarrior asks "Do you want to modify all pending recurrences of this same
task?" on its terminal. Run from the TUI that question was invisible: the
command sat there until the timeout and the change was reported as failed.
"""
import subprocess
from unittest.mock import Mock

import pytest

from task_tui.models import commands
from task_tui.models.commands import RECUR_SERIES, RECUR_THIS
from task_tui.screens import ConfirmScreen, RecurrenceScopeScreen

SERIES = "rc.recurrence.confirmation=yes"
THIS = "rc.recurrence.confirmation=no"


class TestCommands:
    def test_overrides(self):
        assert commands.recurrence_overrides(RECUR_SERIES) == [SERIES]
        assert commands.recurrence_overrides(RECUR_THIS) == [THIS]

    @pytest.mark.parametrize(
        "call",
        [
            lambda: commands.undo_last_action(),
            lambda: commands.start_or_stop("abc", stop=False),
            lambda: commands.mark_done("abc"),
            lambda: commands.delete_task("abc"),
            lambda: commands.annotate_task("abc", "x"),
            lambda: commands.denotate_task("abc", "x"),
            lambda: commands.modify_task("abc", "priority:H"),
            lambda: commands.save_task("abc", {"description": "x"}),
            lambda: commands.recurrence_confirmation(),
        ],
    )
    def test_never_reads_the_terminal(self, mock_subprocess, call):
        call()
        assert mock_subprocess.call_args.kwargs["stdin"] is subprocess.DEVNULL

    def test_overrides_precede_the_filter(self, mock_subprocess):
        commands.delete_task("abc", [SERIES])
        assert mock_subprocess.call_args.args[0] == [
            "task", "rc.confirmation=off", SERIES, "abc", "delete",
        ]
        commands.annotate_task("abc", "note", [THIS])
        assert mock_subprocess.call_args.args[0] == ["task", THIS, "abc", "annotate", "--", "note"]
        commands.modify_task("abc", "priority:H", [THIS])
        assert mock_subprocess.call_args.args[0] == ["task", THIS, "abc", "modify", "priority:H"]

    def test_note_changes_pass_overrides_to_annotate_only(self, mock_subprocess):
        commands.apply_note_changes("abc", ["old"], ["new"], [SERIES])
        denotate, annotate = (c.args[0] for c in mock_subprocess.call_args_list)
        assert SERIES not in denotate
        assert annotate == ["task", SERIES, "abc", "annotate", "--", "new"]

    @pytest.mark.parametrize("stdout, expected", [("prompt\n", "prompt"), ("no\n", "no"), ("", "prompt")])
    def test_setting_is_read_from_taskwarrior(self, mock_subprocess, stdout, expected):
        mock_subprocess.return_value = Mock(returncode=0, stdout=stdout)
        assert commands.recurrence_confirmation() == expected
        assert mock_subprocess.call_args.args[0][-2:] == ["_get", "rc.recurrence.confirmation"]

    def test_setting_defaults_to_prompt_on_failure(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        assert commands.recurrence_confirmation() == "prompt"


class TestScreen:
    @pytest.mark.parametrize(
        "key, result",
        [("t", RECUR_THIS), ("enter", RECUR_THIS), ("a", RECUR_SERIES), ("n", None), ("escape", None)],
    )
    def test_keys(self, key, result):
        screen = RecurrenceScopeScreen()
        screen.dismiss = Mock()
        event = Mock(key=key)
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(result)
        event.stop.assert_called_once()

    def test_other_keys_are_ignored(self):
        screen = RecurrenceScopeScreen()
        screen.dismiss = Mock()
        screen.on_key(Mock(key="x"))
        screen.dismiss.assert_not_called()

    def test_wording_follows_the_action(self):
        assert RecurrenceScopeScreen().body_text.startswith("Apply the change to")
        assert RecurrenceScopeScreen(deleting=True).body_text.startswith("Delete")


def _answer(app, scope, confirm=True):
    """Answer the dialogs the app opens; returns the list of screens shown."""
    shown = []

    def push(screen, callback):
        shown.append(screen)
        if isinstance(screen, RecurrenceScopeScreen):
            callback(scope)
        elif isinstance(screen, ConfirmScreen):
            callback(confirm)
        else:  # AnnotateScreen
            callback("a note")

    app.push_screen = Mock(side_effect=push)
    return shown


def _task_calls(mock_run):
    """Commands that change tasks (the one-off read of the setting left out)."""
    return [c.args[0] for c in mock_run.call_args_list if "_get" not in c.args[0]]


@pytest.fixture
def app(sample_app):
    """The first task is an occurrence of a recurring task."""
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    sample_app.raw_tasks[0].update(parent="tmpl-000", recur="weekly")
    return sample_app


class TestQuickActions:
    @pytest.mark.parametrize("scope, override", [(RECUR_THIS, THIS), (RECUR_SERIES, SERIES)])
    def test_annotate_passes_the_answer(self, mock_subprocess_app, app, scope, override):
        shown = _answer(app, scope)
        app.action_annotate()
        assert isinstance(shown[-1], RecurrenceScopeScreen)
        assert _task_calls(mock_subprocess_app) == [
            ["task", override, "abc-123", "annotate", "--", "a note"]
        ]

    def test_cancel_changes_nothing(self, mock_subprocess_app, app):
        _answer(app, None)
        app.action_annotate()
        app.apply_quick_prio("H")
        app.action_toggle_next()
        app.action_delete_task()
        assert _task_calls(mock_subprocess_app) == []
        app.refresh_tasks.assert_not_called()

    def test_quick_modify(self, mock_subprocess_app, app):
        _answer(app, RECUR_SERIES)
        app.apply_quick_prio("H")
        assert _task_calls(mock_subprocess_app) == [
            ["task", SERIES, "abc-123", "modify", "priority:H"]
        ]

    def test_pin(self, mock_subprocess_app, app):
        _answer(app, RECUR_THIS)
        app.action_toggle_next()
        assert _task_calls(mock_subprocess_app) == [["task", THIS, "abc-123", "modify", "+next"]]

    def test_delete_asks_after_confirming(self, mock_subprocess_app, app):
        shown = _answer(app, RECUR_SERIES)
        app.action_delete_task()
        assert [type(s) for s in shown] == [ConfirmScreen, RecurrenceScopeScreen]
        assert shown[1].body_text.startswith("Delete")
        assert _task_calls(mock_subprocess_app) == [
            ["task", "rc.confirmation=off", SERIES, "abc-123", "delete"]
        ]

    def test_delete_not_confirmed_never_asks(self, mock_subprocess_app, app):
        shown = _answer(app, RECUR_SERIES, confirm=False)
        app.action_delete_task()
        assert [type(s) for s in shown] == [ConfirmScreen]
        assert _task_calls(mock_subprocess_app) == []

    def test_one_answer_covers_a_mixed_selection(self, mock_subprocess_app, app):
        app.selected_uuids = {"abc-123", "def-456"}
        shown = _answer(app, RECUR_THIS)
        app.apply_quick_prio("L")
        assert len(shown) == 1
        calls = _task_calls(mock_subprocess_app)
        assert len(calls) == 2 and all(THIS in c for c in calls)

    def test_plain_tasks_are_not_asked(self, mock_subprocess_app, app):
        app.active_uuid = "def-456"
        shown = _answer(app, RECUR_SERIES)
        app.apply_quick_prio("H")
        assert shown == []
        assert mock_subprocess_app.call_args_list[0].args[0] == [
            "task", "def-456", "modify", "priority:H",
        ]
        assert len(mock_subprocess_app.call_args_list) == 1  # setting not even read


class TestTaskrcAnswer:
    """A fixed ``recurrence.confirmation`` in taskrc is left to Taskwarrior."""

    @pytest.mark.parametrize("setting", ["no", "yes", "0", "on"])
    def test_no_dialog_and_no_override(self, mock_subprocess_app, app, setting):
        mock_subprocess_app.return_value = Mock(returncode=0, stdout=f"{setting}\n", stderr="")
        shown = _answer(app, RECUR_SERIES)
        app.apply_quick_prio("H")
        assert shown == []
        assert _task_calls(mock_subprocess_app) == [["task", "abc-123", "modify", "priority:H"]]

    def test_setting_is_read_once(self, mock_subprocess_app, app):
        _answer(app, RECUR_THIS)
        app.apply_quick_prio("H")
        app.apply_quick_prio("L")
        reads = [c for c in mock_subprocess_app.call_args_list if "_get" in c.args[0]]
        assert len(reads) == 1


class TestTemplates:
    @pytest.fixture
    def template(self, app):
        app.raw_tasks[0].pop("parent")
        app.raw_tasks[0]["status"] = "recurring"
        return app

    def test_modify_and_delete_ask(self, mock_subprocess_app, template):
        shown = _answer(template, RECUR_THIS)
        template.apply_quick_prio("H")
        template.action_delete_task()
        assert sum(isinstance(s, RecurrenceScopeScreen) for s in shown) == 2

    def test_annotate_does_not_ask(self, mock_subprocess_app, template):
        shown = _answer(template, RECUR_SERIES)
        template.action_annotate()
        assert not any(isinstance(s, RecurrenceScopeScreen) for s in shown)
        assert _task_calls(mock_subprocess_app) == [
            ["task", "abc-123", "annotate", "--", "a note"]
        ]


class TestSave:
    @pytest.fixture
    def form(self, app):
        app.exit = Mock()
        app.set_modify_mode = Mock()
        widgets = {
            "#inp_desc": Mock(value="d"), "#inp_proj": Mock(value=""),
            "#inp_due": Mock(value="20261122"), "#inp_wait": Mock(value=""), "#inp_until": Mock(value=""),
            "#inp_dep": Mock(value=""), "#inp_tags": Mock(value=""),
            "#sel_prio": Mock(value="X"), "#txt_notes": Mock(text="new line"),
            "#chk_recur": Mock(value=True), "#sel_recur": Mock(value="weekly"),
            "#inp_recur": Mock(value=""),
        }
        app.query_one = Mock(side_effect=lambda sel: widgets.get(str(sel), Mock()))
        app._widgets = widgets
        return app

    def test_one_answer_for_fields_and_notes(self, mock_subprocess_app, form):
        shown = _answer(form, RECUR_SERIES)
        form.action_save_task()
        assert len(shown) == 1
        modify, annotate = _task_calls(mock_subprocess_app)
        assert modify[:4] == ["task", SERIES, "abc-123", "modify"]
        assert annotate == ["task", SERIES, "abc-123", "annotate", "--", "new line"]

    def test_cancel_keeps_the_form_open(self, mock_subprocess_app, form):
        _answer(form, None)
        form.action_save_task()
        assert _task_calls(mock_subprocess_app) == []
        form.set_modify_mode.assert_not_called()

    def test_changed_recurrence_goes_to_the_series_without_asking(self, mock_subprocess_app, form):
        form._widgets["#sel_recur"].value = "daily"
        shown = _answer(form, RECUR_THIS)
        form.action_save_task()
        assert shown == []
        modify, annotate = _task_calls(mock_subprocess_app)
        assert SERIES in modify and "recur:daily" in modify
        assert SERIES in annotate

    def test_new_task_is_not_asked(self, mock_subprocess_app, form):
        form.active_uuid = "NEW"
        mock_subprocess_app.side_effect = lambda cmd, **kw: Mock(
            returncode=0, stdout="new-uuid\n" if "_uuids" in cmd else "", stderr=""
        )
        shown = _answer(form, RECUR_SERIES)
        form.action_save_task()
        assert shown == []
        assert not any("rc.recurrence.confirmation" in a for c in _task_calls(mock_subprocess_app) for a in c)

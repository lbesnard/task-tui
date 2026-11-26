"""Esc closes a dialog and goes no further; Back leaves a filter or a report.

Four dialogs dismissed themselves on Esc without stopping the key, so it
travelled on to the app's bindings. Harmless with the default shortcuts, but
with ``cancel_edit`` on ``escape`` closing the dependency picker also
discarded the task being edited.
"""
import asyncio
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from task_tui.app import TaskProApp
from task_tui.config import DEFAULT_CONFIG
from task_tui.models.task import Report
from task_tui.screens import (
    DependencyListScreen,
    FuzzySearchScreen,
    MultiSelectFilterScreen,
    ReportPickerScreen,
)

TASKS = [
    {"id": 1, "uuid": "u1", "description": "write exam", "project": "school.exams",
     "tags": ["exam"], "urgency": 9, "depends": ["u2"]},
    {"id": 2, "uuid": "u2", "description": "copy exam", "project": "school",
     "urgency": 5},
    {"id": 3, "uuid": "u3", "description": "buy milk", "urgency": 1},
]
REPORTS = [Report("week", "due.before:eow", "due+"), Report("next", "status:pending", "urgency-")]


def drive(scenario, tasks=TASKS, **overrides):
    """Run ``scenario(app, pilot)`` against a headless app with fake tasks."""
    config = deepcopy(DEFAULT_CONFIG)
    config["shortcuts"].update(overrides.pop("shortcuts", {}))
    config["ui"].update(overrides.pop("ui", {}))

    async def main():
        app = TaskProApp(config=config)
        app.no_sync = True
        async with app.run_test(size=(120, 40)) as pilot:
            await settle(app, pilot)
            await scenario(app, pilot)

    with patch("task_tui.app.load_pending_tasks", return_value=deepcopy(tasks)), patch(
        "task_tui.app.list_reports", return_value=list(REPORTS)
    ), patch("task_tui.app.sync_tasks"):
        asyncio.run(main())


async def settle(app, pilot):
    """Wait for the worker thread behind ``_run_blocking`` and the redraw."""
    for _ in range(100):
        await pilot.pause(0.02)
        if not app._busy:
            break
    await pilot.pause()


async def press(app, pilot, *keys):
    for key in keys:
        await pilot.press(key)
        await settle(app, pilot)


@pytest.mark.unit
class TestEscapeIsStopped:
    @pytest.mark.parametrize(
        "screen",
        [
            FuzzySearchScreen([]),
            ReportPickerScreen([], None),
            DependencyListScreen([], []),
            MultiSelectFilterScreen("FILTER BY PROJECT", [], set(), "__unassigned__", "Unassigned"),
        ],
        ids=lambda screen: type(screen).__name__,
    )
    def test_escape_dismisses_and_stops(self, screen):
        screen.dismiss = Mock()
        screen.query_one = Mock()  # not mounted
        event = Mock(key="escape")
        screen.on_key(event)
        screen.dismiss.assert_called_once()
        event.stop.assert_called_once()


@pytest.mark.unit
class TestEscapeStaysInTheDialog:
    def test_app_binding_on_escape_does_not_fire(self):
        dialogs = [
            (["slash"], FuzzySearchScreen),
            (["R"], ReportPickerScreen),
            (["v"], DependencyListScreen),
            (["f", "p"], MultiSelectFilterScreen),
            (["f", "t"], MultiSelectFilterScreen),
        ]

        async def scenario(app, pilot):
            for keys, screen in dialogs:
                await press(app, pilot, *keys)
                assert isinstance(app.screen, screen), keys
                with patch.object(TaskProApp, "action_cancel_edit") as cancel:
                    await press(app, pilot, "escape")
                assert not isinstance(app.screen, screen), keys
                cancel.assert_not_called()

        drive(scenario, shortcuts={"cancel_edit": "escape"})

    def test_dependency_picker_keeps_the_edit(self):
        async def scenario(app, pilot):
            await press(app, pilot, "i")
            app.query_one("#inp_desc").value = "write the exam"
            app.query_one("#inp_dep").focus()
            await press(app, pilot, "slash")
            assert isinstance(app.screen, FuzzySearchScreen)

            await press(app, pilot, "escape")

            assert not isinstance(app.screen, FuzzySearchScreen)
            assert app.is_modifying and app.is_dirty
            assert app.query_one("#inp_desc").value == "write the exam"
            assert app.query_one("#inp_dep").value == "u2"  # no "/" typed into it
            assert app.focused.id == "inp_dep"

        drive(scenario, shortcuts={"cancel_edit": "escape"})


# ---------------------------------------------------------------------------
# Back: cancel_edit outside Edit Mode
# ---------------------------------------------------------------------------

WEEK = Report("week", "due.before:eow", "due+")
NEXT = Report("next", "status:pending", "urgency-")


@pytest.fixture
def app(sample_app):
    sample_app.raw_tasks = deepcopy(TASKS)
    sample_app.refresh_tasks = Mock()
    sample_app.update_table_view = Mock()
    sample_app.notify = Mock()
    sample_app.set_modify_mode = Mock()
    sample_app.query_one = Mock()
    sample_app._update_subtitle = Mock()
    return sample_app


@pytest.mark.unit
class TestBack:
    def test_leaves_a_report_for_all_pending(self, app):
        app._select_report(WEEK)
        app.refresh_tasks.reset_mock()

        app.action_cancel_edit()

        assert app.state.report is None
        app.refresh_tasks.assert_called_once()

    def test_leaves_a_report_for_the_default_report(self, app):
        with patch("task_tui.app.list_reports", return_value=[WEEK, NEXT]):
            app.config["ui"]["default_report"] = "next"
            app._init_report()
        app._select_report(WEEK)

        app.action_cancel_edit()

        assert app.state.report == NEXT

    def test_unknown_default_report_means_all_pending(self, app):
        with patch("task_tui.app.list_reports", return_value=[WEEK]):
            app.config["ui"]["default_report"] = "gone"
            app._init_report()
        app._select_report(WEEK)

        app.action_cancel_edit()

        assert app.state.report is None

    @pytest.mark.parametrize("default", [None, "next"])
    def test_does_nothing_in_the_start_list(self, app, default):
        with patch("task_tui.app.list_reports", return_value=[WEEK, NEXT]):
            app.config["ui"]["default_report"] = default
            app._init_report()
        app.refresh_tasks.reset_mock()

        app.action_cancel_edit()

        assert app.state.report == (NEXT if default else None)
        app.refresh_tasks.assert_not_called()
        app.update_table_view.assert_not_called()
        app.notify.assert_not_called()

    @pytest.mark.parametrize("kind", ["project", "tag"])
    def test_clears_a_filter_before_leaving_the_report(self, app, kind):
        app._select_report(WEEK)
        app.refresh_tasks.reset_mock()
        if kind == "project":
            app.state.set_project_filter({"school"})
        else:
            app.state.set_tag_filter({"exam"})
        assert len(app.state.get_visible_tasks()) < len(TASKS)

        app.action_cancel_edit()

        assert len(app.state.get_visible_tasks()) == len(TASKS)
        assert not app.state.is_project_filter_active
        assert not app.state.is_tag_filter_active
        assert app.state.report == WEEK
        app.update_table_view.assert_called_once()
        app.notify.assert_called_once_with("Filter cleared")
        app.refresh_tasks.assert_not_called()

        app.action_cancel_edit()

        assert app.state.report is None
        app.refresh_tasks.assert_called_once()

    def test_clears_a_filter_in_the_start_list(self, app):
        app.state.set_tag_filter({"exam"})

        app.action_cancel_edit()

        assert len(app.state.get_visible_tasks()) == len(TASKS)
        app.refresh_tasks.assert_not_called()

    def test_filter_that_hides_nothing_is_not_a_step(self, app):
        """Applying the filter dialog with everything ticked hides no task."""
        app._select_report(WEEK)
        app.state.set_project_filter({"school", "__unassigned__"})
        assert len(app.state.get_visible_tasks()) == len(TASKS)

        app.action_cancel_edit()

        assert app.state.report is None
        assert not app.state.is_project_filter_active
        app.notify.assert_not_called()

    def test_discarding_an_edit_does_not_go_back(self, app):
        app._select_report(WEEK)
        app.state.set_tag_filter({"exam"})
        app.refresh_tasks.reset_mock()
        app.is_modifying = True

        app.action_cancel_edit()

        app.set_modify_mode.assert_called_once_with(False)
        assert app.state.report == WEEK
        assert app.state.is_tag_filter_active
        app.refresh_tasks.assert_not_called()


@pytest.mark.unit
class TestBackInTheRunningApp:
    def test_filter_then_report(self):
        async def scenario(app, pilot):
            notes = []
            app.notify = lambda message, **kwargs: notes.append(message)
            table = app.query_one("#list_panel")

            await press(app, pilot, "R", "w", "enter")
            assert app.sub_title == "Report: week"
            await press(app, pilot, "f", "t", "j", "j", "j", "enter", "escape")
            assert table.row_count == 0  # CLEAR ALL: no tag ticked, untagged not shown

            await press(app, pilot, "escape")
            assert table.row_count == len(TASKS)
            assert app.sub_title == "Report: week"

            await press(app, pilot, "ctrl+z")
            assert app.sub_title == "All pending"

            await press(app, pilot, "escape")
            assert app.sub_title == "All pending"
            assert notes == ["Filter cleared"]

        drive(scenario, shortcuts={"cancel_edit": "escape,ctrl+z"})

    def test_back_to_the_default_report(self):
        async def scenario(app, pilot):
            assert app.sub_title == "Report: next"
            await press(app, pilot, "R", "w", "enter")
            assert app.sub_title == "Report: week"

            await press(app, pilot, "escape")
            assert app.sub_title == "Report: next"

        drive(scenario, shortcuts={"cancel_edit": "escape"}, ui={"default_report": "next"})

    def test_closing_a_dialog_or_an_edit_keeps_the_report(self):
        async def scenario(app, pilot):
            await press(app, pilot, "R", "w", "enter")

            await press(app, pilot, "R", "escape")
            assert app.sub_title == "Report: week"

            await press(app, pilot, "i", "escape")
            assert not app.is_modifying
            assert app.sub_title == "Report: week"

        drive(scenario, shortcuts={"cancel_edit": "escape"})

"""Esc closes a dialog and goes no further.

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
            assert app.focused.id == "inp_dep"

        drive(scenario, shortcuts={"cancel_edit": "escape"})

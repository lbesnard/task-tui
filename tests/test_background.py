import asyncio
import threading
from unittest.mock import patch

import pytest

from task_tui.app import TaskProApp


@pytest.fixture
def running_app_env():
    tasks = [{"id": 1, "uuid": "u1", "description": "one", "urgency": 1}]
    with patch("task_tui.app.load_pending_tasks", return_value=tasks), patch(
        "task_tui.app.sync_tasks"
    ):
        yield


@pytest.mark.unit
def test_cli_call_runs_off_ui_thread_and_rejects_overlap(running_app_env):
    release = threading.Event()
    calls = []
    ui_thread = {}

    def slow_done(uuid):
        calls.append((uuid, threading.current_thread().name))
        release.wait(5)

    async def scenario():
        app = TaskProApp()
        app.no_sync = True
        notes = []
        async with app.run_test() as pilot:
            ui_thread["name"] = threading.current_thread().name
            app.notify = lambda msg, **kw: notes.append(msg)
            app.active_uuid = "u1"
            with patch("task_tui.app.commands.mark_done", side_effect=slow_done):
                app.action_mark_done()
                await pilot.pause()
                # UI still responsive while the job is blocked
                assert app._busy
                app.action_mark_done()
                await pilot.pause()
                assert any("Still working" in n for n in notes)
                release.set()
                for _ in range(50):
                    if not app._busy:
                        break
                    await pilot.pause(0.05)
            assert not app._busy
            assert any("Completed 1 task" in n for n in notes)

    asyncio.run(scenario())

    assert len(calls) == 1
    assert calls[0][1] != ui_thread["name"]

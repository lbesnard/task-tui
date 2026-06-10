"""Tests for screen components."""
import pytest
from unittest.mock import Mock
from task_tui.screens import QuickMenuScreen, FuzzySearchScreen, DependencyListScreen, ErrorModalScreen


@pytest.mark.unit
class TestQuickMenuScreen:
    def test_init_main_menu(self):
        screen = QuickMenuScreen("main")
        assert screen.menu_type == "main"

    def test_init_end_of_menu(self):
        screen = QuickMenuScreen("end_of")
        assert screen.menu_type == "end_of"

    def test_init_priority_menu(self):
        screen = QuickMenuScreen("priority")
        assert screen.menu_type == "priority"

    def test_main_menu_today_key(self):
        screen = QuickMenuScreen("main")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "n"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("today")
        event.stop.assert_called_once()

    def test_main_menu_tomorrow_key(self):
        screen = QuickMenuScreen("main")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "t"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("tomorrow")

    def test_main_menu_end_of_key(self):
        screen = QuickMenuScreen("main")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "e"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("end_of")

    def test_end_of_menu_week_key(self):
        screen = QuickMenuScreen("end_of")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "w"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("eow")

    def test_end_of_menu_month_key(self):
        screen = QuickMenuScreen("end_of")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "m"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("eom")

    def test_end_of_menu_year_key(self):
        screen = QuickMenuScreen("end_of")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "y"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("eoy")

    def test_priority_menu_high(self):
        screen = QuickMenuScreen("priority")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "h"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("H")

    def test_priority_menu_medium(self):
        screen = QuickMenuScreen("priority")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "m"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("M")

    def test_priority_menu_low(self):
        screen = QuickMenuScreen("priority")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "l"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("L")

    def test_priority_menu_clear(self):
        screen = QuickMenuScreen("priority")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "x"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("")

    def test_escape_dismisses_main(self):
        screen = QuickMenuScreen("main")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)

    def test_escape_goes_back_from_end_of(self):
        screen = QuickMenuScreen("end_of")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("back_to_main")

    def test_case_insensitive_keys(self):
        screen = QuickMenuScreen("main")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "N"  # Uppercase — .lower() normalises it
        screen.on_key(event)
        screen.dismiss.assert_called_once_with("today")


@pytest.mark.unit
class TestFuzzySearchScreen:
    """Tests for fuzzy search screen."""

    def test_init_stores_tasks(self):
        tasks = [{"uuid": "abc", "description": "My task", "project": "Work"}]
        screen = FuzzySearchScreen(tasks)
        assert screen.all_tasks == tasks

    def test_init_empty_tasks(self):
        screen = FuzzySearchScreen([])
        assert screen.all_tasks == []

    def test_update_list_filters_by_description(self):
        tasks = [
            {"id": 1, "uuid": "a", "description": "Write tests", "project": "Dev"},
            {"id": 2, "uuid": "b", "description": "Fix bug", "project": "Dev"},
        ]
        screen = FuzzySearchScreen(tasks)
        lv = Mock()
        lv.clear = Mock()
        lv.append = Mock()
        screen.query_one = Mock(return_value=lv)

        screen.update_list("write")

        lv.clear.assert_called_once()
        assert lv.append.call_count == 1  # only "Write tests" matches

    def test_has_key_handler(self):
        screen = FuzzySearchScreen([])
        assert hasattr(screen, "on_key")
        assert callable(screen.on_key)

    def test_escape_dismisses(self):
        screen = FuzzySearchScreen([])
        screen.dismiss = Mock()
        event = Mock()
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)


@pytest.mark.unit
class TestDependencyListScreen:
    def test_init_with_dependencies(self):
        deps = ["abc-123", "def-456"]
        all_tasks = [
            {"id": 1, "uuid": "abc-123", "description": "Task 1"},
            {"id": 2, "uuid": "def-456", "description": "Task 2"},
        ]
        screen = DependencyListScreen(deps, all_tasks)
        assert screen.dependencies == deps
        assert screen.all_tasks == all_tasks

    def test_escape_key_handling(self):
        screen = DependencyListScreen([], [])
        screen.dismiss = Mock()
        event = Mock()
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)


@pytest.mark.unit
class TestErrorModalScreen:
    def test_init_stores_error_message(self):
        msg = "Invalid due date: 'notadate'"
        screen = ErrorModalScreen(msg)
        assert screen.error_message == msg

    def test_escape_key_dismisses(self):
        screen = ErrorModalScreen("some error")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "escape"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)
        event.stop.assert_called_once()

    def test_enter_key_dismisses(self):
        screen = ErrorModalScreen("some error")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "enter"
        screen.on_key(event)
        screen.dismiss.assert_called_once_with(None)
        event.stop.assert_called_once()

    def test_other_key_does_not_dismiss(self):
        screen = ErrorModalScreen("some error")
        screen.dismiss = Mock()
        event = Mock()
        event.key = "q"
        screen.on_key(event)
        screen.dismiss.assert_not_called()

"""Tests for screen components."""
import pytest
from unittest.mock import Mock, patch
from task_tui.screens import QuickMenuScreen, FuzzySearchScreen, DependencyListScreen


@pytest.mark.unit
class TestQuickMenuScreen:
    def test_init_main_menu(self):
        """Test initializing main date menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        
        assert screen.menu_type == "main"
        assert screen.app_ref == app_ref
    
    def test_init_end_of_menu(self):
        """Test initializing end-of submenu."""
        app_ref = Mock()
        screen = QuickMenuScreen("end_of", app_ref)
        
        assert screen.menu_type == "end_of"
    
    def test_init_priority_menu(self):
        """Test initializing priority menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("priority", app_ref)
        
        assert screen.menu_type == "priority"
    
    def test_main_menu_today_key(self):
        """Test 'n' key calls apply_quick_date with 'today'."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        screen.dismiss = Mock()  # Mock dismiss to avoid Textual context
        
        event = Mock()
        event.key = "n"
        
        screen.on_key(event)
        
        app_ref.apply_quick_date.assert_called_once_with("today")
        screen.dismiss.assert_called_once_with(None)
        event.stop.assert_called_once()
    
    def test_main_menu_tomorrow_key(self):
        """Test 't' key calls apply_quick_date with 'tomorrow'."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "t"
        
        screen.on_key(event)
        
        app_ref.apply_quick_date.assert_called_once_with("tomorrow")
        screen.dismiss.assert_called_once_with(None)
    
    def test_main_menu_end_of_key(self):
        """Test 'e' key opens end-of submenu."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "e"
        
        screen.on_key(event)
        
        screen.dismiss.assert_called_once_with("go_to_end_of")
    
    def test_end_of_menu_week_key(self):
        """Test 'w' key in end-of menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("end_of", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "w"
        
        screen.on_key(event)
        
        app_ref.apply_quick_date.assert_called_once_with("eow")
        screen.dismiss.assert_called_once_with(None)
    
    def test_end_of_menu_month_key(self):
        """Test 'm' key in end-of menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("end_of", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "m"
        
        screen.on_key(event)
        
        app_ref.apply_quick_date.assert_called_once_with("eom")
    
    def test_end_of_menu_year_key(self):
        """Test 'y' key in end-of menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("end_of", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "y"
        
        screen.on_key(event)
        
        app_ref.apply_quick_date.assert_called_once_with("eoy")
    
    def test_priority_menu_high(self):
        """Test 'h' key sets high priority."""
        app_ref = Mock()
        screen = QuickMenuScreen("priority", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "h"
        
        screen.on_key(event)
        
        app_ref.apply_quick_prio.assert_called_once_with("H")
        screen.dismiss.assert_called_once_with(None)
    
    def test_priority_menu_medium(self):
        """Test 'm' key sets medium priority."""
        app_ref = Mock()
        screen = QuickMenuScreen("priority", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "m"
        
        screen.on_key(event)
        
        app_ref.apply_quick_prio.assert_called_once_with("M")
    
    def test_priority_menu_low(self):
        """Test 'l' key sets low priority."""
        app_ref = Mock()
        screen = QuickMenuScreen("priority", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "l"
        
        screen.on_key(event)
        
        app_ref.apply_quick_prio.assert_called_once_with("L")
    
    def test_priority_menu_clear(self):
        """Test 'x' key clears priority."""
        app_ref = Mock()
        screen = QuickMenuScreen("priority", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "x"
        
        screen.on_key(event)
        
        app_ref.apply_quick_prio.assert_called_once_with("")
    
    def test_escape_dismisses_main(self):
        """Test ESC dismisses main menu."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "escape"
        
        screen.on_key(event)
        
        screen.dismiss.assert_called_once_with(None)
    
    def test_escape_goes_back_from_end_of(self):
        """Test ESC in end-of menu goes back to main."""
        app_ref = Mock()
        screen = QuickMenuScreen("end_of", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "escape"
        
        screen.on_key(event)
        
        screen.dismiss.assert_called_once_with("back_to_main")
    
    def test_case_insensitive_keys(self):
        """Test keys are case-insensitive."""
        app_ref = Mock()
        screen = QuickMenuScreen("main", app_ref)
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "N"  # Uppercase
        
        screen.on_key(event)
        
        # Should still work
        app_ref.apply_quick_date.assert_called_once_with("today")
        screen.dismiss.assert_called_once_with(None)


@pytest.mark.unit
class TestFuzzySearchScreen:
    """Tests for fuzzy search screen.
    
    Note: Most UI interaction tests require full Textual app context
    and would need to be marked as ui_integration tests.
    """
    
    @patch('task_tui.screens.fuzzy_search.subprocess.run')
    def test_load_tasks(self, mock_subprocess, mock_task_data):
        """Test loading tasks on mount."""
        import json
        mock_subprocess.return_value = Mock(
            stdout=json.dumps(mock_task_data),
            stderr=""
        )
        
        screen = FuzzySearchScreen()
        tasks = screen.load_tasks()
        
        assert len(tasks) == 2
        assert tasks[0]["description"] == "Test task 1"
    
    @patch('task_tui.screens.fuzzy_search.subprocess.run')
    def test_load_tasks_error(self, mock_subprocess):
        """Test handling error when loading tasks."""
        mock_subprocess.return_value = Mock(
            stdout="invalid json",
            stderr=""
        )
        
        screen = FuzzySearchScreen()
        tasks = screen.load_tasks()
        
        assert tasks == []
    
    def test_has_key_handler(self):
        """Test screen has key handler method."""
        screen = FuzzySearchScreen()
        
        # Verify the method exists
        assert hasattr(screen, 'on_key')
        assert callable(screen.on_key)


@pytest.mark.unit
class TestDependencyListScreen:
    def test_init_with_dependencies(self):
        """Test initializing with dependency list."""
        deps = ["abc-123", "def-456"]
        all_tasks = [
            {"id": 1, "uuid": "abc-123", "description": "Task 1"},
            {"id": 2, "uuid": "def-456", "description": "Task 2"},
        ]
        
        screen = DependencyListScreen(deps, all_tasks)
        
        assert screen.dependencies == deps
        assert screen.all_tasks == all_tasks
    
    def test_escape_key_handling(self):
        """Test ESC dismisses dependency list."""
        screen = DependencyListScreen([], [])
        screen.dismiss = Mock()
        
        event = Mock()
        event.key = "escape"
        
        screen.on_key(event)
        
        screen.dismiss.assert_called_once_with(None)

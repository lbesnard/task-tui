"""Tests for app action methods."""
import pytest
import subprocess
from unittest.mock import Mock, PropertyMock, call, patch
from task_tui.app import DependsInput, TaskProApp


@pytest.fixture
def app_with_mocked_ui(sample_app):
    """Create app with mocked UI methods to avoid Textual context."""
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    return sample_app


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestUndoAction:
    def test_undo_success(self, mock_subprocess_app, app_with_mocked_ui):
        """Test successful undo operation."""
        mock_subprocess_app.return_value = Mock(returncode=0)
        
        app_with_mocked_ui.action_undo()
        
        # Verify exact command
        mock_subprocess_app.assert_called_once_with(
            ["task", "rc.confirmation=off", "undo"],
            capture_output=True,
            text=True,
        )
        app_with_mocked_ui.refresh_tasks.assert_called_once()
        app_with_mocked_ui.notify.assert_called()
    
    def test_undo_no_action_to_undo(self, mock_subprocess_app, app_with_mocked_ui):
        """Test undo when there's nothing to undo."""
        mock_subprocess_app.return_value = Mock(returncode=1)
        
        app_with_mocked_ui.action_undo()
        
        mock_subprocess_app.assert_called_once()
    
    def test_undo_exception(self, mock_subprocess_app, app_with_mocked_ui):
        """Test undo handles exceptions gracefully."""
        mock_subprocess_app.side_effect = Exception("Command failed")
        
        # Should not raise
        app_with_mocked_ui.action_undo()
        app_with_mocked_ui.notify.assert_called()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestToggleStartAction:
    def test_start_inactive_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test starting a task that's not active."""
        app_with_mocked_ui.active_uuid = "abc-123"
        
        app_with_mocked_ui.action_toggle_start()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "start"],
            check=True
        )
        app_with_mocked_ui.refresh_tasks.assert_called_once()
    
    def test_stop_active_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test stopping an active task."""
        app_with_mocked_ui.active_uuid = "def-456"
        
        app_with_mocked_ui.action_toggle_start()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "def-456", "stop"],
            check=True
        )
    
    def test_toggle_with_no_active_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test toggle when no task is selected."""
        app_with_mocked_ui.active_uuid = None
        
        app_with_mocked_ui.action_toggle_start()
        
        # Should not call subprocess
        mock_subprocess_app.assert_not_called()
    
    def test_toggle_with_new_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test toggle with NEW task (should skip)."""
        app_with_mocked_ui.active_uuid = "NEW"
        
        app_with_mocked_ui.action_toggle_start()
        
        mock_subprocess_app.assert_not_called()
    
    def test_toggle_failure(self, mock_subprocess_app, app_with_mocked_ui):
        """Test handling toggle failure."""
        app_with_mocked_ui.active_uuid = "abc-123"
        mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
        
        # Should not raise
        app_with_mocked_ui.action_toggle_start()
        app_with_mocked_ui.notify.assert_called()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestMarkDoneAction:
    def test_mark_done_single_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test marking a single task as done."""
        app_with_mocked_ui.active_uuid = "abc-123"
        app_with_mocked_ui.selected_uuids = set()
        
        app_with_mocked_ui.action_mark_done()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "done"],
            check=True
        )
        app_with_mocked_ui.refresh_tasks.assert_called_once()
    
    def test_mark_done_multiple_tasks(self, mock_subprocess_app, app_with_mocked_ui):
        """Test marking multiple selected tasks as done."""
        app_with_mocked_ui.selected_uuids = {"abc-123", "def-456"}
        
        app_with_mocked_ui.action_mark_done()
        
        # Should be called twice
        assert mock_subprocess_app.call_count == 2
        calls = [call[0][0] for call in mock_subprocess_app.call_args_list]
        
        # Verify both UUIDs were processed (order may vary due to set)
        uuids_called = {call_args[1] for call_args in calls}
        assert uuids_called == {"abc-123", "def-456"}
    
    def test_mark_done_with_new_task(self, mock_subprocess_app, app_with_mocked_ui):
        """Test mark done skips NEW task."""
        app_with_mocked_ui.active_uuid = "NEW"
        
        app_with_mocked_ui.action_mark_done()
        
        mock_subprocess_app.assert_not_called()
    
    def test_mark_done_with_empty_selection(self, mock_subprocess_app, app_with_mocked_ui):
        """Test mark done with no task selected."""
        app_with_mocked_ui.active_uuid = None
        app_with_mocked_ui.selected_uuids = set()
        
        app_with_mocked_ui.action_mark_done()
        
        mock_subprocess_app.assert_not_called()
    
    def test_mark_done_partial_failure(self, mock_subprocess_app, app_with_mocked_ui):
        """Test mark done with some tasks failing."""
        app_with_mocked_ui.selected_uuids = {"abc-123", "def-456"}
        
        # First call succeeds, second fails
        mock_subprocess_app.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "task"),
        ]
        
        app_with_mocked_ui.action_mark_done()
        
        # Should attempt both despite failure
        assert mock_subprocess_app.call_count == 2


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestQuickDateActions:
    @pytest.mark.parametrize("date_str", ["today", "tomorrow", "eow", "eom", "eoy"])
    def test_apply_quick_date(self, mock_subprocess_app, app_with_mocked_ui, date_str):
        """Test applying quick date shortcuts."""
        app_with_mocked_ui.active_uuid = "abc-123"
        
        app_with_mocked_ui.apply_quick_date(date_str)
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "modify", f"due:{date_str}"],
            check=True,
            capture_output=True
        )
    
    def test_apply_quick_date_to_selected(self, mock_subprocess_app, app_with_mocked_ui):
        """Test applying date to multiple selected tasks."""
        app_with_mocked_ui.selected_uuids = {"abc-123", "def-456"}
        
        app_with_mocked_ui.apply_quick_date("today")
        
        assert mock_subprocess_app.call_count == 2
    
    def test_apply_quick_date_skips_new(self, mock_subprocess_app, app_with_mocked_ui):
        """Test quick date skips NEW task."""
        app_with_mocked_ui.active_uuid = "NEW"
        
        app_with_mocked_ui.apply_quick_date("today")
        
        mock_subprocess_app.assert_not_called()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestQuickPriorityActions:
    @pytest.mark.parametrize("priority", ["H", "M", "L", ""])
    def test_apply_quick_priority(self, mock_subprocess_app, app_with_mocked_ui, priority):
        """Test applying priority levels."""
        app_with_mocked_ui.active_uuid = "abc-123"
        
        app_with_mocked_ui.apply_quick_prio(priority)
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "modify", f"priority:{priority}"],
            check=True,
            capture_output=True
        )
    
    def test_apply_quick_priority_to_selected(self, mock_subprocess_app, app_with_mocked_ui):
        """Test applying priority to multiple tasks."""
        app_with_mocked_ui.selected_uuids = {"abc-123", "def-456"}
        
        app_with_mocked_ui.apply_quick_prio("H")
        
        assert mock_subprocess_app.call_count == 2


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestCheckTaskwarriorInstalled:
    def test_taskwarrior_installed(self):
        """Test check when Taskwarrior is installed."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.return_value = Mock(returncode=0)
            
            result = check_taskwarrior_installed()
            
            assert result is True
            mock.assert_called_once_with(
                ["task", "--version"],
                capture_output=True,
                check=True
            )
    
    def test_taskwarrior_not_found(self):
        """Test check when Taskwarrior is not installed."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.side_effect = FileNotFoundError()
            
            result = check_taskwarrior_installed()
            
            assert result is False
    
    def test_taskwarrior_error(self):
        """Test check when Taskwarrior command fails."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.side_effect = subprocess.CalledProcessError(1, "task")
            
            result = check_taskwarrior_installed()
            
            assert result is False

    def test_undo_success(self, mock_subprocess_app, sample_app):
        """Test successful undo operation."""
        mock_subprocess_app.return_value = Mock(returncode=0)
        
        sample_app.action_undo()
        
        # Verify exact command
        mock_subprocess_app.assert_called_once_with(
            ["task", "rc.confirmation=off", "undo"],
            capture_output=True,
            text=True,
        )
    
    def test_undo_no_action_to_undo(self, mock_subprocess_app, sample_app):
        """Test undo when there's nothing to undo."""
        mock_subprocess_app.return_value = Mock(returncode=1)
        
        sample_app.action_undo()
        
        mock_subprocess_app.assert_called_once()
    
    def test_undo_exception(self, mock_subprocess_app, sample_app):
        """Test undo handles exceptions gracefully."""
        mock_subprocess_app.side_effect = Exception("Command failed")
        
        # Should not raise
        sample_app.action_undo()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestToggleStartAction:
    def test_start_inactive_task(self, mock_subprocess_app, sample_app):
        """Test starting a task that's not active."""
        sample_app.active_uuid = "abc-123"
        # Task 1 has no 'start' field
        
        sample_app.action_toggle_start()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "start"],
            check=True
        )
    
    def test_stop_active_task(self, mock_subprocess_app, sample_app):
        """Test stopping an active task."""
        sample_app.active_uuid = "def-456"
        # Task 2 has 'start' field
        
        sample_app.action_toggle_start()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "def-456", "stop"],
            check=True
        )
    
    def test_toggle_with_no_active_task(self, mock_subprocess_app, sample_app):
        """Test toggle when no task is selected."""
        sample_app.active_uuid = None
        
        sample_app.action_toggle_start()
        
        # Should not call subprocess
        mock_subprocess_app.assert_not_called()
    
    def test_toggle_with_new_task(self, mock_subprocess_app, sample_app):
        """Test toggle with NEW task (should skip)."""
        sample_app.active_uuid = "NEW"
        
        sample_app.action_toggle_start()
        
        mock_subprocess_app.assert_not_called()
    
    def test_toggle_failure(self, mock_subprocess_app, sample_app):
        """Test handling toggle failure."""
        sample_app.active_uuid = "abc-123"
        mock_subprocess_app.side_effect = subprocess.CalledProcessError(1, "task")
        
        # Should not raise
        sample_app.action_toggle_start()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestMarkDoneAction:
    def test_mark_done_single_task(self, mock_subprocess_app, sample_app):
        """Test marking a single task as done."""
        sample_app.active_uuid = "abc-123"
        sample_app.selected_uuids = set()
        
        sample_app.action_mark_done()
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "done"],
            check=True
        )
    
    def test_mark_done_multiple_tasks(self, mock_subprocess_app, sample_app):
        """Test marking multiple selected tasks as done."""
        sample_app.selected_uuids = {"abc-123", "def-456"}
        
        sample_app.action_mark_done()
        
        # Should be called twice
        assert mock_subprocess_app.call_count == 2
        calls = [call[0][0] for call in mock_subprocess_app.call_args_list]
        
        # Verify both UUIDs were processed (order may vary due to set)
        uuids_called = {call_args[1] for call_args in calls}
        assert uuids_called == {"abc-123", "def-456"}
    
    def test_mark_done_with_new_task(self, mock_subprocess_app, sample_app):
        """Test mark done skips NEW task."""
        sample_app.active_uuid = "NEW"
        
        sample_app.action_mark_done()
        
        mock_subprocess_app.assert_not_called()
    
    def test_mark_done_with_empty_selection(self, mock_subprocess_app, sample_app):
        """Test mark done with no task selected."""
        sample_app.active_uuid = None
        sample_app.selected_uuids = set()
        
        sample_app.action_mark_done()
        
        mock_subprocess_app.assert_not_called()
    
    def test_mark_done_partial_failure(self, mock_subprocess_app, sample_app):
        """Test mark done with some tasks failing."""
        sample_app.selected_uuids = {"abc-123", "def-456"}
        
        # First call succeeds, second fails
        mock_subprocess_app.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "task"),
        ]
        
        sample_app.action_mark_done()
        
        # Should attempt both despite failure
        assert mock_subprocess_app.call_count == 2


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestQuickDateActions:
    @pytest.mark.parametrize("date_str", ["today", "tomorrow", "eow", "eom", "eoy"])
    def test_apply_quick_date(self, mock_subprocess_app, sample_app, date_str):
        """Test applying quick date shortcuts."""
        sample_app.active_uuid = "abc-123"
        
        sample_app.apply_quick_date(date_str)
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "modify", f"due:{date_str}"],
            check=True,
            capture_output=True
        )
    
    def test_apply_quick_date_to_selected(self, mock_subprocess_app, sample_app):
        """Test applying date to multiple selected tasks."""
        sample_app.selected_uuids = {"abc-123", "def-456"}
        
        sample_app.apply_quick_date("today")
        
        assert mock_subprocess_app.call_count == 2
    
    def test_apply_quick_date_skips_new(self, mock_subprocess_app, sample_app):
        """Test quick date skips NEW task."""
        sample_app.active_uuid = "NEW"
        
        sample_app.apply_quick_date("today")
        
        mock_subprocess_app.assert_not_called()


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestQuickPriorityActions:
    @pytest.mark.parametrize("priority", ["H", "M", "L", ""])
    def test_apply_quick_priority(self, mock_subprocess_app, sample_app, priority):
        """Test applying priority levels."""
        sample_app.active_uuid = "abc-123"
        
        sample_app.apply_quick_prio(priority)
        
        mock_subprocess_app.assert_called_once_with(
            ["task", "abc-123", "modify", f"priority:{priority}"],
            check=True,
            capture_output=True
        )
    
    def test_apply_quick_priority_to_selected(self, mock_subprocess_app, sample_app):
        """Test applying priority to multiple tasks."""
        sample_app.selected_uuids = {"abc-123", "def-456"}
        
        sample_app.apply_quick_prio("H")
        
        assert mock_subprocess_app.call_count == 2


@pytest.mark.ui_integration
@pytest.mark.ui_integration
class TestCheckTaskwarriorInstalled:
    def test_taskwarrior_installed(self):
        """Test check when Taskwarrior is installed."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.return_value = Mock(returncode=0)
            
            result = check_taskwarrior_installed()
            
            assert result is True
            mock.assert_called_once_with(
                ["task", "--version"],
                capture_output=True,
                check=True
            )
    
    def test_taskwarrior_not_found(self):
        """Test check when Taskwarrior is not installed."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.side_effect = FileNotFoundError()
            
            result = check_taskwarrior_installed()
            
            assert result is False
    
    def test_taskwarrior_error(self):
        """Test check when Taskwarrior command fails."""
        from task_tui.app import check_taskwarrior_installed
        
        with patch("subprocess.run") as mock:
            mock.side_effect = subprocess.CalledProcessError(1, "task")
            
            result = check_taskwarrior_installed()
            
            assert result is False


@pytest.mark.unit
class TestCursorNavigationActions:
    """Tests for cursor navigation action methods."""
    
    def test_action_cursor_down(self):
        """Test cursor down delegates to DataTable."""
        app = TaskProApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_cursor_down()
        
        mock_table.action_cursor_down.assert_called_once()
    
    def test_action_cursor_up(self):
        """Test cursor up delegates to DataTable."""
        app = TaskProApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_cursor_up()
        
        mock_table.action_cursor_up.assert_called_once()
    
    def test_action_cursor_left(self):
        """Test cursor left delegates to DataTable."""
        app = TaskProApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_cursor_left()
        
        mock_table.action_cursor_left.assert_called_once()
    
    def test_action_cursor_right(self):
        """Test cursor right delegates to DataTable."""
        app = TaskProApp()
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_cursor_right()
        
        mock_table.action_cursor_right.assert_called_once()
    
    def test_action_scroll_top(self):
        """Test scroll to top."""
        app = TaskProApp()
        app.raw_tasks = [{"uuid": "1"}, {"uuid": "2"}]
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_scroll_top()
        
        mock_table.scroll_home.assert_called_once()
        mock_table.move_cursor.assert_called_once_with(row=0)
    
    def test_action_scroll_bottom(self):
        """Test scroll to bottom."""
        app = TaskProApp()
        app.raw_tasks = [{"uuid": "1"}, {"uuid": "2"}, {"uuid": "3"}]
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_scroll_bottom()
        
        mock_table.scroll_end.assert_called_once()
        mock_table.move_cursor.assert_called_once_with(row=2)  # len(raw_tasks) - 1
    
    def test_scroll_bottom_with_empty_tasks(self):
        """Test scroll to bottom with no tasks."""
        app = TaskProApp()
        app.raw_tasks = []
        mock_table = Mock()
        app.query_one = Mock(return_value=mock_table)
        
        app.action_scroll_bottom()
        
        mock_table.scroll_end.assert_called_once()
        mock_table.move_cursor.assert_called_once_with(row=-1)


@pytest.mark.unit
class TestToggleSelectionAction:
    """Tests for toggle selection action."""
    
    def test_select_task(self):
        """Test selecting a task adds it to selected_uuids."""
        app = TaskProApp()
        app.active_uuid = "abc-123"
        app.selected_uuids = set()
        app.update_table_view = Mock()
        
        app.action_toggle_selection()
        
        assert "abc-123" in app.selected_uuids
        app.update_table_view.assert_called_once()
    
    def test_deselect_task(self):
        """Test deselecting a task removes it from selected_uuids."""
        app = TaskProApp()
        app.active_uuid = "abc-123"
        app.selected_uuids = {"abc-123"}
        app.update_table_view = Mock()
        
        app.action_toggle_selection()
        
        assert "abc-123" not in app.selected_uuids
        app.update_table_view.assert_called_once()
    
    def test_toggle_multiple_tasks(self):
        """Test selecting and deselecting multiple tasks."""
        app = TaskProApp()
        app.update_table_view = Mock()
        app.selected_uuids = set()
        
        # Select first task
        app.active_uuid = "task-1"
        app.action_toggle_selection()
        assert "task-1" in app.selected_uuids
        
        # Select second task
        app.active_uuid = "task-2"
        app.action_toggle_selection()
        assert "task-1" in app.selected_uuids
        assert "task-2" in app.selected_uuids
        
        # Deselect first task
        app.active_uuid = "task-1"
        app.action_toggle_selection()
        assert "task-1" not in app.selected_uuids
        assert "task-2" in app.selected_uuids
    
    def test_skip_new_task(self):
        """Test toggle selection skips NEW task."""
        app = TaskProApp()
        app.active_uuid = "NEW"
        app.selected_uuids = set()
        app.update_table_view = Mock()
        
        app.action_toggle_selection()
        
        assert "NEW" not in app.selected_uuids
        app.update_table_view.assert_not_called()
    
    def test_skip_none_uuid(self):
        """Test toggle selection skips when no active task."""
        app = TaskProApp()
        app.active_uuid = None
        app.selected_uuids = set()
        app.update_table_view = Mock()
        
        app.action_toggle_selection()
        
        assert len(app.selected_uuids) == 0
        app.update_table_view.assert_not_called()
    
    def test_selection_state_persistence(self):
        """Test selected_uuids persists across multiple operations."""
        app = TaskProApp()
        app.update_table_view = Mock()
        app.selected_uuids = set()
        
        # Build up selection
        for uuid in ["task-1", "task-2", "task-3"]:
            app.active_uuid = uuid
            app.action_toggle_selection()
        
        assert len(app.selected_uuids) == 3
        assert all(uuid in app.selected_uuids for uuid in ["task-1", "task-2", "task-3"])


@pytest.mark.unit
class TestSearchShortcutBehavior:
    def test_global_search_binding_comes_from_config(self):
        app = TaskProApp(config={"shortcuts": {"global_search": "ctrl+g"}})

        fuzzy_binding = next(b for b in app.BINDINGS if b.action == "fuzzy_find")
        assert fuzzy_binding.key == "ctrl+g"

    def test_view_dependencies_binding_comes_from_config(self):
        app = TaskProApp(config={"shortcuts": {"view_dependencies": "a"}})

        dep_binding = next(b for b in app.BINDINGS if b.action == "view_dependencies")
        assert dep_binding.key == "a"

    def test_dependency_search_uses_slash_in_dep_input(self):
        app = TaskProApp()
        app.is_modifying = True
        app.action_fuzzy_find_dep = Mock()
        event = Mock(key="/", character="/")

        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_focused:
            mock_focused.return_value = Mock(id="inp_dep")
            app.on_key(event)

        app.action_fuzzy_find_dep.assert_called_once()
        event.stop.assert_called_once()


@pytest.mark.unit
class TestDependsInputBehavior:
    def test_depends_input_intercepts_slash_before_typing(self):
        dep_input = DependsInput(id="inp_dep")
        mock_app = Mock()
        mock_app.is_modifying = True
        mock_app._is_dependency_search_key.return_value = True
        mock_app.action_fuzzy_find_dep = Mock()
        event = Mock(key="slash", character="/")

        with patch.object(DependsInput, "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = mock_app
            dep_input.on_key(event)

        mock_app.action_fuzzy_find_dep.assert_called_once()
        event.stop.assert_called_once()

    def test_dependency_search_uses_slash_key_name_in_dep_input(self):
        app = TaskProApp()
        app.is_modifying = True
        app.action_fuzzy_find_dep = Mock()
        event = Mock(key="slash", character="/")

        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_focused:
            mock_focused.return_value = Mock(id="inp_dep")
            app.on_key(event)

        app.action_fuzzy_find_dep.assert_called_once()
        event.stop.assert_called_once()

    def test_action_fuzzy_find_dep_strips_slash_residue(self):
        app = TaskProApp()
        dep_input = Mock()
        dep_input.value = "/"
        app.query_one = Mock(return_value=dep_input)

        def fake_push_screen(_screen, callback):
            callback("69e1-uuid")

        app.push_screen = Mock(side_effect=fake_push_screen)
        app.action_fuzzy_find_dep()

        assert dep_input.value == "69e1-uuid"

    def test_action_fuzzy_find_dep_avoids_duplicates(self):
        app = TaskProApp()
        dep_input = Mock()
        dep_input.value = "69e1-uuid"
        app.query_one = Mock(return_value=dep_input)

        def fake_push_screen(_screen, callback):
            callback("69e1-uuid")

        app.push_screen = Mock(side_effect=fake_push_screen)
        app.action_fuzzy_find_dep()

        assert dep_input.value == "69e1-uuid"

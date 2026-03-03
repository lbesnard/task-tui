"""Tests for app action methods."""
import pytest
import subprocess
from unittest.mock import Mock, call, patch
from task_tui.app import TaskProApp


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

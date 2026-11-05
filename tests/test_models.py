"""Tests for task model functions."""
import pytest
import json
import subprocess
from unittest.mock import Mock, call
from task_tui.models.task import load_pending_tasks, sync_tasks


class TestLoadPendingTasks:
    def test_successful_load(self, mock_subprocess, mock_task_data):
        """Test loading tasks successfully from Taskwarrior."""
        mock_subprocess.return_value.stdout = json.dumps(mock_task_data)
        
        tasks = load_pending_tasks()
        
        assert len(tasks) == 2
        assert tasks[0]["description"] == "Test task 1"
        assert tasks[1]["description"] == "Test task 2"
        
        # Verify exact command called
        mock_subprocess.assert_called_once_with(
            ["task", "status:pending", "export", "rc.json.array=on"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    
    def test_empty_result(self, mock_subprocess):
        """Test handling empty task list."""
        mock_subprocess.return_value.stdout = "[]"
        
        tasks = load_pending_tasks()
        
        assert tasks == []
        mock_subprocess.assert_called_once()
    
    def test_empty_stdout(self, mock_subprocess):
        """Test handling empty stdout."""
        mock_subprocess.return_value.stdout = ""
        
        tasks = load_pending_tasks()
        
        assert tasks == []
    
    def test_subprocess_error(self, mock_subprocess):
        """Test handling subprocess errors gracefully."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        
        tasks = load_pending_tasks()
        
        assert tasks == []
    
    def test_invalid_json(self, mock_subprocess):
        """Test handling invalid JSON output."""
        mock_subprocess.return_value.stdout = "invalid json"
        
        tasks = load_pending_tasks()
        
        assert tasks == []
    
    def test_generic_exception(self, mock_subprocess):
        """Test handling unexpected exceptions."""
        mock_subprocess.side_effect = Exception("Unexpected error")
        
        tasks = load_pending_tasks()
        
        assert tasks == []


class TestLoadPendingTasksErrorReporting:
    def test_reports_stderr_on_failure(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "task", stderr="bad taskrc\n"
        )
        errors = []

        assert load_pending_tasks(on_error=errors.append) == []
        assert errors == ["bad taskrc"]

    def test_reports_timeout(self, mock_subprocess):
        mock_subprocess.side_effect = subprocess.TimeoutExpired("task", 30)
        errors = []

        assert load_pending_tasks(on_error=errors.append) == []
        assert "timed out" in errors[0]

    def test_no_error_reported_on_success(self, mock_subprocess):
        errors = []

        load_pending_tasks(on_error=errors.append)

        assert errors == []


class TestSyncTasks:
    def test_successful_sync(self, mock_subprocess):
        """Test successful sync with Taskwarrior server."""
        result = sync_tasks()
        
        assert result is True
        mock_subprocess.assert_called_once_with(
            ["task", "sync"],
            check=True,
            timeout=10
        )
    
    def test_sync_with_custom_timeout(self, mock_subprocess):
        """Test sync with custom timeout value."""
        result = sync_tasks(timeout=30)
        
        assert result is True
        mock_subprocess.assert_called_once_with(
            ["task", "sync"],
            check=True,
            timeout=30
        )
    
    def test_sync_timeout(self, mock_subprocess):
        """Test handling sync timeout."""
        mock_subprocess.side_effect = subprocess.TimeoutExpired("task", 10)
        
        result = sync_tasks()
        
        assert result is False
    
    def test_sync_error(self, mock_subprocess):
        """Test handling sync command failure."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        
        result = sync_tasks()
        
        assert result is False



class TestSaveTaskCommand:
    def test_new_task_uses_add(self, mock_subprocess):
        from task_tui.models import commands

        commands.save_task(None, {"description": "x", "priority": ""})

        assert mock_subprocess.call_args[0][0] == ["task", "add", "description:x", "priority:"]

    def test_existing_task_uses_modify(self, mock_subprocess):
        from task_tui.models import commands

        commands.save_task("abc", {"project": "P"})

        assert mock_subprocess.call_args[0][0] == ["task", "abc", "modify", "project:P"]

    def test_timeout_is_returned_as_failure(self, mock_subprocess):
        from task_tui.models import commands

        mock_subprocess.side_effect = subprocess.TimeoutExpired("task", 30)

        result = commands.save_task("abc", {"project": "P"})

        assert result.returncode == 1
        assert "timed out" in result.stderr

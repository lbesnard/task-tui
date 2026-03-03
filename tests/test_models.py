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


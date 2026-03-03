"""Tests for task model functions."""
import pytest
import json
from unittest.mock import Mock, patch
from task_tui.models.task import load_pending_tasks, sync_tasks


class TestLoadPendingTasks:
    def test_successful_load(self, mock_subprocess, mock_task_data):
        mock_subprocess.return_value.stdout = json.dumps(mock_task_data)
        
        tasks = load_pending_tasks()
        
        assert len(tasks) == 2
        assert tasks[0]["description"] == "Test task 1"
        mock_subprocess.assert_called_once()
    
    def test_empty_result(self, mock_subprocess):
        mock_subprocess.return_value.stdout = "[]"
        
        tasks = load_pending_tasks()
        
        assert tasks == []
    
    def test_subprocess_error(self, mock_subprocess):
        mock_subprocess.side_effect = Exception("Command failed")
        
        tasks = load_pending_tasks()
        
        assert tasks == []
    
    def test_invalid_json(self, mock_subprocess):
        mock_subprocess.return_value.stdout = "invalid json"
        
        tasks = load_pending_tasks()
        
        assert tasks == []


class TestSyncTasks:
    def test_successful_sync(self, mock_subprocess):
        result = sync_tasks()
        
        assert result is True
        mock_subprocess.assert_called_with(["task", "sync"], check=True, timeout=10)
    
    def test_sync_timeout(self, mock_subprocess):
        import subprocess
        mock_subprocess.side_effect = subprocess.TimeoutExpired("task", 10)
        
        result = sync_tasks()
        
        assert result is False
    
    def test_sync_error(self, mock_subprocess):
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "task")
        
        result = sync_tasks()
        
        assert result is False

import pytest
import json
from unittest.mock import Mock, patch


@pytest.fixture
def mock_task_data():
    """Sample task data for testing."""
    return [
        {
            "id": 1,
            "uuid": "abc-123",
            "description": "Test task 1",
            "project": "Test",
            "priority": "H",
            "urgency": 15.5,
            "status": "pending",
            "tags": ["test", "example"],
        },
        {
            "id": 2,
            "uuid": "def-456",
            "description": "Test task 2",
            "project": "Work",
            "priority": "M",
            "urgency": 22.3,
            "status": "pending",
            "due": "20260315T000000Z",
        },
    ]


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for models.task module.
    
    Patches at the usage point (task_tui.models.task) not globally.
    This ensures the mock is seen by the code under test.
    """
    with patch("task_tui.models.task.subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock


@pytest.fixture
def mock_subprocess_app():
    """Mock subprocess.run for app module.
    
    Used for testing app action methods that call subprocess.
    """
    with patch("task_tui.app.subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock


@pytest.fixture
def sample_app():
    """Create a TaskProApp instance with test data.
    
    Useful for testing app actions without full initialization.
    """
    from task_tui.app import TaskProApp
    app = TaskProApp()
    app.raw_tasks = [
        {
            "id": 1,
            "uuid": "abc-123",
            "description": "Test task 1",
            "project": "Test",
            "priority": "H",
            "status": "pending",
        },
        {
            "id": 2,
            "uuid": "def-456",
            "description": "Test task 2",
            "project": "Work",
            "priority": "M",
            "status": "pending",
            "start": "20260301T100000Z",
        },
    ]
    app.active_uuid = "abc-123"
    app.selected_uuids = set()
    return app


import pytest
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
    """Mock subprocess.run for testing without calling actual taskwarrior."""
    with patch("subprocess.run") as mock:
        mock.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock

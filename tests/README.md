# Task-TUI Tests

This directory contains the test suite for Task-TUI.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=task_tui --cov-report=html

# Run specific test file
pytest tests/test_colors.py

# Run tests matching a pattern
pytest -k "test_urgency"

# Run only unit tests
pytest -m unit

# Verbose output
pytest -v
```

## Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_colors.py` - Tests for color utilities
- `test_models.py` - Tests for data models and Taskwarrior interface
- (more to come)

## Writing Tests

Follow pytest conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

Example:
```python
def test_function_name():
    # Arrange
    input_data = "test"
    
    # Act
    result = function_to_test(input_data)
    
    # Assert
    assert result == expected_output
```

## Coverage

Aim for high test coverage, especially for:
- Utility functions
- Data transformations
- Error handling paths
- Edge cases

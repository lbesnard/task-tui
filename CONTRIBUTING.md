# Contributing to Task-TUI

Thank you for your interest in contributing to Task-TUI! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Making Changes](#making-changes)
- [Running Tests](#running-tests)
- [Submitting Changes](#submitting-changes)
- [Issue Reporting](#issue-reporting)

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/task-tui.git
   cd task-tui
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/lbesnard/task-tui.git
   ```

## Development Setup

### Prerequisites

- Python 3.10 or higher
- [Taskwarrior](https://taskwarrior.org/download/) installed and configured
- pip (Python package manager)

### Installation

1. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install in editable mode**:
   ```bash
   pip install -e .
   ```

3. **Install development dependencies** (when available):
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify installation**:
   ```bash
   task-tui --version
   ```

## Code Style

We follow standard Python coding conventions:

### General Guidelines

- **PEP 8**: Follow [PEP 8](https://pep8.org/) style guide
- **Line length**: Maximum 100 characters
- **Imports**: Group into standard library, third-party, and local imports
- **Docstrings**: Use Google-style docstrings for functions and classes
- **Type hints**: Add type annotations where applicable

### Example

```python
from typing import List, Dict, Any


def process_tasks(tasks: List[Dict[str, Any]]) -> int:
    """Process a list of tasks and return count.
    
    Args:
        tasks: List of task dictionaries from Taskwarrior
        
    Returns:
        Number of tasks processed
    """
    return len([t for t in tasks if t.get("status") == "pending"])
```

### Code Formatting

We will add automated formatting tools in the future (black, ruff). For now:
- Use 4 spaces for indentation
- Use double quotes for strings
- Add blank lines between functions and classes

## Making Changes

### Branch Naming

Create a descriptive branch name:
- `feature/add-bulk-edit` - for new features
- `fix/sync-timeout-error` - for bug fixes
- `docs/update-readme` - for documentation
- `refactor/split-models` - for refactoring

### Commit Messages

Write clear, descriptive commit messages:
```
feat: Add bulk edit functionality for selected tasks

- Implement multi-task editing in edit mode
- Add validation for bulk operations
- Update README with new feature documentation

Closes #123
```

**Commit message format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

### Code Organization

The project structure:
```
task-tui/
├── task_tui/
│   ├── __init__.py
│   ├── app.py           # Main application
│   ├── screens/         # Modal screens
│   │   ├── quick_menu.py
│   │   ├── dependency_list.py
│   │   └── fuzzy_search.py
│   ├── models/          # Data models and Taskwarrior interface
│   │   └── task.py
│   └── utils/           # Utility functions
│       └── colors.py
├── tests/               # Test suite (to be added)
├── README.md
├── CONTRIBUTING.md
└── pyproject.toml
```

## Running Tests

Tests are being added. Once available:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=task_tui

# Run specific test file
pytest tests/test_colors.py
```

## Submitting Changes

### Pull Request Process

1. **Update your branch** with latest upstream:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**:
   ```bash
   git push origin your-branch-name
   ```

3. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Description explaining what and why
   - Reference any related issues
   - Screenshots for UI changes (if applicable)

### Pull Request Checklist

Before submitting:
- [ ] Code follows project style guidelines
- [ ] All existing tests pass (when available)
- [ ] New tests added for new functionality (when applicable)
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] No commented-out code or debug prints
- [ ] Commit messages are clear and descriptive

### Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged

## Issue Reporting

### Bug Reports

Include:
- **Description**: Clear description of the bug
- **Steps to reproduce**: Numbered steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**:
  - OS and version
  - Python version
  - Taskwarrior version
  - Task-TUI version
- **Screenshots**: If applicable

### Feature Requests

Include:
- **Problem**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives**: Other solutions you've considered
- **Additional context**: Mockups, examples, etc.

## Questions?

- Open an issue with the "question" label
- Check existing issues and discussions first

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help make Task-TUI better for everyone

Thank you for contributing to Task-TUI! 🎉

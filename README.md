# 📝 Task-TUI

A modern, high-performance Terminal User Interface (TUI) for [Taskwarrior](https://taskwarrior.org/). Built with the Python [Textual](https://textual.textualize.io/) framework, it provides a seamless way to manage your tasks with live updates and fuzzy searching.

---

## ✨ Features

- **Live Preview**: Browse your task list with arrow keys; the editor panel updates instantly to show descriptions, tags, and annotations.
- **Fuzzy Search**: Quickly find any task by description or project using the built-in fuzzy finder (`f`).
- **Interactive Sorting**: Click on any column header (ID, Project, Due, etc.) to toggle ascending or descending order.
- **Edit Anywhere**: Press `s` to save your changes at any time, even while typing in an input field.
- **Auto-Sync**: Automatically runs `task sync` on startup and exit to keep your remote servers up to date.
- **Visual Priority**: Priority levels are color-coded (High = Red, Medium = Yellow, Low = Green) for instant recognition.

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- [Taskwarrior](https://taskwarrior.org/download/) installed and configured in your `PATH`.

### Quick Install

```
python3 -m pip install git+https://github.com/lbesnard/task-tui.git
```

### Setup

1. Clone the repository:

```bash
git clone https://github.com/lbesnard/task-tui.git
cd task-tui
```

2. Install in editable mode:

```bash
pip install -e .
```

---

## ⌨️ Keyboard Shortcuts

| Key      | Action                                 |
| -------- | -------------------------------------- |
| `f`      | Open Fuzzy Search                      |
| `⇅`      | Navigate task list (Live Preview)      |
| `m`      | Modify selected task (Enter Edit Mode) |
| `n`      | Create a new task                      |
| `s`      | Save changes (Global)                  |
| `d`      | Mark selected task as Done             |
| `r`      | Refresh task list                      |
| `s`      | Refresh task list                      |
| `space`  | multiple select                        |
| `C`      | Cancel multiple selection              |
| `Ctrl+Z` | Cancel edit / Back to list             |
| `q`      | Quit and Sync                          |

---

## 🛠 Configuration

Task-TUI reads directly from your `.taskrc`. No extra configuration is required.

If you have a `taskserver` configured, Task-TUI will attempt to sync your changes automatically when you close the application.

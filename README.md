# 📝 Task-TUI

A modern, high-performance Terminal User Interface (TUI) for [Taskwarrior](https://taskwarrior.org/). Built with the Python [Textual](https://textual.textualize.io/) framework, it provides a seamless way to manage your tasks with live updates and fuzzy searching.

![Example of task-tui](assets/tasktui.png)

---

## ✨ Features

- **Live Preview & Interaction**: Browse your task list with Vim-like navigation; the editor panel updates instantly to show full task details.
- **Dynamic Color Hashing**: Automatically assigns one of 32+ unique colors to each **Project** name for instant visual grouping.
- **Urgency Alerts**: Task **Urgency** values above 20 are highlighted in **bold red** to help you focus on critical items.
- **Fuzzy Search & Dependency Picking**:
  - Press `/` to search all pending tasks.
  - While editing dependencies, press `/` to search and pick tasks to add to the dependency list.
- **Dependency Explorer**: Press `v` to open a dedicated modal showing all tasks the current item depends on, with the ability to "jump" directly to them.
- **Switchable Reports**: Press `R` to switch between your Taskwarrior reports (`next`, `minimal`, `overdue`, or any custom report from your `.taskrc`) without leaving the app. See [Reports](#-reports).
- **Notes (Annotations)**: Taskwarrior annotations appear in a *Notes* field in the side panel, one per line. In edit mode just Tab to it, type, and save with the rest of the task. Taskwarrior can't edit a note in place, so changing a line removes the old note and adds a new one (with a new date); untouched lines keep theirs. Outside edit mode, `a` adds a note and `A` removes one.
- **Snooze (Wait)**: Press `w` to hide a task until later, or set the *Wait* field in the editor. Snoozed tasks leave the default list until their wait date; bring them back with `R` → `waiting`, where they are marked 💤 and can be un-snoozed (`w` → `x`).
- **Recurring Tasks**: Tick *Recurring* in the editor to pick a recurrence (daily, weekdays, weekly, monthly, ..., or a custom value like `3d`). Recurring tasks are marked 🔁. Taskwarrior requires a due date, and a recurrence can be changed but not removed once a task is recurring.
- **Full Edit in your `$EDITOR`**: Press `e` to open the task with `task edit` (all fields, UDAs, annotations); the TUI resumes and reloads when you close the editor. Set `ui.editor` to override `$VISUAL`/`$EDITOR`.
- **Overviews**: Press `V` for Taskwarrior's `stats`, `summary`, `calendar`, `burndown`, `history`, `projects` and `tags` reports without leaving the app.
- **Configurable Columns**: Choose which columns the task table shows (and their order) with `ui.columns`, including extras such as `wait`, `recur`, `entry`, `annotations` and `depends`. See [Configuration](#-configuration).
- **Pin to Top**: Press `N` to toggle the `next` tag on the selected task(s). Taskwarrior gives `+next` a large urgency boost, so pinned tasks float to the top of urgency-sorted lists.
- **Contextual Quick-Actions**: Rapidly set Due Dates (Today, Tomorrow, End of Week/Month) or Priority levels without entering full edit mode.
- **Visual Priority**: Priority levels are color-coded (High = Red, Medium = Yellow, Low = Green).
- **Auto-Sync**: Automatically runs `task sync` on exit to keep your remote servers up to date, and `Y` syncs on demand.

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- [Taskwarrior](https://taskwarrior.org/download/) installed and configured in your `PATH`.

### Stable release (recommended)

Install the latest release with a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/lbesnard/task-tui/main/install.sh | sh
```

The script automatically fetches the latest version, selects the correct wheel, and installs via `pipx` (preferred) or `pip`.

Or pick a specific version from the [Releases page](https://github.com/lbesnard/task-tui/releases) and install it directly:

```bash
pip install https://github.com/lbesnard/task-tui/releases/download/vX.Y.Z/task_tui-X.Y.Z-py3-none-any.whl
```

### Via pipx (isolated environment — great for CLI tools)

```bash
curl -fsSL https://raw.githubusercontent.com/lbesnard/task-tui/main/install.sh | sh
```

### Latest from source

```bash
pip install git+https://github.com/lbesnard/task-tui.git
```

### Development install

1. Clone the repository:

```bash
git clone https://github.com/lbesnard/task-tui.git
cd task-tui
```

2. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run task-tui
```

---

## ⌨️ Keyboard Shortcuts

### 1. Navigation & Global

| Key       | Action                         |
| :-------- | :----------------------------- |
| `j` / `k` | Navigate task list (Vim-style) |
| `g` / `G` | Jump to Top / Bottom of list   |
| `/`       | Open Fuzzy Search              |
| `r`       | Refresh task list              |
| `R`       | Switch Taskwarrior report      |
| `V`       | Overviews: stats, summary, calendar, burndown, history, projects, tags |
| `Y`       | Sync now (`task sync`)         |
| `u`       | Undo last Taskwarrior action   |
| `q`       | Quit and Sync                  |

### 2. Task Quick-Actions

| Key     | Action                                                 |
| :------ | :----------------------------------------------------- |
| `i`     | **Modify**: Enter Edit Mode for selected task          |
| `n`     | **New**: Create a new task                             |
| `x`     | **Save**: Save changes (works while focused in inputs) |
| `s`     | **Start/Stop**: Toggle active status on a task         |
| `N`     | **Pin/Unpin**: Toggle the `+next` tag, which boosts urgency (pinned tasks show 📌) |
| `d`     | **Done**: Mark selected task as completed              |
| `D`     | **Delete**: Delete selected task(s) after confirmation (`u` undoes) |
| `e`     | **Edit in $EDITOR**: open the full task (`task edit`), return to the TUI when done |
| `a` / `A` | **Notes** (view mode only; in edit mode use the Notes field): add / remove an annotation |
| `v`     | **View Deps**: Open the Dependency Explorer modal      |
| `space` | **Select**: Toggle task for batch operations           |

### 3. Quick Context Menus

| Key   | Action                                                    |
| :---- | :-------------------------------------------------------- |
| `t`   | **Quick Date**: Set due date (Today, Tomorrow, EOW, etc.) |
| `p`   | **Quick Prio**: Set priority (High, Mid, Low, Clear)      |
| `w`   | **Snooze**: Hide a task until tomorrow, next Monday, +1 week or end of month (`wait`) |
| `f`   | **Filter**: Filter the list by project (`p`) or tag (`t`) |
| `Esc` | Cancel context menu or Edit Mode                          |

---

## 📊 Reports

Taskwarrior [reports](https://taskwarrior.org/docs/report/) are named views (`next`, `minimal`, `list`, `overdue`, ...) defined in your `.taskrc`. Press `R` to pick one; the task list reloads using that report's filter. The active report is shown in the header (`Report: overdue`).

- Choose **all pending** in the picker to return to the default view (every pending task).
- The picker lists every report that Taskwarrior knows about (`task show report.`), including your custom ones.
- The report's **filter** is applied. Its **sort** is mapped onto the table's sort using the first key only (e.g. `urgency-` sorts by urgency, descending), when that key is a displayed column. You can still re-sort by clicking a header.
- `limit:` terms such as `limit:page` are ignored, since the list scrolls.
- Project/tag filters (`f`) are reset when you switch report.
- Reports that include non-pending tasks (e.g. `completed`, `all`) work for browsing, but actions such as Done are meant for pending tasks.
- Set a report to open on startup with `ui.default_report` in the config file (see below).

---

## 🛠 Configuration

Task-TUI reads directly from your `.taskrc`, and now also supports an optional app config file.

On first run, Task-TUI creates:

`~/.local/share/task-tui/config.json`

You can customize keyboard shortcuts and future UI settings there. Example:

```json
{
  "shortcuts": {
    "global_search": "/",
    "dependency_search": "/",
    "edit_mode": "i",
    "save_task": "x"
  },
  "ui": {
    "show_debug_panel": true,
    "default_report": "next",
    "editor": "nvim",
    "columns": ["id", "project", "priority", "due", "tags", "urgency", "description"]
  }
}
```

`default_report` is optional: leave it `null` to start with all pending tasks. `editor` is optional too: leave it `null` to use your `$VISUAL`/`$EDITOR`. The report switcher key is `shortcuts.switch_report` (default `R`).

`columns` controls the task table. Available names: `id`, `project`, `priority`, `due`, `tags`, `urgency`, `description`, `scheduled`, `wait`, `entry`, `modified`, `start`, `recur`, `annotations` (count), `depends` (count), `status`. Unknown names are ignored and an empty list restores the defaults. The default is the seven columns shown above. The sort column is kept when it is still displayed; clicking a header sorts by it.

If you have a `taskserver` configured, Task-TUI will attempt to sync your changes automatically when you close the application.

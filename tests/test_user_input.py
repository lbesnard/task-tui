"""Tests for user input handling, edit mode, and task save operations.

All tests that exercise paths touching taskwarrior or taskchampion
(i.e. subprocess.run calls) use the mock_subprocess_app fixture so that
no real task data is ever written or read from the system.
"""
import pytest
import subprocess
from unittest.mock import Mock, PropertyMock, call, patch
from task_tui.app import DependsInput, TaskProApp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_no_widgets(sample_app):
    """App with basic method mocks but NO widget queries needed.

    Use this for actions that only call subprocess + notify/refresh_tasks/exit.
    """
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    sample_app.exit = Mock()
    return sample_app


@pytest.fixture
def app_with_widgets(sample_app):
    """App with all UI widgets mocked out.

    Patches query_one / query so tests never touch a real Textual DOM.
    subprocess.run is NOT patched here – use mock_subprocess_app alongside.
    """
    from textual.widgets import DataTable

    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    sample_app.exit = Mock()
    sample_app.set_modify_mode = Mock()

    widgets = {
        "#inp_desc": Mock(value="Test task"),
        "#inp_proj": Mock(value="TestProject"),
        "#inp_due": Mock(value=""),
        "#inp_dep": Mock(value=""),
        "#inp_tags": Mock(value="tag1"),
        "#sel_prio": Mock(value="H"),
        "#debug_panel": Mock(),
        "#mode_indicator": Mock(),
        "#editor_panel": Mock(),
        "#uuid_display": Mock(),
    }

    data_table = Mock()

    def _query_one(selector):
        if selector is DataTable or selector == DataTable:
            return data_table
        return widgets.get(str(selector), Mock())

    sample_app.query_one = Mock(side_effect=_query_one)
    sample_app.query = Mock(return_value=[])
    sample_app._widgets = widgets
    sample_app._data_table = data_table

    return sample_app


# ---------------------------------------------------------------------------
# action_save_task
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActionSaveTask:
    """Verify action_save_task builds the correct taskwarrior command.

    subprocess.run is always mocked via mock_subprocess_app to guarantee
    nothing is written to taskwarrior / taskchampion.
    """

    def test_no_active_uuid_does_not_call_subprocess(
        self, mock_subprocess_app, app_with_widgets
    ):
        """save_task is a no-op when no task is active."""
        app_with_widgets.active_uuid = None
        app_with_widgets.action_save_task()
        mock_subprocess_app.assert_not_called()

    def test_new_task_uses_add_command(self, mock_subprocess_app, app_with_widgets):
        """active_uuid='NEW' → 'task add ...' (not modify)."""
        app_with_widgets.active_uuid = "NEW"
        app_with_widgets._widgets["#inp_desc"].value = "My new task"
        app_with_widgets._widgets["#inp_proj"].value = "Work"
        app_with_widgets._widgets["#inp_due"].value = ""
        app_with_widgets._widgets["#inp_dep"].value = ""
        app_with_widgets._widgets["#inp_tags"].value = ""
        app_with_widgets._widgets["#sel_prio"].value = "X"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert cmd[:2] == ["task", "add"], f"Expected 'task add', got {cmd[:2]}"
        assert "modify" not in cmd
        assert "description:My new task" in cmd
        assert "project:Work" in cmd

    def test_existing_task_uses_modify_command(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Existing task → 'task <uuid> modify ...'."""
        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert cmd[:3] == ["task", "abc-123", "modify"]

    def test_date_8digits_converted_to_taskwarrior_format(
        self, mock_subprocess_app, app_with_widgets
    ):
        """8-digit YYYYMMDD date is converted to YYYYMMDDT000000."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#inp_due"].value = "20261231"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "due:20261231T000000" in cmd

    def test_non_digit_due_passed_unchanged(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Human-readable dates like 'tomorrow' are forwarded as-is."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#inp_due"].value = "tomorrow"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "due:tomorrow" in cmd

    def test_short_date_not_converted(self, mock_subprocess_app, app_with_widgets):
        """A numeric string that isn't exactly 8 digits is forwarded as-is."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#inp_due"].value = "202612"  # only 6 digits
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "due:202612" in cmd
        assert "T000000" not in "".join(cmd)

    @pytest.mark.parametrize("priority", ["H", "M", "L"])
    def test_priority_values_passed_correctly(
        self, mock_subprocess_app, app_with_widgets, priority
    ):
        """H/M/L priority values are forwarded verbatim."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#sel_prio"].value = priority
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert f"priority:{priority}" in cmd

    def test_priority_x_becomes_empty_string(
        self, mock_subprocess_app, app_with_widgets
    ):
        """UI sentinel value 'X' (no priority) is sent as empty string."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#sel_prio"].value = "X"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "priority:" in cmd
        assert "priority:X" not in cmd

    def test_dependency_whitespace_is_cleaned(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Spaces in the depends field are stripped; result is comma-separated UUIDs."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#inp_dep"].value = " uuid1 , uuid2 , "
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "depends:uuid1,uuid2" in cmd

    def test_empty_dependency_field(self, mock_subprocess_app, app_with_widgets):
        """Empty depends field sends 'depends:' (empty value)."""
        app_with_widgets.active_uuid = "abc-123"
        app_with_widgets._widgets["#inp_dep"].value = ""
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        cmd = mock_subprocess_app.call_args[0][0]
        assert "depends:" in cmd

    def test_save_failure_opens_error_modal(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Non-zero returncode opens an ErrorModalScreen with the error text."""
        from task_tui.screens import ErrorModalScreen

        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(
            returncode=1, stdout="", stderr="Task not found"
        )
        app_with_widgets.push_screen = Mock()

        app_with_widgets.action_save_task()

        app_with_widgets.push_screen.assert_called_once()
        modal = app_with_widgets.push_screen.call_args[0][0]
        assert isinstance(modal, ErrorModalScreen)
        assert modal.error_message == "Task not found"

    def test_save_failure_does_not_refresh_tasks(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Failed save must not call refresh_tasks (data not changed)."""
        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(
            returncode=1, stdout="", stderr="error"
        )

        app_with_widgets.action_save_task()

        app_with_widgets.refresh_tasks.assert_not_called()

    def test_save_success_calls_refresh_tasks(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Successful save refreshes the task list."""
        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        app_with_widgets.refresh_tasks.assert_called_once()

    def test_save_success_exits_modify_mode(
        self, mock_subprocess_app, app_with_widgets
    ):
        """Successful save transitions back to view mode."""
        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        app_with_widgets.set_modify_mode.assert_called_once_with(False)

    def test_save_uses_capture_output(self, mock_subprocess_app, app_with_widgets):
        """subprocess.run must use capture_output=True, text=True to read errors."""
        app_with_widgets.active_uuid = "abc-123"
        mock_subprocess_app.return_value = Mock(returncode=0, stdout="", stderr="")

        app_with_widgets.action_save_task()

        _, kwargs = mock_subprocess_app.call_args
        assert kwargs.get("capture_output") is True
        assert kwargs.get("text") is True


# ---------------------------------------------------------------------------
# action_new_task
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActionNewTask:
    """Tests for entering new-task creation mode."""

    def test_active_uuid_set_to_new(self, app_with_widgets):
        """action_new_task sets active_uuid to the sentinel 'NEW'."""
        app_with_widgets.action_new_task()
        assert app_with_widgets.active_uuid == "NEW"

    def test_enters_modify_mode(self, app_with_widgets):
        """action_new_task calls set_modify_mode(True) to enable editing."""
        app_with_widgets.action_new_task()
        app_with_widgets.set_modify_mode.assert_called_once_with(True)

    def test_all_input_fields_cleared(self, app_with_widgets):
        """All input fields are cleared so old data doesn't bleed into new task."""
        for field in ["#inp_desc", "#inp_proj", "#inp_due", "#inp_dep", "#inp_tags"]:
            app_with_widgets._widgets[field].value = "stale value"

        app_with_widgets.action_new_task()

        for field in ["#inp_desc", "#inp_proj", "#inp_due", "#inp_dep", "#inp_tags"]:
            assert app_with_widgets._widgets[field].value == "", (
                f"Field {field} was not cleared"
            )

    def test_uuid_display_shows_new_task(self, app_with_widgets):
        """UUID display widget is updated to indicate a new task."""
        app_with_widgets.action_new_task()
        app_with_widgets._widgets["#uuid_display"].update.assert_called_once_with(
            "NEW TASK"
        )


# ---------------------------------------------------------------------------
# action_cancel_edit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActionCancelEdit:
    def test_cancel_exits_modify_mode(self, app_with_widgets):
        """Cancel edit calls set_modify_mode(False)."""
        app_with_widgets.action_cancel_edit()
        app_with_widgets.set_modify_mode.assert_called_once_with(False)

    def test_cancel_returns_focus_to_table(self, app_with_widgets):
        """Cancel edit returns keyboard focus to the DataTable."""
        app_with_widgets.action_cancel_edit()
        app_with_widgets._data_table.focus.assert_called()


# ---------------------------------------------------------------------------
# action_quit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActionQuit:
    def test_quit_when_clean_calls_exit(self, app_no_widgets):
        """With no unsaved changes, quit calls self.exit()."""
        app_no_widgets.is_dirty = False
        app_no_widgets.action_quit()
        app_no_widgets.exit.assert_called_once()

    def test_quit_when_dirty_shows_error_notification(self, app_no_widgets):
        """Unsaved changes prevent quit and display an error notification."""
        app_no_widgets.is_dirty = True
        app_no_widgets.action_quit()
        app_no_widgets.notify.assert_called()
        _, kwargs = app_no_widgets.notify.call_args
        assert kwargs.get("severity") == "error"

    def test_quit_when_dirty_does_not_exit(self, app_no_widgets):
        """Quit with unsaved changes must NOT call self.exit()."""
        app_no_widgets.is_dirty = True
        app_no_widgets.action_quit()
        app_no_widgets.exit.assert_not_called()


# ---------------------------------------------------------------------------
# Dirty-state tracking
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDirtyStateTracking:
    """is_dirty must be set whenever an input/select changes in edit mode."""

    def test_on_input_changed_marks_dirty_in_edit_mode(self, app_with_widgets):
        """on_input_changed sets is_dirty when is_modifying is True."""
        app_with_widgets.is_modifying = True
        app_with_widgets.is_dirty = False

        app_with_widgets.on_input_changed()

        assert app_with_widgets.is_dirty is True

    def test_on_input_changed_does_not_mark_dirty_in_view_mode(self, app_with_widgets):
        """on_input_changed does nothing when not in edit mode."""
        app_with_widgets.is_modifying = False
        app_with_widgets.is_dirty = False

        app_with_widgets.on_input_changed()

        assert app_with_widgets.is_dirty is False

    def test_on_input_changed_updates_mode_indicator(self, app_with_widgets):
        """mode_indicator is updated to show unsaved state while editing."""
        app_with_widgets.is_modifying = True
        app_with_widgets.is_dirty = False

        app_with_widgets.on_input_changed()

        app_with_widgets._widgets["#mode_indicator"].update.assert_called_once()
        indicator_text = app_with_widgets._widgets["#mode_indicator"].update.call_args[0][0]
        assert "UNSAVED" in indicator_text

    def test_on_select_changed_marks_dirty_in_edit_mode(self, app_no_widgets):
        """on_select_changed sets is_dirty when in edit mode."""
        app_no_widgets.is_modifying = True
        app_no_widgets.is_dirty = False

        app_no_widgets.on_select_changed()

        assert app_no_widgets.is_dirty is True

    def test_on_select_changed_does_not_mark_dirty_in_view_mode(self, app_no_widgets):
        """on_select_changed is a no-op in view mode."""
        app_no_widgets.is_modifying = False
        app_no_widgets.is_dirty = False

        app_no_widgets.on_select_changed()

        assert app_no_widgets.is_dirty is False


# ---------------------------------------------------------------------------
# on_key handler
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOnKeyHandler:
    """Tests for app-level key event routing."""

    def _make_event(self, key, character=None):
        event = Mock()
        event.key = key
        event.character = character if character is not None else (key if len(key) == 1 else None)
        return event

    def test_unbound_char_in_view_mode_notifies_user(self, app_no_widgets):
        """Typing an unbound character in view mode shows 'Edit Mode' hint."""
        app_no_widgets.is_modifying = False
        app_no_widgets.BINDINGS = []  # No keys bound

        event = self._make_event("z")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = None
            app_no_widgets.on_key(event)

        app_no_widgets.notify.assert_called()
        notification_text = app_no_widgets.notify.call_args[0][0]
        assert "Edit Mode" in notification_text or "i" in notification_text
        event.stop.assert_called_once()

    def test_bound_char_in_view_mode_does_not_notify(self, app_no_widgets):
        """A key that IS bound (e.g. 'j') in view mode must not trigger the warning."""
        from textual.binding import Binding

        app_no_widgets.is_modifying = False
        app_no_widgets.BINDINGS = [Binding("j", "cursor_down", "Down", show=False)]

        event = self._make_event("j")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = None
            app_no_widgets.on_key(event)

        app_no_widgets.notify.assert_not_called()

    def test_slash_key_in_view_mode_triggers_fuzzy_find(self, app_no_widgets):
        """'/' bound to fuzzy-search must open the search, not warn about Edit Mode.

        Textual fires event.key='slash' but the binding stores key='/' —
        on_key must manually dispatch the action when they differ.
        """
        from textual.binding import Binding

        app_no_widgets.is_modifying = False
        app_no_widgets.action_fuzzy_find = Mock()
        app_no_widgets.BINDINGS = [Binding("/", "fuzzy_find", "Search", show=True)]

        event = self._make_event("slash", character="/")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = None
            app_no_widgets.on_key(event)

        app_no_widgets.action_fuzzy_find.assert_called_once()
        app_no_widgets.notify.assert_not_called()

    def test_shift_s_triggers_save_task(self, app_no_widgets):
        """Pressing Shift+S (key='S') calls action_save_task and stops propagation."""
        app_no_widgets.action_save_task = Mock()
        app_no_widgets.is_modifying = True

        event = self._make_event("S")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = None
            app_no_widgets.on_key(event)

        app_no_widgets.action_save_task.assert_called_once()
        event.stop.assert_called()

    def test_dep_search_key_in_dep_field_triggers_fuzzy_dep(self, app_no_widgets):
        """'/' while focused on dep input field triggers dependency fuzzy search."""
        app_no_widgets.is_modifying = True
        app_no_widgets.action_fuzzy_find_dep = Mock()
        app_no_widgets._is_dependency_search_key = Mock(return_value=True)

        event = self._make_event("/")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = Mock(id="inp_dep")
            app_no_widgets.on_key(event)

        app_no_widgets.action_fuzzy_find_dep.assert_called_once()
        event.stop.assert_called_once()

    def test_dep_search_key_outside_dep_field_does_not_trigger_fuzzy_dep(
        self, app_no_widgets
    ):
        """'/' while focused on a different field must NOT trigger dep fuzzy search."""
        app_no_widgets.is_modifying = True
        app_no_widgets.action_fuzzy_find_dep = Mock()
        app_no_widgets._is_dependency_search_key = Mock(return_value=True)

        event = self._make_event("/")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = Mock(id="inp_desc")
            app_no_widgets.on_key(event)

        app_no_widgets.action_fuzzy_find_dep.assert_not_called()

    def test_dep_search_key_in_view_mode_does_not_trigger_fuzzy_dep(
        self, app_no_widgets
    ):
        """Dep search key is ignored when not in edit mode."""
        app_no_widgets.is_modifying = False
        app_no_widgets.action_fuzzy_find_dep = Mock()
        app_no_widgets._is_dependency_search_key = Mock(return_value=True)

        event = self._make_event("/")
        with patch.object(TaskProApp, "focused", new_callable=PropertyMock) as mock_f:
            mock_f.return_value = Mock(id="inp_dep")
            app_no_widgets.on_key(event)

        app_no_widgets.action_fuzzy_find_dep.assert_not_called()


# ---------------------------------------------------------------------------
# DependsInput widget key handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDependsInput:
    """Unit tests for the custom DependsInput widget key handler."""

    def _make_event(self, key):
        event = Mock()
        event.key = key
        event.character = key if len(key) == 1 else None
        return event

    def test_search_key_triggers_fuzzy_dep_search(self):
        """DependsInput intercepts the dep-search key and calls action_fuzzy_find_dep."""
        dep_input = DependsInput(id="inp_dep")
        mock_app = Mock()
        mock_app.is_modifying = True
        mock_app._is_dependency_search_key.return_value = True
        event = self._make_event("/")

        with patch.object(DependsInput, "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = mock_app
            dep_input.on_key(event)

        mock_app.action_fuzzy_find_dep.assert_called_once()
        event.stop.assert_called_once()

    def test_non_search_key_not_intercepted(self):
        """DependsInput does NOT intercept regular typing keys."""
        dep_input = DependsInput(id="inp_dep")
        mock_app = Mock()
        mock_app.is_modifying = True
        mock_app._is_dependency_search_key.return_value = False
        event = self._make_event("a")

        with patch.object(DependsInput, "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = mock_app
            dep_input.on_key(event)

        mock_app.action_fuzzy_find_dep.assert_not_called()
        event.stop.assert_not_called()

    def test_search_key_ignored_in_view_mode(self):
        """DependsInput does nothing when app is in view mode (is_modifying=False)."""
        dep_input = DependsInput(id="inp_dep")
        mock_app = Mock()
        mock_app.is_modifying = False
        mock_app._is_dependency_search_key.return_value = True
        event = self._make_event("/")

        with patch.object(DependsInput, "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = mock_app
            dep_input.on_key(event)

        mock_app.action_fuzzy_find_dep.assert_not_called()
        event.stop.assert_not_called()

    def test_no_app_reference_does_not_raise(self):
        """DependsInput on_key is safe when widget has no app yet."""
        dep_input = DependsInput(id="inp_dep")
        event = Mock()
        event.key = "/"
        event.character = "/"

        with patch.object(DependsInput, "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = None
            # Must not raise
            dep_input.on_key(event)

"""Tests for the Until (expiry) field and column."""
import time
from unittest.mock import Mock

import pytest

from task_tui.columns import COLUMN_LABELS, DATE_COLUMNS, cell_text, normalize_columns
from task_tui.editing import build_task_fields

FIELDS = dict(description="d", project="", due="", tags="", depends="", priority="X")
BERLIN = "CET-1CEST,M3.5.0,M10.5.0/3"  # POSIX rule: works without a tz database


@pytest.fixture
def tz(monkeypatch):
    """Run a test in a given local time zone (restored afterwards)."""
    def set_tz(name):
        monkeypatch.setenv("TZ", name)
        time.tzset()
    yield set_tz
    monkeypatch.undo()
    time.tzset()


class TestBuildFields:
    def test_until_normalised_like_due(self):
        assert build_task_fields(**FIELDS, until="20261201")["until"] == "20261201T000000"

    def test_until_relative_passes_through(self):
        assert build_task_fields(**FIELDS, until="2w")["until"] == "2w"

    def test_empty_until_clears(self):
        assert build_task_fields(**FIELDS)["until"] == ""


class TestListMark:
    def test_task_that_expires_is_marked(self, sample_app):
        task = {"description": "idea", "until": "20261201T230000Z"}
        assert sample_app._render_cell(task, "description") == "⏳ idea"

    def test_no_mark_without_until(self, sample_app):
        assert sample_app._render_cell({"description": "d"}, "description") == "d"
        assert sample_app._render_cell({"description": "d", "until": ""}, "description") == "d"

    def test_mark_comes_after_the_other_icons(self, sample_app):
        task = {"description": "d", "depends": ["u"], "until": "20261201T230000Z"}
        assert sample_app._render_cell(task, "description") == "🔗 ⏳ d"

    def test_recurring_tasks_are_not_marked(self, sample_app):
        # there ``until`` ends the series; every occurrence carries it
        for extra in ({}, {"parent": "p"}):
            task = {"description": "d", "recur": "weekly", "until": "20270728T220000Z", **extra}
            assert sample_app._render_cell(task, "description") == "🔁 d"


class TestColumn:
    def test_until_is_a_date_column(self):
        assert COLUMN_LABELS["until"] == "Until"
        assert "until" in DATE_COLUMNS
        assert normalize_columns(["id", "until"]) == ["id", "until"]

    def test_shown_as_local_day(self, tz):
        tz(BERLIN)
        assert cell_text({"until": "20261130T230000Z"}, "until") == "20261201"


@pytest.fixture
def form(sample_app):
    """The edit panel as a dict of mocked widgets, keyed by selector."""
    sample_app.refresh_tasks = Mock()
    sample_app.notify = Mock()
    sample_app.exit = Mock()
    sample_app.set_modify_mode = Mock()
    sample_app._set_recur_widgets = Mock()
    sample_app._set_notes = Mock()
    widgets = {
        "#inp_desc": Mock(value="d"), "#inp_proj": Mock(value=""),
        "#inp_due": Mock(value=""), "#inp_wait": Mock(value=""),
        "#inp_until": Mock(value=""), "#inp_dep": Mock(value=""),
        "#inp_tags": Mock(value=""), "#sel_prio": Mock(value="X"),
        "#txt_notes": Mock(text=""), "#chk_recur": Mock(value=False),
        "#sel_recur": Mock(value="weekly"), "#inp_recur": Mock(value=""),
    }
    sample_app.query_one = Mock(side_effect=lambda sel: widgets.get(str(sel), Mock()))
    sample_app._widgets = widgets
    return sample_app


class TestForm:
    def test_loaded_from_the_task(self, form, tz):
        tz(BERLIN)
        form.raw_tasks[0]["until"] = "20261130T230000Z"
        form.load_task_by_uuid("abc-123", focus=False)
        assert form._widgets["#inp_until"].value == "20261201"

    def test_empty_without_until(self, form):
        form.load_task_by_uuid("abc-123", focus=False)
        assert form._widgets["#inp_until"].value == ""

    def test_time_of_day_survives_the_round_trip(self, form, tz):
        tz(BERLIN)
        form.raw_tasks[0]["until"] = "20261201T123000Z"
        form.load_task_by_uuid("abc-123", focus=False)
        assert form._widgets["#inp_until"].value == "20261201T133000"

    def test_saved_with_the_other_fields(self, mock_subprocess_app, form):
        form._widgets["#inp_until"].value = "2w"
        form.action_save_task()
        assert "until:2w" in mock_subprocess_app.call_args.args[0]

    def test_cleared_field_removes_the_expiry(self, mock_subprocess_app, form):
        form.raw_tasks[0]["until"] = "20261130T230000Z"
        form.action_save_task()
        assert "until:" in mock_subprocess_app.call_args.args[0]

    def test_new_task_starts_empty(self, form):
        form._widgets["#inp_until"].value = "20261201"
        form.query_one("#uuid_display")
        form.action_new_task()
        assert form._widgets["#inp_until"].value == ""

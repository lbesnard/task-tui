"""Switching reports settles the sort order instead of keeping the last one.

A report sorted by a displayed column (``due+``) used to leave that order in
place when going back to "all pending", or on to a report sorted by something
that is not displayed (``entry-``): tasks without a due date ended up on top.
"""
from unittest.mock import Mock

import pytest

from task_tui.columns import COLUMN_LABELS
from task_tui.models.task import Report
from task_tui.state import AppState, default_sort_state

URGENT_FIRST = {"index": 5, "reverse": True}
DUE_ASCENDING = {"index": 3, "reverse": False}


class TestDefaultSortState:
    def test_most_urgent_first(self):
        assert default_sort_state() == URGENT_FIRST
        assert AppState().sort_state == URGENT_FIRST

    def test_follows_the_urgency_column(self):
        columns = [(COLUMN_LABELS[k], k) for k in ["urgency", "id", "description"]]
        assert default_sort_state(columns) == {"index": 0, "reverse": True}

    def test_first_column_when_urgency_is_hidden(self):
        columns = [(COLUMN_LABELS[k], k) for k in ["id", "description"]]
        assert default_sort_state(columns) == {"index": 0, "reverse": False}

    def test_each_state_gets_its_own_dict(self):
        a, b = AppState(), AppState()
        a.sort_state["reverse"] = False
        assert b.sort_state == URGENT_FIRST


@pytest.fixture
def app(sample_app):
    sample_app.refresh_tasks = Mock()
    sample_app._update_subtitle = Mock()
    return sample_app


class TestSelectReport:
    def test_report_sets_its_own_order(self, app):
        app._select_report(Report("week", "status:pending", "due+,urgency-"))
        assert app.state.sort_state == DUE_ASCENDING

    def test_all_pending_goes_back_to_the_default(self, app):
        app._select_report(Report("week", "status:pending", "due+"))
        app._select_report(None)
        assert app.state.sort_state == URGENT_FIRST

    @pytest.mark.parametrize("sort", ["entry-", "until+,entry+", ""])
    def test_undisplayed_sort_key_goes_back_to_the_default(self, app, sort):
        app._select_report(Report("week", "status:pending", "due+"))
        app._select_report(Report("other", "", sort))
        assert app.state.sort_state == URGENT_FIRST

    def test_manual_sort_is_replaced_too(self, app):
        app.state.sort_state = {"index": 6, "reverse": False}
        app._select_report(None)
        assert app.state.sort_state == URGENT_FIRST

    def test_default_respects_configured_columns(self, app):
        app.state.set_columns(["id", "description"])
        app._select_report(Report("week", "status:pending", "due+"))
        assert app.state.sort_state == {"index": 0, "reverse": False}

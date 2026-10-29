import pytest

from task_tui.state import COLUMNS, AppState


def _state(tasks, sort_field, reverse=False):
    state = AppState(raw_tasks=tasks)
    state.sort_state = {
        "index": [field for _, field in COLUMNS].index(sort_field),
        "reverse": reverse,
    }
    return state


@pytest.mark.unit
class TestSorting:
    def test_priority_defaults_to_high_first_and_toggles(self):
        tasks = [
            {"id": 1, "priority": "L"},
            {"id": 2, "priority": "H"},
            {"id": 3, "priority": "M"},
        ]

        first = [t["priority"] for t in _state(tasks, "priority", False).get_visible_tasks()]
        flipped = [t["priority"] for t in _state(tasks, "priority", True).get_visible_tasks()]

        assert first == ["H", "M", "L"]
        assert flipped == ["L", "M", "H"]

    def test_id_sorts_numerically(self):
        tasks = [{"id": 10}, {"id": 2}, {"id": 1}]

        ids = [t["id"] for t in _state(tasks, "id").get_visible_tasks()]

        assert ids == [1, 2, 10]


@pytest.mark.unit
class TestEditingHelpers:
    def test_build_task_fields_normalises_input(self):
        from task_tui.editing import build_task_fields

        fields = build_task_fields(
            description="d", project="p", due="20260315", tags="a,b",
            depends=" u1 , ,u2 ", priority="X",
        )

        assert fields["due"] == "20260315T000000"
        assert fields["depends"] == "u1,u2"
        assert fields["priority"] == ""

    def test_add_dependency_dedupes_and_drops_stray_slash(self):
        from task_tui.editing import add_dependency

        assert add_dependency("u1, /", "u2") == "u1, u2"
        assert add_dependency("u1, u2", "u1") == "u1, u2"

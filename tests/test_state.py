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

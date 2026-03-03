"""Tests for utility functions."""
import pytest
from task_tui.utils.colors import get_project_color, get_priority_color, format_urgency


class TestProjectColor:
    def test_empty_project_returns_white(self):
        assert get_project_color("") == "white"
    
    def test_same_project_returns_same_color(self):
        color1 = get_project_color("TestProject")
        color2 = get_project_color("TestProject")
        assert color1 == color2
    
    def test_different_projects_may_differ(self):
        colors = [get_project_color(f"Project{i}") for i in range(10)]
        assert len(set(colors)) > 1


class TestPriorityColor:
    def test_high_priority(self):
        assert get_priority_color("H") == "red"
    
    def test_medium_priority(self):
        assert get_priority_color("M") == "yellow"
    
    def test_low_priority(self):
        assert get_priority_color("L") == "green"
    
    def test_unknown_priority(self):
        assert get_priority_color("X") == "white"
        assert get_priority_color("") == "white"


class TestFormatUrgency:
    def test_low_urgency(self):
        result = format_urgency(15.5)
        assert "15.5" in result
        assert "[b][red]" not in result
    
    def test_high_urgency(self):
        result = format_urgency(25.0)
        assert "25.0" in result
        assert "[b][red]" in result
    
    def test_threshold_urgency(self):
        result = format_urgency(20.0)
        assert "20.0" in result
        assert "[b][red]" not in result
    
    def test_threshold_plus_one(self):
        result = format_urgency(20.1)
        assert "20.1" in result
        assert "[b][red]" in result

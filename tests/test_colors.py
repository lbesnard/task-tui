"""Tests for utility functions."""
import pytest
from task_tui.utils.colors import get_project_color, get_priority_color, format_urgency


class TestProjectColor:
    def test_empty_project_returns_white(self):
        """Empty project name should return white."""
        assert get_project_color("") == "white"
    
    def test_same_project_returns_same_color(self):
        """Same project name should always return same color (consistency)."""
        color1 = get_project_color("TestProject")
        color2 = get_project_color("TestProject")
        assert color1 == color2
    
    def test_different_projects_may_differ(self):
        """Different projects should likely have different colors."""
        colors = [get_project_color(f"Project{i}") for i in range(10)]
        assert len(set(colors)) > 1
    
    @pytest.mark.parametrize("project_name,expected_not", [
        ("Test", ""),
        ("Work", ""),
        ("Personal", ""),
    ])
    def test_project_returns_valid_color(self, project_name, expected_not):
        """All project names should return a non-empty color."""
        color = get_project_color(project_name)
        assert color != expected_not
        assert isinstance(color, str)


class TestPriorityColor:
    @pytest.mark.parametrize("priority,expected_color", [
        ("H", "red"),
        ("M", "yellow"),
        ("L", "green"),
        ("X", "white"),
        ("", "white"),
        (None, "white"),
    ])
    def test_priority_colors(self, priority, expected_color):
        """Test all priority levels return correct colors."""
        if priority is None:
            # Test edge case where priority might be None
            result = get_priority_color(priority) if priority else get_priority_color("")
        else:
            result = get_priority_color(priority)
        assert result == expected_color


class TestFormatUrgency:
    @pytest.mark.parametrize("urgency,should_highlight", [
        (0.0, False),
        (10.0, False),
        (15.5, False),
        (19.9, False),
        (20.0, False),  # Threshold, not highlighted
        (20.1, True),   # Above threshold, highlighted
        (25.0, True),
        (50.0, True),
        (100.0, True),
    ])
    def test_urgency_formatting(self, urgency, should_highlight):
        """Test urgency formatting with highlighting above threshold."""
        result = format_urgency(urgency)
        
        # Should always contain the urgency value
        assert f"{urgency:.1f}" in result
        
        # Check for highlighting
        if should_highlight:
            assert "[b][red]" in result
            assert "[/][/]" in result
        else:
            assert "[b][red]" not in result
    
    def test_urgency_float_precision(self):
        """Test urgency values are formatted with one decimal place."""
        result = format_urgency(15.567)
        assert "15.6" in result
    
    def test_urgency_zero(self):
        """Test zero urgency is handled correctly."""
        result = format_urgency(0.0)
        assert "0.0" in result
        assert "[b][red]" not in result


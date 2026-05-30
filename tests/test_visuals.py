"""Tests for visual generation — SVG output structure, schema, color constants."""

from __future__ import annotations

from unittest.mock import patch

# ---------------------------------------------------------------------------
# Color constants
# ---------------------------------------------------------------------------


def test_colors_present():
    from ouroboros.tools.visuals import _COLORS
    required = {"bg", "card", "border", "cyan", "purple", "green", "gold", "orange", "muted", "dim"}
    assert required.issubset(set(_COLORS.keys()))


# ---------------------------------------------------------------------------
# Schema tools
# ---------------------------------------------------------------------------


def test_visuals_tool_schemas():
    from ouroboros.tools.visuals import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "generate_system_portrait" in tools
    assert "generate_goal_progress_chart" in tools
    assert "generate_health_dashboard" in tools
    assert "generate_all_visuals" in tools
    assert "generate_dynamic_badge" in tools


def test_dynamic_badge_schema():
    from ouroboros.tools.visuals import get_tools
    tools = {t.name: t for t in get_tools()}
    params = tools["generate_dynamic_badge"].schema["parameters"]["properties"]
    assert "label" in params
    assert "message" in params
    assert "color" in params


# ---------------------------------------------------------------------------
# generate_dynamic_badge
# ---------------------------------------------------------------------------


def test_dynamic_badge_returns_svg():
    from ouroboros.tools.visuals import generate_dynamic_badge
    svg = generate_dynamic_badge("test", "123", color="#00d1ff")
    assert svg.startswith("<svg")
    assert "test" in svg
    assert "123" in svg
    assert "#00d1ff" in svg or "00d1ff" in svg


def test_dynamic_badge_default_color():
    from ouroboros.tools.visuals import generate_dynamic_badge
    svg = generate_dynamic_badge("label", "msg")
    assert svg.startswith("<svg")


# ---------------------------------------------------------------------------
# generate_system_portrait — with mocked file reads
# ---------------------------------------------------------------------------


def test_system_portrait_empty_state(tmp_path):
    """With no goals/tools, portrait should still return valid SVG."""
    from ouroboros.tools.visuals import generate_system_portrait

    with patch("ouroboros.tools.visuals._PROJECT_ROOT", tmp_path), \
         patch("ouroboros.tools.visuals._load_goals", return_value=[]), \
         patch("ouroboros.tools.visuals._load_created_tools", return_value=[]):
        svg = generate_system_portrait()
    assert svg.startswith("<svg")
    assert "xmlns" in svg
    assert "SYSTEM SELF-PORTRAIT" in svg


def test_system_portrait_with_goals(tmp_path):
    from ouroboros.tools.visuals import generate_system_portrait

    mock_goals = [
        {"title": "Test Goal", "status": "active", "priority": "high"},
    ]
    with patch("ouroboros.tools.visuals._load_goals", return_value=mock_goals), \
         patch("ouroboros.tools.visuals._load_created_tools", return_value=[]), \
         patch("ouroboros.tools.visuals._DRIVE_ROOT", tmp_path):
        svg = generate_system_portrait()
    assert "Test Goal" in svg
    assert "ACTIVE GOALS" in svg


# ---------------------------------------------------------------------------
# generate_goal_progress_chart
# ---------------------------------------------------------------------------


def test_goal_progress_chart_empty(tmp_path):
    from ouroboros.tools.visuals import generate_goal_progress_chart
    with patch("ouroboros.tools.visuals._load_goals", return_value=[]):
        svg = generate_goal_progress_chart()
    assert svg.startswith("<svg")


def test_goal_progress_chart_with_data(tmp_path):
    from ouroboros.tools.visuals import generate_goal_progress_chart
    mock_goals = [
        {"title": "Goal A", "status": "completed", "priority": "critical"},
        {"title": "Goal B", "status": "in_progress", "priority": "high"},
    ]
    with patch("ouroboros.tools.visuals._load_goals", return_value=mock_goals):
        svg = generate_goal_progress_chart()
    assert "GOAL PROGRESS" in svg
    assert "Total goals" in svg


# ---------------------------------------------------------------------------
# generate_health_dashboard
# ---------------------------------------------------------------------------


def test_health_dashboard_returns_html(tmp_path):
    from ouroboros.tools.visuals import generate_health_dashboard, _health_html
    with patch("ouroboros.tools.visuals._load_goals", return_value=[]), \
         patch("ouroboros.tools.visuals._load_created_tools", return_value=[]), \
         patch("ouroboros.tools.visuals._DRIVE_ROOT", tmp_path), \
         patch("ouroboros.tools.visuals._save_docs", return_value="docs/health.html"):
        result = generate_health_dashboard()
    assert "dashboard written to" in result
    assert "bytes" in result
    # Verify _health_html produces valid HTML
    html = _health_html()
    assert "<!DOCTYPE html>" in html or "<html>" in html


# ---------------------------------------------------------------------------
# generate_all_visuals
# ---------------------------------------------------------------------------


def test_generate_all_visuals_runs(tmp_path):
    from ouroboros.tools.visuals import generate_all_visuals
    with patch("ouroboros.tools.visuals._load_goals", return_value=[]), \
         patch("ouroboros.tools.visuals._load_created_tools", return_value=[]), \
         patch("ouroboros.tools.visuals._DRIVE_ROOT", tmp_path), \
         patch("ouroboros.tools.visuals._save_docs"):
        result = generate_all_visuals()
    assert "portrait" in result.lower() or "visual" in result.lower() or "saved" in result.lower()

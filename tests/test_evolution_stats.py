"""Tests for evolution stats — version extraction, principle counting, data helpers."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# _extract_version
# ---------------------------------------------------------------------------


def test_extract_version_simple():
    from ouroboros.tools.evolution_stats import _extract_version
    assert _extract_version("v1.2.3: Something") == "1.2.3"
    assert _extract_version("v0.0.1") == "0.0.1"
    assert _extract_version("v10.20.30") == "10.20.30"


def test_extract_version_no_match():
    from ouroboros.tools.evolution_stats import _extract_version
    assert _extract_version("no version here") is None
    assert _extract_version("version 1.2.3 (no v prefix)") is None
    assert _extract_version("") is None


def test_extract_version_in_message():
    from ouroboros.tools.evolution_stats import _extract_version
    msg = "feat: add new tool\n\nv7.0.0: Major update"
    assert _extract_version(msg) == "7.0.0"


# ---------------------------------------------------------------------------
# _count_principle_occurrences
# ---------------------------------------------------------------------------


def test_count_principle_occurrences():
    from ouroboros.tools.evolution_stats import _count_principle_occurrences
    content = "P0: Agency\nP1: Continuity\nP0 again"
    assert _count_principle_occurrences(content) == 2


def test_count_principle_occurrences_empty():
    from ouroboros.tools.evolution_stats import _count_principle_occurrences
    assert _count_principle_occurrences("") == 0
    assert _count_principle_occurrences("No principles here") == 0


# ---------------------------------------------------------------------------
# generate_evolution_stats — via tool schema
# ---------------------------------------------------------------------------


def test_evolution_stats_tool_schema():
    from ouroboros.tools.evolution_stats import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "generate_evolution_stats" in tools
    params = tools["generate_evolution_stats"].schema["parameters"]["properties"]
    assert isinstance(params, dict)


def test_evolution_dashboard_tool_schema():
    from ouroboros.tools.evolution_stats import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "generate_evolution_dashboard" in tools
    desc = tools["generate_evolution_dashboard"].schema["description"]
    assert "dashboard" in desc.lower()


def test_evolution_webapp_tool_schema():
    from ouroboros.tools.evolution_stats import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "generate_evolution_webapp" in tools
    desc = tools["generate_evolution_webapp"].schema["description"]
    assert "webapp" in desc.lower()

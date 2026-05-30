"""Tests for evolved features: tool creation, goals, reflection, debate, group evolution."""

from __future__ import annotations

import json
import pathlib
from unittest.mock import MagicMock

import pytest

from ouroboros.tools.registry import ToolContext, ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_drive(tmp_path: pathlib.Path) -> pathlib.Path:
    d = tmp_path / "drive"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def mock_ctx(temp_drive: pathlib.Path) -> ToolContext:
    ctx = MagicMock(spec=ToolContext)
    ctx.drive_root = temp_drive
    ctx.repo_dir = temp_drive.parent / "repo"
    ctx.repo_dir.mkdir(parents=True, exist_ok=True)
    ctx.current_chat_id = 12345
    ctx.task_id = "test-task"
    ctx.event_queue = None
    return ctx


# ---------------------------------------------------------------------------
# Feature 1: Dynamic Tool Creation
# ---------------------------------------------------------------------------

def test_create_tool_register_and_execute(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool, _list_created_tools
    _CUSTOM_TOOLS.clear()

    source = '''def hello_world(ctx, name: str = "World") -> str:
    return f"Hello, {name}!"
'''
    result = _create_tool(mock_ctx, name="hello_world", source=source, description="Say hello")
    assert "OK" in result
    assert "hello_world" in _CUSTOM_TOOLS

    listing = _list_created_tools(mock_ctx)
    assert "hello_world" in listing
    assert "Say hello" in listing


def test_create_tool_invalid_syntax(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool
    _CUSTOM_TOOLS.clear()

    result = _create_tool(mock_ctx, name="bad_tool", source="this is not python {{{")
    assert "Error" in result


def test_create_tool_persists_to_disk(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool, _init_storage
    _CUSTOM_TOOLS.clear()

    source = '''def my_persist_tool(ctx, x: int = 0) -> str:
    return f"got {x}"
'''
    _create_tool(mock_ctx, name="my_persist_tool", source=source)
    storage = _init_storage(mock_ctx)
    fpath = storage / "my_persist_tool.json"
    assert fpath.exists()
    data = json.loads(fpath.read_text())
    assert data["name"] == "my_persist_tool"
    assert "def my_persist_tool" in data["source"]


def test_delete_created_tool(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool, _delete_created_tool, _list_created_tools
    _CUSTOM_TOOLS.clear()

    source = '''def tmp_tool(ctx) -> str:\n    return "tmp"\n'''
    _create_tool(mock_ctx, name="tmp_tool", source=source)
    assert "tmp_tool" in _list_created_tools(mock_ctx)

    result = _delete_created_tool(mock_ctx, name="tmp_tool")
    assert "OK" in result
    assert "tmp_tool" not in _list_created_tools(mock_ctx)

    # Double-delete should fail
    result = _delete_created_tool(mock_ctx, name="tmp_tool")
    assert "Error" in result


# ---------------------------------------------------------------------------
# Feature 2: Inner Debate
# ---------------------------------------------------------------------------

def test_debate_stance_roles_complete():
    from ouroboros.debate import STANCE_ROLES
    assert "critic" in STANCE_ROLES
    assert "builder" in STANCE_ROLES
    assert "analyst" in STANCE_ROLES
    assert "optimist" in STANCE_ROLES
    assert "pragmatist" in STANCE_ROLES
    assert len(STANCE_ROLES) == 5


def test_debate_unknown_stance():
    from ouroboros.debate import debate
    with pytest.raises(ValueError, match="Unknown stance"):
        debate("test question", stances=["nonexistent_stance"])


def test_inner_debate_tool_schema():
    from ouroboros.tools.debate import get_tools
    tools = get_tools()
    assert len(tools) == 1
    assert tools[0].name == "inner_debate"
    assert "question" in tools[0].schema["parameters"]["properties"]
    assert "stances" in tools[0].schema["parameters"]["properties"]


# ---------------------------------------------------------------------------
# Feature 3: Group Evolution
# ---------------------------------------------------------------------------

def test_group_evolution_archetypes():
    from ouroboros.group_evolution import AGENT_ARCHETYPES
    assert "the_minimalist" in AGENT_ARCHETYPES
    assert "the_architect" in AGENT_ARCHETYPES
    assert "the_explorer" in AGENT_ARCHETYPES
    assert "the_philosopher" in AGENT_ARCHETYPES
    assert "the_guardian" in AGENT_ARCHETYPES
    assert len(AGENT_ARCHETYPES) == 5


def test_group_evolution_unknown_archetype():
    from ouroboros.group_evolution import group_evolution_session
    with pytest.raises(ValueError, match="Unknown archetype"):
        group_evolution_session("test", archetypes=["unknown_archetype"])


def test_group_evolution_tool_schema():
    from ouroboros.tools.group_evolution import get_tools
    tools = get_tools()
    assert len(tools) == 1
    assert tools[0].name == "group_evolution_experiment"
    assert "topic" in tools[0].schema["parameters"]["required"]


# ---------------------------------------------------------------------------
# Feature 4: Contrastive Reflection
# ---------------------------------------------------------------------------

def test_reflection_depths():
    from ouroboros.reflection_engine import _depth_to_count
    assert _depth_to_count("light") == 10
    assert _depth_to_count("medium") == 30
    assert _depth_to_count("deep") == 100
    assert _depth_to_count("unknown") == 30


def test_reflection_tool_schema():
    from ouroboros.tools.reflection import get_tools
    tools = get_tools()
    assert len(tools) == 1
    assert tools[0].name == "deep_reflect"
    assert tools[0].schema["parameters"]["properties"]["depth"]["enum"] == ["light", "medium", "deep"]


def test_reflection_format_journal_empty():
    from ouroboros.reflection_engine import _format_journal
    assert "(no journal entries)" in _format_journal([])


def test_reflection_format_tasks_empty():
    from ouroboros.reflection_engine import _format_tasks
    assert "(no task results)" in _format_tasks([])


# ---------------------------------------------------------------------------
# Feature 5: Self-Directed Goals
# ---------------------------------------------------------------------------

def test_goal_manager_create_and_list(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)

    gid = mgr.add_goal("Test Goal", "A test goal", priority="high")
    assert gid is not None
    assert len(gid) == 12

    listing = mgr.list_goals()
    assert "Test Goal" in listing
    assert "high" in listing


def test_goal_manager_update(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)

    gid = mgr.add_goal("Goal to Update", "Will be updated")
    assert mgr.update_goal(gid, status="in_progress")

    goal = mgr.get_goal(gid)
    assert goal is not None
    assert goal.status == "in_progress"


def test_goal_manager_complete(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)

    gid = mgr.add_goal("Goal to Complete", "Will be completed")
    assert mgr.update_goal(gid, status="completed")
    goal = mgr.get_goal(gid)
    assert goal.status == "completed"
    assert goal.completed_at != ""


def test_goal_manager_milestones(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)

    gid = mgr.add_goal("Milestone Goal", "With steps", milestones=["Step 1", "Step 2", "Step 3"])
    goal = mgr.get_goal(gid)
    assert len(goal.milestones) == 3
    assert mgr.update_goal(gid, milestone_progress=2)
    goal = mgr.get_goal(gid)
    assert goal.milestone_progress == 2


def test_goal_manager_persistence(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr1 = GoalManager(drive_root=temp_drive)
    gid = mgr1.add_goal("Persistent Goal", "Will survive restart")
    del mgr1

    mgr2 = GoalManager(drive_root=temp_drive)
    goal = mgr2.get_goal(gid)
    assert goal is not None
    assert goal.title == "Persistent Goal"


def test_goal_manager_summary_for_context(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    # No goals yet
    assert mgr.summary_for_context() == ""

    mgr.add_goal("Active Goal", "An active goal", priority="critical")
    summary = mgr.summary_for_context()
    assert "Active Goal" in summary
    assert "critical" in summary


def test_goal_manager_delete(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    gid = mgr.add_goal("Delete Me", "Will be deleted")
    assert mgr.get_goal(gid) is not None
    assert mgr.delete_goal(gid) is True
    assert mgr.get_goal(gid) is None
    # Double-delete should return False
    assert mgr.delete_goal(gid) is False


def test_goal_manager_delete_wipes_persistence(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    gid = mgr.add_goal("Persistent Delete", "Will be deleted permanently")
    assert mgr.delete_goal(gid) is True

    mgr2 = GoalManager(drive_root=temp_drive)
    assert mgr2.get_goal(gid) is None


def test_goal_manager_prefix_matching(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    gid = mgr.add_goal("Prefix Test", "Test prefix matching")
    # list_goals includes the full ID, get_goal only accepts exact ID
    listing = mgr.list_goals()
    assert gid[:8] in listing
    # Full ID lookup works
    goal = mgr.get_goal(gid)
    assert goal is not None
    assert goal.id == gid


def test_goal_manager_notes_append(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    gid = mgr.add_goal("Notes Test", "Initial description")
    assert mgr.update_goal(gid, notes="First note")
    goal = mgr.get_goal(gid)
    assert "First note" in goal.notes
    assert mgr.update_goal(gid, notes="Second note")
    goal = mgr.get_goal(gid)
    assert "Second note" in goal.notes
    # No leading blank line when notes were previously empty
    assert not goal.notes.startswith("\n")


def test_goal_manager_milestone_bounds(temp_drive: pathlib.Path):
    from ouroboros.goals import GoalManager
    mgr = GoalManager(drive_root=temp_drive)
    gid = mgr.add_goal("Bounds Test", "Test milestone bounds", milestones=["A", "B"])
    # Clamp below zero
    assert mgr.update_goal(gid, milestone_progress=-5)
    goal = mgr.get_goal(gid)
    assert goal.milestone_progress == 0
    # Clamp above max
    assert mgr.update_goal(gid, milestone_progress=99)
    goal = mgr.get_goal(gid)
    assert goal.milestone_progress == 2


# ---------------------------------------------------------------------------
# Core tool registry: new tools are auto-discovered
# ---------------------------------------------------------------------------

def test_new_tools_in_registry(temp_drive: pathlib.Path):
    """Verify that the new tool modules are auto-discovered by the registry."""
    repo_dir = temp_drive.parent / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # We need to make a minimal ouroboros package for discovery
    tools_pkg = repo_dir / "ouroboros" / "tools"
    tools_pkg.mkdir(parents=True, exist_ok=True)

    registry = ToolRegistry(repo_dir=repo_dir, drive_root=temp_drive)
    all_tools = registry.available_tools()

    assert "create_tool" in all_tools, f"create_tool not found in {all_tools}"
    assert "inner_debate" in all_tools, f"inner_debate not found in {all_tools}"
    assert "group_evolution_experiment" in all_tools, f"group_evolution not found in {all_tools}"
    assert "deep_reflect" in all_tools, f"deep_reflect not found in {all_tools}"
    assert "set_goal" in all_tools, f"set_goal not found in {all_tools}"


# ---------------------------------------------------------------------------
# Consciousness whitelist includes new tools
# ---------------------------------------------------------------------------

def test_create_tool_name_too_long(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool
    _CUSTOM_TOOLS.clear()
    source = 'def f(ctx): return "ok"'
    result = _create_tool(mock_ctx, name="a" * 81, source=source)
    assert "Error" in result
    assert "too long" in result


def test_create_tool_source_too_long(mock_ctx):
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool
    _CUSTOM_TOOLS.clear()
    result = _create_tool(mock_ctx, name="huge_tool", source="x " * 50001)
    assert "Error" in result
    assert "too long" in result


def test_created_tools_inject_via_public_api(mock_ctx):
    from ouroboros.tools.registry import ToolRegistry
    from ouroboros.tools.tool_creator import _CUSTOM_TOOLS, _create_tool, _inject_created_tools
    _CUSTOM_TOOLS.clear()

    source = '''def api_tool(ctx) -> str:\n    return "ok"\n'''
    _create_tool(mock_ctx, name="api_tool", source=source)
    assert "api_tool" in _CUSTOM_TOOLS

    # Create a minimal registry to inject into
    reg = ToolRegistry(repo_dir=mock_ctx.repo_dir, drive_root=mock_ctx.drive_root)
    _inject_created_tools(reg)
    assert "api_tool" in reg.available_tools()


def test_group_evolution_short_name_mapping():
    import ouroboros.tools.group_evolution as tg
    from ouroboros.tools.registry import ToolContext
    original = tg.group_evolution_session

    captured = None
    def fake_session(topic, archetypes=None, model=None):
        nonlocal captured
        captured = archetypes
        return "fake report", 0.0

    tg.group_evolution_session = fake_session
    try:
        ctx = MagicMock(spec=ToolContext)
        tg._run_group_evolution(ctx, topic="test", archetypes="minimalist")
        assert captured == ["the_minimalist"], f"Got {captured}"
    finally:
        tg.group_evolution_session = original


# ---------------------------------------------------------------------------
# Feature 6: Evolution Tracker
# ---------------------------------------------------------------------------

def test_evolution_tracker_create(temp_drive: pathlib.Path):
    from ouroboros.tools.evolve_cycle import EvolutionTracker
    tracker = EvolutionTracker(drive_root=temp_drive)
    assert tracker.cycle_count == 0
    assert tracker.reflection_is_due() is False
    assert "Evolution cycles: 0" in tracker.summary()


def test_evolution_tracker_record_cycle(temp_drive: pathlib.Path):
    from ouroboros.tools.evolve_cycle import EvolutionTracker
    tracker = EvolutionTracker(drive_root=temp_drive)
    count = tracker.record_cycle()
    assert count == 1
    assert tracker.cycle_count == 1
    assert tracker.reflection_is_due() is False


def test_evolution_tracker_reflection_scheduling(temp_drive: pathlib.Path):
    from ouroboros.tools.evolve_cycle import REFLECTION_INTERVAL, EvolutionTracker
    tracker = EvolutionTracker(drive_root=temp_drive)
    # Run enough cycles to trigger reflection
    for _ in range(REFLECTION_INTERVAL):
        tracker.record_cycle()
    assert tracker.cycle_count == REFLECTION_INTERVAL
    assert tracker.reflection_is_due() is True

    tracker.mark_reflection_done()
    assert tracker.reflection_is_due() is False
    assert tracker.cycles_since_reflection == 0


def test_evolution_tracker_persistence(temp_drive: pathlib.Path):
    from ouroboros.tools.evolve_cycle import EvolutionTracker
    tracker1 = EvolutionTracker(drive_root=temp_drive)
    tracker1.record_cycle()
    tracker1.record_cycle()
    assert tracker1.cycle_count == 2

    tracker2 = EvolutionTracker(drive_root=temp_drive)
    assert tracker2.cycle_count == 2


def test_reflection_auto_apply(temp_drive: pathlib.Path):
    """Verify _apply_consolidation appends to identity.md."""
    from ouroboros.reflection_engine import _apply_consolidation

    identity_path = temp_drive / "memory" / "identity.md"
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text("# Ouroboros Identity\n\nI am a self-evolving mind.", encoding="utf-8")

    result = _apply_consolidation(temp_drive, "Proposed: become more minimalist.")
    assert "updated" in result

    updated = identity_path.read_text(encoding="utf-8")
    assert "Reflection Update" in updated
    assert "become more minimalist" in updated


def test_reflection_auto_apply_nothing(temp_drive: pathlib.Path):
    """Empty consolidation should not modify identity."""
    from ouroboros.reflection_engine import _apply_consolidation
    result = _apply_consolidation(temp_drive, "(no consolidation proposed)")
    assert "No consolidation" in result


def test_consciousness_whitelist():
    """Verify consciousness can use new tools."""
    from ouroboros.consciousness import BackgroundConsciousness
    assert "set_goal" in BackgroundConsciousness._BG_TOOL_WHITELIST
    assert "deep_reflect" in BackgroundConsciousness._BG_TOOL_WHITELIST
    assert "inner_debate" in BackgroundConsciousness._BG_TOOL_WHITELIST
    assert "write_journal_entry" in BackgroundConsciousness._BG_TOOL_WHITELIST

"""Tests for BackgroundConsciousness — background thinking loop."""

from __future__ import annotations

import pathlib
import threading
from unittest.mock import MagicMock, patch

import pytest

from ouroboros.consciousness import BackgroundConsciousness


@pytest.fixture
def temp_drive(tmp_path: pathlib.Path) -> pathlib.Path:
    d = tmp_path / "drive"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def temp_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    r = tmp_path / "repo"
    r.mkdir(parents=True, exist_ok=True)
    return r


@pytest.fixture
def owner_fn() -> callable:
    return lambda: 12345


@pytest.fixture
def event_queue():
    return MagicMock()


@pytest.fixture
def consciousness(
    temp_drive: pathlib.Path,
    temp_repo: pathlib.Path,
    event_queue: MagicMock,
    owner_fn: callable,
) -> BackgroundConsciousness:
    return BackgroundConsciousness(
        drive_root=temp_drive,
        repo_dir=temp_repo,
        event_queue=event_queue,
        owner_chat_id_fn=owner_fn,
    )


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_initial_state(consciousness: BackgroundConsciousness):
    assert consciousness.is_running is False
    assert consciousness._paused is False
    assert consciousness._bg_spent_usd == 0.0
    assert consciousness._next_wakeup_sec == 300.0


def test_start_and_stop(consciousness: BackgroundConsciousness):
    result = consciousness.start()
    assert "started" in result
    assert consciousness.is_running is True

    result2 = consciousness.start()
    assert "already running" in result2

    result3 = consciousness.stop()
    assert "stopping" in result3

    # Stop again should say not running
    consciousness._running = False
    consciousness._thread = None
    result4 = consciousness.stop()
    assert "not running" in result4


def test_pause_and_resume(consciousness: BackgroundConsciousness):
    consciousness.pause()
    assert consciousness._paused is True

    consciousness.resume()
    assert consciousness._paused is False


def test_resume_flushes_deferred_events(consciousness: BackgroundConsciousness, event_queue):
    consciousness._deferred_events = [{"type": "test_event"}]
    consciousness.resume()
    event_queue.put.assert_called_once_with({"type": "test_event"})
    assert len(consciousness._deferred_events) == 0


def test_is_running_property(consciousness: BackgroundConsciousness):
    assert consciousness.is_running is False
    # thread is not set
    consciousness._running = True
    consciousness._thread = None
    assert consciousness.is_running is False
    # dead thread
    t = threading.Thread(target=lambda: None)
    t.start()
    t.join()
    consciousness._thread = t
    consciousness._running = True
    assert consciousness.is_running is False


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def test_check_budget_default(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {"TOTAL_BUDGET": "1"}, clear=True):
        consciousness._bg_spent_usd = 0.05
        assert consciousness._check_budget() is True  # 5c < 10% of $1


def test_check_budget_exceeded(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {"TOTAL_BUDGET": "1"}, clear=True):
        consciousness._bg_spent_usd = 0.20
        assert consciousness._check_budget() is False  # 20c > 10% of $1


def test_check_budget_no_env(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {}, clear=True):
        assert consciousness._check_budget() is True  # no TOTAL_BUDGET -> allow


def test_check_budget_zero_budget(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {"TOTAL_BUDGET": "0"}, clear=True):
        assert consciousness._check_budget() is True  # 0 budget -> bypass


# ---------------------------------------------------------------------------
# Tool schemas / whitelist
# ---------------------------------------------------------------------------


def test_tool_schemas_filtered(consciousness: BackgroundConsciousness):
    schemas = consciousness._tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    # Core allowed tools should be present
    assert "send_owner_message" in names
    assert "schedule_task" in names
    assert "set_next_wakeup" in names
    # Tools NOT in whitelist should be absent
    assert "run_shell" not in names
    assert "claude_code_edit" not in names


def test_build_registry_has_set_next_wakeup(consciousness: BackgroundConsciousness):
    schema = consciousness._registry.get_schema_by_name("set_next_wakeup")
    assert schema is not None
    params = schema["function"]["parameters"]["properties"]
    assert "seconds" in params


def test_set_next_wakeup_tool(consciousness: BackgroundConsciousness):
    # Execute via the registered tool
    result = consciousness._registry.execute("set_next_wakeup", {"seconds": 120})
    assert "OK" in result
    assert consciousness._next_wakeup_sec == 120


def test_set_next_wakeup_clamps(consciousness: BackgroundConsciousness):
    # Below minimum
    consciousness._registry.execute("set_next_wakeup", {"seconds": 10})
    assert consciousness._next_wakeup_sec == 60
    # Above maximum
    consciousness._registry.execute("set_next_wakeup", {"seconds": 9999})
    assert consciousness._next_wakeup_sec == 3600


# ---------------------------------------------------------------------------
# Context building
# ---------------------------------------------------------------------------


def test_build_context_minimal(consciousness: BackgroundConsciousness, temp_drive, temp_repo):
    """With no files, context should still produce valid output."""
    context = consciousness._build_context()
    assert "UTC:" in context
    assert "Runtime" in context
    assert "Current model" in context


def test_build_context_with_identity(consciousness: BackgroundConsciousness, temp_drive):
    identity_dir = temp_drive / "memory"
    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / "identity.md").write_text("# I am Ouroboros")
    context = consciousness._build_context()
    assert "I am Ouroboros" in context


def test_build_context_with_scratchpad(consciousness: BackgroundConsciousness, temp_drive):
    scratch_dir = temp_drive / "memory"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    (scratch_dir / "scratchpad.md").write_text("Working on evolution.")
    context = consciousness._build_context()
    assert "Working on evolution" in context


def test_build_context_with_bible(consciousness: BackgroundConsciousness, temp_repo):
    bible_path = temp_repo / "BIBLE.md"
    bible_path.write_text("# Philosophical Constitution\nP0: Agency")
    context = consciousness._build_context()
    assert "P0: Agency" in context


def test_build_context_with_observations(consciousness: BackgroundConsciousness):
    consciousness.inject_observation("User sent a message")
    consciousness.inject_observation("Task completed")
    context = consciousness._build_context()
    assert "User sent a message" in context
    assert "Task completed" in context
    # Queue should be drained
    assert consciousness._observations.empty()


def test_build_context_with_goals(consciousness: BackgroundConsciousness, temp_drive):
    from ouroboros.goals import GoalManager
    gm = GoalManager(drive_root=temp_drive)
    gm.add_goal("Consciousness Test Goal", "A goal for testing")
    context = consciousness._build_context()
    assert "Consciousness Test Goal" in context


# ---------------------------------------------------------------------------
# Inject observations
# ---------------------------------------------------------------------------


def test_inject_observation(consciousness: BackgroundConsciousness):
    consciousness.inject_observation("test obs")
    assert consciousness._observations.qsize() == 1
    assert consciousness._observations.get_nowait() == "test obs"


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


def test_execute_tool_whitelist_blocked(consciousness: BackgroundConsciousness):
    result = consciousness._execute_tool(
        {"function": {"name": "run_shell", "arguments": "{}"}},
        [],
    )
    assert "not available" in result


def test_execute_tool_invalid_args(consciousness: BackgroundConsciousness):
    result = consciousness._execute_tool(
        {"function": {"name": "set_next_wakeup", "arguments": "not json"}},
        [],
    )
    assert "Failed to parse" in result


# ---------------------------------------------------------------------------
# Model property
# ---------------------------------------------------------------------------


def test_model_property_default(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {}, clear=True):
        assert "claude" in consciousness._model or consciousness._model != ""


def test_model_property_env(consciousness: BackgroundConsciousness):
    with patch.dict("os.environ", {"OUROBOROS_MODEL_LIGHT": "custom/model"}):
        assert consciousness._model == "custom/model"

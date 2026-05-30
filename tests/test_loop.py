"""Tests for the main agent loop — pricing, estimation, tool execution, timeout, budget."""

from __future__ import annotations

import pathlib
import queue
from unittest.mock import MagicMock

import pytest

from ouroboros.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Pricing & cost estimation
# ---------------------------------------------------------------------------


def test_estimate_cost_known_model():
    from ouroboros.loop import _estimate_cost, _get_pricing
    pricing = _get_pricing()
    assert len(pricing) > 0
    cost = _estimate_cost("anthropic/claude-sonnet-4.6", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0


def test_estimate_cost_unknown_model():
    from ouroboros.loop import _estimate_cost
    cost = _estimate_cost("unknown/model/v99", prompt_tokens=1000, completion_tokens=500)
    assert cost == 0.0


def test_estimate_cost_zero_tokens():
    from ouroboros.loop import _estimate_cost
    cost = _estimate_cost("anthropic/claude-sonnet-4.6", prompt_tokens=0, completion_tokens=0)
    assert cost == 0.0


def test_estimate_cost_cached_tokens():
    from ouroboros.loop import _estimate_cost
    without_cache = _estimate_cost("anthropic/claude-sonnet-4.6", prompt_tokens=2000, completion_tokens=500, cached_tokens=0)
    with_cache = _estimate_cost("anthropic/claude-sonnet-4.6", prompt_tokens=2000, completion_tokens=500, cached_tokens=1500)
    assert with_cache < without_cache


def test_get_pricing_returns_static():
    from ouroboros.loop import _get_pricing
    pricing = _get_pricing()
    assert "anthropic/claude-sonnet-4.6" in pricing
    assert "openai/gpt-4o" in pricing
    assert "google/gemini-2.0-flash-001" in pricing


# ---------------------------------------------------------------------------
# _truncate_tool_result
# ---------------------------------------------------------------------------


def test_truncate_tool_result_short():
    from ouroboros.loop import _truncate_tool_result
    result = _truncate_tool_result("short result")
    assert result == "short result"


def test_truncate_tool_result_long():
    from ouroboros.loop import _truncate_tool_result
    long_str = "x" * 20000
    result = _truncate_tool_result(long_str)
    assert len(result) <= 15000 + 50
    assert "truncated from 20000" in result


def test_truncate_tool_result_non_string():
    from ouroboros.loop import _truncate_tool_result
    result = _truncate_tool_result(42)
    assert result == "42"


# ---------------------------------------------------------------------------
# _execute_single_tool
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_logs(tmp_path: pathlib.Path) -> pathlib.Path:
    logs = tmp_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


@pytest.fixture
def registry(tmp_path: pathlib.Path) -> ToolRegistry:
    repo = tmp_path / "repo"
    drive = tmp_path / "drive"
    repo.mkdir(parents=True, exist_ok=True)
    drive.mkdir(parents=True, exist_ok=True)
    return ToolRegistry(repo_dir=repo, drive_root=drive)


def test_execute_single_tool_success(registry: ToolRegistry, temp_logs: pathlib.Path):
    from ouroboros.loop import _execute_single_tool
    tc = {"id": "call_1", "function": {"name": "web_search", "arguments": '{"query": "hello"}'}}
    result = _execute_single_tool(registry, tc, temp_logs)
    assert result["tool_call_id"] == "call_1"
    assert result["fn_name"] == "web_search"
    assert result["is_error"] is False


def test_execute_single_tool_invalid_args(registry: ToolRegistry, temp_logs: pathlib.Path):
    from ouroboros.loop import _execute_single_tool
    tc = {"id": "call_2", "function": {"name": "web_search", "arguments": "not json"}}
    result = _execute_single_tool(registry, tc, temp_logs)
    assert result["is_error"] is True
    assert "TOOL_ARG_ERROR" in result["result"]


def test_execute_single_tool_unknown(registry: ToolRegistry, temp_logs: pathlib.Path):
    from ouroboros.loop import _execute_single_tool
    tc = {"id": "call_3", "function": {"name": "nonexistent_tool", "arguments": "{}"}}
    result = _execute_single_tool(registry, tc, temp_logs)
    assert result["is_error"] is True
    assert "Unknown tool" in result["result"]


# ---------------------------------------------------------------------------
# _make_timeout_result
# ---------------------------------------------------------------------------


def test_make_timeout_result(temp_logs: pathlib.Path):
    from ouroboros.loop import _make_timeout_result
    tc = {"id": "call_4", "function": {"name": "web_search", "arguments": '{"q": "test"}'}}
    result = _make_timeout_result(
        fn_name="web_search",
        tool_call_id="call_4",
        is_code_tool=False,
        tc=tc,
        drive_logs=temp_logs,
        timeout_sec=30,
    )
    assert result["is_error"] is True
    assert "TOOL_TIMEOUT" in result["result"]
    assert "30s" in result["result"]


# ---------------------------------------------------------------------------
# _check_budget_limits
# ---------------------------------------------------------------------------


def test_check_budget_limits_none_budget():
    from ouroboros.loop import _check_budget_limits
    result = _check_budget_limits(
        budget_remaining_usd=None,
        accumulated_usage={},
        round_idx=1,
        messages=[{"role": "user", "content": "Hi"}],
        llm=MagicMock(),
        active_model="test/model",
        active_effort="medium",
        max_retries=2,
        drive_logs=MagicMock(),
        task_id="test",
        event_queue=None,
        llm_trace={"assistant_notes": []},
    )
    assert result is None  # No budget configured, continue


def test_check_budget_limits_under_threshold():
    from ouroboros.loop import _check_budget_limits
    result = _check_budget_limits(
        budget_remaining_usd=10.0,
        accumulated_usage={"cost": 0.5},
        round_idx=1,
        messages=[],
        llm=MagicMock(),
        active_model="test/model",
        active_effort="medium",
        max_retries=2,
        drive_logs=MagicMock(),
        task_id="test",
        event_queue=None,
        llm_trace={"assistant_notes": []},
    )
    assert result is None  # Under threshold, continue


def test_check_budget_limits_hard_stop():
    from ouroboros.loop import _check_budget_limits
    result = _check_budget_limits(
        budget_remaining_usd=10.0,
        accumulated_usage={"cost": 6.0},  # >50% of remaining
        round_idx=1,
        messages=[{"role": "user", "content": "Hi"}],
        llm=MagicMock(),
        active_model="test/model",
        active_effort="medium",
        max_retries=1,
        drive_logs=MagicMock(),
        task_id="test",
        event_queue=None,
        llm_trace={"assistant_notes": []},
    )
    assert result is not None
    assert "Budget" in result[0]


# ---------------------------------------------------------------------------
# _maybe_inject_self_check
# ---------------------------------------------------------------------------


def test_maybe_inject_self_check_not_checkpoint():
    from ouroboros.loop import _maybe_inject_self_check
    messages = [{"role": "user", "content": "Hi"}]
    _maybe_inject_self_check(
        round_idx=3,  # Not a checkpoint round
        max_rounds=100,
        messages=messages,
        accumulated_usage={"cost": 0.1},
        emit_progress=lambda s: None,
    )
    assert len(messages) == 1  # Nothing injected


def test_maybe_inject_self_check_at_checkpoint():
    from ouroboros.loop import _maybe_inject_self_check
    messages = [{"role": "user", "content": "Hi"}]
    _maybe_inject_self_check(
        round_idx=5,  # Checkpoint round
        max_rounds=100,
        messages=messages,
        accumulated_usage={"cost": 0.5},
        emit_progress=lambda s: None,
    )
    assert len(messages) == 2
    assert "CHECKPOINT" in messages[1]["content"]


# ---------------------------------------------------------------------------
# _safe_args
# ---------------------------------------------------------------------------


def test_safe_args_simple():
    from ouroboros.loop import _safe_args
    result = _safe_args({"key": "value"})
    assert result == {"key": "value"}


# ---------------------------------------------------------------------------
# _StatefulToolExecutor
# ---------------------------------------------------------------------------


def test_stateful_executor_submit_and_reset():
    from ouroboros.loop import _StatefulToolExecutor
    ex = _StatefulToolExecutor()

    result = []
    def append_val(v):
        result.append(v)
        return v

    future = ex.submit(append_val, 42)
    assert future.result() == 42
    assert len(result) == 1

    ex.reset()
    ex.submit(append_val, 99)
    assert result[-1] == 99

    ex.shutdown(wait=True)


# ---------------------------------------------------------------------------
# _emit_llm_usage_event
# ---------------------------------------------------------------------------


def test_emit_llm_usage_event():
    from ouroboros.loop import _emit_llm_usage_event
    q = queue.Queue()
    _emit_llm_usage_event(
        event_queue=q,
        task_id="task_1",
        model="test/model",
        usage={"prompt_tokens": 100, "completion_tokens": 50},
        cost=0.001,
    )
    assert not q.empty()
    evt = q.get_nowait()
    assert evt["type"] == "llm_usage"
    assert evt["cost"] == 0.001


def test_emit_llm_usage_event_no_queue():
    from ouroboros.loop import _emit_llm_usage_event
    _emit_llm_usage_event(event_queue=None, task_id="t", model="m", usage={}, cost=0)
    # Should not raise

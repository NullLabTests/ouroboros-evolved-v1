"""Tests for context builder — message assembly, compaction, token capping."""

from __future__ import annotations

import json
from unittest.mock import patch

from ouroboros.context import (
    _build_user_content,
    _compact_tool_call_arguments,
    _compact_tool_result,
    apply_message_token_soft_cap,
    compact_tool_history,
)

# ---------------------------------------------------------------------------
# _build_user_content
# ---------------------------------------------------------------------------


def test_user_content_text_only():
    result = _build_user_content({"text": "Hello world"})
    assert result == "Hello world"


def test_user_content_empty():
    result = _build_user_content({})
    assert result == "(empty message)"


def test_user_content_with_image():
    result = _build_user_content({
        "text": "What's in this image?",
        "image_base64": "abc123",
        "image_mime": "image/png",
    })
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["type"] == "text"
    assert "What's in this image?" in result[0]["text"]
    assert result[1]["type"] == "image_url"
    assert "data:image/png;base64,abc123" in result[1]["image_url"]["url"]


def test_user_content_image_no_text():
    result = _build_user_content({
        "image_base64": "abc123",
    })
    assert isinstance(result, list)
    assert result[0]["text"] == "Analyze the screenshot"


def test_user_content_image_with_caption():
    result = _build_user_content({
        "image_base64": "abc123",
        "image_caption": "Dashboard screenshot",
    })
    assert isinstance(result, list)
    assert "Dashboard screenshot" in result[0]["text"]


# ---------------------------------------------------------------------------
# _compact_tool_call_arguments
# ---------------------------------------------------------------------------


def test_compact_small_args():
    result = _compact_tool_call_arguments("web_search", '{"query": "hello"}')
    assert result["name"] == "web_search"
    assert result["arguments"] == '{"query": "hello"}'


def test_compact_large_content_field():
    args = json.dumps({"content": "x" * 5000, "path": "test.py"})
    result = _compact_tool_call_arguments("repo_write_commit", args)
    parsed = json.loads(result["arguments"])
    assert parsed["content"] == {"_truncated": True}
    assert parsed["path"] == "test.py"


def test_compact_other_large_args():
    args = json.dumps({"long_field": "x" * 600})
    result = _compact_tool_call_arguments("web_search", args)
    assert "..." in result["arguments"]
    assert len(result["arguments"]) < 300


def test_compact_invalid_json():
    result = _compact_tool_call_arguments("web_search", "not json")
    assert result["name"] == "web_search"


# ---------------------------------------------------------------------------
# _compact_tool_result
# ---------------------------------------------------------------------------


def test_compact_tool_result_short():
    msg = {"role": "tool", "tool_call_id": "call_1", "content": "short result"}
    result = _compact_tool_result(msg, "short result")
    assert result["content"] == "short result"


def test_compact_tool_result_long():
    long_content = "x" * 300
    msg = {"role": "tool", "tool_call_id": "call_1", "content": long_content}
    result = _compact_tool_result(msg, long_content)
    assert len(result["content"]) < len(long_content)
    assert "..." in result["content"]


# ---------------------------------------------------------------------------
# apply_message_token_soft_cap
# ---------------------------------------------------------------------------


def test_token_cap_no_op_when_under():
    messages = [{"role": "user", "content": "Hello"}]
    pruned, info = apply_message_token_soft_cap(messages, soft_cap_tokens=100_000)
    assert pruned == messages
    assert info["trimmed_sections"] == []


def test_token_cap_removes_prunable_section():
    messages = [
        {"role": "system", "content": "## Recent chat\nlong history here\n## Other\nstuff"},
    ]
    with patch("ouroboros.context.estimate_tokens", return_value=100):
        pruned, info = apply_message_token_soft_cap(messages, soft_cap_tokens=50)
    # String content that starts with prunable prefix gets the whole message removed
    assert len(pruned) == 0
    assert "## Recent chat" in info["trimmed_sections"]


def test_token_cap_handles_multipart():
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "## Recent chat\nlong\n## Other\nstuff"},
            ],
        },
    ]
    with patch("ouroboros.context.estimate_tokens", return_value=100):
        pruned, info = apply_message_token_soft_cap(messages, soft_cap_tokens=50)
    assert "## Recent chat" not in pruned[0]["content"][0]["text"]


def test_token_cap_negative_cap_returns_unchanged():
    messages = [{"role": "user", "content": "Hello"}]
    pruned, info = apply_message_token_soft_cap(messages, soft_cap_tokens=-1)
    assert pruned == messages


# ---------------------------------------------------------------------------
# compact_tool_history
# ---------------------------------------------------------------------------


def make_tool_msg(tool: str, i: int) -> list:
    """Helper: produce a tool-call round pair."""
    return [
        {"role": "assistant", "tool_calls": [
            {"id": f"call_{i}", "function": {"name": tool, "arguments": "{}"}}
        ], "content": f"Using {tool}"},
        {"role": "tool", "tool_call_id": f"call_{i}", "content": f"Result {i}"},
    ]


def test_compact_tool_history_below_threshold():
    """With fewer rounds than keep_recent, nothing should change."""
    messages = []
    for i in range(4):
        messages.extend(make_tool_msg("web_search", i))
    result = compact_tool_history(messages, keep_recent=6)
    assert len(result) == len(messages)


def test_compact_tool_history_compacts_old_rounds():
    """Old rounds should have their tool results truncated."""
    messages = []
    for i in range(10):
        messages.extend(make_tool_msg("web_search", i))
    result = compact_tool_history(messages, keep_recent=6)
    assert len(result) == len(messages)  # Same count, just compacted
    # First few tool results should be compacted (shorter)
    for i, msg in enumerate(result):
        if msg.get("role") == "tool" and i < 4:  # First few pairs compacted
            assert len(msg["content"]) <= 120


def test_compact_tool_history_preserves_recent():
    """Recent rounds (within keep_recent) should be preserved as-is."""
    messages = []
    for i in range(10):
        messages.extend(make_tool_msg("repo_write_commit", i))
    result = compact_tool_history(messages, keep_recent=6)
    # Last tool result should be intact
    last_tool_idx = None
    for i, msg in enumerate(reversed(result)):
        if msg.get("role") == "tool":
            last_tool_idx = len(result) - 1 - i
            break
    if last_tool_idx is not None:
        assert "Result" in result[last_tool_idx]["content"]


def test_compact_tool_history_system_multipart_preserved():
    messages = [
        {"role": "system", "content": [{"type": "text", "text": "You are a helpful assistant."}]},
    ]
    for i in range(10):
        messages.extend(make_tool_msg("web_search", i))
    result = compact_tool_history(messages)
    assert result[0]["role"] == "system"
    assert isinstance(result[0]["content"], list)


# ---------------------------------------------------------------------------
# Integration: known cybersigilism token counts
# ---------------------------------------------------------------------------


def test_estimate_tokens_available():
    """estimate_tokens should be importable and functional."""
    from ouroboros.utils import estimate_tokens
    result = estimate_tokens("Hello world")
    assert isinstance(result, int)
    assert result > 0

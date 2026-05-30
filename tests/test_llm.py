"""Tests for LLM client — reasoning effort, usage tracking, chat, vision."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ouroboros.llm import (
    LLMClient,
    add_usage,
    normalize_reasoning_effort,
    reasoning_rank,
)


# ---------------------------------------------------------------------------
# normalize_reasoning_effort
# ---------------------------------------------------------------------------


def test_normalize_valid():
    assert normalize_reasoning_effort("low") == "low"
    assert normalize_reasoning_effort("high") == "high"
    assert normalize_reasoning_effort("medium") == "medium"
    assert normalize_reasoning_effort("xhigh") == "xhigh"
    assert normalize_reasoning_effort("none") == "none"
    assert normalize_reasoning_effort("minimal") == "minimal"


def test_normalize_invalid_defaults():
    assert normalize_reasoning_effort("extreme") == "medium"
    assert normalize_reasoning_effort("") == "medium"
    assert normalize_reasoning_effort(None) == "medium"
    assert normalize_reasoning_effort("") == "medium"
    assert normalize_reasoning_effort("  ") == "medium"


def test_normalize_case_insensitive():
    assert normalize_reasoning_effort("HIGH") == "high"
    assert normalize_reasoning_effort("Low") == "low"
    assert normalize_reasoning_effort("None") == "none"


def test_normalize_custom_default():
    assert normalize_reasoning_effort("invalid", default="low") == "low"
    assert normalize_reasoning_effort(None, default="none") == "none"


# ---------------------------------------------------------------------------
# reasoning_rank
# ---------------------------------------------------------------------------


def test_reasoning_rank_values():
    assert reasoning_rank("none") == 0
    assert reasoning_rank("minimal") == 1
    assert reasoning_rank("low") == 2
    assert reasoning_rank("medium") == 3
    assert reasoning_rank("high") == 4
    assert reasoning_rank("xhigh") == 5


def test_reasoning_rank_unknown():
    assert reasoning_rank("unknown") == 3
    assert reasoning_rank("") == 3
    assert reasoning_rank(None) == 3


# ---------------------------------------------------------------------------
# add_usage
# ---------------------------------------------------------------------------


def test_add_usage_empty_total():
    total = {}
    add_usage(total, {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.01})
    assert total["prompt_tokens"] == 100
    assert total["completion_tokens"] == 50
    assert total["cost"] == 0.01


def test_add_usage_accumulates():
    total = {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.01}
    add_usage(total, {"prompt_tokens": 200, "completion_tokens": 30, "cost": 0.02})
    assert total["prompt_tokens"] == 300
    assert total["completion_tokens"] == 80
    assert total["cost"] == 0.03


def test_add_usage_missing_keys():
    total = {}
    add_usage(total, {})
    assert total["prompt_tokens"] == 0
    assert total.get("cost") is None


def test_add_usage_cached_tokens():
    total = {}
    add_usage(total, {"cached_tokens": 500})
    assert total["cached_tokens"] == 500


# ---------------------------------------------------------------------------
# LLMClient — model methods
# ---------------------------------------------------------------------------


def test_default_model_from_env():
    with patch.dict("os.environ", {"OUROBOROS_MODEL": "test/model"}, clear=True):
        client = LLMClient()
        assert client.default_model() == "test/model"


def test_default_model_fallback():
    with patch.dict("os.environ", {}, clear=True):
        client = LLMClient()
        assert client.default_model() == "anthropic/claude-sonnet-4.6"


def test_available_models_all_unique():
    with patch.dict("os.environ", {
        "OUROBOROS_MODEL": "model/a",
        "OUROBOROS_MODEL_CODE": "model/b",
        "OUROBOROS_MODEL_LIGHT": "model/c",
    }, clear=True):
        client = LLMClient()
        models = client.available_models()
        assert len(models) == 3
        assert "model/a" in models
        assert "model/b" in models
        assert "model/c" in models


def test_available_models_no_duplicates():
    with patch.dict("os.environ", {
        "OUROBOROS_MODEL": "model/a",
        "OUROBOROS_MODEL_CODE": "model/a",
        "OUROBOROS_MODEL_LIGHT": "model/a",
    }, clear=True):
        client = LLMClient()
        models = client.available_models()
        assert len(models) == 1
        assert models == ["model/a"]


# ---------------------------------------------------------------------------
# LLMClient — chat (mocked)
# ---------------------------------------------------------------------------


def _mock_response(content: str = "Hello!", tool_calls: list | None = None,
                   cost: float = 0.001, tokens: int = 100) -> MagicMock:
    """Build a mock OpenAI chat completion response."""
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls

    choice = MagicMock()
    choice.message.model_dump.return_value = msg

    resp = MagicMock()
    resp.model_dump.return_value = {
        "id": "gen_abc123",
        "usage": {
            "prompt_tokens": tokens,
            "completion_tokens": tokens // 2,
            "total_tokens": tokens + tokens // 2,
            "cost": cost,
        },
        "choices": [{"message": msg}],
    }
    return resp


def test_chat_simple():
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = _mock_response()

        msg, usage = client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="test/model",
        )
    assert msg.get("content") == "Hello!"
    assert usage.get("cost") == 0.001


def test_chat_with_tools():
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_get.return_value.chat.completions.create.return_value = _mock_response(
            tool_calls=[{
                "id": "call_1",
                "function": {"name": "web_search", "arguments": '{"q": "hello"}'},
            }],
        )

        msg, usage = client.chat(
            messages=[{"role": "user", "content": "Search"}],
            model="test/model",
            tools=[{"function": {"name": "web_search"}}],
        )
    assert msg.get("tool_calls") is not None
    assert msg["tool_calls"][0]["function"]["name"] == "web_search"


def test_chat_anthropic_pinned():
    """Anthropic models should be pinned with provider settings."""
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create
        mock_create.return_value = _mock_response()

        client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="anthropic/claude-sonnet-4.6",
        )

        call_kwargs = mock_create.call_args[1]
        extra_body = call_kwargs["extra_body"]
        assert extra_body["provider"]["order"] == ["Anthropic"]
        assert extra_body["provider"]["allow_fallbacks"] is False


def test_chat_no_tools_skips_cache_control():
    """When no tools provided, cache_control should not be added."""
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create
        mock_create.return_value = _mock_response()

        client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="test/model",
        )

        call_kwargs = mock_create.call_args[1]
        assert "tools" not in call_kwargs


def test_chat_extracts_cached_tokens_from_details():
    """When usage has prompt_tokens_details with cached_tokens, extract it."""
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create

        resp = MagicMock()
        resp.model_dump.return_value = {
            "id": "gen_abc",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 50,
                "total_tokens": 250,
                "prompt_tokens_details": {"cached_tokens": 150},
            },
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }
        mock_create.return_value = resp

        _, usage = client.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="test/model",
        )
    assert usage.get("cached_tokens") == 150


# ---------------------------------------------------------------------------
# LLMClient — vision_query (mocked)
# ---------------------------------------------------------------------------


def test_vision_query_url():
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create
        mock_create.return_value = _mock_response(content="I see a cat.")

        text, usage = client.vision_query(
            prompt="What's in this image?",
            images=[{"url": "https://example.com/cat.jpg"}],
            model="test/vision-model",
        )
    assert text == "I see a cat."
    # Verify the image was passed correctly
    call_kwargs = mock_create.call_args[1]
    content = call_kwargs["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "https://example.com/cat.jpg" in content[1]["image_url"]["url"]


def test_vision_query_base64():
    client = LLMClient(api_key="sk-test")
    with patch.object(client, "_get_client") as mock_get:
        mock_create = mock_get.return_value.chat.completions.create
        mock_create.return_value = _mock_response(content="Base64 image analyzed.")

        text, usage = client.vision_query(
            prompt="Analyze",
            images=[{"base64": "abc123==", "mime": "image/png"}],
        )
    assert text == "Base64 image analyzed."
    call_kwargs = mock_create.call_args[1]
    content = call_kwargs["messages"][0]["content"]
    assert "data:image/png;base64,abc123==" in content[1]["image_url"]["url"]


# ---------------------------------------------------------------------------
# Default model constant
# ---------------------------------------------------------------------------


def test_default_light_model():
    from ouroboros.llm import DEFAULT_LIGHT_MODEL
    assert DEFAULT_LIGHT_MODEL == "google/gemini-3-pro-preview"

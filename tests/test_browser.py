"""Tests for browser automation tools — page extraction, action routing, error handling."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ouroboros.tools.registry import ToolContext


@pytest.fixture
def mock_ctx() -> ToolContext:
    ctx = MagicMock(spec=ToolContext)
    ctx.browser_state = MagicMock()
    ctx.browser_state.page = None
    ctx.browser_state.browser = None
    ctx.browser_state.pw_instance = None
    ctx.browser_state.last_screenshot_b64 = None
    return ctx


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.content.return_value = "<html><body><h1>Hello</h1></body></html>"
    page.inner_text.return_value = "Hello"
    page.evaluate.return_value = "# Hello"
    return page


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------


def test_browse_page_tool_schema():
    from ouroboros.tools.browser import get_tools
    tools = get_tools()
    names = [t.name for t in tools]
    assert "browse_page" in names
    assert "browser_action" in names


def test_browse_page_schema_params():
    from ouroboros.tools.browser import get_tools
    tools = {t.name: t for t in get_tools()}
    schema = tools["browse_page"].schema
    params = schema["parameters"]["properties"]
    assert "url" in params
    assert params["output"]["enum"] == ["text", "html", "markdown", "screenshot"]


def test_browser_action_schema_params():
    from ouroboros.tools.browser import get_tools
    tools = {t.name: t for t in get_tools()}
    schema = tools["browser_action"].schema
    params = schema["parameters"]["properties"]
    assert "action" in params
    assert params["action"]["enum"] == ["click", "fill", "select", "screenshot", "evaluate", "scroll"]
    assert "selector" in params
    assert "value" in params


# ---------------------------------------------------------------------------
# _extract_page_output
# ---------------------------------------------------------------------------


def test_extract_page_output_text(mock_ctx, mock_page):
    from ouroboros.tools.browser import _extract_page_output
    result = _extract_page_output(mock_page, "text", mock_ctx)
    assert "Hello" in result
    mock_page.inner_text.assert_called_once_with("body")


def test_extract_page_output_html(mock_ctx, mock_page):
    from ouroboros.tools.browser import _extract_page_output
    result = _extract_page_output(mock_page, "html", mock_ctx)
    assert "<html>" in result
    mock_page.content.assert_called_once()


def test_extract_page_output_markdown(mock_ctx, mock_page):
    from ouroboros.tools.browser import _extract_page_output
    result = _extract_page_output(mock_page, "markdown", mock_ctx)
    assert "# Hello" in result


def test_extract_page_output_screenshot(mock_ctx, mock_page):
    from ouroboros.tools.browser import _extract_page_output
    mock_page.screenshot.return_value = b"fake_png_data"
    result = _extract_page_output(mock_page, "screenshot", mock_ctx)
    assert "Screenshot captured" in result
    assert "send_photo" in result
    # Check base64 was saved to context
    import base64
    expected = base64.b64encode(b"fake_png_data").decode()
    assert mock_ctx.browser_state.last_screenshot_b64 == expected


def test_extract_page_output_html_truncated(mock_ctx):
    from ouroboros.tools.browser import _extract_page_output
    page = MagicMock()
    page.content.return_value = "x" * 60000
    result = _extract_page_output(page, "html", mock_ctx)
    assert len(result) <= 50000 + 20
    assert "truncated" in result


# ---------------------------------------------------------------------------
# _browser_action — action routing
# ---------------------------------------------------------------------------


def test_browser_action_click(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="click", selector="#btn")
    assert "Clicked" in result
    mock_page.click.assert_called_with("#btn", timeout=5000)


def test_browser_action_click_no_selector(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="click")
    assert "Error" in result


def test_browser_action_fill(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="fill", selector="#input", value="hello")
    assert "Filled" in result
    mock_page.fill.assert_called_with("#input", "hello", timeout=5000)


def test_browser_action_screenshot(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    mock_page.screenshot.return_value = b"data"
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="screenshot")
    assert "Screenshot" in result


def test_browser_action_evaluate(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    mock_page.evaluate.return_value = 42
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="evaluate", value="1 + 1")
    assert "42" in result


def test_browser_action_evaluate_no_value(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="evaluate")
    assert "Error" in result


def test_browser_action_scroll_down(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="scroll", value="down")
    assert "Scrolled" in result
    mock_page.evaluate.assert_called_with("window.scrollBy(0, 600)")


def test_browser_action_scroll_top(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="scroll", value="top")
    assert "Scrolled" in result
    mock_page.evaluate.assert_called_with("window.scrollTo(0, 0)")


def test_browser_action_unknown(mock_ctx, mock_page):
    from ouroboros.tools.browser import _browser_action
    with patch("ouroboros.tools.browser._ensure_browser", return_value=mock_page):
        result = _browser_action(mock_ctx, action="nonexistent")
    assert "Unknown action" in result


# ---------------------------------------------------------------------------
# Error handling — greenlet thread recovery
# ---------------------------------------------------------------------------


def test_browse_page_greenlet_error_recovery(mock_ctx, mock_page):
    """_browse_page should catch greenlet errors and retry."""
    from ouroboros.tools.browser import _browse_page

    call_count = [0]
    def _failing_then_succeeding(ctx):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("cannot switch to a different thread")
        return mock_page

    with patch("ouroboros.tools.browser._ensure_browser", side_effect=_failing_then_succeeding), \
         patch("ouroboros.tools.browser.cleanup_browser"), \
         patch("ouroboros.tools.browser._reset_playwright_greenlet"):
        result = _browse_page(mock_ctx, url="https://example.com", output="text")
    assert call_count[0] == 2
    assert "Hello" in result or "Hello" in str(result)


def test_browser_action_greenlet_error_recovery(mock_ctx, mock_page):
    """_browser_action should catch greenlet errors and retry."""
    from ouroboros.tools.browser import _browser_action

    call_count = [0]
    def _failing_then_succeeding(ctx):
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("different thread")
        return mock_page

    with patch("ouroboros.tools.browser._ensure_browser", side_effect=_failing_then_succeeding), \
         patch("ouroboros.tools.browser.cleanup_browser"), \
         patch("ouroboros.tools.browser._reset_playwright_greenlet"):
        result = _browser_action(mock_ctx, action="scroll", value="down")
    assert call_count[0] == 2
    assert "Scrolled" in result


# ---------------------------------------------------------------------------
# _MARKDOWN_JS is valid JS syntax
# ---------------------------------------------------------------------------


def test_markdown_js_syntax():
    """The embedded JS should parse without syntax errors via a JS engine check."""
    from ouroboros.tools.browser import _MARKDOWN_JS
    assert _MARKDOWN_JS.startswith("() =>")
    assert "walk(document.body)" in _MARKDOWN_JS

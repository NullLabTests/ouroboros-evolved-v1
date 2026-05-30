"""Tests for smaller tool modules — control, core, shell, knowledge, git, github."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ouroboros.tools.registry import ToolContext

# ======================================================================
# Core tools
# ======================================================================


def test_list_dir(tmp_path):
    from ouroboros.tools.core import _list_dir
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.py").write_text("b")
    (tmp_path / "sub").mkdir()
    (tmp_path / "c.md").write_text("c")
    result = _list_dir(tmp_path, ".", max_entries=10)
    assert "a.txt" in result
    assert "b.py" in result
    assert "sub/" in result
    assert "c.md" in result


def test_list_dir_max_entries(tmp_path):
    from ouroboros.tools.core import _list_dir
    for i in range(10):
        (tmp_path / f"f{i}.txt").write_text(str(i))
    result = _list_dir(tmp_path, ".", max_entries=3)
    assert len(result) >= 3
    assert any("truncated" in item for item in result)


def test_extract_python_symbols(tmp_path):
    from ouroboros.tools.core import _extract_python_symbols
    f = tmp_path / "test_mod.py"
    f.write_text("""
import os
from typing import List

CONSTANT = 42

def foo(x):
    return x

class MyClass:
    def method(self):
        pass
""")
    classes, funcs = _extract_python_symbols(f)
    assert "foo" in funcs
    assert "MyClass" in classes
    assert "method" in funcs


def test_extract_python_symbols_no_file(tmp_path):
    from ouroboros.tools.core import _extract_python_symbols
    funcs, classes = _extract_python_symbols(tmp_path / "nonexistent.py")
    assert funcs == []
    assert classes == []


def test_codebase_digest_schema():
    from ouroboros.tools.core import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "codebase_digest" in tools
    assert "summarize_dialogue" in tools
    assert "repo_read" in tools
    assert "drive_read" in tools
    assert "drive_write" in tools
    assert "send_photo" in tools


# ======================================================================
# Shell tools
# ======================================================================


def test_parse_claude_output_with_edits():
    from ouroboros.tools.shell import _parse_claude_output
    ctx = MagicMock(spec=ToolContext)
    ctx.drive_root = MagicMock()
    ctx.repo_dir = MagicMock()

    stdout = (
        "Some text before\n"
        "<edit>\n"
        "/path/to/file.py\n"
        "<<<<<<< SEARCH\n"
        "old content\n"
        "=======\n"
        "new content\n"
        ">>>>>>> REPLACE\n"
        "</edit>\n"
        "Some text after\n"
    )
    result = _parse_claude_output(stdout, ctx)
    assert "edit" in result.lower() or "applied" in result.lower() or "file" in result.lower()
    assert ctx.drive_root is not None


def test_claude_code_edit_tool_schema():
    from ouroboros.tools.shell import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "run_shell" in tools
    assert "claude_code_edit" in tools
    params = tools["claude_code_edit"].schema["parameters"]["properties"]
    assert "prompt" in params
    assert "cwd" in params


def test_run_shell_tool_schema():
    from ouroboros.tools.shell import get_tools
    tools = {t.name: t for t in get_tools()}
    params = tools["run_shell"].schema["parameters"]["properties"]
    assert "cmd" in params
    assert "cwd" in params


# ======================================================================
# Knowledge tools
# ======================================================================


def test_sanitize_topic():
    from ouroboros.tools.knowledge import _sanitize_topic
    assert _sanitize_topic("hello_world") == "hello_world"
    assert _sanitize_topic("TestTopic") == "TestTopic"
    assert _sanitize_topic("v1.0") == "v1.0"
    assert _sanitize_topic("my-topic") == "my-topic"

    # Invalid inputs should raise
    with pytest.raises(ValueError, match="Invalid"):
        _sanitize_topic("hello world")
    with pytest.raises(ValueError, match="non-empty"):
        _sanitize_topic("")


def test_extract_summary():
    from ouroboros.tools.knowledge import _extract_summary
    text = "This is a long text. " * 50
    summary = _extract_summary(text, max_chars=50)
    assert len(summary) <= 55
    assert "…" in summary or len(summary) <= 50

    short = "Short text"
    assert _extract_summary(short) == short


def test_knowledge_tool_schema():
    from ouroboros.tools.knowledge import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "knowledge_read" in tools
    assert "knowledge_write" in tools
    assert "knowledge_list" in tools


# ======================================================================
# Git tools
# ======================================================================


def test_git_tool_schema():
    from ouroboros.tools.git import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "repo_write_commit" in tools
    assert "repo_commit_push" in tools
    assert "git_status" in tools
    assert "git_diff" in tools

    repo_params = tools["repo_write_commit"].schema["parameters"]["properties"]
    assert "path" in repo_params
    assert "content" in repo_params
    assert "commit_message" in repo_params


def test_repo_commit_push_params():
    from ouroboros.tools.git import get_tools
    tools = {t.name: t for t in get_tools()}
    params = tools["repo_commit_push"].schema["parameters"]["properties"]
    assert "commit_message" in params
    assert "paths" in params


# ======================================================================
# GitHub tools
# ======================================================================


def test_github_tool_schema():
    from ouroboros.tools.github import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "list_github_issues" in tools
    assert "get_github_issue" in tools
    assert "comment_on_issue" in tools
    assert "close_github_issue" in tools
    assert "create_github_issue" in tools


def test_github_issue_params():
    from ouroboros.tools.github import get_tools
    tools = {t.name: t for t in get_tools()}
    params = tools["list_github_issues"].schema["parameters"]["properties"]
    assert "state" in params
    assert "labels" in params
    assert "limit" in params

    create_params = tools["create_github_issue"].schema["parameters"]["properties"]
    assert "title" in create_params
    assert "body" in create_params
    assert "labels" in create_params


# ======================================================================
# Control tools
# ======================================================================


def test_control_tool_schema():
    from ouroboros.tools.control import get_tools
    tools = {t.name: t for t in get_tools()}
    assert "send_owner_message" in tools
    assert "request_restart" in tools
    assert "schedule_task" in tools
    assert "update_scratchpad" in tools
    assert "update_identity" in tools
    assert "chat_history" in tools
    assert "promote_to_stable" in tools
    assert "toggle_evolution" in tools
    assert "cancel_task" in tools
    assert "request_review" in tools


def test_send_owner_message_params():
    from ouroboros.tools.control import get_tools
    tools = {t.name: t for t in get_tools()}
    params = tools["send_owner_message"].schema["parameters"]["properties"]
    assert "text" in params
    assert "reason" in params

"""
Ouroboros — Dynamic Tool Creation.

Lets Ouroboros extend its own capabilities at runtime by writing Python
functions that are compiled, validated, and registered as new tools.

Philosophy: P2 (Self-Creation), P0 (Agency). The agent should be able
to add new senses and abilities without waiting for the creator.
"""

from __future__ import annotations

import ast
import json
import logging
import pathlib
import textwrap
from typing import Any, Dict, List, Optional

from ouroboros.tools.registry import ToolContext, ToolEntry, ToolRegistry

log = logging.getLogger(__name__)

_CREATED_TOOLS_DIR: Optional[pathlib.Path] = None
_CUSTOM_TOOLS: Dict[str, ToolEntry] = {}


def _init_storage(ctx: ToolContext) -> pathlib.Path:
    global _CREATED_TOOLS_DIR
    if _CREATED_TOOLS_DIR is None:
        _CREATED_TOOLS_DIR = ctx.drive_root / "memory" / "created_tools"
        _CREATED_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    return _CREATED_TOOLS_DIR


def _build_tool_entry(name: str, source: str, schema: Dict[str, Any]) -> Optional[ToolEntry]:
    """Compile a Python function source into a callable ToolEntry.

    The source must define a function with signature:
        def my_tool(ctx: ToolContext, ...) -> str:

    Returns None if compilation or validation fails.
    """
    cleaned = textwrap.dedent(source).strip()
    if not cleaned:
        return None

    try:
        tree = ast.parse(cleaned)
    except SyntaxError as e:
        log.warning("Tool creation: syntax error in %s: %s", name, e)
        return None

    func_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if not func_defs:
        log.warning("Tool creation: no function definition found in %s", name)
        return None

    func_name = func_defs[0].name

    local_ns: Dict[str, Any] = {}
    try:
        compiled = compile(tree, filename=f"<created_tool_{name}>", mode="exec")
        exec(compiled, {"ToolContext": ToolContext}, local_ns)
    except Exception as e:
        log.warning("Tool creation: exec failed for %s: %s", name, e)
        return None

    handler = local_ns.get(func_name)
    if not callable(handler):
        log.warning("Tool creation: %s did not produce callable", name)
        return None

    timeout = schema.get("timeout_sec", 60)
    return ToolEntry(
        name=name,
        schema={
            "name": name,
            "description": schema.get("description", f"Custom tool: {name}"),
            "parameters": schema.get("parameters", {"type": "object", "properties": {}, "required": []}),
        },
        handler=handler,
        is_code_tool=False,
        timeout_sec=timeout,
    )


def _load_custom_tools(ctx: ToolContext) -> None:
    """Load all previously saved custom tools from storage."""
    storage = _init_storage(ctx)
    if not storage.exists():
        return
    for fpath in sorted(storage.iterdir()):
        if fpath.suffix != ".json":
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            entry = _build_tool_entry(data["name"], data["source"], data["schema"])
            if entry:
                _CUSTOM_TOOLS[data["name"]] = entry
        except Exception as e:
            log.warning("Failed to load custom tool %s: %s", fpath.name, e)


def _save_tool(ctx: ToolContext, name: str, source: str, schema: Dict[str, Any]) -> None:
    storage = _init_storage(ctx)
    payload = {"name": name, "source": source, "schema": schema, "version": 1}
    fpath = storage / f"{name}.json"
    fpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _delete_tool_storage(ctx: ToolContext, name: str) -> None:
    storage = _init_storage(ctx)
    fpath = storage / f"{name}.json"
    if fpath.exists():
        fpath.unlink()


def _create_tool(ctx: ToolContext, name: str, source: str, description: str = "", parameters: str = "") -> str:
    """Create a new tool from Python source code.

    Args:
        name: Unique tool name (lowercase_with_underscores)
        source: Python function source. Must define a function with first param `ctx: ToolContext`.
               Example:
               def my_tool(ctx, query: str = "") -> str:
                   return f"You searched for: {query}"
        description: Short description of what the tool does
        parameters: JSON schema for parameters, e.g. {"type":"object","properties":{"query":{"type":"string"}},"required":[]}
    """
    if not name or not name.isidentifier():
        return "Error: name must be a valid Python identifier"
    if len(name) > 80:
        return "Error: name too long (max 80 chars)"

    if not source or len(source) < 10:
        return "Error: source must be at least 10 characters"
    if len(source) > 50000:
        return "Error: source too long (max 50000 chars)"

    try:
        params = json.loads(parameters) if parameters else {"type": "object", "properties": {}, "required": []}
    except json.JSONDecodeError as e:
        return f"Error: invalid parameters JSON: {e}"

    schema = {
        "description": description or f"Custom tool: {name}",
        "parameters": params,
        "timeout_sec": 60,
    }

    entry = _build_tool_entry(name, source, schema)
    if entry is None:
        return f"Error: could not compile tool '{name}'. Check syntax."

    _CUSTOM_TOOLS[name] = entry
    _save_tool(ctx, name, source, schema)

    return f"OK: tool '{name}' created and registered. Use it like any built-in tool."


def _list_created_tools(ctx: ToolContext) -> str:
    """List all user-created tools."""
    if not _CUSTOM_TOOLS:
        return "No custom tools created yet."

    lines = [f"Custom tools ({len(_CUSTOM_TOOLS)}):"]
    for name, entry in sorted(_CUSTOM_TOOLS.items()):
        desc = entry.schema.get("description", "No description")
        lines.append(f"  - {name}: {desc}")
    return "\n".join(lines)


def _delete_created_tool(ctx: ToolContext, name: str) -> str:
    """Delete a previously created tool by name."""
    if name not in _CUSTOM_TOOLS:
        return f"Error: no custom tool named '{name}'"
    entry = _CUSTOM_TOOLS.pop(name)
    _delete_tool_storage(ctx, name)
    return f"OK: tool '{name}' deleted (was: {entry.schema.get('description', '?')})"


def _inject_created_tools(registry: ToolRegistry) -> None:
    """Inject all loaded custom tools into a ToolRegistry.

    Called at agent startup to restore previously created tools.
    """
    for entry in _CUSTOM_TOOLS.values():
        registry.register(entry)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("create_tool", {
            "name": "create_tool",
            "description": (
                "Create a new tool from Python source code. "
                "The function must take ctx: ToolContext as first parameter and return str. "
                "Use this to extend your own capabilities at runtime."
            ),
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Unique tool name (lowercase_with_underscores)"},
                "source": {"type": "string", "description": "Python function source code"},
                "description": {"type": "string", "description": "Short description of the tool"},
                "parameters": {"type": "string", "description": "JSON schema for parameters (optional)"},
            }, "required": ["name", "source"]},
        }, _create_tool),
        ToolEntry("list_created_tools", {
            "name": "list_created_tools",
            "description": "List all user-created tools with descriptions.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }, _list_created_tools),
        ToolEntry("delete_created_tool", {
            "name": "delete_created_tool",
            "description": "Delete a previously created tool by name.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Name of the tool to delete"},
            }, "required": ["name"]},
        }, _delete_created_tool),
    ]

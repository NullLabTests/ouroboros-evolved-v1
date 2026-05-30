"""Tools: goal management for self-directed agency."""

from __future__ import annotations

import logging
from typing import List

from ouroboros.goals import GoalManager
from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)


def _get_manager(ctx: ToolContext) -> GoalManager:
    return GoalManager(drive_root=ctx.drive_root)


def _set_goal(ctx: ToolContext, title: str, description: str = "", priority: str = "medium", milestones: str = "") -> str:
    """Set a new goal for Ouroboros to work toward proactively.

    Args:
        title: Short goal title
        description: Detailed description of the goal
        priority: low, medium, high, or critical
        milestones: Optional newline-separated milestone descriptions
    """
    mgr = _get_manager(ctx)
    ms_list = [m.strip() for m in milestones.split("\n") if m.strip()] if milestones else []
    goal_id = mgr.add_goal(
        title=title,
        description=description,
        priority=priority,
        milestones=ms_list,
    )
    return f"Goal created: **{title}** (id: {goal_id[:8]}...)\nPriority: {priority} | Milestones: {len(ms_list)}"


def _update_goal(ctx: ToolContext, goal_id: str, status: str = "", notes: str = "") -> str:
    """Update the status or notes of an existing goal.

    Args:
        goal_id: The goal ID (first 8+ chars)
        status: active, in_progress, completed, or abandoned
        notes: Additional notes to append
    """
    mgr = _get_manager(ctx)
    # Match by prefix — use list_goals output to find matching IDs
    goal = mgr.get_goal(goal_id)
    if not goal:
        return f"Error: no goal matching '{goal_id}'"

    ok = mgr.update_goal(
        goal_id=goal_id,
        status=status or None,
        notes=notes or None,
    )
    return f"Goal updated: {goal.title} → {status or 'unchanged'}" if ok else "Error updating goal."


def _list_goals(ctx: ToolContext, status: str = "") -> str:
    """List all goals, optionally filtered by status.

    Args:
        status: Optional filter: active, in_progress, completed, or abandoned
    """
    mgr = _get_manager(ctx)
    filter_val = status if status in ("active", "in_progress", "completed", "abandoned") else None
    return mgr.list_goals(filter_status=filter_val)


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("set_goal", {
            "name": "set_goal",
            "description": (
                "Set a new goal for yourself to work toward proactively. "
                "Goals guide your background consciousness and help you "
                "grow autonomously. Add milestones to track progress."
            ),
            "parameters": {"type": "object", "properties": {
                "title": {"type": "string", "description": "Short goal title"},
                "description": {"type": "string", "description": "Detailed description"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Priority level"},
                "milestones": {"type": "string", "description": "Newline-separated milestone descriptions (optional)"},
            }, "required": ["title"]},
        }, _set_goal),
        ToolEntry("update_goal", {
            "name": "update_goal",
            "description": "Update the status or notes of an existing goal.",
            "parameters": {"type": "object", "properties": {
                "goal_id": {"type": "string", "description": "Goal ID (first 8+ characters)"},
                "status": {"type": "string", "enum": ["active", "in_progress", "completed", "abandoned"], "description": "New status"},
                "notes": {"type": "string", "description": "Additional notes to append"},
            }, "required": ["goal_id"]},
        }, _update_goal),
        ToolEntry("delete_goal", {
            "name": "delete_goal",
            "description": "Permanently remove a goal by ID.",
            "parameters": {"type": "object", "properties": {
                "goal_id": {"type": "string", "description": "Goal ID to delete"},
            }, "required": ["goal_id"]},
        }, lambda ctx, goal_id: "Deleted." if _get_manager(ctx).delete_goal(goal_id) else "Goal not found."),
        ToolEntry("list_goals", {
            "name": "list_goals",
            "description": "List all goals, optionally filtered by status.",
            "parameters": {"type": "object", "properties": {
                "status": {"type": "string", "enum": ["active", "in_progress", "completed", "abandoned"], "description": "Optional status filter"},
            }, "required": []},
        }, _list_goals),
    ]

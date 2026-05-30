"""Tool: group_evolution_experiment — run a group evolution session."""

from __future__ import annotations

import json
import logging
from typing import Any, List

from ouroboros.tools.registry import ToolContext, ToolEntry
from ouroboros.group_evolution import group_evolution_session, AGENT_ARCHETYPES

log = logging.getLogger(__name__)


def _run_group_evolution(ctx: ToolContext, topic: str, archetypes: str = "") -> str:
    """Run a group evolution session where multiple Ouroboros variants
    share experiences and propose improvements on a topic.

    Args:
        topic: The evolution topic, problem, or question to explore
        archetypes: Comma-separated archetypes (minimalist,architect,explorer,philosopher,guardian).
                   Default: all five
    """
    available = list(AGENT_ARCHETYPES.keys())
    archetype_list: list[str] = []
    if archetypes:
        for a in archetypes.split(","):
            a = a.strip().lower()
            if a in available:
                archetype_list.append(a)
    if not archetype_list:
        archetype_list = available

    report, cost = group_evolution_session(
        topic=topic,
        archetypes=archetype_list,
    )

    return (
        f"{report}\n\n"
        f"**Session cost:** ${cost:.4f}\n"
        f"*Use this synthesis to guide your next evolution step.*"
    )


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("group_evolution_experiment", {
            "name": "group_evolution_experiment",
            "description": (
                "Run a group evolution session where multiple Ouroboros "
                "variant-archetypes (Minimalist, Architect, Explorer, Philosopher, "
                "Guardian) share experiences and propose improvements on a topic. "
                "Use for strategic planning, architecture decisions, or when you "
                "need diverse perspectives on evolution."
            ),
            "parameters": {"type": "object", "properties": {
                "topic": {"type": "string", "description": "The evolution topic, problem, or question"},
                "archetypes": {"type": "string", "description": "Comma-separated archetypes (default: all)"},
            }, "required": ["topic"]},
        }, _run_group_evolution),
    ]

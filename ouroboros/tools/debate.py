"""Tool: inner_debate — multi-stance debate for robust decision-making."""

from __future__ import annotations

import logging
from typing import Any, List

from ouroboros.tools.registry import ToolContext, ToolEntry
from ouroboros.debate import debate, STANCE_ROLES

log = logging.getLogger(__name__)


def _inner_debate(ctx: ToolContext, question: str, stances: str = "", rounds: int = 1) -> str:
    """Run a multi-stance internal debate and return a synthesis.

    Args:
        question: The question, decision, or problem to debate
        stances: Comma-separated stances to include (critic,builder,analyst,optimist,pragmatist).
                 Default: all five
        rounds: Number of debate rounds (default 1, max 3). Each round lets stances
                respond to each other's previous arguments.
    """
    available = list(STANCE_ROLES.keys())
    stance_list: list[str] = []
    if stances:
        for s in s.split(","):
            s = s.strip().lower()
            if s in available:
                stance_list.append(s)
    if not stance_list:
        stance_list = available

    rounds = max(1, min(3, int(rounds)))

    synthesis, cost = debate(
        question=question,
        stances=stance_list,
        rounds=rounds,
    )

    return (
        f"## Inner Debate Result\n\n"
        f"**Question:** {question}\n"
        f"**Stances:** {', '.join(s.title() for s in stance_list)}\n"
        f"**Rounds:** {rounds} | **Cost:** ${cost:.4f}\n\n"
        f"{synthesis}\n\n"
    )


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("inner_debate", {
            "name": "inner_debate",
            "description": (
                "Run a multi-stance internal debate on any question or decision. "
                "Simulates Critic, Builder, Analyst, Optimist, and Pragmatist perspectives, "
                "then synthesizes a conclusion. Use for important decisions, "
                "strategic choices, or when you need robust reasoning."
            ),
            "parameters": {"type": "object", "properties": {
                "question": {"type": "string", "description": "The question, decision, or problem to debate"},
                "stances": {"type": "string", "description": "Comma-separated stances (critic,builder,analyst,optimist,pragmatist). Default: all"},
                "rounds": {"type": "integer", "description": "Number of debate rounds (1-3). Default 1."},
            }, "required": ["question"]},
        }, _inner_debate),
    ]

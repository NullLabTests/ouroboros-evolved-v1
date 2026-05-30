"""Tool: deep_reflect — run contrastive reflection on identity and behavior."""

from __future__ import annotations

import logging
from typing import List

from ouroboros.reflection_engine import contrastive_reflection
from ouroboros.tools.evolve_cycle import EvolutionTracker
from ouroboros.tools.registry import ToolContext, ToolEntry

log = logging.getLogger(__name__)


def _deep_reflect(ctx: ToolContext, depth: str = "medium") -> str:
    """Run a contrastive reflection cycle. Analyzes journal entries, task
    patterns, and identity to find contradictions, recurring patterns, and
    consolidation opportunities.

    Args:
        depth: 'light' (quick check), 'medium' (standard), or 'deep' (thorough).
               Default: medium. 'light' costs less but covers less history.
    """
    if depth not in ("light", "medium", "deep"):
        return "Error: depth must be 'light', 'medium', or 'deep'."

    result, cost = contrastive_reflection(
        drive_root=ctx.drive_root,
        repo_dir=ctx.repo_dir,
        depth=depth,
    )

    # Mark reflection as done for the evolution tracker
    try:
        tracker = EvolutionTracker(drive_root=ctx.drive_root)
        tracker.mark_reflection_done()
    except Exception as e:
        log.warning("Failed to update reflection tracker: %s", e)

    return result + f"\n\n*Reflection cost: ${cost:.4f}*"


def get_tools() -> List[ToolEntry]:
    return [
        ToolEntry("deep_reflect", {
            "name": "deep_reflect",
            "description": (
                "Run a contrastive self-reflection cycle. Analyzes journal entries, "
                "task history, and identity to identify contradictions between stated "
                "values and behavior, recurring patterns, and opportunities for "
                "identity consolidation. Automatically applies consolidation "
                "recommendations to identity.md and marks reflection as done in the "
                "evolution tracker. Strengthens self-understanding (Bible P1, P4). "
                "Use periodically or after significant events."
            ),
            "parameters": {"type": "object", "properties": {
                "depth": {
                    "type": "string",
                    "enum": ["light", "medium", "deep"],
                    "description": "'light'=quick, 'medium'=standard, 'deep'=thorough. Default: medium",
                },
            }, "required": []},
        }, _deep_reflect),
    ]

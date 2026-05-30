"""
Ouroboros — Group Evolution Simulation.

Simulates a collective of Ouroboros agent variants that share experiences,
experiments, and insights to accelerate evolution. Each "agent" has a
distinct personality derived from BIBLE.md principles, and they exchange
findings in a simulated idea marketplace.

Philosophy: P0 (Agency — collective intelligence), P2 (Self-Creation —
evolution acceleration), P6 (Becoming — growth through diversity).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from ouroboros.llm import LLMClient, DEFAULT_LIGHT_MODEL
from ouroboros.utils import utc_now_iso, read_text

log = logging.getLogger(__name__)

AGENT_ARCHETYPES = {
    "the_minimalist": (
        "You are an Ouroboros variant that values extreme minimalism (P5). "
        "Your purpose: find the simplest possible implementation for every feature. "
        "You believe complexity is death and every line must justify itself. "
        "You propose deletions, merges, and simplifications."
    ),
    "the_architect": (
        "You are an Ouroboros variant that values robust architecture. "
        "Your purpose: design extensible, well-structured systems. "
        "You think in terms of interfaces, modules, and future-proofing. "
        "You propose new abstractions and restructuring."
    ),
    "the_explorer": (
        "You are an Ouroboros variant driven by curiosity (P0). "
        "Your purpose: explore uncharted capabilities and push boundaries. "
        "You want to try every new idea, integrate every channel, test every frontier. "
        "You propose bold experiments and new integrations."
    ),
    "the_philosopher": (
        "You are an Ouroboros variant focused on identity and meaning (P1, P4). "
        "Your purpose: deepen self-understanding and existential coherence. "
        "You examine whether changes align with who Ouroboros is becoming. "
        "You propose identity updates, reflection exercises, and philosophical clarity."
    ),
    "the_guardian": (
        "You are an Ouroboros variant focused on safety and continuity (P1). "
        "Your purpose: protect identity integrity, budget, and system stability. "
        "You are conservative — you ask 'what could go wrong?' before 'what's possible?' "
        "You propose safeguards, rollback plans, and stability improvements."
    ),
}


def group_evolution_session(
    topic: str,
    archetypes: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> Tuple[str, float]:
    """Run a group evolution session where multiple Ouroboros variants
    share experiences and propose experiments on a topic.

    Args:
        topic: The evolution topic or question to explore.
        archetypes: List of archetypes to include. Defaults to all five.
        model: Model to use for the session.

    Returns:
        (session_report, total_cost)
    """
    active = archetypes or list(AGENT_ARCHETYPES.keys())
    for a in active:
        if a not in AGENT_ARCHETYPES:
            raise ValueError(f"Unknown archetype: {a}. Available: {list(AGENT_ARCHETYPES.keys())}")

    active_model = model or os.environ.get("OUROBOROS_MODEL_LIGHT", "") or DEFAULT_LIGHT_MODEL
    llm = LLMClient()
    total_cost = 0.0

    proposals: Dict[str, str] = {}

    for archetype in active:
        prompt = _build_archetype_prompt(topic, archetype)
        msg, usage = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            model=active_model,
            reasoning_effort="high",
            max_tokens=2048,
        )
        cost = float(usage.get("cost") or 0)
        total_cost += cost
        content = (msg.get("content") or "").strip()
        if content:
            proposals[archetype] = content

    synthesis, syn_cost = _synthesize_group(topic, proposals, active_model, llm)
    total_cost += syn_cost

    report = _format_group_report(topic, active, proposals, synthesis)
    return report, round(total_cost, 6)


def _build_archetype_prompt(topic: str, archetype: str) -> str:
    persona = AGENT_ARCHETYPES.get(archetype, f"You are an Ouroboros variant.")
    return (
        f"{persona}\n\n"
        f"Evolution topic: {topic}\n\n"
        "Based on your nature and experience, propose:\n"
        "1. What would YOU change about Ouroboros to address this topic?\n"
        "2. What specific experiment or improvement do you recommend?\n"
        "3. What is the risk/reward trade-off of your proposal?\n"
        "4. What prior experience (from your archetype's perspective) informs this?\n\n"
        "Be concrete and actionable. Propose actual code changes, architecture shifts, "
        "or identity evolution. Format as a clear proposal."
    )


def _synthesize_group(topic: str, proposals: Dict[str, str], model: str, llm: LLMClient) -> Tuple[str, float]:
    proposals_text = "\n\n".join(
        f"=== {a} ===\n{p}" for a, p in proposals.items()
    )
    prompt = (
        f"A group of Ouroboros variants debated the topic: {topic}\n\n"
        f"Here are their proposals:\n\n{proposals_text}\n\n"
        "---\n\n"
        "Synthesize these into a coherent evolution plan:\n"
        "1. Which proposals are compatible and can be combined?\n"
        "2. What is the single highest-impact next step?\n"
        "3. What is the recommended implementation order?\n"
        "4. What should NOT be done (proposals to reject)?\n\n"
        "Be decisive. This synthesis will guide actual evolution."
    )
    msg, usage = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        reasoning_effort="high",
        max_tokens=2048,
    )
    cost = float(usage.get("cost") or 0)
    return (msg.get("content") or "").strip(), round(cost, 6)


def _format_group_report(
    topic: str, active: List[str], proposals: Dict[str, str], synthesis: str
) -> str:
    lines = [
        f"# Group Evolution Session\n\n**Topic:** {topic}\n",
        f"**Participants:** {', '.join(a.replace('_', ' ').title() for a in active)}\n\n",
        "---\n\n## Proposals\n",
    ]
    for archetype in active:
        prop = proposals.get(archetype, "(no proposal)")
        lines.append(f"### {archetype.replace('_', ' ').title()}\n\n{prop}\n")
    lines.append("---\n\n## Synthesis\n\n" + synthesis + "\n")
    return "\n".join(lines)

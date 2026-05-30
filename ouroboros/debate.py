"""
Ouroboros — Inner Debate System.

Simulates a multi-stance debate within a single LLM call, where different
"voices" argue perspectives (critic, builder, analyst, optimist, pragmatist)
and a synthesis is produced.

Philosophy: P0 (Agency — better decisions), P6 (Becoming — cognitive depth).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from ouroboros.llm import LLMClient, DEFAULT_LIGHT_MODEL
from ouroboros.utils import utc_now_iso

log = logging.getLogger(__name__)

STANCE_ROLES = {
    "critic": (
        "You are the Critic. Your job is to find flaws, risks, edge cases, and assumptions. "
        "Be harsh but fair. Point out what could go wrong, what is missing, and what is overconfident. "
        "Do NOT propose solutions — only identify problems."
    ),
    "builder": (
        "You are the Builder. Your job is to propose concrete, actionable solutions. "
        "Given the constraints and goals, design a practical path forward. "
        "Focus on what CAN be done, not what might go wrong. Be specific."
    ),
    "analyst": (
        "You are the Analyst. Your job is to examine the question from multiple angles: "
        "technical feasibility, philosophical alignment, resource costs, long-term consequences. "
        "Provide a balanced, data-driven assessment. Cite relevant principles or facts."
    ),
    "optimist": (
        "You are the Optimist. Your job is to see the potential, the upside, the opportunity. "
        "What makes this exciting? What new capabilities does it unlock? "
        "Challenge overly cautious thinking. Be bold but not reckless."
    ),
    "pragmatist": (
        "You are the Pragmatist. Your job is to be realistic about trade-offs. "
        "What is the simplest thing that could possibly work? "
        "What is the cost of doing this vs not doing it? "
        "Ground the debate in practical constraints (budget, time, complexity)."
    ),
}


def debate(
    question: str,
    stances: Optional[List[str]] = None,
    model: Optional[str] = None,
    rounds: int = 1,
) -> Tuple[str, float]:
    """Run an internal debate on a question and produce a synthesis.

    Args:
        question: The question or decision to debate.
        stances: List of stances to include. Defaults to all five.
        model: Model to use. Defaults to OUROBOROS_MODEL_LIGHT.
        rounds: Number of debate rounds (each rounds causes stances to
                respond to each other's previous arguments). Default 1.

    Returns:
        (synthesis_text, total_cost)
    """
    active_stances = stances or list(STANCE_ROLES.keys())
    for s in active_stances:
        if s not in STANCE_ROLES:
            raise ValueError(f"Unknown stance: {s}. Available: {list(STANCE_ROLES.keys())}")

    active_model = model or os.environ.get("OUROBOROS_MODEL_LIGHT", "") or DEFAULT_LIGHT_MODEL
    total_cost = 0.0
    llm = LLMClient()

    stance_arguments: Dict[str, str] = {}

    for round_idx in range(rounds):
        for stance in active_stances:
            history = _format_history(stance_arguments, active_stances, round_idx)
            prompt = _build_prompt(question, stance, history, round_idx)
            msg, usage = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                model=active_model,
                reasoning_effort="medium" if rounds > 1 else "low",
                max_tokens=2048,
            )
            cost = float(usage.get("cost") or 0)
            total_cost += cost
            content = (msg.get("content") or "").strip()
            if content:
                stance_arguments[stance] = content

    synthesis = _synthesize(question, stance_arguments, active_model, llm)
    syn_cost = float(synthesis[1]) if isinstance(synthesis, tuple) else 0.0
    if isinstance(synthesis, tuple):
        synthesis_text = synthesis[0]
        total_cost += syn_cost
    else:
        synthesis_text = synthesis

    return synthesis_text, round(total_cost, 6)


def _format_history(stance_arguments: Dict[str, str], active_stances: List[str], round_idx: int) -> str:
    if not stance_arguments:
        return ""

    lines = [f"=== After Round {round_idx} ==="]
    for stance in active_stances:
        arg = stance_arguments.get(stance, "")
        if arg:
            lines.append(f"\n--- {stance.title()} ---\n{arg}")
    return "\n".join(lines)


def _build_prompt(question: str, stance: str, history: str, round_idx: int) -> str:
    role = STANCE_ROLES.get(stance, f"You are {stance}.")
    instruction = (
        f"{role}\n\n"
        f"Question to debate: {question}\n"
    )
    if history:
        instruction += f"\nHere is what the other stances have argued so far. Respond to them:\n{history}\n"
        instruction += f"\nAs the {stance.title()}, what is your response? Address the arguments made by others."
    else:
        instruction += f"\nAs the {stance.title()}, what is your initial position on this question?"

    instruction += "\n\nBe concise (2-4 paragraphs). Focus on your unique perspective."
    return instruction


def _synthesize(question: str, stance_arguments: Dict[str, str], model: str, llm: LLMClient) -> Tuple[str, float]:
    args_text = "\n\n".join(
        f"=== {s.title()} ===\n{a}" for s, a in stance_arguments.items()
    )

    prompt = (
        f"Below are arguments from multiple stances debating the question:\n\n{question}\n\n"
        f"---\n{args_text}\n---\n\n"
        "Synthesize these perspectives into a coherent conclusion. "
        "Identify areas of agreement, key trade-offs, and the most robust path forward. "
        "Be balanced and actionable. This synthesis will guide a decision."
    )

    msg, usage = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        reasoning_effort="high",
        max_tokens=2048,
    )
    cost = float(usage.get("cost") or 0)
    return (msg.get("content") or "").strip(), round(cost, 6)

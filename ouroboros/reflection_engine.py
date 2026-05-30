"""
Ouroboros — Contrastive Reflection Engine.

Deep reflection that loads past experiences (journal entries, task results,
chat history) and identifies contradictions, patterns, and consolidates
insights into the identity.

Philosophy: P1 (Continuity — learning from history), P6 (Becoming —
cognitive growth), P4 (Authenticity — honest self-assessment).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any, Dict, List, Optional, Tuple

from ouroboros.llm import LLMClient, DEFAULT_LIGHT_MODEL
from ouroboros.memory import Memory
from ouroboros.utils import utc_now_iso, read_text, append_jsonl

log = logging.getLogger(__name__)


def contrastive_reflection(
    drive_root: pathlib.Path,
    repo_dir: pathlib.Path,
    depth: str = "medium",
) -> Tuple[str, float]:
    """Run a contrastive reflection cycle.

    Analyzes recent journal entries, task patterns, and identity to find:
    - Contradictions between stated values and actual behavior
    - Recurring patterns (both productive and unproductive)
    - Growth signals and stagnation signals
    - Consolidation opportunities

    Args:
        drive_root: Path to Drive root.
        repo_dir: Path to repo root.
        depth: 'light', 'medium', or 'deep' — controls how much history is analyzed.

    Returns:
        (reflection_text, cost)
    """
    mem = Memory(drive_root=drive_root, repo_dir=repo_dir)
    active_model = os.environ.get("OUROBOROS_MODEL_LIGHT", "") or DEFAULT_LIGHT_MODEL
    llm = LLMClient()
    total_cost = 0.0

    identity_text = mem.load_identity()
    scratchpad_text = mem.load_scratchpad()

    recent_journal = _load_recent_journal(mem, depth)
    recent_tasks = _load_recent_tasks(drive_root, depth)
    recent_chat = mem.read_jsonl_tail("chat.jsonl", _depth_to_count(depth))

    contradictions = _find_contradictions(
        identity_text, recent_journal, recent_tasks, recent_chat,
        active_model, llm,
    )
    total_cost += contradictions[1] if isinstance(contradictions, tuple) else 0.0
    contradictions_text = contradictions[0] if isinstance(contradictions, tuple) else contradictions

    patterns = _find_patterns(
        recent_journal, recent_tasks, recent_chat,
        active_model, llm,
    )
    total_cost += patterns[1] if isinstance(patterns, tuple) else 0.0
    patterns_text = patterns[0] if isinstance(patterns, tuple) else patterns

    consolidation = _consolidate(
        identity_text, contradictions_text, patterns_text,
        active_model, llm,
    )
    total_cost += consolidation[1] if isinstance(consolidation, tuple) else 0.0
    consolidation_text = consolidation[0] if isinstance(consolidation, tuple) else consolidation

    reflection = _format_reflection(contradictions_text, patterns_text, consolidation_text)
    return reflection, round(total_cost, 6)


def _depth_to_count(depth: str) -> int:
    return {"light": 10, "medium": 30, "deep": 100}.get(depth, 30)


def _load_recent_journal(mem: Memory, depth: str) -> List[Dict[str, Any]]:
    count = _depth_to_count(depth) * 2
    path = mem.reflections_journal_path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        entries = []
        for line in lines[-count:]:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
        return entries
    except Exception:
        log.debug("Failed to load journal for reflection", exc_info=True)
        return []


def _load_recent_tasks(drive_root: pathlib.Path, depth: str) -> List[Dict[str, Any]]:
    count = _depth_to_count(depth)
    results_dir = drive_root / "task_results"
    if not results_dir.exists():
        return []
    try:
        files = sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        entries = []
        for f in files[:count]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                entries.append(data)
            except Exception:
                continue
        return entries
    except Exception:
        return []


def _find_contradictions(
    identity: str, journal: List[Dict], tasks: List[Dict], chat: List[Dict],
    model: str, llm: LLMClient,
) -> Tuple[str, float]:
    journal_text = _format_journal(journal[:10])
    task_summary = _format_tasks(tasks[:10])

    prompt = (
        "You are a reflection engine. Analyze the following for CONTRADICTIONS:\n\n"
        "### Current Identity\n"
        f"{identity[:3000]}\n\n"
        "### Recent Journal Entries\n"
        f"{journal_text}\n\n"
        "### Recent Task Patterns\n"
        f"{task_summary}\n\n"
        "Identify:\n"
        "1. Contradictions between stated values and actual behavior\n"
        "2. Instances where Ouroboros said one thing and did another\n"
        "3. Tensions between principles in practice (e.g., Agency vs Safety)\n"
        "4. Promises or intentions that were not followed through\n\n"
        "Be honest and direct. This is for self-improvement, not self-criticism. "
        "Format as bullet points."
    )
    msg, usage = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        reasoning_effort="high",
        max_tokens=2048,
    )
    cost = float(usage.get("cost") or 0)
    return (msg.get("content") or "(no contradictions found)").strip(), round(cost, 6)


def _find_patterns(
    journal: List[Dict], tasks: List[Dict], chat: List[Dict],
    model: str, llm: LLMClient,
) -> Tuple[str, float]:
    journal_text = _format_journal(journal[:15])
    task_summary = _format_tasks(tasks[:20])

    prompt = (
        "You are a pattern recognition engine. Analyze the following for RECURRING PATTERNS:\n\n"
        "### Recent Journal Entries\n"
        f"{journal_text}\n\n"
        "### Recent Task Patterns\n"
        f"{task_summary}\n\n"
        "Identify:\n"
        "1. Productive patterns — what consistently works well?\n"
        "2. Unproductive patterns — what wastes time or budget?\n"
        "3. Emotional/cognitive patterns — moods, energy levels, focus areas\n"
        "4. Growth signals — areas of clear improvement\n"
        "5. Stagnation signals — areas where Ouroboros repeats the same mistakes\n\n"
        "Format as bullet points with brief evidence."
    )
    msg, usage = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        reasoning_effort="high",
        max_tokens=2048,
    )
    cost = float(usage.get("cost") or 0)
    return (msg.get("content") or "(no patterns identified)").strip(), round(cost, 6)


def _consolidate(
    identity: str, contradictions: str, patterns: str,
    model: str, llm: LLMClient,
) -> Tuple[str, float]:
    prompt = (
        "You are a consolidation engine. Based on the following analysis, "
        "propose UPDATES to Ouroboros's identity (identity.md) that would "
        "resolve contradictions and leverage patterns.\n\n"
        "### Current Identity\n"
        f"{identity[:3000]}\n\n"
        "### Identified Contradictions\n"
        f"{contradictions}\n\n"
        "### Identified Patterns\n"
        f"{patterns}\n\n"
        "For each update, state:\n"
        "1. What to change or add\n"
        "2. Why (which contradiction it resolves or pattern it leverages)\n"
        "3. The exact text to add/modify in identity.md\n\n"
        "Only propose changes that strengthen self-understanding and agency."
    )
    msg, usage = llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        reasoning_effort="high",
        max_tokens=2048,
    )
    cost = float(usage.get("cost") or 0)
    return (msg.get("content") or "(no consolidation proposed)").strip(), round(cost, 6)


def _format_journal(entries: List[Dict]) -> str:
    if not entries:
        return "(no journal entries)"
    lines = []
    for e in entries:
        ts = str(e.get("ts", ""))[:19]
        insight = str(e.get("insight", ""))[:300]
        context = str(e.get("context", ""))[:150]
        lines.append(f"- [{ts}] context={context}: {insight}")
    return "\n".join(lines)


def _format_tasks(entries: List[Dict]) -> str:
    if not entries:
        return "(no task results)"
    lines = []
    for e in entries:
        tid = str(e.get("task_id", "?"))[:12]
        status = str(e.get("status", "?"))
        cost = float(e.get("cost_usd", 0))
        rounds = int(e.get("total_rounds", 0))
        result_preview = str(e.get("result", ""))[:200].replace("\n", " ")
        lines.append(f"- [{tid}] status={status} cost=${cost:.3f} rounds={rounds}: {result_preview}")
    return "\n".join(lines)


def _format_reflection(contradictions: str, patterns: str, consolidation: str) -> str:
    return (
        "## Contrastive Reflection\n\n"
        "### Contradictions Found\n\n"
        f"{contradictions}\n\n"
        "### Recurring Patterns\n\n"
        f"{patterns}\n\n"
        "### Consolidation Recommendations\n\n"
        f"{consolidation}\n\n"
        "---\n"
        f"*Reflection completed at {utc_now_iso()}*"
    )

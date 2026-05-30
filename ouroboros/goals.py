"""
Ouroboros — Self-Directed Goal System.

Allows Ouroboros to set, track, and complete its own goals proactively.
Goals persist across restarts and guide background consciousness.

Philosophy: P0 (Agency — self-direction), P6 (Becoming — self-improvement),
P1 (Continuity — goals survive restarts).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from ouroboros.utils import utc_now_iso

log = logging.getLogger(__name__)

GOALS_FILE = "goals.json"


@dataclass
class Goal:
    id: str
    title: str
    description: str
    status: str = "active"  # active, in_progress, completed, abandoned
    priority: str = "medium"  # low, medium, high, critical
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    parent_goal_id: Optional[str] = None
    milestones: List[str] = field(default_factory=list)
    milestone_progress: int = 0
    notes: str = ""


class GoalManager:
    """Manages persistent goals for Ouroboros."""

    def __init__(self, drive_root: pathlib.Path):
        self._path = drive_root / "memory" / GOALS_FILE
        self._goals: Dict[str, Goal] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for g in data.get("goals", []):
                goal = Goal(**g)
                self._goals[goal.id] = goal
        except Exception as e:
            log.warning("Failed to load goals: %s", e)

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "goals": [asdict(g) for g in self._goals.values()],
            "updated_at": utc_now_iso(),
        }
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.rename(self._path)

    def add_goal(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        milestones: Optional[List[str]] = None,
        parent_goal_id: Optional[str] = None,
    ) -> str:
        goal_id = uuid.uuid4().hex[:12]
        now = utc_now_iso()
        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            priority=priority if priority in ("low", "medium", "high", "critical") else "medium",
            created_at=now,
            updated_at=now,
            milestones=milestones or [],
            parent_goal_id=parent_goal_id,
        )
        self._goals[goal_id] = goal
        self._save()
        return goal_id

    def update_goal(
        self,
        goal_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        milestone_progress: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        goal = self._goals.get(goal_id)
        if not goal:
            return False
        if status:
            valid = ("active", "in_progress", "completed", "abandoned")
            if status in valid:
                goal.status = status
                if status == "completed":
                    goal.completed_at = utc_now_iso()
        if priority:
            if priority in ("low", "medium", "high", "critical"):
                goal.priority = priority
        if milestone_progress is not None:
            goal.milestone_progress = max(0, min(max(1, len(goal.milestones)), milestone_progress))
        if notes:
            goal.notes = (goal.notes + "\n" + notes).strip() if goal.notes else notes
        goal.updated_at = utc_now_iso()
        self._save()
        return True

    def get_active_goals(self) -> List[Goal]:
        return [g for g in self._goals.values() if g.status in ("active", "in_progress")]

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def delete_goal(self, goal_id: str) -> bool:
        """Permanently remove a goal. Returns True if goal existed."""
        if goal_id not in self._goals:
            return False
        del self._goals[goal_id]
        self._save()
        return True

    def list_goals(self, filter_status: Optional[str] = None) -> str:
        goals = self._goals.values()
        if filter_status:
            goals = [g for g in goals if g.status == filter_status]
        if not goals:
            return "No goals found."
        goals = sorted(goals, key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(g.priority, 99))
        lines = [f"Goals ({len(goals)}):"]
        for g in goals:
            status_mark = {"active": "○", "in_progress": "◷", "completed": "✓", "abandoned": "×"}.get(g.status, "○")
            ms = f" [{g.milestone_progress}/{len(g.milestones)}]" if g.milestones else ""
            lines.append(f"  {status_mark} [{g.priority}] **{g.title}**{ms} ({g.id[:8]}...)")
            if g.description:
                lines.append(f"     {g.description[:120]}")
        return "\n".join(lines)

    def summary_for_context(self) -> str:
        active = self.get_active_goals()
        if not active:
            return ""
        lines = ["## Active Goals\n"]
        for g in sorted(active, key=lambda g: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(g.priority, 99)):
            lines.append(f"- **{g.title}** [{g.priority}]")
            if g.description:
                lines.append(f"  {g.description[:200]}")
            if g.milestones:
                for i, m in enumerate(g.milestones):
                    mark = "✓" if i < g.milestone_progress else "○"
                    lines.append(f"  {mark} {m}")
        return "\n".join(lines)

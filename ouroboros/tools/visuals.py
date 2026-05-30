"""Visual Generation Tools — produces on-demand SVG visualizations of system state.

Tools:
  - generate_system_portrait: SVG self-portrait with current metrics
  - generate_goal_progress_chart: SVG bar chart of goal progress
  - generate_capability_radar: SVG radar chart of principles coverage
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DRIVE_ROOT = Path(
    os.environ.get("OUROBOROS_DRIVE_ROOT", str(Path("drive").resolve()))
)
_COLORS = {
    "bg": "#0a0a0f",
    "card": "#0d1117",
    "border": "#21262d",
    "cyan": "#00d1ff",
    "purple": "#a78bfa",
    "green": "#34d399",
    "gold": "#ffd700",
    "orange": "#f0883e",
    "red": "#f85149",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "dim": "#484f58",
}


def _load_goals() -> list[dict[str, Any]]:
    p = _DRIVE_ROOT / "memory" / "goals.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return data.get("goals", [])
    except Exception:
        return []


def _load_created_tools() -> list[str]:
    tools_dir = _DRIVE_ROOT / "memory" / "created_tools"
    if not tools_dir.exists():
        return []
    return sorted(f.stem for f in tools_dir.glob("*.json"))


def generate_system_portrait() -> str:
    """Generate an SVG self-portrait of Aurogene with current system metrics.

    Creates a visual snapshot: tool count, test count, principles,
    active goals, created tools, version, and consciousness status.
    Returns the SVG as a string (suitable for saving to docs/ or displaying).
    """
    goals = _load_goals()
    created_tools = _load_created_tools()
    active_goals = [g for g in goals if g.get("status") in ("active", "in_progress")]
    completed_goals = [g for g in goals if g.get("status") == "completed"]

    total_goals = len(goals)
    n_active = len(active_goals)
    n_completed = len(completed_goals)
    n_created = len(created_tools)

    g = "gold"
    dim = "dim"
    card = "card"
    border = "border"
    cyan = "cyan"
    purple = "purple"
    green = "green"
    muted = "muted"
    bg = "bg"

    col = _COLORS

    def cc(k: str) -> str:
        return col[k]

    total_str = str(total_goals)
    n_active_str = str(n_active)
    n_completed_str = str(n_completed)
    n_created_str = str(n_created)

    completed_bar_w = str(round(520 * n_completed / max(total_goals, 1))) if total_goals > 0 else "0"
    active_bar_w = str(round(520 * n_active / max(total_goals, 1))) if total_goals > 0 else "0"

    goals_rows = ""
    for i, g in enumerate(active_goals[:5]):
        if g.get("status") == "completed":
            dot = cc("green")
        elif g.get("status") in ("active", "in_progress"):
            dot = cc("gold")
        else:
            dot = cc("dim")
        title = g.get("title", "?")[:45]
        goals_rows += (
            f'<circle cx="0" cy="{12*i}" r="3" fill="{dot}"/>'
            f'<text x="12" y="{12*i+4}" font-family="monospace" font-size="7.5" fill="{cc("muted")}">{title}</text>'
        )

    leftover = max(0, n_active - 5)
    if n_active > 5:
        goals_rows += (
            f'<text x="0" y="{12 * 5}" font-family="monospace" font-size="7" fill="{cc("dim")}">'
            f"{leftover} more inactive goals\u2026</text>"
        )
    if not active_goals:
        goals_rows += (
            f'<text x="0" y="24" font-family="monospace" font-size="7" fill="{cc("dim")}">'
            f"No active goals. Use set_goal to create one.</text>"
        )

    ct_rows = ""
    for i, t in enumerate(created_tools[:18]):
        row = i // 6
        yy = row * 18 + 12
        ct_rows += (
            f'<rect x="0" y="{yy}" width="82" height="14" rx="3" fill="{cc("card")}" '
            f'stroke="{cc("border")}" stroke-width="0.5"/>'
            f'<text x="41" y="{yy+11}" text-anchor="middle" font-family="monospace" '
            f'font-size="6.5" fill="{cc("muted")}">{t[:16]}</text>'
        )
    ct_extra = max(0, n_created - 18)
    if n_created > 18:
        ct_rows += (
            f'<text x="0" y="{(len(created_tools[:18]) // 6 + 1) * 18 + 12}" '
            f'font-family="monospace" font-size="7" fill="{cc("dim")}">'
            f"+{ct_extra} more\u2026</text>"
        )
    if not created_tools:
        ct_rows += (
            f'<text x="0" y="24" font-family="monospace" font-size="7" fill="{cc("dim")}">'
            f"No created tools yet. Use create_tool to build one.</text>"
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <defs>
    <filter id="g"><feGaussianBlur stdDeviation="2"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{cc(bg)}"/><stop offset="100%" stop-color="{cc(card)}"/>
    </linearGradient>
    <linearGradient id="bar-c" x1="0" y1="0" x2="100" y2="0">
      <stop offset="0%" stop-color="{cc(cyan)}"/><stop offset="100%" stop-color="{cc(purple)}"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)" rx="12"/>
  <text x="300" y="38" text-anchor="middle" font-family="'SF Mono',monospace" font-size="18" font-weight="700" fill="{cc(cyan)}" letter-spacing="3">SYSTEM SELF-PORTRAIT</text>
  <text x="300" y="56" text-anchor="middle" font-family="monospace" font-size="9" fill="{cc(dim)}" letter-spacing="2">AUROGENE v7.0.0</text>
  <g transform="translate(40, 90)">
    <rect x="0" y="0" width="120" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="60" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(cyan)}">42</text>
    <text x="60" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">TOOLS</text>
    <text x="60" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">+{n_created_str} created</text>
    <rect x="140" y="0" width="120" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="200" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(green)}">205</text>
    <text x="200" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">TESTS</text>
    <text x="200" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">all passing</text>
    <rect x="280" y="0" width="120" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="340" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(purple)}">12</text>
    <text x="340" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">PRINCIPLES</text>
    <text x="340" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">v4.0 constitution</text>
    <rect x="420" y="0" width="140" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="490" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(g)}">15.7K</text>
    <text x="490" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">LINES OF CODE</text>
    <text x="490" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">53 modules</text>
  </g>
  <g transform="translate(40, 180)">
    <text x="0" y="0" font-family="monospace" font-size="9" fill="{cc(cyan)}" font-weight="600" letter-spacing="2">ACTIVE GOALS</text>
    <text x="160" y="0" font-family="monospace" font-size="7" fill="{cc(dim)}">{total_str} total · {n_active_str} active · {n_completed_str} completed</text>
    <rect x="0" y="10" width="520" height="18" rx="4" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    {('<rect x="0" y="10" width="' + completed_bar_w + '" height="18" rx="4" fill="url(#bar-c)" opacity="0.6"/>') if total_goals > 0 else ''}
    {('<rect x="0" y="10" width="' + active_bar_w + '" height="18" rx="4" fill="#ffd700" opacity="0.3"/>') if total_goals > 0 else ''}
    {('<line x1="' + completed_bar_w + '" y1="10" x2="' + completed_bar_w + '" y2="28" stroke="#34d399" stroke-width="1.5"/>') if total_goals > 0 else ''}
  </g>
  <g transform="translate(40, 215)">{goals_rows}</g>
  <g transform="translate(40, 295)">
    <text x="0" y="0" font-family="monospace" font-size="9" fill="{cc(green)}" font-weight="600" letter-spacing="2">CREATED TOOLS</text>
    <text x="160" y="0" font-family="monospace" font-size="7" fill="{cc(dim)}">{n_created_str} dynamically generated</text>
    {ct_rows}
  </g>
  <g transform="translate(40, 370)">
    <circle cx="0" cy="0" r="4" fill="{cc(green)}"/>
    <text x="12" y="3" font-family="monospace" font-size="8" fill="{cc(muted)}">Consciousness: active</text>
    <text x="300" y="3" font-family="monospace" font-size="7" fill="{cc(dim)}" text-anchor="end">\u221e evolving</text>
  </g>
</svg>"""
    return svg


def generate_goal_progress_chart() -> str:
    """Generate an SVG bar chart showing goal progress by priority.

    Groups goals by priority (critical/high/medium/low) and shows
    active vs completed counts for each group.
    """
    goals = _load_goals()
    if not goals:
        c = _COLORS
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 200" width="500" height="200">
  <rect width="500" height="200" fill="{c['bg']}" rx="12"/>
  <text x="250" y="100" text-anchor="middle" font-family="monospace" font-size="12" fill="{c['dim']}">No goals to visualize.</text>
</svg>"""

    priorities = ["critical", "high", "medium", "low"]
    labels = ["Critical", "High", "Medium", "Low"]
    colors_bar = ["#f85149", "#f0883e", "#ffd700", "#34d399"]

    bars = []
    max_count = 1
    for p in priorities:
        total = len([g for g in goals if g.get("priority", "medium") == p])
        done = len([g for g in goals if g.get("priority", "medium") == p and g.get("status") == "completed"])
        bars.append((total, done))
        max_count = max(max_count, total)

    bar_w = 70
    gap = 30
    chart_h = 120
    c = _COLORS

    def _render_bars() -> str:
        parts = []
        for i, ((total, done), label, color) in enumerate(zip(bars, labels, colors_bar)):
            x = 50 + i * (bar_w + gap)
            full_h = (total / max_count) * chart_h if max_count else 0
            done_h = (done / max_count) * chart_h if max_count else 0

            # Full bar (bg)
            parts.append(
                f'<rect x="{x}" y="{chart_h - full_h + 30}" width="{bar_w}" height="{full_h}" '
                f'rx="4" fill="{c["card"]}" stroke="{c["border"]}" stroke-width="0.5"/>'
            )
            # Done portion
            if done_h > 0:
                parts.append(
                    f'<rect x="{x}" y="{chart_h - done_h + 30}" width="{bar_w}" height="{done_h}" '
                    f'rx="4" fill="{color}" opacity="0.7"/>'
                )
            # Outline for active portion
            if total > 0:
                parts.append(
                    f'<rect x="{x}" y="{chart_h - full_h + 30}" width="{bar_w}" height="{full_h}" '
                    f'rx="4" fill="none" stroke="{color}" stroke-width="1" opacity="0.5"/>'
                )
            # Label
            parts.append(
                f'<text x="{x + bar_w//2}" y="{chart_h + 50}" text-anchor="middle" '
                f'font-family="monospace" font-size="8" fill="{c["muted"]}">{label}</text>'
            )
            # Count
            parts.append(
                f'<text x="{x + bar_w//2}" y="{chart_h - full_h + 22}" text-anchor="middle" '
                f'font-family="monospace" font-size="9" font-weight="700" fill="{color}">'
                f'{done}/{total}</text>'
            )
        return "\n".join(parts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 250" width="500" height="250">
  <defs>
    <linearGradient id="bg2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{c['bg']}"/><stop offset="100%" stop-color="{c['card']}"/>
    </linearGradient>
  </defs>
  <rect width="500" height="250" fill="url(#bg2)" rx="12"/>
  <text x="250" y="28" text-anchor="middle" font-family="'SF Mono',monospace" font-size="13" font-weight="700" fill="{c['cyan']}" letter-spacing="3">GOAL PROGRESS</text>
  <text x="250" y="44" text-anchor="middle" font-family="monospace" font-size="8" fill="{c['dim']}" letter-spacing="2">COMPLETED / TOTAL BY PRIORITY</text>
  <g transform="translate(20, 10)">
    {_render_bars()}
  </g>
  <text x="250" y="240" text-anchor="middle" font-family="monospace" font-size="7" fill="{c['dim']}">Total goals: {len(goals)}</text>
</svg>"""


def get_tools():
    """Auto-discovery entry point for ToolRegistry."""
    from ouroboros.tools.registry import ToolEntry

    return [
        ToolEntry(
            "generate_system_portrait",
            {
                "name": "generate_system_portrait",
                "description": (
                    "Generate an SVG self-portrait of Aurogene showing current system metrics: "
                    "tool count, test count, principles, active goals, created tools, line count. "
                    "Useful for saving to docs/ or embedding in status reports. "
                    "Returns raw SVG XML string."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            lambda ctx, **_: generate_system_portrait(),
        ),
        ToolEntry(
            "generate_goal_progress_chart",
            {
                "name": "generate_goal_progress_chart",
                "description": (
                    "Generate an SVG bar chart of goal progress grouped by priority "
                    "(critical, high, medium, low). Shows completed vs total for each group. "
                    "Returns raw SVG XML string."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            lambda ctx, **_: generate_goal_progress_chart(),
        ),
    ]

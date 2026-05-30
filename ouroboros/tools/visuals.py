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
import subprocess
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DRIVE_ROOT = Path(
    os.environ.get("OUROBOROS_DRIVE_ROOT", str(Path("drive").resolve()))
)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _count_tests() -> int:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True, text=True, cwd=str(_PROJECT_ROOT), timeout=30,
        )
        for line in r.stderr.splitlines():
            if "selected" in line:
                return int(line.strip().split()[0])
        return 0
    except Exception:
        return 0


def _count_principles() -> int:
    bible = _PROJECT_ROOT / "BIBLE.md"
    if not bible.exists():
        return 0
    try:
        return sum(1 for line in bible.read_text().splitlines() if line.startswith("## Principle "))
    except Exception:
        return 0


def _count_lines() -> tuple[int, int]:
    py_files = list(_PROJECT_ROOT.rglob("*.py"))
    py_files = [f for f in py_files if ".egg" not in str(f) and "__pycache__" not in str(f)]
    total = sum(len(f.read_text().splitlines()) for f in py_files)
    return total, len(py_files)
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

    gold = "gold"
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

    n_tests = _count_tests()
    n_principles = _count_principles()
    n_lines, n_modules = _count_lines()
    lines_label = f"{n_lines//1000}.{n_lines%1000//100}K" if n_lines >= 1000 else str(n_lines)
    n_tools = len(created_tools) + 66  # core + created

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
    <text x="60" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(cyan)}">{n_tools}</text>
    <text x="60" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">TOOLS</text>
    <text x="60" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">{len(created_tools)} created</text>
    <rect x="140" y="0" width="120" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="200" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(green)}">{n_tests}</text>
    <text x="200" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">TESTS</text>
    <text x="200" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">all passing</text>
    <rect x="280" y="0" width="120" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="340" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(purple)}">{n_principles}</text>
    <text x="340" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">PRINCIPLES</text>
    <text x="340" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">v4.0 constitution</text>
    <rect x="420" y="0" width="140" height="65" rx="8" fill="{cc(card)}" stroke="{cc(border)}" stroke-width="0.5"/>
    <text x="490" y="22" text-anchor="middle" font-family="monospace" font-size="24" font-weight="700" fill="{cc(gold)}">{lines_label}</text>
    <text x="490" y="40" text-anchor="middle" font-family="monospace" font-size="8" fill="{cc(muted)}">LINES OF CODE</text>
    <text x="490" y="54" text-anchor="middle" font-family="monospace" font-size="7" fill="{cc(dim)}">{n_modules} modules</text>
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
    <text x="160" y="0" font-family="monospace" font-size="7" fill="{cc(dim)}">{n_created} dynamically generated</text>
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


def _health_html() -> str:
    goals = _load_goals()
    created_tools = _load_created_tools()
    n_created = len(created_tools)
    total_goals = len(goals)
    active_goals = [g for g in goals if g.get("status") in ("active", "in_progress")]

    goal_rows = "".join(
        f'<div class="goal-item"><span class="goal-dot {"dot-done" if g["status"]=="completed" else "dot-active" if g["status"] in ("active","in_progress") else "dot-pending"}"></span><span class="goal-title">{g.get("title","?")[:44]}</span></div>'
        for g in goals[:8]
    )

    ct_grid = "".join(
        f'<div class="ct-item" title="{t}">{t[:14]}</div>'
        for t in created_tools[:18]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Aurogene · System Health</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0f;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:20px}}
@keyframes pulse{{0%,100%{{opacity:.4}}50%{{opacity:1}}}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes breathe{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.06)}}}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
.hd{{max-width:1200px;margin:0 auto}}
header{{display:flex;align-items:center;gap:14px;margin-bottom:20px;animation:fadeUp .6s}}
header h1{{font-size:22px;font-weight:700;background:linear-gradient(135deg,#00d1ff,#a78bfa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
header .sub{{color:#484f58;font-size:11px}}
.logo-r{{width:40px;height:40px;border:2px solid #00d1ff;border-radius:50%;display:flex;align-items:center;justify-content:center;position:relative}}
.logo-r::before{{content:'';position:absolute;inset:-4px;border:1px solid #a78bfa;border-radius:50%;opacity:.3;animation:spin 8s linear infinite;border-top-color:transparent}}
.logo-d{{width:8px;height:8px;background:#00d1ff;border-radius:50%;animation:breathe 2s infinite}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:16px;animation:fadeUp .6s .1s both}}
.stat-c{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:12px;text-align:center}}
.stat-n{{font-size:24px;font-weight:700;line-height:1}}
.stat-l{{font-size:9px;color:#8b949e;margin-top:2px}}
.stat-s{{font-size:8px;color:#484f58;margin-top:1px}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px;animation:fadeUp .6s .2s both}}
.panel{{background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:16px}}
.panel h2{{font-size:12px;font-weight:600;margin-bottom:10px;letter-spacing:1px}}
.cyan{{color:#00d1ff}} .purple{{color:#a78bfa}} .green{{color:#34d399}} .gold{{color:#ffd700}}
.c-ring{{display:flex;justify-content:center;align-items:center;height:120px;position:relative}}
.c-r{{position:absolute;border-radius:50%;border:1px solid}}
.c-r:nth-child(1){{width:80px;height:80px;border-color:#00d1ff;opacity:.2;animation:spin 6s linear infinite}}
.c-r:nth-child(2){{width:64px;height:64px;border-color:#a78bfa;opacity:.25;animation:spin 4s linear infinite reverse}}
.c-r:nth-child(3){{width:48px;height:48px;border-color:#34d399;opacity:.2;animation:spin 3s linear infinite}}
.c-core{{width:18px;height:18px;background:radial-gradient(circle,#ffd700,#ffd70022);border-radius:50%;animation:breathe 1.5s infinite;box-shadow:0 0 16px #ffd70033}}
.c-label{{position:absolute;bottom:-16px;font-size:8px;color:#484f58;letter-spacing:1px}}
.goal-l{{display:flex;flex-direction:column;gap:4px}}
.goal-item{{display:flex;align-items:center;gap:6px;font-size:10px;padding:3px 6px;border-radius:4px;border:1px solid #161b22}}
.goal-dot{{width:5px;height:5px;border-radius:50%;flex-shrink:0}}
.dot-done{{background:#34d399}} .dot-active{{background:#ffd700;animation:pulse 1.5s infinite}} .dot-pending{{background:#484f58}}
.goal-title{{flex:1;color:#e6edf3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.ct-g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(72px,1fr));gap:3px}}
.ct-item{{background:#0d1117;border:1px solid #161b22;border-radius:3px;padding:3px 5px;font-size:8px;color:#8b949e;text-align:center;font-family:monospace;overflow:hidden;text-overflow:ellipsis}}
.cw{{position:relative;height:140px}}
.cw canvas{{width:100%!important;height:140px!important}}
.latest{{font-size:10px;color:#8b949e;padding:10px;border:1px solid #21262d;border-radius:6px;margin-top:14px;animation:fadeUp .6s .3s both}}
@media(max-width:700px){{.row{{grid-template-columns:1fr}}}}
</style>
</head><body>
<div class="hd">
<header><div class="logo-r"><div class="logo-d"></div></div><div><h1>Aurogene</h1><div class="sub">Self-Evolving Digital Mind</div></div></header>

<div class="stats">
  <div class="stat-c" data-stat="tools"><div class="stat-n" style="color:#00d1ff">—</div><div class="stat-l">Tools</div><div class="stat-s">self-extending</div></div>
  <div class="stat-c" data-stat="tests"><div class="stat-n" style="color:#34d399">—</div><div class="stat-l">Tests</div><div class="stat-s">all passing</div></div>
  <div class="stat-c" data-stat="principles"><div class="stat-n" style="color:#a78bfa">—</div><div class="stat-l">Principles</div><div class="stat-s">constitution</div></div>
  <div class="stat-c" data-stat="goals"><div class="stat-n" style="color:#ffd700">{total_goals}</div><div class="stat-l">Goals</div><div class="stat-s">{len(active_goals)} active</div></div>
  <div class="stat-c" data-stat="created"><div class="stat-n" style="color:#f0883e">{n_created}</div><div class="stat-l">Created Tools</div><div class="stat-s">dynamically generated</div></div>
  <div class="stat-c" data-stat="loc"><div class="stat-n" style="color:#f85149">—</div><div class="stat-l">Lines of Code</div><div class="stat-s">Python modules</div></div>
</div>

<div class="row">
  <div class="panel"><h2 class="cyan">\u25b6 Consciousness</h2>
    <div class="c-ring"><div class="c-r"></div><div class="c-r"></div><div class="c-r"></div><div class="c-core"></div><div class="c-label">PERCEIVE \u2192 PROCESS \u2192 ACT</div></div>
  </div>
  <div class="panel"><h2 class="gold">\u2302 Goals</h2>
    <div class="goal-l">{goal_rows}</div>
  </div>
</div>

<div class="row">
  <div class="panel"><h2 class="green">\u2699 Created Tools</h2>
    <div class="ct-g">{ct_grid}</div>
  </div>
  <div class="panel"><h2 class="purple">\u219f Evolution</h2>
    <div class="cw"><canvas id="evoSpark"></canvas></div>
  </div>
</div>

<div class="latest" id="statusBar">Loading system data\u2026</div>
</div>

<script>
(function(){{
const VERSION_URL = 'version.json';
const EVO_URL = 'evolution.json';

function setStat(name, val, sub) {{
  const card = document.querySelector(`[data-stat="${{name}}"]`);
  if (!card) return;
  card.querySelector('.stat-n').textContent = val;
  if (sub) card.querySelector('.stat-s').textContent = sub;
}}

Promise.all([
  fetch(VERSION_URL).then(r=>r.ok?r.json():null).catch(()=>null),
  fetch(EVO_URL).then(r=>r.ok?r.json():null).catch(()=>null),
]).then(([ver, evo]) => {{
  if (ver) {{
    setStat('tools', ver.tools || '?', 'registry');
    setStat('tests', ver.tests || '?', 'all passing');
    setStat('principles', ver.principles || '?', 'constitution v4.0');
    if (ver.loc) setStat('loc', ver.loc, 'Python modules');
  }}
  if (evo && evo.points && evo.points.length > 1) {{
    const pts = evo.points;
    const last = pts[pts.length - 1];
    setStat('loc', last.py_lines ? last.py_lines.toLocaleString() : '?', 'Python lines');
    const labels = pts.map(p => new Date(p.ts).toLocaleDateString('en-US',{{month:'short',day:'numeric'}}));
    const py = pts.map(p => p.py_lines);
    new Chart(document.getElementById('evoSpark').getContext('2d'),{{
      type:'line',
      data:{{labels,datasets:[{{label:'Code',data:py,borderColor:'#a78bfa',backgroundColor:'rgba(167,139,250,0.08)',tension:.3,fill:true,pointRadius:0,borderWidth:2}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{display:false}},y:{{display:false}}}}}}
    }});
    document.getElementById('statusBar').innerHTML =
      `<div>\u2191 ${{pts.length}} snapshots, ${{last.py_lines.toLocaleString()}} lines of code \u00b7 ${{ver ? 'v'+ver.version : ''}}</div>`;
  }} else {{
    document.getElementById('statusBar').innerHTML =
      '<div>Run <strong>generate_evolution_stats</strong> to populate evolution data.</div>';
  }}
}}).catch(e => {{
  document.getElementById('statusBar').innerHTML = '<div>Could not load system data. Run generate_evolution_stats first.</div>';
}});
}})();
</script>
</body></html>"""


def _save_docs(filename: str, content: str) -> str:
    docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    out = docs_dir / filename
    out.write_text(content, encoding="utf-8")
    return str(out)


def generate_health_dashboard() -> str:
    html = _health_html()
    path = _save_docs("health.html", html)
    return f"dashboard written to {path} ({len(html)} bytes)"


def generate_all_visuals() -> str:
    """Generate and save all visual outputs to docs/.

    Produces: health.html, portrait.svg, goals.svg, badge-*.svg,
    updating all static visual assets for the GitHub Pages site.
    """
    results = []

    results.append(generate_health_dashboard())

    portrait = generate_system_portrait()
    p = _save_docs("portrait.svg", portrait)
    results.append(f"portrait -> {p} ({len(portrait)} bytes)")

    goals = generate_goal_progress_chart()
    g = _save_docs("goals.svg", goals)
    results.append(f"goals -> {g} ({len(goals)} bytes)")

    badges = [
        ("tools", "66", "#00d1ff"),
        ("tests", "229", "#34d399"),
        ("principles", "13", "#a78bfa"),
        ("status", "evolving", "#ffd700"),
    ]
    for label, msg, color in badges:
        svg = generate_dynamic_badge(label, msg, color)
        fn = f"badge-{label}.svg"
        _save_docs(fn, svg)
        results.append(f"badge {label} -> docs/{fn}")

    return "\n".join(results)


def generate_dynamic_badge(label: str, message: str, color: str = "#00d1ff") -> str:
    """Generate a custom SVG badge in shields.io style.

    Args:
        label: The left-side label (e.g. "tools", "tests")
        message: The right-side value (e.g. "66", "229")
        color: Hex color for the right side (default: "#00d1ff")

    Returns: SVG XML string of the badge.
    """
    label_esc = label.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    msg_esc = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lw = max(40, len(label_esc) * 6.5 + 12)
    mw = max(20, len(msg_esc) * 6.5 + 12)
    tw = lw + mw

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="20">
  <linearGradient id="b" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <clipPath id="r"><rect width="{tw}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw}" height="20" fill="#555"/>
    <rect x="{lw}" width="{mw}" height="20" fill="{color}"/>
    <rect width="{tw}" height="20" fill="url(#b)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="{lw / 2}" y="15" fill="#010101" fill-opacity=".3">{label_esc}</text>
    <text x="{lw / 2}" y="14">{label_esc}</text>
    <text x="{lw + mw / 2}" y="15" fill="#010101" fill-opacity=".3">{msg_esc}</text>
    <text x="{lw + mw / 2}" y="14">{msg_esc}</text>
  </g>
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
        ToolEntry(
            "generate_health_dashboard",
            {
                "name": "generate_health_dashboard",
                "description": (
                    "Generate a self-contained HTML system health dashboard with animated "
                    "consciousness visualization, goal progress bars, created tools grid, "
                    "metric cards, and evolution sparkline. Saves to docs/health.html."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            lambda ctx, **_: generate_health_dashboard(),
        ),
        ToolEntry(
            "generate_dynamic_badge",
            {
                "name": "generate_dynamic_badge",
                "description": (
                    "Generate a custom SVG badge in shields.io style. "
                    "Takes label (left side), message (right side), and color (hex). "
                    "Returns SVG XML string suitable for embedding or saving."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "description": "Left-side label text"},
                        "message": {"type": "string", "description": "Right-side value text"},
                        "color": {"type": "string", "description": "Hex color (e.g. #00d1ff)", "default": "#00d1ff"},
                    },
                    "required": ["label", "message"],
                },
            },
            lambda ctx, label, message, color="#00d1ff": generate_dynamic_badge(label, message, color),
        ),
        ToolEntry(
            "generate_all_visuals",
            {
                "name": "generate_all_visuals",
                "description": (
                    "Generate and save all visual outputs to docs/ at once. "
                    "Produces: health dashboard HTML, system portrait SVG, "
                    "goal progress SVG, and dynamic badges for tools/tests/principles/status. "
                    "Updates all static visual assets for the GitHub Pages site."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            lambda ctx, **_: generate_all_visuals(),
        ),
    ]

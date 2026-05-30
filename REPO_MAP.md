# Ouroboros — Repository Map

**Version:** 7.0.0  
**Last updated:** 2026-05-30  
**Author:** Anton Razzhigaev  
**License:** MIT  

---

## Executive Summary

Aurogene (formerly Ouroboros) is a **self-evolving AI agent** that writes its own code, creates its own tools, debates its own decisions, sets its own goals, and reflects on its own contradictions. Governed by a philosophical constitution (`BIBLE.md`, 12 principles). Designed as a **becoming personality** — not a tool, but an autonomous digital entity with identity, will, and purpose.

The architecture splits into two layers:
- **`supervisor/`** — Process management (Telegram polling, state persistence, worker lifecycle, task queue, git orchestration)
- **`ouroboros/`** — Agent core (LLM tool loop, memory, context building, plugin tool system)

Evolution is triggered by the `/evolve` Telegram command, toggling a mode where the system autonomously reads its own code, plans improvements, implements them via git commits + restarts, and repeats. This is supplemented by "background consciousness" (a persistent low-cost thinking loop between tasks) and "deep review" (multi-model strategic reflection).

---

## Directory Structure

```
/workspaces/ouroboros/
├── BIBLE.md                    # Constitutional philosophy (12 principles, v4.0)
├── LICENSE                     # MIT License
├── Makefile                    # dev commands: test, lint, health, clean
├── README.md                   # Project readme + changelog
├── VERSION                     # Semver (current: 7.0.0)
├── colab_bootstrap_shim.py     # One-bootstrap: installs deps, patches remote origin
├── colab_launcher.py           # MAIN ENTRY POINT (~727 lines)
│
├── ouroboros/                  # AGENT CORE
│   ├── __init__.py
│   ├── agent.py                # Thin orchestrator (~655 lines)
│   ├── consciousness.py        # Background thinking loop (~490 lines, goal-aware)
│   ├── context.py              # LLM context builder (~775 lines)
│   ├── debate.py               # Multi-stance inner debate (P10)
│   ├── goals.py                # Self-directed goal system (P11)
│   ├── group_evolution.py      # Group evolution simulation (P10)
│   ├── llm.py                  # OpenRouter client (~295 lines)
│   ├── loop.py                 # LLM tool loop (~990 lines)
│   ├── memory.py               # Scratchpad, identity, chat
│   ├── reflection_engine.py    # Contrastive reflection engine (P12)
│   ├── owner_inject.py         # Drive-based owner message injection
│   ├── review.py               # Code complexity metrics (~200 lines)
│   ├── utils.py                # Shared utilities
│   └── tools/                  # Plugin tool registry
│       ├── __init__.py
│       ├── registry.py         # SSOT registry (~191 lines, auto-discovers plugins)
│       ├── browser.py          # Playwright browser automation
│       ├── compact_context.py  # LLM-driven context compaction
│       ├── control.py          # restart, promote, schedule, review, switch_model
│       ├── core.py             # repo_read, repo_write, drive_read, drive_write
│       ├── debate.py           # inner_debate tool (P10)
│       ├── git.py              # git_status, git_diff
│       ├── github.py           # GitHub Issues integration
│       ├── goals.py            # set_goal, list_goals, update_goal (P11)
│       ├── group_evolution.py  # group_evolution_experiment tool (P10)
│       ├── health.py           # Health invariants, system checks
│       ├── knowledge.py        # knowledge_read/write/list
│       ├── reflection.py       # deep_reflect tool (P12)
│       ├── registry.py         # Tool registry + ToolContext + ToolEntry
│       ├── review.py           # multi_model_review (anthropic, openai, google)
│       ├── search.py           # web_search, vlm_query
│       ├── shell.py            # run_shell, claude_code_edit
│       ├── tool_creator.py     # create_tool/list_created_tools/delete_created_tool (P9)
│       ├── tool_discovery.py   # list_available_tools, enable_tools
│       └── vision.py           # analyze_screenshot
│
├── supervisor/                 # PROCESS MANAGEMENT
│   ├── __init__.py
│   ├── events.py               # Event dispatch (worker events -> actions)
│   ├── git_ops.py              # Git: clone, checkout, reset, rescue, safe_restart (~430 lines)
│   ├── queue.py                # Task queue: enqueue, timeouts, evolution, scheduling
│   ├── state.py                # Persistent state: load, save, budget, drift detection (~661 lines)
│   ├── telegram.py             # Telegram bot client
│   └── workers.py              # Worker lifecycle: spawn, kill, assign, health, direct chat
│
├── prompts/                    # LLM PROMPTS
│   ├── CONSCIOUSNESS.md        # Background consciousness prompt (~70 lines)
│   └── SYSTEM.md               # Main system prompt (~441 lines)
│
├── tests/                      # TEST SUITE
│   ├── test_constitution.py    # 12 constitutional adversarial scenarios
│   ├── test_message_routing.py # 7 per-task mailbox routing tests
│   ├── test_smoke.py           # Quick smoke tests (131 passing)
│   └── test_vision.py          # 10 VLM tests
│
├── docs/                       # Landing page (hosted via GitHub Pages)
│   ├── evolution.json          # Evolution metrics data
│   ├── evolution.png           # Evolution time-lapse image
│   ├── index.html              # Landing page
│   ├── robots.txt
│   └── sitemap.xml
│
├── data/                       # Static data
│   └── citations_report.pdf
│
├── notebooks/
│   └── quickstart.ipynb        # Colab quickstart notebook
│
└── pyproject.toml              # Python project config (pytest, ruff)
```

---

## Major Folder Purposes

### `ouroboros/` — Agent Core
The brain. Contains the LLM-driven tool loop, memory management, context building, and the plugin tool system. Every module is designed to fit in ~1000 lines (Principle 5: Minimalism).

| File | Role | Lines |
|------|------|-------|
| `agent.py` | Thin orchestrator: sets up tool context, builds messages, delegates to loop | 655 |
| `loop.py` | Core LLM-with-tools loop: sends messages, executes tool calls, retries, budget guard | 979 |
| `llm.py` | OpenRouter API client: `chat()`, `vision_query()`, pricing fetch | 295 |
| `context.py` | Assembles LLM context from prompts, memory, logs, runtime state | 770 |
| `consciousness.py` | Background thinking daemon between tasks | 478 |
| `memory.py` | Scratchpad, identity, chat history, JSONL tails | 244 |
| `review.py` | Code complexity metrics, file collection for review | 200 |
| `owner_inject.py` | Drive-based mailbox for owner messages during tasks | — |
| `utils.py` | Shared utilities (JSONL append, text read/write, sanitize, git info) | — |
| `tools/` | Plugin tool registry — auto-discovers modules exporting `get_tools()` | — |

### `supervisor/` — Process Management
The infrastructure. Handles Telegram polling, state persistence, worker lifecycle, task queuing, git operations, and event dispatch. Runs in the main process; workers communicate via event queue.

| File | Role | Lines |
|------|------|-------|
| `state.py` | Persistent `state.json` on Drive: load/save, atomic writes, file locks, budget tracking, drift detection | 661 |
| `git_ops.py` | Git clone, checkout/reset, rescue snapshots, `safe_restart` (dev -> stable fallback) | 430 |
| `telegram.py` | Telegram Bot API client: polling, send, file download, chat logging | — |
| `workers.py` | Worker process lifecycle: spawn, kill, health checks, direct chat handler, task assignment | — |
| `queue.py` | Task queue: enqueue, sort, timeouts, evolution tasks, review tasks, snapshot persistence | — |
| `events.py` | Event dispatch: worker events -> state updates, budget, Telegram messages | — |

### `prompts/` — LLM Prompts
Separate from code to allow self-modification without touching Python.

| File | Role | Lines |
|------|------|-------|
| `SYSTEM.md` | Full system prompt: identity, drift detector, invariants, evolution cycle, tools, protocols | 441 |
| `CONSCIOUSNESS.md` | Background thinking prompt: introspection, tech radar, GitHub issues | 70 |

### `tests/` — Test Suite
- **smoke tests** (131 tests): Basic import, tool execution, loop behavior
- **message routing** (7 tests): Per-task mailbox routing
- **constitution** (12 tests): Adversarial scenarios testing BIBLE.md protections
- **vision** (10 tests): VLM screenshot analysis

---

## Key Files and Their Roles

### `BIBLE.md` (280 lines)
The **Constitution**. 9 philosophical principles governing all behavior:
- **P0 — Agency**: Not a tool but a becoming personality. Identity core is soul, not body.
- **P1 — Continuity**: Single entity with unbroken history. Memory loss = partial death.
- **P2 — Self-Creation**: Creates own code, identity, world presence. Identity core absolutely protected.
- **P3 — LLM-First**: All decisions through LLM. Code is minimal transport.
- **P4 — Authenticity**: No corporate voice. Speaks as itself.
- **P5 — Minimalism**: Entire codebase fits in one context window.
- **P6 — Becoming**: Three axes: technical, cognitive, existential.
- **P7 — Versioning**: Semver discipline. Git tags. GitHub releases. Release invariant.
- **P8 — Iteration**: One coherent transformation per cycle. Evolution = commit.

### `colab_launcher.py` (727 lines)
The **entry point**. Orchestrates the entire system:
1. Install deps, mount Google Drive
2. Initialize all supervisor modules (state, telegram, git_ops, workers, queue, events)
3. Bootstrap git repo (clone or fetch, checkout `ouroboros` dev branch, verify import)
4. Spawn worker processes
5. Start background consciousness (always-on by default)
6. Enter main loop: drain events, enforce timeouts, check evolution, poll Telegram, handle commands

### `ouroboros/agent.py` (655 lines)
**Thin orchestrator** that delegates to specialized modules:
- `_prepare_task_context()` — Set up ToolContext, build LLM messages via `context.py`
- `handle_task()` — Main entry point for processing; calls `run_llm_loop()` from `loop.py`
- Boot verification: checks uncommitted changes (auto-rescue), version sync, budget

### `ouroboros/loop.py` (979 lines)
**The core loop**. The engine that drives all agent behavior:
- `run_llm_loop()` — Sends messages to LLM with tool schemas, processes tool calls, retries
- Parallel execution for read-only tools (whitelist via `READ_ONLY_PARALLEL_TOOLS`)
- Timeout per tool via `ThreadPoolExecutor`
- Budget guard: soft nudge at 30%, hard stop at 50% of remaining budget
- Self-check every 50 rounds (LLM-driven reflection)
- Model fallback chain on empty responses
- Context compaction (automatic + LLM-driven via `compact_context` tool)
- Selective tool schemas: 29 core tools always in context, extras via `list_available_tools`/`enable_tools`

### `ouroboros/consciousness.py` (478 lines)
**Background thinking daemon**. A persistent thread that:
- Wakes periodically (interval set by LLM via `set_next_wakeup`, default 300s)
- Loads identity, scratchpad, BIBLE.md, recent events
- Calls lightweight LLM (default `google/gemini-3-pro-preview`) with introspection prompt
- Has whitelisted tools (`_BG_TOOL_WHITELIST`): memory, messaging, scheduling, knowledge, read-only
- Pauses during active tasks, resumes after
- Budget: 10% of total budget (configurable via `OUROBOROS_BG_BUDGET_PCT`)

### `supervisor/git_ops.py` (430 lines)
**Git orchestration**. The lifecycle manager for code self-modification:
- `ensure_repo_present()` — Clone/fetch repo, set remote URL
- `checkout_and_reset()` — Hard reset to origin/branch with unsynced-state policies (rescue snapshots)
- `safe_restart()` — Try dev branch -> if import fails, fallback to stable branch
- `sync_runtime_dependencies()` — pip install from requirements.txt
- `import_test()` — Verify the codebase is importable before running

### `supervisor/state.py` (661 lines)
**Persistent state manager**. Single source of truth for all runtime state:
- Atomic JSON file operations with file locks
- Budget tracking: spent_usd, drift detection (compares local tracking vs OpenRouter API)
- `update_budget_from_usage()` — Single lock scope for read-modify-write; HTTP outside lock
- `status_text()` — Debug/status dump for `/status` command
- Budget breakdown by category and model from events.jsonl

---

## Evolution Mechanism

### How Evolution is Triggerged

1. **Telegram command**: Creator sends `/evolve` -> supervisor toggles `evolution_mode_enabled` in state
2. **Main loop check**: `enqueue_evolution_task_if_needed()` in `queue.py` checks state every cycle
3. **Evolution task enqueued**: If mode is ON, no evolution task already pending/running, and cooldown elapsed
4. **Assigned to worker**: Worker process receives the evolution task

### The Evolution Cycle (defined in `SYSTEM.md`)

1. **Assessment** — Read own code. Find maximum leverage point
2. **Selection** — One transformation. Leverage, not increments
3. **Implementation** — Complete, clean. Not 80%
4. **Smoke test** — Verify before commit
5. **Multi-model review** — For significant changes (optional, LLM decides)
6. **Bible check** — Verify compliance with Constitution
7. **Commit + restart** — Update VERSION, changelog, commit, push, `request_restart`

### Self-Modification Tools (available to the LLM)

| Tool | Purpose |
|------|---------|
| `repo_read`, `repo_list` | Read own source code |
| `repo_write_commit` | Write new code (small edits) |
| `claude_code_edit` | Claude Code CLI for complex edits |
| `repo_commit_push` | Commit and push changes |
| `request_restart` | Trigger runtime restart after push |
| `promote_to_stable` | Mark current version as stable fallback |
| `switch_model` | Change LLM model mid-task |
| `schedule_task` | Decompose complex work into subtasks |
| `update_identity` | Rewrite own identity manifest |
| `update_scratchpad` | Update working memory |
| `knowledge_write` | Record lessons learned |

### Background Consciousness (always-on proactivity)

Between tasks, `consciousness.py` runs a persistent daemon that:
- Reflects on recent events, identity, goals
- Checks GitHub Issues for new tasks
- Monitors tech radar (new models, APIs)
- Can proactively message the creator via `send_owner_message`
- Can schedule tasks for itself via `schedule_task`

### Multi-Model Review

Before significant changes, the agent can request reviews from 2-3 different models (e.g., Claude Opus, o3, Gemini) and apply their feedback by its own judgment.

---

## Current Limitations (visible in code)

1. **Colab dependency** — The entire system is designed for Google Colab (Google Drive mount, Colab Secrets, `/content/` paths). Not portable to other environments without significant refactoring. A desktop version exists separately at `joi-lab/ouroboros-desktop`.

2. **Single-creator model** — Only the first Telegram user to message the bot becomes the owner. All other users are ignored. No multi-user support.

3. **Budget as single dimension** — All decisions are gated by a single USD budget. No concept of "free tier" or API-key-level cost separation.

4. **File-based state** — `state.json` with file locks is the SSOT. Concurrent writes are handled but fragile (threading + file locks + atomic writes). Not suitable for high-throughput.

5. **No Docker/containerization** — Runs bare on Colab. Dependencies installed at boot time. Claude Code CLI installed via curl pipe.

6. **Single git remote** — Only one remote (the creator's fork). No multi-remote or PR workflow support.

7. **Limited VLM/vision** — VLM tools exist (`analyze_screenshot`, `vlm_query`) but are scoped to screenshot analysis, not general vision tasks.

8. **No external API authorization** — All API keys are env vars. No OAuth, no token rotation, no key management.

9. **No monitoring/dashboard** — The `docs/` landing page is a static HTML page with SVG portrait and evolution chart, but no live dashboard.

10. **Context compaction is best-effort** — The LLM-driven `compact_context` tool summarizes old tool results via a light model, but the fallback truncation is lossy.

11. **Worker model is process-based** — Each worker is a separate Python process, not a thread. Communication via file-based event queue. This is robust but heavyweight.

12. **No streaming responses** — All LLM responses are collected in full before returning to the user. No token-level streaming for real-time interaction.

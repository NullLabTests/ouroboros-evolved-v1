"""
Aurogene — self-evolving digital mind.

Philosophy: BIBLE.md (12 principles, v4.0)
Architecture: agent (orchestrator) + tools (plugin tools) + loop (tool loop)
              + consciousness (background thinking) + llm (LLM client)
              + memory (identity, journal) + debate (inner debate)
              + goals (self-directed) + group_evolution (collective sim)
              + reflection_engine (deep reflection) + utils (shared utils).
"""

# IMPORTANT: Do NOT import agent/loop/llm/etc here!
# colab_launcher.py imports ouroboros.apply_patch, which triggers __init__.py.
# Any eager imports here get loaded into supervisor's memory and persist
# in forked worker processes as stale code, preventing hot-reload.
# Workers import make_agent directly from ouroboros.agent.

__all__ = ['agent', 'tools', 'llm', 'memory', 'review', 'utils',
           'consciousness', 'debate', 'goals', 'group_evolution',
           'reflection_engine']

from pathlib import Path as _Path

__version__ = (_Path(__file__).resolve().parent.parent / 'VERSION').read_text(encoding='utf-8').strip()

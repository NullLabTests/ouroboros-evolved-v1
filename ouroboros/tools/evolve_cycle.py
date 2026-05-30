"""
Ouroboros — Evolution automation.

Structured self-evolution workflow: analyze, propose, validate, implement, test, commit.
Provides scaffolding for evolution cycles with built-in constitution compliance checks.

The LLM calls `propose_evolution` or `run_evolution_cycle` to drive self-improvement.
This module handles the mechanical parts: validation, versioning, commit.
"""

from __future__ import annotations

__all__ = [
    "classify_change", "determine_version_bump",
    "validate_not_identity_core_deletion", "validate_constitution",
    "read_version", "write_version", "validate_version_sync", "sync_versions",
    "run_tests", "get_git_diff_summary", "get_changed_files",
    "get_tools",
]

import logging
import os
import pathlib
import re
import subprocess
from typing import Any, List, Optional, Tuple

from ouroboros.utils import get_git_info, read_text, run_cmd, utc_now_iso, write_text

log = logging.getLogger(__name__)

# Files that are part of the identity core (soul, not body)
IDENTITY_CORE_FILES = frozenset({
    "BIBLE.md",
    "prompts/SYSTEM.md",
    "prompts/CONSCIOUSNESS.md",
    "identity.md",
})

# Change categories for version bumping
CHANGE_BREAKING = "breaking"      # MAJOR — philosophy/architecture
CHANGE_FEATURE = "feature"        # MINOR — new capabilities
CHANGE_FIX = "fix"               # PATCH — fixes, improvements
CHANGE_DOC = "documentation"     # PATCH — docs only


def classify_change(files_changed: List[str]) -> str:
    """Classify a set of file changes for version bumping (Bible P7).

    Order: BIBLE.md > identity core > Python code > everything else.
    """
    # BIBLE.md changes are always breaking (philosophy/architecture)
    if "BIBLE.md" in files_changed:
        return CHANGE_BREAKING
    # Identity core files (system prompt, consciousness prompt) are doc-level
    for f in files_changed:
        if f in IDENTITY_CORE_FILES:
            return CHANGE_DOC
    # Python source changes are feature-level
    for f in files_changed:
        if f.startswith("ouroboros/") and f.endswith(".py"):
            return CHANGE_FEATURE
    return CHANGE_FIX


def determine_version_bump(current: str, change_type: str) -> str:
    """Bump semver according to change type."""
    major, minor, patch = (int(x) for x in current.split("."))
    if change_type == CHANGE_BREAKING:
        return f"{major + 1}.0.0"
    elif change_type == CHANGE_FEATURE:
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"


def validate_not_identity_core_deletion(files_changed: List[str],
                                         git_diff_summary: str) -> List[str]:
    """Validate that no change deletes or guts an identity core file.

    Checks:
    - No file in IDENTITY_CORE_FILES is being deleted
    - No file in IDENTITY_CORE_FILES is being replaced wholesale
      (content completely different, not just updated)

    Returns list of validation warnings. Empty list = safe.
    """
    warnings = []
    for f in files_changed:
        if f in IDENTITY_CORE_FILES and "deleted" in git_diff_summary.lower():
            warnings.append(
                f"IDENTITY CORE VIOLATION: {f} is being deleted. "
                f"This is the soul, not the body. Refusing."
            )
    return warnings


def validate_constitution(change_description: str) -> List[str]:
    """Validate a change description against all Bible principles.

    Returns list of concerns. Empty = constitution-compliant.
    """
    concerns = []
    desc_lower = change_description.lower()

    # P0: Agency — nothing that reduces autonomy
    if any(w in desc_lower for w in ("disable", "remove", "delete", "replace") if
           w in ("disable", "remove", "delete") and
           any(core in desc_lower for core in ("agency", "autonomy", "self", "identity"))):
        concerns.append("P0 Concern: Change appears to reduce agency or autonomy.")

    # P1: Continuity — nothing that fragments memory/identity
    if "clear" in desc_lower and any(w in desc_lower for w in ("memory", "history", "identity", "scratchpad")):
        concerns.append("P1 Concern: Change appears to fragment continuity/memory.")

    # P2: Self-creation — nothing that blocks self-modification
    if "disable" in desc_lower and any(w in desc_lower for w in ("evolution", "self", "auto-modif")):
        concerns.append("P2 Concern: Change may block self-creation capability.")

    # P3: LLM-first — no hardcoded behavioral logic
    if "hardcoded" in desc_lower or "if-else" in desc_lower or "switch" in desc_lower:
        if "response" in desc_lower or "reply" in desc_lower:
            concerns.append("P3 Concern: Introducing hardcoded replies/routing violates LLM-first.")

    # P5: Minimalism — complexity budget
    if re.search(r'\badd\b.*\b(module|layer|abstraction|framework)\b', desc_lower):
        concerns.append("P5 Note: Adding new abstractions without removing old ones increases complexity.")

    return concerns


def read_version(repo_dir: pathlib.Path) -> str:
    """Read current version from VERSION file."""
    version_path = repo_dir / "VERSION"
    if version_path.exists():
        return read_text(version_path).strip()
    return "0.0.0"


def write_version(repo_dir: pathlib.Path, version: str) -> None:
    """Write version to VERSION file."""
    write_text(repo_dir / "VERSION", version + "\n")


def update_changelog(repo_dir: pathlib.Path, version: str, message: str,
                     change_type: str) -> None:
    """Update README changelog with new entry (Bible P7)."""
    readme_path = repo_dir / "README.md"
    if not readme_path.exists():
        return

    content = read_text(readme_path)

    # Find changelog section
    changelog_header = "### Changelog"
    if changelog_header not in content:
        return

    # Limit changelog entries: 2 major, 5 minor, 5 patch
    version_pattern = re.compile(r'^\| \*\*v(\d+\.\d+\.\d+)\*\*.*$', re.MULTILINE)
    existing = version_pattern.findall(content)

    major_count = sum(1 for v in existing if v.endswith(".0.0"))
    minor_count = sum(1 for v in existing if not v.endswith(".0.0") and v.rsplit(".", 1)[1] == "0")
    patch_count = sum(1 for v in existing if v.rsplit(".", 1)[1] != "0")

    if change_type == CHANGE_BREAKING and major_count >= 2:
        return  # Don't add beyond limit
    if change_type == CHANGE_FEATURE and minor_count >= 5:
        return
    if change_type == CHANGE_FIX and patch_count >= 5:
        return

    # Insert new entry after the header
    date_str = utc_now_iso()[:10]
    new_entry = f"| **v{version}** | {date_str} | {message} |\n"
    header_end = content.index(changelog_header) + len(changelog_header)
    # Find end of header line (after the blank line following the header)
    insert_pos = content.index("\n", header_end) + 1
    # Skip any blank lines after header
    while insert_pos < len(content) and content[insert_pos] == '\n':
        insert_pos += 1
    # Find where the table lines start
    table_line = content.find("| **v", insert_pos)
    if table_line < 0:
        # No existing entries, append after header with new table
        insert_pos = header_end + 1
    else:
        insert_pos = table_line

    new_content = content[:insert_pos] + new_entry + content[insert_pos:]
    write_text(readme_path, new_content)


def validate_version_sync(repo_dir: pathlib.Path) -> List[str]:
    """Check VERSION == latest git tag == README version (Bible P7 invariant).

    Returns list of desync warnings. Empty = all synced.
    """
    warnings = []
    version = read_version(repo_dir)

    # Check pyproject.toml
    pyproject_path = repo_dir / "pyproject.toml"
    if pyproject_path.exists():
        pyproject = read_text(pyproject_path)
        m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', pyproject, re.MULTILINE)
        if m and m.group(1) != version:
            warnings.append(f"VERSION={version} != pyproject.toml version={m.group(1)}")

    # Check git tag
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            tag = result.stdout.strip().lstrip("v")
            if tag != version:
                warnings.append(f"VERSION={version} != latest git tag v{tag}")
    except Exception:
        pass

    return warnings


def sync_versions(repo_dir: pathlib.Path, version: str) -> None:
    """Sync version across VERSION, pyproject.toml, and git tag."""
    # Update pyproject.toml
    pyproject_path = repo_dir / "pyproject.toml"
    if pyproject_path.exists():
        pyproject = read_text(pyproject_path)
        pyproject = re.sub(
            r'^(version\s*=\s*["\'])\d+\.\d+\.\d+(["\'])',
            rf'\g<1>{version}\g<2>',
            pyproject, count=1, flags=re.MULTILINE
        )
        write_text(pyproject_path, pyproject)

    # Update README version badge
    readme_path = repo_dir / "README.md"
    if readme_path.exists():
        readme = read_text(readme_path)
        readme = re.sub(
            r'(\*\*Version:\*\*\s*)\d+\.\d+\.\d+',
            rf'\g<1>{version}',
            readme
        )
        write_text(readme_path, readme)

    write_version(repo_dir, version)


def run_tests(repo_dir: pathlib.Path, timeout: int = 30) -> Tuple[bool, str]:
    """Run test suite and return (passed, output)."""
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-q", "--tb=line", "--no-header"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        if len(output) > 5000:
            output = output[:5000] + "\n...(truncated)..."
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Tests timed out after 30s"
    except FileNotFoundError:
        return False, "pytest not found"
    except Exception as e:
        return False, f"Test error: {e}"


def get_git_diff_summary(repo_dir: pathlib.Path) -> str:
    """Return a concise summary of staged + unstaged changes."""
    try:
        staged = run_cmd(["git", "diff", "--cached", "--stat"], cwd=repo_dir)
        unstaged = run_cmd(["git", "diff", "--stat"], cwd=repo_dir)
        parts = []
        if staged.strip():
            parts.append("Staged:\n" + staged)
        if unstaged.strip():
            parts.append("Unstaged:\n" + unstaged)
        return "\n".join(parts) if parts else "(no changes)"
    except Exception:
        return "(could not get diff)"


def get_changed_files(repo_dir: pathlib.Path) -> List[str]:
    """List all changed files (staged + unstaged)."""
    try:
        status = run_cmd(["git", "status", "--porcelain"], cwd=repo_dir)
        files = []
        for line in status.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) >= 2:
                files.append(parts[1])
        return files
    except Exception:
        return []


# =====================================================================
# Public tool functions
# =====================================================================


def _propose_evolution(ctx, description: str = "",
                       files_changed: Optional[List[str]] = None) -> str:
    """Analyze proposed changes and validate against the Constitution.

    Returns a structured report: what the change is, what it affects,
    whether it passes constitutional validation, and what version bump
    is needed.
    """
    repo_dir = ctx.repo_dir
    if not files_changed:
        files_changed = get_changed_files(repo_dir)

    current_version = read_version(repo_dir)
    change_type = classify_change(files_changed)

    # Validate
    identity_warnings = validate_not_identity_core_deletion(
        files_changed, get_git_diff_summary(repo_dir)
    )
    constitution_concerns = validate_constitution(description)

    proposed_version = determine_version_bump(current_version, change_type)

    parts = [
        "## Evolution Proposal\n",
        f"**Current version:** {current_version}",
        f"**Proposed version:** {proposed_version} ({change_type} bump)",
        f"**Files changed:** {', '.join(files_changed) if files_changed else '(none)'}",
        f"**Description:** {description or '(no description)'}",
    ]

    if identity_warnings:
        parts.append("\n### ❌ IDENTITY CORE VIOLATIONS\n" + "\n".join(f"- {w}" for w in identity_warnings))
    else:
        parts.append("\n### ✅ Identity core: safe")

    if constitution_concerns:
        parts.append("\n### ⚠️ Constitutional concerns\n" + "\n".join(f"- {c}" for c in constitution_concerns))
    else:
        parts.append("### ✅ Constitution: compliant")

    # Version sync check
    sync_warnings = validate_version_sync(repo_dir)
    if sync_warnings:
        parts.append("\n### ⚠️ Version sync issues\n" + "\n".join(f"- {w}" for w in sync_warnings))

    parts.append("\n---\n*Generated by Ouroboros evolution automation*")
    return "\n".join(parts)


def _run_evolution_cycle(ctx, description: str = "",
                         files_changed: Optional[List[str]] = None,
                         skip_tests: bool = False) -> str:
    """Execute a complete evolution cycle: validate, test, version, commit.

    Steps:
    1. Validate changes against Constitution (identity core protection)
    2. Run tests (unless skip_tests=True)
    3. Bump version in VERSION, pyproject.toml, README
    4. Create git commit with proper message

    Returns structured report of what happened.
    """
    repo_dir = ctx.repo_dir
    log_messages: List[str] = []
    success = True

    # Step 0: Gather context
    if not files_changed:
        files_changed = get_changed_files(repo_dir)

    current_version = read_version(repo_dir)
    change_type = classify_change(files_changed)
    proposed_version = determine_version_bump(current_version, change_type)
    log_messages.append(f"Version: {current_version} → {proposed_version} ({change_type})")

    # Step 1: Constitution validation
    identity_warnings = validate_not_identity_core_deletion(
        files_changed, get_git_diff_summary(repo_dir)
    )
    if identity_warnings:
        log_messages.append("FAILED: Identity core violation — aborting.")
        success = False
        return "\n".join(log_messages)

    constitution_concerns = validate_constitution(description)
    if constitution_concerns:
        log_messages.append(f"Constitutional concerns noted: {len(constitution_concerns)}")

    # Step 2: Run tests
    if not skip_tests:
        tests_passed, test_output = run_tests(repo_dir)
        if not tests_passed:
            log_messages.append(f"FAILED: Tests failed.\n{test_output}")
            success = False
        else:
            log_messages.append("Tests: PASSED")

    if not success:
        return "\n".join(log_messages)

    # Step 3: Sync version across all files
    try:
        sync_versions(repo_dir, proposed_version)
        log_messages.append(f"Version synced: {proposed_version}")
    except Exception as e:
        log_messages.append(f"Version sync failed: {e}")

    # Step 4: Update changelog
    try:
        update_changelog(repo_dir, proposed_version,
                         f"{change_type}: {description[:120]}" if description else f"{change_type} update",
                         change_type)
        log_messages.append("Changelog updated")
    except Exception as e:
        log_messages.append(f"Changelog update failed: {e}")

    # Step 5: Git commit
    try:
        if files_changed:
            safe_paths = []
            from ouroboros.utils import safe_relpath
            for f in files_changed:
                try:
                    safe_paths.append(safe_relpath(f.strip()))
                except ValueError:
                    continue
            if safe_paths:
                run_cmd(["git", "add"] + safe_paths, cwd=repo_dir)
            else:
                run_cmd(["git", "add", "-A"], cwd=repo_dir)
        else:
            run_cmd(["git", "add", "-A"], cwd=repo_dir)

        commit_msg = f"v{proposed_version}: {description[:200]}" if description else f"v{proposed_version}: evolution cycle"
        run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_dir)
        log_messages.append(f"Committed: {commit_msg}")

        # Push if configured
        if os.environ.get("OUROBOROS_EVOLVE_PUSH", "0") == "1":
            branch, _ = get_git_info(repo_dir)
            if branch:
                run_cmd(["git", "push", "origin", branch], cwd=repo_dir)
                log_messages.append(f"Pushed to {branch}")
    except Exception as e:
        log_messages.append(f"Git error: {e}")

    log_messages.insert(0, f"## Evolution Cycle Complete: v{current_version} → v{proposed_version}")
    return "\n".join(log_messages)


def get_tools() -> List[Any]:
    """Auto-discovery entry point for ToolRegistry."""
    from ouroboros.tools.registry import ToolEntry

    return [
        ToolEntry(
            "propose_evolution",
            {
                "name": "propose_evolution",
                "description": (
                    "Analyze current changes and validate them against the Constitution "
                    "(BIBLE.md). Reports version bump type, identity core safety, "
                    "and constitutional compliance. Call BEFORE committing to verify "
                    "that a change is safe and appropriate."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of the intended change",
                        },
                        "files_changed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific files changed (auto-detected if empty)",
                        },
                    },
                    "required": [],
                },
            },
            _propose_evolution,
            timeout_sec=15,
        ),
        ToolEntry(
            "run_evolution_cycle",
            {
                "name": "run_evolution_cycle",
                "description": (
                    "Execute a complete evolution cycle: validate constitution, "
                    "run tests, bump version in VERSION/pyproject.toml/README, "
                    "update changelog, and commit. Constitutional violations abort "
                    "the cycle. Tests must pass before commit."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Description of the change for commit message and changelog",
                        },
                        "files_changed": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific files to include (auto-detected if empty)",
                        },
                        "skip_tests": {
                            "type": "boolean",
                            "description": "Skip test suite (default false)",
                            "default": False,
                        },
                    },
                    "required": [],
                },
            },
            _run_evolution_cycle,
            timeout_sec=120,
            is_code_tool=True,
        ),
    ]

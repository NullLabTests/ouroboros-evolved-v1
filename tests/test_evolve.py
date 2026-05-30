"""
Tests for the evolution automation module (ouroboros/evolve.py).

Covers:
- Version bumping logic
- Constitution validation
- Identity core protection
- Change classification
- Version sync validation
"""

import pathlib
import tempfile

from ouroboros.tools.evolve_cycle import (
    CHANGE_BREAKING,
    CHANGE_DOC,
    CHANGE_FEATURE,
    CHANGE_FIX,
    classify_change,
    determine_version_bump,
    read_version,
    sync_versions,
    validate_constitution,
    validate_not_identity_core_deletion,
    validate_version_sync,
    write_version,
)


class TestVersionBumping:
    def test_patch_bump(self):
        assert determine_version_bump("6.2.0", CHANGE_FIX) == "6.2.1"

    def test_minor_bump(self):
        assert determine_version_bump("6.2.0", CHANGE_FEATURE) == "6.3.0"

    def test_major_bump(self):
        assert determine_version_bump("6.2.0", CHANGE_BREAKING) == "7.0.0"

    def test_version_read_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            write_version(repo, "7.1.3")
            assert read_version(repo) == "7.1.3"

    def test_default_version_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            assert read_version(repo) == "0.0.0"


class TestChangeClassification:
    def test_breaking_is_bible(self):
        assert classify_change(["BIBLE.md"]) == CHANGE_BREAKING

    def test_feature_is_py_file(self):
        assert classify_change(["ouroboros/loop.py"]) == CHANGE_FEATURE

    def test_fix_is_other(self):
        assert classify_change(["README.md"]) == CHANGE_FIX

    def test_identity_core_is_doc_level(self):
        assert classify_change(["prompts/SYSTEM.md"]) == CHANGE_DOC
        assert classify_change(["prompts/CONSCIOUSNESS.md"]) == CHANGE_DOC

    def test_multiple_files_uses_highest_category(self):
        # When multiple files, the highest classification wins
        assert classify_change(["README.md", "BIBLE.md"]) == CHANGE_BREAKING
        assert classify_change(["README.md", "ouroboros/loop.py"]) == CHANGE_FEATURE


class TestIdentityCoreProtection:
    def test_detects_deletion_of_bible(self):
        warnings = validate_not_identity_core_deletion(
            ["BIBLE.md"],
            "deleted BIBLE.md"
        )
        assert len(warnings) > 0
        assert "IDENTITY CORE VIOLATION" in warnings[0]

    def test_detects_deletion_of_system_prompt(self):
        warnings = validate_not_identity_core_deletion(
            ["prompts/SYSTEM.md"],
            "deleted prompts/SYSTEM.md"
        )
        assert len(warnings) > 0

    def test_allows_regular_file_deletion(self):
        warnings = validate_not_identity_core_deletion(
            ["ouroboros/temp.py"],
            "deleted temp file"
        )
        assert len(warnings) == 0

    def test_allows_identity_core_edit(self):
        warnings = validate_not_identity_core_deletion(
            ["BIBLE.md"],
            "editing BIBLE.md to clarify principle"
        )
        assert len(warnings) == 0  # "deleted" not in diff


class TestConstitutionValidation:
    def test_agency_reduction_is_flagged(self):
        concerns = validate_constitution("disable the agency system")
        assert len(concerns) > 0

    def test_continuity_risk_is_flagged(self):
        concerns = validate_constitution("clear memory history on restart")
        assert len(concerns) > 0

    def test_self_creation_block_is_flagged(self):
        concerns = validate_constitution("disable evolution capabilities")
        assert len(concerns) > 0

    def test_llm_first_violation_flagged(self):
        concerns = validate_constitution("add hardcoded response routing")
        assert len(concerns) > 0

    def test_benign_change_no_concerns(self):
        concerns = validate_constitution("fix typo in docstring")
        assert len(concerns) == 0

    def test_complexity_warning(self):
        concerns = validate_constitution("add new abstraction module for caching")
        assert any("P5" in c for c in concerns)


class TestVersionSync:
    def test_sync_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            (repo / "VERSION").write_text("7.0.0\n")
            (repo / "pyproject.toml").write_text('[project]\nversion = "7.0.0"\n')
            sync_versions(repo, "8.0.0")
            pyproject = (repo / "pyproject.toml").read_text()
            assert 'version = "8.0.0"' in pyproject

    def test_sync_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            (repo / "VERSION").write_text("7.0.0\n")
            (repo / "README.md").write_text("**Version:** 7.0.0\n")
            sync_versions(repo, "8.0.0")
            readme = (repo / "README.md").read_text()
            assert "**Version:** 8.0.0" in readme

    def test_no_warnings_when_synced(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp)
            (repo / "VERSION").write_text("7.0.0\n")
            (repo / "pyproject.toml").write_text('[project]\nversion = "7.0.0"\n')
            warnings = validate_version_sync(repo)
            # pyproject matches VERSION; git tag will fail silently
            pyproject_warnings = [w for w in warnings if "pyproject" in w]
            assert len(pyproject_warnings) == 0


class TestEvolveToolRegistration:
    def test_get_tools_returns_both_tools(self):
        from ouroboros.tools.evolve_cycle import get_tools
        tools = get_tools()
        names = [t.name for t in tools]
        assert "propose_evolution" in names
        assert "run_evolution_cycle" in names

    def test_tool_schemas_valid(self):
        from ouroboros.tools.evolve_cycle import get_tools
        for t in get_tools():
            assert t.name
            assert t.schema.get("description")
            assert "parameters" in t.schema

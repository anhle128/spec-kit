"""Consistency checks for the /speckit-analyzebatch command template.

Lock in the file-centric DRAFT -> respond -> GATE -> APPLY contract that
downstream tooling (Archon workflow, red-team-style apply parsers) depends on.
A failure here means the contract drifted and consumers will break silently.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "commands" / "analyzebatch.md"


class TestAnalyzeBatchTemplate:
    """Structural invariants of analyzebatch.md."""

    def test_template_exists(self):
        assert TEMPLATE.is_file(), f"{TEMPLATE} missing — analyzebatch template not installed"

    def test_template_non_empty(self):
        assert TEMPLATE.stat().st_size > 1000, "analyzebatch.md suspiciously small"

    def test_frontmatter_declares_apply_and_dry_run_flags(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        first = content.split("---", 2)
        assert len(first) >= 3, "analyzebatch.md must have YAML frontmatter"
        frontmatter = first[1]
        assert "--apply" in frontmatter
        assert "--dry-run" in frontmatter
        assert "--allow-historical-edits" in frontmatter

    def test_uses_check_prerequisites_with_tasks(self):
        """Analyze MUST require tasks.md (it analyzes spec/plan/tasks together)."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "--require-tasks" in content
        assert "--include-tasks" in content

    def test_lifecycle_markers_present(self):
        """DRAFT -> APPLY lifecycle is observable via Status: PENDING / ARCHIVED."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "Status: PENDING" in content
        assert "Status: ARCHIVED" in content

    def test_findings_filename_pattern(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "analyze-findings-<YYYY-MM-DD>" in content
        assert "analyze-findings-applied-<timestamp>.md" in content

    def test_six_analysis_categories_documented(self):
        """Same six categories as /speckit-analyze — wire format consumers depend on."""
        content = TEMPLATE.read_text(encoding="utf-8").lower()
        for category in (
            "duplication",
            "ambiguity",
            "underspecification",
            "constitution",
            "coverage",
            "inconsistency",
        ):
            assert category in content, f"category '{category}' missing from analyzebatch.md"

    def test_four_severity_levels_documented(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            assert sev in content, f"severity '{sev}' missing"

    def test_five_resolution_categories_documented(self):
        """Mirror of red-team-apply categories — apply parser keys off these names."""
        content = TEMPLATE.read_text(encoding="utf-8")
        for cat in ("spec-fix", "new-OQ", "accepted-risk", "out-of-scope", "skipped"):
            assert cat in content, f"resolution category '{cat}' missing"

    def test_literal_substring_contract_present(self):
        """The apply-time deterministic-replace contract MUST be spelled out."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "verbatim substring" in content.lower()
        assert "grep -c -F" in content
        assert "Before-snippet not found" in content

    def test_atomic_write_cadence_present(self):
        """Apply must load each file once, edit in-memory, then write atomically."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "in-memory" in content.lower()
        assert "atomic" in content.lower()

    def test_skills_compatible_no_dot_notation_speckit_refs(self):
        """Skills-mode integrations forbid /speckit. (dot) refs in installed SKILL.md.

        Mirrors the assertion in tests/integrations/test_integration_base_skills.py
        ::test_command_refs_use_hyphen_separator. Catch drift at template level
        so we don't have to wait for the per-integration suite.
        """
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "/speckit." not in content, (
            "analyzebatch.md must not contain /speckit. (dot) command refs; "
            "skills-mode agents require /speckit-<name> (hyphen) form."
        )

    def test_hooks_reuse_analyze_namespace(self):
        """before_analyze / after_analyze hooks (NOT before_analyzebatch).

        Look for actual hook key usage (`hooks.before_analyzebatch`), not bare
        substring — the contract is "don't fork the namespace into a new key",
        not "never mention the word".
        """
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "hooks.before_analyze" in content
        assert "hooks.after_analyze" in content
        assert "hooks.before_analyzebatch" not in content
        assert "hooks.after_analyzebatch" not in content


class TestAnalyzeBatchVsAnalyze:
    """Cross-template invariants: analyze.md and analyzebatch.md must stay aligned."""

    ANALYZE = REPO_ROOT / "templates" / "commands" / "analyze.md"

    def test_analyze_template_still_exists(self):
        """The read-only /analyze command must remain alongside /analyzebatch."""
        assert self.ANALYZE.is_file(), "analyze.md disappeared — /analyzebatch was meant to coexist, not replace"

    def test_both_templates_share_taxonomy_terms(self):
        analyze = self.ANALYZE.read_text(encoding="utf-8").lower()
        batch = TEMPLATE.read_text(encoding="utf-8").lower()
        for term in ("duplication", "ambiguity", "underspecification", "coverage"):
            assert term in analyze
            assert term in batch

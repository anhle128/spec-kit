"""Consistency checks for the /speckit-clarifybatch command template.

Lock in the batch clarification contract, especially the repo-first rule:
questions about existing behavior must be answered from source evidence when
the repository already determines the behavior.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = REPO_ROOT / "templates" / "commands" / "clarifybatch.md"


class TestClarifyBatchTemplate:
    """Structural invariants of clarifybatch.md."""

    def test_template_exists(self):
        assert TEMPLATE.is_file(), f"{TEMPLATE} missing - clarifybatch template not installed"

    def test_template_non_empty(self):
        assert TEMPLATE.stat().st_size > 1000, "clarifybatch.md suspiciously small"

    def test_frontmatter_declares_apply_and_turn_flags(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        first = content.split("---", 2)
        assert len(first) >= 3, "clarifybatch.md must have YAML frontmatter"
        frontmatter = first[1]
        assert "--apply" in frontmatter
        assert "--turn" in frontmatter

    def test_repo_first_source_of_truth_gate_present(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "repo-first source-of-truth gate" in content
        assert "existing behavior" in content.lower()
        assert "If a question can be answered by exploring the codebase" in content
        assert "Only ask the user for unresolved product/policy decisions or migration decisions" in content

    def test_source_derived_answers_have_file_contract(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "## Answered From Source" in content
        assert "### S1. <question text>" in content
        assert "**Category:** <one of the 10 taxonomy categories above>" in content
        assert "**Answer:** <concise answer derived from source>" in content
        assert "**Evidence:** <path:line[, path:line...]>" in content
        assert "do not need editing" in content

    def test_source_answers_apply_without_user_answer(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "For each `## Answered From Source` entry (`### S<N>.`) extract" in content
        assert "already resolved answers" in content
        assert "do not require a `Your Answer:` line" in content
        assert "missing evidence" in content
        assert "(source: <evidence>)" in content

    def test_source_answers_do_not_consume_question_quota(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "Source-derived answers do not consume `MAX_QUESTIONS`" in content
        assert "source-derived answers do not count against the quota" in content

    def test_draft_phase_still_does_not_modify_spec(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "Do **NOT** modify `spec.md`" in content
        assert "Do **NOT** continue to APPLY in the same run" in content
        assert "In DRAFT phase the spec is unchanged" in content

    def test_apply_reports_source_user_and_skipped_counts(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "Number of source-derived answers applied" in content
        assert "number of user answers applied" in content
        assert "number skipped" in content

    def test_skills_compatible_no_dot_notation_speckit_refs(self):
        """Skills-mode integrations forbid /speckit. (dot) refs in installed SKILL.md."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "/speckit." not in content, (
            "clarifybatch.md must not contain /speckit. (dot) command refs; "
            "skills-mode agents require /speckit-<name> (hyphen) form."
        )

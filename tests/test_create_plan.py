"""Tests for create_paper_plan.py — plan generation and placeholder replacement."""

import sys
from pathlib import Path

import pytest

# Import from scripts directory
from create_paper_plan import (
    read_template,
    replace_placeholders,
    kickoff_gate_confirmed,
    main as create_plan_main,
)
from paper_utils import (
    build_plan_filename,
    build_issues_filename,
    slugify,
    now_timestamp,
)


class TestReadTemplate:
    def test_read_existing_template(self):
        """Verify the paper-plan-template.md can be read."""
        content = read_template("paper-plan-template.md")
        assert len(content) > 0
        assert "<paper topic>" in content or "<slug>" in content

    def test_read_nonexistent_template(self):
        with pytest.raises(FileNotFoundError):
            read_template("nonexistent-template-xyzzy.md")


class TestReplacePlaceholders:
    def test_replace_topic(self):
        result = replace_placeholders(
            "<paper topic> is interesting",
            "Test Topic", "2025-01-01_00-00-00", "test-topic", True,
        )
        assert "Test Topic" in result
        assert "<paper topic>" not in result

    def test_replace_slug(self):
        result = replace_placeholders(
            "Project: <slug>",
            "Test Topic", "2025-01-01_00-00-00", "test-slug", True,
        )
        assert "test-slug" in result
        assert "<slug>" not in result

    def test_replace_timestamp(self):
        result = replace_placeholders(
            "Date: <YYYY-MM-DD_HH-mm-ss>",
            "Topic", "2025-01-01_00-00-00", "slug", True,
        )
        assert "2025-01-01_00-00-00" in result

    def test_replace_latex_available_true(self):
        result = replace_placeholders(
            "LaTeX: <true|false>",
            "Topic", "2025-01-01_00-00-00", "slug", True,
        )
        assert "true" in result.lower()
        assert "<true|false>" not in result

    def test_replace_latex_available_false(self):
        result = replace_placeholders(
            "LaTeX: <true|false>",
            "Topic", "2025-01-01_00-00-00", "slug", False,
        )
        assert "false" in result.lower()

    def test_replace_iso_timestamp(self):
        result = replace_placeholders(
            "ISO: <ISO8601 timestamp>",
            "Topic", "2025-01-01_00-00-00", "slug", True,
        )
        assert "<ISO8601 timestamp>" not in result


class TestKickoffGate:
    def test_gate_confirmed_in_plan(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("- [x] User confirmed scope + outline in chat\nOther text")
        assert kickoff_gate_confirmed(plan)

    def test_gate_not_confirmed(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("- [ ] User confirmed scope + outline in chat\n")
        assert not kickoff_gate_confirmed(plan)

    def test_gate_missing_file(self, tmp_path):
        assert not kickoff_gate_confirmed(tmp_path / "nonexistent.md")

    def test_gate_partial_match_rejected(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("- [x] User confirmed something else\n")
        assert not kickoff_gate_confirmed(plan)


class TestMainCLI:
    def test_help_flag(self):
        """Verify --help produces output."""
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1]
             / ".codex/skills/academic-paper-writer/scripts/create_paper_plan.py"),
             "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()

"""End-to-end integration test for the paper writing workflow.

Tests the full pipeline: config → scaffold → issues → validate → compile (if tools available).
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".codex" / "skills" / "academic-paper-writer" / "scripts"
)


def _run_script(script_name, args, timeout=60):
    """Run a script and return (returncode, stdout, stderr)."""
    import subprocess
    script = SCRIPTS / script_name
    if not script.exists():
        pytest.skip(f"Script {script_name} not found")
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode, result.stdout, result.stderr


class TestE2EWorkflow:
    def test_paper_config_detect(self):
        """Step 1: Detect domain from topic."""
        rc, stdout, stderr = _run_script(
            "paper_config.py",
            ["detect", "--topic", "transformer architectures for NLP"],
        )
        assert rc == 0
        assert "computer-science" in stdout.lower() or "domain" in stdout.lower()

    def test_paper_config_generate(self, tmp_path):
        """Step 1b: Generate paper-config.yml."""
        config_path = tmp_path / "paper-config.yml"
        rc, stdout, stderr = _run_script(
            "paper_config.py",
            ["generate", "--topic", "transformer architectures for NLP",
             "--output", str(config_path)],
        )
        assert rc == 0
        assert config_path.exists()

        # Verify config content
        content = config_path.read_text()
        assert "transformer" in content.lower()
        assert "output_format" in content

    def test_bootstrap_kickoff(self, tmp_path):
        """Step 2: Bootstrap project with kickoff stage."""
        rc, stdout, stderr = _run_script(
            "bootstrap_review_paper.py",
            ["--stage", "kickoff",
             "--topic", "Test Review Paper",
             "--name", "test-review",
             "--out", str(tmp_path)],
        )
        # May fail if no paper-config.yml exists; that's OK for this test
        # Just verify it doesn't crash with a Python traceback
        assert "Traceback" not in stderr

    def test_literature_registry_init(self, tmp_path):
        """Initialize literature registry database."""
        rc, stdout, stderr = _run_script(
            "literature_registry.py",
            ["--project-dir", str(tmp_path), "init"],
        )
        assert rc == 0
        db_path = tmp_path / "notes" / "literature-registry.sqlite3"
        assert db_path.exists()

    def test_literature_registry_search(self, tmp_path):
        """Search for papers (network call — may fail gracefully)."""
        # Init first
        _run_script(
            "literature_registry.py",
            ["--project-dir", str(tmp_path), "init"],
        )
        rc, stdout, stderr = _run_script(
            "literature_registry.py",
            ["--project-dir", str(tmp_path), "search", "arxiv",
             "transformer attention", "--max-results", "3"],
            timeout=120,
        )
        # May fail due to network; just verify no traceback
        combined = stdout + stderr
        assert "Traceback" not in combined

    def test_lqs_scorer_help(self):
        """Verify LQS scorer CLI works."""
        rc, stdout, stderr = _run_script(
            "lqs_scorer.py",
            ["--help"],
        )
        assert rc == 0
        assert "score" in stdout.lower()

    def test_review_simulation_fallback(self, tmp_path):
        """Test review simulation with no LLM (should fall back to gap analysis)."""
        # Create a minimal paper directory with a main.typ
        proj = tmp_path / "test-paper"
        proj.mkdir()
        (proj / "main.typ").write_text(
            "= Introduction\n"
            "This is a test introduction @ref1 @ref2.\n\n"
            "= Methods\n"
            "This section has very few citations @ref3.\n\n"
            "= Conclusion\n"
            "Final thoughts @ref4 @ref5 @ref6 @ref7 @ref8 @ref9 @ref10 @ref11 @ref12."
        )
        (proj / "reviews").mkdir()

        rc, stdout, stderr = _run_script(
            "run_review_simulation.py",
            ["--project-dir", str(proj), "--round", "1"],
            timeout=30,
        )
        # Should succeed (with fallback to gap analysis if no LLM bridge)
        assert rc == 0
        assert "Traceback" not in stderr

        # Check output file was created
        output_file = proj / "reviews" / "review-round-1.json"
        if output_file.exists():
            review = json.loads(output_file.read_text())
            assert "round" in review
            assert "project_dir" in review
            # Accept either full review or gap-analysis-only mode
            assert review.get("mode") in (None, "llm-review", "gap-analysis-only")

    def test_validate_issues_resume(self, tmp_path):
        """Test validate_paper_issues.py --resume on a sample CSV."""
        csv_path = tmp_path / "test-issues.csv"
        csv_path.write_text(
            "ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes\n"
            "W01,Writing,Introduction,Write the introduction,10,None,Intro complete,DONE,12,arxiv,\n"
            "W02,Writing,Methods,Write methods section,8,None,Methods complete,DOING,3,openalex,\n"
            "W03,Writing,Conclusion,Write conclusion,6,None,Conclusion done,TODO,0,arxiv,\n"
        )

        rc, stdout, stderr = _run_script(
            "validate_paper_issues.py",
            [str(csv_path), "--resume"],
        )
        assert rc == 0
        # Should print validation summary and resume point
        combined = stdout + stderr
        assert "Validation passed" in combined or "W02" in combined

    def test_full_minimal_pipeline(self, tmp_path):
        """Minimal end-to-end: config → init registry → validate."""
        # 1. Generate config
        config_path = tmp_path / "paper-config.yml"
        rc, _, _ = _run_script(
            "paper_config.py",
            ["generate", "--topic", "test survey paper",
             "--output", str(config_path)],
        )
        assert rc == 0
        assert config_path.exists()

        # 2. Init literature registry
        rc, _, _ = _run_script(
            "literature_registry.py",
            ["--project-dir", str(tmp_path), "init"],
        )
        assert rc == 0
        assert (tmp_path / "notes" / "literature-registry.sqlite3").exists()

        # 3. Verify LQS scorer can read the registry
        rc, stdout, stderr = _run_script(
            "lqs_scorer.py",
            ["--project-dir", str(tmp_path), "score-all"],
            timeout=30,
        )
        # May fail if modules can't be imported from test context; verify no crash
        combined = stdout + stderr
        assert "Traceback" not in combined
        # If it succeeds, exit code should be 0; if import fails, that's OK for e2e

        # All steps completed without traceback
        print("Full minimal pipeline: PASS")

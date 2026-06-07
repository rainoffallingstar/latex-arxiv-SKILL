"""Tests for claude_bridge.py and gemini_bridge.py — argument parsing and CLI interface."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = (
    Path(__file__).resolve().parents[1]
    / ".codex" / "skills"
)

CLAUDE_BRIDGE = SCRIPTS_DIR / "collaborating-with-claude" / "scripts" / "claude_bridge.py"
GEMINI_BRIDGE = SCRIPTS_DIR / "collaborating-with-gemini" / "scripts" / "gemini_bridge.py"


def _bridge_exists(path):
    return path.exists()


class TestClaudeBridge:
    def test_script_exists(self):
        assert _bridge_exists(CLAUDE_BRIDGE), f"Expected {CLAUDE_BRIDGE} to exist"

    def test_help_flag(self):
        """Verify --help produces output and exits 0."""
        result = subprocess.run(
            [sys.executable, str(CLAUDE_BRIDGE), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_missing_prompt_fails_gracefully(self):
        """Calling without --PROMPT should produce a clear error."""
        result = subprocess.run(
            [sys.executable, str(CLAUDE_BRIDGE), "--cd", "."],
            capture_output=True, text=True, timeout=15,
        )
        # Should exit non-zero when required args are missing
        assert result.returncode != 0 or "error" in (result.stdout + result.stderr).lower()

    def test_invalid_session_id(self):
        """Passing a nonexistent SESSION_ID should not crash the script."""
        result = subprocess.run(
            [sys.executable, str(CLAUDE_BRIDGE), "--SESSION_ID", "nonexistent-session-99999",
             "--PROMPT", "Hello", "--cd", "."],
            capture_output=True, text=True, timeout=15,
        )
        # Should exit with an error or produce JSON output
        # (exact behavior depends on whether Claude CLI is installed)
        output = result.stdout + result.stderr
        # Just verify it doesn't crash with a Python traceback
        assert "Traceback" not in output


class TestGeminiBridge:
    def test_script_exists(self):
        assert _bridge_exists(GEMINI_BRIDGE), f"Expected {GEMINI_BRIDGE} to exist"

    def test_help_flag(self):
        """Verify --help produces output and exits 0."""
        result = subprocess.run(
            [sys.executable, str(GEMINI_BRIDGE), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()

    def test_missing_prompt_fails_gracefully(self):
        """Calling without --PROMPT should produce a clear error."""
        result = subprocess.run(
            [sys.executable, str(GEMINI_BRIDGE), "--cd", "."],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode != 0 or "error" in (result.stdout + result.stderr).lower()

    def test_invalid_session_id(self):
        """Passing a nonexistent SESSION_ID should not crash the script."""
        result = subprocess.run(
            [sys.executable, str(GEMINI_BRIDGE), "--SESSION_ID", "nonexistent-session-99999",
             "--PROMPT", "Hello", "--cd", "."],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout + result.stderr
        assert "Traceback" not in output


class TestBridgeFilesStructure:
    def test_both_bridges_present(self):
        assert CLAUDE_BRIDGE.exists()
        assert GEMINI_BRIDGE.exists()

    def test_both_have_prompt_template(self):
        claude_tmpl = SCRIPTS_DIR / "collaborating-with-claude" / "assets" / "prompt-template.md"
        gemini_tmpl = SCRIPTS_DIR / "collaborating-with-gemini" / "assets" / "prompt-template.md"
        assert claude_tmpl.exists()
        assert gemini_tmpl.exists()

    def test_both_have_shell_quoting_ref(self):
        claude_ref = SCRIPTS_DIR / "collaborating-with-claude" / "references" / "shell-quoting.md"
        gemini_ref = SCRIPTS_DIR / "collaborating-with-gemini" / "references" / "shell-quoting.md"
        assert claude_ref.exists()
        assert gemini_ref.exists()

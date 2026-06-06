import sys
from pathlib import Path

import pytest

SKILL_SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / ".codex" / "skills" / "academic-paper-writer" / "scripts"
)

sys.path.insert(0, str(SKILL_SCRIPTS))


@pytest.fixture
def tmp_project_dir(tmp_path):
    """Create a temporary project directory with standard subdirectories."""
    project = tmp_path / "test-paper"
    project.mkdir()
    (project / "plan").mkdir()
    (project / "issues").mkdir()
    (project / "notes").mkdir()
    return project

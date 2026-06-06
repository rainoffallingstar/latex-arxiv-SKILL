"""Tests for validate_paper_issues.py — CSV schema validation."""

import sys
import tempfile
from pathlib import Path

from validate_paper_issues import main as validate_main
from validate_paper_issues import REQUIRED_COLUMNS, ALLOWED_SOURCES


VALID_CSV_CONTENT = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
R1,Research,Literature snapshot,Discover 10-20 key papers,0,N/A,Snapshot created,TODO,0,,First research task
W1,Writing,Introduction,Write introduction section,8,conceptual-diagram,Section complete,TODO,0,arxiv,Main intro
Q1,QA,Citation verification,Verify all citations,0,N/A,All verified,TODO,0,,"Final QA"
"""

INVALID_HEADER = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Notes
R1,Research,Test,Desc,0,N/A,Accept,TODO,0,Test
"""

DUPLICATE_ID = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
R1,Research,Test1,Desc1,0,N/A,Accept,TODO,0,,
R1,Writing,Test2,Desc2,0,N/A,Accept,TODO,0,,
"""

EMPTY_REQUIRED = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
,Research,Test,Desc,0,N/A,Accept,TODO,0,,
"""

INVALID_STATUS = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
R1,Research,Test,Desc,0,N/A,Accept,INVALID,0,,
"""

INVALID_PHASE = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
R1,InvalidPhase,Test,Desc,0,N/A,Accept,TODO,0,,
"""

UNKNOWN_SOURCE = """ID,Phase,Title,Description,Target_Citations,Visualization,Acceptance,Status,Verified_Citations,Sources,Notes
R1,Research,Test,Desc,0,N/A,Accept,TODO,0,google-scholar,
"""


def _write_csv(content: str) -> Path:
    tmp = Path(tempfile.mktemp(suffix=".csv"))
    tmp.write_text(content)
    return tmp


def _run_validator(csv_path: Path) -> int:
    """Run the validator as it reads from sys.argv."""
    old_argv = sys.argv[:]
    sys.argv = ["validate_paper_issues.py", str(csv_path)]
    try:
        return validate_main()
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = old_argv


class TestCSVValidation:
    def test_valid_csv_passes(self):
        csv_path = _write_csv(VALID_CSV_CONTENT)
        assert _run_validator(csv_path) == 0

    def test_invalid_header_fails(self):
        csv_path = _write_csv(INVALID_HEADER)
        assert _run_validator(csv_path) == 1

    def test_duplicate_id_fails(self):
        csv_path = _write_csv(DUPLICATE_ID)
        assert _run_validator(csv_path) == 1

    def test_empty_required_field_fails(self):
        csv_path = _write_csv(EMPTY_REQUIRED)
        assert _run_validator(csv_path) == 1

    def test_invalid_status_fails(self):
        csv_path = _write_csv(INVALID_STATUS)
        assert _run_validator(csv_path) == 1

    def test_invalid_phase_fails(self):
        csv_path = _write_csv(INVALID_PHASE)
        assert _run_validator(csv_path) == 1

    def test_unknown_source_warns(self):
        csv_path = _write_csv(UNKNOWN_SOURCE)
        assert _run_validator(csv_path) == 0


class TestAllowedValues:
    def test_required_columns_includes_sources(self):
        assert "Sources" in REQUIRED_COLUMNS

    def test_required_columns_count(self):
        assert len(REQUIRED_COLUMNS) == 11

    def test_valid_sources(self):
        assert "arxiv" in ALLOWED_SOURCES
        assert "pubmed" in ALLOWED_SOURCES
        assert "openalex" in ALLOWED_SOURCES
        assert "europepmc" in ALLOWED_SOURCES
        assert "biorxiv" in ALLOWED_SOURCES

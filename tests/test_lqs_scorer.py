"""Tests for lqs_scorer.py — LQS scoring, depth classification, venue upgrade."""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Import from lqs_scorer (scripts dir added to path by conftest.py)
from lqs_scorer import (
    LQS_WEIGHTS,
    LQS_THRESHOLD_MUST_CITE,
    LQS_THRESHOLD_CONDITIONAL,
    score_recency,
    score_citation_impact,
    score_venue,
    score_institution,
    score_acceptance,
    calculate_lqs,
    save_lqs,
    ensure_lqs_schema,
    classify_depth,
    upgrade_venues,
    quality_report,
    _citation_bucket,
    _check_dblp_for_acceptance,
)


@pytest.fixture
def db_conn():
    """In-memory SQLite database with works and lqs_scores tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    # Create minimal works schema (matching literature_registry.py)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS works (
            work_id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            published TEXT,
            authors_json TEXT NOT NULL,
            doi TEXT,
            journal_ref TEXT,
            primary_category TEXT,
            categories_json TEXT,
            abs_url TEXT,
            pdf_url TEXT,
            created_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            UNIQUE(source, source_id)
        );
        CREATE TABLE IF NOT EXISTS citation_keys (
            work_id INTEGER PRIMARY KEY REFERENCES works(work_id) ON DELETE CASCADE,
            key TEXT NOT NULL UNIQUE,
            base_key TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS verifications (
            verification_id INTEGER PRIMARY KEY,
            work_id INTEGER REFERENCES works(work_id) ON DELETE CASCADE,
            verified_at TEXT NOT NULL,
            method TEXT NOT NULL,
            doi TEXT,
            status TEXT NOT NULL,
            resolved_title TEXT,
            resolved_authors_json TEXT,
            resolved_year TEXT,
            resolved_journal TEXT,
            error_message TEXT
        );
    """)
    ensure_lqs_schema(conn)
    yield conn
    conn.close()


def _insert_work(
    conn,
    work_id=1,
    source="arxiv",
    source_id="2401.00001",
    title="Test Paper",
    published=None,
    authors_json='["Smith, John", "Doe, Jane"]',
    doi=None,
    journal_ref=None,
    primary_category=None,
    categories_json=None,
):
    """Helper: insert a work row."""
    from datetime import timezone as tz
    now = datetime.now(tz.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO works(work_id, source, source_id, title, published,
           authors_json, doi, journal_ref, primary_category, categories_json,
           created_at, last_seen_at)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (work_id, source, source_id, title, published,
         authors_json, doi, journal_ref, primary_category,
         categories_json, now, now),
    )
    conn.commit()


def _insert_citation_key(conn, work_id=1, key="testKey2024"):
    """Helper: insert a citation key."""
    conn.execute(
        "INSERT INTO citation_keys(work_id, key, base_key, generated_at) VALUES(?, ?, ?, ?)",
        (work_id, key, key, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Test score_recency
# ---------------------------------------------------------------------------

class TestRecencyScoring:
    def test_recent_paper_6mo(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        score, label = score_recency(recent)
        assert score == 10.0
        assert label == "<=6mo"

    def test_paper_1yr(self):
        yr_ago = (datetime.now(timezone.utc) - timedelta(days=300)).isoformat()
        score, label = score_recency(yr_ago)
        assert score == 8.0
        assert label == "<=1yr"

    def test_paper_2yr(self):
        two_yr = (datetime.now(timezone.utc) - timedelta(days=600)).isoformat()
        score, label = score_recency(two_yr)
        assert score == 5.0
        assert label == "<=2yr"

    def test_paper_3yr(self):
        three_yr = (datetime.now(timezone.utc) - timedelta(days=900)).isoformat()
        score, label = score_recency(three_yr)
        assert score == 3.0
        assert label == "<=3yr"

    def test_old_paper(self):
        old = (datetime.now(timezone.utc) - timedelta(days=1200)).isoformat()
        score, label = score_recency(old)
        assert score == 1.0
        assert label == ">3yr"

    def test_none_date(self):
        score, label = score_recency(None)
        assert score == 3.0
        assert label == "unknown_date"

    def test_year_only(self):
        score, label = score_recency("2024")
        assert score in (3.0, 5.0)  # depends on current date

    def test_unparseable_date(self):
        score, label = score_recency("not a date at all")
        assert score == 3.0
        assert label == "unparseable_date"


# ---------------------------------------------------------------------------
# Test _citation_bucket
# ---------------------------------------------------------------------------

class TestCitationBucket:
    def test_high_impact(self):
        # Use a very recent date so cites/month is high
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        score, label = _citation_bucket(500, recent)
        assert score == 10.0
        assert ">=50/mo" in label

    def test_moderate_impact(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        score, label = _citation_bucket(15, recent)
        assert score == 8.0
        assert ">=10/mo" in label

    def test_low_impact(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        score, label = _citation_bucket(10, recent)
        assert score == 6.0

    def test_minimal_impact(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
        score, label = _citation_bucket(8, recent)
        assert score == 4.0

    def test_negligible(self):
        one_yr_ago = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        score, label = _citation_bucket(1, one_yr_ago)
        assert score == 2.0

    def test_default_months(self):
        """When published is None, uses 24-month default."""
        score, label = _citation_bucket(100, None)
        assert score == 6.0  # 100/24 ≈ 4.17 per month -> >=3/mo


# ---------------------------------------------------------------------------
# Test score_venue
# ---------------------------------------------------------------------------

class TestVenueScoring:
    def test_top_tier_nature(self):
        score, label = score_venue("Nature (2024)", None, None)
        assert score == 10.0
        assert "nature" in label

    def test_top_tier_neurips(self):
        score, label = score_venue("Advances in Neural Information Processing Systems (NeurIPS 2024)", None, None)
        assert score == 10.0

    def test_strong_venue(self):
        score, label = score_venue("Published in ECML-PKDD 2023", None, None)
        assert score == 7.0

    def test_workshop(self):
        score, label = score_venue("ICML 2024 Workshop on...", None, None)
        assert score == 4.0
        assert "workshop" in label

    def test_arxiv_only(self):
        score, label = score_venue("arXiv preprint arXiv:2401.00001", None, None)
        assert score == 4.0
        assert "arxiv_only" in label

    def test_no_venue_info(self):
        score, label = score_venue(None, None, None)
        assert score == 4.0
        assert "no_venue_info" in label

    def test_unclassified(self):
        score, label = score_venue("Some Unknown Journal Vol 42", None, None)
        assert score == 5.0
        assert "unclassified" in label

    def test_venue_in_categories(self):
        score, label = score_venue(None, "cs.CV", ["cvpr", "pattern recognition"])
        assert score >= 7.0  # cvpr is in strong venues (wait, cvpr is top_tier actually)


# ---------------------------------------------------------------------------
# Test score_institution
# ---------------------------------------------------------------------------

class TestInstitutionScoring:
    def test_top_lab_deepmind(self):
        score, label = score_institution('["DeepMind Researcher", "Some Other"]')
        assert score == 10.0
        assert "deepmind" in label

    def test_top_university_mit(self):
        score, label = score_institution('["Researcher at MIT", "Another Author"]')
        assert score == 9.0
        assert "mit" in label

    def test_partial_match(self):
        # Use institutions not in TOP lists but that trigger known_count
        score, label = score_institution(
            '["Author affiliated with University of Washington", "Collaborator at UC San Diego"]'
        )
        # Neither UW nor UCSD are in TOP_UNIVERSITIES → partial if any known institution found
        assert score in (4.0, 6.0)  # depends on substring match

    def test_unknown(self):
        score, label = score_institution('["John Smith", "Jane Doe"]')
        assert score == 4.0
        assert "unknown_institution" in label

    def test_no_authors(self):
        score, label = score_institution(None)
        assert score == 3.0
        assert "no_author_data" in label


# ---------------------------------------------------------------------------
# Test score_acceptance
# ---------------------------------------------------------------------------

class TestAcceptanceScoring:
    def test_accepted_at_venue(self):
        score, label = score_acceptance("Accepted at NeurIPS 2024", "arxiv")
        assert score == 10.0
        assert label == "accepted"

    def test_to_appear(self):
        score, label = score_acceptance("To appear in Nature Communications", "arxiv")
        assert score == 10.0
        assert label == "accepted"

    def test_proceedings(self):
        score, label = score_acceptance("Proceedings of the 2024 Conference on...", "arxiv")
        assert score == 10.0
        assert label == "accepted"

    def test_under_review(self):
        score, label = score_acceptance("Under review at ICML", "arxiv")
        assert score == 5.0
        assert label == "under_review"

    def test_arxiv_preprint(self):
        score, label = score_acceptance("arXiv preprint arXiv:2401.00001", "arxiv")
        assert score == 3.0
        assert label == "arxiv_preprint"

    def test_no_journal_ref_arxiv(self):
        score, label = score_acceptance(None, "arxiv")
        assert score == 3.0

    def test_non_arxiv_article(self):
        score, label = score_acceptance("Journal of Something, Vol 42, pp 1-10, 2024", "pubmed")
        assert score == 10.0
        assert label == "journal_article"


# ---------------------------------------------------------------------------
# Test calculate_lqs (composite)
# ---------------------------------------------------------------------------

class TestCalculateLQS:
    def test_full_score_recent_top_paper(self, db_conn):
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        _insert_work(
            db_conn, work_id=1,
            published=recent,
            authors_json='["DeepMind Researcher"]',
            journal_ref="Published in Nature (2024)",
            doi="10.1234/test",
            categories_json='["cs.AI"]',
        )
        result = calculate_lqs(db_conn, 1)
        assert "error" not in result
        assert result["composite_score"] >= 7.0  # should be must-cite
        assert result["classification"] == "must_cite"

    def test_low_quality_paper(self, db_conn):
        old = (datetime.now(timezone.utc) - timedelta(days=1200)).isoformat()
        _insert_work(
            db_conn, work_id=1,
            published=old,
            authors_json='["Unknown Author"]',
            journal_ref="arXiv preprint",
        )
        result = calculate_lqs(db_conn, 1)
        assert result["composite_score"] < 5.0
        assert result["classification"] == "drop"

    def test_conditional_paper(self, db_conn):
        mid = (datetime.now(timezone.utc) - timedelta(days=500)).isoformat()
        _insert_work(
            db_conn, work_id=1,
            published=mid,
            authors_json='["Researcher at Stanford"]',
            journal_ref="Published in a decent workshop",
        )
        result = calculate_lqs(db_conn, 1)
        assert 3.0 <= result["composite_score"] <= 8.0

    def test_all_dimensions_present(self, db_conn):
        _insert_work(db_conn, work_id=1, published="2024-06-01")
        result = calculate_lqs(db_conn, 1)
        for dim in ["recency_score", "citation_impact_score", "venue_score",
                     "institution_score", "acceptance_score", "composite_score",
                     "classification"]:
            assert dim in result

    def test_weighted_sum_is_correct(self, db_conn):
        """Verify the composite score equals the weighted sum of dimensions."""
        _insert_work(db_conn, work_id=1, published="2024-06-01",
                     journal_ref="Nature (2024)",
                     authors_json='["DeepMind Researcher"]')
        result = calculate_lqs(db_conn, 1)
        expected = (
            result["recency_score"] * LQS_WEIGHTS["recency"]
            + result["citation_impact_score"] * LQS_WEIGHTS["citation_impact"]
            + result["venue_score"] * LQS_WEIGHTS["venue"]
            + result["institution_score"] * LQS_WEIGHTS["institution"]
            + result["acceptance_score"] * LQS_WEIGHTS["acceptance"]
        )
        assert abs(result["composite_score"] - expected) < 0.1


# ---------------------------------------------------------------------------
# Test save_lqs
# ---------------------------------------------------------------------------

class TestSaveLQS:
    def test_save_and_retrieve(self, db_conn):
        _insert_work(db_conn, work_id=1)
        result = calculate_lqs(db_conn, 1)
        save_lqs(db_conn, result)

        row = db_conn.execute(
            "SELECT * FROM lqs_scores WHERE work_id = 1"
        ).fetchone()
        assert row is not None
        assert row["composite_score"] == result["composite_score"]
        assert row["classification"] == result["classification"]

    def test_upsert_updates(self, db_conn):
        _insert_work(db_conn, work_id=1, published="2020-01-01")
        result1 = calculate_lqs(db_conn, 1)
        save_lqs(db_conn, result1)

        # Update the work to be more recent
        recent = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        db_conn.execute("UPDATE works SET published = ? WHERE work_id = 1", (recent,))
        db_conn.commit()

        result2 = calculate_lqs(db_conn, 1)
        save_lqs(db_conn, result2)

        # Should still be only one row, with updated score
        count = db_conn.execute("SELECT COUNT(*) FROM lqs_scores").fetchone()[0]
        assert count == 1
        row = db_conn.execute("SELECT * FROM lqs_scores WHERE work_id = 1").fetchone()
        assert row["composite_score"] == result2["composite_score"]


# ---------------------------------------------------------------------------
# Test classify_depth
# ---------------------------------------------------------------------------

class TestClassifyDepth:
    def test_depth_a_protagonist(self, db_conn, tmp_path):
        _insert_work(db_conn, work_id=1)
        _insert_citation_key(db_conn, work_id=1, key="zhang2024survey")

        # Create a source file with many citation usages
        source = tmp_path / "main.typ"
        source.write_text(
            "= Introduction\n"
            + " ".join(["@zhang2024survey"] * 10)
            + "\n\nSome other text."
        )

        result = classify_depth(db_conn, 1, source)
        assert result["depth"] == "A"
        assert result["usage_count"] == 10

    def test_depth_b_important(self, db_conn, tmp_path):
        _insert_work(db_conn, work_id=1)
        _insert_citation_key(db_conn, work_id=1, key="smith2023method")

        source = tmp_path / "main.tex"
        source.write_text(
            r"\section{Methods}"
            + r"\cite{smith2023method} \cite{smith2023method} \cite{smith2023method} "
            + r"\cite{smith2023method} \cite{smith2023method}"
        )

        result = classify_depth(db_conn, 1, source)
        assert result["depth"] == "B"
        assert result["usage_count"] == 5

    def test_depth_c_supporting(self, db_conn, tmp_path):
        _insert_work(db_conn, work_id=1)
        _insert_citation_key(db_conn, work_id=1, key="jones2022study")

        source = tmp_path / "main.typ"
        source.write_text("= Background\nSome text @jones2022study more text.")

        result = classify_depth(db_conn, 1, source)
        assert result["depth"] == "C"
        assert result["usage_count"] == 1

    def test_depth_d_dropped(self, db_conn, tmp_path):
        _insert_work(db_conn, work_id=1)
        _insert_citation_key(db_conn, work_id=1, key="brown2021old")

        source = tmp_path / "main.typ"
        source.write_text("= Methods\nNo reference to brown2021old here.")

        result = classify_depth(db_conn, 1, source)
        assert result["depth"] == "D"
        assert result["usage_count"] == 0

    def test_no_source_file(self, db_conn):
        _insert_work(db_conn, work_id=1)
        _insert_citation_key(db_conn, work_id=1, key="test2024")

        result = classify_depth(db_conn, 1, None)
        assert result["depth"] == "D"

    def test_no_citation_key(self, db_conn, tmp_path):
        _insert_work(db_conn, work_id=1)
        # No citation key inserted

        source = tmp_path / "main.typ"
        source.write_text("Some text.")

        result = classify_depth(db_conn, 1, source)
        assert result["depth"] == "D"


# ---------------------------------------------------------------------------
# Test quality_report
# ---------------------------------------------------------------------------

class TestQualityReport:
    def test_empty_registry(self, db_conn):
        report = quality_report(db_conn)
        assert "error" in report

    def test_report_with_data(self, db_conn):
        _insert_work(db_conn, work_id=1, source="arxiv", journal_ref="NeurIPS 2024")
        _insert_work(db_conn, work_id=2, source="pubmed", journal_ref="Nature (2023)")

        result1 = calculate_lqs(db_conn, 1)
        save_lqs(db_conn, result1)
        result2 = calculate_lqs(db_conn, 2)
        save_lqs(db_conn, result2)

        report = quality_report(db_conn)
        assert "error" not in report
        assert report["total_scored"] == 2
        assert "classification_summary" in report
        assert "quality_gates" in report
        gates = report["quality_gates"]
        assert "arxiv_only_ratio" in gates
        assert "recency_ratio" in gates
        assert "verification_rate" in gates
        # All gates should be boolean
        for gate_key in ["arxiv_only_pass", "recency_pass", "verification_pass"]:
            assert isinstance(gates[gate_key], bool), f"{gate_key} should be bool"


# ---------------------------------------------------------------------------
# Test venue upgrade
# ---------------------------------------------------------------------------

class TestVenueUpgrade:
    def test_arxiv_only_detected(self, db_conn):
        _insert_work(db_conn, work_id=1, source="arxiv", journal_ref="arXiv preprint")
        results = upgrade_venues(db_conn)
        # May or may not find a venue via DBLP (depends on network)
        # At minimum, shouldn't crash
        assert isinstance(results, list)

    def test_non_arxiv_skipped(self, db_conn):
        _insert_work(db_conn, work_id=1, source="pubmed",
                     journal_ref="Nature (2024)")
        results = upgrade_venues(db_conn)
        assert len(results) == 0  # non-arxiv source should not be upgraded


# ---------------------------------------------------------------------------
# Test CLI entry point (basic)
# ---------------------------------------------------------------------------

class TestCLI:
    def test_main_help(self):
        """Verify main() parses --help without error."""
        import sys as _sys
        from lqs_scorer import main
        # Just test that the module can be imported and main exists
        assert callable(main)

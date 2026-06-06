"""Tests for literature_registry.py — database operations (no network calls)."""

import json
import sqlite3

import pytest
from literature_registry import (
    init_schema,
    upsert_work,
    generate_citation_key,
    cross_ref_dois,
    record_verification,
    get_verification_status,
    _clean_doi,
)


@pytest.fixture
def db_conn():
    """In-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_schema(conn)
    yield conn
    conn.close()


SAMPLE_WORK = {
    "source": "arxiv",
    "source_id": "2401.12345",
    "title": "A Comprehensive Survey of Topic",
    "summary": "This paper surveys...",
    "published": "2024-01-15",
    "authors": json.dumps(["Zhang, Wei", "Anderson, Thomas"]),
    "doi": "10.1234/test.2024",
    "journal_ref": "arXiv preprint arXiv:2401.12345",
    "primary_category": "cs.AI",
    "categories": json.dumps(["cs.AI", "cs.LG"]),
    "abs_url": "https://arxiv.org/abs/2401.12345",
    "pdf_url": "https://arxiv.org/pdf/2401.12345",
}


class TestSchemaInit:
    def test_init_creates_tables(self, db_conn):
        tables = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        ).fetchall()
        table_names = {r["name"] for r in tables}
        assert "works" in table_names
        assert "searches" in table_names
        assert "search_results" in table_names
        assert "bibtex" in table_names
        assert "fetches" in table_names
        assert "citation_keys" in table_names
        assert "verifications" in table_names
        assert "schema_meta" in table_names

    def test_init_idempotent(self, db_conn):
        init_schema(db_conn)


class TestUpsertWork:
    def test_insert_new_work(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        assert work_id > 0
        row = db_conn.execute("SELECT * FROM works WHERE work_id = ?", (work_id,)).fetchone()
        assert row["title"] == SAMPLE_WORK["title"]
        assert row["source"] == "arxiv"

    def test_upsert_updates_existing(self, db_conn):
        wid1 = upsert_work(db_conn, SAMPLE_WORK)
        updated = dict(SAMPLE_WORK, title="Updated Title")
        wid2 = upsert_work(db_conn, updated)
        assert wid1 == wid2
        row = db_conn.execute("SELECT title FROM works WHERE work_id = ?", (wid1,)).fetchone()
        assert row["title"] == "Updated Title"

    def test_source_id_uniqueness(self, db_conn):
        upsert_work(db_conn, SAMPLE_WORK)
        duplicate = dict(SAMPLE_WORK, title="Different Title")
        wid2 = upsert_work(db_conn, duplicate)
        count = db_conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        assert count == 1


class TestCitationKeys:
    def test_generate_key(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        # generate_citation_key needs authors_json field
        row = db_conn.execute(
            "SELECT * FROM works WHERE work_id = ?", (work_id,)
        ).fetchone()
        work_dict = dict(row)
        key = generate_citation_key(db_conn, work_id, work_dict)
        assert len(key) > 0
        assert "2024" in key

    def test_generate_duplicate_key_increments(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        row = db_conn.execute(
            "SELECT * FROM works WHERE work_id = ?", (work_id,)
        ).fetchone()
        key1 = generate_citation_key(db_conn, work_id, dict(row))
        assert len(key1) > 0


class TestCrossRefDOIs:
    def test_merge_duplicate_dois(self, db_conn):
        work1 = dict(SAMPLE_WORK)
        wid1 = upsert_work(db_conn, work1)

        work2 = dict(SAMPLE_WORK, source="pubmed", source_id="12345678")
        wid2 = upsert_work(db_conn, work2)

        merged = cross_ref_dois(db_conn)
        assert merged == 1

        remaining = db_conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
        assert remaining == 1

    def test_no_duplicates_no_merge(self, db_conn):
        work1 = dict(SAMPLE_WORK)
        upsert_work(db_conn, work1)

        work2 = dict(SAMPLE_WORK, doi="10.9999/unique.2024", source_id="2401.99999")
        upsert_work(db_conn, work2)

        merged = cross_ref_dois(db_conn)
        assert merged == 0


class TestVerification:
    """Tests for citation verification functions (no network calls)."""

    def test_clean_doi_strips_prefix(self):
        assert _clean_doi("https://doi.org/10.1234/example") == "10.1234/example"
        assert _clean_doi("https://dx.doi.org/10.1234/example") == "10.1234/example"
        assert _clean_doi("10.1234/example") == "10.1234/example"
        assert _clean_doi("  10.1234/example  ") == "10.1234/example"

    def test_record_verification_pass(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        vid = record_verification(
            db_conn,
            work_id=work_id,
            method="crossref-doi",
            doi="10.1234/test.2024",
            status="pass",
            resolved_title="A Comprehensive Survey of Topic",
            resolved_authors=["Zhang Wei", "Anderson Thomas"],
            resolved_year="2024",
            resolved_journal="arXiv preprint",
            error_message=None,
        )
        assert vid > 0

        result = get_verification_status(db_conn, work_id)
        assert result is not None
        assert result["status"] == "pass"
        assert result["method"] == "crossref-doi"
        assert result["resolved_title"] == "A Comprehensive Survey of Topic"

    def test_record_verification_fail(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        record_verification(
            db_conn,
            work_id=work_id,
            method="crossref-doi",
            doi="10.1234/fake.9999",
            status="fail",
            resolved_title=None,
            resolved_authors=None,
            resolved_year=None,
            resolved_journal=None,
            error_message="DOI not found",
        )

        result = get_verification_status(db_conn, work_id)
        assert result is not None
        assert result["status"] == "fail"
        assert result["error_message"] == "DOI not found"

    def test_no_verification_returns_none(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        result = get_verification_status(db_conn, work_id)
        assert result is None

    def test_multiple_verifications_returns_latest(self, db_conn):
        work_id = upsert_work(db_conn, SAMPLE_WORK)
        record_verification(
            db_conn, work_id=work_id, method="manual", doi=None,
            status="pass", resolved_title="Old Title",
            resolved_authors=[], resolved_year=None,
            resolved_journal=None, error_message=None,
        )
        record_verification(
            db_conn, work_id=work_id, method="crossref-doi",
            doi="10.1234/test.2024", status="pass",
            resolved_title="Updated Title",
            resolved_authors=[], resolved_year=None,
            resolved_journal=None, error_message=None,
        )
        result = get_verification_status(db_conn, work_id)
        assert result["resolved_title"] == "Updated Title"

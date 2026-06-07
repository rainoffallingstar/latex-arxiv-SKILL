#!/usr/bin/env python3
"""Literature Quality Scoring (LQS) engine for academic paper writing.

Implements the 4-stage literature quality pipeline:
  1. LQS multi-dimensional scoring (Recency, Citation Impact, Venue, Institution, Acceptance)
  2. A/B/C/D citation depth classification
  3. Venue upgrade (arXiv -> accepted venue cross-check)
  4. Quality gate enforcement

CLI:
    python3 lqs_scorer.py score <work_id> [--db PATH] [--project-dir PATH]
    python3 lqs_scorer.py score-all [--threshold 7.0] [--db PATH] [--project-dir PATH]
    python3 lqs_scorer.py classify-depth <work_id> [--source PATH] [--db PATH]
    python3 lqs_scorer.py classify-depth-all [--source PATH] [--db PATH] [--project-dir PATH]
    python3 lqs_scorer.py upgrade-venues [--db PATH] [--project-dir PATH]
    python3 lqs_scorer.py quality-report [--db PATH] [--project-dir PATH]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Import shared utilities from sibling scripts
try:
    from literature_registry import (
        resolve_db_path,
        init_schema,
        now_iso,
        fetch_url,
        _rate_limiter,
    )
except ImportError:
    # Fallback for standalone use
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def resolve_db_path(args: argparse.Namespace) -> Path:
        if getattr(args, "db", None):
            return Path(args.db).expanduser().resolve()
        project_dir = Path(getattr(args, "project_dir", None) or ".").expanduser().resolve()
        return project_dir / "notes" / "literature-registry.sqlite3"

    def init_schema(conn: sqlite3.Connection) -> None:
        pass  # schema managed by literature_registry.py

    def fetch_url(url: str, *, timeout_s: int = 30, retries: int = 3) -> tuple[int | None, bytes]:
        import urllib.request
        import urllib.error
        for attempt in range(retries + 1):
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "lqs-scorer/1.0"},
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                    return getattr(resp, "status", None), resp.read()
            except urllib.error.HTTPError as e:
                code = getattr(e, "code", None)
                if code == 429 and attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                return code, b""
            except urllib.error.URLError:
                if attempt < retries:
                    time.sleep(1)
                    continue
                return None, b""
        return None, b""


# ---------------------------------------------------------------------------
# LQS scoring weights and thresholds
# ---------------------------------------------------------------------------

LQS_WEIGHTS = {
    "recency": 0.30,
    "citation_impact": 0.25,
    "venue": 0.20,
    "institution": 0.10,
    "acceptance": 0.15,
}

LQS_THRESHOLD_MUST_CITE = 7.0
LQS_THRESHOLD_CONDITIONAL = 5.0

# ---------------------------------------------------------------------------
# Venue tier classification
# ---------------------------------------------------------------------------

TOP_TIER_VENUES: set[str] = {
    # CS conferences
    "neurips", "nips", "icml", "iclr", "cvpr", "iccv", "eccv",
    "acl", "emnlp", "naacl", "aaai", "ijcai", "siggraph",
    "osdi", "sosp", "nsdi", "sigcomm", "mobicom",
    "stoc", "focs", "soda", "crypto",
    # CS journals
    "jmlr", "ieee transactions on pattern analysis", "tpami",
    "ieee transactions on information theory",
    "acm computing surveys",
    # General science
    "nature", "science", "cell", "pnas",
    "the lancet", "nejm", "jama", "bmj",
    # Physics
    "physical review letters", "prl",
    "reviews of modern physics",
    # Biomed
    "nature medicine", "nature genetics", "nature biotechnology",
    "cancer cell", "cell stem cell",
}

STRONG_VENUES: set[str] = {
    # CS conferences
    "icdm", "cikm", "wsdm", "ecml", "pkdd", "colt",
    "uai", "aistats", "icra", "iassist", "iros",
    "eacl", "conll", "coling", "recsys",
    "www", "sigir", "kdd", "sigmod", "vldb",
    "isca", "micro", "hpc", "asplos",
    # CS journals
    "ieee access", "neurocomputing", "pattern recognition",
    "machine learning", "neural networks",
    "artificial intelligence",
    "ieee transactions on neural networks",
    # General
    "scientific reports", "plos one", "elife",
    "nature communications", "science advances",
    # Physics
    "physical review d", "physical review b",
    "physical review e", "physical review x",
    "journal of high energy physics", "classical and quantum gravity",
    # Biomed
    "bioinformatics", "nucleic acids research",
    "genome biology", "genome research",
}

WORKSHOP_VENUES: set[str] = {
    "workshop", "symposium", "poster", "abstract",
    "icml workshop", "neurips workshop", "cvpr workshop",
}

# ---------------------------------------------------------------------------
# Top institutions
# ---------------------------------------------------------------------------

TOP_LABS: set[str] = {
    "deepmind", "google deepmind", "openai", "anthropic",
    "google research", "google brain", "microsoft research",
    "facebook ai research", "fair", "meta ai",
    "nvidia research", "apple machine learning research",
}

TOP_UNIVERSITIES: set[str] = {
    "mit", "stanford", "carnegie mellon", "cmu",
    "uc berkeley", "berkeley", "caltech",
    "oxford", "cambridge", "eth zurich", "ethz",
    "university of toronto", "princeton", "harvard",
    "tsinghua", "peking", "eth",
    "max planck", "epfl", "imperial college",
}

# ---------------------------------------------------------------------------
# Schema migration: add LQS tables
# ---------------------------------------------------------------------------

_LQS_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS lqs_scores (
        work_id INTEGER PRIMARY KEY REFERENCES works(work_id) ON DELETE CASCADE,
        scored_at TEXT NOT NULL,
        recency_score REAL,
        citation_impact_score REAL,
        venue_score REAL,
        institution_score REAL,
        acceptance_score REAL,
        composite_score REAL NOT NULL,
        classification TEXT,
        details_json TEXT
    );

    CREATE INDEX IF NOT EXISTS lqs_composite_idx ON lqs_scores(composite_score);
    CREATE INDEX IF NOT EXISTS lqs_classification_idx ON lqs_scores(classification);
"""


def ensure_lqs_schema(conn: sqlite3.Connection) -> None:
    """Create LQS tables if they don't exist."""
    conn.executescript(_LQS_SCHEMA_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# Dimension 1: Recency scoring
# ---------------------------------------------------------------------------

def score_recency(published: str | None) -> tuple[float, str]:
    """Score based on publication date relative to now.

    Returns (score, bucket_label).
    """
    if not published:
        return 3.0, "unknown_date"

    try:
        # Try ISO format: 2024-01-15
        pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        try:
            # Try year-only: 2024
            pub_date = datetime(int(published.strip()), 1, 1, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            try:
                # Try arXiv format: "Mon, 15 Jan 2024 00:00:00 GMT"
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(published)
            except Exception:
                return 3.0, "unparseable_date"

    now = datetime.now(timezone.utc)
    age_months = (now - pub_date).days / 30.44

    if age_months <= 6:
        return 10.0, "<=6mo"
    elif age_months <= 12:
        return 8.0, "<=1yr"
    elif age_months <= 24:
        return 5.0, "<=2yr"
    elif age_months <= 36:
        return 3.0, "<=3yr"
    else:
        return 1.0, ">3yr"


# ---------------------------------------------------------------------------
# Dimension 2: Citation impact scoring
# ---------------------------------------------------------------------------

def score_citation_impact(
    conn: sqlite3.Connection,
    work_id: int,
    published: str | None,
    source_id: str | None = None,
) -> tuple[float, str]:
    """Score based on citation count and rate.

    First checks cached citation_count in lqs_details, then tries
    to fetch from OpenAlex by DOI.

    Returns (score, bucket_label).
    """
    # Try to get cached citation count
    row = conn.execute(
        "SELECT details_json FROM lqs_scores WHERE work_id = ?",
        (work_id,),
    ).fetchone()

    if row and row[0]:
        try:
            details = json.loads(row[0])
            if "citation_count" in details:
                cites = int(details["citation_count"])
                return _citation_bucket(cites, published)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Try to fetch from OpenAlex by DOI
    doi_row = conn.execute(
        "SELECT doi FROM works WHERE work_id = ? AND doi IS NOT NULL",
        (work_id,),
    ).fetchone()

    if doi_row and doi_row[0]:
        cites = _fetch_citation_count_from_openalex(doi_row[0])
        if cites is not None:
            return _citation_bucket(cites, published)

    return 3.0, "unavailable"


def _citation_bucket(cites: int, published: str | None) -> tuple[float, str]:
    """Map citation count to score bucket."""
    # Estimate cites/month using the published date
    months_since_pub = 24  # default: assume 2 years
    if published:
        try:
            pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            months_since_pub = max(1, (now - pub_date).days / 30.44)
        except (ValueError, TypeError):
            pass

    cites_per_month = cites / months_since_pub

    if cites_per_month >= 50:
        return 10.0, f">=50/mo ({cites} total)"
    elif cites_per_month >= 10:
        return 8.0, f">=10/mo ({cites} total)"
    elif cites_per_month >= 3:
        return 6.0, f">=3/mo ({cites} total)"
    elif cites_per_month >= 1:
        return 4.0, f">=1/mo ({cites} total)"
    else:
        return 2.0, f"<1/mo ({cites} total)"


def _fetch_citation_count_from_openalex(doi: str) -> int | None:
    """Try to fetch citation count from OpenAlex by DOI."""
    clean_doi = doi.strip()
    if clean_doi.startswith("https://doi.org/"):
        clean_doi = clean_doi[len("https://doi.org/"):]
    if clean_doi.startswith("http://"):
        clean_doi = clean_doi[len("http://"):]

    url = f"https://api.openalex.org/works/doi:{clean_doi}"
    status, body = fetch_url(url, timeout_s=15, retries=1)
    if status != 200 or not body:
        return None

    try:
        data = json.loads(body)
        return data.get("cited_by_count")
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Dimension 3: Venue scoring
# ---------------------------------------------------------------------------

def score_venue(journal_ref: str | None, primary_category: str | None, categories: list[str] | None) -> tuple[float, str]:
    """Score based on publication venue tier.

    Returns (score, tier_label).
    """
    search_text = " ".join([
        (journal_ref or "").lower(),
        (primary_category or "").lower(),
        " ".join(categories or []).lower(),
    ])

    # Check top tier
    for venue in TOP_TIER_VENUES:
        if venue in search_text:
            return 10.0, f"top_tier ({venue})"

    # Check strong
    for venue in STRONG_VENUES:
        if venue in search_text:
            return 7.0, f"strong ({venue})"

    # Check workshop
    for venue in WORKSHOP_VENUES:
        if venue in search_text:
            return 4.0, f"workshop ({venue})"

    # Heuristic: arXiv without journal_ref is likely preprint only
    if journal_ref and "arxiv" in (journal_ref or "").lower():
        return 4.0, "arxiv_only"
    if not journal_ref or journal_ref.strip() == "":
        return 4.0, "no_venue_info"

    return 5.0, "unclassified"


# ---------------------------------------------------------------------------
# Dimension 4: Institution scoring
# ---------------------------------------------------------------------------

def score_institution(authors_json: str | None) -> tuple[float, str]:
    """Score based on author affiliations.

    Parses author affiliation from the authors field or searches
    for known top institutions.

    Returns (score, tier_label).
    """
    if not authors_json:
        return 3.0, "no_author_data"

    try:
        authors = json.loads(authors_json)
    except json.JSONDecodeError:
        authors = []

    author_text = " ".join(str(a).lower() for a in authors)

    # Check for top labs (highest weight)
    for lab in TOP_LABS:
        if lab in author_text:
            return 10.0, f"top_lab ({lab})"

    # Check for top universities
    for uni in TOP_UNIVERSITIES:
        if uni in author_text:
            return 9.0, f"top_uni ({uni})"

    # Count known institutions for a boost
    known_count = 0
    for author in authors:
        author_lower = str(author).lower()
        for known in list(TOP_LABS) + list(TOP_UNIVERSITIES):
            if known in author_lower:
                known_count += 1
                break

    if known_count > 0:
        return 6.0, f"partial_match ({known_count})"

    return 4.0, "unknown_institution"


# ---------------------------------------------------------------------------
# Dimension 5: Acceptance scoring
# ---------------------------------------------------------------------------

def score_acceptance(journal_ref: str | None, source: str) -> tuple[float, str]:
    """Score based on acceptance/peer-review status.

    Returns (score, status_label).
    """
    if not journal_ref or journal_ref.strip() == "":
        # arXiv-only = likely preprint
        if source == "arxiv":
            return 3.0, "arxiv_preprint"
        return 3.0, "unknown_status"

    jref_lower = journal_ref.lower()

    # Check for explicit acceptance
    accepted_patterns = [
        r"accepted\s+(?:at|to|by|for|in)\s",
        r"to\s+appear\s+in",
        r"forthcoming\s+in",
        r"in\s+press",
        r"published\s+in",
        r"proceedings\s+of",
    ]
    for pat in accepted_patterns:
        if re.search(pat, jref_lower):
            return 10.0, "accepted"

    # Check for arXiv preprint status
    if "arxiv" in jref_lower and "preprint" not in jref_lower:
        return 3.0, "arxiv_preprint"
    if "arxiv preprint" in jref_lower:
        return 3.0, "arxiv_preprint"

    # Under review indicators
    under_review_patterns = [
        r"under\s+review",
        r"submitted\s+to",
        r"in\s+submission",
    ]
    for pat in under_review_patterns:
        if re.search(pat, jref_lower):
            return 5.0, "under_review"

    # Non-arxiv with journal reference = likely accepted
    if source != "arxiv" and jref_lower:
        return 10.0, "journal_article"

    return 3.0, "unknown"


# ---------------------------------------------------------------------------
# Composite LQS calculation
# ---------------------------------------------------------------------------

def calculate_lqs(
    conn: sqlite3.Connection,
    work_id: int,
    work: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate full LQS score for a work.

    Returns dict with all dimension scores and composite.
    """
    if work is None:
        row = conn.execute(
            "SELECT * FROM works WHERE work_id = ?", (work_id,)
        ).fetchone()
        if not row:
            return {"error": f"Work {work_id} not found"}
        work = dict(row)

    published = work.get("published")
    journal_ref = work.get("journal_ref")
    primary_category = work.get("primary_category")
    authors_json = work.get("authors_json")
    source = work.get("source", "unknown")
    source_id = work.get("source_id")

    # Parse categories
    categories = None
    if work.get("categories_json"):
        try:
            categories = json.loads(work["categories_json"])
        except json.JSONDecodeError:
            pass

    # Score each dimension
    recency, rec_label = score_recency(published)
    citation, cit_label = score_citation_impact(conn, work_id, published, source_id)
    venue, ven_label = score_venue(journal_ref, primary_category, categories)
    institution, inst_label = score_institution(authors_json)
    acceptance, acc_label = score_acceptance(journal_ref, source)

    # Weighted composite
    composite = (
        recency * LQS_WEIGHTS["recency"]
        + citation * LQS_WEIGHTS["citation_impact"]
        + venue * LQS_WEIGHTS["venue"]
        + institution * LQS_WEIGHTS["institution"]
        + acceptance * LQS_WEIGHTS["acceptance"]
    )

    result = {
        "work_id": work_id,
        "title": work.get("title", ""),
        "recency_score": recency,
        "recency_label": rec_label,
        "citation_impact_score": citation,
        "citation_impact_label": cit_label,
        "venue_score": venue,
        "venue_label": ven_label,
        "institution_score": institution,
        "institution_label": inst_label,
        "acceptance_score": acceptance,
        "acceptance_label": acc_label,
        "composite_score": round(composite, 2),
    }

    # Classification
    if composite >= LQS_THRESHOLD_MUST_CITE:
        result["classification"] = "must_cite"
    elif composite >= LQS_THRESHOLD_CONDITIONAL:
        result["classification"] = "conditional"
    else:
        result["classification"] = "drop"

    return result


def save_lqs(conn: sqlite3.Connection, result: dict[str, Any]) -> None:
    """Persist LQS scores to the database."""
    details = {
        "recency_label": result.get("recency_label", ""),
        "citation_impact_label": result.get("citation_impact_label", ""),
        "venue_label": result.get("venue_label", ""),
        "institution_label": result.get("institution_label", ""),
        "acceptance_label": result.get("acceptance_label", ""),
        "title": result.get("title", ""),
    }

    conn.execute(
        """INSERT INTO lqs_scores(
            work_id, scored_at, recency_score, citation_impact_score,
            venue_score, institution_score, acceptance_score,
            composite_score, classification, details_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(work_id) DO UPDATE SET
            scored_at=excluded.scored_at,
            recency_score=excluded.recency_score,
            citation_impact_score=excluded.citation_impact_score,
            venue_score=excluded.venue_score,
            institution_score=excluded.institution_score,
            acceptance_score=excluded.acceptance_score,
            composite_score=excluded.composite_score,
            classification=excluded.classification,
            details_json=excluded.details_json;""",
        (
            result["work_id"],
            now_iso(),
            result["recency_score"],
            result["citation_impact_score"],
            result["venue_score"],
            result["institution_score"],
            result["acceptance_score"],
            result["composite_score"],
            result["classification"],
            json.dumps(details, ensure_ascii=False),
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# A/B/C/D citation depth classification
# ---------------------------------------------------------------------------

def classify_depth(
    conn: sqlite3.Connection,
    work_id: int,
    source_path: Path | None = None,
) -> dict[str, Any]:
    """Classify citation depth based on usage in the paper source.

    Scans main.typ or main.tex to count how many times the citation
    key appears and in what context.

    Returns dict with depth_classification and usage_count.
    """

    # Get the citation key for this work
    key_row = conn.execute(
        "SELECT key FROM citation_keys WHERE work_id = ?",
        (work_id,),
    ).fetchone()

    if not key_row or not source_path or not source_path.exists():
        return {"work_id": work_id, "depth": "D", "usage_count": 0, "reason": "no_source_or_key"}

    cite_key = key_row[0]
    content = source_path.read_text(encoding="utf-8", errors="replace")

    is_typst = source_path.suffix == ".typ"

    if is_typst:
        # Typst: @key syntax
        pattern = re.compile(r"@" + re.escape(cite_key) + r"(?![a-zA-Z0-9_\-:])")
    else:
        # LaTeX: \cite{key} syntax
        pattern = re.compile(
            r"\\(?:cite|citep|citet|citealt|citealp|citenum)\{[^}]*"
            + re.escape(cite_key)
            + r"[^}]*\}"
        )

    matches = list(pattern.finditer(content))

    usage_count = len(matches)

    # Determine depth classification
    if usage_count == 0:
        depth = "D"  # not cited in text
    elif usage_count <= 2:
        depth = "C"  # 1-2 mentions: supporting evidence
    elif usage_count <= 6:
        depth = "B"  # 3-6 mentions: important insight
    else:
        depth = "A"  # 7+ mentions: section protagonist

    return {
        "work_id": work_id,
        "citation_key": cite_key,
        "depth": depth,
        "usage_count": usage_count,
        "reason": _depth_reason(depth, usage_count),
    }


def _depth_reason(depth: str, usage_count: int) -> str:
    labels = {
        "A": "Section protagonist (1-3 paragraphs expected)",
        "B": "Important insight (2-5 sentences expected)",
        "C": "Supporting evidence (1 sentence expected)",
        "D": "Dropped — not cited in text",
    }
    return f"{labels.get(depth, 'Unknown')} — {usage_count} citation usages found"


# ---------------------------------------------------------------------------
# Venue upgrade
# ---------------------------------------------------------------------------

def upgrade_venues(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Cross-check arXiv papers against DBLP and OpenReview for acceptance.

    Returns list of upgrade results.
    """
    # Find arXiv-only works (no journal_ref or arxiv preprint only)
    rows = conn.execute(
        """SELECT work_id, title, authors_json, doi, source_id
           FROM works
           WHERE source = 'arxiv'
             AND (journal_ref IS NULL
                  OR journal_ref = ''
                  OR journal_ref LIKE '%arxiv%')
           ORDER BY published DESC"""
    ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        work_id = row[0]
        title = row[1]
        authors_json = row[2]
        doi = row[3]
        source_id = row[4]

        upgrade = _check_dblp_for_acceptance(title, authors_json)
        if not upgrade:
            upgrade = _check_journal_ref_for_acceptance(conn, work_id)

        if upgrade:
            results.append({
                "work_id": work_id,
                "title": title[:80],
                "upgraded_to": upgrade,
            })

            # Update journal_ref in works table
            conn.execute(
                "UPDATE works SET journal_ref = ? WHERE work_id = ?",
                (upgrade, work_id),
            )
            conn.commit()

    return results


def _check_dblp_for_acceptance(title: str, authors_json: str | None) -> str | None:
    """Query DBLP for a paper's peer-reviewed venue.

    DBLP API: https://dblp.org/search/publ/api?q=<title>&format=json
    """
    clean_title = title.strip()
    if not clean_title:
        return None

    url = f"https://dblp.org/search/publ/api?q={clean_title}&format=json&h=1"
    status, body = fetch_url(url, timeout_s=15, retries=1)
    if status != 200 or not body:
        return None

    try:
        data = json.loads(body)
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        if not hits:
            return None
        hit = hits[0]
        info = hit.get("info", {})
        venue = info.get("venue", "")
        year = info.get("year", "")
        if venue:
            return f"Accepted at {venue} ({year}) [DBLP]"
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return None


def _check_journal_ref_for_acceptance(conn: sqlite3.Connection, work_id: int) -> str | None:
    """Check if journal_ref already contains acceptance info we missed."""
    row = conn.execute(
        "SELECT journal_ref FROM works WHERE work_id = ?",
        (work_id,),
    ).fetchone()
    if not row or not row[0]:
        return None

    jref = row[0]
    # Already has acceptance info
    accepted_patterns = [
        r"Accepted\s+(?:at|to|by|for|in)\s",
        r"Proceedings\s+of",
        r"Published\s+in",
    ]
    for pat in accepted_patterns:
        if re.search(pat, jref, re.IGNORECASE):
            return None  # already classified

    # Not arxiv-only, so it has a venue
    if "arxiv" not in jref.lower():
        return f"Accepted at {jref}"

    return None


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------

def quality_report(conn: sqlite3.Connection) -> dict[str, Any]:
    """Generate a quality report with all quality gate metrics."""
    # Total scored works
    total = conn.execute("SELECT COUNT(*) FROM lqs_scores").fetchone()[0]
    if total == 0:
        return {"error": "No LQS scores available. Run 'score-all' first."}

    # Classification counts
    must_cite = conn.execute(
        "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'must_cite'"
    ).fetchone()[0]
    conditional = conn.execute(
        "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'conditional'"
    ).fetchone()[0]
    dropped = conn.execute(
        "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'drop'"
    ).fetchone()[0]

    # Average composite score
    avg = conn.execute(
        "SELECT AVG(composite_score) FROM lqs_scores"
    ).fetchone()[0] or 0.0

    # Depth distribution
    depth_dist = {}
    depth_rows = conn.execute(
        """SELECT details_json FROM lqs_scores
           WHERE details_json IS NOT NULL"""
    ).fetchall()
    for dr in depth_rows:
        try:
            details = json.loads(dr[0])
            d = details.get("depth", "unknown")
            depth_dist[d] = depth_dist.get(d, 0) + 1
        except json.JSONDecodeError:
            pass

    # arXiv-only ratio
    arxiv_total = conn.execute(
        "SELECT COUNT(*) FROM works WHERE source = 'arxiv'"
    ).fetchone()[0]
    arxiv_only = conn.execute(
        """SELECT COUNT(*) FROM works
           WHERE source = 'arxiv'
             AND (journal_ref IS NULL
                  OR journal_ref = ''
                  OR journal_ref LIKE '%arxiv%')"""
    ).fetchone()[0]

    arxiv_ratio = arxiv_only / arxiv_total if arxiv_total > 0 else 0.0

    # Recency: fraction within 3 years
    recent = conn.execute(
        "SELECT COUNT(*) FROM lqs_scores WHERE recency_score >= 5.0"
    ).fetchone()[0]
    recency_ratio = recent / total if total > 0 else 0.0

    # Verified fraction
    verified = conn.execute(
        "SELECT COUNT(*) FROM verifications WHERE status = 'pass'"
    ).fetchone()[0]
    total_works = conn.execute("SELECT COUNT(*) FROM works").fetchone()[0]
    verification_rate = verified / total_works if total_works > 0 else 0.0

    # Gate checks
    gates = {
        "citations_total": total,
        "citations_must_cite": must_cite,
        "citations_conditional": conditional,
        "citations_dropped": dropped,
        "avg_composite_score": round(avg, 2),
        "depth_distribution": depth_dist,
        "arxiv_only_ratio": round(arxiv_ratio, 2),
        "arxiv_only_target": "<= 0.60",
        "arxiv_only_pass": arxiv_ratio <= 0.60,
        "recency_ratio": round(recency_ratio, 2),
        "recency_target": ">= 0.70",
        "recency_pass": recency_ratio >= 0.70,
        "verification_rate": round(verification_rate, 2),
        "verification_target": ">= 0.80",
        "verification_pass": verification_rate >= 0.80,
    }

    return {
        "total_works": total_works,
        "total_scored": total,
        "classification_summary": {
            "must_cite": must_cite,
            "conditional": conditional,
            "drop": dropped,
        },
        "average_score": round(avg, 2),
        "depth_distribution": depth_dist,
        "quality_gates": gates,
    }


# ---------------------------------------------------------------------------
# CLI Handlers
# ---------------------------------------------------------------------------

def cmd_score(args: argparse.Namespace) -> int:
    """Score a single work by LQS."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}. Run 'init' first.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    ensure_lqs_schema(conn)

    try:
        work_id = int(args.work_id)
        result = calculate_lqs(conn, work_id)

        if "error" in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        save_lqs(conn, result)

        print(f"LQS Score for work #{work_id}: {result['title'][:80]}")
        print(f"  Recency:       {result['recency_score']:.1f}  ({result['recency_label']})")
        print(f"  Citation:      {result['citation_impact_score']:.1f}  ({result['citation_impact_label']})")
        print(f"  Venue:         {result['venue_score']:.1f}  ({result['venue_label']})")
        print(f"  Institution:   {result['institution_score']:.1f}  ({result['institution_label']})")
        print(f"  Acceptance:    {result['acceptance_score']:.1f}  ({result['acceptance_label']})")
        print(f"  COMPOSITE:     {result['composite_score']:.1f}  [{result['classification']}]")

        return 0
    finally:
        conn.close()


def cmd_score_all(args: argparse.Namespace) -> int:
    """Score all works in the registry."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    ensure_lqs_schema(conn)

    try:
        rows = conn.execute("SELECT * FROM works ORDER BY work_id").fetchall()
        if not rows:
            print("No works in registry.")
            return 1

        threshold = getattr(args, "threshold", 0.0) or 0.0
        scored = 0
        skipped = 0

        for row in rows:
            work = dict(row)
            result = calculate_lqs(conn, work["work_id"], work)

            if "error" in result:
                continue

            save_lqs(conn, result)
            scored += 1

            if result["composite_score"] >= threshold:
                print(f"  [{result['classification']}] {result['composite_score']:.1f} — {work['title'][:70]}")

        print(f"\nScored {scored} works. Threshold: >= {threshold}")

        # Print summary
        must = conn.execute(
            "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'must_cite'"
        ).fetchone()[0]
        cond = conn.execute(
            "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'conditional'"
        ).fetchone()[0]
        drop = conn.execute(
            "SELECT COUNT(*) FROM lqs_scores WHERE classification = 'drop'"
        ).fetchone()[0]
        print(f"Must-cite: {must}, Conditional: {cond}, Drop: {drop}")

        return 0
    finally:
        conn.close()


def cmd_classify_depth(args: argparse.Namespace) -> int:
    """Classify citation depth for a work."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        return 1

    # Find source file
    source_path = None
    if getattr(args, "source", None):
        source_path = Path(args.source)
    else:
        proj = Path(getattr(args, "project_dir", ".")).expanduser().resolve()
        for name in ("main.typ", "main.tex"):
            candidate = proj / name
            if candidate.exists():
                source_path = candidate
                break

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    ensure_lqs_schema(conn)

    try:
        work_id = int(args.work_id)
        result = classify_depth(conn, work_id, source_path)

        print(f"Depth classification for work #{work_id}:")
        print(f"  Key:     {result.get('citation_key', 'N/A')}")
        print(f"  Depth:   {result['depth']}")
        print(f"  Usages:  {result['usage_count']}")
        print(f"  Reason:  {result['reason']}")

        # Save depth to lqs_scores
        conn.execute(
            "UPDATE lqs_scores SET details_json = json_set("
            "  COALESCE(details_json, '{}'), '$.depth', ?, '$.usage_count', ?"
            ") WHERE work_id = ?",
            (result["depth"], result["usage_count"], work_id),
        )
        conn.commit()

        return 0
    finally:
        conn.close()


def cmd_classify_depth_all(args: argparse.Namespace) -> int:
    """Classify depth for all works with citation keys."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        return 1

    source_path = None
    if getattr(args, "source", None):
        source_path = Path(args.source)
    else:
        proj = Path(getattr(args, "project_dir", ".")).expanduser().resolve()
        for name in ("main.typ", "main.tex"):
            candidate = proj / name
            if candidate.exists():
                source_path = candidate
                break

    if not source_path:
        print("No source file found. Use --source or run from a paper directory.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    try:
        rows = conn.execute(
            "SELECT work_id FROM citation_keys ORDER BY work_id"
        ).fetchall()

        distribution = {"A": 0, "B": 0, "C": 0, "D": 0}
        for row in rows:
            result = classify_depth(conn, row[0], source_path)
            distribution[result["depth"]] += 1

            # Save depth
            conn.execute(
                "UPDATE lqs_scores SET details_json = json_set("
                "  COALESCE(details_json, '{}'), '$.depth', ?, '$.usage_count', ?"
                ") WHERE work_id = ?",
                (result["depth"], result["usage_count"], row[0]),
            )

        conn.commit()

        print(f"Depth classification complete for {len(rows)} works:")
        print(f"  A (protagonist):    {distribution['A']}")
        print(f"  B (important):      {distribution['B']}")
        print(f"  C (supporting):     {distribution['C']}")
        print(f"  D (dropped):        {distribution['D']}")

        return 0
    finally:
        conn.close()


def cmd_upgrade_venues(args: argparse.Namespace) -> int:
    """Run venue upgrade pipeline."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    try:
        results = upgrade_venues(conn)
        if not results:
            print("No arXiv-only papers found for upgrade.")
            return 0

        print(f"Upgraded {len(results)} paper(s):")
        for r in results:
            print(f"  #{r['work_id']}: {r['title']} -> {r['upgraded_to']}")

        # Check arxiv ratio after upgrade
        total = conn.execute("SELECT COUNT(*) FROM works WHERE source = 'arxiv'").fetchone()[0]
        only = conn.execute(
            """SELECT COUNT(*) FROM works
               WHERE source = 'arxiv'
                 AND (journal_ref IS NULL OR journal_ref = '' OR journal_ref LIKE '%arxiv%')"""
        ).fetchone()[0]
        ratio = only / total if total > 0 else 0
        print(f"\narXiv-only ratio: {only}/{total} = {ratio:.1%} (target: <= 60%)")
        print("PASS" if ratio <= 0.60 else "FAIL — more upgrades needed")

        return 0
    finally:
        conn.close()


def cmd_quality_report(args: argparse.Namespace) -> int:
    """Generate quality report."""
    db_path = resolve_db_path(args)
    if not db_path.exists():
        print(f"Error: database not found at {db_path}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    ensure_lqs_schema(conn)

    try:
        report = quality_report(conn)
        if "error" in report:
            print(report["error"], file=sys.stderr)
            return 1

        print("=== Literature Quality Report ===\n")
        print(f"Total works:    {report['total_works']}")
        print(f"Scored works:   {report['total_scored']}")
        print(f"Average score:  {report['average_score']:.1f}/10")
        print()

        cs = report["classification_summary"]
        print("Classification:")
        print(f"  Must-cite (>=7.0):   {cs['must_cite']}")
        print(f"  Conditional (5-7):   {cs['conditional']}")
        print(f"  Drop (<5.0):         {cs['drop']}")
        print()

        if report["depth_distribution"]:
            print("Depth Distribution:")
            for d in ["A", "B", "C", "D"]:
                count = report["depth_distribution"].get(d, 0)
                print(f"  {d}: {count}")
            print()

        gates = report["quality_gates"]
        print("Quality Gates:")
        print(f"  arXiv-only ratio:  {gates['arxiv_only_ratio']:.0%} (target {gates['arxiv_only_target']}) — {'PASS' if gates['arxiv_only_pass'] else 'FAIL'}")
        print(f"  Recency ratio:     {gates['recency_ratio']:.0%} (target {gates['recency_target']}) — {'PASS' if gates['recency_pass'] else 'FAIL'}")
        print(f"  Verification rate: {gates['verification_rate']:.0%} (target {gates['verification_target']}) — {'PASS' if gates['verification_pass'] else 'FAIL'}")

        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Literature Quality Scoring (LQS) engine for academic paper writing."
    )
    parser.add_argument("--db", help="Path to SQLite database file")
    parser.add_argument("--project-dir", default=".", help="Project root directory")

    sub = parser.add_subparsers(dest="command", required=True)

    sp_score = sub.add_parser("score", help="Score a single work by LQS")
    sp_score.add_argument("work_id", help="Work ID from literature registry")

    sp_score_all = sub.add_parser("score-all", help="Score all works in registry")
    sp_score_all.add_argument("--threshold", type=float, default=0.0, help="Only show results >= threshold")

    sp_depth = sub.add_parser("classify-depth", help="Classify citation depth for a work")
    sp_depth.add_argument("work_id", help="Work ID")
    sp_depth.add_argument("--source", help="Path to main.typ or main.tex")

    sp_depth_all = sub.add_parser("classify-depth-all", help="Classify depth for all works")
    sp_depth_all.add_argument("--source", help="Path to main.typ or main.tex")

    sub.add_parser("upgrade-venues", help="Cross-check arXiv papers for accepted venues")

    sub.add_parser("quality-report", help="Generate full literature quality report")

    args = parser.parse_args()

    commands = {
        "score": cmd_score,
        "score-all": cmd_score_all,
        "classify-depth": cmd_classify_depth,
        "classify-depth-all": cmd_classify_depth_all,
        "upgrade-venues": cmd_upgrade_venues,
        "quality-report": cmd_quality_report,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

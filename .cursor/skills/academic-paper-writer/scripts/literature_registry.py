#!/usr/bin/env python3
"""Multi-source literature registry with SQLite cache.

Supports discovery and BibTeX retrieval from:
  - arXiv (Atom API)
  - PubMed (via pubmed_database skill)
  - OpenAlex (via literature_search_openalex skill)
  - Europe PMC (via literature_search_europepmc skill)
  - bioRxiv (via literature_search_biorxiv skill)

Design
------
The registry normalizes papers from all sources into a unified SQLite schema
with a ``source`` column. DOI-based cross-referencing removes duplicates.

For source-specific API wrappers, this module imports the corresponding
system-level skill scripts when available. If a source's script is not
installed, that source is gracefully unavailable.

CLI
---
    python literature_registry.py init [--db PATH]
    python literature_registry.py search <source> <query> [--max-results N] [--db PATH]
    python literature_registry.py search all <query> [--db PATH]
    python literature_registry.py export-bibtex <source> <source_id> [--bib PATH] [--db PATH]
    python literature_registry.py list-citations [--by-source] [--db PATH]
    python literature_registry.py list-searches [--db PATH]
    python literature_registry.py stats [--db PATH]
    python literature_registry.py cross-ref [--db PATH]
    python literature_registry.py verify-citation --doi <DOI> [--db PATH]
    python literature_registry.py verify-citation --title "<title>" [--author "<name>"]
    python literature_registry.py add-manual [--db PATH]  < data.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


_SCHEMA_VERSION = "2"


DEFAULT_DB_NAME = "literature-registry.sqlite3"


ARXIV_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


VALID_SOURCES = frozenset({"arxiv", "pubmed", "openalex", "europepmc", "biorxiv", "paper-search"})


def sha256_str(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")




# === Rate limiter for proactive API throttling ===
import threading

class RateLimiter:
    """Per-domain rate limiter for proactive API throttling."""
    _RATE_LIMITS = {"arxiv": 3.0, "pubmed": 1.0, "openalex": 0.5, "europepmc": 1.0, "biorxiv": 1.0, "paper-search": 0.5}
    def __init__(self):
        self._lock = threading.Lock()
        self._last_call = {}
    def wait(self, source: str) -> None:
        interval = self._RATE_LIMITS.get(source, 1.0)
        with self._lock:
            now = time.monotonic()
            if source in self._last_call:
                elapsed = now - self._last_call[source]
                if elapsed < interval:
                    time.sleep(interval - elapsed)
            self._last_call[source] = time.monotonic()

_rate_limiter = RateLimiter()

def fetch_url(url: str, *, timeout_s: int = 30, retries: int = 3) -> tuple[int | None, bytes]:
    """Fetch a URL with exponential backoff on 429 rate-limit responses."""
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "literature-registry/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return getattr(resp, "status", None), resp.read()
        except urllib.error.HTTPError as e:
            code = getattr(e, "code", None)
            body = e.read() if hasattr(e, "read") else b""
            if code == 429 and attempt < retries:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            return code, body
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(1)
                continue
            return None, b""
    return None, b""


def resolve_db_path(args: argparse.Namespace) -> Path:
    if getattr(args, "db", None):
        return Path(args.db).expanduser().resolve()
    project_dir = Path(getattr(args, "project_dir", None) or ".").expanduser().resolve()
    return project_dir / "notes" / DEFAULT_DB_NAME


# ---------------------------------------------------------------------------
# Backend: arXiv
# ---------------------------------------------------------------------------

def _normalize_arxiv_id(value: str) -> tuple[str, str]:
    raw = value.strip()
    raw = re.sub(r"^arxiv:\s*", "", raw, flags=re.IGNORECASE)
    for sep in ("?", "#"):
        if sep in raw:
            raw = raw.split(sep, 1)[0]
    raw = raw.rstrip("/")
    if "/abs/" in raw:
        raw = raw.split("/abs/", 1)[1]
    if "/pdf/" in raw:
        raw = raw.split("/pdf/", 1)[1]
    if raw.endswith(".pdf"):
        raw = raw[: -len(".pdf")]
    raw = raw.strip()
    base = re.sub(r"v\d+$", "", raw)
    return base, raw


def _arxiv_query_url(query: str, start: int, max_results: int) -> str:
    qs = {
        "search_query": query.strip(),
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    return f"https://export.arxiv.org/api/query?{urllib.parse.urlencode(qs)}"


def _parse_arxiv_feed(xml_bytes: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)

    def _text(el: ET.Element | None) -> str | None:
        if el is None or el.text is None:
            return None
        return " ".join(el.text.split())

    entries: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ARXIV_ATOM_NS):
        entry_id = _text(entry.find("atom:id", ARXIV_ATOM_NS)) or ""
        _, arxiv_id_v = _normalize_arxiv_id(entry_id)
        arxiv_id_base, _ = _normalize_arxiv_id(arxiv_id_v)

        doi = _text(entry.find("arxiv:doi", ARXIV_ATOM_NS))

        authors = []
        for author in entry.findall("atom:author", ARXIV_ATOM_NS):
            name = _text(author.find("atom:name", ARXIV_ATOM_NS))
            if name:
                authors.append(name)

        abs_url = None
        pdf_url = None
        for link in entry.findall("atom:link", ARXIV_ATOM_NS):
            href = (link.attrib.get("href") or "").strip()
            if not href:
                continue
            lt = (link.attrib.get("type") or "").strip()
            rel = (link.attrib.get("rel") or "").strip()
            if abs_url is None and rel == "alternate" and lt == "text/html":
                abs_url = href
            if pdf_url is None and lt == "application/pdf":
                pdf_url = href

        categories = []
        primary_category = None
        primary_el = entry.find("arxiv:primary_category", ARXIV_ATOM_NS)
        if primary_el is not None:
            primary_category = primary_el.attrib.get("term")
        for cat in entry.findall("atom:category", ARXIV_ATOM_NS):
            term = (cat.attrib.get("term") or "").strip()
            if term:
                categories.append(term)

        entries.append({
            "source": "arxiv",
            "source_id": arxiv_id_base,
            "title": _text(entry.find("atom:title", ARXIV_ATOM_NS)) or "",
            "summary": _text(entry.find("atom:summary", ARXIV_ATOM_NS)) or "",
            "published": _text(entry.find("atom:published", ARXIV_ATOM_NS)),
            "authors": authors,
            "doi": doi,
            "journal_ref": _text(entry.find("arxiv:journal_ref", ARXIV_ATOM_NS)),
            "primary_category": primary_category,
            "categories": categories,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
        })
    return entries


# ---------------------------------------------------------------------------
# Backend: OpenAlex (simplified, delegates to system skill when available)
# ---------------------------------------------------------------------------

def _search_openalex(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search OpenAlex works API."""
    base = "https://api.openalex.org/works"
    params = {
        "search": query,
        "per_page": str(min(max_results, 200)),
        "sort": "cited_by_count:desc",
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    status, body = fetch_url(url, timeout_s=30)
    if status != 200 or not body:
        print(f"  [openalex] HTTP {status or 'error'} for query: {query}", file=sys.stderr)
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []

    results: list[dict[str, Any]] = []
    for work in data.get("results", []):
        oa_id = (work.get("id") or "").rsplit("/", 1)[-1]
        if not oa_id:
            continue
        authors = [
            a.get("author", {}).get("display_name", "")
            for a in work.get("authorships", [])
            if a.get("author", {}).get("display_name")
        ]
        title = work.get("title") or ""
        results.append({
            "source": "openalex",
            "source_id": oa_id,
            "title": title.strip(),
            "summary": "",
            "published": work.get("publication_date"),
            "authors": authors,
            "doi": (work.get("doi") or "").lstrip("https://doi.org/"),
            "journal_ref": "",
            "primary_category": "",
            "categories": [c.get("display_name", "") for c in work.get("concepts", [])],
            "abs_url": work.get("primary_location", {}).get("landing_page_url", ""),
            "pdf_url": "",
        })
    return results


# ---------------------------------------------------------------------------
# Backend: Europe PMC
# ---------------------------------------------------------------------------

def _search_europepmc(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    base = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {
        "query": query,
        "pageSize": str(min(max_results, 100)),
        "format": "json",
        "resultType": "core",
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    status, body = fetch_url(url, timeout_s=30)
    if status != 200 or not body:
        print(f"  [europepmc] HTTP {status or 'error'}", file=sys.stderr)
        return []
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []

    results: list[dict[str, Any]] = []
    for item in data.get("resultList", {}).get("result", []):
        pmcid = item.get("pmcid", "")
        if not pmcid:
            continue
        authors = item.get("authorString", "")
        author_list = [a.strip() for a in authors.split(",") if a.strip()] if authors else []
        title = item.get("title") or ""
        doi = item.get("doi") or ""
        results.append({
            "source": "europepmc",
            "source_id": pmcid,
            "title": title.strip(),
            "summary": (item.get("abstractText") or "").strip(),
            "published": item.get("firstPublicationDate"),
            "authors": author_list,
            "doi": doi,
            "journal_ref": item.get("journalTitle") or "",
            "primary_category": "",
            "categories": item.get("meshLabels", "").split("; ") if item.get("meshLabels") else [],
            "abs_url": f"https://europepmc.org/article/PMC/{pmcid}",
            "pdf_url": "",
        })
    return results


# ---------------------------------------------------------------------------
# Backend: PubMed Entrez (simplified)
# ---------------------------------------------------------------------------

def _search_pubmed(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    base_search = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(min(max_results, 100)),
        "retmode": "json",
        "sort": "relevance",
    }
    url = f"{base_search}?{urllib.parse.urlencode(params)}"
    status, body = fetch_url(url, timeout_s=30)
    if status != 200 or not body:
        print(f"  [pubmed] search HTTP {status or 'error'}", file=sys.stderr)
        return []
    try:
        search_data = json.loads(body)
    except json.JSONDecodeError:
        return []
    id_list = search_data.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        return []

    ids = ",".join(id_list[:max_results])
    # Rate-limit delay between esearch and esummary (NCBI: 3 req/s without API key)
    time.sleep(1.0)
    fetch_url_str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    fetch_params = {"db": "pubmed", "id": ids, "retmode": "json"}
    fetch_query_url = f"{fetch_url_str}?{urllib.parse.urlencode(fetch_params)}"
    status2, body2 = fetch_url(fetch_query_url, timeout_s=30)
    if status2 != 200 or not body2:
        print(f"  [pubmed] fetch HTTP {status2 or 'error'}", file=sys.stderr)
        return []
    try:
        summary_data = json.loads(body2)
    except json.JSONDecodeError:
        return []

    results: list[dict[str, Any]] = []
    for pmid in id_list:
        info = summary_data.get("result", {}).get(pmid, {})
        if not info or "uid" not in info:
            continue
        authors = [a.get("name", "") for a in info.get("authors", []) if a.get("name")]
        title = info.get("title") or ""
        doi = ""
        for aid in info.get("articleids", []):
            if aid.get("idtype") == "doi":
                doi = aid.get("value", "")
                break
        results.append({
            "source": "pubmed",
            "source_id": pmid,
            "title": title.strip(),
            "summary": "",
            "published": info.get("pubdate", ""),
            "authors": authors,
            "doi": doi,
            "journal_ref": info.get("source", ""),
            "primary_category": "",
            "categories": [],
            "abs_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pdf_url": "",
        })
    return results


# ---------------------------------------------------------------------------
# System skill imports (optional, graceful fallback)
# ---------------------------------------------------------------------------
# When the corresponding system-level skill scripts are available, richer
# operations (full-text, citation graph, etc.) can be delegated to them.
# The inline search implementations above handle basic discovery.

_SKILL_PUBMED = None
_SKILL_OPENALEX = None
_SKILL_EUROPEPMC = None

try:
    _SKILLS_DIR = Path(os.environ.get(
        "CURSOR_SKILLS_DIR",
        os.path.expanduser("~/.cursor/skills"),
    ))
except Exception:
    _SKILLS_DIR = None

if _SKILLS_DIR and _SKILLS_DIR.exists():
    _pubmed_script = _SKILLS_DIR / "pubmed_database" / "scripts" / "pubmed_api.py"
    if _pubmed_script.exists():
        try:
            sys.path.insert(0, str(_pubmed_script.parent))
            import pubmed_api as _skill_pubmed
            _SKILL_PUBMED = _skill_pubmed
        except ImportError:
            pass

    _openalex_script = _SKILLS_DIR / "literature_search_openalex" / "scripts" / "openalex_cli.py"
    if _openalex_script.exists():
        try:
            sys.path.insert(0, str(_openalex_script.parent))
            import openalex_cli as _skill_openalex
            _SKILL_OPENALEX = _skill_openalex
        except ImportError:
            pass

    _europepmc_script = _SKILLS_DIR / "literature_search_europepmc" / "scripts" / "europepmc_api.py"
    if _europepmc_script.exists():
        try:
            sys.path.insert(0, str(_europepmc_script.parent))
            import europepmc_api as _skill_europepmc
            _SKILL_EUROPEPMC = _skill_europepmc
        except ImportError:
            pass


# ---------------------------------------------------------------------------
# Backend: bioRxiv
# ---------------------------------------------------------------------------

def _search_biorxiv(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search bioRxiv content-detail API.
    Without a date range, results may be limited. For broader biomedical
    preprint searches, Europe PMC or PubMed are recommended.
    """
    base = "https://api.biorxiv.org/details/biorxiv"
    # Try a recent 2-year window as default
    url = f"{base}/2023-01-01/2024-12-31/0/{max_results}"
    status, body = fetch_url(url, timeout_s=15)
    if status == 200 and body:
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return []

        collection = data.get("collection", [])
        if collection:
            results: list[dict[str, Any]] = []
            for item in collection:
                doi = item.get("doi", "")
                biorxiv_id = doi.replace("/", "_") or str(item.get("doi", ""))
                results.append({
                    "source": "biorxiv",
                    "source_id": biorxiv_id,
                    "title": item.get("title", "").strip(),
                    "summary": item.get("abstract", "").strip() if item.get("abstract") else "",
                    "published": item.get("date", ""),
                    "authors": [a.strip() for a in item.get("authors", "").split(";") if a.strip()],
                    "doi": doi,
                    "journal_ref": item.get("journal", ""),
                    "primary_category": item.get("category", ""),
                    "categories": [],
                    "abs_url": f"https://www.biorxiv.org/content/{doi}" if doi else "",
                    "pdf_url": "",
                })
            return results

    print(
        "  [biorxiv] No results from direct API. For broader biomedical preprint "
        "searches, use `search europepmc` or `search pubmed` instead.",
        file=sys.stderr,
    )
    return []


# ---------------------------------------------------------------------------


def _search_paper_search(query: str, max_results: int = 25) -> list[dict[str, Any]]:
    """Search using the paper-search CLI (supports 12+ sources: Crossref, OpenAlex, PubMed, arXiv, etc.)."""
    import subprocess
    import shutil as _shutil

    ps = _shutil.which("paper-search")
    if not ps:
        print("  [paper-search] CLI not found. Install with: brew install paper-search", file=sys.stderr)
        return []

    try:
        result = subprocess.run(
            [ps, "search", query, "--sources", "crossref,openalex", "--max-results", str(max_results), "--pretty"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0 or not result.stdout.strip():
            print(f"  [paper-search] No results or error (code {result.returncode})", file=sys.stderr)
            return []
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  [paper-search] Error: {e}", file=sys.stderr)
        return []

    results: list[dict[str, Any]] = []
    items = data.get("results", data) if isinstance(data, dict) else data
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title", "") or ""
            doi = item.get("doi", "") or ""
            source_id = doi.replace("/", "_") or hashlib.sha256(title.encode()).hexdigest()[:16]
            results.append({
                "source": "paper-search",
                "source_id": source_id,
                "title": str(title).strip(),
                "summary": str(item.get("abstract", item.get("summary", ""))).strip(),
                "published": str(item.get("published", item.get("year", ""))),
                "authors": [str(a).strip() for a in item.get("authors", [])] if isinstance(item.get("authors"), list) else [],
                "doi": doi,
                "journal_ref": str(item.get("journal", item.get("container_title", ""))),
                "primary_category": "",
                "categories": [str(c) for c in item.get("topics", item.get("categories", []))] if isinstance(item.get("topics", item.get("categories")), list) else [],
                "abs_url": str(item.get("url", item.get("landing_page_url", ""))),
                "pdf_url": "",
            })
    return results


# Source dispatcher
# ---------------------------------------------------------------------------

SOURCE_SEARCHERS = {
    "arxiv": lambda q, n: _parse_arxiv_feed(
        fetch_url(_arxiv_query_url(q, 0, n), timeout_s=30)[1]
    ) if fetch_url(_arxiv_query_url(q, 0, n), timeout_s=30)[0] == 200 else [],
    "openalex": _search_openalex,
    "europepmc": _search_europepmc,
    "pubmed": _search_pubmed,
    "biorxiv": _search_biorxiv,
    "paper-search": _search_paper_search,
}


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
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

        CREATE INDEX IF NOT EXISTS works_doi_idx ON works(doi) WHERE doi IS NOT NULL;
        CREATE INDEX IF NOT EXISTS works_source_idx ON works(source);

        CREATE TABLE IF NOT EXISTS searches (
            search_id INTEGER PRIMARY KEY,
            requested_at TEXT NOT NULL,
            source TEXT NOT NULL,
            query TEXT NOT NULL,
            url TEXT NOT NULL,
            total_results INTEGER,
            result_count INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS searches_source_query_idx
            ON searches(source, query, requested_at);

        CREATE TABLE IF NOT EXISTS search_results (
            search_id INTEGER NOT NULL REFERENCES searches(search_id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            work_id INTEGER REFERENCES works(work_id) ON DELETE SET NULL,
            PRIMARY KEY (search_id, position)
        );

        CREATE TABLE IF NOT EXISTS bibtex (
            work_id INTEGER PRIMARY KEY REFERENCES works(work_id) ON DELETE CASCADE,
            fetched_at TEXT NOT NULL,
            source_url TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            bibtex TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fetches (
            fetch_id INTEGER PRIMARY KEY,
            fetched_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            url TEXT NOT NULL,
            status INTEGER,
            sha256 TEXT,
            bytes INTEGER
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

        CREATE INDEX IF NOT EXISTS verifications_work_idx ON verifications(work_id);
    """)
    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value;",
        ("schema_version", _SCHEMA_VERSION),
    )
    conn.commit()


def _record_fetch(conn: sqlite3.Connection, *, kind: str, url: str, status: int | None, body: bytes) -> None:
    conn.execute(
        "INSERT INTO fetches(fetched_at, kind, url, status, sha256, bytes) VALUES(?, ?, ?, ?, ?, ?);",
        (now_iso(), kind, url, status, sha256_bytes(body) if body else None, len(body)),
    )


def upsert_work(conn: sqlite3.Connection, work: dict[str, Any]) -> int:
    now = now_iso()
    source = work["source"]
    source_id = work["source_id"]
    authors_json = json.dumps(work.get("authors") or [], ensure_ascii=False)
    categories_json = json.dumps(work.get("categories") or [], ensure_ascii=False)

    row = conn.execute(
        "SELECT work_id FROM works WHERE source = ? AND source_id = ?;",
        (source, source_id),
    ).fetchone()

    if row:
        work_id = row["work_id"]
        conn.execute(
            """UPDATE works SET title=?, summary=?, published=?, authors_json=?,
               doi=?, journal_ref=?, primary_category=?, categories_json=?,
               abs_url=?, pdf_url=?, last_seen_at=?
               WHERE work_id=?;""",
            (
                work["title"], work.get("summary"), work.get("published"),
                authors_json, work.get("doi"), work.get("journal_ref"),
                work.get("primary_category"), categories_json,
                work.get("abs_url"), work.get("pdf_url"), now, work_id,
            ),
        )
    else:
        cur = conn.execute(
            """INSERT INTO works(source, source_id, title, summary, published,
               authors_json, doi, journal_ref, primary_category, categories_json,
               abs_url, pdf_url, created_at, last_seen_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                source, source_id, work["title"], work.get("summary"),
                work.get("published"), authors_json, work.get("doi"),
                work.get("journal_ref"), work.get("primary_category"),
                categories_json, work.get("abs_url"), work.get("pdf_url"),
                now, now,
            ),
        )
        work_id = cur.lastrowid
    conn.commit()
    return work_id


def generate_citation_key(conn: sqlite3.Connection, work_id: int, work: dict[str, Any]) -> str:
    from datetime import datetime as dt

    authors = json.loads(work.get("authors_json", "[]"))
    first_author = authors[0] if authors else "unknown"
    last_name = first_author.split()[-1] if first_author else "unknown"
    last_name = re.sub(r"[^a-zA-Z]", "", last_name).lower() or "unknown"

    published = work.get("published") or ""
    year_match = re.search(r"(\d{4})", str(published))
    year = year_match.group(1) if year_match else str(dt.now().year)

    title = work.get("title", "")
    words = re.findall(r"[a-zA-Z]+", title.lower())
    first_word = words[0] if words else "untitled"
    first_word = first_word[:8]

    base_key = f"{last_name}{year}{first_word}"
    key = base_key
    counter = 0
    while True:
        existing = conn.execute(
            "SELECT 1 FROM citation_keys WHERE key = ?;", (key,)
        ).fetchone()
        if not existing:
            break
        counter += 1
        key = f"{base_key}{chr(96 + counter)}"

    conn.execute(
        """INSERT OR REPLACE INTO citation_keys(work_id, key, base_key, generated_at)
           VALUES(?, ?, ?, ?);""",
        (work_id, key, base_key, now_iso()),
    )
    conn.commit()
    return key


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_source(
    conn: sqlite3.Connection,
    source: str,
    query: str,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    if source not in SOURCE_SEARCHERS:
        print(f"Unknown source: {source}", file=sys.stderr)
        return []

    searcher = SOURCE_SEARCHERS[source]
    results = searcher(query, max_results)
    return results


def run_search(
    conn: sqlite3.Connection,
    source: str,
    query: str,
    max_results: int = 25,
) -> int:
    results = search_source(conn, source, query, max_results)
    if not results:
        print(f"0 results from {source} for: {query}")
        return 0

    url = f"{source}:{query}"
    now = now_iso()
    cur = conn.execute(
        """INSERT INTO searches(requested_at, source, query, url, total_results, result_count)
           VALUES(?, ?, ?, ?, ?, ?);""",
        (now, source, query, url, len(results), len(results)),
    )
    search_id = cur.lastrowid

    for i, work in enumerate(results):
        work_id = upsert_work(conn, work)
        conn.execute(
            """INSERT INTO search_results(search_id, position, source, source_id, work_id)
               VALUES(?, ?, ?, ?, ?);""",
            (search_id, i, work["source"], work["source_id"], work_id),
        )
    conn.commit()
    print(f"Cached {len(results)} results from {source} (search_id={search_id})")
    return search_id


# ---------------------------------------------------------------------------
# BibTeX
# ---------------------------------------------------------------------------

ARXIV_BIBTEX_URL = "https://export.arxiv.org/bibtex"


def _fetch_arxiv_bibtex(arxiv_id: str) -> str | None:
    url = f"{ARXIV_BIBTEX_URL}/{arxiv_id}"
    status, body = fetch_url(url, timeout_s=30)
    if status == 200 and body:
        return body.decode("utf-8", errors="replace")
    return None


def _build_bibtex(conn: sqlite3.Connection, work_id: int) -> str | None:
    """Build a minimal BibTeX entry from work metadata."""
    row = conn.execute(
        "SELECT source, source_id, title, published, authors_json, doi, journal_ref, abs_url FROM works WHERE work_id = ?;",
        (work_id,),
    ).fetchone()
    if not row:
        return None

    source = row["source"]
    source_id = row["source_id"]
    title = row["title"]
    published = row["published"] or ""
    authors = json.loads(row["authors_json"] or "[]")
    doi = row["doi"] or ""
    journal = row["journal_ref"] or ""
    abs_url = row["abs_url"] or ""

    year_match = re.search(r"(\d{4})", published)
    year = year_match.group(1) if year_match else ""

    author_str = " and ".join(authors) if authors else "{Unknown}"

    key = generate_citation_key(conn, work_id, dict(row))

    entry_type = "inproceedings" if source == "arxiv" else "article"
    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  title = {{{title}}},")
    lines.append(f"  author = {{{author_str}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if journal:
        lines.append(f"  journal = {{{journal}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if source == "arxiv":
        lines.append(f"  eprint = {{{source_id}}},")
        lines.append(f"  archivePrefix = {{arXiv}},")
    if abs_url:
        lines.append(f"  url = {{{abs_url}}},")
    lines.append("}")
    return "\n".join(lines)


def export_bibtex(
    conn: sqlite3.Connection,
    source: str,
    source_id: str,
    bib_path: Path | None = None,
) -> str | None:
    row = conn.execute(
        "SELECT work_id, source, source_id, title FROM works WHERE source = ? AND source_id = ?;",
        (source, source_id),
    ).fetchone()
    if not row:
        work = {
            "source": source,
            "source_id": source_id,
            "title": source_id,
            "authors": [],
        }
        work_id = upsert_work(conn, work)
    else:
        work_id = row["work_id"]

    bibtex = None
    if source == "arxiv":
        bibtex = _fetch_arxiv_bibtex(source_id)
    if bibtex is None:
        bibtex = _build_bibtex(conn, work_id)
    if bibtex is None:
        print(f"Could not generate BibTeX for {source}:{source_id}", file=sys.stderr)
        return None

    sha = sha256_str(bibtex)
    conn.execute(
        """INSERT OR REPLACE INTO bibtex(work_id, fetched_at, source_url, sha256, bibtex)
           VALUES(?, ?, ?, ?, ?);""",
        (work_id, now_iso(), f"{source}:{source_id}", sha, bibtex),
    )
    conn.commit()

    if bib_path:
        bib_path = bib_path.expanduser().resolve()
        existing = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
        if bibtex not in existing:
            with open(bib_path, "a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(bibtex + "\n")
        print(f"Appended BibTeX for {source}:{source_id} to {bib_path}")
    return bibtex


# ---------------------------------------------------------------------------
# Cross-referencing
# ---------------------------------------------------------------------------

def cross_ref_dois(conn: sqlite3.Connection) -> int:
    """Find works with duplicate DOIs across sources and merge metadata."""
    rows = conn.execute(
        """SELECT doi, COUNT(*) as cnt, GROUP_CONCAT(work_id) as ids
           FROM works WHERE doi IS NOT NULL AND doi != ''
           GROUP BY doi HAVING cnt > 1;"""
    ).fetchall()

    merged = 0
    for row in rows:
        ids = [int(x) for x in row["ids"].split(",")]
        if len(ids) < 2:
            continue
        keep = ids[0]
        for dup in ids[1:]:
            conn.execute(
                "UPDATE search_results SET work_id = ? WHERE work_id = ?;",
                (keep, dup),
            )
            conn.execute(
                "UPDATE citation_keys SET work_id = ? WHERE work_id = ?;",
                (keep, dup),
            )
            conn.execute("DELETE FROM bibtex WHERE work_id = ?;", (dup,))
            conn.execute("DELETE FROM works WHERE work_id = ?;", (dup,))
            merged += 1

    conn.commit()
    return merged


# ---------------------------------------------------------------------------
# Citation Verification (CrossRef DOI resolution)
# ---------------------------------------------------------------------------

CROSSREF_API = "https://api.crossref.org/works"


def _clean_doi(doi: str) -> str:
    """Normalize a DOI string: strip URL prefixes, whitespace, and lowercase."""
    raw = doi.strip()
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.IGNORECASE)
    return raw.strip().lower()


def verify_citation_by_doi(
    doi: str,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Verify that a DOI resolves to a real publication via CrossRef API.

    Args:
        doi: The DOI to verify (accepts full URL or bare DOI).
        conn: Optional SQLite connection to record the verification.

    Returns:
        A dict with keys:
          - status: 'pass' | 'fail' | 'error'
          - title: resolved title (if pass)
          - authors: list of resolved author names (if pass)
          - year: resolved publication year (if pass)
          - journal: resolved journal/venue (if pass)
          - doi: normalized DOI used in the query
          - error: error message (if fail/error)
          - method: 'crossref-doi'
    """
    normalized = _clean_doi(doi)
    if not normalized:
        return {
            "status": "fail",
            "doi": doi,
            "method": "crossref-doi",
            "error": "Empty or invalid DOI after normalization",
        }

    url = f"{CROSSREF_API}/{urllib.parse.quote(normalized, safe='')}"
    status_code, body = fetch_url(url, timeout_s=15, retries=2)

    result: dict[str, Any] = {
        "status": "error",
        "doi": normalized,
        "method": "crossref-doi",
    }

    if status_code != 200 or not body:
        result["error"] = f"CrossRef API returned HTTP {status_code or 'error'}"
        return result

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        result["error"] = f"Failed to parse CrossRef response: {e}"
        return result

    msg = data.get("message")
    if not msg:
        result["status"] = "fail"
        result["error"] = "DOI not found in CrossRef (no message in response)"
        return result

    # Extract resolved metadata
    title_list = msg.get("title", [])
    title = title_list[0] if title_list else None
    if not title:
        result["status"] = "fail"
        result["error"] = "DOI resolved but no title found"
        return result

    authors = []
    for author in msg.get("author", []):
        family = author.get("family", "")
        given = author.get("given", "")
        if family or given:
            authors.append(f"{given} {family}".strip())

    issued = msg.get("issued", {})
    date_parts = issued.get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

    container = msg.get("container-title", [])
    journal = container[0] if container else (msg.get("publisher", "") or None)
    if isinstance(journal, list):
        journal = journal[0] if journal else None

    result.update({
        "status": "pass",
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
    })

    # Check for retractions, corrections, and updates
    is_retracted = msg.get("is-retracted", False)
    update_to = msg.get("update-to", [])
    update_policy = msg.get("update-policy")

    if is_retracted:
        result["status"] = "fail"
        result["error"] = "Paper has been retracted"
        result["retraction_warning"] = (
            "This DOI has been marked as retracted. "
            "Do not cite. Search for a retraction notice for details."
        )
    elif update_to:
        update_dois = [
            u.get("DOI", "") for u in update_to
            if isinstance(u, dict) and u.get("DOI")
        ]
        if update_dois:
            result["retraction_warning"] = (
                f"Paper superseded by updated version(s): {', '.join(update_dois)}. "
                f"Consider citing the updated version instead."
            )
    elif update_policy and update_policy != "http://dx.doi.org/10.1007/12001":
        result["retraction_warning"] = (
            f"Paper has active update policy ({update_policy}). "
            "Check for corrections or updated versions."
        )

    return result


def verify_citation_by_title(
    title: str,
    author: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Verify a citation exists by searching CrossRef by title (+ optional author).

    This is a fallback method when a DOI is not available. It queries the
    CrossRef works API with a bibliographic search.

    Args:
        title: Full or partial paper title.
        author: Optional author name to narrow the search.
        conn: Optional SQLite connection to record the verification.

    Returns:
        Same dict structure as verify_citation_by_doi(), with method='crossref-title'.
    """
    params = {
        "query.bibliographic": title.strip(),
        "rows": "3",
    }
    if author:
        params["query.author"] = author.strip()

    qs = urllib.parse.urlencode(params)
    url = f"{CROSSREF_API}?{qs}"
    status_code, body = fetch_url(url, timeout_s=15, retries=2)

    result: dict[str, Any] = {
        "status": "error",
        "method": "crossref-title",
        "title_query": title,
        "author_query": author,
    }

    if status_code != 200 or not body:
        result["error"] = f"CrossRef API returned HTTP {status_code or 'error'}"
        return result

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        result["error"] = f"Failed to parse CrossRef response: {e}"
        return result

    items = data.get("message", {}).get("items", [])
    if not items:
        result["status"] = "fail"
        result["error"] = "No matching publications found for title query"
        return result

    # Return the best (first) match
    best = items[0]
    title_list = best.get("title", [])
    title_resolved = title_list[0] if title_list else None

    authors_resolved = []
    for a in best.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family or given:
            authors_resolved.append(f"{given} {family}".strip())

    issued = best.get("issued", {})
    date_parts = issued.get("date-parts", [[]])
    year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

    container = best.get("container-title", [])
    journal = container[0] if container else None
    if isinstance(journal, list):
        journal = journal[0] if journal else None

    doi = best.get("DOI")

    result.update({
        "status": "pass",
        "title": title_resolved,
        "authors": authors_resolved,
        "year": year,
        "journal": journal,
        "doi": doi,
        "match_count": len(items),
    })
    return result


def record_verification(
    conn: sqlite3.Connection,
    work_id: int | None,
    method: str,
    doi: str | None,
    status: str,
    resolved_title: str | None,
    resolved_authors: list[str] | None,
    resolved_year: str | None,
    resolved_journal: str | None,
    error_message: str | None,
) -> int:
    """Store a verification record in the database.

    Returns the verification_id of the new record.
    """
    now = now_iso()
    authors_json = json.dumps(resolved_authors or [], ensure_ascii=False)
    cur = conn.execute(
        """INSERT INTO verifications(
               work_id, verified_at, method, doi, status,
               resolved_title, resolved_authors_json,
               resolved_year, resolved_journal, error_message)
           VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
        (
            work_id, now, method, doi, status,
            resolved_title, authors_json,
            resolved_year, resolved_journal, error_message,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_verification_status(
    conn: sqlite3.Connection,
    work_id: int,
) -> dict[str, Any] | None:
    """Get the latest verification result for a work.

    Returns None if the work has never been verified.
    """
    row = conn.execute(
        """SELECT * FROM verifications
           WHERE work_id = ?
           ORDER BY verified_at DESC, verification_id DESC LIMIT 1;""",
        (work_id,),
    ).fetchone()
    if not row:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)
    print(f"Initialized registry at: {db_path}")
    conn.close()
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    sources: list[str]
    if args.source == "all":
        sources = [s for s in args.preferred_sources if s in SOURCE_SEARCHERS] if args.preferred_sources else list(SOURCE_SEARCHERS)
        if not sources:
            sources = ["openalex"]
    else:
        if args.source not in VALID_SOURCES:
            print(f"Unknown source: {args.source}. Valid: {', '.join(sorted(VALID_SOURCES))}", file=sys.stderr)
            conn.close()
            return 1
        sources = [args.source]

    for src in sources:
        try:
            run_search(conn, src, args.query, args.max_results)
        except Exception as exc:
            print(f"  [{src}] error: {exc}", file=sys.stderr)

    conn.close()
    return 0


def cmd_export_bibtex(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    # Gate enforcement: refuse export unless verified (can force override)
    must_be_verified = getattr(args, "must_be_verified", True)
    force = getattr(args, "force", False)

    if must_be_verified and not force:
        # Look up work_id and check verification status
        row = conn.execute(
            "SELECT work_id FROM works WHERE source = ? AND source_id = ?;",
            (args.source, args.source_id),
        ).fetchone()
        if row:
            status = get_verification_status(conn, row["work_id"])
            if status is None or status["status"] != "pass":
                conn.close()
                print(
                    "error: Citation not verified. "
                    "Run verify-citation --doi <DOI> first, or use --force to skip.",
                    file=sys.stderr,
                )
                return 1
            print(f"Verification check passed (verified {status['verified_at']}).")
        else:
            conn.close()
            print(
                "error: Work not found in registry. Cannot check verification status. "
                "Use --force to export anyway.",
                file=sys.stderr,
            )
            return 1

    bib_path = Path(args.bib) if args.bib else None
    result = export_bibtex(conn, args.source, args.source_id, bib_path)
    if result:
        if not bib_path:
            print(result)
    else:
        conn.close()
        return 1

    conn.close()
    return 0


def cmd_list_citations(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)

    sql = """
        SELECT ck.key, w.source, w.source_id, w.title, w.published, w.doi
        FROM citation_keys ck
        JOIN works w ON ck.work_id = w.work_id
        ORDER BY w.source, ck.key;
    """
    rows = conn.execute(sql).fetchall()
    if not rows:
        print("No citations in registry.")
    else:
        print(f"{'CITATION KEY':<32} {'SOURCE':<10} {'SOURCE ID':<24} TITLE")
        print("-" * 100)
        for r in rows:
            title = (r["title"] or "")[:50]
            print(f"{r['key']:<32} {r['source']:<10} {r['source_id']:<24} {title}")

    conn.close()
    return 0


def cmd_list_searches(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)

    rows = conn.execute(
        "SELECT search_id, requested_at, source, query, result_count FROM searches ORDER BY search_id DESC LIMIT 50;"
    ).fetchall()
    if not rows:
        print("No searches recorded.")
    else:
        for r in rows:
            print(f"[{r['search_id']:>4}] {r['requested_at']}  {r['source']:<10}  {r['result_count']:>3} results  {r['query'][:80]}")

    conn.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)

    total = conn.execute("SELECT COUNT(*) FROM works;").fetchone()[0]
    by_source = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM works GROUP BY source ORDER BY cnt DESC;"
    ).fetchall()
    with_bib = conn.execute(
        "SELECT COUNT(*) FROM bibtex;"
    ).fetchone()[0]
    with_doi = conn.execute(
        "SELECT COUNT(*) FROM works WHERE doi IS NOT NULL AND doi != '';"
    ).fetchone()[0]

    print(f"Total works:     {total}")
    print(f"With BibTeX:     {with_bib}")
    print(f"With DOI:        {with_doi}")
    print("By source:")
    for r in by_source:
        print(f"  {r['source']:<12} {r['cnt']:>5}")

    conn.close()
    return 0


def cmd_cross_ref(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    merged = cross_ref_dois(conn)
    print(f"Merged {merged} duplicate DOI entries across sources.")
    conn.close()
    return 0


def cmd_check_consistency(args: argparse.Namespace) -> int:
    """Compare verified CrossRef metadata against what would be exported to BibTeX.

    Detects discrepancies between the authoritative CrossRef record and the
    local registry metadata that _build_bibtex() would use.
    """
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    if args.doi:
        result = verify_citation_by_doi(args.doi, conn=conn)
    elif args.source and args.source_id:
        row = conn.execute(
            "SELECT work_id, doi, title FROM works WHERE source = ? AND source_id = ?;",
            (args.source, args.source_id),
        ).fetchone()
        if row and row["doi"]:
            result = verify_citation_by_doi(row["doi"], conn=conn)
        else:
            result = {
                "status": "error",
                "error": "No DOI found for this work; cannot run CrossRef consistency check",
            }
    else:
        conn.close()
        print("error: must provide --doi or --source + --source-id", file=sys.stderr)
        return 1

    if result["status"] != "pass":
        conn.close()
        print(f"Cannot check consistency: verification failed ({result.get('error', 'unknown')})")
        return 1

    # Now get what _build_bibtex would produce for this work
    crossref_metadata = {
        "title": result.get("title", ""),
        "authors": result.get("authors", []),
        "year": result.get("year", ""),
        "journal": result.get("journal", ""),
    }

    # Look up the work in the registry
    work_row = None
    if args.doi:
        work_row = conn.execute(
            "SELECT work_id, source, source_id, title, authors_json, published, journal_ref FROM works WHERE doi = ? LIMIT 1;",
            (result.get("doi", args.doi),),
        ).fetchone()

    discrepancies = []
    if work_row:
        registry_title = work_row["title"] or ""
        registry_authors = json.loads(work_row["authors_json"] or "[]")
        registry_journal = work_row["journal_ref"] or ""

        # Title comparison (normalize whitespace and case)
        norm = lambda s: re.sub(r"\s+", " ", s.strip().lower().rstrip("."))
        if norm(registry_title) != norm(crossref_metadata["title"]):
            discrepancies.append(
                f"Title mismatch:\n"
                f"    CrossRef: {crossref_metadata['title']}\n"
                f"    Registry: {registry_title}"
            )

        # First author comparison
        xref_first = crossref_metadata["authors"][0].split()[-1].lower() if crossref_metadata["authors"] else ""
        reg_first = (registry_authors[0] or "").split()[-1].lower() if registry_authors else ""
        if xref_first and reg_first and xref_first != reg_first:
            discrepancies.append(
                f"First author last name mismatch:\n"
                f"    CrossRef: {xref_first}\n"
                f"    Registry: {reg_first}"
            )

        # Year comparison
        reg_year = ""
        if work_row["published"]:
            ym = re.search(r"(\d{4})", str(work_row["published"]))
            reg_year = ym.group(1) if ym else ""
        if crossref_metadata["year"] and reg_year and crossref_metadata["year"] != reg_year:
            discrepancies.append(
                f"Year mismatch: CrossRef={crossref_metadata['year']}, Registry={reg_year}"
            )

        # Journal comparison
        if norm(registry_journal) != norm(crossref_metadata["journal"]):
            discrepancies.append(
                f"Journal mismatch:\n"
                f"    CrossRef: {crossref_metadata['journal']}\n"
                f"    Registry: {registry_journal}"
            )

        if not discrepancies:
            print("All metadata consistent between CrossRef and registry.")
            # Generate what BibTeX would look like vs what's ideal
            bibtex = _build_bibtex(conn, work_row["work_id"])
            print(f"\nBibTeX entry that would be exported:\n{bibtex}")
        else:
            print(f"\n{len(discrepancies)} DISCREPANCY(IES) FOUND:\n")
            for d in discrepancies:
                print(f"  - {d}\n")
            print("The BibTeX in ref.bib will use registry metadata, not CrossRef.")
            print("Consider re-searching with the verified title to get correct metadata.")
    else:
        print("Work not found in registry. Run search/export to add it first.")

    conn.close()
    return 1 if discrepancies else 0


def _record_verification_result(conn, result):
    """Persist verification result to database. Returns the result dict (may be updated)."""
    work_id = None
    if result.get("doi"):
        row = conn.execute(
            "SELECT work_id FROM works WHERE doi = ? LIMIT 1;",
            (result["doi"],),
        ).fetchone()
        if row:
            work_id = row["work_id"]

    record_verification(
        conn,
        work_id=work_id,
        method=result.get("method", "crossref-doi"),
        doi=result.get("doi"),
        status=result["status"],
        resolved_title=result.get("title"),
        resolved_authors=result.get("authors"),
        resolved_year=result.get("year"),
        resolved_journal=result.get("journal"),
        error_message=result.get("error"),
    )
    return result


def _print_verification_result(result):
    """Print verification result to stdout."""
    if result["status"] == "pass":
        print(f"\n  VERIFIED: {result['status'].upper()}")
        print(f"  Title:    {result.get('title', 'N/A')}")
        if result.get("authors"):
            print(f"  Authors:  {', '.join(result['authors'][:5])}"
                  f"{' ...' if len(result['authors']) > 5 else ''}")
        if result.get("year"):
            print(f"  Year:     {result['year']}")
        if result.get("journal"):
            print(f"  Journal:  {result['journal']}")
        if result.get("doi"):
            print(f"  DOI:      {result['doi']}")
        if result.get("match_count"):
            print(f"  Matches:  {result['match_count']}")
        if result.get("retraction_warning"):
            print(f"  WARNING:  {result['retraction_warning']}")
        print()
    else:
        print(f"\n  VERIFICATION FAILED")
        print(f"  Status: {result['status']}")
        print(f"  Error:  {result.get('error', 'Unknown error')}")
        if result.get('doi'):
            print(f"  DOI:    {result['doi']}")
        if result.get("retraction_warning"):
            print(f"  WARNING: {result['retraction_warning']}")
        print()


def _cascade_to_title(doi, conn):
    """Try title-based verification using metadata from the works table."""
    row = conn.execute(
        "SELECT title, authors_json FROM works WHERE doi = ? LIMIT 1;",
        (doi,),
    ).fetchone()
    if not row or not row["title"]:
        return None
    authors = json.loads(row["authors_json"] or "[]")
    first_author = authors[0] if authors else None
    return verify_citation_by_title(row["title"], author=first_author, conn=conn)


def cmd_verify_citation(args: argparse.Namespace) -> int:
    """Verify a citation by DOI, title+author, or manual confirmation.

    Auto-cascades from failed DOI to title search unless --no-cascade is set.
    Supports --manual for human-confirmed verification without API call.

    Results are persisted to the verifications table for audit trail
    and downstream enforcement (e.g., export-bibtex).
    """
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    # ── Manual mode: record human-confirmed pass ──
    if getattr(args, "manual", False):
        if not args.doi:
            conn.close()
            print("error: --manual requires --doi", file=sys.stderr)
            return 1
        result = {
            "status": "pass",
            "method": "manual",
            "doi": _clean_doi(args.doi) if args.doi else "",
            "title": getattr(args, "manual_title", None),
            "authors": [a.strip() for a in getattr(args, "manual_authors", "").split(",") if a.strip()] if getattr(args, "manual_authors", None) else [],
            "year": getattr(args, "manual_year", None),
            "journal": getattr(args, "manual_journal", None),
            "error": None,
        }
        _record_verification_result(conn, result)
        _print_verification_result(result)
        conn.close()
        return 0 if result["status"] == "pass" else 1

    # ── DOI mode (with auto-cascade) ──
    no_cascade = getattr(args, "no_cascade", False)
    if args.doi:
        result = verify_citation_by_doi(args.doi, conn=conn)
        _record_verification_result(conn, result)
        if result["status"] != "pass" and not no_cascade:
            print("  DOI verification failed — auto-cascading to title search...")
            cascade_result = _cascade_to_title(_clean_doi(args.doi), conn)
            if cascade_result and cascade_result["status"] == "pass":
                result = cascade_result
                _record_verification_result(conn, result)
                print("  Auto-cascade succeeded via title search.")
        _print_verification_result(result)
        # Extract metadata for prompt before closing connection
        doi_clean = _clean_doi(args.doi)
        fallback_title = ""
        fallback_authors = ""
        row = conn.execute(
            "SELECT title, authors_json FROM works WHERE doi = ? LIMIT 1;",
            (doi_clean,),
        ).fetchone()
        if row:
            fallback_title = row["title"] or ""
            authors = json.loads(row["authors_json"] or "[]")
            fallback_authors = ", ".join(authors[:3]) if authors else ""
        conn.close()

        if result["status"] == "pass":
            return 0

        # Auto-cascade also failed — prompt user for next action
        print()
        print("─" * 50)
        print("Both DOI and title verification failed.")
        print()
        print("Next actions:")
        print("  [m] Manual confirmation  — manually verify and record pass")
        print("  [f] Fact-driven re-search — find alternative paper for same claim")
        print("  [d] Discard               — accept failure, move on")
        print()
        choice = input("Choose [m/f/d]: ").strip().lower()
        print()
        if choice == "m":
            print("Run manual confirmation with:")
            print(f"  verify-citation --manual --doi \"{doi_clean}\" \\")
            if fallback_title:
                print(f"    --title \"{fallback_title[:80]}\" \\")
            if fallback_authors:
                print(f"    --authors \"{fallback_authors}\"")
            print()
            return 1
        elif choice == "f":
            print("Fact-driven re-search workflow:")
            print(f"  1. Locate @{{{doi_clean}}} in main.typ")
            print(f"  2. Extract the core factual claim")
            print(f"  3. Search: search all \"<fact-claim>\"")
            print(f"  4. Verify candidates, replace @key, update CSV")
            print()
            return 1
        else:
            print("Citation discarded. Mark as TODO or remove.")
            print()
            return 1

    # ── Title mode ──
    if args.title:
        result = verify_citation_by_title(args.title, author=args.author, conn=conn)
        _record_verification_result(conn, result)
        _print_verification_result(result)
        conn.close()
        return 0 if result["status"] == "pass" else 1

    conn.close()
    print("error: must provide --doi, --title, or --manual", file=sys.stderr)
    return 1


def cmd_verify_all(args: argparse.Namespace) -> int:
    """Batch-verify all unverified or failed citations in the registry.

    Scans the works table for entries that have no passing verification record,
    and runs verify-citation --doi on each. When a DOI is available, the
    auto-cascade to title search applies automatically.

    Use --limit to cap the number of verifications in one run.
    """
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    # Find works that need verification
    rows = conn.execute("""
        SELECT w.work_id, w.source, w.source_id, w.title, w.doi, w.authors_json
        FROM works w
        WHERE w.doi IS NOT NULL AND w.doi != ''
          AND w.work_id NOT IN (
            SELECT DISTINCT work_id FROM verifications
            WHERE work_id IS NOT NULL AND status = 'pass'
          )
        ORDER BY w.last_seen_at DESC
    """).fetchall()

    if not rows:
        print("All citations already verified.")
        conn.close()
        return 0

    limit = getattr(args, "limit", 0) or len(rows)
    count = min(limit, len(rows))
    print(f"Found {len(rows)} unverified citations. Verifying up to {count}...\n")

    passed = 0
    failed = 0
    for i, row in enumerate(rows[:count]):
        doi = row["doi"]
        title = row["title"]
        print(f"[{i+1}/{count}] {doi} — {title[:60]}...")
        result = verify_citation_by_doi(doi, conn=conn)
        _record_verification_result(conn, result)
        if result["status"] != "pass":
            cascade_result = _cascade_to_title(_clean_doi(doi), conn)
            if cascade_result and cascade_result["status"] == "pass":
                result = cascade_result
                _record_verification_result(conn, result)
                print("  Auto-cascade passed via title search.")
        if result["status"] == "pass":
            passed += 1
        else:
            failed += 1
        print()

    conn.commit()
    conn.close()
    print(f"Batch verification complete: {passed} passed, {failed} failed.")
    return 0 if failed == 0 else 1


def cmd_add_manual(args: argparse.Namespace) -> int:
    db_path = resolve_db_path(args)
    conn = connect(db_path)
    init_schema(conn)

    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        print("Expected a JSON object on stdin", file=sys.stderr)
        return 1

    work_id = upsert_work(conn, data)
    key = generate_citation_key(conn, work_id, data)
    print(f"Added {data['source']}:{data['source_id']} as work_id={work_id}, key={key}")
    conn.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Multi-source literature registry for academic paper writing."
    )
    parser.add_argument("--db", help="Path to SQLite database file")
    parser.add_argument("--project-dir", default=".", help="Project root directory (for default db path)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the registry database")

    sp_search = sub.add_parser("search", help="Search a literature source")
    sp_search.add_argument("source", help="Source name or 'all'")
    sp_search.add_argument("query", help="Search query string")
    sp_search.add_argument("--max-results", type=int, default=25, help="Maximum results (default: 25)")
    sp_search.add_argument("--preferred-sources", nargs="*", help="Sources to use when source='all'")

    sp_export = sub.add_parser("export-bibtex", help="Export BibTeX for a work")
    sp_export.add_argument("source", help="Source name")
    sp_export.add_argument("source_id", help="Source-specific identifier")
    sp_export.add_argument("--bib", help="Path to .bib file to append to")
    sp_export.add_argument("--must-be-verified", action="store_true", help="Refuse export unless citation passed verification")
    sp_export.add_argument("--force", action="store_true", help="Skip verification gate check (with --must-be-verified)")

    sub.add_parser("list-citations", help="List all cached citations")
    sub.add_parser("list-searches", help="List recent searches")
    sub.add_parser("stats", help="Show registry statistics")
    sub.add_parser("cross-ref", help="Merge duplicates by DOI")
    sp_check = sub.add_parser("check-consistency", help="Compare verified CrossRef metadata against registry BibTeX output")
    sp_check.add_argument("--doi", help="DOI to check")
    sp_check.add_argument("--source", help="Source name (alternative to --doi)")
    sp_check.add_argument("--source-id", help="Source-specific identifier (use with --source)")
    sp_verify = sub.add_parser("verify-citation", help="Verify a citation via CrossRef DOI or title lookup")
    sp_verify.add_argument("--doi", help="DOI to verify (e.g. 10.1234/example)")
    sp_verify.add_argument("--title", help="Paper title to search (fallback when no DOI)")
    sp_verify.add_argument("--author", help="Author name to narrow title search")
    sp_verify.add_argument("--no-cascade", action="store_true", help="Disable auto-cascade from DOI to title search")
    sp_verify.add_argument("--manual", action="store_true", help="Record a manual verification pass (requires --doi)")
    sp_verify.add_argument("--manual-title", help="Title for manual verification")
    sp_verify.add_argument("--manual-authors", help="Comma-separated authors for manual verification")
    sp_verify.add_argument("--manual-year", help="Year for manual verification")
    sp_verify.add_argument("--manual-journal", help="Journal for manual verification")
    sp_verify_all = sub.add_parser("verify-all", help="Batch-verify all unverified citations")
    sp_verify_all.add_argument("--limit", type=int, default=0, help="Max verifications per run (0 = unlimited)")
    sub.add_parser("add-manual", help="Add a work manually via stdin JSON")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "search": cmd_search,
        "export-bibtex": cmd_export_bibtex,
        "list-citations": cmd_list_citations,
        "list-searches": cmd_list_searches,
        "stats": cmd_stats,
        "cross-ref": cmd_cross_ref,
        "check-consistency": cmd_check_consistency,
        "verify-citation": cmd_verify_citation,
        "verify-all": cmd_verify_all,
        "add-manual": cmd_add_manual,
    }
    handler = commands.get(args.command)
    if handler:
        return handler(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

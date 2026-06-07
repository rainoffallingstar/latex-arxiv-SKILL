#!/usr/bin/env python3
"""Shared helpers for paper plan scripts (domain-agnostic).

Provides utilities for:
  - Typst and LaTeX detection and counting (citations, BibTeX entries)
  - Config loading (paper-config.yml)
  - Template resolution by domain and output format
  - Citation style detection
  - Slug/timestamp naming conventions
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")


def get_skill_root() -> Path:
    """Get the skill root directory."""
    return Path(__file__).resolve().parents[1]


def get_assets_dir() -> Path:
    """Get the assets directory."""
    return get_skill_root() / "assets"


def get_template_dir() -> Path:
    """Get the primary template directory (Typst templates)."""
    return get_assets_dir() / "template"


def get_latex_template_dir() -> Path:
    """Get the legacy LaTeX template directory."""
    return get_assets_dir() / "template" / "latex"


def get_typst_fragment_dir() -> Path:
    """Get the Typst fragment template directory (figures, tables, diagrams)."""
    return get_assets_dir() / "typst-templates"


def slugify(text: str) -> str:
    """Convert text to a slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:60] or "paper"


def validate_slug(slug: str) -> None:
    """Validate a slug format."""
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(
            "Invalid slug. Use lower-case, hyphen-delimited names (e.g., transformer-vision-review)."
        )


def validate_timestamp(timestamp: str) -> None:
    """Validate a timestamp format."""
    if not _TIMESTAMP_RE.match(timestamp):
        raise ValueError("Timestamp must be in YYYY-MM-DD_HH-mm-ss format.")


def now_timestamp() -> str:
    """Get current timestamp in plan format."""
    return datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S")


def now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_plan_filename(timestamp: str, slug: str) -> str:
    """Build a plan filename from timestamp and slug."""
    validate_timestamp(timestamp)
    validate_slug(slug)
    return f"{timestamp}-{slug}.md"


def build_issues_filename(timestamp: str, slug: str) -> str:
    """Build an issues filename from timestamp and slug."""
    validate_timestamp(timestamp)
    validate_slug(slug)
    return f"{timestamp}-{slug}.csv"


def format_yaml_value(value: str) -> str:
    """Format a value for YAML frontmatter."""
    if value is None:
        return ""
    needs_quotes = (
        not value
        or value.strip() != value
        or "\n" in value
        or any(ch in value for ch in (":", "#", "{", "}", "[", "]", ","))
    )
    if needs_quotes:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def check_latex_available() -> dict:
    """Check if LaTeX tools are available on the system."""
    tools = {
        "pdflatex": shutil.which("pdflatex"),
        "bibtex": shutil.which("bibtex"),
        "latexmk": shutil.which("latexmk"),
    }
    available = tools["pdflatex"] is not None and tools["bibtex"] is not None
    return {
        "available": available,
        "pdflatex": tools["pdflatex"],
        "bibtex": tools["bibtex"],
        "latexmk": tools["latexmk"],
        "recommended": "latexmk" if tools["latexmk"] else "pdflatex+bibtex" if available else None,
    }


def check_typst_available() -> dict:
    """Check if Typst compiler is available on the system."""
    typst_path = shutil.which("typst")
    pandoc_path = shutil.which("pandoc")
    available = typst_path is not None
    return {
        "available": available,
        "typst": typst_path,
        "pandoc": pandoc_path,
    }


def check_compiler_available(output_format: str = "typst") -> dict:
    """Check if the compiler for the given output format is available."""
    if output_format == "typst":
        result = check_typst_available()
        result["compiler"] = "typst"
        return result
    else:
        result = check_latex_available()
        result["compiler"] = "latex"
        return result


def count_citations(source_path: Path) -> dict:
    """Count citations in a source file (supports Typst @key and LaTeX \\cite{}).

    Auto-detects format from file extension.
    """
    if not source_path.exists():
        return {"total": 0, "unique": 0, "keys": []}

    content = source_path.read_text(encoding="utf-8")

    if source_path.suffix == ".typ":
        # Typst: @citation-key syntax
        cite_matches = re.findall(r'@([a-zA-Z][a-zA-Z0-9_\-:]*)', content)
        unique_keys = sorted(set(cite_matches))
        return {
            "total": len(cite_matches),
            "unique": len(unique_keys),
            "keys": unique_keys,
        }

    # LaTeX: \cite{key1,key2} and natbib variants
    cite_matches = re.findall(
        r"\\(?:cite|citep|citet|citealt|citealp|citenum)\{([^}]+)\}",
        content,
    )
    all_keys = []
    for match in cite_matches:
        keys = [k.strip() for k in match.split(",")]
        all_keys.extend(keys)
    unique_keys = sorted(set(all_keys))
    return {
        "total": len(all_keys),
        "unique": len(unique_keys),
        "keys": unique_keys,
    }


def count_bibtex_entries(bib_path: Path) -> dict:
    """Count entries in a BibTeX file."""
    if not bib_path.exists():
        return {"total": 0, "by_year": {}, "keys": []}

    content = bib_path.read_text(encoding="utf-8")

    entry_matches = re.findall(r"@\w+\{([^,]+),", content)
    keys = [k.strip() for k in entry_matches]

    year_matches = re.findall(r"year\s*=\s*\{?(\d{4})\}?", content, re.IGNORECASE)
    by_year = {}
    for year in year_matches:
        by_year[year] = by_year.get(year, 0) + 1

    return {
        "total": len(keys),
        "by_year": by_year,
        "keys": sorted(keys),
    }


# ---------------------------------------------------------------------------
# Config-aware helpers
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = {
    "output_format": "typst",
    "template_class": "article",
    "citation_style": "author-year",
    "preferred_sources": ["openalex", "paper-search"],
    "domain": "general",
    "section_framework": [
        "Introduction",
        "Background and Related Work",
        "Core Approaches and Methods",
        "Key Challenges and Open Problems",
        "Future Directions",
        "Conclusion",
    ],
}


def load_config(config_path: Path | str) -> dict[str, Any]:
    """Load a paper-config.yml file.

    Falls back to _DEFAULT_CONFIG if the file is missing or unreadable.
    """
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        print(f"Config not found ({path}), using defaults.")
        return dict(_DEFAULT_CONFIG)

    if yaml is None:
        print("PyYAML not installed, using defaults.")
        return dict(_DEFAULT_CONFIG)

    try:
        with open(path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh)
        if not isinstance(config, dict):
            print(f"warning: Invalid config format in {path} (expected YAML mapping), using defaults.")
            return dict(_DEFAULT_CONFIG)
        return config
    except ImportError:
        print(f"warning: PyYAML not installed, cannot load config from {path}, using defaults.")
        return dict(_DEFAULT_CONFIG)
    except (yaml.YAMLError, OSError) as e:
        print(f"warning: Failed to load config from {path}: {e}. Using defaults.")
        return dict(_DEFAULT_CONFIG)


def detect_citation_style(source_path: Path) -> str:
    """Detect citation style from a source file.

    Supports Typst (.typ) and LaTeX (.tex) files.
    Returns 'ieee' or 'author-year'.
    """
    if not source_path.exists():
        return "ieee"

    content = source_path.read_text(encoding="utf-8")

    if source_path.suffix == ".typ":
        # Typst: check bibliography style
        if 'style: "apa.csl"' in content or 'style: "apa"' in content:
            return "author-year"
        if 'style: "ieee.csl"' in content or 'style: "ieee"' in content:
            return "ieee"
        # Default for Typst: check if natbib-equivalent
        return "author-year"

    # LaTeX
    natbib_active = bool(re.search(
        r"\\usepackage(?:\[.*?\])?\{natbib\}",
        content,
    ))
    cite_active = bool(re.search(
        r"\\usepackage\{cite\}",
        content,
    ))

    if natbib_active and not cite_active:
        return "author-year"
    return "ieee"


def get_template_for_domain(
    domain: str,
    output_format: str = "typst",
    citation_style: str = "author-year",
) -> tuple[str, str]:
    """Return (template_filename, document_class) for a given domain and format.

    Args:
        domain: Academic domain (biomedical, computer-science, physics, etc.)
        output_format: 'typst', 'latex', or 'markdown'
        citation_style: 'ieee' or 'author-year'

    Returns:
        (template_file_name, document_class)
    """
    try:
        from paper_config import get_domain_config
        cfg = get_domain_config(domain)
        tclass = cfg.get("template_class", "article")
    except ImportError:
        tclass = "article"

    ext = ".typ" if output_format in ("typst", "markdown") else ".tex"

    if output_format == "latex":
        if domain in ("biomedical", "medical", "life-sciences", "biology", "medicine"):
            return ("main-biomedical.template.tex", "article")
        _tmpl_map = {
            "IEEEtran": "main.template.tex",
            "article": "main-article.template.tex",
        }
        tname = _tmpl_map.get(tclass, "main-article.template.tex")
        return (tname, tclass)

    # Typst (primary)
    if tclass == "biomedical" or domain in ("biomedical", "medical", "life-sciences", "biology", "medicine"):
        return ("main-biomedical.template.typ", "article")
    if tclass == "IEEEtran":
        return ("main.template.typ", "IEEEtran")
    return ("main.template.typ", tclass)


def resolve_registry_db_path(project_dir: Path | str) -> Path:
    """Get the default path for the literature-registry.sqlite3 database."""
    return Path(project_dir) / "notes" / "literature-registry.sqlite3"


# ---------------------------------------------------------------------------
# Tool availability checks
# ---------------------------------------------------------------------------

_TOOL_HINTS = {
    "typst": "Install with: brew install typst  (https://typst.app)",
    "pdflatex": "Install with: brew install --cask mactex  or  apt install texlive",
    "bibtex": "Install with: brew install --cask mactex  or  apt install texlive",
    "pandoc": "Install with: brew install pandoc  or  apt install pandoc",
    "gemini": "Install Gemini CLI and run gemini_bridge.py via collaborating-with-gemini skill",
    "claude": "Install Claude Code CLI and run claude_bridge.py via collaborating-with-claude skill",
}


def check_tool(command: str) -> bool:
    """Check if a command-line tool is available.

    Prints a clear install hint if not found.

    Returns:
        True if the tool is available, False otherwise.
    """
    path = shutil.which(command)
    if path is None:
        hint = _TOOL_HINTS.get(command, f"Please install '{command}' to use this feature.")
        print(f"Warning: '{command}' not found. {hint}", file=sys.stderr)
        return False
    return True


def check_required_tools(tools: list[str]) -> bool:
    """Check all required tools and return True only if all are available.

    Prints warnings for each missing tool.
    """
    all_ok = True
    for tool in tools:
        if not check_tool(tool):
            all_ok = False
    return all_ok

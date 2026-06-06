#!/usr/bin/env python3
"""Iterative review gap analysis for academic paper writing.

Scans main.tex (or main.typ) to identify coverage gaps by section,
classifying them as P0 (critical/missing), P1 (recommended/shallow),
or P2 (optional/refinement). Tracks round-over-round citation growth.

CLI
---
    python3 review_gaps.py --project-dir <dir> --round <N> [--output <file>]
    python3 review_gaps.py --project-dir <dir> --history
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Defaults (overridable via paper-config.yml)
# ---------------------------------------------------------------------------

DEFAULT_MIN_CITATIONS_PER_SECTION = 8
# Sections with fewer citations than this are candidate P0 gaps.


# ---------------------------------------------------------------------------
# Source parsing
# ---------------------------------------------------------------------------

def _find_source_file(project_dir: Path) -> Path | None:
    """Find main.tex or main.typ in the project directory."""
    for name in ("main.typ", "main.tex"):
        candidate = project_dir / name
        if candidate.exists():
            return candidate
    return None


def parse_sections(source_path: Path) -> list[dict]:
    """Extract section headings and their citation counts from a .tex/.typ file.

    Returns a list of dicts with keys: title, start_line, end_line,
    citation_count, unique_citations, paragraph_count, char_count.
    """
    content = source_path.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    is_typst = source_path.suffix == ".typ"

    if is_typst:
        section_pattern = re.compile(r"^\s*=\s+(.+)$", re.MULTILINE)
        cite_pattern = re.compile(r"@([a-zA-Z][a-zA-Z0-9_\-:]*)")
    else:
        section_pattern = re.compile(
            r'\\(?:section|subsection|subsubsection)\{([^}]+)\}',
            re.MULTILINE,
        )
        cite_pattern = re.compile(
            r'\\(?:cite|citep|citet|citealt|citealp|citenum)\{([^}]+)\}',
        )

    # Find all section boundaries
    section_boundaries = []
    for m in section_pattern.finditer(content):
        section_boundaries.append((m.start(), m.group(1).strip()))

    if not section_boundaries:
        return []

    sections = []
    for i, (start_pos, title) in enumerate(section_boundaries):
        end_pos = (
            section_boundaries[i + 1][0]
            if i + 1 < len(section_boundaries)
            else len(content)
        )
        section_text = content[start_pos:end_pos]

        # Count citations
        unique_keys: set[str] = set()
        total_usages = 0
        for m in cite_pattern.finditer(section_text):
            if is_typst:
                unique_keys.add(m.group(1))
                total_usages += 1
            else:
                for k in m.group(1).split(","):
                    k = k.strip()
                    if k:
                        unique_keys.add(k)
                        total_usages += 1

        # Count paragraphs (non-empty lines)
        sec_lines = section_text.split("\n")
        paragraph_count = sum(1 for line in sec_lines if line.strip() and not line.strip().startswith("%"))

        sections.append({
            "title": title,
            "citation_count": len(unique_keys),
            "citation_usages": total_usages,
            "char_count": len(section_text),
            "paragraph_count": paragraph_count,
        })

    return sections


# ---------------------------------------------------------------------------
# Gap classification
# ---------------------------------------------------------------------------

def classify_gaps(
    sections: list[dict],
    *,
    min_citations: int = DEFAULT_MIN_CITATIONS_PER_SECTION,
    expected_keywords: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Classify each section into P0, P1, P2, or OK based on coverage metrics.

    Args:
        sections: List of parsed section dicts from parse_sections().
        min_citations: Minimum expected citations per section.
        expected_keywords: Optional dict mapping section title (substring match)
            to list of expected keywords that should appear.

    Returns:
        List of gap dicts with keys: priority, section, issue, est_work,
        impact, citation_count, min_expected.
    """
    gaps: list[dict] = []

    for sec in sections:
        title = sec["title"]
        cite_count = sec["citation_count"]
        para_count = sec["paragraph_count"]

        # P0: Section has critically low citations or no citations
        if cite_count < min_citations:
            severity = "critical" if cite_count < 4 else "low"
            gaps.append({
                "priority": "P0",
                "section": title,
                "issue": (
                    f"Section has only {cite_count} verified citations "
                    f"(minimum expected: {min_citations})"
                ),
                "est_work": "2-4 paragraphs of supplementary content",
                "impact": (
                    f"Core dimension under-covered — {severity} citation density"
                ),
                "citation_count": cite_count,
                "min_expected": min_citations,
                "paragraph_count": para_count,
            })
            continue

        # Check for expected keyword coverage
        if expected_keywords:
            for sec_pattern, keywords in expected_keywords.items():
                if sec_pattern.lower() in title.lower():
                    # Cannot check without the actual section text here;
                    # the keyword check is done at a higher level
                    pass

        # P1: Citation count is borderline (within 50% above minimum)
        if cite_count < min_citations * 1.5:
            gaps.append({
                "priority": "P1",
                "section": title,
                "issue": (
                    f"Section has {cite_count} citations — meets minimum "
                    f"({min_citations}) but lacks depth for a review"
                ),
                "est_work": "1-2 paragraphs of supplementary content",
                "impact": "Significant quality gain from additional depth",
                "citation_count": cite_count,
                "min_expected": min_citations,
                "paragraph_count": para_count,
            })
            continue

        # P2: Section is well-covered but could be refined
        if cite_count >= min_citations * 1.5 and para_count < 8:
            gaps.append({
                "priority": "P2",
                "section": title,
                "issue": (
                    f"Section has adequate citations ({cite_count}) but "
                    f"only {para_count} paragraphs — may benefit from expansion"
                ),
                "est_work": "Optional 1-2 paragraphs",
                "impact": "Refinement and polish",
                "citation_count": cite_count,
                "min_expected": min_citations,
                "paragraph_count": para_count,
            })

    return gaps


# ---------------------------------------------------------------------------
# Round history tracking
# ---------------------------------------------------------------------------

HISTORY_FILE = "review-history.json"


def load_history(project_dir: Path) -> list[dict]:
    """Load the review round history from a JSON file."""
    history_path = project_dir / "notes" / HISTORY_FILE
    if not history_path.exists():
        return []
    try:
        with open(history_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_history(project_dir: Path, history: list[dict]) -> None:
    """Save the review round history to a JSON file."""
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    history_path = notes_dir / HISTORY_FILE
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def record_round(
    project_dir: Path,
    round_num: int,
    total_citations: int,
    sections: list[dict],
    gaps: list[dict],
) -> None:
    """Record a review round in the history file."""
    history = load_history(project_dir)
    entry = {
        "round": round_num,
        "total_citations": total_citations,
        "section_count": len(sections),
        "sections": [
            {"title": s["title"], "citations": s["citation_count"]}
            for s in sections
        ],
        "gaps": [
            {"priority": g["priority"], "section": g["section"], "issue": g["issue"]}
            for g in gaps
        ],
        "p0_count": sum(1 for g in gaps if g["priority"] == "P0"),
        "p1_count": sum(1 for g in gaps if g["priority"] == "P1"),
        "p2_count": sum(1 for g in gaps if g["priority"] == "P2"),
    }
    history.append(entry)
    save_history(project_dir, history)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_gap_table(gaps: list[dict], round_num: int) -> str:
    """Format the gap table as a markdown string."""
    lines = [f"## Round {round_num} Gap Analysis", ""]

    # Summary metrics
    p0 = sum(1 for g in gaps if g["priority"] == "P0")
    p1 = sum(1 for g in gaps if g["priority"] == "P1")
    p2 = sum(1 for g in gaps if g["priority"] == "P2")

    lines.append(f"- P0 (critical): {p0}")
    lines.append(f"- P1 (recommended): {p1}")
    lines.append(f"- P2 (optional): {p2}")
    lines.append("")

    if not gaps:
        lines.append("No gaps detected. All sections meet coverage thresholds.")
        lines.append("")
        return "\n".join(lines)

    # Gap table
    lines.extend([
        "| Priority | Section | Issue | Est. Work | Impact | Cites |",
        "|---|---|---|---|---|---|",
    ])

    for g in sorted(gaps, key=lambda x: (0 if x["priority"] == "P0" else 1 if x["priority"] == "P1" else 2)):
        lines.append(
            f"| {g['priority']} | {g['section']} | {g['issue']} | "
            f"{g['est_work']} | {g['impact']} | {g['citation_count']}/{g['min_expected']} |"
        )

    lines.append("")

    # Auto-fix guidance
    lines.append("### Auto-Fix Guidance")
    lines.append(f"- P0 gaps ({p0}): **must be fixed** before proceeding to Phase 2.5")
    lines.append(f"- P1 gaps ({p1}): recommended fix; ask user before proceeding")
    lines.append(f"- P2 gaps ({p2}): optional; user may skip")
    lines.append("")

    return "\n".join(lines)


def format_round_delta(history: list[dict]) -> str:
    """Format a round-over-round citation growth summary."""
    if len(history) < 2:
        return ""

    lines = ["### Round-over-Round Citation Growth", ""]
    lines.append("| Round | Total Cites | Delta | P0 | P1 | P2 | Sections |")
    lines.append("|---|---|---|---|---|---|---|")

    for i, entry in enumerate(history):
        delta = ""
        if i > 0:
            prev = history[i - 1]["total_citations"]
            diff = entry["total_citations"] - prev
            delta = f"+{diff}" if diff > 0 else str(diff)

        lines.append(
            f"| R{entry['round']} | {entry['total_citations']} | {delta} | "
            f"{entry['p0_count']} | {entry['p1_count']} | {entry['p2_count']} | "
            f"{entry['section_count']} |"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_analyze(args: argparse.Namespace) -> int:
    """Run gap analysis for a given round."""
    project_dir = Path(args.project_dir).resolve()
    source_path = _find_source_file(project_dir)
    if source_path is None:
        print("error: no main.tex or main.typ found in project directory", file=sys.stderr)
        return 1

    round_num = args.round or 1

    sections = parse_sections(source_path)
    if not sections:
        print("No sections found in source file.")
        return 1

    total_citations = sum(s["citation_count"] for s in sections)

    min_cit = getattr(args, "min_citations", None) or DEFAULT_MIN_CITATIONS_PER_SECTION

    gaps = classify_gaps(sections, min_citations=min_cit)

    # Record round
    record_round(project_dir, round_num, total_citations, sections, gaps)

    # Format output
    output = []
    output.append("")
    output.append(f"=== Round {round_num} Review ===")
    output.append(f"Source: {source_path.name}")
    output.append(f"Total sections: {len(sections)}")
    output.append(f"Total unique citations: {total_citations}")
    output.append("")

    # Per-section citation breakdown
    output.append("### Section Citation Breakdown")
    output.append("")
    output.append("| Section | Citations | Usages | Paragraphs |")
    output.append("|---|---|---|---|")
    for s in sections:
        output.append(
            f"| {s['title']} | {s['citation_count']} | "
            f"{s['citation_usages']} | {s['paragraph_count']} |"
        )
    output.append("")

    # Gap table
    output.append(format_gap_table(gaps, round_num))

    # Round history
    history = load_history(project_dir)
    delta_summary = format_round_delta(history)
    if delta_summary:
        output.append(delta_summary)

    # Maturity assessment
    p0_count = sum(1 for g in gaps if g["priority"] == "P0")
    p1_count = sum(1 for g in gaps if g["priority"] == "P1")
    output.append("### Maturity Assessment")
    if p0_count == 0 and p1_count == 0:
        output.append("All sections meet coverage thresholds.")
        output.append("Recommendation: **proceed to Phase 2.5 (Rhythm Refinement)**.")
    elif p0_count > 0:
        output.append(f"{p0_count} critical gaps remain.")
        output.append("Recommendation: **fix P0 gaps before proceeding.**")
    else:
        output.append(f"No P0 gaps. {p1_count} recommended improvements remain.")
        output.append("Recommendation: **ask user whether to fix P1 gaps or proceed.**")
    output.append("")

    full_output = "\n".join(output)
    print(full_output)

    # Write to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_output, encoding="utf-8")
        print(f"Review output written to: {output_path}")

    return 1 if p0_count > 0 else 0


def cmd_history(args: argparse.Namespace) -> int:
    """Display round-over-round review history."""
    project_dir = Path(args.project_dir).resolve()
    history = load_history(project_dir)
    if not history:
        print("No review history found.")
        return 0

    print(format_round_delta(history))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Iterative review gap analysis for academic papers."
    )
    parser.add_argument(
        "--project-dir", default=".",
        help="Project directory containing main.tex/main.typ",
    )

    sub = parser.add_subparsers(dest="command")

    sp_analyze = sub.add_parser("analyze", help="Run gap analysis for a review round")
    sp_analyze.add_argument("--round", type=int, default=1, help="Review round number")
    sp_analyze.add_argument("--min-citations", type=int, help="Override minimum citations per section")
    sp_analyze.add_argument("--output", help="Write output to file")

    sp_history = sub.add_parser("history", help="Show round-over-round citation growth")

    args = parser.parse_args()

    if args.command == "analyze":
        return cmd_analyze(args)
    if args.command == "history":
        return cmd_history(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate paper issues CSV schema and required fields.

Also supports --sync to count actual citations per section from main.typ or main.tex
and update the Verified_Citations column.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = [
    "ID",
    "Phase",
    "Title",
    "Description",
    "Target_Citations",
    "Visualization",
    "Acceptance",
    "Status",
    "Verified_Citations",
    "Sources",
    "Notes",
]

ALLOWED_STATUS = {"TODO", "DOING", "DONE", "SKIP"}
ALLOWED_PHASES = {"Research", "Writing", "Extension", "Refinement", "QA"}
ALLOWED_SOURCES = {"arxiv", "pubmed", "openalex", "europepmc", "biorxiv", "paper-search"}


def fail(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 1


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def count_citations_by_section(tex_path: Path) -> dict[str, int]:
    """Scan a .typ or .tex file and count unique citation keys per section.

    Returns a dict mapping section title -> unique citation count.
    Also supports Typst @citation_key syntax.
    """
    if not tex_path.exists():
        print(f"warning: {tex_path} not found", file=sys.stderr)
        return {}

    content = tex_path.read_text(encoding="utf-8")

    # Find section boundaries and their citation counts
    section_pattern = re.compile(
        r'\\(?:section|subsection|subsubsection)\{([^}]+)\}',
        re.MULTALLINE,
    )

    sections = []
    for m in section_pattern.finditer(content):
        sections.append((m.start(), m.group(1).strip()))

    if not sections:
        return {}

    # Add end-of-file as final boundary
    sections.append((len(content), "__END__"))

    result: dict[str, int] = {}
    # Support both LaTeX \cite{key1,key2} and Typst @key1, @key2
    cite_pattern = re.compile(r'\\(?:cite|citep|citet|citealt|citealp|citenum)\{([^}]+)\}')
    typst_cite_pattern = re.compile(r'@([a-zA-Z][a-zA-Z0-9_\-:]*)')

    for i in range(len(sections) - 1):
        start_pos = sections[i][0]
        end_pos = sections[i + 1][0]
        section_title = sections[i][1]
        section_text = content[start_pos:end_pos]

        keys: set[str] = set()

        # LaTeX citations
        for m in cite_pattern.finditer(section_text):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    keys.add(k)

        # Typst citations
        for m in typst_cite_pattern.finditer(section_text):
            keys.add(m.group(1))

        result[section_title] = len(keys)

    return result


def sync_issues(
    csv_path: Path,
    tex_path: Path | None = None,
    dry_run: bool = False,
) -> int:
    """Update Verified_Citations in the issues CSV from actual source content.

    Reads the CSV, scans main.typ (or main.tex) for citation counts per section, and
    updates rows whose title matches a section heading.

    Returns 0 on success, 1 on error.
    """
    if not csv_path.exists():
        return fail(f"CSV not found: {csv_path}")

    # Auto-detect main.typ in the project
    if tex_path is None:
        project_dir = csv_path.parent.parent
        tex_path = project_dir / "main.typ"
        # Also check for LaTeX
        if not tex_path.exists():
            tex_path = project_dir / "main.tex"

    section_citations = count_citations_by_section(tex_path)
    if not section_citations:
        print("No sections found in source file; nothing to sync.")
        return 0

    # Read CSV
    rows = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append(row)

    if len(rows) < 2:
        return fail("CSV has no data rows")

    header = rows[0]
    if header != REQUIRED_COLUMNS:
        return fail("CSV header mismatch; cannot sync")

    # Build section name -> citation count lookup
    # Also try partial matching (issue title may contain section heading)
    citation_lookup: dict[str, int] = {}
    for sec_title, count in section_citations.items():
        citation_lookup[sec_title.lower()] = count

    updated = 0
    for i in range(1, len(rows)):
        row_data = dict(zip(REQUIRED_COLUMNS, rows[i]))
        issue_title = row_data["Title"].strip().lower()
        current_verified = row_data["Verified_Citations"].strip()

        actual_count = None
        # Try exact match first, then partial match
        if issue_title in citation_lookup:
            actual_count = citation_lookup[issue_title]
        else:
            for sec_title, count in section_citations.items():
                if sec_title.lower() in issue_title or issue_title in sec_title.lower():
                    actual_count = count
                    break

        if actual_count is not None:
            if current_verified != str(actual_count):
                if dry_run:
                    print(f"  [{row_data['ID']}] {row_data['Title']}: {current_verified} -> {actual_count}")
                else:
                    rows[i][8] = str(actual_count)
                updated += 1

    if updated == 0:
        print("All citation counts already in sync.")
        return 0

    if dry_run:
        print(f"\nDry run: {updated} row(s) would be updated.")
        return 0

    # Write back
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)

    print(f"Synced {updated} row(s) with actual citation counts from {tex_path.name}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return fail("usage: validate_paper_issues.py <issues.csv> [--strict] [--sync [--dry-run]] [--tex <path>] [--resume]")

    # Handle --sync before the CSV path
    args = sys.argv[1:]
    sync_mode = False
    dry_run = False
    tex_path = None
    csv_arg = None
    resume_mode = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--sync":
            sync_mode = True
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--resume":
            resume_mode = True
        elif arg == "--tex" and i + 1 < len(args):
            i += 1
            tex_path = Path(args[i])
        elif arg == "--strict":
            pass  # handled later
        elif not arg.startswith("--"):
            csv_arg = arg
        i += 1

    if csv_arg is None:
        return fail("usage: validate_paper_issues.py <issues.csv> [--strict] [--sync [--dry-run]]")

    path = Path(csv_arg)
    strict = "--strict" in sys.argv

    # Sync mode: update citation counts from source file
    if sync_mode:
        if not path.exists():
            return fail(f"file not found: {path}")
        return sync_issues(path, tex_path=tex_path, dry_run=dry_run)

    if not path.exists():
        return fail(f"file not found: {path}")

    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if any(cell.strip() for cell in row):
                rows.append(row)

    if not rows:
        return fail("csv is empty")

    header = rows[0]
    if header != REQUIRED_COLUMNS:
        return fail(
            "invalid header. expected: "
            + ",".join(REQUIRED_COLUMNS)
            + " | got: "
            + ",".join(header)
        )

    seen_ids: set[str] = set()
    total_target_citations = 0
    total_verified_citations = 0
    status_counts = {"TODO": 0, "DOING": 0, "DONE": 0, "SKIP": 0}
    phase_counts = {"Research": 0, "Writing": 0, "Extension": 0, "Refinement": 0, "QA": 0}
    errors = 0
    warnings = 0

    for idx, row in enumerate(rows[1:], start=2):
        if len(row) != len(REQUIRED_COLUMNS):
            print(f"error: row {idx}: expected {len(REQUIRED_COLUMNS)} columns, got {len(row)}", file=sys.stderr)
            errors += 1
            continue

        row_data = dict(zip(REQUIRED_COLUMNS, row))

        # Check required fields
        for col in ["ID", "Phase", "Title", "Description", "Acceptance", "Status"]:
            if not row_data[col].strip():
                print(f"error: row {idx}: '{col}' is empty", file=sys.stderr)
                errors += 1

        # Validate Status
        status = row_data["Status"].strip()
        if status not in ALLOWED_STATUS:
            print(f"error: row {idx}: 'Status' must be one of {sorted(ALLOWED_STATUS)}, got '{status}'", file=sys.stderr)
            errors += 1
        else:
            status_counts[status] += 1

        # Validate Phase
        phase = row_data["Phase"].strip()
        if phase not in ALLOWED_PHASES:
            print(f"error: row {idx}: 'Phase' must be one of {sorted(ALLOWED_PHASES)}, got '{phase}'", file=sys.stderr)
            errors += 1
        else:
            phase_counts[phase] += 1

        # Check for duplicate IDs
        issue_id = row_data["ID"].strip()
        if issue_id in seen_ids:
            print(f"error: row {idx}: duplicate ID '{issue_id}'", file=sys.stderr)
            errors += 1
        seen_ids.add(issue_id)

        # Parse citation counts
        try:
            target = int(row_data["Target_Citations"].strip())
            total_target_citations += target
        except ValueError:
            if strict:
                print(f"warning: row {idx}: 'Target_Citations' is not a number", file=sys.stderr)
                warnings += 1

        try:
            verified = int(row_data["Verified_Citations"].strip())
            total_verified_citations += verified
        except ValueError:
            if strict:
                print(f"warning: row {idx}: 'Verified_Citations' is not a number", file=sys.stderr)
                warnings += 1

        # Validate Sources (optional, comma-separated source names)
        sources_str = row_data.get("Sources", "").strip()
        if sources_str:
            for src in [s.strip() for s in sources_str.split(",") if s.strip()]:
                if src not in ALLOWED_SOURCES:
                    print(f"warning: row {idx}: unknown source '{src}'", file=sys.stderr)
                    warnings += 1

    if errors > 0:
        print(f"\nValidation failed with {errors} error(s).", file=sys.stderr)
        return 1

    # Print summary
    print("Validation passed!")
    print(f"\nSummary:")
    print(f"  Total issues: {len(rows) - 1}")
    print(
        "  By phase: "
        f"Research={phase_counts['Research']}, "
        f"Writing={phase_counts['Writing']}, "
        f"Extension={phase_counts['Extension']}, "
        f"Refinement={phase_counts['Refinement']}, "
        f"QA={phase_counts['QA']}"
    )
    print(f"  By status: TODO={status_counts['TODO']}, DOING={status_counts['DOING']}, DONE={status_counts['DONE']}, SKIP={status_counts['SKIP']}")
    print(f"  Target citations: {total_target_citations}")
    print(f"  Verified citations: {total_verified_citations}")

    if total_target_citations > 0:
        progress = (total_verified_citations / total_target_citations) * 100
        print(f"  Citation progress: {progress:.1f}%")

    if status_counts["DONE"] > 0:
        completion = (status_counts["DONE"] / (len(rows) - 1)) * 100
        print(f"  Task completion: {completion:.1f}%")

    if warnings > 0:
        print(f"\n{warnings} warning(s) found.", file=sys.stderr)

    # Resume mode: find next actionable issue
    if resume_mode:
        next_issue = None
        for i in range(1, len(rows)):
            row_data = dict(zip(REQUIRED_COLUMNS, rows[i]))
            status = row_data["Status"].strip()
            if status in ("TODO", "DOING"):
                next_issue = row_data
                break

        if next_issue:
            print(f"\n>>> RESUME POINT <<<")
            print(f"Next: {next_issue['ID']} - {next_issue['Title']}")
            print(f"  Phase: {next_issue['Phase']}")
            print(f"  Status: {next_issue['Status']}")
            print(f"  Target citations: {next_issue['Target_Citations']}")
            print(f"  Verified citations: {next_issue['Verified_Citations']}")
            print(f"  Acceptance criteria: {next_issue['Acceptance']}")
        else:
            print("\nAll issues are DONE or SKIP. Nothing to resume.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

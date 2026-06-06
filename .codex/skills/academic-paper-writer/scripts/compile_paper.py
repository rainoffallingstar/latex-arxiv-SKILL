#!/usr/bin/env python3
"""Compile main.typ or main.tex for a paper project.

Supports:
  - Typst (primary): typst compile main.typ
  - LaTeX (legacy): pdflatex + bibtex or latexmk
  - Markdown: typst → pandoc → markdown
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from paper_utils import check_typst_available, check_latex_available


def run(cmd: list[str], cwd: Path) -> int:
    result = subprocess.run(cmd, cwd=str(cwd))
    return result.returncode


def parse_total_pages(log_path: Path) -> int | None:
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"Output written on .*?\((\d+)\s+pages?", text)
    if not match:
        return None
    return int(match.group(1))


def parse_label_page(aux_path: Path, label: str) -> int | None:
    if not aux_path.exists():
        return None
    text = aux_path.read_text(encoding="utf-8", errors="replace")

    def parse_braced_group(content: str, start_idx: int) -> tuple[str, int] | None:
        if start_idx >= len(content) or content[start_idx] != "{":
            return None
        depth = 0
        i = start_idx + 1
        group_start = i
        while i < len(content):
            ch = content[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                if depth == 0:
                    return content[group_start:i], i + 1
                depth -= 1
            i += 1
        return None

    label_prefix = f"\\newlabel{{{label}}}"
    for line in text.splitlines():
        if not line.startswith(label_prefix):
            continue
        brace_start = line.find("{", len(label_prefix))
        if brace_start == -1:
            continue
        outer = parse_braced_group(line, brace_start)
        if outer is None:
            continue
        outer_content, _ = outer
        idx = 0
        first = parse_braced_group(outer_content, idx)
        if first is None:
            continue
        _, idx = first
        while idx < len(outer_content) and outer_content[idx].isspace():
            idx += 1
        second = parse_braced_group(outer_content, idx)
        if second is None:
            continue
        page_str, _ = second
        page_str = page_str.strip()
        if page_str.isdigit():
            return int(page_str)
    return None


def report_page_counts(project_dir: Path, label: str) -> None:
    log_path = project_dir / "main.log"
    aux_path = project_dir / "main.aux"
    total_pages = parse_total_pages(log_path)
    if total_pages is None:
        print("warning: could not read total page count from main.log", file=sys.stderr)
        return
    bib_start_page = parse_label_page(aux_path, label)
    if bib_start_page is None:
        print(
            f"warning: could not find label '{label}' in main.aux; "
            "add a label at bibliography start to enable main-text page counting",
            file=sys.stderr,
        )
        return
    main_text_pages_excl = max(bib_start_page - 1, 0)
    ref_pages_incl = max(total_pages - main_text_pages_excl, 0)
    main_text_pages_incl = bib_start_page
    ref_pages_excl = max(total_pages - main_text_pages_incl, 0)
    print("\nPage count report:")
    print(f"  Total pages (incl. references): {total_pages}")
    print(f"  References start page (label '{label}'): {bib_start_page}")
    print(f"  Main text pages (exclude ref-start page): {main_text_pages_excl}")
    print(f"  Reference pages (include ref-start page): {ref_pages_incl}")
    print(f"  Main text pages (include ref-start page): {main_text_pages_incl}")
    print(f"  Reference pages (exclude ref-start page): {ref_pages_excl}")


def cross_check_citations(project_dir: Path) -> int:
    """Cross-reference cite keys against ref.bib entries.

    Supports Typst (@key) and LaTeX (\\cite{key}) syntax.
    """
    # Auto-detect source file
    src_path = None
    for name in ("main.typ", "main.tex"):
        candidate = project_dir / name
        if candidate.exists():
            src_path = candidate
            break
    if src_path is None:
        print("error: No main.typ or main.tex found", file=sys.stderr)
        return 1

    bib_path = project_dir / "ref.bib"
    if not bib_path.exists():
        print("error: ref.bib not found", file=sys.stderr)
        return 1

    tex_content = src_path.read_text(encoding="utf-8", errors="replace")
    bib_content = bib_path.read_text(encoding="utf-8", errors="replace")

    cite_keys: set[str] = set()

    if src_path.suffix == ".typ":
        # Typst @key syntax
        for m in re.finditer(r'@([a-zA-Z][a-zA-Z0-9_\-:]*)', tex_content):
            cite_keys.add(m.group(1))
    else:
        # LaTeX \cite{key1,key2,...} syntax
        for m in re.finditer(r'\\(?:cite|citep|citet|citealt|citealp|citenum|footcite|parencite)\{([^}]+)\}', tex_content):
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    cite_keys.add(k)

    bib_re = re.compile(r'@\w+\{([^,]+),')
    bib_keys: set[str] = set()
    for m in bib_re.finditer(bib_content):
        bib_keys.add(m.group(1).strip())

    undefined = sorted(cite_keys - bib_keys)
    unused = sorted(bib_keys - cite_keys)

    print("\nCitation Cross-Reference Report")
    print(f"  Source: {src_path.name} + ref.bib")
    print(f"  Unique cite keys in source: {len(cite_keys)}")
    print(f"  Unique entry keys in ref.bib: {len(bib_keys)}")
    if len(cite_keys) > 0:
        print(f"  Citation-to-reference ratio: {len(cite_keys)}/{len(bib_keys)} = {len(cite_keys)/len(bib_keys):.2f}")
    print()

    if undefined:
        print(f"  UNDEFINED CITATIONS ({len(undefined)}):")
        for k in undefined:
            print(f"    - {k}")
        print()
    else:
        print("  No undefined citations.")
        print()

    if unused:
        print(f"  UNUSED REFERENCES ({len(unused)}):")
        for k in unused:
            print(f"    - {k}")
        print()
    else:
        print("  No unused references.")
        print()

    return 1 if undefined else 0


def report_citation_counts(project_dir: Path) -> None:
    """Count citations and report per-section distribution."""
    src_path = None
    for name in ("main.typ", "main.tex"):
        candidate = project_dir / name
        if candidate.exists():
            src_path = candidate
            break
    if src_path is None:
        print("warning: no source file found", file=sys.stderr)
        return

    content = src_path.read_text(encoding="utf-8", errors="replace")
    is_typst = src_path.suffix == ".typ"

    if is_typst:
        cite_re = re.compile(r'@([a-zA-Z][a-zA-Z0-9_\-:]*)')
        section_pattern = re.compile(r'^=\s+(.+)$', re.MULTILINE)
    else:
        cite_re = re.compile(r'\\(?:cite|citep|citet|citealt|citealp|citenum)\{([^}]+)\}')
        section_pattern = re.compile(r'\\(?:section|subsection|subsubsection)\{([^}]+)\}', re.MULTILINE)

    all_keys: set[str] = set()
    for m in cite_re.finditer(content):
        if is_typst:
            all_keys.add(m.group(1))
        else:
            for k in m.group(1).split(","):
                k = k.strip()
                if k:
                    all_keys.add(k)

    print("\nCitation report:")
    print(f"  Source: {src_path.name}")
    print(f"  Unique citation keys: {len(all_keys)}")

    sections = [(m.start(), m.group(1).strip()) for m in section_pattern.finditer(content)]
    if sections:
        sections.append((len(content), "__END__"))
        print("\n  Per-section citation count:")
        for i in range(len(sections) - 1):
            start_pos = sections[i][0]
            end_pos = sections[i + 1][0]
            section_title = sections[i][1]
            section_text = content[start_pos:end_pos]
            sec_keys: set[str] = set()
            for m in cite_re.finditer(section_text):
                if is_typst:
                    sec_keys.add(m.group(1))
                else:
                    for k in m.group(1).split(","):
                        k = k.strip()
                        if k:
                            sec_keys.add(k)
            print(f"    {len(sec_keys):>3}  {section_title}")


def compile_typst(project_dir: Path) -> int:
    """Compile a Typst project."""
    src = project_dir / "main.typ"
    if not src.exists():
        print("error: main.typ not found", file=sys.stderr)
        return 1

    typst = shutil.which("typst")
    if not typst:
        print("error: typst not found. Install with: brew install typst", file=sys.stderr)
        return 1

    pdf_path = project_dir / "main.pdf"
    cmd = [typst, "compile", str(src), str(pdf_path)]
    print(f"Compiling: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_dir))
    if result.returncode != 0:
        print(f"Typst compilation failed (exit code {result.returncode})", file=sys.stderr)
        return result.returncode

    print(f"Compiled: {pdf_path}")
    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"  Size: {size_kb:.0f} KB")
    return 0


def compile_latex(project_dir: Path) -> int:
    """Compile a LaTeX project (legacy)."""
    src = project_dir / "main.tex"
    if not src.exists():
        print("error: main.tex not found", file=sys.stderr)
        return 1

    latexmk = shutil.which("latexmk")
    pdflatex = shutil.which("pdflatex")
    bibtex = shutil.which("bibtex")

    if latexmk:
        cmd = [latexmk, "-pdf", "-interaction=nonstopmode", str(src.name)]
    elif pdflatex and bibtex:
        cmd = [pdflatex, "-interaction=nonstopmode", str(src.name)]
    else:
        print("error: No LaTeX compiler found. Install pdflatex + bibtex or latexmk.", file=sys.stderr)
        return 1

    print(f"Compiling: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_dir))
    if result.returncode != 0:
        print(f"LaTeX compilation failed (exit code {result.returncode})", file=sys.stderr)
        return result.returncode

    pdf_path = project_dir / "main.pdf"
    if pdf_path.exists():
        size_kb = pdf_path.stat().st_size / 1024
        print(f"Compiled: {pdf_path} ({size_kb:.0f} KB)")
    return 0


def compile_markdown(project_dir: Path) -> int:
    """Compile Typst to Markdown via pandoc."""
    src = project_dir / "main.typ"
    if not src.exists():
        print("error: main.typ not found", file=sys.stderr)
        return 1

    pandoc = shutil.which("pandoc")
    if not pandoc:
        print("error: pandoc not found. Install with: brew install pandoc", file=sys.stderr)
        return 1

    # Compile Typst to PDF first (ensures no errors)
    code = compile_typst(project_dir)
    if code != 0:
        print("Cannot generate Markdown: Typst compilation failed.", file=sys.stderr)
        return code

    md_path = project_dir / "main.md"
    cmd = [pandoc, str(src), "-f", "typst", "-t", "markdown", "-o", str(md_path)]
    print(f"Converting to Markdown: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_dir))
    if result.returncode != 0:
        # Fallback: try via PDF
        pdf_path = project_dir / "main.pdf"
        if pdf_path.exists():
            cmd2 = [pandoc, str(pdf_path), "-f", "pdf", "-t", "markdown", "-o", str(md_path)]
            print(f"PDF fallback: {' '.join(cmd2)}")
            result = subprocess.run(cmd2, cwd=str(project_dir))
    if result.returncode == 0 and md_path.exists():
        size_kb = md_path.stat().st_size / 1024
        print(f"Markdown output: {md_path} ({size_kb:.0f} KB)")
        return 0
    print(f"Markdown conversion failed (exit code {result.returncode})", file=sys.stderr)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile paper (Typst primary, LaTeX legacy, Markdown via pandoc).")
    parser.add_argument("--project-dir", default=".", help="Project directory containing main.typ or main.tex.")
    parser.add_argument("--format", default=None, choices=["typst", "latex", "markdown"],
                        help="Output format (auto-detected if not specified).")
    parser.add_argument("--report-page-counts", action="store_true",
                        help="Print page counts (LaTeX only).")
    parser.add_argument("--references-start-label", default="ReferencesStart",
                        help="Label at bibliography start (LaTeX only).")
    parser.add_argument("--citation-report", action="store_true",
                        help="Print per-section citation counts.")
    parser.add_argument("--cross-check", action="store_true",
                        help="Cross-reference cite keys against ref.bib entries.")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        print(f"error: Not a directory: {project_dir}", file=sys.stderr)
        return 1

    # Auto-detect format
    fmt = args.format
    if fmt is None:
        if (project_dir / "main.typ").exists():
            fmt = "typst"
        elif (project_dir / "main.tex").exists():
            fmt = "latex"
        else:
            print("error: No main.typ or main.tex found", file=sys.stderr)
            return 1

    # Cross-check (before compilation)
    if args.cross_check:
        cross_code = cross_check_citations(project_dir)
        print()

    # Compile
    if fmt == "latex":
        code = compile_latex(project_dir)
    elif fmt == "markdown":
        code = compile_markdown(project_dir)
    else:
        code = compile_typst(project_dir)

    if code != 0:
        return code

    # Post-compilation reports
    if args.report_page_counts and fmt == "latex":
        report_page_counts(project_dir, args.references_start_label)
    if args.citation_report:
        report_citation_counts(project_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

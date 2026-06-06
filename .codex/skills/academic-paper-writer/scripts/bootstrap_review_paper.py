#!/usr/bin/env python3
"""Bootstrap a review paper project (scaffold + plan/issues).

This is the domain-agnostic replacement for bootstrap_ieee_review_paper.py.
It reads paper-config.yml to decide:
  - Output format (Typst by default, LaTeX legacy)
  - Which template to use (IEEEtran, article, biomedical) in the correct format
  - Citation style (ieee vs author-year)
  - Whether to initialize the multi-source literature registry

Workflow:
  1) Kickoff: scaffold project + draft plan (for user review)
  2) Continue: create issues CSV after user approval
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from paper_utils import (
    get_template_dir,
    get_latex_template_dir,
    get_typst_fragment_dir,
    now_timestamp,
    slugify,
    validate_slug,
    validate_timestamp,
)

try:
    from paper_config import load_config, generate_config
    _HAS_CONFIG = True
except ImportError:
    _HAS_CONFIG = False


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd)
    return proc.returncode


_LATEX_TEMPLATE_MAP = {
    "IEEEtran": "main.template.tex",
    "article": "main-article.template.tex",
    "biomedical": "main-biomedical.template.tex",
}

_TYPST_TEMPLATE_MAP = {
    "IEEEtran": "main.template.typ",
    "article": "main.template.typ",
    "biomedical": "main-biomedical.template.typ",
}


def _resolve_template(config: dict | None, template_dir: Path, output_format: str = "typst") -> Path:
    """Pick the correct template file based on config and output format."""
    tclass = config.get("template_class", "article") if config else "article"

    if output_format == "latex":
        tmap = _LATEX_TEMPLATE_MAP
        template_dir = template_dir / "latex" if (template_dir / "latex").is_dir() else template_dir
    else:
        tmap = _TYPST_TEMPLATE_MAP

    tname = tmap.get(tclass, tmap["article"])
    candidate = template_dir / tname
    if candidate.exists():
        return candidate

    fallback = template_dir / tmap["article"]
    if fallback.exists():
        return fallback

    raise FileNotFoundError(f"No template found. Tried: {candidate}, {fallback}")


def _apply_latex_citation_style(main_tex: Path, citation_style: str) -> None:
    """Toggle between IEEE numbered and author-year in the generated main.tex."""
    content = main_tex.read_text(encoding="utf-8")

    if citation_style == "author-year":
        content = content.replace(
            r"\usepackage{cite}",
            r"% \usepackage{cite}  % disabled in favor of natbib",
        )
        content = content.replace(
            r"% \usepackage[round]{natbib}",
            r"\usepackage[round]{natbib}",
        )
        content = content.replace(
            r"\bibliographystyle{ieeetr}",
            r"% \bibliographystyle{ieeetr}  % disabled in favor of author-year",
        )
        content = content.replace(
            r"% \bibliographystyle{plainnat}",
            r"\bibliographystyle{plainnat}",
        )
    else:
        content = content.replace(
            r"% \usepackage{cite}  % disabled in favor of natbib",
            r"\usepackage{cite}",
        )
        content = content.replace(
            r"\usepackage[round]{natbib}",
            r"% \usepackage[round]{natbib}",
        )
        content = content.replace(
            r"% \bibliographystyle{ieeetr}  % disabled in favor of author-year",
            r"\bibliographystyle{ieeetr}",
        )
        content = content.replace(
            r"\bibliographystyle{plainnat}",
            r"% \bibliographystyle{plainnat}",
        )
    main_tex.write_text(content, encoding="utf-8")


def _apply_typst_citation_style(main_typ: Path, citation_style: str) -> None:
    """Toggle between IEEE numbered and author-year in the generated main.typ."""
    content = main_typ.read_text(encoding="utf-8")

    if citation_style == "ieee":
        # Enable IEEE CSL, disable APA
        content = content.replace(
            '#bibliography("ref.bib", style: "apa")',
            '// #bibliography("ref.bib", style: "apa")  % disabled in favor of ieee',
        )
        content = content.replace(
            '// #bibliography("ref.bib", style: "ieee")',
            '#bibliography("ref.bib", style: "ieee")',
        )
    else:
        # Author-year (APA CSL, default)
        content = content.replace(
            '#bibliography("ref.bib", style: "ieee")',
            '// #bibliography("ref.bib", style: "ieee")  % disabled in favor of apa',
        )
        content = content.replace(
            '// #bibliography("ref.bib", style: "apa")',
            '#bibliography("ref.bib", style: "apa")',
        )
    main_typ.write_text(content, encoding="utf-8")


def _scaffold_typst_project(
    topic: str,
    dest_dir: Path,
    config: dict | None = None,
    template_dir: Path | None = None,
) -> None:
    """Scaffold a Typst project."""
    if template_dir is None:
        template_dir = get_template_dir()
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    # Copy the correct .typ template
    src_template = _resolve_template(config, template_dir, "typst")
    dest_main = dest_dir / "main.typ"
    shutil.copy2(src_template, dest_main)

    # Create figures directory
    (dest_dir / "figures").mkdir(exist_ok=True)

    # Copy Typst fragment templates (figures, tables, diagrams)
    fragment_dir = get_typst_fragment_dir()
    if fragment_dir.exists():
        for f in fragment_dir.glob("*.typ"):
            dest_f = dest_dir / "figures" / f.name
            if not dest_f.exists():
                shutil.copy2(f, dest_f)

    # Copy references template
    bib_src = template_dir / "references.template.bib"
    bib_dest = dest_dir / "ref.bib"
    if bib_src.exists() and not bib_dest.exists():
        shutil.copy2(bib_src, bib_dest)

    # Update bibliography reference in template
    if dest_main.exists():
        content = dest_main.read_text(encoding="utf-8")
        content = content.replace(
            '#bibliography("references")',
            '#bibliography("ref.bib", style: "apa")',
        )
        content = content.replace(
            '#bibliography("references.bib")',
            '#bibliography("ref.bib", style: "apa")',
        )
        dest_main.write_text(content, encoding="utf-8")
        if config:
            _apply_typst_citation_style(dest_main, config.get("citation_style", "author-year"))
        else:
            _apply_typst_citation_style(dest_main, "author-year")

    print(f"Created Typst paper scaffold at: {dest_dir}")
    if config:
        print(f"  Output format: typst")
        print(f"  Template class: {config.get('template_class', 'article')}")
        print(f"  Citation style: {config.get('citation_style', 'author-year')}")


def _scaffold_latex_project(
    topic: str,
    dest_dir: Path,
    config: dict | None = None,
    template_dir: Path | None = None,
) -> None:
    """Scaffold a LaTeX project (legacy)."""
    if template_dir is None:
        template_dir = get_template_dir()

    latex_dir = template_dir / "latex" if (template_dir / "latex").is_dir() else template_dir

    ignore = shutil.ignore_patterns(
        "*.aux", "*.bbl", "*.blg", "*.fdb_latexmk", "*.fls",
        "*.lof", "*.log", "*.lot", "*.out", "*.synctex",
        "*.synctex.gz", "*.toc", "main.template.pdf",
        "main-article.template.pdf", "main-biomedical.template.pdf",
        "*.typ",
    )
    shutil.copytree(latex_dir, dest_dir, ignore=ignore, dirs_exist_ok=True)

    src_template = _resolve_template(config, latex_dir, "latex")
    dest_main = dest_dir / "main.tex"
    bib_template = dest_dir / "references.template.bib"
    dest_bib = dest_dir / "ref.bib"

    if src_template.name != "main.tex":
        shutil.copy2(src_template, dest_main)
        generic = dest_dir / "main.template.tex"
        if generic.exists():
            generic.unlink()
    else:
        main_template = dest_dir / "main.template.tex"
        if main_template.exists():
            main_template.rename(dest_main)

    for unused in (dest_dir / "main.template.tex", dest_dir / "main-article.template.tex", dest_dir / "main-biomedical.template.tex"):
        if unused.exists():
            unused.unlink()

    if bib_template.exists():
        bib_template.rename(dest_bib)

    if dest_main.exists():
        content = dest_main.read_text(encoding="utf-8")
        content = content.replace("\\bibliography{references}", "\\bibliography{ref}")
        dest_main.write_text(content, encoding="utf-8")
        if config:
            _apply_latex_citation_style(dest_main, config.get("citation_style", "ieee"))
        else:
            _apply_latex_citation_style(dest_main, "ieee")

    print(f"Created LaTeX paper scaffold at: {dest_dir}")
    if config:
        print(f"  Output format: latex")
        print(f"  Template class: {config.get('template_class', 'article')}")
        print(f"  Citation style: {config.get('citation_style', 'ieee')}")


def scaffold_project(
    topic: str,
    folder_name: str,
    out_dir: Path,
    config: dict | None = None,
) -> Path:
    """Scaffold a paper project, selecting format based on config."""
    dest_dir = out_dir / folder_name
    if dest_dir.exists():
        raise SystemExit(f"Destination already exists: {dest_dir}")

    output_format = config.get("output_format", "typst") if config else "typst"
    template_dir = get_template_dir()

    if output_format == "latex":
        _scaffold_latex_project(topic, dest_dir, config, template_dir)
    else:
        _scaffold_typst_project(topic, dest_dir, config, template_dir)

    return dest_dir


def infer_latest_plan_timestamp_and_slug(plan_dir: Path) -> tuple[str, str] | None:
    if not plan_dir.exists():
        return None
    candidates = sorted(p for p in plan_dir.glob("*.md") if p.is_file())
    if not candidates:
        return None
    latest = candidates[-1].name
    if not latest.endswith(".md"):
        return None
    stem = latest[:-3]
    if len(stem) < 21 or stem[19] != "-":
        return None
    ts = stem[:19]
    slug = stem[20:]
    try:
        validate_timestamp(ts)
        validate_slug(slug)
    except ValueError:
        return None
    return ts, slug


def _init_registry(project_dir: Path, sources: list[str]) -> None:
    """Initialize the multi-source literature registry."""
    registry_script = Path(__file__).resolve().parent / "literature_registry.py"
    if not registry_script.exists():
        return
    notes_dir = project_dir / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    db_path = notes_dir / "literature-registry.sqlite3"
    code = run([
        sys.executable, str(registry_script),
        "--project-dir", str(project_dir),
        "init",
    ])
    if code == 0:
        print(f"  Literature registry initialized: {db_path}")
        print(f"  Preferred sources: {', '.join(sources)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap a review paper project (Typst-first, config-driven)."
    )
    parser.add_argument(
        "--stage", default="kickoff", choices=["kickoff", "issues"],
        help="kickoff=scaffold+plan; issues=create issues CSV (default: kickoff).",
    )
    parser.add_argument("--topic", required=True, help="Paper topic description.")
    parser.add_argument("--name", help="Folder name override (default: slugified topic).")
    parser.add_argument("--out", default=".", help="Output directory (default: current directory).")
    parser.add_argument(
        "--complexity", default="medium", choices=["simple", "medium", "complex"],
        help="Plan complexity.",
    )
    parser.add_argument("--timestamp", help="Timestamp override (YYYY-MM-DD_HH-mm-ss).")
    parser.add_argument("--slug", help="Optional slug override.")
    parser.add_argument("--check-latex", action="store_true", help="Check LaTeX availability.")
    parser.add_argument(
        "--with-literature-notes", action="store_true",
        help="Create notes/literature-notes.md.",
    )
    parser.add_argument("--config", help="Path to paper-config.yml (generated if absent).")
    parser.add_argument(
        "--template", default=None, choices=["IEEEtran", "article", "biomedical"],
        help="Template class (auto-detected if not specified).",
    )
    parser.add_argument(
        "--citation-style", default=None, choices=["ieee", "author-year"],
        help="Citation style (auto-detected if not specified).",
    )
    parser.add_argument(
        "--format", default=None, dest="output_format",
        choices=["typst", "latex", "markdown"],
        help="Output format (default: typst, from config).",
    )
    parser.add_argument(
        "--sources", nargs="*",
        choices=["arxiv", "pubmed", "openalex", "europepmc", "biorxiv", "paper-search"],
        help="Preferred literature sources.",
    )
    args = parser.parse_args()

    topic = args.topic.strip()
    if not topic:
        print("error: Topic cannot be empty.", file=sys.stderr)
        return 1

    out_dir = Path(args.out).resolve()
    folder_name = (args.name or slugify(topic)).strip()
    if not folder_name:
        print("error: Folder name cannot be empty.", file=sys.stderr)
        return 1

    project_dir = out_dir / folder_name
    if args.stage == "issues":
        if not project_dir.exists():
            print(f"error: Project does not exist: {project_dir}", file=sys.stderr)
            return 1
    else:
        if project_dir.exists():
            print(f"error: Destination already exists: {project_dir}", file=sys.stderr)
            return 1

    slug = args.slug.strip() if args.slug else slugify(folder_name)
    try:
        validate_slug(slug)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.timestamp:
        timestamp = args.timestamp.strip()
        try:
            validate_timestamp(timestamp)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    else:
        timestamp = now_timestamp()

    config: dict | None = None
    if _HAS_CONFIG:
        if args.config:
            config = load_config(Path(args.config))
            print(f"Loaded config from: {args.config}")
        else:
            config = generate_config(
                topic, domain=None,
                output_format=args.output_format,
                template_class=args.template,
                citation_style=args.citation_style,
                preferred_sources=list(args.sources) if args.sources else None,
            )
            fmt = config.get("output_format", "typst")
            print(f"Generated config: domain={config['domain']}, format={fmt}, template={config['template_class']}, style={config['citation_style']}, sources={config['preferred_sources']}")
    else:
        config = {
            "output_format": args.output_format or "typst",
            "template_class": args.template or "article",
            "citation_style": args.citation_style or "author-year",
            "preferred_sources": list(args.sources) if args.sources else ["openalex", "paper-search"],
            "domain": "general",
        }

    scripts_dir = Path(__file__).resolve().parent
    plan_script = scripts_dir / "create_paper_plan.py"

    if args.stage == "kickoff":
        scaffold_project(topic, folder_name, out_dir, config)

        if _HAS_CONFIG:
            from paper_config import dump_config
            config_path = project_dir / "paper-config.yml"
            dump_config(config, config_path)
            print(f"Config saved: {config_path}")

        _init_registry(project_dir, config.get("preferred_sources", ["openalex", "paper-search"]))

        plan_cmd = [
            sys.executable, str(plan_script),
            "--topic", topic,
            "--stage", "plan",
            "--complexity", args.complexity,
            "--timestamp", timestamp,
            "--slug", slug,
            "--output-dir", str(project_dir),
        ]
        if args.check_latex:
            plan_cmd.append("--check-latex")
        if args.with_literature_notes:
            plan_cmd.append("--with-literature-notes")
        code = run(plan_cmd)
        if code != 0:
            print("Plan creation failed.", file=sys.stderr)
            return code
        return 0

    if args.stage == "issues":
        plan_dir = project_dir / "plan"
        inferred = infer_latest_plan_timestamp_and_slug(plan_dir)
        if inferred:
            ts, sl = inferred
            if not args.timestamp:
                timestamp = ts
            if not args.slug:
                slug = sl

        issues_cmd = [
            sys.executable, str(plan_script),
            "--topic", topic,
            "--stage", "issues",
            "--timestamp", timestamp,
            "--slug", slug,
            "--output-dir", str(project_dir),
        ]
        if args.with_literature_notes:
            issues_cmd.append("--with-literature-notes")
        code = run(issues_cmd)
        if code != 0:
            print("Issues creation failed.", file=sys.stderr)
            return code
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

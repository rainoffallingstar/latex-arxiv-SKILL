# Changelog

## v1.1.0 (unreleased) — Typst-First Framework

### Major Changes
- **Typst-first output**: `main.template.typ` and `main-biomedical.template.typ` are the primary templates. Typst compiles in a single pass (`typst compile`) with native CJK font support and `@key` citation syntax.
- **LaTeX demoted to legacy**: LaTeX templates moved to `template/latex/`. Still functional via `output_format: latex` in config.
- **Markdown output**: `compile_paper.py --format markdown` converts Typst to Markdown via pandoc.
- **`paper_config.py` updated**: new `output_format` field (typst | latex | markdown). Domain defaults now produce Typst configs. `paper-search` added to valid literature sources.
- **`compile_paper.py` rewritten**: supports `typst compile`, `pdflatex` (legacy), and pandoc Markdown conversion. Cross-reference checking supports both `@key` (Typst) and `\cite{}` (LaTeX).
- **`bootstrap_review_paper.py` rewritten**: Typst scaffolding via `_scaffold_typst_project()`, LaTeX legacy via `_scaffold_latex_project()`. Typst fragment templates (figures, tables, diagrams) auto-copied to `figures/`.
- **`literature_registry.py` integration**: `paper-search` CLI added as a search backend, covering 12+ sources (Crossref, OpenAlex, PubMed, arXiv, etc.).
- **`paper_utils.py` expanded**: `check_typst_available()`, `count_citations()` supports `.typ` and `.tex`, `detect_citation_style()` supports Typst, `get_template_for_domain()` returns format-specific templates.
- **`latex-rhythm-refiner` updated**: SKILL.md now covers Typst (`@key`), LaTeX (`\cite{}`), and Markdown (`[@key]`) citation syntax.
- **CI configured**: `pytest.ini` + GitHub Actions workflow (Python 3.10–3.12).
- **Test suite expanded**: 102 tests covering paper_config, literature_registry, paper_utils, review_gaps, and validate_issues. Typst-specific tests added.

### Breaking Changes
- `bootstrap_ieee_review_paper.py` removed (replaced by `bootstrap_review_paper.py`).
- `arxiv_registry.py` removed (replaced by `literature_registry.py`).
- `.codex/skills/arxiv-paper-writer/` removed (duplicate of `academic-paper-writer`).
- `paper-config.yml` schema changed: added `output_format`, removed `recommended_compiler`.
- `paper_config.py` API: `generate_config()` returns `output_format` instead of `recommended_compiler`. Function `get_recommended_compiler()` replaced by `get_recommended_output_format()`.

### Migration from v1.0.0
1. Deleted scripts are no longer available; use `bootstrap_review_paper.py` and `literature_registry.py`.
2. Regenerate `paper-config.yml` to get the new `output_format` field:
   ```bash
   python3 scripts/paper_config.py generate --topic "..." --output paper-config.yml
   ```
3. Typst templates are in `assets/template/`; LaTeX templates are in `assets/template/latex/`.
4. Install recommended tools:
   ```bash
   brew install typst          # primary compiler
   brew install pandoc          # optional, for Markdown output
   brew install paper-search    # optional, unified literature search
   ```
5. Tests can be run with `python3 -m pytest tests/`.

---

## v1.0.0 (2026-06-04) — Generalized Multi-Domain Framework

### Major Changes
- **Multi-source literature**: Support for arXiv, PubMed, OpenAlex, Europe PMC, and bioRxiv via `literature_registry.py` (replaces arXiv-only `arxiv_registry.py`).
- **Multi-domain support**: Auto-detection of 8 scientific domains (computer-science, biomedical, physics, chemistry, engineering, mathematics, social-sciences, environmental) with per-domain defaults.
- **Configurable templates**: Three LaTeX templates — IEEEtran (two-column), article (single-column), and biomedical (single-column for life sciences) — selected automatically by domain.
- **Configurable citation styles**: IEEE numbered (ieeetr) or author-year (natbib/plainnat), toggled automatically by domain.
- **Paper configuration system**: `paper-config.yml` drives template selection, citation style, literature sources, and section framework. Domain auto-detected from topic via `paper_config.py`.
- **New scripts**: `bootstrap_review_paper.py` (replaces `bootstrap_ieee_review_paper.py`), `literature_registry.py`, `paper_config.py`.
- **Updated reference docs**: All 5 reference guides updated for multi-source, multi-domain workflows.
- **Template cleanup**: Removed ML/AI-specific sections, colors, and placeholder text from default template.

### Breaking Changes
- `bootstrap_ieee_review_paper.py` replaced by `bootstrap_review_paper.py` (old script kept for backward compatibility).
- `arxiv_registry.py` superseded by `literature_registry.py` (old script kept for backward compatibility).
- Issues CSV schema updated: added `Sources` column.
- Plan template updated: venue/template field now references `paper-config.yml`.

### Migration from v0.x
1. Install PyYAML: `pip install -r requirements.txt`
2. Use `bootstrap_review_paper.py` instead of `bootstrap_ieee_review_paper.py`
3. Use `literature_registry.py` instead of `arxiv_registry.py` for literature management
4. Review auto-generated `paper-config.yml` at project creation time
5. Run `python3 scripts/validate_paper_issues.py` to check updated CSV schema

## v0.x — Original arXiv-only Framework

- arXiv-only literature discovery via `arxiv_registry.py`
- ML/AI-specific IEEEtran template with fixed sections (Building Blocks, Frontier Models, Safety)
- Fixed IEEE numbered citations only
- Single bootstrap script: `bootstrap_ieee_review_paper.py`

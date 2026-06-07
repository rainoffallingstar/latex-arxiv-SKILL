# Academic Review Paper Writing Framework

[English](README.md) . [简体中文](README.zh-CN.md)

An end-to-end, issues-driven framework for writing academic review/survey papers with verified citations. Supports multiple literature sources, scientific domains, Typst (primary) and LaTeX (legacy) templates, and configurable citation styles. Markdown output via pandoc. Compatible with Cursor and Codex CLI.

## What's New in v1.1

- **LQS multi-dimensional scoring** — automatic quality scoring of literature (recency, citation impact, venue, institution, acceptance) with must-cite/conditional/drop classification
- **4 sub-skills** — literature-search, structure-logic, figures-tables, review-sim with automated weakness routing
- **Review simulation engine** — 5-persona LLM-based peer review with anti-inflation scoring and no-LLM gap-analysis fallback
- **Typst-first output** — native CJK font support, single-pass compilation
- **229 tests** — comprehensive coverage across 12 test modules

## Capabilities

| Dimension | Support |
|-----------|---------|
| **Output formats** | Typst (primary), LaTeX (legacy), Markdown (via pandoc) |
| **Literature sources** | arXiv, PubMed, OpenAlex, Europe PMC, bioRxiv, paper-search (12+ sources) |
| **Scientific domains** | 8 domains auto-detected from topic (CS, biomedical, physics, chemistry, engineering, math, social sciences, environmental) |
| **Quality scoring** | 5-dimension LQS (recency, citation impact, venue, institution, acceptance) + A/B/C/D depth classification |
| **Review process** | 5-persona LLM review simulation with anti-inflation rules + gap-analysis-only fallback |
| **Templates** | Typst: generic academic + biomedical; LaTeX: IEEEtran, article, biomedical (legacy) |
| **Citation styles** | IEEE numbered (ieee.csl) or author-year (apa.csl) |
| **Workflow** | Gated: config → plan → issues CSV → per-section writing → iterative review → QA → compile |

## What's in here

- **Primary SKILL**: `academic-paper-writer` at `.codex/skills/academic-paper-writer/SKILL.md`.
- **Helper scripts**: scaffolding, literature registry, planning, validation, compilation under `scripts/`.
- **Config system**: `paper-config.yml` drives output format, template selection, citation style, and literature source preferences based on topic domain.
- **Example output**: generated papers in `example/` (including compiled PDFs).

## Quickstart (2 prompts → a compiled paper)

### Example 1: Computer Science topic (Typst, IEEE numbered citations)

**Prompt 1:**
```
write a review article about recent advances in transformer architectures
```

The agent auto-detects the domain (computer-science), generates a `paper-config.yml` with Typst output and IEEE citations, performs a literature pass, drafts a section framework, proposes candidate titles, and creates a `plan/` file.

**Prompt 2:**
```
I will let you choose the best title and proceed
```

The agent writes the full paper and compiles it to PDF.

### Example 2: Biomedical topic (Typst, author-year citations)

**Prompt 1:**
```
write a review article about CRISPR gene editing for cancer therapy
```

The agent auto-detects the domain (biomedical), generates a `paper-config.yml` with Typst output and author-year (APA) citations, and recommends PubMed + Europe PMC + OpenAlex + paper-search as literature sources.

**Prompt 2:**
```
approved, proceed
```

The agent scaffolds the project using the biomedical Typst template, initializes the multi-source literature registry, and begins the writing loop.

### Example 3: Markdown output

```bash
python3 scripts/compile_paper.py --project-dir <paper_dir> --format markdown
```

Compiles Typst to PDF, then converts to Markdown via pandoc.

## Paper Configuration

The framework auto-detects your topic's domain and generates `paper-config.yml`. You can review and adjust it:

```bash
python3 scripts/paper_config.py detect --topic "your topic here"
python3 scripts/paper_config.py generate --topic "your topic here" --output paper-config.yml
```

Example config for a biomedical paper:

```yaml
topic: CRISPR gene editing for cancer therapy
domain: biomedical
output_format: typst
template_class: article
citation_style: author-year
preferred_sources: [pubmed, europepmc, openalex, paper-search]
section_framework: [Introduction, Disease Overview, Molecular Mechanisms, ...]
```

## Workflow (Gated)

```
Gate 0: paper-config.yml + research snapshot + draft plan → user approval
Gate 1: issues CSV (execution contract)
Phase 2: per-issue writing loop (research → write → verify → update)
Phase 3: QA + cross-ref dedup + compile → deliver
```


## Citation Verification (Mandatory Gate)

Every citation undergoes a **three-stage verification pipeline** before entering `ref.bib`. Unverified citations are rejected by default at the export gate.

### Verification Pipeline
```
verify-citation --doi → PASS → export-bibtex → ref.bib
         ↓ FAIL
    auto-cascade: title search → PASS
         ↓ FAIL
    interactive prompt: [m] manual / [f] re-search / [d] discard
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Auto-cascade** | DOI failure automatically retries via title search using registry metadata |
| **Manual confirmation** | `--manual` flag records human-confirmed passes without API call |
| **Interactive prompt** | When all automated checks fail, choose next action inline |
| **Batch verification** | `verify-all` scans the entire registry for unverified citations |
| **Fact-driven re-search** | Failed citation → extract claim → search for alternative paper → replace |
| **Enforced gate** | `export-bibtex` refuses unverified entries unless `--force` is used |


## Environment

| Requirement | Notes |
|-------------|-------|
| Python 3.8+ | Required for scripts |
| PyYAML | `pip install -r requirements.txt` |
| Typst | `brew install typst` (primary compiler) |
| Pandoc | `brew install pandoc` (optional, for Markdown) |
| LaTeX | `pdflatex` + `bibtex` (optional, for legacy mode) |
| paper-search | `brew install paper-search` (optional, unified literature search) |

Tested on macOS with Codex CLI.

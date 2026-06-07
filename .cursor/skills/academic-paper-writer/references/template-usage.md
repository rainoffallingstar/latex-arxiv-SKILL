# Template Usage Notes (Typst-first, LaTeX legacy)

## Format Selection

The framework selects the output format based on `paper-config.yml` → `output_format`:

| `output_format` | Main file | Compiler | Citation syntax |
|----------------|-----------|----------|----------------|
| `typst` (default) | `main.typ` | `typst compile` | `@key` |
| `latex` (legacy) | `main.tex` | `pdflatex` + `bibtex` | `\cite{key}` |
| `markdown` | `main.typ` → `main.md` | `pandoc` | `[@key]` |

## Typst Templates (Primary)

Templates live in `assets/template/`:
- `main.template.typ` — generic academic (all domains except biomedical)
- `main-biomedical.template.typ` — biomedical / life sciences

Typst compiles in a single pass — no separate bibtex run needed.
Fragment templates for figures, tables, and diagrams are in `assets/typst-templates/`.

### Citation Style

Citation style is toggled by switching the CSL style in `#bibliography()`:

- **IEEE numbered**: `#bibliography("ref.bib", style: "ieee")`
- **APA author-year**: `#bibliography("ref.bib", style: "apa")`

The `bootstrap_review_paper.py` script toggles these automatically based on config.

Citation syntax is always `@key` — Typst renders according to the active CSL style.

### Structure

- Section headings: `= Introduction`, `== Subsection`, `=== Subsubsection`
- Heading numbering: `#set heading(numbering: "1. 1.1 1.1.1")`
- Use the section framework from `paper-config.yml` as the starting outline
- Keep abstract, keywords, and bibliography sections intact
- Replace all placeholder text and instructional comments before delivery

### Figures, Tables, and Diagrams

Use the fragment templates in `assets/typst-templates/`:
- `figure.template.typ` — images, sub-figures, block-based diagrams
- `table.template.typ` — data tables, clinical trial tables, comparisons
- `diagram.template.typ` — architecture blocks, flowcharts, taxonomy trees, timelines

Copy the relevant blocks into `main.typ` and replace placeholders.

Key syntax:
- Label: `<fig-label>`, `<table-label>`
- Reference: `@fig-label`, `@table-label`
- Caption with citation: `caption: [Description adapted from @key.]`

### Bibliography

```typst
#bibliography("ref.bib", style: "ieee")  // numbered
#bibliography("ref.bib", style: "apa")   // author-year
```

BibTeX entries are stored in `ref.bib`. Use `literature_registry.py export-bibtex` to populate it.

### CJK Support

Typst has native CJK font support — no packages needed. The template includes CJK font fallbacks:

```typst
#set text(
  font: ("Libertinus Serif", "Noto Serif CJK SC", "Noto Serif CJK JP", "Noto Serif CJK KR"),
)
```

Install CJK fonts if rendering Chinese/Japanese/Korean text:
```bash
brew install font-noto-serif-cjk-sc font-noto-serif-cjk-jp font-noto-serif-cjk-kr
```

### Formatting

- Do not override fonts or margins — the template controls layout
- Keep sources in one directory; avoid absolute paths
- For block diagrams, prefer Typst's built-in `#block()`, `#stack()`, `#grid()`; use the `cetz` package only for complex arrow-connected diagrams

---

## LaTeX Templates (Legacy)

Templates live in `assets/template/latex/`:
- `main.template.tex` — IEEEtran (two-column, CS/engineering)
- `main-article.template.tex` — article class (single-column, general)
- `main-biomedical.template.tex` — article class (single-column, life sciences)

Used when `output_format: latex` is set in `paper-config.yml`, or when the user explicitly requests LaTeX.

### Citation Style

- **IEEE numbered** (`ieeetr`): uses `\usepackage{cite}`, citations appear as [1], [2], etc.
- **Author-year** (`plainnat`): uses `natbib`, citations as (Author, Year)
  - `\citep{key}` for parenthetical, `\citet{key}` for textual

### Structure, Figures, and Formatting

See the LaTeX template comments for full guidance. Key rules:
- Prefer vector/TikZ for figures when feasible
- Use `booktabs` for tables with clear headers
- For IEEEtran: use two-column floats only when needed to avoid overflow
- For single-column templates: standard `figure` and `table` environments
- Keep `\bibliography{ref}` pointing to `ref.bib`

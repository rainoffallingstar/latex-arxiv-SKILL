---
name: academic-paper-writer
description: >
  Write academic review articles using Typst (primary) or LaTeX (legacy) with
  verified BibTeX citations. Supports multiple literature sources (arXiv, PubMed,
  OpenAlex, Europe PMC, paper-search) and multiple domains (CS, biomedical,
  physics, etc.), with configurable templates and citation styles (IEEE numbered
  or author-year). Markdown output via pandoc.
compatibility: >
  Python 3.8+ for scripts. Typst recommended for compilation (typst compile).
  LaTeX (pdflatex + bibtex) optional for legacy mode. Pandoc for Markdown output.
  PyYAML recommended.
metadata:
  short-description: Academic review papers (Typst-first) with multi-source citations
---

# Academic Review Paper Workflow

## When to Use
- Academic review / survey papers for any scientific domain
- Typst + BibTeX workflow with verified citations (primary)
- LaTeX + BibTeX workflow (legacy mode)
- Citation validation/repair on existing projects
- Markdown output via Typst → pandoc

## When NOT to Use
- Novel experimental research papers (this is a review workflow)
- Non-academic documents

## Inputs
- Topic description (required)
- Constraints: venue, page limit, author/affiliations (optional)
- Domain and source preferences (inferred automatically, configurable)
- Output format preference (Typst default, LaTeX legacy, Markdown via pandoc)
- Existing project path for citation validation (optional)

## Outputs
- `paper-config.yml` (configuration: domain, output format, sources, citation style, template)
- `main.typ` (Typst source — primary)
- `main.tex` (LaTeX source — legacy mode only)
- `main.md` (Markdown output — via pandoc)
- `ref.bib` (verified BibTeX entries)
- `plan/<timestamp>-<slug>.md`, `issues/<timestamp>-<slug>.csv`
- Figures/tables; `main.pdf`
- `notes/literature-notes.md` (optional per-citation notes)
- `notes/literature-registry.sqlite3` (multi-source metadata/BibTeX cache)

**Conventions**: run `python3 scripts/...` from this skill folder; `<paper_dir>` is the paper root
(contains `main.typ`, `ref.bib`, `plan/`, `issues/`, `notes/`).
Use `scripts/literature_registry.py` for all literature discovery and BibTeX management.
For literature search, also use the `paper-search` CLI (available as system skill).

---

## Gated Workflow

> Tip: Run `python3 scripts/<script>.py --help` before use.
> Open reference files only when a step calls them out.

### Non-Negotiable Rules
1. **No prose in `main.typ`** (or `main.tex`) until plan approved AND issues CSV exists.
2. First deliverable: research snapshot + paper config + outline + clarification questions + draft plan.
3. **Use plan + issues tracking for all new papers; do not opt out.**
4. Issues CSV is the execution contract; update `Status` and `Verified_Citations` per issue,
   and add/split/insert issue rows when scope grows (do not do untracked work).
5. **Template is config-driven**: use `bootstrap_review_paper.py` which reads `paper-config.yml`
   to select the correct template (Typst by default) and citation style.

### Gate 0: Research Snapshot + Draft Plan + Paper Config
1. Confirm constraints (venue, page limit, author block, date range).
2. Generate paper configuration:
   ```bash
   python3 scripts/paper_config.py generate --topic "<topic>" --output <paper_dir>/paper-config.yml
   ```
   This detects the domain, recommends literature sources, sets output format (Typst by default),
   and configures template class and citation style. Review with the user and adjust as needed.
   To detect domain only:
   ```bash
   python3 scripts/paper_config.py detect --topic "<topic>"
   ```
3. Translate the topic into search keywords and run a light discovery pass:
   10-20 key papers (see `references/research-workflow.md`). Use `paper-search` CLI or `literature_registry.py`.
4. Propose 2-4 candidate titles aligned to the topic.
5. Scaffold the project folder and draft plan:
   ```bash
   python3 scripts/bootstrap_review_paper.py --stage kickoff --topic "<topic>"
   ```
   This copies the appropriate Typst template from `assets/template/` based on config;
   plan/issues are generated from templates in `assets/`.
   (The multi-source literature registry is initialized automatically by `bootstrap_review_paper.py`.)
6. Create a **framework skeleton** in `main.typ`
   (section headings + 2-4 bullets per section + seed citations; **no prose**).
   Use the section framework from `paper-config.yml` as a starting point.
   Citation syntax: `@key` for all styles.
7. Update the plan file to reflect the framework, proposed titles, and section/subsection plan.
8. Compile early: `python3 scripts/compile_paper.py --project-dir <paper_dir>`
9. Return to user:
    - Proposed outline and paper config (domain, output format, sources, citation style)
    - Planned visualizations (5+) mapped to sections (see `references/visual-templates.md`)
    - Clarification questions
10. **STOP** until user approves.

### Gate 1: Create Issues CSV (after approval)
1. Check kickoff gate in plan: `- [x] User confirmed scope + outline in chat`.
2. Create issues CSV:
   ```bash
   python3 scripts/bootstrap_review_paper.py --stage issues --topic "<topic>" --with-literature-notes
   ```
3. Validate:
   ```bash
   python3 scripts/validate_paper_issues.py <paper_dir>/issues/<timestamp>-<slug>.csv
   ```
4. If literature notes are enabled, keep short summaries and (optional) abstract snippets.
5. The plan may evolve; add/split/insert issues as needed, re-validate after edits.

### Phase 2: Per-Issue Writing Loop
For each writing issue in the CSV:
- If an issue balloons, split/insert new issue row(s) before proceeding; re-run validation; keep going until all issues are `DONE`/`SKIP`.
1. **Research**: 8-12 section-specific papers. Use multiple sources configured in `paper-config.yml`:
   ```bash
   python3 scripts/literature_registry.py --project-dir <paper_dir> search all "<query>"
   # Or search a specific source:
   python3 scripts/literature_registry.py --project-dir <paper_dir> search pubmed "<query>"
   python3 scripts/literature_registry.py --project-dir <paper_dir> search paper-search "<query>"
   ```
2. **Write**: Never 3 sentences without citations (`@key`); varied paragraph rhythm
   (see `references/writing-style.md`). For section intent and structure, use `references/template-usage.md`.
3. **Visualize**: Match content triggers (see `references/visual-templates.md`).
   Use Typst fragment templates in `figures/` for ready-to-copy blocks.
   Cite externally sourced figure content.
4. **Verify (MANDATORY GATE)**: Every new citation must pass verification before
   being added to `ref.bib`. This is NOT optional — unverified citations are the
   #1 source of quality issues.

   - **DOI verification** (preferred):
     ```bash
     python3 scripts/literature_registry.py --project-dir <paper_dir> verify-citation --doi "10.1234/example"
     ```

   - **Title+author fallback** (when no DOI available):
     ```bash
     python3 scripts/literature_registry.py --project-dir <paper_dir> verify-citation --title "Paper Title" --author "Smith"
     ```

   - **After verification passes**, export to ref.bib:
     ```bash
     python3 scripts/literature_registry.py --project-dir <paper_dir> export-bibtex <source> <source_id> --bib <paper_dir>/ref.bib
     ```

   - Web search + open source page (and PDF if available) as a secondary sanity check.

5. **Update**: Mark issue `DONE` with `Verified_Citations` count.
6. Compile after meaningful changes:
   ```bash
   python3 scripts/compile_paper.py --project-dir <paper_dir>
   ```

**After the last writing issue (conclusion) is marked `DONE`**: draft the abstract. The abstract should reflect the completed paper, not the placeholder from the template. Revisit and finalize after QA (Phase 3).

### Phase 2.x: Iterative Review Gate

After all writing issues are DONE and the abstract is drafted, the paper enters
iterative review. This is NOT rework — it is the normal academic writing process
of identifying coverage gaps and deepening the manuscript across multiple rounds.

**Trigger conditions** (configured in `paper-config.yml` → `iteration.review_triggers`):
- `after_all_writing`: auto-triggers after the last W-issue is DONE and abstract is drafted
- `user_invokes_review`: user says "review and assess" or runs review manually

**Per-round workflow:**

1. Run gap analysis:
   ```bash
   python3 scripts/review_gaps.py --project-dir <paper_dir> analyze --round <N>
   ```
   This produces a standardized gap table with P0/P1/P2 priorities.
   Supports both `main.typ` and `main.tex`.

2. Review the gap table:
   - **P0 (Critical)**: Section has < min_citations_per_section citations or a core
     dimension is completely absent. Paper is **not ready** without fixing these.
   - **P1 (Recommended)**: Section has citations but lacks depth on expected sub-topics.
     Fixing significantly improves quality.
   - **P2 (Optional)**: Well-covered section that could be refined. User decides.

3. For each accepted gap:
   a. Search literature for the gap topic:
      ```bash
      python3 scripts/literature_registry.py --project-dir <paper_dir> search all "<query>"
      ```
   b. Write supplementary content and insert at the correct section position.
   c. Verify all new citations via `verify-citation --doi`.
   d. Export BibTeX via `export-bibtex`.
   e. Create an Rx (Extension) issue in the CSV to track the round:
      `Rx,Extension,Round N - <gap description>,<desc>,<target_cites>,N/A,<acceptance>,DONE,<count>,,`
   f. Compile and re-run `review_gaps.py` to check if P0 is cleared.

4. **Auto-fix behavior** (configured in `paper-config.yml` → `iteration.auto_fix`):
   - `P0: true` — auto-fix all P0 gaps (they are blocking)
   - `P1: ask_user` — present P1 gaps and ask user "Fix these or proceed?"
   - `P2: skip` — skip P2 unless user explicitly requests

5. **Stop conditions:**
   - No P0 gaps remain AND either no P1 gaps remain or user chooses to skip them
   - `max_rounds` reached (default 5) — forced progression to Phase 2.5

6. Track round history:
   ```bash
   python3 scripts/review_gaps.py --project-dir <paper_dir> history
   ```

### Phase 2.5: Rhythm Refinement
After all writing issues are `DONE`, refine prose section-by-section using the `latex-rhythm-refiner` skill. This handles Typst (`@key`), LaTeX (`\cite{}`), and Markdown (`[@key]`) citation syntax. Varies sentence/paragraph lengths and removes filler phrases while preserving all citations.

### Phase 3: QA Gate
1. Run internal QA checklist (see `references/quality-report.md`).
2. Run cross-reference deduplication:
   ```bash
   python3 scripts/literature_registry.py --project-dir <paper_dir> cross-ref
   ```
3. Compile:
   ```bash
   python3 scripts/compile_paper.py --project-dir <paper_dir>
   ```
4. For Markdown output:
   ```bash
   python3 scripts/compile_paper.py --project-dir <paper_dir> --format markdown
   ```
5. Deliver `main.typ`, `ref.bib`, figures, and `main.pdf` (and `main.md` if requested).

---

## Existing Paper Workflow (No Re-Scaffold)
If a paper folder already exists, do NOT rerun scaffold:
```bash
# Create plan
python3 scripts/create_paper_plan.py --topic "<topic>" --stage plan --output-dir <paper_dir>
# STOP for approval, then check kickoff gate box
# Create issues
python3 scripts/create_paper_plan.py --topic "<topic>" --stage issues --timestamp "<TS>" --slug "<slug>" --output-dir <paper_dir> --with-literature-notes
```

## Citation-Validation Variant
1. Treat provided path as paper project root (Typst or LaTeX).
2. Follow `references/citation-workflow.md`.
3. Use `references/bibtex-guide.md` for BibTeX rules if entries need repair.
4. Deliver validation report and corrected `ref.bib` if requested.

---

## Success Criteria

**Compilation**: `python3 scripts/compile_paper.py --project-dir <paper_dir>` (exit 0).
For Typst projects, `typst compile` produces `main.pdf` in a single pass.

**Default Quality Metrics** (overridable via `quality_targets` in `paper-config.yml`):
- 6-10 pages of main text (references excluded)
- 60-80 total citations (8+ per section)
- 100% citation verification rate
- 70%+ citations from the last 3 years
- 5+ distinct visualization types (figures/tables/diagrams)
- Zero unverified citations

---

## Format Selection

**Typst** (default, `output_format: typst` in config):
- Single-pass compilation: `typst compile main.typ`
- Native CJK font support without extra packages
- Citation syntax: `@key` with CSL styles (IEEE, APA)
- Fragment templates in `assets/typst-templates/` for figures, tables, diagrams

**LaTeX** (legacy, `output_format: latex` in config):
- Templates in `assets/template/latex/`
- Requires `pdflatex` + `bibtex` or `latexmk`
- Citation syntax: `\cite{key}` / `\citep{key}`

**Markdown** (via pandoc):
- `python3 scripts/compile_paper.py --project-dir <paper_dir> --format markdown`
- Requires `pandoc` installed

---

## Issues CSV Schema
| Phase | Issues |
|-------|--------|
| Research | Rx: discovery, scaffolding, framework, viz planning |
| Writing | Wx: each section with target citations and visualization. **Always include a W_abstract issue** to be written after the last section (conclusion) is `DONE` and before Phase 2.5. |
| Extension | Rx: iterative review round N gap fixes, tracked per round (Phase 2.x) |
| Refinement | RFx: apply `latex-rhythm-refiner` skill (after all Wx DONE) |
| QA | Qx: citation verification, cross-ref dedup, QA checklist, compilation |

Status: `TODO` → `DOING` → `DONE`. Schema validated by `validate_paper_issues.py`.

---

## Literature Sources

| Source | Coverage | Search |
|--------|----------|--------|
| `arxiv` | CS, physics, math, stats preprints | Atom API |
| `pubmed` | Biomedical, life sciences | Entrez API |
| `openalex` | All disciplines (OA) | REST API |
| `europepmc` | Life sciences OA | REST API |
| `biorxiv` | Biology/medicine preprints | Content API |
| `paper-search` | 12+ sources unified | CLI tool |

---

## Safety & Guardrails
- **Never fabricate** citations or results; add TODO and ask user if evidence missing.
- **Mandatory citation verification gate**: every new citation MUST pass `verify-citation --doi` (or `--title` fallback) before being added to `ref.bib`.
- **Verify every citation** via web search + source page (and PDF if available) as secondary check.
- **Confirm before** large literature searches.
- **Do not overwrite** user files without confirmation.
- **Issues CSV** is the contract; mark `DONE` only when criteria met.
- **No submission bundles** unless user requests.

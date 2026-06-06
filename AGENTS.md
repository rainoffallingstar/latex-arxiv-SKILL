# AGENTS.md

This repo uses an **issues-driven paper writing workflow** for academic review papers (Typst primary, LaTeX legacy).

## Workflow (issue-driven)
1) **Paper config**: generate `paper-config.yml` to set domain, output format, literature sources, citation style, and template.
2) **Research snapshot (no prose)**: translate topic → keywords → search 10-20 key papers across configured sources (use `literature_registry.py` or `paper-search` CLI).
3) **Scaffold project**: create the folder and base files (Typst by default) using `bootstrap_review_paper.py`; compile early to catch errors.
4) **Framework + titles**: build a section framework (headings + bullets + seed citations using `@key` syntax) and propose 2-4 titles.
5) **Draft plan**: document the framework, section/subsection plan, and writing approach.
6) **Gate**: after framework generation, only headings/bullets/seed cites until user approves the plan **and** issues CSV exists (no prose).
7) **Create issues CSV**: this is the execution contract; validate it and update as it evolves.
8) **Write per issue**: research → write → verify citations → update issue status + verified counts.
9) **QA + compile**: run internal QA checks, cross-ref dedup, and compile; fix errors before delivery.

## Non-negotiable rules
- **No prose before approval**: do not write into `main.typ` (or `main.tex`) until plan approved and issues CSV exists.
- **Issues CSV is the contract**: update it as you progress; only mark DONE when criteria met.
- **Insert issues when scope grows**: if a new non-trivial task is discovered mid-run, add/split/insert an issue row and keep going until all issues are `DONE`/`SKIP` (re-validate after edits).
- **Citations must be verified**: every citation must be checked against an online source before adding to `ref.bib`.
- **Use literature_registry.py**: use the multi-source registry for all literature discovery and BibTeX management; avoid ad-hoc commands. Also use `paper-search` CLI when available.
- **Typst is recommended** for compilation (single-pass `typst compile`); LaTeX is available as legacy option.
- **Keep issues CSV valid**: re-validate after edits.

# Academic Paper Writer Skill

A structured, issue-driven workflow for writing academic review papers using LLM-assisted peer review simulation.

## Directory Structure

```
.codex/skills/academic-paper-writer/
├── SKILL.md                       # Parent skill: workflow, phase routing, weakness routing
├── README.md                      # This file
├── scripts/                       # Automation scripts
│   ├── bootstrap_review_paper.py  # Scaffold new paper projects
│   ├── paper_config.py           # Generate paper-config.yml
│   ├── literature_registry.py    # Multi-source literature discovery + BibTeX
│   ├── lqs_scorer.py             # LQS scoring, depth classification, venue upgrade
│   ├── create_paper_plan.py      # Draft plan from framework
│   ├── run_review_simulation.py  # LLM-based peer review simulation (with no-LLM fallback)
│   ├── review_gaps.py            # Gap analysis against citation/paragraph targets
│   ├── compile_paper.py          # Typst/LaTeX compilation
│   ├── validate_paper_issues.py  # Validate issues CSV (+ --sync, --resume)
│   └── paper_utils.py            # Shared utilities (+ tool availability checks)
└── subskills/                     # Sub-skill specializations
    ├── literature-search/SKILL.md    # Literature survey + LQS scoring
    ├── structure-logic/SKILL.md      # Paper structure + logic patterns
    ├── figures-tables/SKILL.md       # Academic figure/table guidelines
    └── review-sim/                   # Peer review simulation
        ├── SKILL.md                  # Review simulation overview
        └── review-prompt-templates.md # Persona prompt templates
```

## Prerequisites

- **Python 3.9+**
- **Typst** (recommended) or **LaTeX** (legacy)
- One of:
  - **Gemini CLI** (`code .codex/skills/collaborating-with-gemini/`) for LLM review
  - **Claude CLI** (`code .codex/skills/collaborating-with-claude/`) as alternative

## Quick Start

### 1. Detect domain and generate paper config

```bash
# Detect domain from topic
python3 .codex/skills/academic-paper-writer/scripts/paper_config.py detect \
  --topic "Recent Advances in Transformer Architectures"

# Generate full config
python3 .codex/skills/academic-paper-writer/scripts/paper_config.py generate \
  --topic "Recent Advances in Transformer Architectures" \
  --output paper-config.yml
```

### 2. Scaffold project and discover literature

```bash
# Scaffold with Typst template (default)
python3 .codex/skills/academic-paper-writer/scripts/bootstrap_review_paper.py \
  --stage kickoff --topic "Recent Advances in Transformer Architectures" \
  --name transformer-review --out .

# Search for literature across all sources
python3 .codex/skills/academic-paper-writer/scripts/literature_registry.py \
  --project-dir ./transformer-review search all "transformer architecture attention"
```

### 3. Create issues CSV (after user approves plan)

```bash
python3 .codex/skills/academic-paper-writer/scripts/bootstrap_review_paper.py \
  --stage issues --topic "Recent Advances in Transformer Architectures" \
  --name transformer-review --out .
```

### 4. Validate and resume

```bash
# Validate issues CSV
python3 .codex/skills/academic-paper-writer/scripts/validate_paper_issues.py \
  transformer-review/issues/*.csv

# Find next actionable issue
python3 .codex/skills/academic-paper-writer/scripts/validate_paper_issues.py \
  transformer-review/issues/*.csv --resume
```

### 5. Score literature quality (LQS)

```bash
# Score all works in the registry
python3 .codex/skills/academic-paper-writer/scripts/lqs_scorer.py \
  --project-dir ./transformer-review score-all --threshold 5.0

# Generate quality report
python3 .codex/skills/academic-paper-writer/scripts/lqs_scorer.py \
  --project-dir ./transformer-review quality-report
```

### 6. Run review simulation

```bash
# Full LLM review (requires gemini or claude CLI)
python3 .codex/skills/academic-paper-writer/scripts/run_review_simulation.py \
  --project-dir ./transformer-review --round 1

# With 3 personas, using claude:
python3 .codex/skills/academic-paper-writer/scripts/run_review_simulation.py \
  --project-dir ./transformer-review --round 2 --personas 3 --llm claude

# Falls back to gap-analysis-only if no LLM bridge is installed
```

### 7. Analyze gaps

```bash
python3 .codex/skills/academic-paper-writer/scripts/review_gaps.py \
  --project-dir ./transformer-review analyze --round 1
```

### 8. Compile

```bash
# Typst (default)
python3 .codex/skills/academic-paper-writer/scripts/compile_paper.py \
  --project-dir ./transformer-review

# LaTeX (legacy)
python3 .codex/skills/academic-paper-writer/scripts/compile_paper.py \
  --project-dir ./transformer-review --format latex

# Markdown via pandoc
python3 .codex/skills/academic-paper-writer/scripts/compile_paper.py \
  --project-dir ./transformer-review --format markdown
```

## Core Workflow

1. **Phase 1: Draft** (target ≥6.0/10) — Scaffold, literature search, write, first review
2. **Phase 2: Deep Improvement** (target 7.5–8.0) — Address weaknesses, improve depth
3. **Phase 3: Sprint** (target ≥8.5) — Polish figures, fix citations, final compilation

Each phase triggers a review simulation with anti-inflation scoring:
- Round 1: capped at 7.0
- Each round: max +1.5 increase
- At least 1 unresolved weakness must remain

## Sub-skills Quick Reference

| Sub-skill | Focus |
|-----------|-------|
| `literature-search` | 4-stage pipeline: Recall → LQS Score → ABC Classify → Upgrade |
| `structure-logic` | Chapter architecture, paragraph patterns, MECE taxonomy |
| `figures-tables` | Table types, TikZ/matplotlib/PDF priority, density targets |
| `review-sim` | 5-persona review, weakness routing, anti-inflation rules |

## Citation Standards

- **LQS scoring**: Recency 30%, Citation Impact 25%, Venue 20%, Institution 10%, Acceptance 15%
- **≥7.0**: must cite; **5.0–7.0**: conditional; **<5.0**: drop
- **arXiv-only ratio**: must be ≤60%
- **Citations per major section**: ≥12, minor sections: ≥8

## Review Simulation

The review engine (`run_review_simulation.py`) simulates 3–5 reviewer personas:

| Persona | Focus | Weight |
|---------|-------|--------|
| R1-Experimentalist | Statistical rigor, baselines | 30% |
| R2-Theorist | Formal definitions, MECE | 35% |
| R3-Perfectionist | Writing quality, figures | 30% |
| R4-Synthesizer | Cross-cutting analysis | 25% |
| R5-Newcomer | Accessibility, examples | 35% |

Weaknesses are automatically routed to the appropriate sub-skill for remediation guidance.

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
│   ├── create_paper_plan.py      # Draft plan from framework
│   ├── run_review_simulation.py  # LLM-based peer review simulation
│   ├── review_gaps.py            # Gap analysis against citation/paragraph targets
│   ├── compile_paper.py          # Typst/LaTeX compilation
│   ├── validate_paper_issues.py  # Validate issues CSV
│   └── paper_utils.py            # Shared utilities
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

### 1. Set up paper config

```bash
python3 .codex/skills/academic-paper-writer/scripts/paper_config.py \
  --domain "Your Research Domain"
```

### 2. Discover literature

```bash
python3 .codex/skills/academic-paper-writer/scripts/literature_registry.py \
  --domain "topic" --keywords "key1,key2"
```

### 3. Scaffold project

```bash
python3 .codex/skills/academic-paper-writer/scripts/bootstrap_review_paper.py \
  --title "My Survey" --domain "topic" --output ./papers/my-survey
```

### 4. Create issues CSV

```bash
python3 .codex/skills/academic-paper-writer/scripts/create_paper_plan.py \
  --project-dir ./papers/my-survey
```

### 5. Run review simulation

```bash
python3 .codex/skills/academic-paper-writer/scripts/run_review_simulation.py \
  --project-dir ./papers/my-survey --round 1

# With 3 personas, using claude:
python3 .codex/skills/academic-paper-writer/scripts/run_review_simulation.py \
  --project-dir ./papers/my-survey --round 2 --personas 3 --llm claude
```

### 6. Analyze gaps

```bash
python3 .codex/skills/academic-paper-writer/scripts/review_gaps.py analyze \
  --project-dir ./papers/my-survey --round 1
```

### 7. Compile

```bash
python3 .codex/skills/academic-paper-writer/scripts/compile_paper.py \
  --project-dir ./papers/my-survey
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

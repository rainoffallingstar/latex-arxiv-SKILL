---
name: paper-literature-search
description: Multi-source literature discovery, BibTeX export, and citation verification.
---

> NOTE: The LQS scoring, depth classification (A/B/C/D), and venue upgrade features are planned but not yet implemented. Currently available: multi-source search, deduplication, BibTeX export, and citation verification.



# Literature Survey Sub-Skill

## Overview
4-stage pipeline: Recall -> Score (LQS) -> Classify (A/B/C/D) -> Upgrade (arXiv->accepted)

**IN:** topic + taxonomy keywords
**OUT:** references.bib + citation_plan.jsonl

## Stage 1: High-Recall Retrieval
- 20-30 keyword queries via `paper-search` CLI or `literature_registry.py`
- Each taxonomy cell: 3+ query variants (core terms, synonyms, method names)
- Snowball: seed paper citation networks
- Target: 200-500 raw candidates

## Stage 2: LQS Multi-Dimensional Scoring

| Dimension | Weight | Scoring |
|-----------|--------|---------|
| Recency | 30% | 6mo=10, 1yr=8, 2yr=5, 3yr=3 |
| Citation Impact | 25% | cites/mo >=50=10, >=10=8, >=3=6 |
| Venue | 20% | Top-tier=10, Strong=7, Workshop=4 |
| Institution | 10% | Top lab=10, Top uni=9 |
| Acceptance | 15% | Accepted=10, Under review=5, None=3 |

Thresholds: LQS >= 7.0 must-cite, 5.0-7.0 conditional, < 5.0 drop

## Stage 3: Citation Depth Classification
- A-level (1-3 paragraphs): section protagonist, 3-5 per chapter
- B-level (2-5 sentences): important insight, 5-10 per chapter
- C-level (1 sentence): supporting evidence
- D-level: dropped, not cited

## Stage 4: Venue Upgrade
- Cross-check DBLP + OpenReview for acceptance status
- arXiv with "Accepted at X" -> @inproceedings
- Target: arXiv-only ratio <= 60%

## Quality Gates
- Citations >= 80 (draft) / >= pages*3 (final)
- Within 1yr >= 40%
- Accepted >= 30%
- arXiv-only <= 60%
- Verification rate >= 80%
- Every taxonomy cell >= 2 A/B refs

---
name: paper-review-simulation
description: Multi-persona peer review simulation that drives the iteration loop by routing weaknesses back to sub-skills.
---

# Peer Review Simulation Sub-Skill

## Overview
Multi-persona scoring that drives the iteration loop by routing weaknesses back to sub-skills #1-4.

**IN:** compiled PDF
**OUT:** score + weakness list -> routed to corresponding sub-skill

## Reviewer Personas (3-5 per round)
| Persona | Focus | Scoring Weight |
|---------|-------|----------------|
| R1 Experimentalist | Statistical rigor, baselines, replication | Experimental 30% |
| R2 Theorist | Formal definitions, proofs, MECE taxonomy | Technical depth 35% |
| R3 Perfectionist | Writing quality, figures, formatting | Clarity 30% |
| R4 Synthesizer | Cross-cutting analysis, gap identification | Novelty 25% |
| R5 Newcomer | Accessibility, definitions, examples | Clarity 35% |

## Scoring Protocol
- Each reviewer scores independently (no anchoring)
- Final score = median of all reviewers
- Dimensions: Novelty, Comprehensiveness, Clarity, Technical Depth, Experimental Validation
- Calibration: 6.0=workshop, 7.0=main conference, 8.0=Strong Accept (top 20%), 9.0=Oral

## Anti-Inflation Rules
- First round score capped at 7.0 (every paper has room to improve)
- Max +1.5 per round
- At least 1 unresolved weakness must remain
- Different LLM model for at least 1 reviewer per round (diversity)

## Output Format
- Overall score + per-dimension scores
- 3-5 Strengths, 3-5 Weaknesses (prioritized Major/Minor)
- Concrete suggestions (actionable)
- Recommendation: Accept / Weak Accept / Borderline / Reject
- Regression check: are previously-fixed weaknesses still fixed?

## Execution
Run the review simulation script:
```bash
python3 scripts/run_review_simulation.py --project-dir <paper_dir> --round <N>
```

See also: review-prompt-templates.md for persona-specific prompts.

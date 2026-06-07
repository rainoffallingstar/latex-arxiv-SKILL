# Iterative Review Output Template

Copy this template and fill in the gaps identified by `review_gaps.py analyze`.
Use one template per review round.

---

## Round N Review

**Date:** YYYY-MM-DD
**Source file:** `main.typ` (or `main.tex`)
**Config:** min_citations_per_section = 8

---

## Section Citation Breakdown

| Section | Citations | Usages | Paragraphs | Status |
|---|---|---|---|---|
| Introduction | 12 | 18 | 6 | OK |
| Background | 9 | 14 | 5 | P1 — borderline |
| Core Methods | 14 | 22 | 8 | OK |
| Discussion | 3 | 5 | 3 | P0 — critical |
| Conclusion | 7 | 10 | 4 | P1 — borderline |

**Total unique citations:** 45
**Delta from previous round:** +8 (was 37 in R(N-1))

---

## Gap Table

| Priority | ID | Section | Issue | Est. Work | Impact |
|---|---|---|---|---|---|
| P0 | 1 | Discussion | Only 3 citations — core dimension uncovered | 2-4 paragraphs | Blocking: section not substantive without more evidence |
| P1 | 2 | Background | 9 citations meets minimum but lacks depth on sub-topic X | 1-2 paragraphs | Significant quality gain |
| P1 | 3 | Conclusion | 7 citations — borderline, could be strengthened | 1 paragraph | Improves synthesis and takeaway |
| P2 | 4 | Core Methods | Well-covered (14 cites) but only 8 paragraphs — could expand comparison table | Optional 1 para | Refinement |

---

## Items Fixed This Round

- [ ] P0-1: Added 5 references on sub-topic X (Discussion section)
- [ ] P1-2: Expanded Background on sub-topic Y
- [ ] P1-3: Strengthened Conclusion with synthesis references

---

## Round-over-Round Citation Growth

| Round | Total Cites | Delta | P0 | P1 | P2 | Sections |
|---|---|---|---|---|---|---|
| R1 | 28 | — | 3 | 4 | 1 | 8 |
| R2 | 41 | +13 | 1 | 3 | 1 | 8 |
| R3 | 52 | +11 | 0 | 2 | 2 | 8 |
| R4 | 59 | +7 | 0 | 1 | 1 | 8 |
| R5 | 60 | +1 | 0 | 0 | 0 | 8 |

---

## Maturity Assessment

Checklist for determining if the paper is ready for Phase 2.5:

- [ ] All sections have >= 8 verified citations
- [ ] No P0 gaps remain (critical dimensions missing)
- [ ] P1 gaps are resolved or explicitly deferred by user
- [ ] Total citations >= quality_targets.total_citations minimum (default 60)
- [ ] Abstract is drafted and reflects the complete paper
- [ ] All figures/tables are referenced in text
- [ ] Compilation passes with no `Overfull \hbox` warnings

**Recommendation:**
- If all checked: **proceed to Phase 2.5 (Rhythm Refinement)**
- If P0 remain: **continue review rounds until P0 = 0**
- If only P1/P2 remain: **ask user whether to fix or proceed**

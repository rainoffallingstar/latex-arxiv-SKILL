---
name: figures-tables
description: High information-density tables and vector figures for academic papers, with quality checklists and quantity targets.
---

# Academic Figures & Tables Sub-Skill

## Table Types
| Type | Use | Info Density |
|------|-----|--------------|
| Comparison Matrix | Methods x features | Very high |
| Benchmark Table | Models x metrics | High |
| Ablation Table | Conditions x results | High |
| Taxonomy Table | Classification visualization | Medium |
| Meta-analysis | Aggregated cross-paper data | Very high |

## Table Rules
- No vertical lines - booktabs three-line style only
- Alternating row color: \rowcolor{gray!6}
- Bold best results in each column
- All experimental data: mean +/- std
- Caption must contain key finding, not just description

## Figure Types & Tools
- Data-driven (curves, bars, heatmaps): matplotlib -> PDF
- Architecture/flow diagrams: TikZ or SVG->PDF
- Simple schematics: PIL -> PNG (acceptable per reviewer feedback)
- Priority: TikZ > matplotlib PDF > SVG->PDF > PIL PNG

## Quality Checklist
- Vector format (PDF) preferred, PNG >= 300 DPI
- Font size >= 10pt after scaling
- Academic palette: blue #2196F3, red #F44336, green #4CAF50, orange #FF9800
- All axes labeled, all lines have legend
- Light grid (alpha=0.3) for readability
- Self-contained: understandable without reading main text

## Quantity Targets
- Full survey (50+ pages): >= 10 tables, >= 6 figures
- Short survey (30 pages): >= 5 tables, >= 3 figures

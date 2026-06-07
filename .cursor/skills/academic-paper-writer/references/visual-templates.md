# Visual Guidance (Concise)

## Triggers (domain-agnostic)
| Content | Visualization |
|--------|---------------|
| 3+ related concepts | Concept map or Venn diagram |
| Process or pipeline | Flowchart |
| System or component relationships | Architecture / block diagram |
| Quantitative comparison | Table (+ optional plot) |
| Historical development | Timeline |
| Decision logic | Decision tree |
| Relationships | Node/link diagram |
| Taxonomies/categories | Classification tree |
| Biological pathways | Pathway map (TikZ) |
| Clinical trial results | Forest plot or summary table |
| Reaction sequences | Reaction scheme |

## Domain-Specific Visualization Guidance

### Computer Science / Engineering
- Architecture diagrams with labeled components and data flow arrows
- Comparison tables for models/methods (metrics aggregated from cited sources)
- Taxonomy trees for method classification (use `forest` package)

### Biomedical / Life Sciences
- Pathway and mechanism diagrams (receptors, kinases, transcription factors)
- Clinical trial summary tables (trial name, phase, N, endpoint, reference)
- Forest plots for meta-analyses; PRISMA flowcharts for systematic reviews

### Physics / Chemistry
- Schematic diagrams of experimental setups
- Phase diagrams and energy-level diagrams
- Reaction schemes with chemical structures

### Social Sciences
- Conceptual frameworks (boxes and arrows showing theoretical relationships)
- PRISMA flowcharts for systematic reviews
- Thematic analysis tables

## Requirements
> **Compiler note**: The LaTeX examples below use TikZ. For Typst projects, see
> `assets/typst-templates/` for ready-to-copy figure, table, and diagram templates
> with Typst-native syntax (`#figure()`, `#block()`, `#grid()`, `cetz`).
> The Typst ↔ LaTeX mapping table in the templates README helps translate syntax.
>
- **Layout-aware sizing**: use single-column width by default; switch to wide/two-column only when labels or data density require it
- **Optimize for readability**: avoid font sizes below `\footnotesize` in figures/tables
- **If a figure includes externally sourced content (nodes, labels, data), add citations (usually in the caption to avoid clutter)**
- Minimum 5 distinct visualization types per paper
- Every figure/table referenced in text
- Captions may include citations when appropriate

## Notes
- Use the approved outline to choose visuals; avoid inventing sections to fit a diagram
- Keep designs simple and readable; prioritize clarity over ornament
- Prefer low-saturation color accents for diagrams
- Adapt visuals to content (do not copy placeholders verbatim)

// Typst Figure Template
// Usage: copy the relevant block into your main.typ, replace placeholders.
//
// Key concepts:
//   - #figure() for auto-numbered figures with captions
//   - #image() for raster graphics (PNG, JPG)
//   - #block() + #place() for custom TikZ-like diagrams
//   - @figure-label for cross-references

// -------------------------------------------------------
// Template 1: Image-based figure (external graphic)
// -------------------------------------------------------
#figure(
  image("figures/architecture-diagram.png", width: 100%),
  caption: [
    Architecture overview. Key components: (A) input preprocessing,
    (B) core processing pipeline, (C) output generation.
    Adapted from @reference-key.
  ],
) <fig-architecture>

// -------------------------------------------------------
// Template 2: Auto-sized image in single column
// -------------------------------------------------------
#figure(
  image("figures/flowchart.pdf", width: 80%),
  caption: [Workflow of the proposed method.],
) <fig-flowchart>

// -------------------------------------------------------
// Template 3: Wide figure (spans full page width)
// -------------------------------------------------------
#figure(
  image("figures/large-diagram.png", width: 100%),
  caption: [Full-width system overview.],
  kind: "wide-figure",   // requires show rule in main.typ: show figure.where(kind: "wide-figure"): set par(columns: 1)
) <fig-wide>

// -------------------------------------------------------
// Template 4: Figure with sub-figures (side by side)
// -------------------------------------------------------
#figure(
  grid(
    columns: 2,
    gutter: 1em,
    image("figures/component-a.png", width: 100%),
    image("figures/component-b.png", width: 100%),
  ),
  caption: [
    Comparison of two architectural variants.
    (Left) Component A. (Right) Component B.
  ],
) <fig-comparison>

// -------------------------------------------------------
// Template 5: Block-based diagram (no external image needed)
// -------------------------------------------------------
#figure(
  {
    set align(center + horizon)
    block(
      width: 100%,
      inset: 12pt,
      fill: rgb("#f0f4f8"),
      stroke: 1pt + rgb("#3b82f6"),
      radius: 6pt,
      [
        *Input Data* \
        (raw sensor readings)
      ],
    )
    arrow-down
    block(
      width: 100%,
      inset: 12pt,
      fill: rgb("#e8f5e9"),
      stroke: 1pt + rgb("#22c55e"),
      radius: 6pt,
      [
        *Preprocessing* \
        normalization, filtering
      ],
    )
    arrow-down
    block(
      width: 100%,
      inset: 12pt,
      fill: rgb("#fff3e0"),
      stroke: 1pt + rgb("#f59e0b"),
      radius: 6pt,
      [
        *Core Model* \
        inference or prediction
      ],
    )
  },
  caption: [Three-stage processing pipeline.],
) <fig-pipeline-block>

// -------------------------------------------------------
// Helper: downward arrow between blocks
// -------------------------------------------------------
#let arrow-down = {
  align(center, text(size: 14pt, fill: rgb("#64748b"))[▼])
  v(4pt)
}

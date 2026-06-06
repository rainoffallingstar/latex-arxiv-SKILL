// Typst Diagram Templates
// For complex diagrams, consider using the `cetz` package:
//   #import "@preview/cetz:0.1.2": canvas, draw
//
// For simple diagrams, Typst's built-in #block(), #stack(), and #grid()
// can produce clean results without external dependencies.

// -------------------------------------------------------
// Template 1: Architecture / Block diagram (built-in only)
// -------------------------------------------------------
#figure(
  {
    set align(center)
    stack(
      dir: ttb,
      spacing: 8pt,

      // Top row: two input streams
      grid(
        columns: (1fr, 1fr),
        gutter: 12pt,
        block(fill: rgb("#e3f2fd"), stroke: 1pt + rgb("#1976d2"), radius: 4pt, inset: 8pt)[
          *Text Input* \
          raw text \& metadata
        ],
        block(fill: rgb("#e8f5e9"), stroke: 1pt + rgb("#388e3c"), radius: 4pt, inset: 8pt)[
          *Image Input* \
          pixel data \& labels
        ],
      ),

      v(4pt),

      // Center: encoder block
      block(
        width: 100%,
        fill: rgb("#fff3e0"),
        stroke: 1.5pt + rgb("#f57c00"),
        radius: 6pt,
        inset: 10pt,
        [
          *Multi-Modal Encoder* \
          cross-attention fusion layer \
          $arrow.r$ $arrow.r$ $arrow.r$ latent representation
        ],
      ),

      v(4pt),

      // Bottom row: two output heads
      grid(
        columns: (1fr, 1fr),
        gutter: 12pt,
        block(fill: rgb("#fce4ec"), stroke: 1pt + rgb("#c62828"), radius: 4pt, inset: 8pt)[
          *Classification Head* \
          label prediction
        ],
        block(fill: rgb("#f3e5f5"), stroke: 1pt + rgb("#7b1fa2"), radius: 4pt, inset: 8pt)[
          *Generation Head* \
          text/image output
        ],
      ),
    )
  },
  caption: [Multi-modal architecture with dual input streams, shared encoder,
  and task-specific output heads. Inspired by @reference-key.],
) <fig-architecture-blocks>

// -------------------------------------------------------
// Template 2: Flowchart (process steps)
// -------------------------------------------------------
#figure(
  {
    set align(center + horizon)
    let step(body, color) = block(
      width: 100%,
      fill: color,
      stroke: 0.5pt + rgb("#64748b"),
      radius: 4pt,
      inset: 8pt,
      body,
    )

    let arrow-right = {
      align(center, text(size: 14pt, fill: rgb("#64748b"))[→])
    }

    grid(
      columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
      rows: 1,
      gutter: 4pt,

      step([*Data* \ Collection], rgb("#e3f2fd")),
      arrow-right,
      step([*Pre-* \ processing], rgb("#e8f5e9")),
      arrow-right,
      step([*Model* \ Training], rgb("#fff3e0")),
      arrow-right,
      step([*Evaluation*], rgb("#fce4ec")),
    )
  },
  caption: [Four-stage workflow: data collection, preprocessing, model training,
  and evaluation.],
) <fig-flowchart-steps>

// -------------------------------------------------------
// Template 3: Concept map / Taxonomy tree
// -------------------------------------------------------
#figure(
  {
    set align(center)
    let node(body, color: rgb("#e3f2fd")) = block(
      fill: color,
      stroke: 0.5pt + rgb("#94a3b8"),
      radius: 4pt,
      inset: 6pt,
      width: 100%,
      body,
    )

    stack(
      dir: ttb,
      spacing: 4pt,

      // Root node
      node([*Machine Learning Methods*], color: rgb("#bbdefb")),

      // Vertical connector (simplified)
      align(center, text(size: 14pt, fill: rgb("#64748b"))[|]),

      // Level 1: three categories side by side
      grid(
        columns: (1fr, 1fr, 1fr),
        gutter: 8pt,
        node([*Supervised* \ Learning]),
        node([*Unsupervised* \ Learning]),
        node([*Reinforcement* \ Learning]),
      ),

      align(center, text(size: 10pt, fill: rgb("#94a3b8"))[| | |]),

      // Level 2: examples
      grid(
        columns: (1fr, 1fr, 1fr),
        gutter: 8pt,
        node([Classification \ Regression], color: rgb("#f0f4f8")),
        node([Clustering \ Dimensionality], color: rgb("#f0f4f8")),
        node([Q-Learning \ Policy Gradient], color: rgb("#f0f4f8")),
      ),
    )
  },
  caption: [Taxonomy of machine learning methods, organized by learning paradigm
  and representative algorithms.],
) <fig-taxonomy>

// -------------------------------------------------------
// Template 4: Timeline (horizontal)
// -------------------------------------------------------
#figure(
  {
    set align(center)
    let entry(year, desc) = block(
      width: 100%,
      fill: rgb("#f8fafc"),
      stroke: 1pt + rgb("#cbd5e1"),
      radius: 4pt,
      inset: 6pt,
      text(size: 9pt, [
        *year* \
        #desc
      ]),
    )

    grid(
      columns: (1fr, 1fr, 1fr, 1fr, 1fr),
      gutter: 4pt,
      entry([2017], [Transformer \ @vaswani2017]),
      entry([2018], [BERT \ @devlin2019]),
      entry([2020], [GPT-3 \ @brown2020]),
      entry([2022], [ChatGPT \ @openai2022]),
      entry([2023], [GPT-4 \ @openai2023]),
    )
  },
  caption: [Timeline of key developments in language models (2017--2023).
  Chronological order from left to right.],
) <fig-timeline>

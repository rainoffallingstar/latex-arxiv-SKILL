// ============================================================================
// ACADEMIC REVIEW PAPER TEMPLATE — Typst
// ============================================================================
// This template supports two citation styles via CSL:
//   - IEEE numbered:   #bibliography("ref.bib", style: "ieee")
//   - APA author-year: #bibliography("ref.bib", style: "apa")
//
// Citation syntax: @key for all styles (Typst renders per CSL).
// ============================================================================

// ---------------------------------------------------------------------------
// PAGE & TEXT SETUP
// ---------------------------------------------------------------------------
#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 2.5cm, right: 2.5cm),
  numbering: "1",
)

#set text(
  font: ("Libertinus Serif", "Noto Serif CJK SC", "Noto Serif CJK JP", "Noto Serif CJK KR"),
  size: 11pt,
  lang: "en",
)

#set par(
  justify: true,
  leading: 0.65em,
  first-line-indent: 0pt,
  spacing: 6pt,
)

// ---------------------------------------------------------------------------
// CITATION STYLE CONFIGURATION
// ---------------------------------------------------------------------------
// For IEEE numbered citations, use:
#bibliography("ref.bib", style: "ieee")

// For APA author-year citations, uncomment this and comment the IEEE line:
// #bibliography("ref.bib", style: "apa")
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// HEADING STYLES
// ---------------------------------------------------------------------------
#show heading.where(level: 1): set text(size: 16pt, weight: "bold")
#show heading.where(level: 1): set block(spacing: 18pt)
#show heading.where(level: 2): set text(size: 13pt, weight: "bold")
#show heading.where(level: 2): set block(spacing: 12pt)
#show heading.where(level: 3): set text(size: 11.5pt, weight: "bold")
#show heading.where(level: 3): set block(spacing: 8pt)

// ---------------------------------------------------------------------------
// HEADING NUMBERING (comment out for numbered, keep for unnumbered)
// ---------------------------------------------------------------------------
#set heading(numbering: "1. 1.1 1.1.1")

// ---------------------------------------------------------------------------
// TITLE PAGE
// ---------------------------------------------------------------------------
#align(center, [
  #text(size: 20pt, weight: "bold")[[Paper Title — Specific and Descriptive]]

  #v(0.8em)

  #text(size: 12pt, fill: gray)[
    Author 1#super[1,2,\*], Author 2#super[1], Author 3#super[3]
  ]

  #v(0.4em)

  #text(size: 9pt, fill: gray)[
    #super[1] Institution 1, Country \
    #super[2] Institution 2, Country \
    #super[3] Institution 3, Country
  ]

  #v(0.3em)

  #text(size: 9pt, fill: gray)[Correspondence: email\@example.com]

  #v(1.5em)
])

// ---------------------------------------------------------------------------
// KEYWORDS
// ---------------------------------------------------------------------------
#text(size: 10pt, weight: "bold")[Keywords:] #text(size: 10pt)[keyword1, keyword2, keyword3, keyword4, keyword5]

// ---------------------------------------------------------------------------
// ABSTRACT
// ---------------------------------------------------------------------------
#block(
  fill: luma(245),
  inset: 12pt,
  radius: 4pt,
  [
    #text(size: 11pt)[
      = Abstract
      [Write a concise abstract summarizing the paper's motivation, scope, key findings,
      and implications. Target 150-250 words. Use \@key for citations within the abstract.
      The abstract should reflect the completed paper — revisit after all sections are written.]
    ]
  ],
)

#pagebreak()

// ============================================================================
// PAPER SECTIONS
// ============================================================================

= Introduction
// --- placeholder: 2-4 bullet goals ---
// Replace bullets with prose. Never 3 consecutive sentences without a citation.
// Goals:
// - Establish context and motivation for this review
// - Define scope and key research questions
// - Outline the paper structure


= Background and Related Work
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Present foundational concepts and terminology
// - Summarize prior surveys and position this review relative to them
// - Identify gaps in existing literature


= Core Approaches and Methods
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Describe the main methodological families
// - Compare approaches with citations to key papers
// - Highlight trade-offs and design decisions


= Key Challenges and Open Problems
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Identify unresolved issues and limitations
// - Discuss reproducibility, scalability, or generality concerns
// - Propose directions for future work


= Future Directions
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Project emerging trends and promising research avenues
// - Suggest methodological improvements or new application domains
// - Connect to broader implications


= Conclusion
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Synthesize key takeaways (no new claims)
// - Restate the main contributions of this review
// - Offer closing perspective on the field's trajectory

// ============================================================================
// APPENDIX (optional, uncomment if needed)
// ============================================================================
// #pagebreak()
// = Appendix: Supplementary Material

// ============================================================================
// ACKNOWLEDGMENTS
// ============================================================================
#pagebreak()
= Acknowledgments
This work was supported by [FUNDING SOURCE — grant number if applicable].
We thank [NAMES] for helpful discussions and feedback.

// ============================================================================
// FIGURES & TABLES
// ============================================================================
// Use the templates in assets/typst-templates/ for:
//   - figure.template.typ   (images, sub-figures, block diagrams)
//   - table.template.typ    (data tables, clinical trial tables, comparisons)
//   - diagram.template.typ  (architecture, flowcharts, taxonomy, timelines)
//
// Key cross-reference syntax:
//   - Label a figure:  <fig-label>
//   - Reference it:    @fig-label
//   - Cite a source:   @citation-key
//   - Caption cite:    caption: [Description adapted from @citation-key.]

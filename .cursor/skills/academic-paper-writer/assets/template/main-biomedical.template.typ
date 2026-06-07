// ============================================================================
// BIOMEDICAL / LIFE SCIENCES REVIEW PAPER TEMPLATE — Typst
// ============================================================================
// Uses APA author-year citations (default for biomedical).
// To switch to numbered citations, change the bibliography style to IEEE.
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
  font: ("Libertinus Serif", "Noto Serif CJK SC"),
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
// Author-year (default for biomedical):
#bibliography("ref.bib", style: "apa")

// For IEEE numbered citations, uncomment this and comment the APA line:
// #bibliography("ref.bib", style: "ieee")
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
])

// ---------------------------------------------------------------------------
// KEYWORDS
// ---------------------------------------------------------------------------
#v(1.5em)
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
      [Write a concise abstract summarizing the disease context, molecular mechanisms reviewed,
      therapeutic approaches covered, and clinical implications. Target 150-250 words.
      Use \@key for citations within the abstract.]
    ]
  ],
)

#pagebreak()

// ============================================================================
// PAPER SECTIONS (biomedical domain framework)
// ============================================================================

= Introduction
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Establish the clinical significance of the disease or pathway
// - Define the scope of this review (mechanisms, therapies, trials)
// - Outline the paper structure


= Disease Overview and Clinical Context
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Describe the disease: epidemiology, risk factors, classification
// - Present current standard of care and unmet clinical needs
// - Cite key clinical guidelines and epidemiological studies


= Molecular Mechanisms
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Detail the molecular pathways implicated (signaling, genetic, epigenetic)
// - Discuss key proteins, receptors, and transcription factors
// - Connect mechanisms to disease phenotypes and therapeutic targets


= Therapeutic Approaches
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Review small molecule inhibitors, biologics, and gene therapies
// - Compare mechanisms of action across drug classes
// - Address resistance mechanisms and combination strategies


= Clinical Translation and Trials
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Summarize pivotal clinical trials (phase, N, endpoint, outcome)
// - Discuss biomarkers for patient stratification
// - Address translational bottlenecks from bench to bedside


= Future Perspectives
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Highlight emerging technologies (CRISPR, CAR-T, mRNA, AI-driven discovery)
// - Propose next-generation therapeutic strategies
// - Discuss personalized/precision medicine directions


= Conclusion
// --- placeholder: 2-4 bullet goals ---
// Goals:
// - Synthesize key takeaways across mechanisms, therapies, and trials
// - Restate the main contributions and clinical relevance
// - Offer closing perspective on the field's trajectory

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
//   - figure.template.typ   (mechanism diagrams, pathway maps, images)
//   - table.template.typ    (clinical trial tables, comparison tables, data tables)
//   - diagram.template.typ  (pathway schematics, taxonomy trees, timelines)
//
// Key cross-reference syntax:
//   - Label:         <fig-label>
//   - Reference:     @fig-label
//   - Cite source:   @citation-key
//   - Caption cite:  caption: [Results from @key.]

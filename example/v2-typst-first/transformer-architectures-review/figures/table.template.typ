// Typst Table Template
// Usage: copy the relevant block into your main.typ, replace placeholders.
//
// Key concepts:
//   - #table() for auto-numbered tables with captions
//   - columns: (auto, 1fr, ...) for column width control
//   - table.header for repeating header rows
//   - @table-label for cross-references

// -------------------------------------------------------
// Template 1: Simple data table with header
// -------------------------------------------------------
#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr),
    align: (left, center, center, center),
    table.header(
      [*Method*], [*Accuracy (%)*], [*F1 Score*], [*Source*],
    ),
    [BERT-base], [84.2], [82.1], [@devlin2019bert],
    [RoBERTa], [88.5], [86.3], [@liu2019roberta],
    [DeBERTa], [90.1], [88.7], [@he2021deberta],
    [GPT-4], [92.3], [90.8], [@openai2023gpt4],
  ),
  caption: [Performance comparison of language models on benchmark X.
  Metrics aggregated from cited sources. Bold values indicate SOTA.],
) <table-benchmark>

// -------------------------------------------------------
// Template 2: Clinical trial summary table
// -------------------------------------------------------
#figure(
  table(
    columns: (1fr, 1fr, auto, auto, auto, 1fr),
    align: (left, left, center, center, center, left),
    table.header(
      [*Trial*], [*Phase*], [*N*], [*Endpoint*], [*Year*], [*Reference*],
    ),
    [KEYNOTE-024], [III], [305], [PFS, OS], [2016], [@reck2016pembrolizumab],
    [CheckMate 017], [III], [272], [OS], [2015], [@brahmer2015nivolumab],
    [IMpower150], [III], [1202], [PFS, OS], [2018], [@socinski2018atezolizumab],
  ),
  caption: [Summary of pivotal clinical trials for immune checkpoint inhibitors
  in non-small cell lung cancer. Adapted from cited references.],
) <table-trials>

// -------------------------------------------------------
// Template 3: Numeric comparison with horizontal rules
// -------------------------------------------------------
#figure(
  table(
    columns: (1.5fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center),
    stroke: (x, y) => if y < 2 { (top: 0.5pt, bottom: 0.5pt) },
    inset: 8pt,
    table.header(
      [*Dataset*], [*Train*], [*Test*], [*Features*], [*Year*],
    ),
    [MNIST], [60,000], [10,000], [784], [1998],
    [CIFAR-10], [50,000], [10,000], [3072], [2009],
    [ImageNet], [1.28M], [50,000], [224x224x3], [2009],
  ),
  caption: [Common benchmark datasets used in the reviewed literature.],
) <table-datasets>

// -------------------------------------------------------
// Template 4: Long table for papers/survey comparison
// -------------------------------------------------------
#figure(
  table(
    columns: (2fr, 1fr, 1fr, 1.5fr),
    align: (left, center, center, left),
    table.header(
      [*Paper*], [*Year*], [*Citations*], [*Key Contribution*],
    ),
    [A Survey of LLMs @zhao2023survey], [2023], [1200+], [Comprehensive LLM taxonomy],
    [Attention Is All You Need @vaswani2017attention], [2017], [90k+], [Transformer architecture],
    [BERT @devlin2019bert], [2019], [80k+], [Bidirectional pre-training],
  ),
  caption: [Chronological comparison of key papers reviewed in this survey.
  Citation counts approximate as of 2024.],
) <table-paper-comparison>

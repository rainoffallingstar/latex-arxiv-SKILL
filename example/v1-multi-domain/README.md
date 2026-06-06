# Example: Multi-Domain Review Paper Generator

This directory contains example outputs demonstrating the framework's multi-domain capabilities.

## CRISPR Cancer Review (`crispr-cancer-review/`)

**Domain**: biomedical  
**Template**: article (single-column)  
**Citation style**: author-year (natbib + plainnat)  
**Literature source**: multi-source (PubMed + Europe PMC + OpenAlex)

This example shows the output of running:

```
write a review article about CRISPR gene editing for cancer therapy
```

Key differences from the ML/AI examples in `v0-single-SKILL/`:
- Uses `main-article.template.tex` (single-column article class) instead of IEEEtran two-column
- Uses `\citep{}` and `\citet{}` natbib commands instead of `\cite{}` numbered references
- `paper-config.yml` shows auto-detected biomedical domain configuration
- `ref.bib` includes PubMed and Europe PMC sourced entries
- `notes/literature-registry.sqlite3` demonstrates multi-source literature caching

## ML/AI Examples

- `v0-single-SKILL/` — Generative image models review (IEEEtran, arXiv-only, numbered citations)
- `v0.5-sqlite-multi-SKILLs/` — Video world simulators review (IEEEtran, arXiv + SQLite cache)

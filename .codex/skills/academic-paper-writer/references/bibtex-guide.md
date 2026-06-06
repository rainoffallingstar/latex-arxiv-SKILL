# BibTeX Guide (Multi-Source)

## Citation keys
- Use `firstauthorYEARfirstword` (e.g., `smith2023transformer`).
- Keep keys consistent with `\cite{key}` or `\citep{key}` usage.
- The literature registry auto-generates keys in this format.

## Author formatting
- Format names as `Last, First` and separate with `and`.
- Use `and others` for large author lists when appropriate.
- Escape special characters in names and titles (e.g., `&`, `%`, `_`, `#`, `{`, `}`) and represent accented characters with LaTeX commands when needed (e.g., `Garc{\'i}a`, `Fran{\c{c}}ois`, `Gr{\"o}bner`).

## Required fields by type
- `@article`: author, title, journal, year.
- `@inproceedings`: author, title, booktitle, year.
- `@book`: author/editor, title, publisher, year.
- `@misc`: author/title, howpublished or url, year.

## Source-specific fields

| Source | Extra Fields | Notes |
|--------|-------------|-------|
| arXiv | `eprint`, `archivePrefix`, `primaryClass` | Use `archivePrefix = {arXiv}` |
| PubMed | `pmid` | Include PMID for traceability |
| OpenAlex | `doi` | DOI is the canonical identifier |
| Europe PMC | `pmcid` | PMC ID links to OA full text |

## DOI priority
When a paper exists in multiple sources, prefer the DOI as the canonical link:
```bibtex
doi = {10.xxxx/xxxxx},
url = {https://doi.org/10.xxxx/xxxxx},
```

## Quality tips
- Include DOI and URL when available.
- Use braces to protect capitalization in titles (e.g., `{BERT}`, `{DNA}`, `{CRISPR}`).
- Use three-letter month abbreviations: jan, feb, mar, etc.
- Run `literature_registry.py cross-ref` to merge duplicate DOI entries across sources.

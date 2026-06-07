# Typst Templates for Academic Papers

Copy the relevant template blocks into your `main.typ` file and replace
placeholders with your content. All templates produce auto-numbered figures
and tables with cross-reference labels.

## Files

| File | Contents |
|------|----------|
| `figure.template.typ` | Image figures, sub-figures, block-based diagrams |
| `table.template.typ` | Data tables, clinical trial tables, comparison tables |
| `diagram.template.typ` | Architecture blocks, flowcharts, taxonomy trees, timelines |

## Usage

1. Copy the template block into `main.typ`.
2. Replace placeholder paths (e.g., `"figures/my-diagram.png"`), labels
   (e.g., `<fig-architecture>`), and citation keys (e.g., `@reference-key`).
3. Cross-reference figures in text using `@fig-architecture`.

## Typst vs LaTeX

| LaTeX / TikZ | Typst equivalent |
|---|---|
| `\includegraphics{file}` | `image("file", width: 100%)` |
| `\caption{...}` | `caption: [...]` |
| `\label{fig:foo}` | `<fig-foo>` |
| `\ref{fig:foo}` | `@fig-foo` |
| TikZ `\node`, `\draw` | `block()`, `stack()`, `grid()` or `cetz` package |
| `\begin{table}` | `#figure(table(...), caption: [...])` |
| `\cite{key}` | `@key` |

## Dependencies

For complex diagrams (arrow connections, shapes, precise positioning), install
the `cetz` package:

```typst
#import "@preview/cetz:0.1.2": canvas, draw
```

For simple block diagrams, the built-in `block()`, `stack()`, and `grid()`
functions (used in the templates) are sufficient.

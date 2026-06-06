# Research Workflow (Concise)

Purpose: build a verified, scoped literature base without over-collecting or drifting off-topic.

## Scope definition
- Clarify topic, intended contribution (survey/benchmark/application), and constraints
- Define the time window (default: 70%+ from the last 3 years relative to the plan as-of date)
- Identify the evaluation focus (metrics, datasets, baselines) only if relevant

## Phases

### Phase 0: Research snapshot (before outline)
**Target: 10-20 key papers**
- Identify core sub-areas and representative approaches
- Build a small “spine” set (foundational + recent flagships)
- Use this snapshot to propose outline, visuals, and clarification questions
- Do not expand to a large pool until scope is approved

### Phase 1: Initial discovery (before writing)
**Target: ~60-120 candidates; expect to cite ~60-80**
- Start from recent surveys and highly cited anchors
- Expand using keywords from the approved outline
- Verify and add to `ref.bib` immediately
- Use `literature_registry.py` with the sources configured in `paper-config.yml`.
  Cache searches and BibTeX to avoid duplicates:
  ```bash
  python3 scripts/literature_registry.py --project-dir <paper_dir> search all "<query>"
  ```
- Cross-source dedup: DOI-based merging via `cross-ref` command eliminates duplicates
- Avoid bulk dumps; prefer incremental, section-driven additions

### Phase 2: Per-section discovery (during writing)
**Target: 8-12 additional papers per section**
- Identify gaps or unsupported claims in the section
- Search, verify, and integrate immediately
- Repeat if gaps remain after drafting

## Keyword expansion (lightweight)
- Start from outline terms, then expand with synonyms and adjacent terms
- Prefer query refinement over broad, low-signal harvesting

## Relevance filter
**Keep** papers that directly support scope, provide essential context, or enable meaningful comparison.
**Reject** papers that are unrelated, unverifiable, redundant, or from low-quality venues.

## Verification protocol (mandatory)
1. **DOI verification** (preferred): run `verify-citation --doi <DOI>` via `literature_registry.py`. This queries CrossRef to confirm the DOI resolves to a real publication and returns verified metadata.
   ```bash
   python3 scripts/literature_registry.py --project-dir <paper_dir> verify-citation --doi "10.1234/example"
   ```
2. **Title+author fallback**: when no DOI is available, search by title:
   ```bash
   python3 scripts/literature_registry.py --project-dir <paper_dir> verify-citation --title "Paper Title" --author "Smith"
   ```
3. Web search + open source page (and PDF if available) as secondary sanity check.
4. **Only after verification passes**, export to ref.bib via `export-bibtex`.
5. Never add a citation to `ref.bib` without first passing the verification gate.


### Failure paths
When verification fails, proceed through these stages in order:

1. **Auto-cascade**: `verify-citation --doi` automatically retries via title
   search using metadata from the registry cache. No manual intervention needed.
   Use `--no-cascade` to disable.

2. **Manual confirmation**: open the paper's source page (DOI link or arXiv abs
   URL). Verify title, authors, and year match. Record via:
   ```bash
   verify-citation --manual --doi "..." --title "..." --authors "..." --year "..."
   ```

3. **Fact-driven re-search**: if the paper cannot be confirmed, extract the
   factual claim from the surrounding sentence. Search for alternative papers
   supporting the same claim, verify them, and replace the citation.
   See SKILL.md → "Fact-Driven Citation Replacement" for the full procedure.

4. **Discard**: if no alternative exists and the claim is non-critical, remove
   the citation and mark the claim as TODO. Ask the user to provide a source.

Batch-verify all pending citations with:
```bash
python3 scripts/literature_registry.py --project-dir <paper_dir> verify-all
```


## Evidence discipline
- Never fabricate citations or results
- Mark uncertainty as TODO and ask the user
- Use citations for all non-trivial claims

## Quality targets
- 100% verification rate
- 70%+ from the last 3 years
- Zero duplicates or hallucinated citations
- High relevance: every paper supports specific claims

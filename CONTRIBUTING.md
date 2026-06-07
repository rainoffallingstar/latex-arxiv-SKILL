# Contributing

## Setup

```bash
git clone https://github.com/renocrypt/latex-arxiv-skill
cd latex-arxiv-skill
pip install -e ".[test]"
pre-commit install
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

## Code Style

- Python: 4-space indentation, follow existing patterns
- YAML: 2-space indentation
- Markdown: wrap at 100 characters where practical
- Use type hints (`from __future__ import annotations`) in all Python scripts
- Add tests for new features in `tests/`

## Commit Messages

Use conventional commits:
- `feat:` for new features
- `fix:` for bug fixes
- `test:` for test additions/changes
- `docs:` for documentation
- `refactor:` for code restructuring
- `chore:` for build/config changes

## Skill Structure

Skills follow the [agent-skills-standard.md](agent-skills-standard.md) format:
- `SKILL.md` with YAML frontmatter and operational body
- `scripts/` for deterministic Python helpers
- `references/` for longer documentation
- `assets/` for templates and examples

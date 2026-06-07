.PHONY: test
SCRIPTS := .codex/skills/academic-paper-writer/scripts

test:
	python3 -m pytest tests/ -v

bootstrap:
	python3 $(SCRIPTS)/bootstrap_review_paper.py --stage kickoff --topic "$(TOPIC)"

compile:
	python3 $(SCRIPTS)/compile_paper.py --project-dir "$(PROJECT)"

validate:
	python3 $(SCRIPTS)/validate_paper_issues.py "$(PROJECT)/issues/"*.csv

review:
	python3 $(SCRIPTS)/run_review_simulation.py --project-dir "$(PROJECT)" --round $(ROUND)

"""Tests for run_review_simulation.py."""
import sys
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent.parent / ".codex/skills/academic-paper-writer/scripts"
sys.path.insert(0, str(SCRIPTS))
import run_review_simulation as rrs

def test_route_weaknesses_empty():
    assert rrs.route_weaknesses([]) == []

def test_route_weaknesses_known_pattern():
    result = rrs.route_weaknesses([{"text": "Citation coverage insufficient", "priority": "Major"}])
    assert result[0]["routed_to"] == "subskills/literature-search/SKILL.md"

def test_route_weaknesses_missing_visualizations():
    result = rrs.route_weaknesses([{"text": "Missing visualizations", "priority": "Major"}])
    assert result[0]["routed_to"] == "subskills/figures-tables/SKILL.md"

def test_generate_gaps_major_p0():
    w = [{"text": "Section lacks citations", "priority": "Major"}]
    gaps = rrs.generate_gaps(w, 6.0, {"Novelty": 5.0})
    assert gaps[0]["priority"] == "P0"

def test_generate_gaps_minor_p1():
    w = [{"text": "Minor issue", "priority": "Minor"}]
    gaps = rrs.generate_gaps(w, 6.0, {"Novelty": 3.0})
    assert gaps[0]["priority"] == "P1"

def test_apply_anti_inflation_round1():
    assert rrs.apply_anti_inflation(9.0, 1) == 7.0

def test_apply_anti_inflation_round2():
    assert rrs.apply_anti_inflation(9.0, 2) == 8.5

def test_reviewer_personas_count():
    assert len(rrs.REVIEWER_PERSONAS) == 5

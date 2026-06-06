"""Tests for review_gaps.py — gap analysis and classification."""

import json
import sys
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".codex" / "skills" / "academic-paper-writer" / "scripts"))

from review_gaps import (
    parse_sections,
    classify_gaps,
    format_gap_table,
    format_round_delta,
    load_history,
    save_history,
    record_round,
)


# ---------------------------------------------------------------------------
# Sample .tex content for testing
# ---------------------------------------------------------------------------

SAMPLE_TEX = r"""
\section{Introduction}
This is the introduction with some citations \cite{ref1,ref2}. More text here
with another reference \cite{ref3}. The intro has good coverage \cite{ref4,ref5}.

Some more intro text with references \cite{ref6,ref7,ref8,ref9,ref10}.

\section{Background}
The background section has some context \cite{ref11,ref12}. But not much depth
yet. Only a few citations here \cite{ref13}.

\section{Methods}
This section is very well covered \cite{ref14,ref15,ref16,ref17,ref18,ref19,
ref20,ref21,ref22,ref23,ref24,ref25}. Lots of depth and detail here.

\section{Discussion}
A short discussion with \cite{ref26,ref27}.

\section{Conclusion}
Wrapping up with final thoughts \cite{ref28,ref29,ref30,ref31,ref32,ref33,ref34}.
"""

SAMPLE_TYPST = """
= Introduction
This is the introduction with some citations @ref1 @ref2. More text here
with another reference @ref3.

= Background
The background section has some context @ref11 @ref12 @ref13.

= Methods
This section is well covered @ref14 @ref15 @ref16 @ref17 @ref18 @ref19
@ref20 @ref21 @ref22 @ref23 @ref24 @ref25.

= Discussion
A short discussion with @ref26 @ref27.

= Conclusion
Final thoughts @ref28 @ref29 @ref30 @ref31 @ref32 @ref33 @ref34.
"""


@pytest.fixture
def sample_tex(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(SAMPLE_TEX)
    return tex


@pytest.fixture
def sample_typst(tmp_path):
    typ = tmp_path / "main.typ"
    typ.write_text(SAMPLE_TYPST)
    return typ


@pytest.fixture
def temp_project(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Test parse_sections
# ---------------------------------------------------------------------------

class TestParseSections:
    def test_parse_tex_section_count(self, sample_tex):
        sections = parse_sections(sample_tex)
        assert len(sections) == 5

    def test_parse_tex_section_titles(self, sample_tex):
        sections = parse_sections(sample_tex)
        titles = [s["title"] for s in sections]
        assert "Introduction" in titles
        assert "Background" in titles
        assert "Methods" in titles
        assert "Discussion" in titles
        assert "Conclusion" in titles

    def test_parse_tex_citation_counts(self, sample_tex):
        sections = parse_sections(sample_tex)
        by_title = {s["title"]: s["citation_count"] for s in sections}
        # Introduction: ref1-ref10 = 10 unique keys
        assert by_title["Introduction"] == 10
        # Background: ref11-ref13 = 3
        assert by_title["Background"] == 3
        # Methods: ref14-ref25 = 12
        assert by_title["Methods"] == 12
        # Discussion: ref26-ref27 = 2
        assert by_title["Discussion"] == 2
        # Conclusion: ref28-ref34 = 7
        assert by_title["Conclusion"] == 7

    def test_parse_typst(self, sample_typst):
        sections = parse_sections(sample_typst)
        assert len(sections) == 5
        by_title = {s["title"]: s["citation_count"] for s in sections}
        assert by_title["Introduction"] == 3
        assert by_title["Background"] == 3
        assert by_title["Methods"] == 12

    def test_empty_file(self, tmp_path):
        empty = tmp_path / "empty.tex"
        empty.write_text("")
        sections = parse_sections(empty)
        assert sections == []


# ---------------------------------------------------------------------------
# Test classify_gaps
# ---------------------------------------------------------------------------

class TestClassifyGaps:
    def test_p0_for_low_citations(self, sample_tex):
        sections = parse_sections(sample_tex)
        gaps = classify_gaps(sections, min_citations=8)
        priorities = {g["section"]: g["priority"] for g in gaps}
        # Discussion has 2 cites -> P0
        assert priorities.get("Discussion") == "P0"
        # Background has 3 cites -> P0
        assert priorities.get("Background") == "P0"

    def test_p1_for_borderline(self, sample_tex):
        sections = parse_sections(sample_tex)
        gaps = classify_gaps(sections, min_citations=8)
        priorities = {g["section"]: g["priority"] for g in gaps}
        # Methods has 12 cites, not P0. But let's test with a lower min:
        # With min_citations=6, Introduction (10) meets threshold,
        # Conclusion (7) is borderline P1.
        gaps_alt = classify_gaps(sections, min_citations=6)
        priorities_alt = {g["section"]: g["priority"] for g in gaps_alt}
        # Conclusion has 7 >= 6, but 7 < 9 (6*1.5) -> P1 borderline
        assert priorities_alt.get("Conclusion") == "P1"

    def test_gap_for_low_below_min(self, sample_tex):
        sections = parse_sections(sample_tex)
        gaps = classify_gaps(sections, min_citations=8)
        priorities = {g["section"]: g["priority"] for g in gaps}
        # Conclusion has 7 < 8 -> P0 (below min)
        assert priorities.get("Conclusion") == "P0"

    def test_no_gap_for_well_covered(self, sample_tex):
        sections = parse_sections(sample_tex)
        gaps = classify_gaps(sections, min_citations=8)
        priorities = {g["section"]: g["priority"] for g in gaps}
        # Introduction has 10 cites (>= 8 but < 12) → P1 (borderline)
        assert priorities.get("Introduction") == "P1"
        # Methods has 12 cites (>= 12) but low paragraphs → P2
        assert priorities.get("Methods") == "P2"

    def test_custom_min_citations(self, sample_tex):
        sections = parse_sections(sample_tex)
        # With min_citations=5, Background (3) still P0, Discussion (2) still P0
        gaps = classify_gaps(sections, min_citations=5)
        priorities = {g["section"]: g["priority"] for g in gaps}
        assert priorities.get("Discussion") == "P0"

    def test_no_gaps_when_all_covered(self):
        # Well-covered sections with no gaps
        sections = [
            {"title": "Intro", "citation_count": 15, "paragraph_count": 10},
            {"title": "Methods", "citation_count": 20, "paragraph_count": 12},
            {"title": "Results", "citation_count": 18, "paragraph_count": 10},
        ]
        gaps = classify_gaps(sections, min_citations=8)
        assert len(gaps) == 0


# ---------------------------------------------------------------------------
# Test history tracking
# ---------------------------------------------------------------------------

class TestHistoryTracking:
    def test_load_empty_history(self, temp_project):
        history = load_history(temp_project)
        assert history == []

    def test_save_and_load(self, temp_project):
        history = [
            {"round": 1, "total_citations": 28, "p0_count": 3},
        ]
        save_history(temp_project, history)
        loaded = load_history(temp_project)
        assert len(loaded) == 1
        assert loaded[0]["total_citations"] == 28

    def test_record_round_appends(self, temp_project):
        sections = [{"title": "Intro", "citation_count": 10}]
        gaps = [{"priority": "P0", "section": "Intro", "issue": "too few cites"}]
        record_round(temp_project, 1, 10, sections, gaps)
        record_round(temp_project, 2, 20, sections, [])
        history = load_history(temp_project)
        assert len(history) == 2
        assert history[0]["round"] == 1
        assert history[1]["round"] == 2
        assert history[1]["total_citations"] == 20

    def test_format_round_delta(self, temp_project):
        history = [
            {"round": 1, "total_citations": 28, "section_count": 8, "p0_count": 3, "p1_count": 4, "p2_count": 1},
            {"round": 2, "total_citations": 41, "section_count": 8, "p0_count": 1, "p1_count": 3, "p2_count": 1},
            {"round": 3, "total_citations": 52, "section_count": 8, "p0_count": 0, "p1_count": 2, "p2_count": 2},
        ]
        output = format_round_delta(history)
        assert "R1" in output
        assert "R2" in output
        assert "R3" in output
        assert "+13" in output  # 41-28
        assert "+11" in output  # 52-41


# ---------------------------------------------------------------------------
# Test format_gap_table
# ---------------------------------------------------------------------------

class TestFormatGapTable:
    def test_format_empty(self):
        output = format_gap_table([], 1)
        assert "No gaps detected" in output

    def test_format_with_gaps(self):
        gaps = [
            {"priority": "P0", "section": "Discussion", "issue": "too few cites",
             "est_work": "2-4 paragraphs", "impact": "critical", "citation_count": 2, "min_expected": 8},
            {"priority": "P1", "section": "Conclusion", "issue": "borderline",
             "est_work": "1-2 paragraphs", "impact": "quality gain", "citation_count": 7, "min_expected": 8},
        ]
        output = format_gap_table(gaps, 2)
        assert "P0" in output
        assert "P1" in output
        assert "Discussion" in output
        assert "Round 2" in output
        assert "Auto-Fix Guidance" in output

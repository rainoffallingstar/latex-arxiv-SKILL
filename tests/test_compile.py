"""Tests for compile_paper.py — compilation and cross-reference utilities."""

import sys
from pathlib import Path

import pytest

# Import from scripts directory
from paper_utils import (
    check_typst_available,
    check_latex_available,
    check_compiler_available,
    count_citations,
    count_bibtex_entries,
    detect_citation_style,
    load_config,
    get_template_for_domain,
    check_tool,
)


class TestTypstAvailability:
    def test_returns_dict(self):
        result = check_typst_available()
        assert isinstance(result, dict)
        assert "available" in result
        assert "typst" in result
        assert "pandoc" in result

    def test_available_is_boolean(self):
        result = check_typst_available()
        assert isinstance(result["available"], bool)


class TestLatexAvailability:
    def test_returns_dict(self):
        result = check_latex_available()
        assert isinstance(result, dict)
        assert "available" in result
        assert "pdflatex" in result
        assert "bibtex" in result

    def test_available_is_boolean(self):
        result = check_latex_available()
        assert isinstance(result["available"], bool)


class TestCompilerAvailability:
    def test_typst_compiler(self):
        result = check_compiler_available("typst")
        assert result["compiler"] == "typst"

    def test_latex_compiler(self):
        result = check_compiler_available("latex")
        assert result["compiler"] == "latex"


class TestCountCitations:
    def test_typst_citations(self, tmp_path):
        source = tmp_path / "main.typ"
        source.write_text(
            "= Introduction\n"
            "Some text @ref1 and more @ref2. Also @ref1 again.\n"
            "= Methods\n"
            "More text @ref3 @ref4."
        )
        result = count_citations(source)
        assert result["unique"] == 4
        assert result["total"] == 5  # ref1 appears twice

    def test_latex_citations(self, tmp_path):
        source = tmp_path / "main.tex"
        source.write_text(
            r"\section{Intro}"
            r"Text \cite{ref1,ref2} and \citep{ref3}. "
            r"\section{Methods}"
            r"More \cite{ref4,ref5}."
        )
        result = count_citations(source)
        assert result["unique"] == 5

    def test_empty_file(self, tmp_path):
        source = tmp_path / "main.typ"
        source.write_text("No citations here.")
        result = count_citations(source)
        assert result["unique"] == 0
        assert result["total"] == 0

    def test_missing_file(self, tmp_path):
        source = tmp_path / "nonexistent.typ"
        result = count_citations(source)
        assert result["unique"] == 0


class TestCountBibtexEntries:
    def test_entries_with_years(self, tmp_path):
        bib = tmp_path / "ref.bib"
        bib.write_text(
            r"""@article{ref1,
  author = {Smith},
  title = {Paper One},
  year = {2024},
}
@inproceedings{ref2,
  author = {Jones},
  title = {Paper Two},
  year = {2023},
}
@misc{ref3,
  author = {Brown},
  title = {Paper Three},
  year = {2024},
}
"""
        )
        result = count_bibtex_entries(bib)
        assert result["total"] == 3
        assert result["by_year"]["2024"] == 2
        assert result["by_year"]["2023"] == 1

    def test_missing_file(self, tmp_path):
        bib = tmp_path / "nonexistent.bib"
        result = count_bibtex_entries(bib)
        assert result["total"] == 0


class TestDetectCitationStyle:
    def test_typst_author_year(self, tmp_path):
        source = tmp_path / "main.typ"
        source.write_text('#set bibliography(style: "apa.csl")\nSome text.')
        result = detect_citation_style(source)
        assert result == "author-year"

    def test_typst_ieee(self, tmp_path):
        source = tmp_path / "main.typ"
        source.write_text('#set bibliography(style: "ieee.csl")\nSome text.')
        result = detect_citation_style(source)
        assert result == "ieee"

    def test_typst_default(self, tmp_path):
        source = tmp_path / "main.typ"
        source.write_text("Some text without explicit style.")
        result = detect_citation_style(source)
        assert result == "author-year"

    def test_latex_natbib(self, tmp_path):
        source = tmp_path / "main.tex"
        source.write_text(r"\usepackage{natbib}" + "\nSome text.")
        result = detect_citation_style(source)
        assert result == "author-year"

    def test_latex_default(self, tmp_path):
        source = tmp_path / "main.tex"
        source.write_text(r"\usepackage{graphicx}" + "\nSome text.")
        result = detect_citation_style(source)
        assert result == "ieee"


class TestLoadConfig:
    def test_defaults_when_missing(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yml")
        assert config["output_format"] == "typst"
        assert config["domain"] == "general"

    def test_load_valid_yaml(self, tmp_path):
        import yaml
        config_path = tmp_path / "paper-config.yml"
        config_path.write_text("topic: Test\noutput_format: latex\ndomain: physics\n")
        config = load_config(config_path)
        assert config["domain"] == "physics"
        assert config["output_format"] == "latex"


class TestGetTemplateForDomain:
    def test_cs_typst_ieee(self):
        tmpl, cls = get_template_for_domain("computer-science", "typst", "ieee")
        assert "main.template.typ" in tmpl

    def test_biomedical_typst(self):
        tmpl, cls = get_template_for_domain("biomedical", "typst")
        assert "biomedical" in tmpl

    def test_general_latex(self):
        tmpl, cls = get_template_for_domain("general", "latex")
        assert tmpl.endswith(".tex")

    def test_markdown_uses_typst_template(self):
        tmpl, cls = get_template_for_domain("general", "markdown")
        assert tmpl.endswith(".typ")

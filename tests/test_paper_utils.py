"""Tests for paper_utils.py — helper functions."""

from pathlib import Path

import pytest
from paper_utils import (
    slugify,
    validate_slug,
    validate_timestamp,
    now_timestamp,
    count_citations,
    count_bibtex_entries,
    detect_citation_style,
    get_template_for_domain,
    load_config,
    resolve_registry_db_path,
    check_typst_available,
    check_compiler_available,
)


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("CRISPR gene  editing") == "crispr-gene-editing"

    def test_special_chars(self):
        assert slugify("AI/ML: A Review") == "ai-ml-a-review"

    def test_max_length(self):
        long_topic = "a" * 100 + " b"
        result = slugify(long_topic)
        assert len(result) <= 60

    def test_empty_returns_paper(self):
        assert slugify("!!!") == "paper"


class TestValidate:
    def test_valid_slug(self):
        validate_slug("transformer-vision-review")

    def test_invalid_slug_raises(self):
        with pytest.raises(ValueError):
            validate_slug("Invalid Slug!")

    def test_valid_timestamp(self):
        validate_timestamp("2026-06-04_12-00-00")

    def test_invalid_timestamp_raises(self):
        with pytest.raises(ValueError):
            validate_timestamp("2026/06/04")

    def test_now_timestamp_format(self):
        ts = now_timestamp()
        validate_timestamp(ts)


class TestCitationCounting:
    def test_count_cite(self, tmp_path):
        tex = tmp_path / "test.tex"
        tex.write_text(r"Hello \cite{key1,key2} world \cite{key3}.")
        result = count_citations(tex)
        assert result["unique"] == 3

    def test_count_citep(self, tmp_path):
        tex = tmp_path / "test.tex"
        tex.write_text(r"Hello \citep{key1} world \citet{key2}.")
        result = count_citations(tex)
        assert result["unique"] == 2

    def test_count_typst(self, tmp_path):
        typ = tmp_path / "test.typ"
        typ.write_text(r"Hello @key1 world @key2 and @key3.")
        result = count_citations(typ)
        assert result["unique"] == 3

    def test_count_empty_file(self, tmp_path):
        tex = tmp_path / "test.tex"
        tex.write_text("No citations here.")
        result = count_citations(tex)
        assert result["unique"] == 0

    def test_count_missing_file(self, tmp_path):
        result = count_citations(tmp_path / "nonexistent.tex")
        assert result["unique"] == 0

    def test_count_bibtex(self, tmp_path):
        bib = tmp_path / "test.bib"
        bib.write_text("""
@article{key1,
  title = {Test},
  author = {Author},
  year = {2023},
}
@inproceedings{key2,
  title = {Test2},
  author = {Author},
  booktitle = {Conf},
  year = {2024},
}
""")
        result = count_bibtex_entries(bib)
        assert result["total"] == 2
        assert result["by_year"]["2023"] == 1
        assert result["by_year"]["2024"] == 1


class TestCitationStyleDetection:
    def test_detect_ieee_latex(self, tmp_path):
        tex = tmp_path / "test.tex"
        tex.write_text(r"\usepackage{cite}" "\n" r"\bibliographystyle{ieeetr}")
        assert detect_citation_style(tex) == "ieee"

    def test_detect_author_year_latex(self, tmp_path):
        tex = tmp_path / "test.tex"
        tex.write_text(r"\usepackage{natbib}" "\n" r"\bibliographystyle{plainnat}")
        assert detect_citation_style(tex) == "author-year"

    def test_detect_ieee_typst(self, tmp_path):
        typ = tmp_path / "test.typ"
        typ.write_text(r'#bibliography("ref.bib", style: "ieee.csl")')
        assert detect_citation_style(typ) == "ieee"

    def test_detect_apa_typst(self, tmp_path):
        typ = tmp_path / "test.typ"
        typ.write_text(r'#bibliography("ref.bib", style: "apa.csl")')
        assert detect_citation_style(typ) == "author-year"

    def test_detect_missing_file(self, tmp_path):
        assert detect_citation_style(tmp_path / "nonexistent.tex") == "ieee"


class TestTemplateForDomain:
    def test_cs_domain_typst(self):
        template, docclass = get_template_for_domain("computer-science", "typst")
        assert template == "main.template.typ"
        assert docclass == "IEEEtran"

    def test_biomedical_domain_typst(self):
        template, docclass = get_template_for_domain("biomedical", "typst")
        assert template == "main-biomedical.template.typ"
        assert docclass == "article"

    def test_physics_domain_typst(self):
        template, docclass = get_template_for_domain("physics", "typst")
        assert template == "main.template.typ"
        assert docclass == "article"

    def test_cs_domain_latex(self):
        template, docclass = get_template_for_domain("computer-science", "latex")
        assert template in ("main.template.tex", "main-article.template.tex")
        assert docclass in ("IEEEtran", "article")

    def test_biomedical_domain_latex(self):
        template, docclass = get_template_for_domain("biomedical", "latex")
        assert template == "main-biomedical.template.tex"
        assert docclass == "article"


class TestCompilerAvailability:
    def test_check_typst_available(self):
        result = check_typst_available()
        assert isinstance(result, dict)
        assert "available" in result

    def test_check_compiler_typst(self):
        result = check_compiler_available("typst")
        assert result["compiler"] == "typst"

    def test_check_compiler_latex(self):
        result = check_compiler_available("latex")
        assert result["compiler"] == "latex"


class TestConfigLoading:
    def test_missing_config_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yml")
        assert config["template_class"] == "article"
        assert config["citation_style"] == "author-year"
        assert config["output_format"] == "typst"


class TestRegistryDBPath:
    def test_resolve(self):
        path = resolve_registry_db_path("/tmp/test")
        assert str(path).endswith("literature-registry.sqlite3")

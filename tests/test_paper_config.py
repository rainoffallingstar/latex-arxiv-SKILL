"""Tests for paper_config.py — domain detection, config generation, validation."""

import pytest
from paper_config import detect_domain, generate_config, validate_config, get_recommended_output_format


class TestDomainDetection:
    def test_detect_cs(self):
        domain, conf = detect_domain("recent advances in transformer architectures")
        assert domain == "computer-science"
        assert conf > 0

    def test_detect_biomedical(self):
        domain, conf = detect_domain("CRISPR gene editing for cancer therapy")
        assert domain == "biomedical"
        assert conf > 0

    def test_detect_physics(self):
        domain, conf = detect_domain("gravitational wave detection advances")
        assert domain == "physics"
        assert conf > 0

    def test_detect_chemistry(self):
        domain, conf = detect_domain("recent advances in organic chemistry synthesis")
        assert domain == "chemistry"
        assert conf > 0

    def test_detect_social_sciences(self):
        domain, conf = detect_domain("behavioral economics and cognitive psychology")
        assert domain == "social-sciences"
        assert conf > 0

    def test_detect_environmental(self):
        domain, conf = detect_domain("climate change impacts on biodiversity and ecosystems")
        assert domain == "environmental"
        assert conf > 0

    def test_detect_general_fallback(self):
        domain, conf = detect_domain("xyzzy foobar nonsense")
        assert domain == "general"
        assert conf == 0.0

    def test_detect_math(self):
        domain, conf = detect_domain("differential geometry and topology methods")
        assert domain == "mathematics"
        assert conf > 0

    def test_short_word_boundary_llm(self):
        domain, conf = detect_domain("LLM reasoning capabilities")
        assert domain == "computer-science"

    def test_short_word_no_false_match(self):
        """'robot' removed from CS patterns; 'robotic surgery' should not match CS."""
        domain, _ = detect_domain("robotic surgery for cancer treatment")
        assert domain != "computer-science"


class TestConfigGeneration:
    def test_generate_cs_config(self):
        config = generate_config("transformer architectures review")
        assert config["topic"] == "transformer architectures review"
        assert config["domain"] == "computer-science"
        assert config["template_class"] == "IEEEtran"
        assert config["citation_style"] == "ieee"
        assert config["output_format"] == "typst"
        assert "arxiv" in config["preferred_sources"]

    def test_generate_biomedical_config(self):
        config = generate_config("CRISPR gene editing for cancer therapy")
        assert config["domain"] == "biomedical"
        assert config["template_class"] == "article"
        assert config["citation_style"] == "author-year"
        assert config["output_format"] == "typst"
        assert "pubmed" in config["preferred_sources"]

    def test_generate_physics_config(self):
        config = generate_config("gravitational wave detection")
        assert config["domain"] == "physics"
        assert config["template_class"] == "article"
        assert config["output_format"] == "typst"
        assert "arxiv" in config["preferred_sources"]

    def test_generate_with_overrides(self):
        config = generate_config(
            "some topic",
            domain="physics",
            output_format="latex",
            template_class="IEEEtran",
            citation_style="ieee",
        )
        assert config["template_class"] == "IEEEtran"
        assert config["citation_style"] == "ieee"
        assert config["domain"] == "physics"
        assert config["output_format"] == "latex"


class TestConfigValidation:
    def test_valid_config_passes(self):
        config = generate_config("test topic")
        errors = validate_config(config)
        assert errors == []

    def test_missing_required_field(self):
        errors = validate_config({"topic": "test"})
        assert len(errors) > 0

    def test_invalid_template_class(self):
        errors = validate_config({
            "topic": "test",
            "domain": "general",
            "output_format": "typst",
            "template_class": "invalid-class",
            "citation_style": "ieee",
            "preferred_sources": ["openalex"],
            "section_framework": ["Intro"],
        })
        assert any("template_class" in e.lower() for e in errors)

    def test_invalid_citation_style(self):
        errors = validate_config({
            "topic": "test",
            "domain": "general",
            "output_format": "typst",
            "template_class": "article",
            "citation_style": "unknown-style",
            "preferred_sources": ["openalex"],
            "section_framework": ["Intro"],
        })
        assert any("citation_style" in e.lower() for e in errors)

    def test_invalid_source(self):
        errors = validate_config({
            "topic": "test",
            "domain": "general",
            "output_format": "typst",
            "template_class": "article",
            "citation_style": "ieee",
            "preferred_sources": ["google-scholar"],
            "section_framework": ["Intro"],
        })
        assert any("invalid preferred_source" in e.lower() for e in errors)

    def test_invalid_output_format(self):
        errors = validate_config({
            "topic": "test",
            "domain": "general",
            "output_format": "invalid-format",
            "template_class": "article",
            "citation_style": "ieee",
            "preferred_sources": ["openalex"],
            "section_framework": ["Intro"],
        })
        assert any("output_format" in e.lower() for e in errors)

    def test_valid_paper_search_source(self):
        errors = validate_config({
            "topic": "test",
            "domain": "general",
            "output_format": "typst",
            "template_class": "article",
            "citation_style": "ieee",
            "preferred_sources": ["paper-search", "openalex"],
            "section_framework": ["Intro"],
        })
        assert errors == []


class TestLanguageDetection:
    """Tests for CJK language detection and output format recommendation."""

    def test_detect_english(self):
        from paper_config import detect_language
        assert detect_language("transformer architectures for NLP") == "en"

    def test_detect_chinese(self):
        from paper_config import detect_language
        assert detect_language("深度学习在自然语言处理中的应用") == "zh"

    def test_detect_mixed_cjk_latin(self):
        from paper_config import detect_language
        assert detect_language("CRISPR基因编辑技术在癌症治疗中的应用 review") == "mixed"

    def test_detect_japanese(self):
        from paper_config import detect_language
        assert detect_language("ディープラーニングの応用") == "ja"

    def test_detect_korean(self):
        from paper_config import detect_language
        assert detect_language("딥러닝을 이용한 자연어 처리") == "ko"

    def test_output_format_default(self):
        assert get_recommended_output_format("zh") == "typst"
        assert get_recommended_output_format("en") == "typst"
        assert get_recommended_output_format("ja") == "typst"

    def test_generate_config_with_cjk_topic(self):
        config = generate_config("深度学习在自然语言处理中的应用综述")
        assert config["language"] in ("zh", "mixed")
        assert config["output_format"] == "typst"

    def test_generate_config_english_topic(self):
        config = generate_config("transformer architectures review")
        assert config["language"] == "en"
        assert config["output_format"] == "typst"

    def test_language_override(self):
        config = generate_config("some topic", language="zh")
        assert config["language"] == "zh"
        assert config["output_format"] == "typst"

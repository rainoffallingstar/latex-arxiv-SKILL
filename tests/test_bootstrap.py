"""Tests for bootstrap_review_paper.py — project scaffolding and template handling."""

import sys
from pathlib import Path

import pytest

# Import from scripts directory (added to path by conftest.py)
from paper_utils import (
    slugify,
    validate_slug,
    validate_timestamp,
    now_timestamp,
    build_plan_filename,
    build_issues_filename,
    get_template_dir,
    get_latex_template_dir,
    get_typst_fragment_dir,
    get_assets_dir,
    get_skill_root,
    resolve_registry_db_path,
)


class TestSlugify:
    def test_basic_topic(self):
        assert slugify("Transformer Architectures Review") == "transformer-architectures-review"

    def test_special_characters(self):
        assert slugify("CRISPR: Gene Editing & Therapy") == "crispr-gene-editing-therapy"

    def test_long_topic_truncated(self):
        long_topic = "A Comprehensive Survey of Very Long Topic " * 3
        result = slugify(long_topic)
        assert len(result) <= 60

    def test_chinese_characters(self):
        result = slugify("深度学习综述")
        assert result == "paper"  # CJK chars stripped, fallback to 'paper'

    def test_multiple_dashes(self):
        assert slugify("hello---world") == "hello-world"

    def test_leading_trailing_dashes(self):
        assert slugify("-hello world-") == "hello-world"


class TestValidateSlug:
    def test_valid_slug(self):
        validate_slug("transformer-review")

    def test_invalid_slug_uppercase(self):
        with pytest.raises(ValueError):
            validate_slug("Transformer-Review")

    def test_invalid_slug_special_chars(self):
        with pytest.raises(ValueError):
            validate_slug("transformer_review")


class TestValidateTimestamp:
    def test_valid_timestamp(self):
        validate_timestamp("2025-12-27_12-43-32")

    def test_invalid_timestamp(self):
        with pytest.raises(ValueError):
            validate_timestamp("2025/12/27")


class TestNowTimestamp:
    def test_format(self):
        ts = now_timestamp()
        assert len(ts) == 19  # YYYY-MM-DD_HH-mm-ss
        validate_timestamp(ts)


class TestBuildFilenames:
    def test_build_plan_filename(self):
        name = build_plan_filename("2025-12-27_12-43-32", "transformer-review")
        assert name == "2025-12-27_12-43-32-transformer-review.md"

    def test_build_issues_filename(self):
        name = build_issues_filename("2025-12-27_12-43-32", "transformer-review")
        assert name == "2025-12-27_12-43-32-transformer-review.csv"


class TestTemplatePaths:
    def test_skill_root_exists(self):
        root = get_skill_root()
        assert root.exists()
        assert (root / "SKILL.md").exists()

    def test_assets_dir_exists(self):
        assets = get_assets_dir()
        assert assets.exists()

    def test_template_dir_exists(self):
        tmpl = get_template_dir()
        assert tmpl.exists()
        assert (tmpl / "main.template.typ").exists()

    def test_latex_template_dir_exists(self):
        ltx = get_latex_template_dir()
        assert ltx.exists()
        assert (ltx / "main.template.tex").exists()

    def test_typst_fragment_dir_exists(self):
        frag = get_typst_fragment_dir()
        assert frag.exists()

    def test_registry_db_path(self):
        path = resolve_registry_db_path("/some/project")
        assert str(path).endswith("notes/literature-registry.sqlite3")


class TestCheckTool:
    def test_python3_available(self):
        from paper_utils import check_tool
        assert check_tool("python3")

    def test_nonexistent_tool(self):
        from paper_utils import check_tool
        assert not check_tool("nonexistent-tool-xyzzy-12345")

    def test_check_required_tools_all_available(self):
        from paper_utils import check_required_tools
        assert check_required_tools(["python3"])

    def test_check_required_tools_one_missing(self):
        from paper_utils import check_required_tools
        assert not check_required_tools(["python3", "nonexistent-tool-xyzzy"])

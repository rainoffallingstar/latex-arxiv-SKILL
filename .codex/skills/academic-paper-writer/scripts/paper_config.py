#!/usr/bin/env python3
"""Paper configuration: domain detection, config generation, and validation.

This module maps a user's topic to sensible defaults for:
- Output format (Typst by default, LaTeX legacy)
- Template class (IEEEtran, article, biomedical)
- Citation style (ieee, author-year)
- Preferred literature sources (arXiv, PubMed, OpenAlex, Europe PMC, paper-search)
- Visualization preferences
- Section framework suggestions

The output is a paper-config.yml that the agent and other scripts consume
to drive template selection, citation management, and discovery workflows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "paper-config.schema.yml"
)


DOMAIN_PATTERNS: dict[str, list[str]] = {
    "computer-science": [
        "machine learning", "deep learning", "neural network", "transformer",
        "attention", "diffusion model", "generative model", "language model",
        "llm", "reinforcement learning", "computer vision", "natural language",
        "nlp", "autonomous driving", "distributed system", "cloud computing",
        "cybersecurity", "blockchain", "compiler", "operating system",
        "algorithm", "data structure", "software engineering", "database",
        "graph neural", "generative adversarial", "variational autoencoder",
        "backpropagat", "robotics", "robot learning",
    ],
    "biomedical": [
        "gene", "genome", "protein", "crispr", "dna", "rna", "mrna",
        "stem cell", "t cell", "b cell", "cancer", "tumor", "immun",
        "drug", "clinical trial", "epidem", "disease", "patient",
        "therapy", "biomarker", "molecular", "pathway", "metabol",
        "microbio", "virolog", "antibod", "vaccine", "surgery",
        "radiology", "diagnos", "pharmac", "toxicolog", "physiolog",
        "anatomy", "neuroscien", "cognit", "psychiat",
    ],
    "physics": [
        "quantum", "particle", "cosmolog", "astrophys", "gravit",
        "thermodynam", "fluid", "superconduct", "semiconductor",
        "optics", "laser", "photon", "nuclear", "plasma",
        "condensed matter", "string theory", "relativity",
    ],
    "chemistry": [
        "synthesis", "catalyst", "polymer", "organic chemistry",
        "inorganic chemistry", "electrochem", "spectroscopy",
        "chromatography", "molecular dynamics",
    ],
    "engineering": [
        "circuit", "vlsi", "fpga", "embedded", "robotics",
        "control system", "signal processing", "antenna",
        "power system", "renewable energy", "aerospace",
    ],
    "mathematics": [
        "topology", "algebra", "differential equation", "optimization",
        "statistic", "probability", "number theory", "combinator",
        "geometry", "numerical analysis",
    ],
    "social-sciences": [
        "economic", "sociolog", "psycholog", "political", "education",
        "behavioral", "cognitive scien", "linguistic",
        "anthropolog", "demograph",
    ],
    "environmental": [
        "climate", "ecology", "biodiversity", "conservation",
        "pollution", "sustainability", "renewable", "carbon",
        "ecosystem", "ocean",
    ],
}


DOMAIN_CONFIG: dict[str, dict[str, Any]] = {
    "computer-science": {
        "output_format": "typst",
        "template_class": "IEEEtran",
        "citation_style": "ieee",
        "preferred_sources": ["arxiv", "openalex", "paper-search"],
        "section_framework": [
            "Introduction",
            "Background and Preliminaries",
            "Core Methods and Approaches",
            "Evaluation and Benchmarks",
            "Open Challenges",
            "Conclusion",
        ],
        "visualization_prefs": [
            "architecture-diagrams",
            "comparison-tables",
            "timeline-charts",
            "flow-charts",
            "taxonomy-trees",
        ],
    },
    "biomedical": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["pubmed", "europepmc", "openalex", "paper-search"],
        "section_framework": [
            "Introduction",
            "Disease Overview and Clinical Context",
            "Molecular Mechanisms",
            "Therapeutic Approaches",
            "Clinical Translation and Trials",
            "Future Perspectives",
            "Conclusion",
        ],
        "visualization_prefs": [
            "mechanism-diagrams",
            "clinical-trial-tables",
            "pathway-maps",
            "meta-analysis-forest-plots",
            "dose-response-plots",
        ],
    },
    "physics": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["arxiv", "openalex", "paper-search"],
        "section_framework": [
            "Introduction",
            "Theoretical Framework",
            "Experimental Methods",
            "Key Results and Observations",
            "Open Questions",
            "Conclusion",
        ],
        "visualization_prefs": [
            "schematic-diagrams",
            "data-plots",
            "phase-diagrams",
            "comparison-tables",
        ],
    },
    "chemistry": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["pubmed", "openalex", "europepmc", "paper-search"],
        "section_framework": [
            "Introduction",
            "Synthetic Methods",
            "Characterization and Analysis",
            "Mechanistic Studies",
            "Applications",
            "Conclusion",
        ],
        "visualization_prefs": [
            "reaction-schemes",
            "spectra-plots",
            "crystal-structure-diagrams",
            "comparison-tables",
        ],
    },
    "engineering": {
        "output_format": "typst",
        "template_class": "IEEEtran",
        "citation_style": "ieee",
        "preferred_sources": ["openalex", "arxiv", "paper-search"],
        "section_framework": [
            "Introduction",
            "System Architecture",
            "Design Methodology",
            "Performance Analysis",
            "Applications and Case Studies",
            "Conclusion",
        ],
        "visualization_prefs": [
            "block-diagrams",
            "circuit-diagrams",
            "performance-plots",
            "comparison-tables",
        ],
    },
    "mathematics": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["openalex", "arxiv", "paper-search"],
        "section_framework": [
            "Introduction",
            "Preliminaries and Notation",
            "Main Results",
            "Proofs and Derivations",
            "Applications and Examples",
            "Conclusion",
        ],
        "visualization_prefs": [
            "commutative-diagrams",
            "conceptual-illustrations",
            "data-tables",
        ],
    },
    "social-sciences": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["openalex", "paper-search"],
        "section_framework": [
            "Introduction",
            "Theoretical Background",
            "Literature Review",
            "Methodological Approaches",
            "Findings and Discussion",
            "Implications and Future Directions",
            "Conclusion",
        ],
        "visualization_prefs": [
            "conceptual-frameworks",
            "prisma-flowcharts",
            "meta-analysis-plots",
            "thematic-tables",
        ],
    },
    "environmental": {
        "output_format": "typst",
        "template_class": "article",
        "citation_style": "author-year",
        "preferred_sources": ["openalex", "pubmed", "europepmc", "paper-search"],
        "section_framework": [
            "Introduction",
            "System Overview and Drivers",
            "Impacts and Consequences",
            "Mitigation and Adaptation Strategies",
            "Policy and Governance",
            "Future Outlook",
            "Conclusion",
        ],
        "visualization_prefs": [
            "spatial-maps",
            "time-series-plots",
            "system-diagrams",
            "comparison-tables",
        ],
    },
}

DEFAULT_CONFIG: dict[str, Any] = {
    "output_format": "typst",
    "template_class": "article",
    "citation_style": "author-year",
    "preferred_sources": ["openalex", "paper-search"],
    "section_framework": [
        "Introduction",
        "Background and Related Work",
        "Core Approaches and Methods",
        "Key Challenges and Open Problems",
        "Future Directions",
        "Conclusion",
    ],
    "visualization_prefs": [
        "conceptual-diagrams",
        "comparison-tables",
        "taxonomy-figures",
        "data-plots",
    ],
}


def detect_domain(topic: str) -> tuple[str, float]:
    """Detect the most likely academic domain from a topic string.

    Returns a (domain, confidence) tuple where confidence is the ratio
    of matched keywords to total domain patterns.
    """
    topic_lower = topic.lower()
    scores: dict[str, float] = {}
    for domain, patterns in DOMAIN_PATTERNS.items():
        hits = 0
        for pattern in patterns:
            matched = False
            if len(pattern) <= 3:
                if re.search(rf"\b{re.escape(pattern)}\b", topic_lower):
                    matched = True
            elif " " not in pattern and len(pattern) <= 5:
                if re.search(rf"\b{re.escape(pattern)}\b", topic_lower):
                    matched = True
            else:
                if pattern in topic_lower:
                    matched = True
            if matched:
                hits += 1
        if hits > 0:
            scores[domain] = hits / len(patterns)
    if not scores:
        return ("general", 0.0)
    best = max(scores, key=lambda k: scores[k])
    return best, scores[best]


# CJK Unicode ranges for language detection
_CJK_RANGES = [
    (0x4E00, 0x9FFF),
    (0x3400, 0x4DBF),
    (0x20000, 0x2A6DF),
    (0xF900, 0xFAFF),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0xAC00, 0xD7AF),
    (0x1100, 0x11FF),
]


def detect_language(topic: str) -> str:
    """Detect the primary language from the topic string.

    Returns one of: 'en' (English/Latin), 'zh' (Chinese), 'ja' (Japanese),
    'ko' (Korean), 'mixed' (CJK + Latin).
    """
    has_cjk = False
    has_latin = False

    for ch in topic:
        cp = ord(ch)
        if cp < 128 and not ch.isspace():
            has_latin = True
        for lo, hi in _CJK_RANGES:
            if lo <= cp <= hi:
                has_cjk = True
                break

    if has_cjk and has_latin:
        return "mixed"
    if has_cjk:
        has_jp = any(0x3040 <= ord(ch) <= 0x30FF for ch in topic)
        has_ko = any(0xAC00 <= ord(ch) <= 0xD7AF for ch in topic)
        if has_jp:
            return "ja"
        if has_ko:
            return "ko"
        return "zh"
    return "en"


def get_recommended_output_format(language: str) -> str:
    """Recommend output format. Typst is default (native CJK support)."""
    return "typst"


def get_domain_config(domain: str) -> dict[str, Any]:
    """Get the recommended configuration for a domain."""
    return DOMAIN_CONFIG.get(domain, DEFAULT_CONFIG)


def generate_config(
    topic: str,
    *,
    domain: str | None = None,
    language: str | None = None,
    output_format: str | None = None,
    template_class: str | None = None,
    citation_style: str | None = None,
    preferred_sources: list[str] | None = None,
    section_framework: list[str] | None = None,
    visualization_prefs: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a complete paper configuration.

    Any explicitly provided arguments override domain defaults.
    """
    if domain is None:
        domain, confidence = detect_domain(topic)
    else:
        confidence = 1.0

    if language is None:
        language = detect_language(topic)

    base = get_domain_config(domain)

    config: dict[str, Any] = {
        "topic": topic,
        "domain": domain,
        "domain_confidence": round(confidence, 3),
        "language": language,
        "output_format": output_format or base["output_format"],
        "template_class": template_class or base["template_class"],
        "citation_style": citation_style or base["citation_style"],
        "preferred_sources": preferred_sources or base["preferred_sources"],
        "section_framework": section_framework or base["section_framework"],
        "visualization_prefs": visualization_prefs or base["visualization_prefs"],
        "iteration": {
            "enabled": True,
            "max_rounds": 5,
            "min_citations_per_section": 8,
            "review_triggers": ["user_invokes_review", "after_all_writing"],
            "auto_fix": {"P0": True, "P1": "ask_user", "P2": "skip"},
        },
    }
    return config


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate a paper configuration dict.

    Returns a list of validation errors (empty = valid).
    """
    errors: list[str] = []

    required = [
        "topic", "domain", "output_format", "template_class", "citation_style",
        "preferred_sources", "section_framework",
    ]
    for key in required:
        if key not in config or not config[key]:
            errors.append(f"Missing required field: {key}")

    valid_formats = {"typst", "latex", "markdown"}
    if config.get("output_format") and config["output_format"] not in valid_formats:
        errors.append(
            f"Invalid output_format '{config['output_format']}'. "
            f"Valid: {', '.join(sorted(valid_formats))}"
        )

    valid_templates = {"IEEEtran", "article", "biomedical"}
    if config.get("template_class") and config["template_class"] not in valid_templates:
        errors.append(
            f"Invalid template_class '{config['template_class']}'. "
            f"Valid: {', '.join(sorted(valid_templates))}"
        )

    valid_styles = {"ieee", "author-year"}
    if config.get("citation_style") and config["citation_style"] not in valid_styles:
        errors.append(
            f"Invalid citation_style '{config['citation_style']}'. "
            f"Valid: {', '.join(sorted(valid_styles))}"
        )

    valid_sources = {"arxiv", "pubmed", "openalex", "europepmc", "biorxiv", "paper-search"}
    if config.get("preferred_sources"):
        for src in config["preferred_sources"]:
            if src not in valid_sources:
                errors.append(
                    f"Invalid preferred_source '{src}'. "
                    f"Valid: {', '.join(sorted(valid_sources))}"
                )

    return errors


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate a paper config from a YAML file."""
    if yaml is None:
        raise ImportError(
            "PyYAML is required for config loading. Install with: pip install pyyaml"
        )
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("Config file must contain a YAML mapping")
    errors = validate_config(config)
    if errors:
        raise ValueError("Config validation errors:\n  " + "\n  ".join(errors))
    return config


def dump_config(config: dict[str, Any], path: Path) -> None:
    """Write a paper configuration to a YAML file."""
    if yaml is None:
        raise ImportError(
            "PyYAML is required for config output. Install with: pip install pyyaml"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# Paper configuration generated by paper_config.py\n"
        f"# Generated for topic: {config.get('topic', 'N/A')}\n"
        f"# Output format: {config.get('output_format', 'typst')} (typst | latex | markdown)\n"
        "# Edit this file before proceeding to Gate 1.\n"
        "\n"
    )
    body = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body)


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Paper configuration generator and validator."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    detect_parser = sub.add_parser("detect", help="Detect domain from topic")
    detect_parser.add_argument("--topic", required=True, help="Paper topic")

    gen_parser = sub.add_parser("generate", help="Generate config from topic")
    gen_parser.add_argument("--topic", required=True, help="Paper topic")
    gen_parser.add_argument("--domain", help="Override detected domain")
    gen_parser.add_argument("--language", help="Override detected language (en, zh, ja, ko)")
    gen_parser.add_argument("--output-format", help="Override output format (typst, latex, markdown)")
    gen_parser.add_argument("--template", help="Override template class")
    gen_parser.add_argument("--citation-style", help="Override citation style")
    gen_parser.add_argument("--sources", nargs="*", help="Override preferred sources")
    gen_parser.add_argument("--output", required=True, help="Output config file path")

    val_parser = sub.add_parser("validate", help="Validate an existing config file")
    val_parser.add_argument("--config", required=True, help="Path to paper-config.yml")

    args = parser.parse_args()

    if args.command == "detect":
        domain, confidence = detect_domain(args.topic)
        language = detect_language(args.topic)
        output_format = get_recommended_output_format(language)
        print(json.dumps({
            "domain": domain,
            "confidence": round(confidence, 3),
            "language": language,
            "output_format": output_format,
        }))
        return 0

    if args.command == "generate":
        config = generate_config(
            args.topic,
            domain=args.domain,
            language=getattr(args, "language", None),
            output_format=getattr(args, "output_format", None),
            template_class=args.template,
            citation_style=args.citation_style,
            preferred_sources=args.sources if args.sources else None,
        )
        output = Path(args.output)
        dump_config(config, output)
        print(f"Config written to: {output}")
        dom = config["domain"]
        conf = config["domain_confidence"]
        lang = config.get("language", "en")
        fmt = config.get("output_format", "typst")
        print(f"Detected domain: {dom} (confidence: {conf:.3f})")
        print(f"Detected language: {lang} | Output format: {fmt}")
        return 0

    if args.command == "validate":
        try:
            config = load_config(Path(args.config))
            print("Config is valid.")
            print(f"  Domain: {config['domain']}")
            print(f"  Output format: {config.get('output_format', 'typst')}")
            print(f"  Template: {config['template_class']}")
            print(f"  Citation style: {config['citation_style']}")
            print(f"  Sources: {', '.join(config['preferred_sources'])}")
        except (FileNotFoundError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

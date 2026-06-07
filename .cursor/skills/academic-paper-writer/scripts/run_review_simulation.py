#!/usr/bin/env python3
"""Multi-persona peer review simulation engine.

Calls gemini_bridge.py or claude_bridge.py via subprocess to perform
LLM-based review with configurable reviewer personas. Applies anti-inflation
rules and routes weaknesses to sub-skills.

Usage:
    python3 scripts/run_review_simulation.py --project-dir <paper_dir> --round <N>
    python3 scripts/run_review_simulation.py --project-dir <paper_dir> --round 1 --llm gemini --personas 3
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent

REVIEWER_PERSONAS = {
    "R1-Experimentalist": {"focus": "Statistical rigor, baselines, replication", "weight": "Experimental 30%"},
    "R2-Theorist": {"focus": "Formal definitions, proofs, MECE taxonomy", "weight": "Technical depth 35%"},
    "R3-Perfectionist": {"focus": "Writing quality, figures, formatting", "weight": "Clarity 30%"},
    "R4-Synthesizer": {"focus": "Cross-cutting analysis, gap identification", "weight": "Novelty 25%"},
    "R5-Newcomer": {"focus": "Accessibility, definitions, examples", "weight": "Clarity 35%"},
}

WEAKNESS_ROUTING_TABLE = {
    "Citation coverage insufficient": "literature-search",
    "Too many arXiv-only refs": "literature-search",
    "Missing recent papers": "literature-search",
    "Structure unclear": "structure-logic",
    "Analysis lacks depth": "structure-logic",
    "Taxonomy not novel": "structure-logic",
    "Claims too strong": "structure-logic",
    "Tables incomparable": "figures-tables",
    "Missing visualizations": "figures-tables",
    "No error bars": "figures-tables",
}


def parse_args():
    p = argparse.ArgumentParser(description="Run peer review simulation with LLM")
    p.add_argument("--project-dir", required=True, help="Path to paper project directory")
    p.add_argument("--round", type=int, default=1, help="Review round number (for anti-inflation)")
    p.add_argument("--personas", type=int, choices=[3, 4, 5], default=5, help="Number of reviewer personas")
    p.add_argument("--llm", choices=["gemini", "claude"], default="gemini", help="Which LLM bridge to use")
    p.add_argument("--model", default="", help="Model override passed to the bridge")
    p.add_argument("--output", help="Output JSON file path (default: reviews/review-round-N.json)")
    return p.parse_args()


def load_prompt_templates():
    """Load persona prompt templates from review-prompt-templates.md."""
    path = SKILL_DIR / "subskills" / "review-sim" / "review-prompt-templates.md"
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    templates = {}
    sections = re.split(r"^##\s+", text, flags=re.MULTILINE)
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        header_match = re.match(r"(R\d+\s*-\s*\w+)", sec)
        if header_match:
            key = header_match.group(1).strip()
            templates[key] = sec
    return templates


def build_reviewer_prompt(persona_key, persona_info, prompt_template, paper_summary, round_num):
    """Build a complete prompt for one reviewer persona."""
    anti_inflation = ""
    if round_num == 1:
        anti_inflation = "\nIMPORTANT: This is round 1. First round score is capped at 7.0/10."
    else:
        max_score = min(7.0 + 1.5 * (round_num - 1), 10.0)
        anti_inflation = f"\nIMPORTANT: Score cannot exceed {max_score:.1f}/10 (anti-inflation rule)."

    rubric = prompt_template if prompt_template else f"Focus: {persona_info['focus']}. Weight: {persona_info['weight']}"

    prompt = f"""You are {persona_key} reviewing a scientific survey paper.
{rubric}

Please review the following paper and provide:
1. An overall score (1-10)
2. Per-dimension scores: Novelty, Comprehensiveness, Clarity, Technical Depth, Experimental Validation
3. 3-5 strengths
4. 3-5 weaknesses (prioritized as Major or Minor)
5. Concrete, actionable suggestions
6. A recommendation: Accept / Weak Accept / Borderline / Reject
{anti_inflation}

Paper summary:
{paper_summary}

Output your review in JSON format with keys: overall_score, dimension_scores, strengths, weaknesses, suggestions, recommendation.
Each weakness should have: text (str), priority (Major/Minor).
"""
    return prompt


def call_llm_via_bridge(prompt, project_dir, llm_type, model_override):
    """Call gemini_bridge.py or claude_bridge.py via subprocess."""
    if llm_type == "gemini":
        bridge = SKILL_DIR.parent / "collaborating-with-gemini" / "scripts" / "gemini_bridge.py"
    else:
        bridge = SKILL_DIR.parent / "collaborating-with-claude" / "scripts" / "claude_bridge.py"

    if not bridge.exists():
        print(f"Warning: Bridge script not found at {bridge}. Falling back to no-LLM mode.")
        return None

    cmd = ["python3", str(bridge), "--PROMPT", prompt, "--cd", str(project_dir)]
    if model_override:
        cmd.extend(["--model", model_override])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"Bridge warning: exit code {result.returncode}")
        output = json.loads(result.stdout)
        if output.get("success"):
            return output.get("agent_messages", "")
        else:
            print(f"Bridge error: {output.get('error', 'unknown')}")
            return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Bridge call failed: {e}")
        return None


def parse_review_from_llm_output(text):
    """Try to extract structured review data from LLM output text."""
    if not text:
        return None

    # Try to find JSON block in the response
    json_match = re.search(r'\{.*"overall_score".*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try to parse numeric score via regex
    score_match = re.search(r'(?:overall\s*score|score)[:\s]+(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if score_match:
        return {"overall_score": float(score_match.group(1)), "raw_text": text[:500]}

    return None


def apply_anti_inflation(score, round_num):
    """Apply anti-inflation rules."""
    if round_num == 1:
        return min(score, 7.0)
    max_score = min(7.0 + 1.5 * (round_num - 1), 10.0)
    return min(score, max_score)


def route_weaknesses(weaknesses):
    """Route weaknesses to sub-skills."""
    actions = []
    for w in weaknesses:
        text = w.get("text", "") if isinstance(w, dict) else str(w)
        routed = "review-sim"
        for pattern, target in WEAKNESS_ROUTING_TABLE.items():
            if pattern.lower() in text.lower():
                routed = target
                break
        actions.append({
            "weakness": text[:100],
            "routed_to": f"subskills/{routed}/SKILL.md",
            "action": f"See subskills/{routed}/SKILL.md for remediation guidance",
        })
    return actions


def generate_gaps(weaknesses, overall_score, dimension_scores):
    """Generate gap entries from review weakness/score data matching review_gaps.py format."""
    gaps = []
    for w in weaknesses:
        text = w.get("text", "") if isinstance(w, dict) else str(w)
        priority = w.get("priority", "Major") if isinstance(w, dict) else "Major"
        gap_priority = "P0" if priority == "Major" else "P1"
        est_work = "2-4 paragraphs of supplementary content" if gap_priority == "P0" else "1-2 paragraphs of supplementary content"
        impact = "Core dimension under-covered — critical" if gap_priority == "P0" else "Recommended improvement"

        # Infer section from weakness routing table
        section = "General"
        for pattern, target in WEAKNESS_ROUTING_TABLE.items():
            if pattern.lower() in text.lower():
                section = pattern
                break

        gaps.append({
            "priority": gap_priority,
            "section": section,
            "issue": text[:200],
            "est_work": est_work,
            "impact": impact,
            "citation_count": int(max(dimension_scores.values(), default=0) * 2),
        })
    return gaps


def check_bridge_available(llm_type: str) -> bool:
    """Check if the specified LLM bridge script is available."""
    if llm_type == "gemini":
        bridge = SKILL_DIR.parent / "collaborating-with-gemini" / "scripts" / "gemini_bridge.py"
    else:
        bridge = SKILL_DIR.parent / "collaborating-with-claude" / "scripts" / "claude_bridge.py"
    return bridge.exists()


def run_gap_analysis_only(project_dir: Path, round_num: int, output_path: Path) -> dict[str, Any]:
    """Run gap analysis as fallback when no LLM bridge is available."""
    print("\n*** No LLM bridge available — running gap analysis only ***")
    print("Install gemini CLI or claude CLI for full multi-persona review.\n")

    review_gaps_path = SKILL_DIR / "scripts" / "review_gaps.py"
    gaps_data: list[dict] = []

    if review_gaps_path.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("review_gaps", review_gaps_path)
            rg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rg)

            source = rg._find_source_file(project_dir)
            if source:
                sections = rg.parse_sections(source)
                gaps_data = rg.classify_gaps(sections)
                print(f"Analyzed {len(sections)} sections, found {len(gaps_data)} gaps.")
            else:
                print("No source file (main.typ/main.tex) found in project directory.")
        except Exception as e:
            print(f"Gap analysis error: {e}")

    p0 = sum(1 for g in gaps_data if g.get("priority") == "P0")
    p1 = sum(1 for g in gaps_data if g.get("priority") == "P1")
    p2 = sum(1 for g in gaps_data if g.get("priority") == "P2")

    return {
        "round": round_num,
        "project_dir": str(project_dir),
        "mode": "gap-analysis-only",
        "llm_used": "none (fallback)",
        "personas_used": [],
        "gaps": gaps_data,
        "gap_summary": {"P0_critical": p0, "P1_recommended": p1, "P2_optional": p2},
        "recommendation": "N/A — install gemini CLI or claude CLI for full review",
    }


def main():
    args = parse_args()
    proj = Path(args.project_dir)
    if not proj.exists():
        print(f"Error: project directory {args.project_dir} does not exist")
        sys.exit(1)

    reviews_dir = proj / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output or str(reviews_dir / f"review-round-{args.round}.json"))

    # Check if LLM bridge is available; fall back to gap analysis if not
    if not check_bridge_available(args.llm):
        review = run_gap_analysis_only(proj, args.round, output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(review, f, indent=2, ensure_ascii=False)
        print(f"\nGap analysis saved to: {output_path}")
        return 0

    persona_names = list(REVIEWER_PERSONAS.keys())[:args.personas]
    templates = load_prompt_templates()

    # Build paper summary from available sources
    paper_summary = f"Paper directory: {proj}"
    for src_name in ["main.typ", "main.tex"]:
        src_path = proj / src_name
        if src_path.exists():
            content = src_path.read_text(encoding="utf-8", errors="replace")[:3000]
            paper_summary += f"\n\nSource ({src_name}):\n{content}"
            break

    # Run review for each persona
    all_scores = []
    all_weaknesses = []
    all_strengths = []
    all_parsed_reviews = []

    for persona_key in persona_names:
        info = REVIEWER_PERSONAS[persona_key]
        template = templates.get(persona_key, "")
        prompt = build_reviewer_prompt(persona_key, info, template, paper_summary, args.round)

        llm_output = call_llm_via_bridge(prompt, proj, args.llm, args.model)

        if llm_output:
            parsed = parse_review_from_llm_output(llm_output)
            if parsed and "overall_score" in parsed:
                all_parsed_reviews.append(parsed)
                score = apply_anti_inflation(parsed["overall_score"], args.round)
                all_scores.append(score)
                if "weaknesses" in parsed:
                    all_weaknesses.extend(parsed["weaknesses"])
                if "strengths" in parsed:
                    all_strengths.extend(parsed["strengths"][:5])
                continue

        # Fallback for failed persona review
        all_scores.append(0.0)
        all_weaknesses.append({"text": f"{persona_key}: review could not be completed", "priority": "Major"})

    # Calculate final score (median)
    all_scores.sort()
    n = len(all_scores)
    final_score = all_scores[n // 2] if n > 0 else 0.0

    # Deduplicate weaknesses
    unique_weaknesses = []
    seen = set()
    for w in all_weaknesses:
        text = w.get("text", "") if isinstance(w, dict) else str(w)
        if text not in seen:
            seen.add(text)
            unique_weaknesses.append(w if isinstance(w, dict) else {"text": str(w), "priority": "Major"})

    # Aggregate dimension scores from all persona reviews
    dim_keys = ["Novelty", "Comprehensiveness", "Clarity", "Technical Depth", "Experimental Validation"]
    dimension_scores = {}
    for dk in dim_keys:
        scores_for_dim = []
        for p in all_parsed_reviews:
            ds = p.get("dimension_scores", {})
            if dk in ds and isinstance(ds[dk], (int, float)):
                scores_for_dim.append(float(ds[dk]))
        dimension_scores[dk] = round(sum(scores_for_dim) / len(scores_for_dim), 1) if scores_for_dim else 0.0

    # Generate gaps from weaknesses
    gaps = generate_gaps(unique_weaknesses[:10], final_score, dimension_scores) if unique_weaknesses else []

    # Derive recommendation from final score
    if final_score >= 8.0:
        recommendation = "Accept"
    elif final_score >= 7.0:
        recommendation = "Weak Accept"
    elif final_score >= 5.0:
        recommendation = "Borderline"
    else:
        recommendation = "Reject"

    review = {
        "round": args.round,
        "project_dir": str(proj),
        "llm_used": args.llm,
        "personas_used": persona_names,
        "anti_inflation": {
            "first_round_cap": 7.0,
            "max_increase_per_round": 1.5,
            "round_max_score": 7.0 if args.round == 1 else min(7.0 + 1.5 * (args.round - 1), 10.0),
        },
        "overall_score": round(final_score, 1),
        "dimension_scores": dimension_scores,
        "strengths": all_strengths[:5],
        "weaknesses": unique_weaknesses[:10],
        "gaps": gaps,
        "routing_actions": route_weaknesses(unique_weaknesses[:10]) if unique_weaknesses else [],
        "recommendation": recommendation,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2, ensure_ascii=False)

    print(f"\nReview round {args.round} complete.")
    print(f"  Personas: {', '.join(persona_names)}")
    print(f"  Final median score: {round(final_score, 1)}/10")
    print(f"  Recommendation: {recommendation}")
    print(f"  Weaknesses identified: {len(unique_weaknesses)}")
    print(f"  Gaps (for remediation): {len(gaps)}")
    print(f"  Output: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

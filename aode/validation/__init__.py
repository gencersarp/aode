"""Validation Engine.

For each top-scored opportunity:
  1. Generates landing page copy (headline + sub-headline + CTA + feature bullets)
  2. Generates a cold-outreach message template
  3. Simulates a heuristic "validation score" (CTR proxy)
  4. Assigns a confidence level
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


# ---------------------------------------------------------------------------
# Landing page generation
# ---------------------------------------------------------------------------

_HEADLINE_TEMPLATES = [
    "Stop {pain_verb} {object} Manually. Finally.",
    "{object} Sync Without the {pain_noun}.",
    "The {adjective} Way to {action} for {persona}.",
    "Cut Your {pain_noun} Time by 80%.",
    "Affordable {object} for {persona}.",
]

_CTA_PHRASES = [
    "Start free — no credit card required",
    "Join 500 teams already saving hours every week",
    "Get early access — limited spots",
    "Try it free for 14 days",
    "See how it works in 2 minutes",
]


def _extract_noun(cluster_name: str) -> str:
    """Pull the most noun-like phrase from a cluster label."""
    words = cluster_name.replace("/", " ").split()
    # Skip stop words
    stops = {"and", "or", "for", "the", "a", "an", "of", "to", "&"}
    meaningful = [w for w in words if w.lower() not in stops]
    return " ".join(meaningful[:3]) if meaningful else cluster_name[:30]


def _simulated_ctr(cluster: dict[str, Any], score: float) -> float:
    """Heuristic CTR proxy: higher score + more frequency → higher CTR."""
    freq = cluster.get("frequency", 1)
    base_ctr = 0.01 + score * 0.08 + min(0.05, freq * 0.005)
    return round(min(0.25, base_ctr), 4)


def generate_landing_page(
    cluster: dict[str, Any], score_record: dict[str, Any]
) -> str:
    """Generate simple landing page copy for the opportunity."""
    name = cluster.get("problem_cluster", "Unknown Problem")
    noun = _extract_noun(name)
    score = score_record.get("score", 0.5)
    examples = cluster.get("example_cases", [])

    # Pull pain keywords from examples
    pain_words = ["manual work", "wasted time", "high costs", "complexity"]
    for ex in examples:
        if "expensive" in ex.lower() or "overpriced" in ex.lower():
            pain_words.insert(0, "high costs")
            break
        if "slow" in ex.lower() or "hours" in ex.lower():
            pain_words.insert(0, "wasted hours")
            break

    cta = _CTA_PHRASES[hash(name) % len(_CTA_PHRASES)]

    feature_bullets = _generate_feature_bullets(name, examples)

    page = (
        f"# {noun}\n\n"
        f"**Stop dealing with {pain_words[0]}. We built the tool you needed.**\n\n"
        f"Thousands of teams struggle with: {name.lower()}.\n"
        f"We fix that — fast, affordable, and without the enterprise price tag.\n\n"
        f"## Why Us?\n"
        + "".join(f"- {b}\n" for b in feature_bullets)
        + f"\n## {cta}\n\n"
        f"*Opportunity score: {score:.0%} confidence*\n"
    )
    return page


def _generate_feature_bullets(name: str, examples: list[str]) -> list[str]:
    bullets = [
        f"Solve {name[:50].lower()} in minutes, not days",
        "Integrates with tools you already use",
        "Priced for small teams — not enterprise budgets",
        "No-code setup, up and running in under 10 minutes",
    ]
    if examples:
        first_example = examples[0][:80]
        bullets.append(f'Designed around real pain: "{first_example}…"')
    return bullets


def generate_outreach(cluster: dict[str, Any], score_record: dict[str, Any]) -> str:
    """Generate a cold-outreach message template."""
    name = cluster.get("problem_cluster", "your workflow")
    noun = _extract_noun(name)
    score = score_record.get("score", 0.5)

    message = (
        f"Hi {{{{first_name}}}},\n\n"
        f"I came across your post about {name.lower()} and it really resonated with me.\n\n"
        f"We're building a tool that helps teams solve exactly this — {noun.lower()} "
        f"without the usual pain.\n\n"
        f"We're in early access and looking for 10 design partners to shape the product.\n"
        f"Would you be open to a 20-minute call to share your experience? "
        f"Happy to give you free access in return.\n\n"
        f"Best,\n{{{{sender_name}}}}\n\n"
        f"[Confidence level: {score:.0%}]"
    )
    return message


def validate_opportunity(
    cluster: dict[str, Any],
    score_record: dict[str, Any],
    scored_id: int | None = None,
) -> dict[str, Any]:
    """Run full validation pipeline for one opportunity.

    Returns a validation dict ready for persistence.
    """
    landing_page = generate_landing_page(cluster, score_record)
    outreach = generate_outreach(cluster, score_record)

    score = score_record.get("score", 0.0)
    ctr = _simulated_ctr(cluster, score)

    # Validation score: blend of opportunity score + simulated CTR signal
    validation_score = round(score * 0.7 + ctr * 3.0, 4)

    # Confidence: lower if risks are present
    num_risks = len(score_record.get("risks", []))
    confidence = round(max(0.1, 1.0 - num_risks * 0.12), 4)

    return {
        "scored_id": scored_id,
        "landing_page": landing_page,
        "outreach_message": outreach,
        "validation_score": validation_score,
        "confidence": confidence,
        "simulated_ctr": ctr,
        "problem_cluster": cluster.get("problem_cluster", ""),
    }


def validate_top_opportunities(
    top_scored: list[dict[str, Any]],
    scored_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Validate the top N scored opportunities."""
    results: list[dict[str, Any]] = []
    for i, scored in enumerate(top_scored):
        sid = (scored_ids[i] if scored_ids and i < len(scored_ids) else None)
        cluster = {
            "problem_cluster": scored.get("problem_cluster", ""),
            "frequency": scored.get("frequency", 1),
            "example_cases": scored.get("example_cases", []),
        }
        results.append(validate_opportunity(cluster, scored, scored_id=sid))
    return results

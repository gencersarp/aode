"""Goodhart-Aware Scoring System.

Scores each opportunity cluster across multiple dimensions and applies
explicit penalties to avoid proxy-metric overoptimisation.

Scoring dimensions (each 0-10):
  - pain_intensity      : strength and frequency of complaints
  - monetization        : willingness-to-pay signals
  - build_feasibility   : can a small team ship an MVP?
  - competition_density : penalises crowded markets (inverted)

Penalties applied AFTER raw scoring:
  - anti_hype_penalty      : deducts points for buzzword-heavy descriptions
  - anti_generic_penalty   : deducts for LLM-style vague idea descriptions

Final score is normalised to [0, 1].
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Heuristic dictionaries
# ---------------------------------------------------------------------------

_PAIN_SIGNALS = [
    "frustrating", "nightmare", "broken", "kills me", "waste", "painful",
    "impossible", "hours", "days", "every week", "every month", "blocked",
    "lost deal", "losing", "no solution", "can't find", "doesn't exist",
    "too expensive", "overpriced", "manual",
]

_MONETIZE_SIGNALS = [
    "would pay", "willing to pay", "subscription", "enterprise", "deal",
    "revenue", "customers", "clients", "charge", "$", "€", "£",
    "pricing", "budget", "cost", "affordable",
]

_BUILD_EASY_SIGNALS = [
    "simple", "cli", "script", "csv", "spreadsheet", "api", "webhook",
    "automation", "template", "form", "email", "notification",
]

_COMPETITION_SIGNALS = [
    "already exists", "there are many", "tons of tools", "saturated",
    "just use", "have you tried", "just use zapier", "just use notion",
    "you can use airtable",
]

_HYPE_WORDS = [
    "ai", "machine learning", "blockchain", "web3", "nft", "gpt",
    "llm", "neural", "deep learning", "metaverse", "defi",
]

_GENERIC_PHRASES = [
    "productivity app", "all-in-one", "platform for everything",
    "super app", "one tool to rule", "next-generation", "revolutionary",
    "disrupt", "uber for", "airbnb for",
]


def _count_signals(text: str, signals: list[str]) -> int:
    lower = text.lower()
    return sum(1 for s in signals if s in lower)


def _hype_penalty(text: str) -> float:
    """Return a penalty [0, 3] proportional to hype-word density."""
    count = _count_signals(text, _HYPE_WORDS)
    return min(3.0, count * 0.75)


def _generic_penalty(text: str) -> float:
    """Return a penalty [0, 2] for vague/generic idea language."""
    count = _count_signals(text, _GENERIC_PHRASES)
    return min(2.0, count * 1.0)


def _pain_score(cluster: dict[str, Any]) -> float:
    """Score 0-10: pain intensity."""
    base = 0.0
    texts = " ".join(cluster.get("example_cases", []))
    full_text = cluster.get("problem_cluster", "") + " " + texts

    # Signal hits
    hits = _count_signals(full_text, _PAIN_SIGNALS)
    base += min(5.0, hits * 1.0)

    # Frequency bonus (more posts = more widespread pain)
    freq = cluster.get("frequency", 1)
    base += min(5.0, freq * 0.8)

    return min(10.0, base)


def _monetize_score(cluster: dict[str, Any]) -> float:
    """Score 0-10: monetisation potential."""
    texts = " ".join(cluster.get("example_cases", []))
    full_text = cluster.get("problem_cluster", "") + " " + texts
    hits = _count_signals(full_text, _MONETIZE_SIGNALS)
    return min(10.0, hits * 1.5)


def _feasibility_score(cluster: dict[str, Any]) -> float:
    """Score 0-10: build feasibility for a small team."""
    texts = " ".join(cluster.get("example_cases", []))
    full_text = cluster.get("problem_cluster", "") + " " + texts

    # Easy-build signals raise score
    easy_hits = _count_signals(full_text, _BUILD_EASY_SIGNALS)
    score = 5.0 + min(5.0, easy_hits * 1.0)

    # Long text implies complex requirements
    word_count = len(full_text.split())
    if word_count > 300:
        score -= 1.0

    return max(0.0, min(10.0, score))


def _competition_score(cluster: dict[str, Any]) -> float:
    """Score 0-10: market openness (higher = less competition)."""
    texts = " ".join(cluster.get("example_cases", []))
    full_text = cluster.get("problem_cluster", "") + " " + texts
    competition_hits = _count_signals(full_text, _COMPETITION_SIGNALS)
    # Invert: more competition signals → lower score
    return max(0.0, 10.0 - competition_hits * 2.5)


_WEIGHTS = {
    "pain_intensity": 0.35,
    "monetization": 0.25,
    "build_feasibility": 0.20,
    "competition_density": 0.20,
}


def score_opportunity(cluster: dict[str, Any]) -> dict[str, Any]:
    """Score a single opportunity cluster.

    Returns a dict with ``score`` (float, 0-1), ``reasoning`` (str) and
    ``risks`` (list[str]).
    """
    pain = _pain_score(cluster)
    money = _monetize_score(cluster)
    feasibility = _feasibility_score(cluster)
    competition = _competition_score(cluster)

    raw = (
        _WEIGHTS["pain_intensity"] * pain
        + _WEIGHTS["monetization"] * money
        + _WEIGHTS["build_feasibility"] * feasibility
        + _WEIGHTS["competition_density"] * competition
    )

    full_text = (
        cluster.get("problem_cluster", "")
        + " "
        + " ".join(cluster.get("example_cases", []))
    )
    hype_pen = _hype_penalty(full_text)
    generic_pen = _generic_penalty(full_text)

    penalised = raw - hype_pen - generic_pen
    normalised = max(0.0, min(1.0, penalised / 10.0))

    risks: list[str] = []
    if competition < 4.0:
        risks.append("High competition — differentiation will be critical")
    if money < 3.0:
        risks.append("Low monetisation signals — validate willingness to pay first")
    if feasibility < 4.0:
        risks.append("Complex build — may require significant engineering effort")
    if hype_pen > 1.5:
        risks.append("Hype-heavy framing detected — ensure genuine user pain exists")
    if generic_pen > 0.5:
        risks.append("Idea framing is generic — needs sharper problem definition")

    reasoning = (
        f"Pain={pain:.1f}/10, Monetization={money:.1f}/10, "
        f"Feasibility={feasibility:.1f}/10, Competition openness={competition:.1f}/10. "
        f"Hype penalty={hype_pen:.2f}, Generic penalty={generic_pen:.2f}. "
        f"Raw weighted={raw:.2f} → normalised={normalised:.3f}."
    )

    return {
        "cluster_id": cluster.get("id"),
        "score": round(normalised, 4),
        "reasoning": reasoning,
        "risks": risks,
        "problem_cluster": cluster.get("problem_cluster", ""),
    }


def score_opportunities(
    clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Score all clusters and return sorted results (highest score first)."""
    scored = [score_opportunity(c) for c in clusters]
    return sorted(scored, key=lambda s: s["score"], reverse=True)

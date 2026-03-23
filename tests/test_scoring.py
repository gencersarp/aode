"""Tests for the Goodhart-Aware Scoring System."""

from __future__ import annotations

import pytest

from aode.scoring import score_opportunity, score_opportunities


_STRONG_CLUSTER = {
    "id": 1,
    "problem_cluster": "Affordable invoicing & payment for freelancers",
    "frequency": 8,
    "example_cases": [
        "I would pay $20/month for an affordable invoicing tool. "
        "Every option is too expensive and I'm losing money on payment fees.",
        "International payments are painful. Wise fees add up. $100 lost every month.",
    ],
}

_WEAK_CLUSTER = {
    "id": 2,
    "problem_cluster": "AI blockchain metaverse super app for everything",
    "frequency": 1,
    "example_cases": [
        "Revolutionary AI-powered all-in-one platform using deep learning and blockchain."
    ],
}

_COMPETITION_CLUSTER = {
    "id": 3,
    "problem_cluster": "Project management tool",
    "frequency": 3,
    "example_cases": [
        "There are many tools already. Just use Notion or Trello. "
        "You can use Airtable for this. Just use Zapier.",
    ],
}


def test_score_opportunity_returns_dict():
    result = score_opportunity(_STRONG_CLUSTER)
    assert isinstance(result, dict)
    assert "score" in result
    assert "reasoning" in result
    assert "risks" in result


def test_score_is_between_zero_and_one():
    for cluster in [_STRONG_CLUSTER, _WEAK_CLUSTER, _COMPETITION_CLUSTER]:
        result = score_opportunity(cluster)
        assert 0.0 <= result["score"] <= 1.0, f"Score out of range: {result['score']}"


def test_strong_cluster_scores_higher_than_weak():
    strong = score_opportunity(_STRONG_CLUSTER)
    weak = score_opportunity(_WEAK_CLUSTER)
    assert strong["score"] > weak["score"], (
        f"Expected strong ({strong['score']:.3f}) > weak ({weak['score']:.3f})"
    )


def test_hype_penalty_applied_to_weak_cluster():
    result = score_opportunity(_WEAK_CLUSTER)
    assert "Hype" in result["reasoning"] or result["score"] < 0.5


def test_competition_cluster_has_risk():
    result = score_opportunity(_COMPETITION_CLUSTER)
    risks = result["risks"]
    competition_risk = any("competition" in r.lower() for r in risks)
    assert competition_risk, f"Expected competition risk, got: {risks}"


def test_score_opportunities_sorted():
    clusters = [_WEAK_CLUSTER, _STRONG_CLUSTER, _COMPETITION_CLUSTER]
    scored = score_opportunities(clusters)
    scores = [s["score"] for s in scored]
    assert scores == sorted(scores, reverse=True)


def test_reasoning_contains_all_dimensions():
    result = score_opportunity(_STRONG_CLUSTER)
    reasoning = result["reasoning"]
    assert "Pain=" in reasoning
    assert "Monetization=" in reasoning
    assert "Feasibility=" in reasoning


def test_risks_is_list():
    result = score_opportunity(_STRONG_CLUSTER)
    assert isinstance(result["risks"], list)


def test_score_empty_cluster():
    empty = {"id": 99, "problem_cluster": "", "frequency": 0, "example_cases": []}
    result = score_opportunity(empty)
    assert 0.0 <= result["score"] <= 1.0

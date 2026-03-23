"""Tests for the Validation Engine."""

from __future__ import annotations

import pytest

from aode.validation import (
    generate_landing_page,
    generate_outreach,
    validate_opportunity,
    validate_top_opportunities,
)


_CLUSTER = {
    "problem_cluster": "Affordable invoicing for freelancers",
    "frequency": 6,
    "example_cases": [
        "Every invoicing tool is overpriced. I just need to send 5 invoices a month.",
        "Payment fees eat into my revenue as a freelancer.",
    ],
}

_SCORE_RECORD = {
    "score": 0.72,
    "reasoning": "High pain, good monetisation signals",
    "risks": ["Low competition differentiation"],
    "cluster_id": 1,
}


def test_generate_landing_page_returns_string():
    page = generate_landing_page(_CLUSTER, _SCORE_RECORD)
    assert isinstance(page, str)
    assert len(page) > 50


def test_landing_page_contains_headline():
    page = generate_landing_page(_CLUSTER, _SCORE_RECORD)
    assert "#" in page  # markdown heading present


def test_generate_outreach_returns_string():
    msg = generate_outreach(_CLUSTER, _SCORE_RECORD)
    assert isinstance(msg, str)
    assert len(msg) > 50


def test_outreach_contains_placeholders():
    msg = generate_outreach(_CLUSTER, _SCORE_RECORD)
    assert "first_name" in msg or "{" in msg


def test_validate_opportunity_schema():
    result = validate_opportunity(_CLUSTER, _SCORE_RECORD, scored_id=1)
    required_keys = {
        "scored_id", "landing_page", "outreach_message",
        "validation_score", "confidence", "simulated_ctr",
    }
    assert required_keys.issubset(result.keys())


def test_validation_score_in_range():
    result = validate_opportunity(_CLUSTER, _SCORE_RECORD)
    assert 0.0 <= result["validation_score"] <= 1.5  # blended score


def test_confidence_decreases_with_more_risks():
    low_risk = {**_SCORE_RECORD, "risks": []}
    high_risk = {**_SCORE_RECORD, "risks": ["Risk A", "Risk B", "Risk C", "Risk D"]}
    low_conf = validate_opportunity(_CLUSTER, low_risk)
    high_conf = validate_opportunity(_CLUSTER, high_risk)
    assert low_conf["confidence"] >= high_conf["confidence"]


def test_simulated_ctr_in_range():
    result = validate_opportunity(_CLUSTER, _SCORE_RECORD)
    assert 0.0 < result["simulated_ctr"] <= 0.25


def test_validate_top_opportunities_list():
    top = [
        {**_SCORE_RECORD, "problem_cluster": "Invoicing", "frequency": 5, "example_cases": []},
        {**_SCORE_RECORD, "problem_cluster": "Sync pain", "frequency": 3, "example_cases": []},
    ]
    results = validate_top_opportunities(top)
    assert len(results) == 2
    for r in results:
        assert "validation_score" in r
        assert "landing_page" in r

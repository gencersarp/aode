"""Tests for the opportunity extraction engine."""

from __future__ import annotations

import pytest

from aode.extraction import extract_opportunities, _extract_heuristic


_SAMPLE_POSTS = [
    {
        "source": "reddit",
        "text": "I spend hours every week manually copying data from Excel into our CRM.",
        "metadata": {"id": "p1"},
    },
    {
        "source": "reddit",
        "text": "Invoicing tools are too expensive for freelancers. I just need to send invoices.",
        "metadata": {"id": "p2"},
    },
    {
        "source": "github",
        "text": "Client onboarding takes forever. Need to automate the email flow.",
        "metadata": {"id": "p3"},
    },
    {
        "source": "reddit",
        "text": "Multi-channel inventory sync between Shopify and Amazon is broken.",
        "metadata": {"id": "p4"},
    },
    {
        "source": "reddit",
        "text": "Social media scheduling tools like Hootsuite are too expensive for solo creators.",
        "metadata": {"id": "p5"},
    },
    {
        "source": "github",
        "text": "Row-level permissions are missing. Need user-based access control for multi-tenant apps.",
        "metadata": {"id": "p6"},
    },
]


def test_extract_heuristic_returns_clusters():
    clusters = _extract_heuristic(_SAMPLE_POSTS)
    assert isinstance(clusters, list)
    assert len(clusters) >= 1


def test_extract_heuristic_cluster_schema():
    clusters = _extract_heuristic(_SAMPLE_POSTS)
    for c in clusters:
        assert "problem_cluster" in c
        assert "frequency" in c
        assert "example_cases" in c
        assert isinstance(c["frequency"], int)
        assert c["frequency"] >= 1
        assert isinstance(c["example_cases"], list)


def test_extract_heuristic_finds_known_clusters():
    clusters = _extract_heuristic(_SAMPLE_POSTS)
    cluster_names = [c["problem_cluster"] for c in clusters]
    # At least one known pain area should be detected
    known = [
        "Manual data entry & sync automation",
        "Affordable invoicing & payment for freelancers",
        "Affordable social media scheduling",
    ]
    found = any(n in cluster_names for n in known)
    assert found, f"Expected at least one known cluster, got: {cluster_names}"


def test_extract_opportunities_heuristic_fallback():
    clusters = extract_opportunities(_SAMPLE_POSTS, use_sklearn=False)
    assert isinstance(clusters, list)
    assert len(clusters) >= 1


def test_extract_opportunities_sklearn():
    try:
        from sklearn.cluster import KMeans  # noqa: F401
        clusters = extract_opportunities(_SAMPLE_POSTS, use_sklearn=True, n_clusters=3)
        assert isinstance(clusters, list)
        assert len(clusters) >= 1
        for c in clusters:
            assert "problem_cluster" in c
            assert "frequency" in c
    except ImportError:
        pytest.skip("scikit-learn not installed")


def test_extract_empty_posts():
    clusters = extract_opportunities([])
    assert clusters == []


def test_extract_single_post():
    posts = [{"source": "reddit", "text": "manual data entry is painful", "metadata": {}}]
    clusters = extract_opportunities(posts, use_sklearn=False)
    assert isinstance(clusters, list)


def test_clusters_sorted_by_frequency():
    clusters = _extract_heuristic(_SAMPLE_POSTS)
    frequencies = [c["frequency"] for c in clusters]
    assert frequencies == sorted(frequencies, reverse=True)

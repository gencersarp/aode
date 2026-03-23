"""Opportunity Extraction Engine.

Groups raw posts into problem clusters using TF-IDF + k-means when scikit-learn
is available, falling back to a keyword-based heuristic otherwise.

Each cluster is summarised into a canonical "pain statement".
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Keyword-based cluster definitions (heuristic fallback & seed topics)
# ---------------------------------------------------------------------------

_CLUSTER_KEYWORDS: dict[str, list[str]] = {
    "Manual data entry & sync automation": [
        "manual", "copy", "sync", "excel", "spreadsheet", "csv", "import",
        "export", "automate", "repetitive", "hours",
    ],
    "Affordable invoicing & payment for freelancers": [
        "invoice", "invoicing", "payment", "freelancer", "paid", "subscription",
        "expensive", "fee", "wire", "international",
    ],
    "Client onboarding workflow automation": [
        "onboarding", "client", "document", "email", "chase", "collect",
        "workflow", "agency", "flow",
    ],
    "Multi-channel inventory & e-commerce sync": [
        "inventory", "shopify", "amazon", "etsy", "multi-channel", "stock",
        "oversell", "e-commerce", "sync",
    ],
    "Affordable social media scheduling": [
        "social", "scheduling", "buffer", "hootsuite", "instagram", "twitter",
        "linkedin", "post", "creator", "content",
    ],
    "Granular access control & row-level permissions": [
        "permission", "access", "row-level", "security", "multi-tenant",
        "saml", "sso", "enterprise", "role",
    ],
    "Marketing attribution & analytics for SMBs": [
        "attribution", "utm", "marketing", "channel", "conversion", "analytics",
        "tracking", "affordable",
    ],
    "Performance & scalability for large datasets": [
        "slow", "timeout", "export", "performance", "large", "scale",
        "streaming", "background job",
    ],
}


def _keyword_score(text: str, keywords: list[str]) -> int:
    """Return the count of keyword matches in *text* (case-insensitive)."""
    lower = text.lower()
    return sum(1 for kw in keywords if kw in lower)


def _extract_heuristic(
    posts: list[dict[str, Any]], min_frequency: int = 1
) -> list[dict[str, Any]]:
    """Assign each post to its best-matching cluster via keyword overlap."""
    cluster_posts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for post in posts:
        text = post.get("text", "")
        best_cluster = None
        best_score = 0
        for cluster_name, keywords in _CLUSTER_KEYWORDS.items():
            score = _keyword_score(text, keywords)
            if score > best_score:
                best_score = score
                best_cluster = cluster_name
        if best_cluster and best_score > 0:
            cluster_posts[best_cluster].append(post)

    clusters: list[dict[str, Any]] = []
    for cluster_name, matched_posts in cluster_posts.items():
        if len(matched_posts) < min_frequency:
            continue
        examples = [p.get("text", "")[:200] for p in matched_posts[:3]]
        clusters.append(
            {
                "problem_cluster": cluster_name,
                "frequency": len(matched_posts),
                "example_cases": examples,
            }
        )

    return sorted(clusters, key=lambda c: c["frequency"], reverse=True)


def _extract_sklearn(
    posts: list[dict[str, Any]], n_clusters: int = 8
) -> list[dict[str, Any]]:
    """TF-IDF + k-means clustering with automatic label extraction."""
    from sklearn.cluster import KMeans  # type: ignore[import-untyped]
    from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore[import-untyped]

    texts = [p.get("text", "") for p in posts]
    if len(texts) < n_clusters:
        n_clusters = max(1, len(texts))

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
    )
    X = vectorizer.fit_transform(texts)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(X)

    feature_names = vectorizer.get_feature_names_out()

    clusters: list[dict[str, Any]] = []
    for cluster_id in range(n_clusters):
        indices = [i for i, lbl in enumerate(labels) if lbl == cluster_id]
        if not indices:
            continue

        # Extract top terms from cluster centre
        center = km.cluster_centers_[cluster_id]
        top_term_indices = center.argsort()[-5:][::-1]
        top_terms = [feature_names[i] for i in top_term_indices]
        cluster_label = _to_title_case(top_terms)

        examples = [texts[i][:200] for i in indices[:3]]
        clusters.append(
            {
                "problem_cluster": cluster_label,
                "frequency": len(indices),
                "example_cases": examples,
            }
        )

    return sorted(clusters, key=lambda c: c["frequency"], reverse=True)


def _to_title_case(terms: list[str]) -> str:
    """Convert a list of TF-IDF terms into a readable cluster label."""
    cleaned = [re.sub(r"[^a-zA-Z0-9 ]", " ", t).strip() for t in terms[:3]]
    return " / ".join(t.title() for t in cleaned if t)


def extract_opportunities(
    posts: list[dict[str, Any]],
    use_sklearn: bool = True,
    n_clusters: int = 8,
) -> list[dict[str, Any]]:
    """Extract problem clusters from raw posts.

    Tries TF-IDF + k-means first (``use_sklearn=True``).  Falls back to a
    keyword heuristic if scikit-learn is not installed.

    Args:
        posts: List of raw post dicts (from scrapers).
        use_sklearn: Attempt ML-based clustering when ``True``.
        n_clusters: Number of k-means clusters to create.

    Returns:
        List of cluster dicts sorted by frequency (descending).
    """
    if not posts:
        return []

    if use_sklearn:
        try:
            return _extract_sklearn(posts, n_clusters=n_clusters)
        except Exception:  # noqa: BLE001
            pass  # fall through to heuristic

    return _extract_heuristic(posts)

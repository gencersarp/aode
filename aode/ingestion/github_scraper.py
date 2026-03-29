"""GitHub Issues scraper — uses PyGitHub when token is available, falls back to mock."""

from __future__ import annotations

import os
from typing import Any

from aode.ingestion import BaseScraper

_TARGET_REPOS = [
    "nicehash/NiceHashQuickMiner",
    "nocodb/nocodb",
    "appwrite/appwrite",
    "n8n-io/n8n",
    "supabase/supabase",
]

_MOCK_ISSUES: list[dict[str, Any]] = [
    {
        "source": "github",
        "text": (
            "Feature request: bulk import from CSV/Excel. "
            "Right now every row has to be entered manually which takes hours for large datasets. "
            "This is blocking adoption for our 50-person sales team."
        ),
        "metadata": {
            "id": "gh_mock_1",
            "title": "Bulk CSV import support",
            "url": "https://github.com/nocodb/nocodb/issues/1001",
            "score": 312,
            "comments": 78,
            "repo": "nocodb/nocodb",
            "labels": ["enhancement", "help wanted"],
        },
    },
    {
        "source": "github",
        "text": (
            "Workflow automation is very limited. "
            "We need conditional branching and loops to handle real business logic. "
            "Current version can only do simple linear pipelines."
        ),
        "metadata": {
            "id": "gh_mock_2",
            "title": "Advanced workflow branching & loops",
            "url": "https://github.com/n8n-io/n8n/issues/2002",
            "score": 487,
            "comments": 123,
            "repo": "n8n-io/n8n",
            "labels": ["enhancement"],
        },
    },
    {
        "source": "github",
        "text": (
            "Authentication provider integration is painful. "
            "We need SAML SSO support for enterprise customers urgently. "
            "Lost two enterprise deals because of this missing feature."
        ),
        "metadata": {
            "id": "gh_mock_3",
            "title": "SAML SSO for enterprise authentication",
            "url": "https://github.com/supabase/supabase/issues/3003",
            "score": 654,
            "comments": 201,
            "repo": "supabase/supabase",
            "labels": ["enhancement", "enterprise"],
        },
    },
    {
        "source": "github",
        "text": (
            "Data export is very slow for large tables (>100k rows). "
            "Export hangs browser tab and often times out. "
            "Need streaming export or background job with download link."
        ),
        "metadata": {
            "id": "gh_mock_4",
            "title": "Slow/timeout on large data exports",
            "url": "https://github.com/nocodb/nocodb/issues/1004",
            "score": 289,
            "comments": 67,
            "repo": "nocodb/nocodb",
            "labels": ["bug", "performance"],
        },
    },
    {
        "source": "github",
        "text": (
            "Mobile app is missing core features available on desktop. "
            "Can't create records or run automations from mobile. "
            "Remote teams heavily depend on mobile access."
        ),
        "metadata": {
            "id": "gh_mock_5",
            "title": "Mobile app feature parity with desktop",
            "url": "https://github.com/appwrite/appwrite/issues/5005",
            "score": 543,
            "comments": 156,
            "repo": "appwrite/appwrite",
            "labels": ["enhancement", "mobile"],
        },
    },
    {
        "source": "github",
        "text": (
            "There's no way to set up granular row-level permissions. "
            "We need users to only see records they created, not all data. "
            "Critical for multi-tenant SaaS use case."
        ),
        "metadata": {
            "id": "gh_mock_6",
            "title": "Row-level security / permissions",
            "url": "https://github.com/nocodb/nocodb/issues/1006",
            "score": 731,
            "comments": 189,
            "repo": "nocodb/nocodb",
            "labels": ["enhancement", "security"],
        },
    },
    {
        "source": "github",
        "text": (
            "Real-time collaboration causes data conflicts when two users edit the same record. "
            "Need conflict resolution and last-write-wins or merge strategy."
        ),
        "metadata": {
            "id": "gh_mock_7",
            "title": "Conflict resolution for concurrent edits",
            "url": "https://github.com/supabase/supabase/issues/3007",
            "score": 398,
            "comments": 93,
            "repo": "supabase/supabase",
            "labels": ["bug", "collaboration"],
        },
    },
]


class GitHubScraper(BaseScraper):
    """Scrapes GitHub Issues for pain points and feature requests.

    Uses the PyGitHub library when ``GITHUB_TOKEN`` is set in the environment.
    Falls back to a curated mock dataset otherwise.
    """

    source_name = "github"

    def __init__(self) -> None:
        self._token = os.getenv("GITHUB_TOKEN", "")

    def _use_real_api(self) -> bool:
        if not self._token:
            return False
        try:
            import github  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._use_real_api():
            return self._fetch_real(limit)
        return self._fetch_mock(limit)

    def _fetch_real(self, limit: int) -> list[dict[str, Any]]:
        try:
            from github import Github  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "PyGithub is required for real GitHub scraping: pip install PyGithub"
            ) from exc

        g = Github(self._token)
        issues: list[dict[str, Any]] = []
        per_repo = max(1, limit // len(_TARGET_REPOS))

        for repo_name in _TARGET_REPOS:
            try:
                repo = g.get_repo(repo_name)
                for issue in repo.get_issues(state="open", sort="reactions")[:per_repo]:
                    body = (issue.body or "").strip()
                    text = f"{issue.title}\n\n{body}".strip()
                    issues.append(
                        {
                            "source": "github",
                            "text": text,
                            "metadata": {
                                "id": str(issue.number),
                                "title": issue.title,
                                "url": issue.html_url,
                                "score": issue.reactions.get("total_count", 0)
                                if hasattr(issue, "reactions")
                                else 0,
                                "comments": issue.comments,
                                "repo": repo_name,
                                "labels": [lbl.name for lbl in issue.labels],
                            },
                        }
                    )
            except Exception:  # noqa: BLE001
                continue  # skip repos that are inaccessible

        return issues[:limit]

    def _fetch_mock(self, limit: int) -> list[dict[str, Any]]:
        return _MOCK_ISSUES[:limit]

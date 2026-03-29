"""Reddit scraper — uses PRAW when credentials are available, falls back to mock data."""

from __future__ import annotations

import os
from typing import Any

from aode.ingestion import BaseScraper

# Pain-point subreddits that surface genuine user frustrations
_TARGET_SUBREDDITS = [
    "entrepreneur",
    "smallbusiness",
    "SaaS",
    "startups",
    "Entrepreneur",
    "freelance",
    "digitalnomad",
]

_MOCK_POSTS: list[dict[str, Any]] = [
    {
        "source": "reddit",
        "text": (
            "I spend 3 hours every week manually copying data from Excel into our CRM. "
            "There has to be a better way. The sync tools I've tried are $300+/month and "
            "still break half the time. Wish there was something simple and affordable."
        ),
        "metadata": {
            "id": "mock_r1",
            "title": "Excel to CRM sync is a nightmare",
            "url": "https://reddit.com/r/smallbusiness/mock1",
            "score": 412,
            "comments": 87,
            "subreddit": "smallbusiness",
        },
    },
    {
        "source": "reddit",
        "text": (
            "Why is it so hard to find a simple invoicing tool that doesn't require a "
            "monthly subscription? I just need to send 5-10 invoices a month. Every option "
            "is either too basic or costs $30+/month."
        ),
        "metadata": {
            "id": "mock_r2",
            "title": "Invoicing tools are overpriced for freelancers",
            "url": "https://reddit.com/r/freelance/mock2",
            "score": 678,
            "comments": 134,
            "subreddit": "freelance",
        },
    },
    {
        "source": "reddit",
        "text": (
            "Client onboarding is killing me. I have to send the same 10 emails, "
            "collect documents manually, and chase people for weeks. "
            "No tool handles the whole flow end-to-end for agencies our size."
        ),
        "metadata": {
            "id": "mock_r3",
            "title": "Client onboarding automation for small agencies?",
            "url": "https://reddit.com/r/entrepreneur/mock3",
            "score": 521,
            "comments": 203,
            "subreddit": "entrepreneur",
        },
    },
    {
        "source": "reddit",
        "text": (
            "I run a small e-commerce store and inventory tracking across Shopify, "
            "Amazon, and Etsy is a mess. Sold the same item twice last week. "
            "Multi-channel inventory sync is either enterprise-only or insanely expensive."
        ),
        "metadata": {
            "id": "mock_r4",
            "title": "Multi-channel inventory sync for small stores",
            "url": "https://reddit.com/r/smallbusiness/mock4",
            "score": 344,
            "comments": 91,
            "subreddit": "smallbusiness",
        },
    },
    {
        "source": "reddit",
        "text": (
            "Scheduling social media posts across platforms manually is exhausting. "
            "Buffer and Hootsuite are way too expensive for a solo creator. "
            "I need something that supports LinkedIn + Twitter + Instagram under $10/month."
        ),
        "metadata": {
            "id": "mock_r5",
            "title": "Affordable social scheduling for solo creators",
            "url": "https://reddit.com/r/digitalnomad/mock5",
            "score": 899,
            "comments": 267,
            "subreddit": "digitalnomad",
        },
    },
    {
        "source": "reddit",
        "text": (
            "Tried 6 different project management tools this year. "
            "They're all either too complicated or don't have the exact features my team needs. "
            "We end up going back to spreadsheets every time."
        ),
        "metadata": {
            "id": "mock_r6",
            "title": "Project management tools are overcomplicated",
            "url": "https://reddit.com/r/startups/mock6",
            "score": 731,
            "comments": 188,
            "subreddit": "startups",
        },
    },
    {
        "source": "reddit",
        "text": (
            "Getting paid as an international freelancer is a huge pain. "
            "Wise fees add up, PayPal holds funds, and crypto isn't accepted everywhere. "
            "I lose 5-8% on every payment. There's no affordable solution for small amounts."
        ),
        "metadata": {
            "id": "mock_r7",
            "title": "International payment pain for freelancers",
            "url": "https://reddit.com/r/freelance/mock7",
            "score": 1043,
            "comments": 312,
            "subreddit": "freelance",
        },
    },
    {
        "source": "reddit",
        "text": (
            "I can never figure out which of my marketing channels actually converts. "
            "UTM tracking is manual and breaks all the time. "
            "Attribution software costs $500+/month and is built for enterprise teams."
        ),
        "metadata": {
            "id": "mock_r8",
            "title": "Affordable marketing attribution for SMBs",
            "url": "https://reddit.com/r/SaaS/mock8",
            "score": 456,
            "comments": 102,
            "subreddit": "SaaS",
        },
    },
]


class RedditScraper(BaseScraper):
    """Scrapes Reddit for pain-point discussions.

    When ``REDDIT_CLIENT_ID`` / ``REDDIT_CLIENT_SECRET`` / ``REDDIT_USER_AGENT``
    environment variables are set the real PRAW API is used.  Otherwise the
    built-in mock dataset is returned so the system works fully offline.
    """

    source_name = "reddit"

    def __init__(self) -> None:
        self._client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self._client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self._user_agent = os.getenv("REDDIT_USER_AGENT", "aode/0.1 by aode-bot")

    def _use_real_api(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def fetch(self, limit: int = 100) -> list[dict[str, Any]]:
        if self._use_real_api():
            return self._fetch_real(limit)
        return self._fetch_mock(limit)

    def _fetch_real(self, limit: int) -> list[dict[str, Any]]:
        try:
            import praw  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "praw is required for real Reddit scraping: pip install praw"
            ) from exc

        reddit = praw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        )

        posts: list[dict[str, Any]] = []
        per_sub = max(1, limit // len(_TARGET_SUBREDDITS))
        for sub_name in _TARGET_SUBREDDITS:
            subreddit = reddit.subreddit(sub_name)
            for submission in subreddit.hot(limit=per_sub):
                text = (submission.selftext or submission.title).strip()
                if not text:
                    continue
                posts.append(
                    {
                        "source": "reddit",
                        "text": f"{submission.title}\n\n{submission.selftext}".strip(),
                        "metadata": {
                            "id": submission.id,
                            "title": submission.title,
                            "url": submission.url,
                            "score": submission.score,
                            "comments": submission.num_comments,
                            "subreddit": sub_name,
                        },
                    }
                )
        return posts[:limit]

    def _fetch_mock(self, limit: int) -> list[dict[str, Any]]:
        return _MOCK_POSTS[:limit]

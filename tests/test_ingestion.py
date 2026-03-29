"""Tests for the data ingestion layer."""

from __future__ import annotations

import pytest

from aode.ingestion.reddit_scraper import RedditScraper
from aode.ingestion.github_scraper import GitHubScraper


def test_reddit_scraper_mock_returns_list():
    scraper = RedditScraper()
    posts = scraper.fetch(limit=5)
    assert isinstance(posts, list)
    assert len(posts) <= 5


def test_reddit_scraper_mock_post_schema():
    scraper = RedditScraper()
    posts = scraper.fetch(limit=3)
    for post in posts:
        assert "source" in post
        assert "text" in post
        assert "metadata" in post
        assert post["source"] == "reddit"
        assert isinstance(post["text"], str)
        assert len(post["text"]) > 0
        assert "id" in post["metadata"]


def test_github_scraper_mock_returns_list():
    scraper = GitHubScraper()
    issues = scraper.fetch(limit=5)
    assert isinstance(issues, list)
    assert len(issues) <= 5


def test_github_scraper_mock_issue_schema():
    scraper = GitHubScraper()
    issues = scraper.fetch(limit=3)
    for issue in issues:
        assert "source" in issue
        assert "text" in issue
        assert "metadata" in issue
        assert issue["source"] == "github"
        assert isinstance(issue["text"], str)
        assert len(issue["text"]) > 0


def test_reddit_scraper_respects_limit():
    scraper = RedditScraper()
    posts = scraper.fetch(limit=2)
    assert len(posts) <= 2


def test_github_scraper_respects_limit():
    scraper = GitHubScraper()
    issues = scraper.fetch(limit=2)
    assert len(issues) <= 2


def test_scrapers_combined_output():
    reddit = RedditScraper()
    github = GitHubScraper()
    all_posts = reddit.fetch(limit=4) + github.fetch(limit=4)
    sources = {p["source"] for p in all_posts}
    assert "reddit" in sources
    assert "github" in sources

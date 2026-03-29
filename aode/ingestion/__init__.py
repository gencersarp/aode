"""Data ingestion layer — base scraper contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseScraper(ABC):
    """All scrapers must implement this interface."""

    source_name: str = "unknown"

    @abstractmethod
    def fetch(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return a list of raw post dicts.

        Each dict must have the shape::

            {
                "source": str,
                "text": str,
                "metadata": {
                    "id": str,          # unique external identifier
                    "title": str,       # optional headline
                    "url": str,         # optional permalink
                    "score": int,       # upvotes / reactions / thumbs
                    "comments": int,    # engagement signal
                },
            }
        """

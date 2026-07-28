"""
Tavily Data Models — Plan B

Immutable, fully-typed data models representing the data structures
exchanged between the elements of the Tavily independent module.

These models are responsible ONLY for data modelling:
    - No business logic
    - No network operations
    - No environment variable reads
    - No imports from frozen modules (MarketEvent, MasterEngine,
      DecisionEngine, RuntimeService)
    - No side effects on import

All models use :func:`dataclasses.dataclass` with ``frozen=True``
to guarantee immutability.

Usage::

    from data.tavily.models import TavilyResultItem, TavilyContext, TavilyQueryRequest
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# TavilyResultItem — a single search result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TavilyResultItem:
    """A single result returned by the Tavily Search API.

    This is the atomic unit of the ``top_results`` field in
    :class:`TavilyContext`.  Each item represents one web page
    or news article found by Tavily.

    Attributes:
        title: Title of the result (headline or page title).
        url: Full URL of the result.
        content: Snippet or full text content returned by Tavily.
        published_date: Publication date, if provided by the source.
            May be ``None`` when the source does not include a date.
        score: Relevance score assigned by Tavily (0.0–1.0).
            May be ``None`` when Tavily does not provide a score.
    """

    title: str
    url: str
    content: str
    published_date: Optional[datetime] = None
    score: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate fields after frozen init."""
        if not self.title.strip():
            raise ValueError("title must be a non-empty, non-blank string")
        if not self.url.strip():
            raise ValueError("url must be a non-empty, non-blank string")
        if self.score is not None and not (0.0 <= self.score <= 1.0):
            raise ValueError(
                f"score must be in [0.0, 1.0], got {self.score}"
            )


# ---------------------------------------------------------------------------
# TavilyContext — the tavily_context field of MarketEvent (§3.5)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TavilyContext:
    """Context produced by the Tavily module for a :class:`MarketEvent`.

    This object is assigned to ``MarketEvent.tavily_context``
    (ETAP 7 of the MarketEvent lifecycle — see
    ``docs/Kontrakt_Zdarzen_Rynkowych.md`` §3.5).

    The structure is defined by the MarketEvent contract (§1.2, field 21):
    ``object (fields: query, results_count, top_results, sentiment)``.

    Attributes:
        query: The search query sent to Tavily.
        results_count: Total number of results returned by Tavily
            (before filtering).
        top_results: Immutable tuple of the best results after filtering
            and normalisation.  May be empty if no results were found.
        sentiment: Aggregate sentiment of the top results (-1.0 to 1.0).
            May be ``None`` if sentiment analysis was not performed or
            is not available.
    """

    query: str
    results_count: int
    top_results: tuple[TavilyResultItem, ...] = field(default_factory=tuple)
    sentiment: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate fields after frozen init."""
        if not self.query.strip():
            raise ValueError("query must be a non-empty, non-blank string")
        if self.results_count < 0:
            raise ValueError(
                f"results_count must be >= 0, got {self.results_count}"
            )
        if self.sentiment is not None and not (-1.0 <= self.sentiment <= 1.0):
            raise ValueError(
                f"sentiment must be in [-1.0, 1.0], got {self.sentiment}"
            )


# ---------------------------------------------------------------------------
# TavilyQueryRequest — internal query model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TavilyQueryRequest:
    """Immutable representation of a search query for the Tavily API.

    This is an internal data model exchanged between the elements
    of the Tavily module (e.g. between the decision layer and the
    API client).  It is NOT part of the MarketEvent contract.

    Attributes:
        query: Free-text search query. Must be a non-empty,
            non-blank string.
        max_results: Maximum number of results to request from
            the API.
        search_depth: Search depth — ``"basic"`` or ``"advanced"``.
        include_domains: Domains to include (whitelist).  An empty
            tuple means no domain filtering.
        exclude_domains: Domains to exclude (blacklist).  An empty
            tuple means no domain filtering.
    """

    query: str
    max_results: int = 10
    search_depth: str = "basic"
    include_domains: tuple[str, ...] = field(default_factory=tuple)
    exclude_domains: tuple[str, ...] = field(default_factory=tuple)

    # Allowed values for search_depth
    _ALLOWED_DEPTHS: tuple[str, ...] = ("basic", "advanced")

    def __post_init__(self) -> None:
        """Validate fields after frozen init."""
        if not self.query.strip():
            raise ValueError("query must be a non-empty, non-blank string")
        if self.max_results < 1:
            raise ValueError(
                f"max_results must be >= 1, got {self.max_results}"
            )
        if self.search_depth not in self._ALLOWED_DEPTHS:
            raise ValueError(
                f"search_depth must be one of {self._ALLOWED_DEPTHS}, "
                f"got {self.search_depth!r}"
            )
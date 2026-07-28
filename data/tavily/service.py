"""
Tavily Service Layer — Plan B

Independent, synchronous service layer that orchestrates the
full Tavily search workflow:

    1. Build a TavilyQueryRequest from business parameters.
    2. Call TavilyClient.search().
    3. Parse the raw API response into TavilyResultItems.
    4. Filter results by time window (max_age_hours).
    5. Sort and limit results.
    6. Return a validated TavilyContext.

This module is part of the independent Tavily module:
    - No imports from frozen modules
    - No integration with MasterEngine, Runtime, or DecisionEngine
    - No side effects on import
    - Uses only existing Tavily components (config, client, models, errors)

Usage::

    from data.tavily.config import TavilyConfig
    from data.tavily.service import TavilyService

    config = TavilyConfig.from_env()
    service = TavilyService(config)
    ctx = service.search(
        ticker="XYZ.WA",
        market="GPW",
        event_type="PRICE_SURGE",
        event_category="Cenowe",
        detection_time=datetime.now(timezone.utc),
    )
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from data.tavily.client import TavilyClient
from data.tavily.config import TavilyConfig
from data.tavily.errors import (
    TavilyConfigError,
    TavilyValidationError,
)
from data.tavily.models import (
    TavilyContext,
    TavilyQueryRequest,
    TavilyResultItem,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known Tavily API response fields for result items
# ---------------------------------------------------------------------------
# Tavily returns results as a list of dicts inside the "results" key.
# Each result dict typically contains:
#   title    (str)       — headline / page title
#   url      (str)       — full URL
#   content  (str)       — snippet or full text
#   score    (float|None)— relevance score (0.0–1.0)
#   published_date (str|None) — ISO 8601 string or None
#
# The service must handle missing or malformed fields gracefully:
#   - Missing "title" / "url" / "content" → skip the record
#   - Malformed "score" → set to None
#   - Unparseable "published_date" → set to None
# ---------------------------------------------------------------------------

_TITLE_KEY = "title"
_URL_KEY = "url"
_CONTENT_KEY = "content"
_SCORE_KEY = "score"
_PUBLISHED_DATE_KEY = "published_date"

# Fields that must be present AND have a usable value for a result to be kept.
_REQUIRED_FIELDS = (_TITLE_KEY, _URL_KEY, _CONTENT_KEY)


class TavilyService:
    """Orchestrates the full Tavily search workflow.

    Constructed with a :class:`TavilyConfig`.  Uses an internal
    :class:`TavilyClient` for HTTP operations.

    The service is designed to be **called once per MarketEvent**
    — it handles one search cycle end-to-end.

    Attributes:
        config: The immutable configuration.
        _client: Internal TavilyClient instance.
    """

    def __init__(self, config: TavilyConfig) -> None:
        """Initialise the service with a TavilyConfig.

        Args:
            config: A validated :class:`TavilyConfig` instance.

        Raises:
            TypeError: If *config* is not a :class:`TavilyConfig`.
        """
        if not isinstance(config, TavilyConfig):
            raise TypeError(
                f"config must be a TavilyConfig instance, "
                f"got {type(config).__name__}"
            )
        self._config = config
        self._client = TavilyClient(config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        ticker: str,
        market: str,
        event_type: str,
        event_category: str,
        detection_time: datetime,
        *,
        company_name: Optional[str] = None,
        event_subcategory: Optional[str] = None,
    ) -> TavilyContext:
        """Execute a full search cycle and return a validated TavilyContext.

        The workflow is:
            1. Build a TavilyQueryRequest from the business parameters.
            2. Execute the search via TavilyClient.
            3. Parse raw API response into TavilyResultItems.
            4. Filter by time window (config.max_age_hours from detection_time).
            5. Sort and limit to config.max_accepted_results.
            6. Build and return a TavilyContext.

        Args:
            ticker: Instrument ticker (e.g. ``"XYZ.WA"``).
            market: Exchange identifier (e.g. ``"GPW"``, ``"NYSE"``).
            event_type: The detected event type (e.g. ``"PRICE_SURGE"``).
            event_category: The event category (e.g. ``"Cenowe"``).
            detection_time: UTC timestamp when the event was detected.
                Used for time-window filtering.
            company_name: Optional company name to enrich the query.
            event_subcategory: Optional event subcategory for finer
                query granularity.

        Returns:
            TavilyContext: Validated and time-filtered search context.
            May contain an empty ``top_results`` tuple if no valid
            results were found or the API returned empty results.

        Raises:
            TavilyConfigError: If the Tavily module is disabled.
            TavilyAPIError, TavilyTimeoutError, TavilyRateLimitError,
                TavilyConnectionError, TavilyValidationError:
                Propagated from TavilyClient.
        """
        query_text = self._build_query_text(
            ticker=ticker,
            market=market,
            event_type=event_type,
            event_category=event_category,
            company_name=company_name,
            event_subcategory=event_subcategory,
        )

        request = TavilyQueryRequest(
            query=query_text,
            max_results=self._config.max_results_from_api,
        )

        raw_response = self._client.search(request)

        results = self._parse_results(raw_response)
        filtered = self._filter_by_time_window(
            results, detection_time, self._config.max_age_hours
        )
        filtered = self._sort_and_limit(
            filtered, self._config.max_accepted_results
        )

        raw_results = raw_response.get("results")
        results_count = len(raw_results) if isinstance(raw_results, list) else 0

        return TavilyContext(
            query=query_text,
            results_count=results_count,
            top_results=tuple(filtered),
            sentiment=None,
        )

    # ------------------------------------------------------------------
    # Query builder
    # ------------------------------------------------------------------

    def _build_query_text(
        self,
        ticker: str,
        market: str,
        event_type: str,
        event_category: str,
        *,
        company_name: Optional[str] = None,
        event_subcategory: Optional[str] = None,
    ) -> str:
        """Build a natural-language search query for Tavily.

        The query is focused on fresh, event-specific context:
          - The ticker and market anchor the search to the instrument.
          - The event type and category describe *what* happened.
          - The company name (if available) adds precision.
          - The query targets recent news and analysis relevant to the event.

        Philosophy (from docs/FILOZOFIA_ALCHEMIKA.md):
            Tavily is used to find fresh informational context, not
            historical data. The query must target *why* the event
            is happening right now.

        Returns:
            A non-empty, non-blank search query string.
        """
        parts: list[str] = []

        # Anchor: ticker + market
        market_label = self._market_label(market)
        parts.append(f"stock {ticker} {market_label}")

        # Company name (if available)
        if company_name and company_name.strip():
            parts.append(company_name.strip())

        # Event classification
        human_event = event_type.replace("_", " ").lower()
        parts.append(human_event)

        if event_subcategory and event_subcategory.strip():
            parts.append(event_subcategory.strip())
        parts.append(event_category.lower())

        # Time context: search for recent information
        parts.append("recent news analysis why")

        return " ".join(parts)

    @staticmethod
    def _market_label(market: str) -> str:
        """Return a human-readable label for a market identifier."""
        mapping: dict[str, str] = {
            "GPW": "Warsaw Stock Exchange GPW",
            "NYSE": "NYSE",
            "NASDAQ": "NASDAQ",
            "AMEX": "AMEX",
            "LSE": "London Stock Exchange",
            "XETRA": "XETRA",
        }
        upper = market.upper()
        return mapping.get(upper, market.upper())

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_results(self, raw_response: dict[str, object]) -> list[TavilyResultItem]:
        """Extract and validate TavilyResultItems from the raw API response.

        Each result entry in ``raw_response["results"]`` is converted
        to a TavilyResultItem.  Malformed or incomplete records are
        silently skipped (logged as debug).

        Returns:
            List of valid TavilyResultItem objects.  Empty list if no
            results were present or all were invalid.
        """
        raw_results = raw_response.get("results")
        if raw_results is None:
            return []
        if not isinstance(raw_results, list):
            return []

        parsed: list[TavilyResultItem] = []
        for idx, entry in enumerate(raw_results):
            if not isinstance(entry, dict):
                logger.debug("Skipping result[%d]: not a dict", idx)
                continue

            # Required fields must be present AND have string values.
            title = entry.get(_TITLE_KEY)
            url = entry.get(_URL_KEY)
            content = entry.get(_CONTENT_KEY)

            if not isinstance(title, str) or not title.strip():
                logger.debug("Skipping result[%d]: missing/empty title", idx)
                continue
            if not isinstance(url, str) or not url.strip():
                logger.debug("Skipping result[%d]: missing/empty url", idx)
                continue
            if not isinstance(content, str) or not content.strip():
                logger.debug("Skipping result[%d]: missing/empty content", idx)
                continue

            # Optional fields
            score = self._parse_score(entry.get(_SCORE_KEY))
            published_date = self._parse_published_date(
                entry.get(_PUBLISHED_DATE_KEY)
            )

            try:
                item = TavilyResultItem(
                    title=title.strip(),
                    url=url.strip(),
                    content=content.strip(),
                    published_date=published_date,
                    score=score,
                )
                parsed.append(item)
            except ValueError as exc:
                logger.debug("Skipping result[%d]: %s", idx, exc)
                continue

        return parsed

    @staticmethod
    def _parse_score(raw: object) -> Optional[float]:
        """Parse a Tavily relevance score, defaulting to None on failure."""
        if raw is None:
            return None
        try:
            value = float(raw)  # type: ignore[arg-type]
            if 0.0 <= value <= 1.0:
                return value
        except (TypeError, ValueError):
            pass
        return None

    @staticmethod
    def _parse_published_date(raw: object) -> Optional[datetime]:
        """Parse an ISO 8601 published_date string, defaulting to None."""
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            # Python 3.11+ datetime.fromisoformat handles most ISO 8601 forms
            dt = datetime.fromisoformat(raw.strip())
            # Normalise to UTC if it carries tzinfo, treat naive as UTC
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Time-window filtering
    # ------------------------------------------------------------------

    def _filter_by_time_window(
        self,
        results: list[TavilyResultItem],
        detection_time: datetime,
        max_age_hours: int,
    ) -> list[TavilyResultItem]:
        """Filter results to those within the time window.

        A result is kept if:
          - It has no ``published_date`` (we keep items without dates),
            OR
          - Its ``published_date`` >= detection_time - max_age_hours.

        Args:
            results: Parsed result items.
            detection_time: The UTC timestamp of event detection.
            max_age_hours: Maximum age of accepted results in hours.

        Returns:
            Filtered list of TavilyResultItems.
        """
        if max_age_hours <= 0 or not results:
            return results

        cutoff = detection_time - timedelta(hours=max_age_hours)
        filtered: list[TavilyResultItem] = []
        for item in results:
            if item.published_date is None:
                # Keep items without dates — we cannot determine age.
                filtered.append(item)
            elif item.published_date >= cutoff:
                filtered.append(item)
            else:
                logger.debug(
                    "Dropping result (too old): %s published %s (cutoff %s)",
                    item.title,
                    item.published_date.isoformat(),
                    cutoff.isoformat(),
                )
        return filtered

    # ------------------------------------------------------------------
    # Sorting and limiting
    # ------------------------------------------------------------------

    def _sort_and_limit(
        self,
        results: list[TavilyResultItem],
        max_accepted: int,
    ) -> list[TavilyResultItem]:
        """Sort results by score (descending), then published_date (descending).

        Items with ``score=None`` are placed after scored items.
        Items with ``published_date=None`` are placed after dated items
        within their score group.

        The result is limited to ``max_accepted`` items.

        Args:
            results: Result items.
            max_accepted: Maximum number of results to return.

        Returns:
            Sorted and limited list.
        """
        if not results:
            return []

        def _sort_key(item: TavilyResultItem) -> tuple[int, float, float]:
            # sort ascending:
            #   group: 0 (scored) before 1 (unscored)
            #   neg_score: more negative (= higher score) comes first
            #   neg_ts: more negative (= newer date) comes first
            group = 0 if item.score is not None else 1
            neg_score = -(item.score if item.score is not None else 0.0)
            if item.published_date is not None:
                neg_ts = -item.published_date.timestamp()
            else:
                # Use +inf so undated items sort AFTER dated items
                # (ascending sort puts smaller values first;
                #  -timestamp < +inf, so dated items come first)
                neg_ts = float("inf")
            return (group, neg_score, neg_ts)

        results.sort(key=_sort_key)

        return results[:max_accepted]

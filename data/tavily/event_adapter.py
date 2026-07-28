"""
Tavily Event Adapter — MarketEvent → TavilyService bridge.

Independent adapter that maps an existing :class:`MarketEvent`
to the arguments expected by :class:`TavilyService.search` and
delegates the actual search call.

This module is part of the independent Tavily module:
    - No imports from Runtime, MasterEngine, DecisionEngine
    - No imports from frozen silnki (engines.*)
    - Does NOT consume PipelineDecision.run_tavily
    - No side effects on import
    - Uses only existing Tavily components

Usage::

    from data.tavily.config import TavilyConfig
    from data.tavily.service import TavilyService
    from data.tavily.event_adapter import TavilyEventAdapter

    config = TavilyConfig.from_env()
    service = TavilyService(config)
    adapter = TavilyEventAdapter(service)
    ctx = adapter.search_for_event(market_event)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from data.tavily.errors import TavilyConfigError
from data.tavily.models import TavilyContext
from data.tavily.service import TavilyService

if TYPE_CHECKING:
    from data.models.market_event import MarketEvent


class TavilyEventAdapter:
    """Adapts a MarketEvent for TavilyService.search().

    Reads classification and timestamp fields from the MarketEvent
    and passes them to TavilyService in the format it expects.

    Constructed with a pre-configured :class:`TavilyService` instance.
    The adapter performs **no network operations** itself — it delegates
    entirely to the service.

    Attributes:
        _service: The TavilyService instance used for searches.
    """

    def __init__(self, service: TavilyService) -> None:
        """Initialise the adapter with a TavilyService.

        Args:
            service: A pre-configured :class:`TavilyService` instance.

        Raises:
            TypeError: If *service* is not a :class:`TavilyService`.
        """
        if not isinstance(service, TavilyService):
            raise TypeError(
                f"service must be a TavilyService instance, "
                f"got {type(service).__name__}"
            )
        self._service = service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_for_event(self, event: "MarketEvent") -> TavilyContext:
        """Execute a Tavily search for a given MarketEvent.

        Extracts classification and timestamp data from the event,
        normalises ``timestamp_utc`` to UTC, and delegates to
        :meth:`TavilyService.search`.

        The following MarketEvent fields are used:
            - ``ticker``
            - ``market``
            - ``event_type``
            - ``event_category``
            - ``event_subcategory`` (optional)
            - ``timestamp_utc``

        ``company_name`` is **not available** in MarketEvent and
        is always passed as ``None`` (the default).

        Args:
            event: A MarketEvent with at minimum identification,
                classification, and timestamp fields set.

        Returns:
            TavilyContext: The search context returned by TavilyService.

        Raises:
            TypeError: If *event* is not a MarketEvent instance.
            TavilyConfigError: If the Tavily module is disabled.
            TavilyAPIError, TavilyTimeoutError, TavilyRateLimitError,
                TavilyConnectionError, TavilyValidationError:
                Propagated from TavilyService/TavilyClient.
        """
        # Late import avoids hard dependency at module level.
        # TYPE_CHECKING block ensures type safety at analysis time.
        from data.models.market_event import MarketEvent

        if not isinstance(event, MarketEvent):
            raise TypeError(
                f"event must be a MarketEvent instance, "
                f"got {type(event).__name__}"
            )

        detection_time = self._normalise_timestamp(event.timestamp_utc)

        return self._service.search(
            ticker=event.ticker,
            market=event.market,
            event_type=event.event_type,
            event_category=event.event_category,
            detection_time=detection_time,
            event_subcategory=event.event_subcategory,
            # company_name is not available in MarketEvent.
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_timestamp(ts: datetime) -> datetime:
        """Ensure *ts* is a timezone-aware UTC datetime.

        Naive datetimes are treated as UTC. Already-aware datetimes
        are converted to UTC via ``astimezone``.

        Args:
            ts: A datetime from MarketEvent.timestamp_utc.

        Returns:
            An equivalent timezone-aware datetime in UTC.
        """
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
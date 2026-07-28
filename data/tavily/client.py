"""
Tavily HTTP Client — Plan B

Independent, synchronous HTTP client for the Tavily Search API.
Uses the ``requests`` library already present in the project.

This module is part of the independent Tavily module:
    - No imports from frozen modules
    - No side effects on import
    - No environment variable reads (uses TavilyConfig)

Usage::

    from data.tavily.config import TavilyConfig
    from data.tavily.models import TavilyQueryRequest
    from data.tavily.client import TavilyClient

    config = TavilyConfig.from_env()
    client = TavilyClient(config)
    request = TavilyQueryRequest(query="market news")
    result = client.search(request)

Error handling — every error maps to a specific exception
from :mod:`data.tavily.errors`:

    ======================== ============================
    Condition                 Exception
    ======================== ============================
    ``enabled=False``         :class:`TavilyConfigError`
    Invalid config/request    :class:`TypeError`
    ``requests.Timeout``      :class:`TavilyTimeoutError`
    ``requests.ConnectionError` :class:`TavilyConnectionError`
    HTTP 429                  :class:`TavilyRateLimitError`
    HTTP 4xx / 5xx            :class:`TavilyAPIError`
    Invalid JSON response     :class:`TavilyValidationError`
    Non-dict JSON response    :class:`TavilyValidationError`
    ======================== ============================
"""

from __future__ import annotations

import requests

from data.tavily.config import TavilyConfig
from data.tavily.errors import (
    TavilyAPIError,
    TavilyConfigError,
    TavilyConnectionError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    TavilyValidationError,
)
from data.tavily.models import TavilyQueryRequest


class TavilyClient:
    """Synchronous HTTP client for the Tavily Search API.

    Constructed with a :class:`TavilyConfig` instance.  The constructor
    performs **no network operations** — the first HTTP call happens in
    :meth:`search`.

    Attributes:
        config: The immutable configuration used for every request.
    """

    def __init__(self, config: TavilyConfig) -> None:
        """Initialise the client with a TavilyConfig.

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, request: TavilyQueryRequest) -> dict[str, object]:
        """Execute a single synchronous search request against Tavily.

        Args:
            request: A validated :class:`TavilyQueryRequest`.

        Returns:
            The raw JSON response dictionary, unchanged.

        Raises:
            TypeError: If *request* is not a :class:`TavilyQueryRequest`.
            TavilyConfigError: If the module is disabled
                (``config.enabled == False``).
            TavilyTimeoutError: If the request times out.
            TavilyConnectionError: If a network connection cannot be
                established.
            TavilyRateLimitError: If the API returns HTTP 429.
            TavilyAPIError: For any other HTTP 4xx or 5xx response.
            TavilyValidationError: If the response body is not valid
                JSON or the JSON root is not a ``dict``.
        """
        if not isinstance(request, TavilyQueryRequest):
            raise TypeError(
                f"request must be a TavilyQueryRequest instance, "
                f"got {type(request).__name__}"
            )

        if not self._config.enabled:
            raise TavilyConfigError(
                "Tavily module is disabled (TAVILY_ENABLED=False). "
                "Set TAVILY_ENABLED=True to enable API calls."
            )

        url = f"{self._config.base_url.rstrip('/')}/search"
        payload = self._build_payload(request)
        timeout = self._config.timeout_seconds

        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.Timeout:
            raise TavilyTimeoutError(
                f"Tavily API request timed out after {timeout}s"
            )
        except requests.ConnectionError:
            raise TavilyConnectionError(
                "Failed to connect to Tavily API"
            )

        # --- HTTP status checks ---
        if response.status_code == 429:
            raise TavilyRateLimitError("Tavily API rate limit exceeded")
        if response.status_code >= 400:
            raise TavilyAPIError(
                f"Tavily API returned HTTP {response.status_code}"
            )

        # --- JSON parsing & validation ---
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            raise TavilyValidationError(
                "Tavily API returned invalid JSON"
            )

        if not isinstance(data, dict):
            raise TavilyValidationError(
                f"Tavily API returned unexpected type "
                f"{type(data).__name__} (expected dict)"
            )

        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_payload(self, request: TavilyQueryRequest) -> dict[str, object]:
        """Build the JSON payload for a Tavily search request.

        The *api_key* is included in every request but is never exposed
        in log messages or exception text.
        """
        payload: dict[str, object] = {
            "api_key": self._config.api_key,
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": request.search_depth,
        }
        if request.include_domains:
            payload["include_domains"] = list(request.include_domains)
        if request.exclude_domains:
            payload["exclude_domains"] = list(request.exclude_domains)
        return payload
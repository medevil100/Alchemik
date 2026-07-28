"""
Tavily Configuration

This module provides the configuration class for the Tavily module.
Configuration values are read from environment variables via the
factory method :meth:`TavilyConfig.from_env`.

The import of this module has no side effects — no environment
variables are read until :meth:`TavilyConfig.from_env` is called.

Usage:
    config = TavilyConfig.from_env()
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from data.tavily.errors import TavilyConfigError


@dataclass(frozen=True)
class TavilyConfig:
    """Immutable configuration for the Tavily module.

    All fields are read-only after construction. Use :meth:`from_env`
    to create an instance populated from environment variables.

    Attributes:
        api_key: Tavily API key. Must be a non-empty, non-blank string.
        enabled: Whether the Tavily module is active. Disabled modules
            skip all API calls without raising errors.
        timeout_seconds: Total HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts for transient errors.
        max_results_from_api: Number of results requested from the Tavily API
            in a single call.
        max_accepted_results: Maximum number of results stored in
            ``tavily_context`` after filtering and normalisation.
        max_age_hours: Maximum age of accepted results. Results older than
            this are discarded during time-window filtering.
        max_requests_per_minute: Hard limit on API calls per minute.
            Calls exceeding this limit are skipped with a rate-limit error.
        base_url: Base URL of the Tavily API.
    """

    api_key: str
    enabled: bool = True
    timeout_seconds: float = 15.0
    max_retries: int = 2
    max_results_from_api: int = 20
    max_accepted_results: int = 10
    max_age_hours: int = 24
    max_requests_per_minute: int = 5
    base_url: str = "https://api.tavily.com"

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "TavilyConfig":
        """Create a TavilyConfig from environment variables.

        Reads the following variables:

        * ``TAVILY_API_KEY`` — required when ``TAVILY_ENABLED`` is not
          ``"False"``. Must be a non-empty string that is not solely
          whitespace.
        * ``TAVILY_ENABLED`` — optional, ``"True"`` by default.
          Set to ``"False"`` (case-insensitive) to disable all Tavily
          API calls.
        * ``TAVILY_TIMEOUT`` — optional, defaults to ``15`` (seconds).
        * ``TAVILY_MAX_RETRIES`` — optional, defaults to ``2``.
        * ``TAVILY_RATE_LIMIT`` — optional, defaults to ``5``.

        Returns:
            TavilyConfig: A fully initialised, validated configuration.

        Raises:
            TavilyConfigError: If the module is enabled and
                ``TAVILY_API_KEY`` is missing, empty, or whitespace-only.
        """
        enabled = cls._read_enabled()
        api_key = cls._read_api_key(required=enabled)

        return cls(
            api_key=api_key,
            enabled=enabled,
            timeout_seconds=cls._read_float("TAVILY_TIMEOUT", 15.0),
            max_retries=cls._read_int("TAVILY_MAX_RETRIES", 2),
            max_results_from_api=20,
            max_accepted_results=10,
            max_age_hours=24,
            max_requests_per_minute=cls._read_int("TAVILY_RATE_LIMIT", 5),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_enabled() -> bool:
        """Determine whether the Tavily module is enabled."""
        raw = os.environ.get("TAVILY_ENABLED", "True").strip().lower()
        if raw in ("false", "0", "no", "off"):
            return False
        return True

    @staticmethod
    def _read_api_key(*, required: bool) -> str:
        """Read ``TAVILY_API_KEY``, raising TavilyConfigError if invalid."""
        raw = os.environ.get("TAVILY_API_KEY", "")

        if required:
            if not raw or not raw.strip():
                raise TavilyConfigError(
                    "Tavily is enabled but TAVILY_API_KEY is missing, empty, "
                    "or whitespace-only. Set TAVILY_API_KEY in the environment "
                    "or disable the module with TAVILY_ENABLED=False."
                )

        return raw

    @staticmethod
    def _read_float(name: str, default: float) -> float:
        """Read a float environment variable, falling back to *default*."""
        raw = os.environ.get(name, "")
        if not raw.strip():
            return float(default)
        try:
            return float(raw.strip())
        except ValueError:
            raise TavilyConfigError(
                f"{name} must be a valid number, got: {raw!r}"
            )

    @staticmethod
    def _read_int(name: str, default: int) -> int:
        """Read an integer environment variable, falling back to *default*."""
        raw = os.environ.get(name, "")
        if not raw.strip():
            return default
        try:
            return int(raw.strip())
        except ValueError:
            raise TavilyConfigError(
                f"{name} must be a valid integer, got: {raw!r}"
            )
"""
Tavily Custom Exceptions

This module defines the exception hierarchy for the Tavily module.
All Tavily-specific exceptions inherit from a common base class
to allow a single except clause for the entire module.

Usage:
    from data.tavily.errors import TavilyError, TavilyConfigError

    raise TavilyConfigError("Tavily API key is not set")
"""


class TavilyError(Exception):
    """Base exception for all Tavily-related errors."""


class TavilyConfigError(TavilyError):
    """Raised when Tavily configuration is missing or invalid."""


class TavilyAPIError(TavilyError):
    """Raised when the Tavily API returns an HTTP error (4xx or 5xx)."""


class TavilyTimeoutError(TavilyError):
    """Raised when a request to the Tavily API times out."""


class TavilyRateLimitError(TavilyError):
    """Raised when the Tavily API rate limit has been exceeded (HTTP 429)."""


class TavilyConnectionError(TavilyError):
    """Raised when a network connection to the Tavily API cannot be established."""


class TavilyValidationError(TavilyError):
    """Raised when the Tavily API response fails structural or content validation."""
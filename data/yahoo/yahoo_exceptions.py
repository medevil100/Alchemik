"""
Yahoo Finance Custom Exceptions

This module contains custom exceptions for the Yahoo Finance module.
"""

class YahooFinanceError(Exception):
    """Base exception for Yahoo Finance related errors."""
    pass

class InvalidSymbolError(YahooFinanceError):
    """Raised when an invalid stock symbol is provided."""
    pass

class APIError(YahooFinanceError):
    """Raised when there's an error with the Yahoo Finance API."""
    pass

class RateLimitExceededError(YahooFinanceError):
    """Raised when the rate limit for the Yahoo Finance API is exceeded."""
    pass
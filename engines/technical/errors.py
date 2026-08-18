"""Dedicated exception for insufficient input history.

Technical indicators require a minimum number of market data points before
their windows can produce a value. Instead of raising a generic ``ValueError``,
they raise :class:`InsufficientDataError` so callers can distinguish the
explicit, expected condition "history too short for the requested window"
from a genuine computation error.

``InsufficientDataError`` subclasses ``ValueError``, so existing callers that
expect ``ValueError`` remain backward compatible.
"""


class InsufficientDataError(ValueError):
    """Raised when the supplied OHLCV history is too short for an indicator."""

    def __init__(self, message: str):
        super().__init__(message)
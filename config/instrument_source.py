"""Explicit instrument-source selection for the ALCHEMIK composition root.

The production source is dynamic Yahoo discovery. Static symbols are an
explicit fallback that must never be selected implicitly.
"""

SOURCE_KIND_YAHOO = "yahoo_discovery"
SOURCE_KIND_STATIC = "static"

_DEFAULT_SOURCE_KIND = SOURCE_KIND_YAHOO


def resolve_source_kind(source_kind: str = None) -> str:
    """Return the effective source kind (defaults to dynamic Yahoo)."""
    if source_kind is None or source_kind == "":
        return _DEFAULT_SOURCE_KIND
    if source_kind not in (SOURCE_KIND_YAHOO, SOURCE_KIND_STATIC):
        raise ValueError(f"Unknown source_kind: {source_kind}")
    return source_kind


def validate_static_tickers(static_tickers):
    """Require an explicitly provided, approved list of exact Yahoo symbols."""
    if static_tickers is None:
        raise ValueError("static source requires an approved list of tickers")
    if not isinstance(static_tickers, (list, tuple)) or len(static_tickers) == 0:
        raise ValueError("static source requires a non-empty list of tickers")
    for ticker in static_tickers:
        if not isinstance(ticker, str) or ticker == "":
            raise ValueError(f"invalid ticker in static list: {ticker!r}")
    return list(static_tickers)
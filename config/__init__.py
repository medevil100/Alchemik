"""
Configuration module for ALCHEMIK.

Provides configuration classes and instrument metadata resolution.
"""
from typing import Optional, Dict, Tuple
from datetime import timedelta
from pathlib import Path
from data.models.event_enums import InstrumentType


class CacheConfig:
    """
    Configuration class for cache settings.
    
    Attributes:
        news_ttl_hours (Optional[int]): Time-to-live for news cache entries in hours.
            If not provided, defaults to 24 hours.
    """
    news_ttl_hours: Optional[int] = 24


DB_DIR: Path = Path("data") / "runtime"
DB_FILENAME: str = "alchemik_runtime.db"


class RuntimeConfig:
    """
    Configuration for RuntimeService persistent storage.
    
    Attributes:
        db_dir (Path): Directory for runtime database files.
            Defaults to data/runtime relative to project root.
        db_filename (str): SQLite database filename.
        db_path (Path): Full path to the SQLite database file (computed).
    """
    db_dir: Path = DB_DIR
    db_filename: str = DB_FILENAME

    @classmethod
    def get_db_path(cls) -> Path:
        """Return the full path to the runtime SQLite database."""
        path = cls.db_dir / cls.db_filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


# ---------------------------------------------------------------------------
# Instrument metadata configuration
# ---------------------------------------------------------------------------
# Maps a ticker symbol to its (market, instrument_type) pair.
# This is the single source of truth for instrument classification
# used by RuntimeService and MasterEngine.
#
# The key is the ticker symbol as used in Yahoo Finance.
# The value is a tuple of (market: str, instrument_type: InstrumentType).
#
# Market values follow the Kontrakt Zdarzen Rynkowych:
#   GPW, NYSE, NASDAQ, AMEX, LSE, XETRA, etc.
#
# InstrumentType values:
#   STOCK_GPW, STOCK_USA, ETF
#
# Example entries (commented out):
#   "PKN.ORLEN.WA": ("GPW", InstrumentType.STOCK_GPW),
#   "AAPL": ("NASDAQ", InstrumentType.STOCK_USA),
#   "SPY": ("NYSE", InstrumentType.ETF),
# ---------------------------------------------------------------------------
INSTRUMENT_METADATA: Dict[str, Tuple[str, InstrumentType]] = {
    # USA stocks (default mapping for common test tickers and real instruments)
    "TEST": ("NYSE", InstrumentType.STOCK_USA),
    "XYZ.WA": ("GPW", InstrumentType.STOCK_GPW),
}


def resolve_instrument_metadata(
    ticker: str,
    metadata: Optional[Dict[str, Tuple[str, InstrumentType]]] = None,
) -> Tuple[str, InstrumentType]:
    """
    Resolve market and instrument_type for a given ticker symbol.

    Uses the INSTRUMENT_METADATA dictionary as the primary source.
    Falls back to default values if ticker is not found.

    Args:
        ticker: Instrument symbol (e.g., "XYZ.WA").
        metadata: Optional custom metadata dict (for testing).

    Returns:
        Tuple of (market: str, instrument_type: InstrumentType).

    Raises:
        ValueError: If ticker is None or empty.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError(f"Invalid ticker: {ticker}")

    lookup = metadata if metadata is not None else INSTRUMENT_METADATA
    if ticker in lookup:
        return lookup[ticker]

    # Default fallback for unknown tickers
    # In production, this should be configured explicitly.
    return ("UNKNOWN", InstrumentType.STOCK_USA)
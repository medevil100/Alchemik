"""
Price Event Detector — detects price-based market events (EventFamily.PRICE).

Owned by TechnicalEngine. Accepts data in the format returned by
MarketScanner / YahooScanProvider (List[MarketData]) and creates
MarketEvent objects for each detected price event.

Implements the 10 approved price event types from the ALCHEMIK
Katalog Zdarzen Rynkowych v2.0:
  1.1 Price Surge
  1.2 Price Drop
  1.3 Gap Up
  1.4 Gap Down
  1.5 52-Week High
  1.6 52-Week Low
  1.7 All-Time High
  1.8 All-Time Low
  1.9 Level Rejection
  1.10 Psychological Level Cross
"""

from .engine import PriceDetector

__all__ = ["PriceDetector"]
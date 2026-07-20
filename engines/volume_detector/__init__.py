"""
Volume Event Detector — detects volume-based market events (EventFamily.VOLUME).

Owned by TechnicalEngine. Accepts data in the format returned by
MarketScanner / YahooScanProvider (List[MarketData]) and creates
MarketEvent objects for each detected volume event.

Implements the 5 approved volume event types from the ALCHEMIK
Katalog Zdarzen Rynkowych v2.0:
  2.1 Volume Spike
  2.2 Near-Zero Volume
  2.3 Cumulative Volume Anomaly
  2.4 High Volume on Down Days
  2.5 High Volume on Up Days
"""

from .engine import VolumeDetector

__all__ = ["VolumeDetector"]
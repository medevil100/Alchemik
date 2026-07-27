"""
ComposerEngine — merges related MarketEvents into Composite Events.

Part of ETAP 7.3.  Groups events by ticker within a configurable time
window and creates Composite Events for groups of 2+ events.

Implements invariants N10 (priority_final = max component priorities)
from the Kontrakt Zdarzen Rynkowych.
"""

from .engine import ComposerEngine

__all__ = ["ComposerEngine"]
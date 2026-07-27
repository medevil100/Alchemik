"""
Quality Assessment Engine — ETAP 7.2.

Public API for quality evaluation of MarketEvents.

Modules:
    engine — QualityEngine: assesses quality_level for a MarketEvent.

Usage:
    from engines.quality import QualityEngine
"""

from engines.quality.engine import QualityEngine

__all__ = ["QualityEngine"]
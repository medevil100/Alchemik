"""
Enum definitions for the MarketEvent system.

Defines all enumerations specified in the Kontrakt Zdarzen Rynkowych:
- SignalTiming: canonical timing role of event_type
- InstrumentType: classification of financial instruments
- EventFamily: top-level logical classification of events
- PriorityLevel: priority and quality levels (shared enum)
- EventOwner: ALCHEMIK engine responsible for the event
"""

from enum import Enum


class SignalTiming(str, Enum):
    """
    Canonical timing role of an event_type relative to a developing
    market situation.

    Each event_type has exactly one immutable SignalTiming class.
    The class is NOT a hierarchy — no ordering, weighting, or
    comparison between values is permitted.
    """

    LEADING = "leading"
    CONFIRMING = "confirming"
    WARNING = "warning"
    CONTEXT = "context"


class InstrumentType(str, Enum):
    """Type of financial instrument. Determines which detectors are triggered."""

    STOCK_GPW = "STOCK_GPW"
    STOCK_USA = "STOCK_USA"
    ETF = "ETF"


class EventFamily(str, Enum):
    """
    Event family — highest level of logical classification.
    Corresponds to the name of the detector responsible for detection.
    """

    PRICE = "PRICE"
    VOLUME = "VOLUME"
    TECHNICAL = "TECHNICAL"
    FUNDAMENTAL = "FUNDAMENTAL"
    CORPORATE = "CORPORATE"
    REGULATORY = "REGULATORY"
    MACRO = "MACRO"
    ETF = "ETF"
    DERIVATIVES = "DERIVATIVES"
    SENTIMENT = "SENTIMENT"
    SYSTEM = "SYSTEM"


class PriorityLevel(str, Enum):
    """
    Priority / quality level.
    Used for priority_raw, priority_final, and quality_level fields.
    """

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    IGNORE = "IGNORE"


class EventOwner(str, Enum):
    """
    Owner of the event — the ALCHEMIK engine responsible for detection
    and initial analysis.
    """

    TechnicalEngine = "TechnicalEngine"
    AnalystEngine = "AnalystEngine"
    NewsEngine = "NewsEngine"
    AIEngine = "AIEngine"
    Multi_Engine = "Multi-Engine"
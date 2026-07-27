"""
Configuration for the Quality Assessment engine (ETAP 7.2).

Maps priority_raw and composite event characteristics to quality_level
for each instrument type, as defined in docs/ETAP_7_PLAN.md §7.2.

All mapping rules are configurable — no hardcoded logic in the engine.
"""

from dataclasses import dataclass, field
from typing import Dict

from data.models.event_enums import InstrumentType, PriorityLevel


# ---------------------------------------------------------------------------
# Per-instrument-type mapping: priority_raw → quality_level (non-composite)
# ---------------------------------------------------------------------------
# For a single (non-composite) event, the base quality_level is the highest
# level whose map includes the event's priority_raw.
#
# Composite events are promoted according to CompositePromotion rules.

@dataclass(frozen=True)
class _InstrumentQualityProfile:
    """
    Immutable quality mapping for a single instrument type.

    non_composite_map:
        priority_raw → quality_level for single (non-composite) events.
        A PriorityLevel key maps to the quality_level it yields.

    composite_promotion: tuple of (min_component_count, min_priority, promoted_level)
        Applied in order; the first matching rule wins.
    """

    non_composite_map: Dict[PriorityLevel, PriorityLevel]
    composite_promotion: tuple = field(default_factory=tuple)

    def quality_for_non_composite(self, raw: PriorityLevel) -> PriorityLevel:
        return self.non_composite_map.get(raw, PriorityLevel.LOW)


# ---- Default profiles ----------------------------------------------------

_GPW_PROFILE = _InstrumentQualityProfile(
    non_composite_map={
        PriorityLevel.CRITICAL: PriorityLevel.HIGH,
        PriorityLevel.HIGH:     PriorityLevel.MEDIUM,
        PriorityLevel.MEDIUM:   PriorityLevel.LOW,
        PriorityLevel.LOW:      PriorityLevel.IGNORE,
    },
    composite_promotion=(
        # (min_components, min_priority_raw, promoted_quality)
        (3, PriorityLevel.CRITICAL, PriorityLevel.CRITICAL),
        (2, PriorityLevel.HIGH,     PriorityLevel.HIGH),
        (1, PriorityLevel.MEDIUM,   PriorityLevel.MEDIUM),
    ),
)

_USA_PROFILE = _InstrumentQualityProfile(
    non_composite_map={
        PriorityLevel.CRITICAL: PriorityLevel.HIGH,
        PriorityLevel.HIGH:     PriorityLevel.MEDIUM,
        PriorityLevel.MEDIUM:   PriorityLevel.LOW,
        PriorityLevel.LOW:      PriorityLevel.IGNORE,
    },
    composite_promotion=(
        (3, PriorityLevel.CRITICAL, PriorityLevel.CRITICAL),
        (2, PriorityLevel.HIGH,     PriorityLevel.HIGH),
        (1, PriorityLevel.MEDIUM,   PriorityLevel.MEDIUM),
    ),
)

_ETF_PROFILE = _InstrumentQualityProfile(
    non_composite_map={
        PriorityLevel.CRITICAL: PriorityLevel.HIGH,
        PriorityLevel.HIGH:     PriorityLevel.MEDIUM,
        PriorityLevel.MEDIUM:   PriorityLevel.LOW,
        PriorityLevel.LOW:      PriorityLevel.IGNORE,
    },
    composite_promotion=(
        (3, PriorityLevel.CRITICAL, PriorityLevel.CRITICAL),
        (2, PriorityLevel.HIGH,     PriorityLevel.HIGH),
        (1, PriorityLevel.MEDIUM,   PriorityLevel.MEDIUM),
    ),
)


@dataclass(frozen=True)
class QualityConfig:
    """
    Immutable configuration for QualityEngine.

    Profiles:
        Per-instrument-type quality assessment profiles.

    confidence_k_factor:
        Multiplier used to adjust confidence_level for composite events.
        confidence = min(1.0, base_confidence * (1 + k * (component_count - 1)))
        Default 0.05 → 5 % boost per additional component.
    """

    profiles: Dict[InstrumentType, _InstrumentQualityProfile] = field(default_factory=lambda: {
        InstrumentType.STOCK_GPW: _GPW_PROFILE,
        InstrumentType.STOCK_USA: _USA_PROFILE,
        InstrumentType.ETF:       _ETF_PROFILE,
    })

    confidence_k_factor: float = 0.05

    def profile_for(self, instrument_type: InstrumentType) -> _InstrumentQualityProfile:
        """Return the quality profile for *instrument_type*, falling back to GPW."""
        return self.profiles.get(instrument_type, _GPW_PROFILE)


# Module-level default instance.
DEFAULT_QUALITY_CONFIG = QualityConfig()
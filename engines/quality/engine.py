"""
Quality Assessment Engine — ETAP 7.2.

QualityEngine assigns a final quality_level to each MarketEvent based on its
priority_raw, composite characteristics, and instrument type. This corresponds
to Stage 5 (Ocena jakosci) in the MarketEvent lifecycle defined in
Kontrakt Zdarzen Rynkowych.

Invariants preserved:
    - event_id, ticker, detection_source, event_owner, priority_raw unchanged.
    - confidence_level may be adjusted (N5).
    - quality_level == IGNORE or LOW stops further processing (N11).
"""

from __future__ import annotations

from config.quality import DEFAULT_QUALITY_CONFIG, QualityConfig, _InstrumentQualityProfile
from data.models.event_enums import PriorityLevel
from data.models.market_event import MarketEvent


class QualityEngine:
    """
    Assigns a quality_level to a MarketEvent.

    Usage::

        engine = QualityEngine()
        event = engine.assess(event)

    The engine uses a QualityConfig to map priority_raw → quality_level
    for non-composite events and to promote composite events based on
    component count and priority_final.
    """

    def __init__(self, config: QualityConfig | None = None) -> None:
        self._config = config or DEFAULT_QUALITY_CONFIG

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def assess(self, event: MarketEvent) -> MarketEvent:
        """
        Assign quality_level to *event* and return it.

        The method calls ``event.set_quality_assessment(level)``, which
        records a HistoryEntry and sets ``event.quality_level``.

        Rules (from ETAP_7_PLAN §7.2):
            - Non-composite: mapped from priority_raw via QualityConfig.
            - Composite: base mapped + promotion rules based on
              component count and priority_final (N10: max of components).
            - Confidence is boosted for composites with 2+ components.
        """
        profile = self._config.profile_for(event.instrument_type)

        if event.is_composite:
            component_count = len(event.composite_events)
            quality = self._determine_composite_quality(
                profile, event, component_count
            )
            self._adjust_confidence(event, component_count)
        else:
            quality = profile.quality_for_non_composite(event.priority_raw)

        event.set_quality_assessment(quality)
        return event

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_composite_quality(
        profile: _InstrumentQualityProfile,
        event: MarketEvent,
        component_count: int,
    ) -> PriorityLevel:
        """
        Determine quality_level for a composite event.

        Applies composite_promotion rules in order; the first matching
        rule determines the quality. Falls back to the non-composite
        base mapping for the event's priority_raw.
        """
        base = profile.quality_for_non_composite(event.priority_raw)
        for min_count, min_priority, promoted_level in profile.composite_promotion:
            if component_count >= min_count and event.priority_final == min_priority:
                return promoted_level
        return base

    def _adjust_confidence(self, event: MarketEvent, component_count: int) -> None:
        """
        Boost confidence_level for composite events.

        Formula:
            new_conf = base_conf * (1 + k * (component_count - 1))
            clamped to [0.0, 1.0].

        This is documented in QualityConfig.confidence_k_factor.
        """
        if component_count <= 1:
            return
        k = self._config.confidence_k_factor
        event.confidence_level = min(
            1.0,
            event.confidence_level * (1.0 + k * (component_count - 1)),
        )
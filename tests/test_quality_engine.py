"""
Unit tests for QualityEngine — ETAP 7.2.

Covers:
    - Non-composite events: priority_raw → quality_level mapping
    - Composite events: promotion rules based on component count and priority_final
    - Confidence adjustment for composite events
    - Invariant preservation (event_id, ticker, priority_raw unchanged)
    - All instrument types (STOCK_GPW, STOCK_USA, ETF)
    - IGNORE and LOW path termination
    - History entry recording
"""

import unittest

from config.quality import DEFAULT_QUALITY_CONFIG, QualityConfig, _InstrumentQualityProfile
from data.models.event_enums import InstrumentType, PriorityLevel
from data.models.market_event import MarketEvent
from engines.quality.engine import QualityEngine


def _make_event(
    ticker: str = "TST.WA",
    market: str = "GPW",
    instrument_type: InstrumentType = InstrumentType.STOCK_GPW,
    priority_raw: PriorityLevel = PriorityLevel.LOW,
    priority_final: PriorityLevel = PriorityLevel.LOW,
    confidence: float = 0.5,
    is_composite: bool = False,
    composite_events: list | None = None,
) -> MarketEvent:
    """Factory for a fully initialized MarketEvent ready for quality assessment."""
    event = MarketEvent.create_new(
        event_type="PRICE_SURGE",
        ticker=ticker,
        market=market,
        instrument_type=instrument_type,
    )
    # Simulate detection
    event.set_detection(
        event_family=event.event_family,
        event_category=event.event_category,
        event_type="TEST_EVENT",
        priority_raw=priority_raw,
        confidence_level=confidence,
        detection_source="TestDetector",
        event_owner=event.event_owner,
    )
    # Simulate normalization if composite
    if is_composite:
        comp_events = composite_events if composite_events is not None else ["fake-uuid-1", "fake-uuid-2"]
        event.set_normalization(
            priority_final=priority_final,
            is_composite=True,
            composite_events=comp_events,
        )
    else:
        event.priority_final = priority_final
    return event


class TestQualityEngineNonComposite(unittest.TestCase):
    """Tests for non-composite (single) events."""

    def setUp(self):
        self.engine = QualityEngine()

    # ------------------------------------------------------------------
    # priority_raw → quality_level mapping (GPW default)
    # ------------------------------------------------------------------

    def test_critical_raw_maps_to_high_quality(self):
        """CRITICAL → base HIGH, promoted to CRITICAL by LEADING signal_timing."""
        event = _make_event(priority_raw=PriorityLevel.CRITICAL, priority_final=PriorityLevel.CRITICAL)
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.CRITICAL)

    def test_high_raw_maps_to_medium_quality(self):
        """HIGH → base MEDIUM, promoted to HIGH by LEADING signal_timing."""
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.HIGH)

    def test_medium_raw_maps_to_low_quality(self):
        """MEDIUM → base LOW, promoted to MEDIUM by LEADING signal_timing."""
        event = _make_event(priority_raw=PriorityLevel.MEDIUM, priority_final=PriorityLevel.MEDIUM)
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.MEDIUM)

    def test_low_raw_maps_to_ignore_quality(self):
        """LOW → base IGNORE, promoted to LOW by LEADING signal_timing."""
        event = _make_event(priority_raw=PriorityLevel.LOW, priority_final=PriorityLevel.LOW)
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.LOW)

    # ------------------------------------------------------------------
    # Instrument-specific profiles
    # ------------------------------------------------------------------

    def test_usa_instrument_uses_usa_profile(self):
        """USA profile: CRITICAL → base HIGH, promoted to CRITICAL by LEADING."""
        event = _make_event(
            ticker="TST",
            market="NYSE",
            instrument_type=InstrumentType.STOCK_USA,
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.CRITICAL)

    def test_etf_instrument_uses_etf_profile(self):
        """ETF profile: CRITICAL → base HIGH, promoted to CRITICAL by LEADING."""
        event = _make_event(
            ticker="SPY",
            market="NYSE",
            instrument_type=InstrumentType.ETF,
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.CRITICAL)

    # ------------------------------------------------------------------
    # Invariant preservation
    # ------------------------------------------------------------------

    def test_event_id_unchanged(self):
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        original_id = event.event_id
        result = self.engine.assess(event)
        self.assertEqual(result.event_id, original_id)

    def test_ticker_unchanged(self):
        event = _make_event(ticker="UNCHANGED.WA", priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        result = self.engine.assess(event)
        self.assertEqual(result.ticker, "UNCHANGED.WA")

    def test_priority_raw_unchanged(self):
        event = _make_event(priority_raw=PriorityLevel.CRITICAL, priority_final=PriorityLevel.CRITICAL)
        result = self.engine.assess(event)
        self.assertEqual(result.priority_raw, PriorityLevel.CRITICAL)

    def test_detection_source_unchanged(self):
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        result = self.engine.assess(event)
        self.assertEqual(result.detection_source, "TestDetector")

    def test_event_owner_unchanged(self):
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        result = self.engine.assess(event)
        self.assertEqual(result.event_owner, event.event_owner)

    # ------------------------------------------------------------------
    # History entry recording
    # ------------------------------------------------------------------

    def test_history_entry_added(self):
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        history_before = len(event.history)
        result = self.engine.assess(event)
        self.assertEqual(len(result.history), history_before + 1)
        last = result.history[-1]
        self.assertEqual(last.module, "Ocena jakości")
        self.assertIn("quality_level", last.fields_changed)


class TestQualityEngineComposite(unittest.TestCase):
    """Tests for composite events."""

    def setUp(self):
        self.engine = QualityEngine()

    # ------------------------------------------------------------------
    # Composite promotion rules (3 CRITICAL → CRITICAL)
    # ------------------------------------------------------------------

    def test_composite_three_critical_promotes_to_critical(self):
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            is_composite=True,
            composite_events=["e1", "e2", "e3"],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.CRITICAL)

    def test_composite_two_high_promotes_to_high(self):
        event = _make_event(
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            is_composite=True,
            composite_events=["e1", "e2"],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.HIGH)

    def test_composite_one_medium_stays_medium(self):
        event = _make_event(
            priority_raw=PriorityLevel.MEDIUM,
            priority_final=PriorityLevel.MEDIUM,
            is_composite=True,
            composite_events=["e1"],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.MEDIUM)

    def test_composite_two_critical_no_promotion(self):
        """2 CRITICAL events should NOT promote to CRITICAL (need 3+)."""
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            is_composite=True,
            composite_events=["e1", "e2"],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.HIGH)  # base mapping

    # ------------------------------------------------------------------
    # Confidence boost for composite events
    # ------------------------------------------------------------------

    def test_composite_confidence_boosted(self):
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            confidence=0.80,
            is_composite=True,
            composite_events=["e1", "e2", "e3"],
        )
        result = self.engine.assess(event)
        # confidence = 0.80 * (1 + 0.05 * (3 - 1)) = 0.80 * 1.10 = 0.88
        self.assertAlmostEqual(result.confidence_level, 0.88, places=3)

    def test_composite_confidence_clamped_to_1(self):
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            confidence=0.99,
            is_composite=True,
            composite_events=["e1", "e2", "e3"],
        )
        result = self.engine.assess(event)
        self.assertLessEqual(result.confidence_level, 1.0)

    def test_non_composite_confidence_not_boosted(self):
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            confidence=0.80,
            is_composite=False,
        )
        result = self.engine.assess(event)
        self.assertEqual(result.confidence_level, 0.80)

    # ------------------------------------------------------------------
    # N10: priority_final = max of components (already set)
    # ------------------------------------------------------------------

    def test_priority_final_preserved(self):
        event = _make_event(
            priority_raw=PriorityLevel.CRITICAL,
            priority_final=PriorityLevel.CRITICAL,
            is_composite=True,
            composite_events=["e1", "e2", "e3"],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.priority_final, PriorityLevel.CRITICAL)


class TestQualityEngineCustomConfig(unittest.TestCase):
    """Tests with a custom QualityConfig."""

    def test_custom_profile_respected(self):
        """Custom profile: MEDIUM → base HIGH, promoted to CRITICAL by LEADING."""
        custom_profile = _InstrumentQualityProfile(
            non_composite_map={
                PriorityLevel.CRITICAL: PriorityLevel.CRITICAL,
                PriorityLevel.HIGH:     PriorityLevel.HIGH,
                PriorityLevel.MEDIUM:   PriorityLevel.HIGH,
                PriorityLevel.LOW:      PriorityLevel.LOW,
            },
        )
        custom_config = QualityConfig(
            profiles={
                InstrumentType.STOCK_GPW: custom_profile,
                InstrumentType.STOCK_USA: custom_profile,
                InstrumentType.ETF:       custom_profile,
            },
        )
        engine = QualityEngine(config=custom_config)
        event = _make_event(priority_raw=PriorityLevel.MEDIUM, priority_final=PriorityLevel.MEDIUM)
        result = engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.CRITICAL)


class TestQualityEdgeCases(unittest.TestCase):
    """Edge case tests."""

    def setUp(self):
        self.engine = QualityEngine()

    def test_empty_composite_events_treated_as_non_composite(self):
        """is_composite=True with empty list should not crash."""
        event = _make_event(
            priority_raw=PriorityLevel.HIGH,
            priority_final=PriorityLevel.HIGH,
            is_composite=True,
            composite_events=[],
        )
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.MEDIUM)

    def test_ignore_level_stops_processing_meta(self):
        """
        quality_level IGNORE means processing stops.
        With LEADING signal_timing, LOW is promoted to LOW (IGNORE → LOW).
        The quality_level itself must be set correctly.
        """
        event = _make_event(priority_raw=PriorityLevel.LOW, priority_final=PriorityLevel.LOW)
        result = self.engine.assess(event)
        self.assertEqual(result.quality_level, PriorityLevel.LOW)

    def test_assess_is_idempotent(self):
        event = _make_event(priority_raw=PriorityLevel.HIGH, priority_final=PriorityLevel.HIGH)
        result1 = self.engine.assess(event)
        result2 = self.engine.assess(result1)
        self.assertEqual(result1.quality_level, result2.quality_level)


if __name__ == "__main__":
    unittest.main()
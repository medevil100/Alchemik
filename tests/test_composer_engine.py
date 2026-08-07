"""
Unit tests for ComposerEngine (ETAP 7.3).

Tests cover:
  - Correct creation of Composite Events for same-ticker, close-timestamp events
  - Grouping by ticker (no cross-ticker merging)
  - Time window enforcement (events outside the window are NOT merged)
  - priority_final = max(component priorities) — invariant N10
  - Component event IDs preserved in composite_events
  - Input events never modified
  - Edge cases: empty list, single event, events outside window,
    mixed tickers, many events, single-ticker multiple clusters
  - Determinism: same input → same result structure
  - is_composite flag and detection_source (N2) correctly set
  - A. Market-technical family compatibility
  - B. Fundamental/informational family compatibility
  - C. SYSTEM/SENTIMENT/MACRO isolation
  - D. Forbidden combinations
  - E. Mixed groups — maximal compatible subgroups
  - F. Symmetry of compatibility matrix
  - G. Deterministic subgroup formation
  - H. Input immutability (expanded)
  - I. CompositeEvent model actually used (import, instantiation, validation)
  - J. max_composite_events bounds components per Composite Event
  - K. max_composite_events boundary tests (limit 3)
"""

import unittest
from copy import deepcopy
from datetime import datetime, timezone, timedelta

from config.composer import ComposerConfig, set_composer_config
from data.models.composite_event import CompositeEvent
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    InstrumentType,
    PriorityLevel,
)
from data.models.market_event import MarketEvent
from engines.composer.engine import ComposerEngine, _are_compatible, _COMPATIBILITY


# ---------------------------------------------------------------------------
# Helpers — create minimal MarketEvents for testing
# ---------------------------------------------------------------------------

def _make_event(
    ticker: str = "XYZ.WA",
    market: str = "GPW",
    instrument_type: InstrumentType = InstrumentType.STOCK_GPW,
    timestamp: datetime | None = None,
    event_type: str = "PRICE_SURGE",
    event_family: EventFamily = EventFamily.PRICE,
    priority_raw: PriorityLevel = PriorityLevel.HIGH,
    confidence_level: float = 0.8,
) -> MarketEvent:
    """Create a fully-detected MarketEvent suitable for composer input."""
    if timestamp is None:
        timestamp = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)

    evt = MarketEvent.create_new(
        ticker=ticker,
        market=market,
        instrument_type=instrument_type,
        event_type=event_type,
        timestamp_utc=timestamp,
    )
    evt.set_detection(
        event_family=event_family,
        event_category="TestCategory",
        event_type=event_type,
        priority_raw=priority_raw,
        confidence_level=confidence_level,
        detection_source="TestDetector",
        event_owner=EventOwner.TechnicalEngine,
    )
    return evt


_base_time = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)


# ===========================================================================
# Original basic tests
# ===========================================================================

class TestComposerEngineBasic(unittest.TestCase):
    """Basic correctness tests."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_empty_input_returns_empty(self):
        result = self.engine.compose([])
        self.assertEqual(result, [])

    def test_single_event_returns_unchanged(self):
        evt = _make_event(timestamp=_base_time)
        result = self.engine.compose([evt])
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].is_composite)

    def test_two_same_ticker_within_window_creates_composite(self):
        """2 events, same ticker, same timestamp → composite created."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=30))

        result = self.engine.compose([evt1, evt2])

        # Original 2 + 1 composite = 3
        self.assertEqual(len(result), 3)

        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        ce = composites[0]
        self.assertCountEqual(ce.composite_events, [evt1.event_id, evt2.event_id])

    def test_two_events_outside_window_no_composite(self):
        """2 events, same ticker but beyond the time window → no composite."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=90))

        result = self.engine.compose([evt1, evt2])
        self.assertEqual(len(result), 2)
        self.assertFalse(any(e.is_composite for e in result))

    def test_two_events_boundary_in_window(self):
        """Exactly at the window boundary (60s) should be merged."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=60))

        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertCountEqual(composites[0].composite_events,
                              [evt1.event_id, evt2.event_id])

    def test_two_events_boundary_outside_window(self):
        """61 seconds apart should NOT be merged with default window."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=61))

        result = self.engine.compose([evt1, evt2])
        self.assertEqual(len(result), 2)
        self.assertFalse(any(e.is_composite for e in result))


class TestComposerEngineTickerGrouping(unittest.TestCase):
    """Events for different tickers must never be merged."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_different_tickers_same_timestamp_no_merge(self):
        evt_a = _make_event(ticker="AAA.WA", timestamp=_base_time)
        evt_b = _make_event(ticker="BBB.WA", timestamp=_base_time)

        result = self.engine.compose([evt_a, evt_b])
        self.assertEqual(len(result), 2)
        self.assertFalse(any(e.is_composite for e in result))

    def test_mixed_tickers_clusters(self):
        """One ticker forms a cluster, the other remains alone."""
        a1 = _make_event(ticker="AAA.WA", timestamp=_base_time)
        a2 = _make_event(ticker="AAA.WA", timestamp=_base_time + timedelta(seconds=10))
        b1 = _make_event(ticker="BBB.WA", timestamp=_base_time)

        result = self.engine.compose([a1, a2, b1])
        # a1 + a2 → composite, b1 unchanged, a1 & a2 unchanged
        self.assertEqual(len(result), 4)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        ce = composites[0]
        self.assertCountEqual(ce.composite_events, [a1.event_id, a2.event_id])


class TestComposerEnginePriorityAndConfidence(unittest.TestCase):
    """Test N10 (priority_final = max) and confidence averaging."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_priority_final_is_max_low_high(self):
        evt1 = _make_event(priority_raw=PriorityLevel.LOW, timestamp=_base_time)
        evt2 = _make_event(priority_raw=PriorityLevel.HIGH,
                           timestamp=_base_time + timedelta(seconds=10))

        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertEqual(ce.priority_final, PriorityLevel.HIGH)

    def test_priority_final_is_max_critical(self):
        evt1 = _make_event(priority_raw=PriorityLevel.MEDIUM, timestamp=_base_time)
        evt2 = _make_event(priority_raw=PriorityLevel.CRITICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(priority_raw=PriorityLevel.LOW,
                           timestamp=_base_time + timedelta(seconds=20))

        result = self.engine.compose([evt1, evt2, evt3])
        ce = next(e for e in result if e.is_composite)
        self.assertEqual(ce.priority_final, PriorityLevel.CRITICAL)

    def test_confidence_is_average(self):
        evt1 = _make_event(confidence_level=0.5, timestamp=_base_time)
        evt2 = _make_event(confidence_level=0.9, timestamp=_base_time + timedelta(seconds=10))

        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertAlmostEqual(ce.confidence_level, 0.7, places=6)

    def test_confidence_three_events(self):
        evt1 = _make_event(confidence_level=1.0, timestamp=_base_time)
        evt2 = _make_event(confidence_level=0.0,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(confidence_level=0.5,
                           timestamp=_base_time + timedelta(seconds=20))

        result = self.engine.compose([evt1, evt2, evt3])
        ce = next(e for e in result if e.is_composite)
        self.assertAlmostEqual(ce.confidence_level, 0.5, places=6)


class TestComposerEngineInputImmutability(unittest.TestCase):
    """Input MarketEvents must never be modified."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_input_events_unchanged(self):
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=10))

        orig1 = deepcopy(evt1)
        orig2 = deepcopy(evt2)

        self.engine.compose([evt1, evt2])

        self.assertEqual(evt1.event_id, orig1.event_id)
        self.assertEqual(evt1.ticker, orig1.ticker)
        self.assertEqual(evt1.is_composite, orig1.is_composite)
        self.assertEqual(evt1.priority_raw, orig1.priority_raw)
        self.assertEqual(evt1.priority_final, orig1.priority_final)
        self.assertEqual(evt1.confidence_level, orig1.confidence_level)
        self.assertEqual(evt1.composite_events, orig1.composite_events)

        self.assertEqual(evt2.event_id, orig2.event_id)
        self.assertEqual(evt2.priority_raw, orig2.priority_raw)


class TestCompositeEventMetadata(unittest.TestCase):
    """Verify metadata fields on the created Composite Event."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_is_composite_true(self):
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=5))
        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertTrue(ce.is_composite)

    def test_composite_events_list_contains_ids(self):
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=5))
        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertIsInstance(ce.composite_events, list)
        self.assertEqual(len(ce.composite_events), 2)
        self.assertIn(evt1.event_id, ce.composite_events)
        self.assertIn(evt2.event_id, ce.composite_events)

    def test_detection_source_empty_for_composite(self):
        """N2: detection_source must be empty for Composite Events."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=5))
        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertEqual(ce.detection_source, "")

    def test_event_family_from_components(self):
        """Composite event_family should be the most common among components."""
        evt1 = _make_event(event_family=EventFamily.VOLUME, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=5))
        evt3 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))

        result = self.engine.compose([evt1, evt2, evt3])
        ce = next(e for e in result if e.is_composite)
        self.assertEqual(ce.event_family, EventFamily.VOLUME)

    def test_ticker_market_instrument_preserved(self):
        evt1 = _make_event(ticker="XYZ.WA", market="GPW",
                           instrument_type=InstrumentType.STOCK_GPW,
                           timestamp=_base_time)
        evt2 = _make_event(ticker="XYZ.WA", market="GPW",
                           instrument_type=InstrumentType.STOCK_GPW,
                           timestamp=_base_time + timedelta(seconds=5))

        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)
        self.assertEqual(ce.ticker, "XYZ.WA")
        self.assertEqual(ce.market, "GPW")
        self.assertEqual(ce.instrument_type, InstrumentType.STOCK_GPW)


class TestComposerEngineEdgeCases(unittest.TestCase):
    """Miscellaneous edge case tests."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_many_events_single_cluster(self):
        """10 events within the window → 1 composite (default limit is 10)."""
        events = [
            _make_event(timestamp=_base_time + timedelta(seconds=i * 5))
            for i in range(10)
        ]
        result = self.engine.compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertEqual(len(composites[0].composite_events), 10)

    def test_multiple_clusters_same_ticker(self):
        """2 clusters, each with 2 events → 2 composites."""
        t0 = _base_time
        t1 = t0 + timedelta(seconds=200)  # well outside the 60 s window

        evt_a1 = _make_event(timestamp=t0)
        evt_a2 = _make_event(timestamp=t0 + timedelta(seconds=10))
        evt_b1 = _make_event(timestamp=t1)
        evt_b2 = _make_event(timestamp=t1 + timedelta(seconds=10))

        result = self.engine.compose([evt_a1, evt_a2, evt_b1, evt_b2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)

        # Each composite should have exactly 2 components
        for ce in composites:
            self.assertEqual(len(ce.composite_events), 2)

    def test_original_events_still_in_result(self):
        """Non-composite original events are returned alongside composites."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=10))

        result = self.engine.compose([evt1, evt2])
        orig = [e for e in result if not e.is_composite]
        self.assertIn(evt1, orig)
        self.assertIn(evt2, orig)

    def test_deterministic_output(self):
        """Same input twice → same structure (same number of composites)."""
        events = [
            _make_event(timestamp=_base_time + timedelta(seconds=i * 10))
            for i in range(5)
        ]
        result1 = self.engine.compose(events)
        result2 = self.engine.compose(events)

        self.assertEqual(len(result1), len(result2))
        self.assertEqual(
            [e.is_composite for e in result1],
            [e.is_composite for e in result2],
        )

    def test_timestamp_utc_on_composite_is_recent(self):
        """Composite event timestamp should be close to 'now'."""
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=5))

        before = datetime.now(timezone.utc)
        result = self.engine.compose([evt1, evt2])
        after = datetime.now(timezone.utc)

        ce = next(e for e in result if e.is_composite)
        self.assertLessEqual(before, ce.timestamp_utc)
        self.assertLessEqual(ce.timestamp_utc, after)

    def test_configurable_time_window(self):
        """Custom time_window_seconds should be respected."""
        config = ComposerConfig(time_window_seconds=30)
        set_composer_config(config)
        try:
            engine = ComposerEngine()
            evt1 = _make_event(timestamp=_base_time)
            # 31s apart — outside custom 30s window
            evt2 = _make_event(timestamp=_base_time + timedelta(seconds=31))

            result = engine.compose([evt1, evt2])
            self.assertFalse(any(e.is_composite for e in result))
        finally:
            set_composer_config(ComposerConfig())


# ===========================================================================
# A. Market-technical family compatibility
# ===========================================================================

class TestFamilyCompatibilityMarketTechnical(unittest.TestCase):
    """PRICE, VOLUME, TECHNICAL should be mutually compatible."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_price_plus_volume_merged(self):
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertCountEqual(composites[0].composite_events,
                              [evt1.event_id, evt2.event_id])

    def test_price_plus_momentum_manifests_as_technical(self):
        """MOMENTUM is a subtype of TECHNICAL — uses TECHNICAL family."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_price_plus_volatility_manifests_as_technical(self):
        """VOLATILITY is a subtype of TECHNICAL."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_price_plus_technical_merged(self):
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_price_plus_gap_is_price(self):
        """GAP manifests as PRICE family."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_price_plus_breakout_is_technical(self):
        """BREAKOUT manifests as TECHNICAL family."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_volume_plus_liquidity_via_volume(self):
        """LIQUIDITY does not exist as family; volume-to-volume test."""
        evt1 = _make_event(event_family=EventFamily.VOLUME, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_momentum_plus_technical_merged(self):
        """TECHNICAL + TECHNICAL (same family)."""
        evt1 = _make_event(event_family=EventFamily.TECHNICAL, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_three_way_technical_group(self):
        """PRICE + VOLUME + TECHNICAL all mutually compatible."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=20))
        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertEqual(len(composites[0].composite_events), 3)


# ===========================================================================
# B. Fundamental/informational family compatibility
# ===========================================================================

class TestFamilyCompatibilityFundamental(unittest.TestCase):
    """FUNDAMENTAL, CORPORATE, REGULATORY group tests."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_corporate_plus_corporate_merged(self):
        evt1 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_news_not_a_family_no_special_handling(self):
        """NEWS does not exist as EventFamily — no special mapping."""
        evt1 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_corporate_plus_news_not_applicable(self):
        """CORPORATE + SENTIMENT should NOT be merged (different groups)."""
        evt1 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0,
                         "CORPORATE + SENTIMENT should not be merged")

    def test_fundamental_plus_corporate_merged(self):
        evt1 = _make_event(event_family=EventFamily.FUNDAMENTAL,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_corporate_plus_regulatory_merged(self):
        evt1 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.REGULATORY,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_fundamental_plus_regulatory_merged(self):
        evt1 = _make_event(event_family=EventFamily.FUNDAMENTAL,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.REGULATORY,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)


# ===========================================================================
# C. SYSTEM/SENTIMENT/MACRO isolation
# ===========================================================================

class TestFamilyCompatibilityIsolation(unittest.TestCase):
    """Families that can only combine with themselves."""

    def setUp(self):
        self.engine = ComposerEngine()

    # SYSTEM isolation
    def test_system_plus_system_merged(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SYSTEM,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_system_plus_price_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_system_plus_volume_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_system_plus_corporate_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_system_plus_sentiment_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    # MACRO isolation
    def test_macro_plus_macro_merged(self):
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.MACRO,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_macro_plus_price_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    # SENTIMENT isolation
    def test_sentiment_plus_price_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)


# ===========================================================================
# D. Forbidden combinations
# ===========================================================================

class TestForbiddenCombinations(unittest.TestCase):
    """Explicitly test that disallowed combinations are NOT merged."""

    def setUp(self):
        self.engine = ComposerEngine()

    def _assert_not_merged(self, family_a, family_b):
        evt1 = _make_event(event_family=family_a, timestamp=_base_time)
        evt2 = _make_event(event_family=family_b,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0,
                         f"{family_a.value} + {family_b.value} should NOT be merged")

    def test_price_plus_corporate_not_merged(self):
        self._assert_not_merged(EventFamily.PRICE, EventFamily.CORPORATE)

    def test_price_plus_sentiment_not_merged(self):
        self._assert_not_merged(EventFamily.PRICE, EventFamily.SENTIMENT)

    def test_volume_plus_corporate_not_merged(self):
        self._assert_not_merged(EventFamily.VOLUME, EventFamily.CORPORATE)

    def test_technical_plus_sentiment_not_merged(self):
        self._assert_not_merged(EventFamily.TECHNICAL, EventFamily.SENTIMENT)

    def test_corporate_plus_system_not_merged(self):
        self._assert_not_merged(EventFamily.CORPORATE, EventFamily.SYSTEM)

    def test_sentiment_plus_system_not_merged(self):
        self._assert_not_merged(EventFamily.SENTIMENT, EventFamily.SYSTEM)

    def test_price_plus_fundamental_not_merged(self):
        self._assert_not_merged(EventFamily.PRICE, EventFamily.FUNDAMENTAL)

    def test_technical_plus_corporate_not_merged(self):
        self._assert_not_merged(EventFamily.TECHNICAL, EventFamily.CORPORATE)

    def test_macro_plus_volume_not_merged(self):
        self._assert_not_merged(EventFamily.MACRO, EventFamily.VOLUME)

    def test_macro_plus_corporate_not_merged(self):
        self._assert_not_merged(EventFamily.MACRO, EventFamily.CORPORATE)


# ===========================================================================
# E. Mixed groups — maximal compatible subgroups
# ===========================================================================

class TestMixedGroupsMaximalSubgroups(unittest.TestCase):
    """Test that clusters with incompatible families are split correctly."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_price_volume_plus_corporate(self):
        """PRICE + VOLUME + CORPORATE → composite(PRICE+VOLUME) + corporate."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=20))

        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]

        self.assertEqual(len(composites), 1,
                         "Should have exactly 1 composite (PRICE+VOLUME)")
        ce = composites[0]
        self.assertCountEqual(ce.composite_events, [evt1.event_id, evt2.event_id])

        # CORPORATE should remain as original (non-composite)
        non_composites = [e for e in result if not e.is_composite]
        corporate_events = [e for e in non_composites
                            if e.event_family == EventFamily.CORPORATE]
        self.assertEqual(len(corporate_events), 1)
        self.assertEqual(corporate_events[0].event_id, evt3.event_id)

    def test_price_volume_corporate_fundamental(self):
        """PRICE+VOLUME+CORPORATE+FUNDAMENTAL → 2 composites."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=20))
        evt4 = _make_event(event_family=EventFamily.FUNDAMENTAL,
                           timestamp=_base_time + timedelta(seconds=30))

        result = self.engine.compose([evt1, evt2, evt3, evt4])
        composites = [e for e in result if e.is_composite]

        self.assertEqual(len(composites), 2,
                         "Should have 2 composites: PRICE+VOLUME and CORPORATE+FUNDAMENTAL")

        # Find each composite
        price_volume_ce = None
        corporate_fund_ce = None
        for ce in composites:
            component_families = set()
            for eid in ce.composite_events:
                for e in [evt1, evt2, evt3, evt4]:
                    if e.event_id == eid:
                        component_families.add(e.event_family)
            if EventFamily.PRICE in component_families:
                price_volume_ce = ce
            if EventFamily.CORPORATE in component_families:
                corporate_fund_ce = ce

        self.assertIsNotNone(price_volume_ce)
        self.assertIsNotNone(corporate_fund_ce)
        self.assertEqual(len(price_volume_ce.composite_events), 2)
        self.assertEqual(len(corporate_fund_ce.composite_events), 2)

        # No event duplicated
        all_comp_ids = []
        for ce in composites:
            all_comp_ids.extend(ce.composite_events)
        self.assertEqual(len(all_comp_ids), len(set(all_comp_ids)),
                         "No event ID should appear in more than one composite")

    def test_incompatible_subgroup_no_composite_created(self):
        """When a subgroup has only 1 event, no composite is created."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=10))

        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)
        self.assertEqual(len(result), 2)  # both originals returned

    def test_no_event_duplicated_across_subgroups(self):
        """Each event belongs to at most one Composite Event."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=20))
        evt4 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=30))

        result = self.engine.compose([evt1, evt2, evt3, evt4])
        composites = [e for e in result if e.is_composite]
        all_ids: set = set()
        for ce in composites:
            for cid in ce.composite_events:
                self.assertNotIn(cid, all_ids,
                                 f"Event {cid} duplicated across composites")
                all_ids.add(cid)

    def test_events_not_assignable_remain_unchanged(self):
        """Events that cannot be assigned to any group >= 2 remain."""
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=20))

        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0,
                         "No pair is compatible — all 3 are incompatible")
        self.assertEqual(len(result), 3)  # all originals returned unchanged


# ===========================================================================
# F. Symmetry of compatibility matrix
# ===========================================================================

class TestCompatibilityMatrixSymmetry(unittest.TestCase):
    """The compatibility matrix must be symmetric."""

    def test_matrix_is_symmetric(self):
        all_families = list(EventFamily)
        for family_a in all_families:
            for family_b in all_families:
                a_to_b = _are_compatible(family_a, family_b)
                b_to_a = _are_compatible(family_b, family_a)
                self.assertEqual(
                    a_to_b, b_to_a,
                    f"Asymmetry: {family_a.value} -> {family_b.value} = {a_to_b}, "
                    f"but {family_b.value} -> {family_a.value} = {b_to_a}"
                )

    def test_all_families_have_entries(self):
        """Every EventFamily must have an entry in the matrix."""
        for family in EventFamily:
            self.assertIn(family, _COMPATIBILITY,
                          f"Missing matrix entry for {family.value}")

    def test_matrix_only_contains_existing_families(self):
        """No non-existent family values in the matrix."""
        all_families = set(EventFamily)
        for family, compat in _COMPATIBILITY.items():
            self.assertIn(family, all_families)
            for cf in compat:
                self.assertIn(cf, all_families,
                              f"Unknown family {cf} in matrix for {family.value}")

    def test_every_family_compatible_with_itself(self):
        """Each family must be compatible with itself."""
        for family in EventFamily:
            self.assertTrue(
                _are_compatible(family, family),
                f"{family.value} must be compatible with itself"
            )


# ===========================================================================
# G. Deterministic subgroup formation
# ===========================================================================

class TestDeterministicSubgroups(unittest.TestCase):
    """Result must not depend on input order."""

    def setUp(self):
        self.engine = ComposerEngine()

    def _make_mixed_cluster(self, order_fn):
        """Create PRICE, VOLUME, CORPORATE, FUNDAMENTAL events."""
        base = _base_time
        events = [
            _make_event(event_family=EventFamily.PRICE,
                        timestamp=base + timedelta(seconds=0)),
            _make_event(event_family=EventFamily.VOLUME,
                        timestamp=base + timedelta(seconds=10)),
            _make_event(event_family=EventFamily.CORPORATE,
                        timestamp=base + timedelta(seconds=15)),
            _make_event(event_family=EventFamily.FUNDAMENTAL,
                        timestamp=base + timedelta(seconds=25)),
        ]
        return order_fn(events)

    def test_chronological_order(self):
        events = self._make_mixed_cluster(lambda e: e)
        result = self.engine.compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)

    def test_reverse_order(self):
        events = self._make_mixed_cluster(lambda e: list(reversed(e)))
        result = self.engine.compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)

    def test_random_shuffle(self):
        """Shuffled input must produce same number of composites."""
        # Deterministic "shuffle": interleave
        original = self._make_mixed_cluster(lambda e: e)
        shuffled = [original[0], original[2], original[1], original[3]]

        result_orig = self.engine.compose(original)
        result_shuf = self.engine.compose(shuffled)

        composites_orig = [e for e in result_orig if e.is_composite]
        composites_shuf = [e for e in result_shuf if e.is_composite]

        self.assertEqual(len(composites_orig), len(composites_shuf))

        # Component IDs should be the same (ignoring new UUIDs)
        orig_ids = sorted(
            [frozenset(c.composite_events) for c in composites_orig],
            key=lambda s: sorted(s)[0],
        )
        shuf_ids = sorted(
            [frozenset(c.composite_events) for c in composites_shuf],
            key=lambda s: sorted(s)[0],
        )
        self.assertEqual(orig_ids, shuf_ids)

    def test_same_ticker_families_produce_consistent_output(self):
        """Same events twice must produce equivalent composites in structure."""
        events = []
        base = _base_time
        for i, family in enumerate([EventFamily.PRICE, EventFamily.VOLUME,
                                     EventFamily.TECHNICAL, EventFamily.CORPORATE]):
            events.append(_make_event(
                event_family=family,
                timestamp=base + timedelta(seconds=i * 10),
            ))

        result1 = self.engine.compose(events)
        result2 = self.engine.compose(events)

        comp1 = sorted(
            [frozenset(c.composite_events) for c in result1 if c.is_composite],
            key=lambda s: sorted(s)[0],
        )
        comp2 = sorted(
            [frozenset(c.composite_events) for c in result2 if c.is_composite],
            key=lambda s: sorted(s)[0],
        )
        self.assertEqual(comp1, comp2)


# ===========================================================================
# H. Input immutability (extended)
# ===========================================================================

class TestInputImmutabilityExtended(unittest.TestCase):
    """Extended tests for input immutability."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_input_list_not_modified(self):
        events = [
            _make_event(event_family=EventFamily.PRICE, timestamp=_base_time),
            _make_event(event_family=EventFamily.VOLUME,
                        timestamp=_base_time + timedelta(seconds=10)),
            _make_event(event_family=EventFamily.CORPORATE,
                        timestamp=_base_time + timedelta(seconds=20)),
        ]
        original_len = len(events)
        original_ids = [e.event_id for e in events]
        original_families = [e.event_family for e in events]

        self.engine.compose(events)

        self.assertEqual(len(events), original_len)
        self.assertEqual([e.event_id for e in events], original_ids)
        self.assertEqual([e.event_family for e in events], original_families)

    def test_input_event_ids_never_modified(self):
        events = [
            _make_event(event_family=EventFamily.PRICE, timestamp=_base_time),
            _make_event(event_family=EventFamily.VOLUME,
                        timestamp=_base_time + timedelta(seconds=10)),
        ]
        event_ids_before = {e.event_id for e in events}

        result = self.engine.compose(events)
        event_ids_after_input = {e.event_id for e in events}

        self.assertEqual(event_ids_before, event_ids_after_input)

        # Also check that component IDs in composites reference original events
        for ce in result:
            if ce.is_composite:
                for cid in ce.composite_events:
                    self.assertIn(cid, event_ids_before,
                                  f"Composite references unknown event {cid}")

    def test_input_event_families_unchanged(self):
        events = [
            _make_event(event_family=EventFamily.PRICE, timestamp=_base_time),
            _make_event(event_family=EventFamily.VOLUME,
                        timestamp=_base_time + timedelta(seconds=10)),
        ]
        families_before = [e.event_family for e in events]

        self.engine.compose(events)

        families_after = [e.event_family for e in events]
        self.assertEqual(families_before, families_after)


# ===========================================================================
# I. CompositeEvent model actually used by ComposerEngine
# ===========================================================================

class TestCompositeEventModelIntegration(unittest.TestCase):
    """Verify that ComposerEngine actually uses the CompositeEvent model."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_import_present(self):
        """CompositeEvent is importable and used by the engine module."""
        import engines.composer.engine as engine_module
        self.assertTrue(hasattr(engine_module, "CompositeEvent"))
        self.assertIs(engine_module.CompositeEvent, CompositeEvent)

    def test_composite_event_instantiated_during_compose(self):
        """
        The engine must instantiate CompositeEvent during compose().
        We verify this by checking that invalid component data
        (fewer than 2 events) is rejected by CompositeEvent validation
        before it can become a MarketEvent.
        """
        # 2 events → should produce a valid composite
        evt1 = _make_event(timestamp=_base_time)
        evt2 = _make_event(timestamp=_base_time + timedelta(seconds=5))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        ce = composites[0]
        self.assertEqual(len(ce.composite_events), 2)
        self.assertIn(evt1.event_id, ce.composite_events)
        self.assertIn(evt2.event_id, ce.composite_events)

    def test_composite_event_validation_prevents_invalid_market_event(self):
        """
        The _create_composite_event helper passes through
        CompositeEvent.create() which validates min 2 components.
        The engine's _build_composites_from_subgroup enforces a
        minimum limit of 2, so even with config max_composite_events=1,
        each chunk still gets 2 events (1 clamped to 2).
        With 2 events total, we get 1 Composite Event (both events
        in one chunk), correctly validated by CompositeEvent.create().
        """
        config = ComposerConfig(
            time_window_seconds=3600,
            max_composite_events=1,  # clamped to 2 internally
        )
        set_composer_config(config)
        try:
            engine = ComposerEngine()
            evt1 = _make_event(timestamp=_base_time)
            evt2 = _make_event(timestamp=_base_time + timedelta(seconds=10))
            result = engine.compose([evt1, evt2])
            composites = [e for e in result if e.is_composite]
            # limit 1 → clamped to 2, both events form one valid composite
            self.assertEqual(len(composites), 1,
                             "Limit clamped to 2, 2 events → 1 composite")
            self.assertEqual(len(composites[0].composite_events), 2)
        finally:
            set_composer_config(ComposerConfig())

    def test_result_market_event_built_from_composite_event(self):
        """
        The returned MarketEvent's fields must match what
        CompositeEvent.create() would produce.
        """
        evt1 = _make_event(
            event_family=EventFamily.PRICE,
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.9,
            timestamp=_base_time,
        )
        evt2 = _make_event(
            event_family=EventFamily.VOLUME,
            priority_raw=PriorityLevel.CRITICAL,
            confidence_level=0.5,
            timestamp=_base_time + timedelta(seconds=5),
        )

        result = self.engine.compose([evt1, evt2])
        ce = next(e for e in result if e.is_composite)

        # Build reference CompositeEvent
        expected = CompositeEvent.create(
            ticker="XYZ.WA",
            component_event_ids=[evt1.event_id, evt2.event_id],
            priority_final=PriorityLevel.CRITICAL,
            event_family=EventFamily.PRICE,
            confidence_level=0.7,
            timestamp_utc=ce.timestamp_utc,
        )

        self.assertEqual(ce.is_composite, expected.is_composite)
        self.assertCountEqual(ce.composite_events, list(expected.component_event_ids))
        self.assertEqual(ce.priority_final, expected.priority_final)
        self.assertAlmostEqual(ce.confidence_level, expected.confidence_level, places=6)

    def test_public_api_unchanged(self):
        """compose(events) -> list[MarketEvent] signature preserved."""
        import inspect
        sig = inspect.signature(ComposerEngine.compose)
        params = list(sig.parameters.keys())
        self.assertIn("events", params)
        result_annotation = sig.return_annotation
        self.assertIsNotNone(result_annotation)


# ===========================================================================
# J. max_composite_events — bounds components per Composite Event
# ===========================================================================

class TestMaxCompositeEventsBoundary(unittest.TestCase):
    """
    Boundary tests for max_composite_events (limit = 3 components per
    Composite Event).  Verifies correct splitting, no event loss,
    no single-element composites, determinism, and that the config
    field does NOT limit the number of Composite Events created.
    """

    def _setup_config(self, limit: int):
        config = ComposerConfig(
            time_window_seconds=3600,  # all events in one window
            max_composite_events=limit,
        )
        set_composer_config(config)
        return config

    def tearDown(self):
        set_composer_config(ComposerConfig())

    def _make_events(self, count: int, family: EventFamily = EventFamily.PRICE):
        return [
            _make_event(
                event_family=family,
                timestamp=_base_time + timedelta(seconds=i),
            )
            for i in range(count)
        ]

    # --- limit = 3 boundary tests ---

    def test_limit3_zero_events(self):
        self._setup_config(3)
        result = ComposerEngine().compose([])
        self.assertEqual(len(result), 0)

    def test_limit3_one_event(self):
        self._setup_config(3)
        events = self._make_events(1)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)
        self.assertEqual(len(result), 1)

    def test_limit3_two_events(self):
        self._setup_config(3)
        events = self._make_events(2)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertEqual(len(composites[0].composite_events), 2)

    def test_limit3_three_events(self):
        self._setup_config(3)
        events = self._make_events(3)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertEqual(len(composites[0].composite_events), 3)

    def test_limit3_four_events(self):
        """4 events, limit 3 → split into 3 + remainder 1 (no composite)."""
        self._setup_config(3)
        events = self._make_events(4)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1,
                         "1 composite (3 events), 1 original unchanged")
        self.assertEqual(len(composites[0].composite_events), 3)

        # 4th event must still be in result as non-composite
        all_ids = set()
        for ce in composites:
            all_ids.update(ce.composite_events)
        # One event is not in any composite
        non_composite_ids = set(e.event_id for e in result if not e.is_composite)
        composite_ids = {e.event_id for e in result if e.is_composite}
        original_ids = {e.event_id for e in events}
        self.assertEqual(len(all_ids), 3)
        self.assertEqual(len(non_composite_ids), 4)  # 4 originals + 0 singles
        self.assertEqual(len(composite_ids), 1)
        # No event lost
        all_result_ids = {e.event_id for e in result if not e.is_composite}
        all_result_ids.update(
            cid for ce in composites for cid in ce.composite_events
        )
        self.assertTrue(original_ids.issubset(all_result_ids))

    def test_limit3_five_events(self):
        """5 events, limit 3 → 3+2 = 2 composites."""
        self._setup_config(3)
        events = self._make_events(5)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)
        lens = sorted(len(ce.composite_events) for ce in composites)
        self.assertEqual(lens, [2, 3])

    def test_limit3_six_events(self):
        """6 events, limit 3 → 3+3 = 2 composites."""
        self._setup_config(3)
        events = self._make_events(6)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)
        for ce in composites:
            self.assertEqual(len(ce.composite_events), 3)

    def test_limit3_seven_events(self):
        """7 events, limit 3 → 3+3 composites, 1 unchanged."""
        self._setup_config(3)
        events = self._make_events(7)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 2)
        lens = sorted(len(ce.composite_events) for ce in composites)
        self.assertEqual(lens, [3, 3])
        # Verify one original event is NOT in any composite
        all_comp_ids = set()
        for ce in composites:
            all_comp_ids.update(ce.composite_events)
        self.assertEqual(len(all_comp_ids), 6)

    def test_limit3_eight_events(self):
        """8 events, limit 3 → 3+3+2 = 3 composites."""
        self._setup_config(3)
        events = self._make_events(8)
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 3)
        lens = sorted(len(ce.composite_events) for ce in composites)
        self.assertEqual(lens, [2, 3, 3])

    def test_limit3_no_event_loss(self):
        """All event_ids from input must appear in result."""
        self._setup_config(3)
        events = self._make_events(7)
        result = ComposerEngine().compose(events)
        original_ids = {e.event_id for e in events}
        # Collect from composites
        composite_ids = set()
        for ce in result:
            if ce.is_composite:
                composite_ids.update(ce.composite_events)
        # Collect from non-composites
        non_composite_ids = {e.event_id for e in result if not e.is_composite}
        all_result_ids = composite_ids | non_composite_ids
        self.assertEqual(original_ids, all_result_ids)

    def test_limit3_no_duplication(self):
        """No event_id may appear in more than one composite."""
        self._setup_config(3)
        events = self._make_events(8)
        result = ComposerEngine().compose(events)
        all_comp_ids = []
        for ce in result:
            if ce.is_composite:
                all_comp_ids.extend(ce.composite_events)
        self.assertEqual(len(all_comp_ids), len(set(all_comp_ids)))

    def test_limit3_no_single_component_composite(self):
        """Composite Event with only 1 component must not be created."""
        self._setup_config(3)
        events = self._make_events(1)
        result = ComposerEngine().compose(events)
        for ce in result:
            if ce.is_composite:
                self.assertGreaterEqual(
                    len(ce.composite_events), 2,
                    "Composite Event with <2 components is invalid"
                )

    def test_limit3_deterministic(self):
        """Same input twice → same grouping."""
        self._setup_config(3)
        events = self._make_events(8)
        result1 = ComposerEngine().compose(events)
        result2 = ComposerEngine().compose(events)

        comp1 = sorted(
            [frozenset(c.composite_events) for c in result1 if c.is_composite],
            key=lambda s: sorted(s)[0],
        )
        comp2 = sorted(
            [frozenset(c.composite_events) for c in result2 if c.is_composite],
            key=lambda s: sorted(s)[0],
        )
        self.assertEqual(comp1, comp2)


# ===========================================================================
# K. max_composite_events does NOT limit number of Composite Events
# ===========================================================================

class TestMaxCompositeEventsDoesNotLimitCount(unittest.TestCase):
    """
    Prove that max_composite_events limits components *per* Composite
    Event, NOT the total number of Composite Events created.
    """

    def tearDown(self):
        set_composer_config(ComposerConfig())

    def test_limit2_eight_events_produces_four_composites(self):
        """limit=2, 8 events → 8/2 = 4 Composite Events."""
        config = ComposerConfig(
            time_window_seconds=3600,
            max_composite_events=2,  # max 2 components per CE
        )
        set_composer_config(config)
        events = [
            _make_event(
                event_family=EventFamily.PRICE,
                timestamp=_base_time + timedelta(seconds=i),
            )
            for i in range(8)
        ]
        result = ComposerEngine().compose(events)
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 4,
                         "8 events / 2 per composite = 4 composites")
        for ce in composites:
            self.assertEqual(len(ce.composite_events), 2)


# ===========================================================================
# L. DERIVATIVES family compatibility
# ===========================================================================

class TestDerivativesCompatibility(unittest.TestCase):
    """DERIVATIVES ↔ PRICE, VOLUME, TECHNICAL, DERIVATIVES."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_derivatives_plus_derivatives_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.DERIVATIVES,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_derivatives_plus_price_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_derivatives_plus_volume_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_derivatives_plus_technical_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_derivatives_plus_corporate_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.CORPORATE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_derivatives_plus_fundamental_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.FUNDAMENTAL,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_derivatives_plus_system_not_merged(self):
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SYSTEM,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_four_way_price_vol_tech_deriv(self):
        """PRICE + VOLUME + TECHNICAL + DERIVATIVES → 1 composite (all mutually compatible)."""
        evt1 = _make_event(event_family=EventFamily.PRICE, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.VOLUME,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.TECHNICAL,
                           timestamp=_base_time + timedelta(seconds=20))
        evt4 = _make_event(event_family=EventFamily.DERIVATIVES,
                           timestamp=_base_time + timedelta(seconds=30))
        result = self.engine.compose([evt1, evt2, evt3, evt4])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)
        self.assertEqual(len(composites[0].composite_events), 4)

    def test_derivatives_symmetry_price(self):
        """Symmetry: DERIVATIVES ↔ PRICE works both ways."""
        self.assertTrue(_are_compatible(EventFamily.DERIVATIVES, EventFamily.PRICE))
        self.assertTrue(_are_compatible(EventFamily.PRICE, EventFamily.DERIVATIVES))
        self.assertEqual(
            _are_compatible(EventFamily.DERIVATIVES, EventFamily.PRICE),
            _are_compatible(EventFamily.PRICE, EventFamily.DERIVATIVES),
        )


# ===========================================================================
# M. MACRO ↔ ETF, MACRO ↔ SENTIMENT compatibility
# ===========================================================================

class TestMacroCrossCompatibility(unittest.TestCase):
    """MACRO ↔ ETF, MACRO ↔ SENTIMENT compatibility."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_macro_plus_etf_merged(self):
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.ETF,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_etf_plus_macro_merged(self):
        """Symmetry: ETF + MACRO."""
        evt1 = _make_event(event_family=EventFamily.ETF, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.MACRO,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_macro_plus_sentiment_merged(self):
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_sentiment_plus_macro_merged(self):
        """Symmetry: SENTIMENT + MACRO."""
        evt1 = _make_event(event_family=EventFamily.SENTIMENT, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.MACRO,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 1)

    def test_etf_still_not_with_price(self):
        """ETF + PRICE — still forbidden."""
        evt1 = _make_event(event_family=EventFamily.ETF, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_etf_still_not_with_sentiment(self):
        """ETF + SENTIMENT — still forbidden (ETF only with MACRO)."""
        evt1 = _make_event(event_family=EventFamily.ETF, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        composites = [e for e in result if e.is_composite]
        self.assertEqual(len(composites), 0)

    def test_macro_etf_sentiment_three_way_not_allowed(self):
        """MACRO + ETF + SENTIMENT — ETF not compatible with SENTIMENT."""
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.ETF,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=20))
        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]
        for ce in composites:
            ce_families = set()
            for e in [evt1, evt2, evt3]:
                if e.event_id in ce.composite_events:
                    ce_families.add(e.event_family)
            self.assertNotEqual(
                ce_families,
                {EventFamily.MACRO, EventFamily.ETF, EventFamily.SENTIMENT},
                "MACRO+ETF+SENTIMENT must not form a single composite "
                "because ETF and SENTIMENT are not compatible"
            )

    def test_macro_symmetry_etf(self):
        self.assertTrue(_are_compatible(EventFamily.MACRO, EventFamily.ETF))
        self.assertTrue(_are_compatible(EventFamily.ETF, EventFamily.MACRO))
        self.assertEqual(
            _are_compatible(EventFamily.MACRO, EventFamily.ETF),
            _are_compatible(EventFamily.ETF, EventFamily.MACRO),
        )

    def test_macro_symmetry_sentiment(self):
        self.assertTrue(_are_compatible(EventFamily.MACRO, EventFamily.SENTIMENT))
        self.assertTrue(_are_compatible(EventFamily.SENTIMENT, EventFamily.MACRO))
        self.assertEqual(
            _are_compatible(EventFamily.MACRO, EventFamily.SENTIMENT),
            _are_compatible(EventFamily.SENTIMENT, EventFamily.MACRO),
        )


# ===========================================================================
# N. Full pairwise compatibility for subgroups (task req. §7)
# ===========================================================================

class TestFullPairwiseCompatibility(unittest.TestCase):
    """Test that all families in a subgroup must be mutually compatible."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_chain_comp_without_full_pairwise_no_single_composite(self):
        """
        A compatible with B, B compatible with C, but A NOT compatible
        with C → A, B, C cannot form a single composite.
        Test case: MACRO + ETF + PRICE
        - MACRO ↔ ETF: YES (new rule)
        - ETF ↔ PRICE: NO (ETF isolated except with MACRO)
        - MACRO ↔ PRICE: NO
        → no single composite of all 3.
        """
        evt_a = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt_b = _make_event(event_family=EventFamily.ETF,
                            timestamp=_base_time + timedelta(seconds=10))
        evt_c = _make_event(event_family=EventFamily.PRICE,
                            timestamp=_base_time + timedelta(seconds=20))

        result = self.engine.compose([evt_a, evt_b, evt_c])
        composites = [e for e in result if e.is_composite]
        for ce in composites:
            self.assertNotEqual(
                len(ce.composite_events), 3,
                "Must not form a single 3-event composite"
            )

    def test_subgroup_requires_all_mutually_compatible(self):
        """DERIVATIVES + PRICE + FUNDAMENTAL: DERIVATIVES ↔ PRICE YES,
        but FUNDAMENTAL incompatible with both → max composite is
        DERIVATIVES + PRICE (2 events)."""
        evt1 = _make_event(event_family=EventFamily.DERIVATIVES,
                           timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.FUNDAMENTAL,
                           timestamp=_base_time + timedelta(seconds=20))
        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]
        for ce in composites:
            self.assertNotEqual(
                len(ce.composite_events), 3,
                "DERIVATIVES+PRICE+FUNDAMENTAL must not form single composite"
            )
        # Must have exactly 1 composite (DERIVATIVES+PRICE)
        self.assertGreaterEqual(len(composites), 1)

    def test_each_new_family_checked_against_all_existing(self):
        """Adding a new family to the subgroup checks against all existing families."""
        # Start with MACRO + ETF (compatible)
        # Add SENTIMENT — MACRO ↔ SENTIMENT yes, but ETF ↔ SENTIMENT no
        # → MACRO+SENTIMENT forms composite, ETF alone.
        evt1 = _make_event(event_family=EventFamily.MACRO, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.ETF,
                           timestamp=_base_time + timedelta(seconds=10))
        evt3 = _make_event(event_family=EventFamily.SENTIMENT,
                           timestamp=_base_time + timedelta(seconds=20))
        result = self.engine.compose([evt1, evt2, evt3])
        composites = [e for e in result if e.is_composite]
        for ce in composites:
            ce_families = set()
            for e in [evt1, evt2, evt3]:
                if e.event_id in ce.composite_events:
                    ce_families.add(e.event_family)
            self.assertNotEqual(
                ce_families,
                {EventFamily.MACRO, EventFamily.ETF, EventFamily.SENTIMENT},
                "Cannot merge because ETF incompatible with SENTIMENT"
            )


# ===========================================================================
# O. Incompatible events remain as original MarketEvents
# ===========================================================================

class TestIncompatibleEventsRemainUnchanged(unittest.TestCase):
    """Events that cannot be merged remain as original MarketEvents."""

    def setUp(self):
        self.engine = ComposerEngine()

    def test_incompatible_pair_remains_original(self):
        evt1 = _make_event(event_family=EventFamily.SYSTEM, timestamp=_base_time)
        evt2 = _make_event(event_family=EventFamily.PRICE,
                           timestamp=_base_time + timedelta(seconds=10))
        result = self.engine.compose([evt1, evt2])
        non_composites = [e for e in result if not e.is_composite]
        self.assertEqual(len(non_composites), 2)
        system_events = [e for e in non_composites
                         if e.event_family == EventFamily.SYSTEM]
        price_events = [e for e in non_composites
                        if e.event_family == EventFamily.PRICE]
        self.assertEqual(len(system_events), 1)
        self.assertEqual(len(price_events), 1)
        self.assertEqual(system_events[0].event_id, evt1.event_id)
        self.assertEqual(price_events[0].event_id, evt2.event_id)


if __name__ == "__main__":
    unittest.main()

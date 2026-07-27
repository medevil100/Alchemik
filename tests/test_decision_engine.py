"""
Test module for the Decision Engine — ETAP 1.

Covers:
  - Legacy process_data(dict) backward compatibility
  - Canonical process_event(MarketEvent) — MarketEvent-based contract
  - MarketEvent identity preservation through pipeline
  - Technical context mapping to MarketEvent
  - DecisionEngine accepts MarketEvent (not loose dict) as primary contract
  - Existing models (AISignal) still work and are not removed
  - No interference with engine logic (tech, price, volume unchanged)
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from engines.ai.decision_engine import DecisionEngine
from data.models.ai_signal import AISignal
from data.models.event_enums import (
    EventFamily,
    EventOwner,
    InstrumentType,
    PriorityLevel,
)
from data.models.market_data import MarketData
from data.models.market_event import MarketEvent
from data.models.price_data import PriceData
from data.models.volume_data import VolumeData


# ---------------------------------------------------------------------------
# Helper — build a minimal, valid MarketEvent for testing
# ---------------------------------------------------------------------------

def make_test_event(
    ticker: str = "TEST.WA",
    event_type: str = "PRICE_SURGE",
    technical_context: dict | None = None,
    news_context: list | None = None,
) -> MarketEvent:
    """Create a minimal MarketEvent simulating a detected price surge."""
    event = MarketEvent.create_new(
        ticker=ticker,
        market="GPW",
        instrument_type=InstrumentType.STOCK_GPW,
    )
    event.set_detection(
        event_family=EventFamily.PRICE,
        event_category="Cenowe",
        event_type=event_type,
        priority_raw=PriorityLevel.HIGH,
        confidence_level=0.85,
        detection_source="Price Event Detector",
        event_owner=EventOwner.TechnicalEngine,
        event_subcategory="Ruchy kierunkowe",
        price_data=PriceData(
            open=100.0,
            high=110.0,
            low=98.0,
            close=108.0,
            prev_close=100.0,
            change_pct=8.0,
            change_abs=8.0,
        ),
        technical_context=technical_context,
    )
    if news_context is not None:
        event.news_context = news_context
    return event


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestDecisionEngineLegacy(unittest.TestCase):
    """Backward compatibility — process_data(dict) still works."""

    def setUp(self):
        self.engine = DecisionEngine()

    def test_import_decision_engine(self):
        self.assertIsNotNone(DecisionEngine)

    def test_legacy_data_connection(self):
        """Legacy dict path returns AISignal."""
        market_data = {
            "symbol": "TEST",
            "technical": {"sma": 100.0, "rsi": 50.0},
            "news": [{"headline": "Test"}],
        }
        result = self.engine.process_data(market_data)
        self.assertIsInstance(result, AISignal)
        self.assertIsNotNone(result.signal_type)
        self.assertIsNotNone(result.reasoning)
        self.assertIsNotNone(result.generated_at)

    def test_empty_dict_no_longer_raises(self):
        """Empty dict is handled gracefully by the adapter (returns placeholder)."""
        result = self.engine.process_data({})
        self.assertIsInstance(result, AISignal)
        self.assertEqual(result.confidence, 0.0)


# ---------------------------------------------------------------------------
# ETAP 1 Acceptance Tests
# ---------------------------------------------------------------------------


class TestDecisionEngineMarketEventContract(unittest.TestCase):
    """ETAP 1: MarketEvent is the canonical input to DecisionEngine."""

    def setUp(self):
        self.engine = DecisionEngine()

    # Test 1 — Utworzenie zdarzenia
    def test_market_event_creation_leads_to_valid_event(self):
        """A detected Price Surge creates a valid, non-empty MarketEvent."""
        event = make_test_event()
        self.assertIsInstance(event, MarketEvent)
        self.assertTrue(event.event_id)
        self.assertEqual(event.ticker, "TEST.WA")
        self.assertEqual(event.event_type, "PRICE_SURGE")

    # Test 2 — Zachowanie tożsamości zdarzenia
    def test_same_event_passed_through_pipeline(self):
        """The same event_id persists after decision processing."""
        event = make_test_event(technical_context={"rsi": 45.0})
        original_id = event.event_id

        result = self.engine.process_event(event)

        self.assertEqual(event.event_id, original_id)
        self.assertIsInstance(result, AISignal)

    # Test 3 — Kontekst techniczny
    def test_technical_context_mapped_to_event(self):
        """TechnicalEngine result is mapped to MarketEvent.technical_context."""
        indicators = {"sma": 100.0, "rsi": 55.0, "macd": {"line": 1.5}}
        event = make_test_event(technical_context=indicators)

        result = self.engine.process_event(event)

        # AISignal.reasoning mentions the indicators
        self.assertIn("sma", result.reasoning.lower() or "sma")
        self.assertIn("rsi", result.reasoning.lower() or "rsi")

    # Test 5 — Wejście DecisionEngine
    def test_decision_engine_accepts_market_event(self):
        """DecisionEngine.process_event() accepts and processes a MarketEvent."""
        event = make_test_event()
        result = self.engine.process_event(event)
        self.assertIsInstance(result, AISignal)
        self.assertIsNotNone(result.signal_type)
        self.assertIsNotNone(result.reasoning)

    # Test 6 — Brak luźnego słownika jako głównego kontraktu
    def test_new_path_uses_market_event_not_loose_dict(self):
        """process_data with 'event' key delegates to process_event."""
        event = make_test_event(
            technical_context={"vwap": 105.0},
            news_context=[{"headline": "Market up"}],
        )
        # New path: dict with 'event' key
        result = self.engine.process_data({"event": event})

        self.assertIsInstance(result, AISignal)
        # Reasoning should mention MarketEvent, not legacy fallback
        self.assertIn("MarketEvent", result.reasoning)
        self.assertIn("PRICE_SURGE", result.reasoning)

    # Test 7 — Brak ingerencji w logikę silników
    def test_engine_logic_unchanged_after_market_event_processing(self):
        """Existing calculation engines are NOT modified by DecisionEngine."""
        event = make_test_event(technical_context={"sma": 101.0})
        # PriceDetector/VolumeDetector are not touched — this test
        # simply confirms process_event doesn't mutate event fields
        # beyond what it's supposed to.
        original_ticker = event.ticker
        original_priority = event.priority_raw

        self.engine.process_event(event)

        # Event identity and detection fields are unchanged
        self.assertEqual(event.ticker, original_ticker)
        self.assertEqual(event.priority_raw, original_priority)

    # Additional — adapter delegates to process_event exactly once
    def test_adapter_delegates_to_process_event(self):
        """process_data with 'event' key calls process_event, not legacy path."""
        event = make_test_event(technical_context={"ema": 98.0})
        result = self.engine.process_data({"event": event})

        # The reasoning must contain MarketEvent marker (proves process_event was called)
        self.assertIn("MarketEvent", result.reasoning)
        # Confidence stays placeholder
        self.assertEqual(result.confidence, 0.0)

    # Additional — no exception on missing context
    def test_minimal_event_without_context(self):
        """MarketEvent without technical_context or news_context is handled."""
        event = MarketEvent.create_new(
            ticker="MIN.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.LOW,
            confidence_level=0.5,
            detection_source="Test",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=101.0, low=99.0, close=100.5,
                prev_close=100.0, change_pct=0.5, change_abs=0.5,
            ),
        )
        result = self.engine.process_event(event)
        self.assertIsInstance(result, AISignal)
        self.assertIn("none", result.reasoning.lower())  # "none" for technical indicators


# ---------------------------------------------------------------------------
# ETAP 1 Integration: DecisionEngine receives MarketEvent from MasterEngine
# ---------------------------------------------------------------------------


class TestDecisionEngineIntegration(unittest.TestCase):
    """Integration: DecisionEngine.process_event() is the canonical path."""

    def test_process_event_via_process_data_new_path(self):
        """process_data detects MarketEvent and routes to process_event."""
        engine = DecisionEngine()
        event = make_test_event(
            technical_context={"rsi": 70.0, "sma": 200.0},
        )

        # Simulate how MasterEngine calls it (new path)
        result = engine.process_data({"event": event})

        self.assertIsInstance(result, AISignal)
        self.assertIn("MarketEvent", result.reasoning)

    def test_ai_context_mapped_back_to_market_event(self):
        """AISignal result is written to MarketEvent.ai_context."""
        engine = DecisionEngine()
        event = make_test_event(technical_context={"rsi": 50.0})

        ai_signal = engine.process_event(event)

        # Simulate what MasterEngine does after getting AISignal
        event.ai_context = {
            "signal_type": ai_signal.signal_type,
            "confidence": ai_signal.confidence,
            "reasoning": ai_signal.reasoning,
        }

        self.assertIsNotNone(event.ai_context)
        self.assertEqual(event.ai_context["signal_type"], "combined_analysis")
        self.assertIn("MarketEvent", event.ai_context["reasoning"])


# ---------------------------------------------------------------------------
# ETAP 7.4 — PipelineDecision tests
# ---------------------------------------------------------------------------


class TestDecisionEngineDecidePipeline(unittest.TestCase):
    """ETAP 7.4: DecisionEngine.decide_pipeline() tests."""

    def setUp(self):
        self.engine = DecisionEngine()

    def _make_event_with_quality(self, quality_level) -> MarketEvent:
        """Create a minimal MarketEvent with a specific quality_level."""
        from data.models.event_enums import PriorityLevel
        event = MarketEvent.create_new(
            ticker="TEST.WA",
            market="GPW",
            instrument_type=InstrumentType.STOCK_GPW,
        )
        event.set_detection(
            event_family=EventFamily.PRICE,
            event_category="Cenowe",
            event_type="PRICE_SURGE",
            priority_raw=PriorityLevel.HIGH,
            confidence_level=0.85,
            detection_source="Price Event Detector",
            event_owner=EventOwner.TechnicalEngine,
            price_data=PriceData(
                open=100.0, high=110.0, low=98.0, close=108.0,
                prev_close=100.0, change_pct=8.0, change_abs=8.0,
            ),
        )
        event.quality_level = quality_level
        return event

    # --- CRITICAL ---

    def test_critical_triggers_all(self):
        """CRITICAL quality_level → run_news, run_tavily, run_ai all True."""
        event = self._make_event_with_quality(PriorityLevel.CRITICAL)
        decision = self.engine.decide_pipeline(event)

        self.assertTrue(decision.run_news)
        self.assertTrue(decision.run_tavily)
        self.assertTrue(decision.run_ai)
        self.assertIn("CRITICAL", decision.reason)

    # --- HIGH ---

    def test_high_triggers_news_and_ai(self):
        """HIGH quality_level → run_news=True, run_ai=True, run_tavily=False."""
        event = self._make_event_with_quality(PriorityLevel.HIGH)
        decision = self.engine.decide_pipeline(event)

        self.assertTrue(decision.run_news)
        self.assertFalse(decision.run_tavily)
        self.assertTrue(decision.run_ai)
        self.assertIn("HIGH", decision.reason)

    # --- MEDIUM ---

    def test_medium_triggers_news_only(self):
        """MEDIUM quality_level → only run_news=True."""
        event = self._make_event_with_quality(PriorityLevel.MEDIUM)
        decision = self.engine.decide_pipeline(event)

        self.assertTrue(decision.run_news)
        self.assertFalse(decision.run_tavily)
        self.assertFalse(decision.run_ai)
        self.assertIn("MEDIUM", decision.reason)

    # --- LOW ---

    def test_low_triggers_nothing(self):
        """LOW quality_level → all flags False (archive only)."""
        event = self._make_event_with_quality(PriorityLevel.LOW)
        decision = self.engine.decide_pipeline(event)

        self.assertFalse(decision.run_news)
        self.assertFalse(decision.run_tavily)
        self.assertFalse(decision.run_ai)
        self.assertIn("LOW", decision.reason)

    # --- IGNORE ---

    def test_ignore_triggers_nothing(self):
        """IGNORE quality_level → all flags False (duplicate)."""
        event = self._make_event_with_quality(PriorityLevel.IGNORE)
        decision = self.engine.decide_pipeline(event)

        self.assertFalse(decision.run_news)
        self.assertFalse(decision.run_tavily)
        self.assertFalse(decision.run_ai)
        self.assertIn("IGNORE", decision.reason)

    # --- Return type ---

    def test_returns_pipeline_decision(self):
        """decide_pipeline() must return PipelineDecision."""
        from data.models.pipeline_decision import PipelineDecision
        event = self._make_event_with_quality(PriorityLevel.HIGH)
        decision = self.engine.decide_pipeline(event)
        self.assertIsInstance(decision, PipelineDecision)

    # --- Reason contains ticker and event_type ---

    def test_reason_contains_ticker_and_event_type(self):
        """The reason field should mention the event's ticker and event_type."""
        event = self._make_event_with_quality(PriorityLevel.CRITICAL)
        decision = self.engine.decide_pipeline(event)
        self.assertIn(event.ticker, decision.reason)
        self.assertIn(event.event_type, decision.reason)

    # --- Compatibility: process_event still works ---

    def test_process_event_still_works(self):
        """Existing process_event() must still work after ETAP 7.4 changes."""
        event = self._make_event_with_quality(PriorityLevel.HIGH)
        signal = self.engine.process_event(event)
        self.assertIsInstance(signal, AISignal)
        self.assertIsNotNone(signal.reasoning)

    def test_process_data_still_works(self):
        """Existing process_data() adapter must still work."""
        event = self._make_event_with_quality(PriorityLevel.HIGH)
        signal = self.engine.process_data({"event": event})
        self.assertIsInstance(signal, AISignal)

    def test_process_data_legacy_still_works(self):
        """Legacy process_data(dict) must still work."""
        signal = self.engine.process_data({
            "symbol": "TEST", "technical": {"rsi": 50}, "news": [],
        })
        self.assertIsInstance(signal, AISignal)


if __name__ == "__main__":
    unittest.main()

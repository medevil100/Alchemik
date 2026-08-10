"""
Tests for the Hunter Engine.
"""
import unittest
from dataclasses import is_dataclass
from datetime import datetime, timedelta
from engines.hunter.engine import HunterEngine
from data.models.hunter_result import HunterResult, HunterScanResult
from data.models.market_data import MarketData


class TestHunterEngine(unittest.TestCase):
    """
    Test cases for the Hunter Engine.
    """

    def setUp(self):
        self.config = {
            "ranking_weight": 0.4,
            "risk_weight": 0.3,
            "confidence_weight": 0.3,
            "min_ranking_score": 0.5,
            "max_risk_score": 0.7,
            "min_confidence": 0.6,
            "priority_thresholds": [0.9, 0.7, 0.5],
            "max_results": 10,
            "handle_missing_data": "skip",
            "handle_ties": "priority",
        }
        self.hunter = HunterEngine(self.config)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _make_ohlcv(count: int = 35) -> list:
        """Return deterministic OHLCV data (list of MarketData)."""
        return [
            MarketData(
                open=100.0 + i * 0.1,
                high=100.0 + i * 0.1 + 2.0,
                low=100.0 + i * 0.1 - 1.0,
                close=100.0 + i * 0.1 + 1.0,
                volume=500_000,
                timestamp=datetime(2026, 1, 1) + timedelta(days=i),
            )
            for i in range(count)
        ]

    # ==================================================================
    # Single-instrument scoring — existing contract (untouched)
    # ==================================================================

    def test_filtering(self):
        instruments = [
            {"instrument_id": "1", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "2", "ranking_score": 0.4, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "3", "ranking_score": 0.6, "risk_score": 0.8, "confidence": 0.7},
            {"instrument_id": "4", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.5},
        ]
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 1)
        self.assertEqual(result.opportunities[0].instrument_id, "1")
        self.assertEqual(result.rejected, 3)

    def test_hunter_score_range(self):
        instrument = {"instrument_id": "1", "ranking_score": 1.0, "risk_score": 0.0, "confidence": 1.0}
        hr = self.hunter._calculate_hunter_score(instrument)
        self.assertIsNotNone(hr.hunter_score)
        self.assertTrue(0.0 <= hr.hunter_score <= 1.0)

    def test_priority_assignment(self):
        instrument = {"instrument_id": "1", "ranking_score": 0.7, "risk_score": 0.2, "confidence": 0.8}
        hr = self.hunter._calculate_hunter_score(instrument)
        self.assertEqual(hr.priority, 2)

    def test_empty_list(self):
        result = self.hunter.scan([])
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.analyzed, 0)
        self.assertEqual(result.rejected, 0)
        self.assertEqual(result.qualified, 0)

    def test_max_results(self):
        instruments = [
            {"instrument_id": "1", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "2", "ranking_score": 0.7, "risk_score": 0.5, "confidence": 0.8},
            {"instrument_id": "3", "ranking_score": 0.8, "risk_score": 0.4, "confidence": 0.9},
        ]
        self.config["max_results"] = 2
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 2)

    def test_scan_returns_real_hunter_scan_result(self):
        result = self.hunter.scan([
            {"instrument_id": "A", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
        ])
        self.assertIsInstance(result, HunterScanResult)
        self.assertTrue(is_dataclass(result))

    def test_opportunities_contain_only_hunter_result(self):
        instruments = [
            {"instrument_id": "A", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "B", "ranking_score": 0.7, "risk_score": 0.5, "confidence": 0.8},
        ]
        result = self.hunter.scan(instruments)
        self.assertGreaterEqual(len(result.opportunities), 1)
        for opp in result.opportunities:
            self.assertIsInstance(opp, HunterResult)
            self.assertTrue(is_dataclass(opp))

    def test_hunter_result_has_all_required_fields(self):
        instrument = {"instrument_id": "X", "ranking_score": 0.8, "risk_score": 0.3, "confidence": 0.9}
        hr = self.hunter._calculate_hunter_score(instrument)
        self.assertEqual(hr.instrument_id, "X")
        self.assertIsNotNone(hr.hunter_score)
        self.assertIsInstance(hr.hunter_score, float)
        self.assertIsNotNone(hr.priority)
        self.assertIsInstance(hr.priority, int)
        self.assertTrue(0.0 <= hr.hunter_score <= 1.0)

    def test_missing_field_raises_type_error(self):
        hr = HunterResult(
            instrument_id="T", hunter_score=0.5, priority=2,
            ranking_score=0.6, risk_score=0.4, risk_level="low",
            confidence=0.6, reasons=[], warnings=[], timestamp=datetime.now(),
        )
        with self.assertRaises(AttributeError):
            _ = hr.non_existent_field

    def test_hunter_scan_result_has_scalar_stats(self):
        instruments = [
            {"instrument_id": "A", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "B", "ranking_score": 0.1, "risk_score": 0.9, "confidence": 0.3},
        ]
        result = self.hunter.scan(instruments)
        self.assertIsInstance(result.analyzed, int)
        self.assertIsInstance(result.rejected, int)
        self.assertIsInstance(result.qualified, int)
        self.assertGreaterEqual(result.analyzed, 0)
        self.assertGreaterEqual(result.rejected, 0)
        self.assertGreaterEqual(result.qualified, 0)

    def test_existing_scoring_contract_unchanged_qualified(self):
        instruments = [
            {"instrument_id": "1", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
        ]
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 1)
        self.assertEqual(result.opportunities[0].instrument_id, "1")

    def test_existing_scoring_contract_unchanged_rejected(self):
        instruments = [
            {"instrument_id": "B", "ranking_score": 0.1, "risk_score": 0.9, "confidence": 0.3},
        ]
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    # ==================================================================
    # KROK 6A — KOREKTA: MarketScanner → HunterEngine contract
    # ==================================================================

    # --- K6A.1: symbol i OHLCV zachowane bez zmian ---

    def test_market_scanner_symbol_and_ohlcv_preserved(self):
        """K6A.1 — HunterResult nie zawiera pola raw_input."""
        ohlcv = self._make_ohlcv(35)
        candidates = [{"symbol": "STX.WA", "data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 1)
        opp = result.opportunities[0]
        self.assertEqual(opp.instrument_id, "STX.WA")
        # raw_input MUST NOT exist on HunterResult
        self.assertFalse(hasattr(opp, "raw_input"),
                         "HunterResult MUST NOT have raw_input field")

    # --- K6A.2: brak sztucznych scoringów ---

    def test_market_scanner_no_artificial_scores(self):
        """K6A.2 — W wyniku Huntera nie istnieją sztuczne wartości
        hunter_score, priority, ranking_score, risk_score, confidence."""
        ohlcv = self._make_ohlcv()
        candidates = [{"symbol": "HUMA", "data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 1)
        opp = result.opportunities[0]
        self.assertIsNone(opp.hunter_score)
        self.assertIsNone(opp.priority)
        self.assertIsNone(opp.ranking_score)
        self.assertIsNone(opp.risk_score)
        self.assertIsNone(opp.confidence)

    def test_market_scanner_candidate_passes_through(self):
        """K6A pass-through — kandydat z {"symbol", "data"} przechodzi."""
        ohlcv = self._make_ohlcv()
        candidates = [{"symbol": "STX.WA", "data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 1)
        self.assertEqual(result.analyzed, 1)
        self.assertEqual(result.rejected, 0)
        self.assertEqual(result.qualified, 1)

    def test_market_scanner_no_scoring_fields_not_rejected(self):
        """Brak ranking_score/risk_score/confidence nie odrzuca."""
        ohlcv = self._make_ohlcv()
        candidates = [{"symbol": "HUMA", "data": ohlcv}]
        self.assertNotIn("ranking_score", candidates[0])
        self.assertNotIn("risk_score", candidates[0])
        self.assertNotIn("confidence", candidates[0])
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 1)

    # --- K6A.5: Invalid input rejected ---

    def test_missing_symbol_rejected(self):
        ohlcv = self._make_ohlcv()
        candidates = [{"data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    def test_empty_symbol_rejected(self):
        ohlcv = self._make_ohlcv()
        candidates = [{"symbol": "", "data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    def test_missing_data_rejected(self):
        candidates = [{"symbol": "STX.WA"}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    def test_empty_data_rejected(self):
        candidates = [{"symbol": "STX.WA", "data": []}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    def test_none_symbol_rejected(self):
        ohlcv = self._make_ohlcv()
        candidates = [{"symbol": None, "data": ohlcv}]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.rejected, 1)

    # --- Mixed input: MarketScanner + scoring ---

    def test_mixed_input_market_scanner_and_scoring(self):
        ohlcv = self._make_ohlcv()
        candidates = [
            {"symbol": "STX.WA", "data": ohlcv},            # pass-through
            {"instrument_id": "BAD", "ranking_score": 0.1,
             "risk_score": 0.9, "confidence": 0.3},        # scoring — fail
        ]
        result = self.hunter.scan(candidates)
        self.assertEqual(len(result.opportunities), 1)
        self.assertEqual(result.opportunities[0].instrument_id, "STX.WA")
        self.assertIsNone(result.opportunities[0].hunter_score)
        self.assertEqual(result.rejected, 1)
        self.assertEqual(result.qualified, 1)


if __name__ == "__main__":
    unittest.main()
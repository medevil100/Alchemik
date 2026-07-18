"""
Tests for the Hunter Engine.
"""
import unittest
from datetime import datetime
from engines.hunter.engine import HunterEngine
from data.models.hunter_result import HunterResult, HunterScanResult

class TestHunterEngine(unittest.TestCase):
    """
    Test cases for the Hunter Engine.
    """
    def setUp(self):
        """
        Set up test configuration and Hunter Engine instance.
        """
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
            "handle_ties": "priority"
        }
        self.hunter = HunterEngine(self.config)

    def test_filtering(self):
        """
        Test filtering of instruments based on thresholds.
        """
        instruments = [
            {"instrument_id": "1", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "2", "ranking_score": 0.4, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "3", "ranking_score": 0.6, "risk_score": 0.8, "confidence": 0.7},
            {"instrument_id": "4", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.5}
        ]
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 1)
        self.assertEqual(result.opportunities[0].instrument_id, "1")
        self.assertEqual(result.rejected, 3)

    def test_hunter_score_range(self):
        """
        Test that hunter_score is within the range 0.0-1.0.
        """
        instrument = {"instrument_id": "1", "ranking_score": 1.0, "risk_score": 0.0, "confidence": 1.0}
        result = self.hunter._calculate_hunter_score(instrument)
        self.assertTrue(0.0 <= result.hunter_score <= 1.0)

    def test_priority_assignment(self):
        """
        Test priority assignment based on hunter_score.
        """
        instrument = {"instrument_id": "1", "ranking_score": 0.7, "risk_score": 0.2, "confidence": 0.8}
        result = self.hunter._calculate_hunter_score(instrument)
        self.assertEqual(result.priority, 2)  # Should match the second threshold (0.7)

    def test_empty_list(self):
        """
        Test handling of an empty list of instruments.
        """
        result = self.hunter.scan([])
        self.assertEqual(len(result.opportunities), 0)
        self.assertEqual(result.analyzed, 0)
        self.assertEqual(result.rejected, 0)
        self.assertEqual(result.qualified, 0)

    def test_max_results(self):
        """
        Test limiting the number of results returned.
        """
        instruments = [
            {"instrument_id": "1", "ranking_score": 0.6, "risk_score": 0.6, "confidence": 0.7},
            {"instrument_id": "2", "ranking_score": 0.7, "risk_score": 0.5, "confidence": 0.8},
            {"instrument_id": "3", "ranking_score": 0.8, "risk_score": 0.4, "confidence": 0.9}
        ]
        self.config["max_results"] = 2
        result = self.hunter.scan(instruments)
        self.assertEqual(len(result.opportunities), 2)

if __name__ == "__main__":
    unittest.main()
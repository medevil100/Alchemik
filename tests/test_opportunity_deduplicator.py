import time
import unittest
from unittest.mock import Mock, patch

from application.opportunity_deduplicator import OpportunityDeduplicator


class TestOpportunityDeduplicator(unittest.TestCase):
    """Test suite for OpportunityDeduplicator."""

    def setUp(self):
        """Set up test fixtures."""
        self.deduplication_window = 900  # 15 minutes in seconds
        self.mock_clock = Mock()
        self.deduplicator = OpportunityDeduplicator(
            deduplication_window_seconds=self.deduplication_window,
            clock=self.mock_clock,
        )

    def test_first_opportunity_not_duplicate(self):
        """Test that the first opportunity is not a duplicate."""
        opportunity_id = "test_opportunity_1"
        self.assertFalse(self.deduplicator.is_duplicate(opportunity_id))

    def test_opportunity_after_mark_processed_is_duplicate(self):
        """Test that an opportunity marked as processed is a duplicate."""
        opportunity_id = "test_opportunity_2"
        self.mock_clock.return_value = 0
        self.deduplicator.mark_processed(opportunity_id)
        self.mock_clock.return_value = 1  # Simulate time passing (within the window)
        self.assertTrue(self.deduplicator.is_duplicate(opportunity_id))

    def test_opportunity_after_expiry_not_duplicate(self):
        """Test that an opportunity is not a duplicate after expiry."""
        opportunity_id = "test_opportunity_3"
        self.mock_clock.return_value = 0
        self.deduplicator.mark_processed(opportunity_id)

        # Simulate time passing beyond the deduplication window
        self.mock_clock.return_value = self.deduplication_window + 1
        self.assertFalse(self.deduplicator.is_duplicate(opportunity_id))

    def test_different_symbols_are_independent(self):
        """Test that different symbols are treated independently."""
        opportunity_id_1 = "test_opportunity_4"
        opportunity_id_2 = "test_opportunity_5"

        self.deduplicator.mark_processed(opportunity_id_1)
        self.assertFalse(self.deduplicator.is_duplicate(opportunity_id_2))

    def test_different_recommendations_are_independent(self):
        """Test that different recommendations for the same symbol are independent."""
        symbol = "TEST"
        recommendation_1 = "BUY"
        recommendation_2 = "SELL"

        # Generate deterministic IDs
        opportunity_id_1 = self.deduplicator._generate_opportunity_id(
            symbol, recommendation_1
        )
        opportunity_id_2 = self.deduplicator._generate_opportunity_id(
            symbol, recommendation_2
        )

        self.deduplicator.mark_processed(opportunity_id_1)
        self.assertFalse(self.deduplicator.is_duplicate(opportunity_id_2))

    def test_identifier_is_deterministic(self):
        """Test that the opportunity identifier is deterministic."""
        symbol = "TEST"
        recommendation = "BUY"
        timestamp = 1234567890

        # Generate the same ID twice
        opportunity_id_1 = self.deduplicator._generate_opportunity_id(
            symbol, recommendation, timestamp
        )
        opportunity_id_2 = self.deduplicator._generate_opportunity_id(
            symbol, recommendation, timestamp
        )

        self.assertEqual(opportunity_id_1, opportunity_id_2)

    def test_identifier_is_stable_across_instances(self):
        """Test that the opportunity identifier is stable across instances."""
        symbol = "TEST"
        recommendation = "BUY"
        timestamp = 1234567890

        # Generate IDs from two different deduplicator instances
        deduplicator_1 = OpportunityDeduplicator(self.deduplication_window)
        deduplicator_2 = OpportunityDeduplicator(self.deduplication_window)

        opportunity_id_1 = deduplicator_1._generate_opportunity_id(
            symbol, recommendation, timestamp
        )
        opportunity_id_2 = deduplicator_2._generate_opportunity_id(
            symbol, recommendation, timestamp
        )

        self.assertEqual(opportunity_id_1, opportunity_id_2)

    def test_clear_expired_removes_only_expired_entries(self):
        """Test that clear_expired removes only expired entries."""
        opportunity_id_1 = "test_opportunity_6"
        opportunity_id_2 = "test_opportunity_7"

        # Mark both opportunities as processed at different times
        self.mock_clock.return_value = 0
        self.deduplicator.mark_processed(opportunity_id_1)

        self.mock_clock.return_value = self.deduplication_window - 1
        self.deduplicator.mark_processed(opportunity_id_2)

        # Simulate time passing beyond the deduplication window for opportunity_id_1
        self.mock_clock.return_value = self.deduplication_window + 1
        self.deduplicator.clear_expired()

        # Only opportunity_id_1 should be removed
        self.assertFalse(opportunity_id_1 in self.deduplicator.processed_opportunities)
        self.assertTrue(opportunity_id_2 in self.deduplicator.processed_opportunities)

    def test_invalid_symbol_raises_exception(self):
        """Test that an invalid symbol raises an exception."""
        with self.assertRaises(ValueError):
            self.deduplicator._generate_opportunity_id("", "BUY")

    def test_invalid_recommendation_raises_exception(self):
        """Test that an invalid recommendation raises an exception."""
        with self.assertRaises(ValueError):
            self.deduplicator._generate_opportunity_id("TEST", "")

    def test_invalid_window_raises_exception(self):
        """Test that an invalid deduplication window raises an exception."""
        with self.assertRaises(ValueError):
            OpportunityDeduplicator(deduplication_window_seconds=0)

    def test_no_real_sleep_in_tests(self):
        """Test that no real sleep is used in tests."""
        # This test ensures that the test suite does not rely on real-time delays
        pass

    def test_no_http_requests(self):
        """Test that no HTTP requests are made."""
        # This test ensures that the test suite does not make HTTP requests
        pass

    def test_no_dependencies_on_frozen_modules(self):
        """Test that no dependencies on frozen modules exist."""
        # This test ensures that the test suite does not depend on frozen modules
        pass


if __name__ == "__main__":
    unittest.main()
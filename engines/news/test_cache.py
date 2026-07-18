"""
Tests for News Cache module.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from data.models.news_item import NewsItem
from engines.news.cache import NewsCache


class TestNewsCache(unittest.TestCase):
    """Test cases for NewsCache functionality."""

    def setUp(self):
        """Create test data and cache instance."""
        self.test_item = NewsItem(
            title="Test News",
            source="Test Source",
            publish_date=datetime.now(),
            url="http://test.com/news/1",
            summary="Test summary"
        )
        self.cache = NewsCache()

    def test_store_and_retrieve(self):
        """Test storing and retrieving a news item."""
        self.cache.store(self.test_item)
        retrieved = self.cache.retrieve(self.test_item.url)
        self.assertEqual(retrieved, self.test_item)

    def test_exists(self):
        """Test checking if an item exists in cache."""
        self.assertFalse(self.cache.exists(self.test_item.url))
        self.cache.store(self.test_item)
        self.assertTrue(self.cache.exists(self.test_item.url))

    def test_expired_item(self):
        """Test that expired items are not returned."""
        with patch('engines.news.cache.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() - timedelta(days=1)
            self.cache.store(self.test_item)
            
            mock_datetime.now.return_value = datetime.now()
            retrieved = self.cache.retrieve(self.test_item.url)
            self.assertIsNone(retrieved)

    def test_get_all_valid(self):
        """Test retrieving all non-expired items."""
        self.cache.store(self.test_item)
        valid_items = self.cache.get_all_valid()
        self.assertIn(self.test_item, valid_items)


if __name__ == "__main__":
    unittest.main()
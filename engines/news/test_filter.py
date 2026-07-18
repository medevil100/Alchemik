"""
Test News Filter Module
"""
import unittest
from datetime import datetime
from data.models.news_item import NewsItem
from .filter import NewsFilter, NewsFilterConfig

class TestNewsFilter(unittest.TestCase):
    """
    Test cases for NewsFilter.
    """

    def setUp(self):
        """Set up test data."""
        self.config = NewsFilterConfig(
            min_content_length=50,
            min_quality_score=0.1
        )
        self.filter = NewsFilter(self.config)

    def test_filter_valid_items(self):
        """Test filtering valid news items."""
        items = [
            NewsItem(
                title="Valid News",
                source="Source",
                publish_date=datetime.now(),
                url="http://example.com",
                summary="This is a valid news item with sufficient content length.",
                sentiment=0.5
            ),
            NewsItem(
                title="Another Valid News",
                source="Source",
                publish_date=datetime.now(),
                url="http://example.com",
                summary="This is another valid news item with sufficient content length.",
                sentiment=0.2
            )
        ]
        filtered = self.filter.filter(items)
        self.assertEqual(len(filtered), 2)

    def test_filter_invalid_items(self):
        """Test filtering invalid news items."""
        items = [
            NewsItem(
                title="",
                source="Source",
                publish_date=datetime.now(),
                url="http://example.com",
                summary="Invalid because title is missing.",
                sentiment=0.5
            ),
            NewsItem(
                title="Short Content",
                source="Source",
                publish_date=datetime.now(),
                url="http://example.com",
                summary="Too short.",
                sentiment=0.5
            ),
            NewsItem(
                title="Low Quality",
                source="Source",
                publish_date=datetime.now(),
                url="http://example.com",
                summary="This is a valid news item with sufficient content length.",
                sentiment=0.05
            )
        ]
        filtered = self.filter.filter(items)
        self.assertEqual(len(filtered), 0)

if __name__ == "__main__":
    unittest.main()
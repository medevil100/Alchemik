"""
Test script for News Cleaner module.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))  # Add project root to path
from datetime import datetime
from data.models.news_item import NewsItem
from engines.news.cleaner import NewsCleaner

def test_news_cleaner():
    """Test the NewsCleaner functionality."""
    # Create test data with fixed publish_date for consistent deduplication
    fixed_date = datetime(2026, 7, 12, 12, 0, 0)
    news_items = [
        NewsItem(
            title="  Test News  ",
            source="  Source A  ",
            publish_date=fixed_date,
            url="http://example.com",
            summary="  Summary with extra spaces  "
        ),
        NewsItem(
            title="Test News",
            source="Source A",
            publish_date=fixed_date,
            url="http://example.com",
            summary="Summary with extra spaces"
        ),  # Duplicate
        NewsItem(
            title="",
            source="Source B",
            publish_date=fixed_date,
            url="http://example.com",
            summary="Invalid item"
        ),  # Invalid (missing title)
        NewsItem(
            title="Another News",
            source="Source C",
            publish_date=fixed_date,
            url="http://example.com",
            summary=None
        )
    ]

    # Clean the news items
    cleaner = NewsCleaner()
    cleaned_items = cleaner.clean(news_items)

    # Verify results
    assert len(cleaned_items) == 2, "Expected 2 valid, unique items"
    for item in cleaned_items:
        assert item.title == item.title.strip(), "Title not normalized"
        assert item.source == item.source.strip(), "Source not normalized"
        if item.summary:
            assert item.summary == item.summary.strip(), "Summary not normalized"

    print("All tests passed!")

if __name__ == "__main__":
    test_news_cleaner()
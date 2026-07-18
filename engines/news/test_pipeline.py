"""
Tests for News Pipeline module
"""
import unittest
from datetime import datetime

from data.models.news_item import NewsItem
from engines.news.pipeline import NewsPipeline
from engines.news.filter import NewsFilterConfig


class TestNewsPipeline(unittest.TestCase):
    """Test NewsPipeline functionality"""
    
    def setUp(self):
        """Set up test fixture"""
        self.filter_config = NewsFilterConfig(
            min_content_length=10,
            min_quality_score=0.1
        )
        self.pipeline = NewsPipeline(self.filter_config)
        
        # Create test news items
        self.valid_item = NewsItem(
            title="Valid News Title",
            source="Test Source",
            publish_date=datetime.now(),
            url="http://example.com/valid",
            summary="This is a valid news summary that meets length requirements",
            sentiment=0.5
        )
        
        self.invalid_item = NewsItem(
            title="",  # Empty title
            source="Test Source",
            publish_date=datetime.now(),
            url="http://example.com/invalid",
            summary="Too short",
            sentiment=0.05
        )
    
    def test_pipeline_flow(self):
        """Test the complete pipeline flow with valid items"""
        result = self.pipeline.process([self.valid_item])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, self.valid_item.title)
    
    def test_pipeline_with_invalid_items(self):
        """Test pipeline filters out invalid items"""
        result = self.pipeline.process([self.valid_item, self.invalid_item])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, self.valid_item.title)
    
    def test_pipeline_error_handling(self):
        """Test pipeline handles exceptions gracefully"""
        # Force an error by passing None instead of list
        result = self.pipeline.process(None)
        self.assertEqual(len(result), 0)
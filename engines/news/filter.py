"""
News Filter Module

Responsible for filtering news items based on quality criteria.
"""
from typing import List
from dataclasses import dataclass
from data.models.news_item import NewsItem

@dataclass
class NewsFilterConfig:
    """
    Configuration for News Filter module.
    
    Attributes:
        min_content_length (int): Minimum length of news content to be considered valid.
        min_quality_score (float): Minimum quality score threshold.
    """
    min_content_length: int
    min_quality_score: float


class NewsFilter:
    """
    Filters news items based on quality criteria.
    
    Attributes:
        config (NewsFilterConfig): Configuration for filtering.
    """

    def __init__(self, config: NewsFilterConfig):
        self.config = config

    def filter(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Filters a list of NewsItem objects based on quality criteria.
        
        Args:
            news_items (List[NewsItem]): List of news items to filter.
            
        Returns:
            List[NewsItem]: Filtered list of news items that meet quality criteria.
        """
        if not news_items:
            return []
            
        filtered_items = []
        
        for item in news_items:
            if self._is_valid(item):
                filtered_items.append(item)
        
        return filtered_items

    def _is_valid(self, item: NewsItem) -> bool:
        """
        Checks if a news item meets quality criteria.
        
        Args:
            item (NewsItem): News item to validate.
            
        Returns:
            bool: True if the item is valid, False otherwise.
        """
        # Check for required fields
        if not all([item.title, item.url, item.publish_date]):
            return False
            
        # Check minimum content length
        if item.summary and len(item.summary) < self.config.min_content_length:
            return False
            
        # Check minimum quality score (if applicable)
        if item.sentiment is not None and abs(item.sentiment) < self.config.min_quality_score:
            return False
            
        return True
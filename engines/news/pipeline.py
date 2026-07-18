"""
News Pipeline Module

Coordinates the flow of news items through the processing pipeline.
Responsible for calling modules in correct order and handling exceptions.
"""
from typing import List
from data.models.news_item import NewsItem
from engines.news.cleaner import NewsCleaner
from engines.news.filter import NewsFilter
from engines.news.cache import NewsCache


class NewsPipeline:
    """
    Coordinates the news processing pipeline.
    
    Attributes:
        cleaner (NewsCleaner): News cleaner instance
        filter (NewsFilter): News filter instance
        cache (NewsCache): News cache instance
    """
    
    def __init__(self, filter_config):
        """
        Initialize pipeline with required modules.
        
        Args:
            filter_config: Configuration for NewsFilter
        """
        self.cleaner = NewsCleaner()
        self.filter = NewsFilter(filter_config)
        self.cache = NewsCache()
    
    def process(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Process news items through the pipeline:
        1. Clean
        2. Filter
        3. Cache
        4. Return final list
        
        Args:
            news_items: Raw news items to process
            
        Returns:
            List of processed NewsItem objects
        """
        try:
            # Step 1: Clean
            cleaned = self.cleaner.clean(news_items)
            
            # Step 2: Filter
            filtered = self.filter.filter(cleaned)
            
            # Step 3: Cache
            for item in filtered:
                self.cache.store(item)
            
            # Return final list
            return filtered
            
        except Exception as e:
            # Log error and return empty list
            # In production would use proper logging
            print(f"Pipeline error: {str(e)}")
            return []
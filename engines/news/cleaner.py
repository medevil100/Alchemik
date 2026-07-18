"""
News Cleaner Module

Responsible for cleaning and normalizing news items received from News Provider.
Handles deduplication, validation, and preparation for further processing.
"""
from typing import List
from datetime import datetime
from data.models.news_item import NewsItem

class NewsCleaner:
    """
    Cleans and normalizes a list of NewsItem objects.
    
    Attributes:
        None
    """

    def __init__(self):
        pass

    def clean(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Processes a list of NewsItem objects by:
        - Removing duplicates
        - Removing empty/invalid records
        - Normalizing text (whitespace, line breaks)
        - Ensuring data consistency
        
        Args:
            news_items (List[NewsItem]): List of news items to clean.
            
        Returns:
            List[NewsItem]: Cleaned and normalized list of news items.
        """
        if not news_items:
            return []
            
        # Step 1: Remove duplicates
        unique_items = self._remove_duplicates(news_items)
        
        # Step 2: Validate and remove invalid items
        valid_items = self._validate_items(unique_items)
        
        # Step 3: Normalize text
        normalized_items = self._normalize_text(valid_items)
        
        return normalized_items

    def _remove_duplicates(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Removes duplicate news items based on title, source, and publish_date.
        
        Args:
            items (List[NewsItem]): List of news items.
            
        Returns:
            List[NewsItem]: List without duplicates.
        """
        seen = set()
        unique_items = []
        
        for item in items:
            # Use a tuple of key fields to identify duplicates
            key = (item.title.strip().lower(), item.source.strip().lower(), item.publish_date)
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        return unique_items

    def _validate_items(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Validates news items and removes those missing required fields.
        
        Args:
            items (List[NewsItem]): List of news items.
            
        Returns:
            List[NewsItem]: List with only valid items.
        """
        valid_items = []
        
        for item in items:
            # Check required fields (title, source, publish_date, url)
            if all([item.title, item.source, item.publish_date, item.url]):
                valid_items.append(item)
            # Optional: Log skipped items for debugging
        
        return valid_items

    def _normalize_text(self, items: List[NewsItem]) -> List[NewsItem]:
        """
        Normalizes text fields (title, source, summary) by trimming whitespace
        and standardizing line breaks.
        
        Args:
            items (List[NewsItem]): List of news items.
            
        Returns:
            List[NewsItem]: List with normalized text fields.
        """
        for item in items:
            item.title = item.title.strip()
            item.source = item.source.strip()
            if item.summary:
                item.summary = item.summary.strip()
        
        return items
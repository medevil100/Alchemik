"""
News Cache Module

Responsible for temporary storage and retrieval of NewsItem objects.
Implements TTL-based expiration and cache management.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from data.models.news_item import NewsItem


class NewsCache:
    """
    In-memory cache for storing NewsItem objects with TTL support.
    
    Attributes:
        _cache (Dict[str, Dict]): Internal cache storage
        _ttl (timedelta): Time-to-live for cache entries
    """
    def __init__(self, ttl_hours: Optional[int] = None):
        """
        Initialize cache with TTL from config or default.
        
        Args:
            ttl_hours: Number of hours entries should remain valid.
                If None, uses value from CacheConfig.
        """
        from config import CacheConfig
        
        self._cache: Dict[str, Dict] = {}
        self._ttl = timedelta(
            hours=ttl_hours if ttl_hours is not None 
            else CacheConfig.news_ttl_hours
        )

    def exists(self, news_id: str) -> bool:
        """Check if a news item exists in cache."""
        self._clean_expired()
        return news_id in self._cache

    def store(self, item: NewsItem) -> None:
        """Store a NewsItem in cache."""
        self._cache[item.url] = {
            'item': item,
            'expires_at': datetime.now() + self._ttl
        }

    def retrieve(self, news_id: str) -> Optional[NewsItem]:
        """Retrieve a NewsItem from cache if it exists and is not expired."""
        self._clean_expired()
        if news_id in self._cache:
            return self._cache[news_id]['item']
        return None

    def _clean_expired(self) -> None:
        """Remove expired entries from cache."""
        now = datetime.now()
        expired_keys = [
            k for k, v in self._cache.items() 
            if v['expires_at'] < now
        ]
        for key in expired_keys:
            del self._cache[key]

    def get_all_valid(self) -> List[NewsItem]:
        """Get all non-expired news items from cache."""
        self._clean_expired()
        return [v['item'] for v in self._cache.values()]
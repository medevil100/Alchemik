from typing import Optional
from datetime import timedelta


class CacheConfig:
    """
    Configuration class for cache settings.
    
    Attributes:
        news_ttl_hours (Optional[int]): Time-to-live for news cache entries in hours.
            If not provided, defaults to 24 hours.
    """
    news_ttl_hours: Optional[int] = 24

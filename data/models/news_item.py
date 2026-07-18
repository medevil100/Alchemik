from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class NewsItem:
    """
    Represents a single news item related to a financial instrument.
    
    Attributes:
        title (str): Headline of the news
        source (str): News source/publisher
        publish_date (datetime): When the news was published
        url (str): Link to full article
        summary (Optional[str]): Brief summary of the content
        sentiment (Optional[float]): Sentiment score (-1 to 1) if available
    """
    title: str
    source: str
    publish_date: datetime
    url: str
    summary: Optional[str] = None
    sentiment: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create NewsItem from a dictionary (for potential API responses)."""
        return cls(
            title=data['title'],
            source=data['source'],
            publish_date=datetime.fromisoformat(data['publish_date']),
            url=data['url'],
            summary=data.get('summary'),
            sentiment=data.get('sentiment')
        )
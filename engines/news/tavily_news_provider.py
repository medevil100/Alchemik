"""
Tavily News Provider implementation for the ALCHEMIK project.

This module handles communication with the Tavily API to fetch financial news.
"""

import requests
from typing import List, Optional
from datetime import datetime

from data.models.news_item import NewsItem


class TavilyNewsProvider:
    """
    Fetches news from the Tavily API and converts them to NewsItem objects.
    
    Attributes:
        api_key (str): Tavily API key
        base_url (str): Tavily API base URL
    """

    def __init__(self, api_key: str):
        """Initialize with Tavily API key."""
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"

    def fetch_news(self, query: str, max_results: int = 10) -> List[NewsItem]:
        """
        Fetch news from Tavily based on a query.
        
        Args:
            query (str): Search query for news
            max_results (int): Maximum number of results to return
            
        Returns:
            List[NewsItem]: List of news items
            
        Raises:
            requests.exceptions.RequestException: If API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/news",
                params={
                    "q": query,
                    "limit": max_results,
                    "api_key": self.api_key
                }
            )
            response.raise_for_status()
            
            news_data = response.json()
            return [
                NewsItem(
                    title=item["title"],
                    source=item["source"],
                    publish_date=datetime.fromisoformat(item["publish_date"]),
                    url=item["url"],
                    summary=item.get("summary")
                )
                for item in news_data.get("results", [])
            ]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch news from Tavily: {e}") from e
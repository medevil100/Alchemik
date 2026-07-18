from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from data.models.company_info import CompanyInfo
from data.models.market_data import MarketData
from data.models.news_item import NewsItem
from data.models.ai_signal import AISignal

@dataclass
class AnalysisResult:
    """
    Represents a complete analysis result for a financial instrument.
    
    Attributes:
        company (CompanyInfo): Company information
        market_data (List[MarketData]): Market data for the instrument
        news (List[NewsItem]): Relevant news items
        signals (List[AISignal]): AI-generated signals
        generated_at (datetime): When this analysis was performed
    """
    company: CompanyInfo
    market_data: List[MarketData]
    news: List[NewsItem]
    signals: List[AISignal]
    generated_at: datetime

    @classmethod
    def from_dict(cls, data: dict):
        """Create AnalysisResult from a dictionary (for potential API responses)."""
        from data.models.company_info import CompanyInfo
        from data.models.market_data import MarketData
        from data.models.news_item import NewsItem
        from data.models.ai_signal import AISignal
        
        return cls(
            company=CompanyInfo.from_dict(data['company']),
            market_data=[MarketData.from_dict(md) for md in data['market_data']],
            news=[NewsItem.from_dict(n) for n in data['news']],
            signals=[AISignal.from_dict(s) for s in data['signals']],
            generated_at=datetime.fromisoformat(data['generated_at'])
        )

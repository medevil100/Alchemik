from dataclasses import dataclass
from typing import Optional

@dataclass
class CompanyInfo:
    """
    Represents information about a financial instrument (company, ETF, etc.).
    
    Attributes:
        name (str): Full name of the instrument
        symbol (str): Ticker symbol
        sector (Optional[str]): Industry sector (if applicable)
        country (Optional[str]): Country of origin (if applicable)
        description (Optional[str]): Brief description of the company
        exchange (Optional[str]): Primary exchange where traded
    """
    name: str
    symbol: str
    sector: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    exchange: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create CompanyInfo from a dictionary (for potential API responses)."""
        return cls(
            name=data['name'],
            symbol=data['symbol'],
            sector=data.get('sector'),
            country=data.get('country'),
            description=data.get('description'),
            exchange=data.get('exchange')
        )
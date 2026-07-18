from typing import List
from application.universe import InstrumentSource

class StaticInstrumentSource(InstrumentSource):
    """A static implementation of InstrumentSource for controlled testing.
    
    Args:
        tickers: A list of tickers to be used as the instrument source.
    """
    def __init__(self, tickers: List[str]):
        self._tickers = self._validate_and_deduplicate(tickers)
    
    def get_instruments(self) -> List[str]:
        """Return the list of validated and deduplicated tickers."""
        return self._tickers
    
    def _validate_and_deduplicate(self, tickers: List[str]) -> List[str]:
        """Validate and deduplicate the provided tickers.
        
        Args:
            tickers: List of tickers to validate and deduplicate.
            
        Returns:
            A validated and deduplicated list of tickers.
            
        Raises:
            ValueError: If any ticker is empty or invalid.
        """
        if not tickers:
            raise ValueError("Tickers list cannot be empty")
            
        validated_tickers = []
        seen = set()
        
        for ticker in tickers:
            if not ticker or not isinstance(ticker, str):
                raise ValueError(f"Invalid ticker: {ticker}")
            if ticker not in seen:
                seen.add(ticker)
                validated_tickers.append(ticker)
        
        return validated_tickers
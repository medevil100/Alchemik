from typing import List, Dict, Optional, Union
from data.yahoo.yahoo_fetcher import YahooFetcher
from application.market_scanner import ScanProvider
from data.models.market_data import MarketData

class YahooScanProvider(ScanProvider):
    """An adapter that uses YahooFetcher to implement the ScanProvider protocol.
    
    Args:
        fetcher: An instance of YahooFetcher to use for data fetching.
    """
    def __init__(self, fetcher: YahooFetcher):
        self._fetcher = fetcher
    
    def scan(self, instruments: List[str]) -> List[Dict[str, Union[str, List[MarketData]]]]:
        """Scan instruments using YahooFetcher and return market data.
        
        Args:
            instruments: List of instrument tickers to scan.
            
        Returns:
            A list of dictionaries containing market data for each instrument.
            Each dictionary contains:
            - 'symbol': The instrument ticker
            - 'data': List[MarketData] with full history
            Failed scans are omitted from results but don't stop execution.
        """
        results = []
        
        for symbol in instruments:
            try:
                data = self._fetcher.fetch_stock_data(symbol)
                results.append({
                    'symbol': symbol,
                    'data': data
                })
            except Exception as e:
                # Log error but continue with next symbol
                print(f"Failed to scan {symbol}: {e}")
        
        return results

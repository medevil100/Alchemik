from typing import List, Protocol
from application.universe import PennyStockUniverse

class ScanProvider(Protocol):
    """Interface for scan providers."""
    def scan(self, instruments: List[str]) -> List[str]:
        """Return a list of candidate instruments.
        
        Args:
            instruments: List of instruments to scan.
            
        Returns:
            List of candidate instruments.
        """
        ...

class MarketScanner:
    """Scans instruments from Universe using a provided ScanProvider.
    
    Args:
        universe: An instance of PennyStockUniverse.
        provider: An object implementing the ScanProvider protocol.
    """
    def __init__(self, universe: PennyStockUniverse, provider: ScanProvider):
        self._universe = universe
        self._provider = provider
    
    def scan(self) -> List[dict]:
        """Scan instruments and return candidates.
        
        Returns:
            List of candidate instruments with their data.
        """
        instruments = self._universe.get_universe()
        scan_results = self._provider.scan(instruments)
        return scan_results

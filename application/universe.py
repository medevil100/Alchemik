from typing import List, Protocol

class InstrumentSource(Protocol):
    """Interface for instrument sources."""
    def get_instruments(self) -> List[str]:
        """Return a list of instruments."""
        ...

class PennyStockUniverse:
    """Manages the list of instruments to be observed by ALCHEMIK.

    Args:
        source: An object implementing the InstrumentSource protocol.
    """
    def __init__(self, source: InstrumentSource):
        self._source = source

    def get_universe(self) -> List[str]:
        """Return the list of instruments to be scanned.

        Returns:
            A list of instrument tickers.
        """
        instruments = self._source.get_instruments()
        return list(dict.fromkeys(instruments))  # Remove duplicates while preserving order

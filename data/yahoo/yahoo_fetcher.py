"""
Yahoo Finance Data Fetcher Module

This module is responsible for fetching financial data from Yahoo Finance.
It adheres to Clean Code principles and Single Responsibility Principle.
"""

import yfinance as yf
import time
from typing import Dict, List, Union
from .yahoo_exceptions import YahooFinanceError, InvalidSymbolError, RateLimitExceededError
from data.models.market_data import MarketData

class YahooFetcher:
    """
    A class to fetch data from Yahoo Finance.

    Methods:
        fetch_stock_data: Fetches stock data for a given symbol.
    """

    def __init__(self, ticker_factory=None, sleep_func=None):
        """
        Initialize the YahooFetcher with optional dependency injection.

        Args:
            ticker_factory (callable): Optional factory function to create yfinance.Ticker objects (for testing).
            sleep_func (callable): Optional function to use for sleeping (for testing).
        """
        self._ticker_factory = ticker_factory or yf.Ticker
        self._sleep_func = sleep_func or time.sleep

    def fetch_stock_data(self, symbol: str) -> List[MarketData]:
        """
        Fetch stock data for a given symbol.

        Args:
            symbol (str): The stock symbol to fetch data for.

        Returns:
            List[MarketData]: A list of MarketData objects containing the full history.

        Raises:
            InvalidSymbolError: If the symbol is invalid or no data is available.
            RateLimitExceededError: If Yahoo Finance API rate limit is exceeded.
            YahooFinanceError: For other Yahoo Finance API errors.
        """
        try:
            ticker = self._ticker_factory(symbol)
            try:
                history = ticker.history(period="260d")
            except Exception as e:
                if "too many requests" in str(e).lower():
                    raise RateLimitExceededError("Yahoo Finance API rate limit exceeded")
                elif "symbol may be delisted" in str(e).lower():
                    raise InvalidSymbolError(f"Invalid stock symbol: {symbol}")
                raise

            if history.empty:
                raise InvalidSymbolError(f"No data available for symbol: {symbol}")
            
            # Convert DataFrame to List[MarketData]
            market_data_list = []
            for timestamp, row in history.iterrows():
                market_data_list.append(
                    MarketData(
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=float(row["Volume"]),
                        timestamp=timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp
                    )
                )
            
            return market_data_list
        except (InvalidSymbolError, RateLimitExceededError):
            raise
        except Exception as e:
            raise YahooFinanceError(f"Failed to fetch data for symbol {symbol}: {e}")

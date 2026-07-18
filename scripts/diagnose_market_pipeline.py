import traceback
from typing import List, Dict, Optional
from application.sources.static_instrument_source import StaticInstrumentSource
from application.universe import PennyStockUniverse
from data.yahoo.yahoo_fetcher import YahooFetcher
from application.providers.yahoo_scan_provider import YahooScanProvider
from application.market_scanner import MarketScanner
from engines.hunter.engine import HunterEngine


def diagnose():
    # Initialize dependencies
    tickers = ["AAPL"]
    source = StaticInstrumentSource(tickers)
    universe = PennyStockUniverse(source)
    fetcher = YahooFetcher()
    provider = YahooScanProvider(fetcher)
    scanner = MarketScanner(universe, provider)
    hunter = HunterEngine({
        'min_price': 1.0,
        'max_price': 100.0,
        'min_volume': 100000,
        'min_market_cap': 100000000
    })

    # Step 1: StaticInstrumentSource
    try:
        print("\n--- StaticInstrumentSource ---")
        instruments = source.get_instruments()
        print(f"Result type: {type(instruments)}")
        if isinstance(instruments, list):
            print(f"Length: {len(instruments)}")
            if instruments:
                print(f"First item type: {type(instruments[0])}")
    except Exception:
        traceback.print_exc()

    # Step 2: PennyStockUniverse
    try:
        print("\n--- PennyStockUniverse ---")
        universe_result = universe.get_universe()
        print(f"Result type: {type(universe_result)}")
        if isinstance(universe_result, list):
            print(f"Length: {len(universe_result)}")
            if universe_result:
                print(f"First item type: {type(universe_result[0])}")
    except Exception:
        traceback.print_exc()

    # Step 3: YahooFetcher
    try:
        print("\n--- YahooFetcher ---")
        yahoo_result = fetcher.fetch_stock_data("AAPL")
        print(f"Result type: {type(yahoo_result)}")
        if isinstance(yahoo_result, dict):
            print(f"Keys: {list(yahoo_result.keys())}")
    except Exception:
        traceback.print_exc()

    # Step 4: YahooScanProvider
    try:
        print("\n--- YahooScanProvider ---")
        provider_result = provider.scan(["AAPL"])
        print(f"Result type: {type(provider_result)}")
        if isinstance(provider_result, list):
            print(f"Length: {len(provider_result)}")
            if provider_result:
                print(f"First item type: {type(provider_result[0])}")
                if isinstance(provider_result[0], dict):
                    print(f"Keys: {list(provider_result[0].keys())}")
    except Exception:
        traceback.print_exc()

    # Step 5: MarketScanner
    try:
        print("\n--- MarketScanner ---")
        scanner_result = scanner.scan()
        print(f"Result type: {type(scanner_result)}")
        if isinstance(scanner_result, list):
            print(f"Length: {len(scanner_result)}")
            if scanner_result:
                print(f"First item type: {type(scanner_result[0])}")
                if isinstance(scanner_result[0], dict):
                    print(f"Keys: {list(scanner_result[0].keys())}")
    except Exception:
        traceback.print_exc()

    # Step 6: HunterEngine
    try:
        print("\n--- HunterEngine ---")
        hunter_result = hunter.scan({"candidates": [{"symbol": "AAPL"}]})
        print(f"Result type: {type(hunter_result)}")
        if hasattr(hunter_result, "opportunities"):
            print(f"Opportunities length: {len(hunter_result.opportunities)}")
            if hunter_result.opportunities:
                print(f"First opportunity type: {type(hunter_result.opportunities[0])}")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
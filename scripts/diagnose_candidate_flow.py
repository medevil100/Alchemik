import sys
from application.sources.static_instrument_source import StaticInstrumentSource
from application.universe import PennyStockUniverse
from data.yahoo.yahoo_fetcher import YahooFetcher
from application.providers.yahoo_scan_provider import YahooScanProvider
from application.market_scanner import MarketScanner
from engines.hunter.engine import HunterEngine
import config.hunter

def diagnose_ticker(ticker):
    print(f"==== Diagnosing {ticker} ====")
    
    # 1. Create StaticInstrumentSource and PennyStockUniverse
    source = StaticInstrumentSource([ticker])
    universe = PennyStockUniverse(source)
    
    # 2. Create YahooFetcher and YahooScanProvider
    fetcher = YahooFetcher()
    provider = YahooScanProvider(fetcher)
    
    # 3. Create MarketScanner and scan
    scanner = MarketScanner(universe, provider)
    scanner_result = scanner.scan()
    
    # 4. Check if scan was successful
    scan_ok = scanner_result is not None and len(scanner_result) > 0
    print(f"1. Fetch/Provider OK: {scan_ok}")
    if scan_ok:
        first_record = scanner_result[0]
        print(f"   Provider result type: {type(first_record)}")
        print(f"   Keys in first record: {list(first_record.keys())}")
        print(f"   Ranking score: {first_record.get('ranking_score', 'N/A')}")
        print(f"   Risk score: {first_record.get('risk_score', 'N/A')}")
        print(f"   Confidence: {first_record.get('confidence', 'N/A')}")
    
    # 5. HunterEngine evaluation
    hunter = HunterEngine(config=config.hunter.HUNTER_CONFIG)
    hunter_result = hunter.scan(scanner_result) if scan_ok else None
    hunter_ok = hunter_result and len(hunter_result.opportunities) > 0
    print(f"2. HunterEngine result: {'PASSED' if hunter_ok else 'REJECTED'}")
    
    if not hunter_ok and scan_ok:
        print(f"   Rejection reason: {hunter_result.rejection_reason if hasattr(hunter_result, 'rejection_reason') else 'Unknown'}")
    
    # Prepare summary row
    return {
        "ticker": ticker,
        "fetch_ok": scan_ok,
        "provider_ok": scan_ok,
        "ranking_score": first_record.get('ranking_score', 0) if scan_ok else 0,
        "risk_score": first_record.get('risk_score', 0) if scan_ok else 0,
        "confidence": first_record.get('confidence', 0) if scan_ok else 0,
        "hunter_result": "PASS" if hunter_ok else "REJECT",
        "rejection_reason": hunter_result.rejection_reason if not hunter_ok and hasattr(hunter_result, 'rejection_reason') else "N/A"
    }

if __name__ == "__main__":
    tickers = ["CDR.WA", "11B.WA", "AAPL", "MSFT"]
    results = []
    
    for ticker in tickers:
        results.append(diagnose_ticker(ticker))
    
    # Print summary table
    print("\n==== SUMMARY TABLE ====")
    print(f"{'Ticker':<8} | {'Fetch OK':<8} | {'Provider OK':<10} | {'ranking_score':<13} | {'risk_score':<10} | {'confidence':<10} | {'Hunter result':<12} | {'Rejection reason'}")
    print("-" * 100)
    for result in results:
        print(f"{result['ticker']:<8} | {str(result['fetch_ok']):<8} | {str(result['provider_ok']):<10} | {result['ranking_score']:<13} | {result['risk_score']:<10} | {result['confidence']:<10} | {result['hunter_result']:<12} | {result['rejection_reason']}")

import sys
from data.yahoo.yahoo_fetcher import YahooFetcher

def main():
    try:
        # 1. Create YahooFetcher
        fetcher = YahooFetcher()
        
        # 2. Fetch AAPL data
        response = fetcher.fetch_stock_data('AAPL')
        
        # 3. Print diagnostic info
        print(f"Symbol: AAPL")
        print(f"Result type: {type(response).__name__}")
        print(f"Number of candles: {len(response)}")
        
        if len(response) > 0:
            first = response[0]
            last = response[-1]
            print(f"First candle type: {type(first).__name__}")
            print(f"First timestamp: {first.timestamp}")
            print(f"Last candle type: {type(last).__name__}")
            print(f"Last timestamp: {last.timestamp}")
        else:
            print("No data returned")
        
    except Exception as e:
        print(f"Type: Exception ({type(e).__name__})")
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            print(f"HTTP Status: {e.response.status_code}")
            print(f"Retry-After: {e.response.headers.get('Retry-After', 'N/A')}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
import os

import requests
from dotenv import load_dotenv

load_dotenv()
import json

import os
import json
from datetime import datetime, timedelta
import pandas as pd
try:
    from nselib import capital_market as nse_cm
    HAS_NSELIB = True
except ImportError:
    HAS_NSELIB = False

all_nifty_50_symbols = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL",
    "INFY", "ITC", "SBIN", "LICI", "HINDUNILVR",
    "LT", "HCLTECH", "BAJFINANCE", "SUNPHARMA", "MARUTI",
    "ADANIENT", "KOTAKBANK", "TITAN", "ULTRACEMCO", "AXISBANK",
    "NTPC", "ADANIPORTS", "ASIANPAINT", "ONGC", "POWERGRID",
    "COALINDIA", "TATASTEEL", "M&M", "JIOFIN", "HAL",
    "JSWSTEEL", "TATAMOTORS", "APOLLOHOSP", "BAJAJ-AUTO", "BAJAJFINSV",
    "BPCL", "CIPLA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "GRASIM", "HEROMOTOCO", "INDUSINDBK", "LTIM", "NESTLEIND",
    "SHREECEM", "TECHM", "WIPRO", "HINDALCO", "BRITANNIA"
]

def get_daily_price_nse(SYMBOL: str):
    if not HAS_NSELIB:
        print("nselib not installed.")
        return

    print(f"Fetching historical data for {SYMBOL}...")
    try:
        # Fetch last 2 years of data
        end_date = datetime.now().strftime("%d-%m-%Y")
        start_date = (datetime.now() - timedelta(days=730)).strftime("%d-%m-%Y")
        
        df = nse_cm.price_volume_data(SYMBOL, start_date, end_date)
        
        if df is None or df.empty:
            print(f"No data for {SYMBOL}")
            return

        # Convert to Alpha Vantage-like format for the merger to work
        # Alpha Vantage uses "Time Series (Daily)"
        time_series = {}
        for _, row in df.iterrows():
            date_str = pd.to_datetime(row['Date']).strftime("%Y-%m-%d")
            time_series[date_str] = {
                "1. open": str(row['OpenPrice']),
                "2. high": str(row['HighPrice']),
                "3. low": str(row['LowPrice']),
                "4. close": str(row['ClosePrice']),
                "5. volume": str(row['TotalTradedQuantity'])
            }
        
        data = {
            "Meta Data": {
                "1. Information": "Daily Prices (open, high, low, close) and Volumes",
                "2. Symbol": SYMBOL,
                "3. Last Refreshed": end_date
            },
            "Time Series (Daily)": time_series
        }
        
        output_path = os.path.join(os.path.dirname(__file__), f"daily_prices_{SYMBOL}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"Error fetching {SYMBOL}: {e}")

if __name__ == "__main__":
    for symbol in all_nifty_50_symbols:
        get_daily_price_nse(symbol)

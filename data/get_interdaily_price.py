import os

import requests
from dotenv import load_dotenv

load_dotenv()
import json

all_nifty_50_symbols = [
    "RELIANCE.BSE", "TCS.BSE", "HDFCBANK.BSE", "ICICIBANK.BSE", "BHARTIARTL.BSE",
    "INFY.BSE", "ITC.BSE", "SBIN.BSE", "LICI.BSE", "HINDUNILVR.BSE",
    "LT.BSE", "HCLTECH.BSE", "BAJFINANCE.BSE", "SUNPHARMA.BSE", "MARUTI.BSE",
    "ADANIENT.BSE", "KOTAKBANK.BSE", "TITAN.BSE", "ULTRACEMCO.BSE", "AXISBANK.BSE",
    "NTPC.BSE", "ADANIPORTS.BSE", "ASIANPAINT.BSE", "ONGC.BSE", "POWERGRID.BSE",
    "COALINDIA.BSE", "TATASTEEL.BSE", "M&M.BSE", "JIOFIN.BSE", "HAL.BSE",
    "JSWSTEEL.BSE", "TATAMOTORS.BSE", "APOLLOHOSP.BSE", "BAJAJ-AUTO.BSE", "BAJAJFINSV.BSE",
    "BPCL.BSE", "CIPLA.BSE", "DIVISLAB.BSE", "DRREDDY.BSE", "EICHERMOT.BSE",
    "GRASIM.BSE", "HEROMOTOCO.BSE", "INDUSINDBK.BSE", "LTIM.BSE", "NESTLEIND.BSE",
    "SHREECEM.BSE", "TECHM.BSE", "WIPRO.BSE", "HINDALCO.BSE", "BRITANNIA.BSE"
]


def update_json(data: dict, SYMBOL: str):
    clean_sym = SYMBOL.split('.')[0]
    file_path = f'./daily_prices_{clean_sym}.json'
    
    try:
        new_ts_key = "Time Series (60min)"
        if new_ts_key not in data:
            print(f"Skipping {SYMBOL} as it has no {new_ts_key}")
            return

        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            old_ts = old_data.get(new_ts_key, {})
            new_ts = data.get(new_ts_key, {})
            merged_ts = {**old_ts, **new_ts}
            
            merged_data = data.copy()
            merged_data[new_ts_key] = merged_ts
            
            if "Meta Data" not in merged_data and "Meta Data" in old_data:
                merged_data["Meta Data"] = old_data["Meta Data"]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                    
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"Error when update {SYMBOL}: {e}")
        raise


def get_daily_price(SYMBOL: str):
    FUNCTION = "TIME_SERIES_INTRADAY"
    INTERVAL = "60min"
    OUTPUTSIZE = 'full'
    APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
    url = f'https://www.alphavantage.co/query?function={FUNCTION}&symbol={SYMBOL}&interval={INTERVAL}&outputsize={OUTPUTSIZE}&apikey={APIKEY}'
    r = requests.get(url)
    data = r.json()
    print(f"Fetching {SYMBOL} intraday...")
    if data.get("Note") is not None or data.get("Information") is not None:
        print(f"Error fetching {SYMBOL}: Limit reached or invalid.")
        return
    update_json(data, SYMBOL)


if __name__ == "__main__":
    for symbol in all_nifty_50_symbols:
        get_daily_price(symbol)

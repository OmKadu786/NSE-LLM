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


def get_daily_price(SYMBOL: str):
    FUNCTION = "TIME_SERIES_DAILY"
    OUTPUTSIZE = "full"
    APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
    url = (
        f"https://www.alphavantage.co/query?function={FUNCTION}&symbol={SYMBOL}&outputsize={OUTPUTSIZE}&apikey={APIKEY}"
    )
    r = requests.get(url)
    data = r.json()
    print(f"Fetching {SYMBOL}...")
    if data.get("Note") is not None or data.get("Information") is not None:
        print(f"Error fetching {SYMBOL}: Limit reached or invalid.")
        return
    # Use clean symbol for filename (remove suffix)
    clean_sym = SYMBOL.split('.')[0]
    with open(f"./daily_prices_{clean_sym}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    for symbol in all_nifty_50_symbols:
        get_daily_price(symbol)

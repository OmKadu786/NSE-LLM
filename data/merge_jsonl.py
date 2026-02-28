import glob
import json
import os

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

# 合并所有以 daily_prices_ 开头的 json，逐文件一行写入 merged_in.jsonl
current_dir = os.path.dirname(__file__)
pattern = os.path.join(current_dir, "daily_prices_*.json")
files = sorted(glob.glob(pattern))

output_file = os.path.join(current_dir, "merged_in.jsonl")

with open(output_file, "w", encoding="utf-8") as fout:
    for fp in files:
        basename = os.path.basename(fp)
        # 仅当文件名包含任一 Nifty 50 成分符号时才写入
        if not any(symbol in basename for symbol in all_nifty_50_symbols):
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        try:
            # 查找所有以 "Time Series" 开头的键 (支持 60min 和 Daily)
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            if isinstance(series, dict) and series:
                # 统一重命名："1. open" -> "1. buy price"；"4. close" -> "4. sell price"
                for d, bar in list(series.items()):
                    if not isinstance(bar, dict):
                        continue
                    if "1. open" in bar:
                        bar["1. buy price"] = bar.pop("1. open")
                    if "4. close" in bar:
                        bar["4. sell price"] = bar.pop("4. close")
                
                # 更新 Meta Data 描述
                meta = data.get("Meta Data", {})
                if isinstance(meta, dict):
                    meta["1. Information"] = "Equities Prices (buy price, high, low, sell price) and Volumes"
        except Exception:
            pass

        fout.write(json.dumps(data, ensure_ascii=False) + "\n")

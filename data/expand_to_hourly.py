import json
import os
from datetime import datetime

def clean_float(val):
    if val is None: return 0.0
    if isinstance(val, float) or isinstance(val, int): return float(val)
    return float(str(val).replace(',', '').strip())

def expand_daily_to_hourly(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(output_file, 'w', encoding='utf-8') as f:
        for line in lines:
            if not line.strip():
                continue
            data = json.loads(line)
            meta = data.get("Meta Data", {})
            symbol = meta.get("2. Symbol")
            
            daily_series = data.get("Time Series (Daily)", {})
            if not daily_series:
                 if "Time Series (60min)" in data:
                     f.write(json.dumps(data) + '\n')
                     continue
            
            hourly_series = {}
            for date_str, daily_data in daily_series.items():
                try:
                    open_p = clean_float(daily_data.get("1. buy price", 0))
                    high_p = clean_float(daily_data.get("2. high", 0))
                    low_p = clean_float(daily_data.get("3. low", 0))
                    close_p = clean_float(daily_data.get("4. sell price", 0))
                    # Handle volume comma if not handled by clean_float
                    vol_str = str(daily_data.get("5. volume", "0")).replace(',', '')
                    vol = int(float(vol_str))
                except Exception as e:
                    # print(f"Skipping {date_str} due to {e}")
                    continue
                
                # Market hours: 9:15 AM to 3:30 PM (7 samples)
                hours = ["09:15:00", "10:15:00", "11:15:00", "12:15:00", "13:15:00", "14:15:00", "15:15:00"]
                for i, h in enumerate(hours):
                    timestamp = f"{date_str} {h}"
                    p_val = open_p
                    if i == 0: p_val = open_p
                    elif i == 1: p_val = high_p
                    elif i == 2: p_val = low_p
                    elif i == 3: p_val = (high_p + low_p) / 2
                    elif i == 6: p_val = close_p
                    else: p_val = (open_p + close_p) / 2
                    
                    hourly_series[timestamp] = {
                        "1. buy price": str(round(p_val, 2)),
                        "2. high": str(round(high_p, 2)),
                        "3. low": str(round(low_p, 2)),
                        "4. sell price": str(round(p_val, 2)),
                        "5. volume": str(vol // 7)
                    }

            new_doc = {
                "Meta Data": meta,
                "Time Series (60min)": hourly_series
            }
            new_doc["Meta Data"]["1. Information"] = "Equities Prices (buy price, high, low, sell price) and Volumes (60min simulated)"
            
            f.write(json.dumps(new_doc, ensure_ascii=False) + '\n')

if __name__ == "__main__":
    expand_daily_to_hourly('data/merged_in_daily.jsonl', 'data/merged_in_hourly.jsonl')
    print("Regenerated data/merged_in_hourly.jsonl with comma cleaning.")

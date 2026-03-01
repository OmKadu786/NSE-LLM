import os

from dotenv import load_dotenv

load_dotenv()
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 将项目根目录加入 Python 路径，便于从子目录直接运行本文件
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from tools.general_tools import get_config_value

try:
    from nsepython import nse_quote_ltp
    HAS_NSEPYTHON = True
except ImportError:
    HAS_NSEPYTHON = False

def _normalize_timestamp_str(ts: str) -> str:
    """
    Normalize timestamp string to zero-padded HH for robust string/chrono comparisons.
    - If ts has time part like 'YYYY-MM-DD H:MM:SS', pad hour to 'HH'.
    - If ts is date-only, return as-is.
    """
    try:
        if " " not in ts:
            return ts
        date_part, time_part = ts.split(" ", 1)
        parts = time_part.split(":")
        if len(parts) != 3:
            return ts
        hour, minute, second = parts
        hour = hour.zfill(2)
        return f"{date_part} {hour}:{minute}:{second}"
    except Exception:
        return ts

def _parse_timestamp_to_dt(ts: str) -> datetime:
    """
    Parse timestamp string to datetime, supporting both date-only and datetime.
    Assumes ts is already normalized if time exists.
    """
    if " " in ts:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    return datetime.strptime(ts, "%Y-%m-%d")


def get_market_type() -> str:
    """
    Returns the current market type (in/us/cn) from the MARKET environment variable.
    """
    return get_config_value("MARKET", "us").lower()


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

all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "NFLX",
    "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN", "PEP",
    "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG",
    "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
    "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS", "ORLY", "SNPS",
    "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI", "MAR", "MNST", "CSX", "ADSK",
    "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST",
    "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
    "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP", "GEHC", "VRSK",
    "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD", "ON", "BIIB", "LULU", "CDW", "GFS"
]

all_sse_50_symbols = [
    "600519.SH", "601318.SH", "600036.SH", "601899.SH", "600900.SH", "601166.SH", "600276.SH", "600030.SH", "603259.SH", "688981.SH",
    "688256.SH", "601398.SH", "688041.SH", "601211.SH", "601288.SH", "601328.SH", "688008.SH", "600887.SH", "600150.SH", "601816.SH",
    "601127.SH", "600031.SH", "688012.SH", "603501.SH", "601088.SH", "600309.SH", "601601.SH", "601668.SH", "603993.SH", "601012.SH",
    "601728.SH", "600690.SH", "600809.SH", "600941.SH", "600406.SH", "601857.SH", "601766.SH", "601919.SH", "600050.SH", "600760.SH",
    "601225.SH", "600028.SH", "601988.SH", "688111.SH", "601985.SH", "601888.SH", "601628.SH", "601600.SH", "601658.SH", "600048.SH"
]



def get_merged_file_path(market: str = "us") -> Path:
    """Get merged.jsonl path for the given market."""
    base_dir = Path(__file__).resolve().parents[1]
    if market == "in":
        return base_dir / "data" / "merged_in.jsonl"
    return base_dir / "data" / "merged.jsonl"

def _resolve_merged_file_path_for_date(
    today_date: Optional[str], market: str, merged_path: Optional[str] = None
) -> Path:
    """Returns the market-specific merged.jsonl path."""
    return get_merged_file_path(market)


def is_trading_day(date: str, market: str = "us") -> bool:
    """Check if a given date is a trading day by looking up merged.jsonl.

    Args:
        date: Date string in "YYYY-MM-DD" format
        market: Market type ("us", "cn", or "crypto")

    Returns:
        True if the date exists in merged.jsonl (is a trading day), False otherwise
    """
    # MVP assumption: crypto trades every day, but the date should not be neither in the future nor no any data yet.
    # if market == "crypto":
    #     # Parse input date/time and compare real-world time (to the minute).
    #     # If input has no time part, default to 00:00. Supported formats:
    #     #   "YYYY-MM-DD", "YYYY-MM-DD HH:MM", "YYYY-MM-DD HH:MM:SS"
    #     fmt_candidates = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    #     input_dt = None
    #     for fmt in fmt_candidates:
    #         try:
    #             input_dt = datetime.strptime(date, fmt)
    #             break
    #         except Exception:
    #             continue
    #     if input_dt is None:
    #         # Unable to parse input date -> treat as not a trading day
    #         return False

    #     # Normalize to minute precision (ignore seconds/microseconds)
    #     input_dt = input_dt.replace(second=0, microsecond=0)
    #     now_minute = datetime.now().replace(second=0, microsecond=0)

    #     # If current real-world time is earlier than the requested time, it's future -> return False
    #     if now_minute < input_dt:
    #         return False
    #     return True

    merged_file_path = get_merged_file_path(market)

    if not merged_file_path.exists():
        print(f"⚠️  Warning: {merged_file_path} not found, cannot validate trading day")
        return False

    try:
        with open(merged_file_path, "r", encoding="utf-8") as f:
            # Read first line to check if date exists
            for line in f:
                try:
                    data = json.loads(line.strip())
                    # Check for daily time series first
                    time_series = data.get("Time Series (Daily)", {})
                    if date in time_series:
                        return True

                    # If no daily data, check for hourly data (e.g., "Time Series (60min)")
                    for key, value in data.items():
                        if key.startswith("Time Series") and isinstance(value, dict):
                            # Check if any hourly timestamp starts with the date
                            for timestamp in value.keys():
                                if timestamp.startswith(date):
                                    return True
                except json.JSONDecodeError:
                    continue
            # If we get here, checked all stocks and date was not found in any
            return False
    except Exception as e:
        print(f"⚠️  Error checking trading day: {e}")
        return False


def get_all_trading_days(market: str = "us") -> List[str]:
    """Get all available trading days from merged.jsonl.

    Args:
        market: Market type ("us" or "cn")

    Returns:
        Sorted list of trading dates in "YYYY-MM-DD" format
    """
    merged_file_path = get_merged_file_path(market)

    if not merged_file_path.exists():
        print(f"⚠️  Warning: {merged_file_path} not found")
        return []

    trading_days = set()
    try:
        with open(merged_file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    time_series = data.get("Time Series (Daily)", {})
                    # Add all dates from this stock's time series
                    trading_days.update(time_series.keys())
                except json.JSONDecodeError:
                    continue
        return sorted(list(trading_days))
    except Exception as e:
        print(f"⚠️  Error reading trading days: {e}")
        return []


def get_stock_name_mapping(market: str = "us") -> Dict[str, str]:
    """Get mapping from stock symbols to names.

    Args:
        market: Market type ("us" or "cn")

    Returns:
        Dictionary mapping symbols to names, e.g. {"600519.SH": "贵州茅台"}
    """
    merged_file_path = get_merged_file_path(market)

    if not merged_file_path.exists():
        return {}

    name_map = {}
    try:
        with open(merged_file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    meta = data.get("Meta Data", {})
                    symbol = meta.get("2. Symbol")
                    name = meta.get("2.1. Name", "")
                    if symbol and name:
                        name_map[symbol] = name
                except json.JSONDecodeError:
                    continue
        return name_map
    except Exception as e:
        print(f"⚠️  Error reading stock names: {e}")
        return {}


def format_price_dict_with_names(
    price_dict: Dict[str, Optional[float]], market: str = "us"
) -> Dict[str, Optional[float]]:
    """Format price dictionary to include stock names for display.

    Args:
        price_dict: Original price dictionary with keys like "600519.SH_price"
        market: Market type ("us" or "cn")

    Returns:
        New dictionary with keys like "600519.SH (贵州茅台)_price" for CN market,
        unchanged for US market
    """
    if market != "cn":
        return price_dict

    name_map = get_stock_name_mapping(market)
    if not name_map:
        return price_dict

    formatted_dict = {}
    for key, value in price_dict.items():
        if key.endswith("_price"):
            symbol = key[:-6]  # Remove "_price" suffix
            stock_name = name_map.get(symbol, "")
            if stock_name:
                new_key = f"{symbol} ({stock_name})_price"
            else:
                new_key = key
            formatted_dict[new_key] = value
        else:
            formatted_dict[key] = value

    return formatted_dict


def get_yesterday_date(today_date: str, merged_path: Optional[str] = None, market: str = "us") -> str:
    """
    获取输入日期的上一个交易日或时间点。
    从 merged.jsonl 读取所有可用的交易时间，然后找到 today_date 的上一个时间。
    
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS。
        merged_path: 可选，自定义 merged.jsonl 路径；默认根据 market 参数读取对应市场的 merged.jsonl。
        market: 市场类型，"us" 为美股，"cn" 为A股

    Returns:
        yesterday_date: 上一个交易日或时间点的字符串，格式与输入一致。
    """
    # 解析输入日期/时间
    if ' ' in today_date:
        input_dt = datetime.strptime(today_date, "%Y-%m-%d %H:%M:%S")
        date_only = False
    else:
        input_dt = datetime.strptime(today_date, "%Y-%m-%d")
        date_only = True
    
    # 获取 merged.jsonl 文件路径
    merged_file = _resolve_merged_file_path_for_date(today_date, market, merged_path)
    
    if not merged_file.exists():
        # 如果文件不存在，根据输入类型回退
        print(f"merged.jsonl file does not exist at {merged_file}")
        if date_only:
            yesterday_dt = input_dt - timedelta(days=1)
            while yesterday_dt.weekday() >= 5:
                yesterday_dt -= timedelta(days=1)
            return yesterday_dt.strftime("%Y-%m-%d")
        else:
            yesterday_dt = input_dt - timedelta(hours=1)
            return yesterday_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 从 merged.jsonl 读取所有可用的交易时间
    all_timestamps = set()
    
    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                # 查找所有以 "Time Series" 开头的键
                for key, value in doc.items():
                    if key.startswith("Time Series"):
                        if isinstance(value, dict):
                            all_timestamps.update(value.keys())
                        break
            except Exception:
                continue
    
    if not all_timestamps:
        # 如果没有找到任何时间戳，根据输入类型回退
        if date_only:
            yesterday_dt = input_dt - timedelta(days=1)
            while yesterday_dt.weekday() >= 5:
                yesterday_dt -= timedelta(days=1)
            return yesterday_dt.strftime("%Y-%m-%d")
        else:
            yesterday_dt = input_dt - timedelta(hours=1)
            return yesterday_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 将所有时间戳转换为 datetime 对象，并找到小于 today_date 的最大时间戳
    previous_timestamp = None
    
    for ts_str in all_timestamps:
        try:
            ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            if ts_dt < input_dt:
                if previous_timestamp is None or ts_dt > previous_timestamp:
                    previous_timestamp = ts_dt
        except Exception:
            continue
    
    # 如果没有找到更早的时间戳，根据输入类型回退
    if previous_timestamp is None:
        if date_only:
            yesterday_dt = input_dt - timedelta(days=1)
            while yesterday_dt.weekday() >= 5:
                yesterday_dt -= timedelta(days=1)
            return yesterday_dt.strftime("%Y-%m-%d")
        else:
            yesterday_dt = input_dt - timedelta(hours=1)
            return yesterday_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 返回结果
    if date_only:
        return previous_timestamp.strftime("%Y-%m-%d")
    else:
        return previous_timestamp.strftime("%Y-%m-%d %H:%M:%S")



def get_open_prices(
    today_date: str, symbols: List[str], merged_path: Optional[str] = None, market: str = "us"
) -> Dict[str, Optional[float]]:
    """从 data/merged.jsonl 中读取指定日期与标的的开盘价。
    如果是 Indian 且是今天，尝试通过 nsepython 获取实时 ltp。
    """
    wanted = set(symbols)
    results: Dict[str, Optional[float]] = {}

    # 尝试通过 nsepython 获取实时 ltp (仅限今日且为印度市场)
    if HAS_NSEPYTHON and (market == "in" or market == "nse"):
        try:
            current_date_str = datetime.now().strftime("%Y-%m-%d")
            # 如果请求的是今天，则优先使用实时数据
            if today_date.startswith(current_date_str):
                for sym in symbols:
                    try:
                        ltp = nse_quote_ltp(sym)
                        if ltp:
                            results[f"{sym}_price"] = float(ltp)
                    except Exception:
                        results[f"{sym}_price"] = None
                if all(v is not None for v in results.values()) and len(results) == len(symbols):
                    return results
        except Exception:
            pass

    merged_file = _resolve_merged_file_path_for_date(today_date, market, merged_path)
    if not merged_file.exists():
        return results

    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            meta = doc.get("Meta Data", {}) if isinstance(doc, dict) else {}
            sym = meta.get("2. Symbol", "")
            
            # 🇮🇳 Indian Market Suffix-Agnostic Matching
            match_found = False
            if market == "in":
                clean_sym = sym.split('.')[0]
                for wanted_sym in wanted:
                    if wanted_sym == clean_sym or wanted_sym == sym:
                        match_found = True
                        current_wanted_sym = wanted_sym
                        break
            else:
                if sym in wanted:
                    match_found = True
                    current_wanted_sym = sym

            if not match_found:
                continue

            # 查找所有以 "Time Series" 开头的键
            series = None
            for key, value in doc.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            if not isinstance(series, dict):
                continue
            bar = series.get(today_date)
            
            if isinstance(bar, dict):
                open_val = bar.get("1. buy price")
                
                try:
                    results[f"{current_wanted_sym}_price"] = float(open_val) if open_val is not None else None
                except Exception:
                    results[f"{current_wanted_sym}_price"] = None

    return results


def get_yesterday_open_and_close_price(
    today_date: str, symbols: List[str], merged_path: Optional[str] = None, market: str = "us"
) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
    """从 data/merged.jsonl 中读取指定日期与股票的昨日买入价和卖出价。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        symbols: 需要查询的股票代码列表。
        merged_path: 可选，自定义 merged.jsonl 路径；默认读取项目根目录下 data/merged.jsonl。
        market: 市场类型，"us" 为美股，"cn" 为A股

    Returns:
        (买入价字典, 卖出价字典) 的元组；若未找到对应日期或标的，则值为 None。
    """
    wanted = set(symbols)
    buy_results: Dict[str, Optional[float]] = {}
    sell_results: Dict[str, Optional[float]] = {}

    merged_file = _resolve_merged_file_path_for_date(today_date, market, merged_path)

    if not merged_file.exists():
        return buy_results, sell_results

    yesterday_date = get_yesterday_date(today_date, merged_path=merged_path, market=market)

    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            meta = doc.get("Meta Data", {}) if isinstance(doc, dict) else {}
            sym = meta.get("2. Symbol", "")
            
            # 🇮🇳 Indian Market Suffix-Agnostic Matching
            match_found = False
            if market == "in":
                clean_sym = sym.split('.')[0]
                for wanted_sym in wanted:
                    if wanted_sym == clean_sym or wanted_sym == sym:
                        match_found = True
                        current_wanted_sym = wanted_sym
                        break
            else:
                if sym in wanted:
                    match_found = True
                    current_wanted_sym = sym

            if not match_found:
                continue

            # 查找所有以 "Time Series" 开头的键
            series = None
            for key, value in doc.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            if not isinstance(series, dict):
                continue

            # 尝试获取昨日买入价和卖出价
            bar = series.get(yesterday_date)
            if isinstance(bar, dict):
                buy_val = bar.get("1. buy price")  # 买入价字段
                sell_val = bar.get("4. sell price")  # 卖出价字段

                try:
                    buy_price = float(buy_val) if buy_val is not None else None
                    sell_price = float(sell_val) if sell_val is not None else None
                    buy_results[f"{current_wanted_sym}_price"] = buy_price
                    sell_results[f"{current_wanted_sym}_price"] = sell_price
                except Exception:
                    buy_results[f"{current_wanted_sym}_price"] = None
                    sell_results[f"{current_wanted_sym}_price"] = None
            else:
                buy_results[f'{current_wanted_sym}_price'] = None
                sell_results[f'{current_wanted_sym}_price'] = None
                # today_dt = datetime.strptime(today_date, "%Y-%m-%d")
                # yesterday_dt = today_dt - timedelta(days=1)
                # current_date = yesterday_dt
                # found_data = False
                
                # # 最多向前查找5个交易日
                # for _ in range(5):
                #     current_date -= timedelta(days=1)
                #     # 跳过周末
                #     while current_date.weekday() >= 5:
                #         current_date -= timedelta(days=1)
                    
                #     check_date = current_date.strftime("%Y-%m-%d")
                #     bar = series.get(check_date)
                #     if isinstance(bar, dict):
                #         buy_val = bar.get("1. buy price")
                #         sell_val = bar.get("4. sell price")
                        
                #         try:
                #             buy_price = float(buy_val) if buy_val is not None else None
                #             sell_price = float(sell_val) if sell_val is not None else None
                #             buy_results[f'{sym}_price'] = buy_price
                #             sell_results[f'{sym}_price'] = sell_price
                #             found_data = True
                #             break
                #         except Exception:
                #             continue
                
                # if not found_data:
                #     buy_results[f'{sym}_price'] = None
                #     sell_results[f'{sym}_price'] = None

    return buy_results, sell_results


def get_yesterday_profit(
    today_date: str,
    yesterday_buy_prices: Dict[str, Optional[float]],
    yesterday_sell_prices: Dict[str, Optional[float]],
    yesterday_init_position: Dict[str, float],
    stock_symbols: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    获取持仓收益（适用于日线和小时级交易）
    
    收益计算方式为：(前一时间点收盘价 - 前一时间点开盘价) × 当前持仓数量
    
    对于日线交易：计算昨日的收益
    对于小时级交易：计算上一小时的收益
    
    Args:
        today_date: 日期/时间字符串，格式 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        yesterday_buy_prices: 前一时间点开盘价格字典，格式为 {symbol_price: price}
        yesterday_sell_prices: 前一时间点收盘价格字典，格式为 {symbol_price: price}
        yesterday_init_position: 前一时间点初始持仓字典，格式为 {symbol: quantity}
        stock_symbols: 股票代码列表，默认为 all_nasdaq_100_symbols

    Returns:
        {symbol: profit} 的字典；若未找到对应日期或标的，则值为 0.0。
    """
    profit_dict = {}

    # 使用传入的股票列表或默认的纳斯达克100列表
    if stock_symbols is None:
        stock_symbols = all_nasdaq_100_symbols

    # 遍历所有股票代码
    for symbol in stock_symbols:
        symbol_price_key = f"{symbol}_price"

        # 获取昨日开盘价和收盘价
        buy_price = yesterday_buy_prices.get(symbol_price_key)
        sell_price = yesterday_sell_prices.get(symbol_price_key)

        # 获取昨日持仓权重
        position_weight = yesterday_init_position.get(symbol, 0.0)

        # 计算收益：(收盘价 - 开盘价) * 持仓权重
        if buy_price is not None and sell_price is not None and position_weight > 0:
            profit = (sell_price - buy_price) * position_weight
            profit_dict[symbol] = round(profit, 4)  # 保留4位小数
        else:
            profit_dict[symbol] = 0.0

    return profit_dict

def get_today_init_position(today_date: str, signature: str) -> Dict[str, float]:
    """
    获取今日开盘时的初始持仓（即文件中上一个交易日代表的持仓）。从../data/agent_data/{signature}/position/position.jsonl中读取。
    如果同一日期有多条记录，选择id最大的记录作为初始持仓。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        {symbol: weight} 的字典；若未找到对应日期，则返回空字典。
    """
    from tools.general_tools import get_config_value
    import os

    base_dir = Path(__file__).resolve().parents[1]

    # Get log_path from config, default to "agent_data" for backward compatibility
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Handle different path formats:
    # - If it's an absolute path (like temp directory), use it directly
    # - If it's a relative path starting with "./data/", remove the prefix and prepend base_dir/data
    # - Otherwise, treat as relative to base_dir/data
    if os.path.isabs(log_path):
        # Absolute path (like temp directory) - use directly
        position_file = Path(log_path) / signature / "position" / "position.jsonl"
    else:
        if log_path.startswith("./data/"):
            log_path = log_path[7:]  # Remove "./data/" prefix
        position_file = base_dir / "data" / log_path / signature / "position" / "position.jsonl"
#     position_file = base_dir / "data" / "agent_data" / signature / "position" / "position.jsonl"

    if not position_file.exists():
        print(f"Position file {position_file} does not exist")
        return {}
    
    # 获取市场类型，智能判断
    market = get_market_type()
    yesterday_date = get_yesterday_date(today_date, market=market)
    
    max_id = -1
    latest_positions = {}
    all_records = []
  
    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                record_date = doc.get("date")
                if record_date and record_date < today_date:
                    all_records.append(doc)
            except Exception:
                continue

    if not all_records:
        return {}

    # Sort by date (descending) then by id (descending) to get the most recent record
    all_records.sort(key=lambda x: (x.get("date", ""), x.get("id", 0)), reverse=True)

    return all_records[0].get("positions", {})


def get_latest_position(today_date: str, signature: str) -> Tuple[Dict[str, float], int]:
    """
    获取最新持仓。从 ../data/agent_data/{signature}/position/position.jsonl 中读取。
    优先选择当天 (today_date) 中 id 最大的记录；
    若当天无记录，则回退到上一个交易日，选择该日中 id 最大的记录。

    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        (positions, max_id):
          - positions: {symbol: weight} 的字典；若未找到任何记录，则为空字典。
          - max_id: 选中记录的最大 id；若未找到任何记录，则为 -1.
    """
    from tools.general_tools import get_config_value
    import os

    base_dir = Path(__file__).resolve().parents[1]

    # Get log_path from config, default to "agent_data" for backward compatibility
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Handle different path formats:
    # - If it's an absolute path (like temp directory), use it directly
    # - If it's a relative path starting with "./data/", remove the prefix and prepend base_dir/data
    # - Otherwise, treat as relative to base_dir/data
    if os.path.isabs(log_path):
        # Absolute path (like temp directory) - use directly
        position_file = Path(log_path) / signature / "position" / "position.jsonl"
    else:
        if log_path.startswith("./data/"):
            log_path = log_path[7:]  # Remove "./data/" prefix
        position_file = base_dir / "data" / log_path / signature / "position" / "position.jsonl"

    if not position_file.exists():
        return {}, -1

    # 获取市场类型，智能判断
    market = get_market_type()
    
    # Step 1: 先查找当天的记录
    max_id_today = -1
    latest_positions_today: Dict[str, float] = {}
    
    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                if doc.get("date") == today_date:
                    current_id = doc.get("id", -1)
                    if current_id > max_id_today:
                        max_id_today = current_id
                        latest_positions_today = doc.get("positions", {})
            except Exception:
                continue
    
    # 如果当天有记录，直接返回
    if max_id_today >= 0 and latest_positions_today:
        return latest_positions_today, max_id_today
    
    # Step 2: 当天没有记录，则回退到上一个交易日
    prev_date = get_yesterday_date(today_date, market=market)
    
    max_id_prev = -1
    latest_positions_prev: Dict[str, float] = {}

    with position_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
                if doc.get("date") == prev_date:
                    current_id = doc.get("id", -1)
                    if current_id > max_id_prev:
                        max_id_prev = current_id
                        latest_positions_prev = doc.get("positions", {})
            except Exception:
                continue
    
    # 如果前一天也没有记录，尝试找文件中最新的非空记录（按实际时间和id排序）
    if max_id_prev < 0 or not latest_positions_prev:
        all_records: List[Dict[str, Any]] = []
        norm_today = _normalize_timestamp_str(today_date)
        today_dt = _parse_timestamp_to_dt(norm_today)
        with position_file.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    doc = json.loads(line)
                    doc_date = doc.get("date")
                    if not doc_date:
                        continue
                    norm_doc_date = _normalize_timestamp_str(doc_date)
                    doc_dt = _parse_timestamp_to_dt(norm_doc_date)
                    # 仅考虑早于today_date的记录
                    if doc_dt < today_dt:
                        positions = doc.get("positions", {})
                        # 跳过空持仓记录
                        if positions:
                            all_records.append(doc)
                except Exception:
                    continue
        
        if all_records:
            # 先按实际时间排序，再按id排序，取最新的一条
            all_records.sort(
                key=lambda x: (
                    _parse_timestamp_to_dt(_normalize_timestamp_str(x.get("date", "1900-01-01"))),
                    x.get("id", 0),
                ),
                reverse=True,
            )
            latest_positions_prev = all_records[0].get("positions", {})
            max_id_prev = all_records[0].get("id", -1)
    
    return latest_positions_prev, max_id_prev

def add_no_trade_record(today_date: str, signature: str):
    """
    添加不交易记录。从 ../data/agent_data/{signature}/position/position.jsonl 中前一日最后一条持仓，并更新在今日的position.jsonl文件中。
    Args:
        today_date: 日期字符串，格式 YYYY-MM-DD，代表今天日期。
        signature: 模型名称，用于构建文件路径。

    Returns:
        None
    """
    save_item = {}
    current_position, current_action_id = get_latest_position(today_date, signature)
    
    save_item["date"] = today_date
    save_item["id"] = current_action_id + 1
    save_item["this_action"] = {"action": "no_trade", "symbol": "", "amount": 0}

    save_item["positions"] = current_position

    from tools.general_tools import get_config_value
    import os

    base_dir = Path(__file__).resolve().parents[1]

    # Get log_path from config, default to "agent_data" for backward compatibility
    log_path = get_config_value("LOG_PATH", "./data/agent_data")

    # Handle different path formats:
    # - If it's an absolute path (like temp directory), use it directly
    # - If it's a relative path starting with "./data/", remove the prefix and prepend base_dir/data
    # - Otherwise, treat as relative to base_dir/data
    if os.path.isabs(log_path):
        # Absolute path (like temp directory) - use directly
        position_file = Path(log_path) / signature / "position" / "position.jsonl"
    else:
        if log_path.startswith("./data/"):
            log_path = log_path[7:]  # Remove "./data/" prefix
        position_file = base_dir / "data" / log_path / signature / "position" / "position.jsonl"

    with position_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(save_item) + "\n")
    return


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(today_date, signature)
    yesterday_date = get_yesterday_date(today_date)
    print(yesterday_date)
    # today_buy_price = get_open_prices(today_date, all_nasdaq_100_symbols)
    # print(today_buy_price)
    # yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(today_date, all_nasdaq_100_symbols)
    # print(yesterday_sell_prices)
    # today_init_position = get_today_init_position(today_date, signature='qwen3-max')
    # print(today_init_position)
    # latest_position, latest_action_id = get_latest_position('2025-10-24', 'qwen3-max')
    # print(latest_position, latest_action_id)
    latest_position, latest_action_id = get_latest_position('2025-10-16 16:00:00', 'test')
    print(latest_position, latest_action_id)
    
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    # # print(yesterday_profit)
    # add_no_trade_record(today_date, signature)

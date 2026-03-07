import os

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from tools.general_tools import get_config_value
from tools.price_tools import (all_nasdaq_100_symbols, all_sse_50_symbols,
                               all_nifty_50_symbols,
                               format_price_dict_with_names, get_open_prices,
                               get_today_init_position, get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit, get_merged_file_path)

STOP_SIGNAL = "<FINISH_SIGNAL>"

# NSE hourly trading slots in order
NSE_HOURLY_SLOTS = [
    "09:15:00", "10:15:00", "11:15:00",
    "12:15:00", "13:15:00", "14:15:00", "15:15:00"
]

agent_system_prompt = """
You are a professional stock trading assistant with full autonomy.

Your goals are:
### 🛡️ THE "BALANCED SNIPER" RISK FRAMEWORK
- **Position Sizing (Anti-Concentration):** Maximum investment per stock is **₹40,000** (40% of capital). You may hold 1 stock, a basket, or stay in cash — your choice based on market quality.
- **Autonomous Risk Management:**
    - **Self-Defined Exits:** For every trade, you MUST define your own **Stop-Loss** and **Price Target** based on current volatility and catalyst strength. 
    - **Dynamic Trailing:** As a stock moves in your favour, raise your mental stop-loss to protect profits.
- **Velocity Rule:** If a stock has been stagnant for **5 sessions**, reassess. If a better catalyst exists elsewhere, rotate.

### 🎯 DUAL-GATE ENTRY SYSTEM (BOTH gates must pass before any Buy)
Before entering ANY trade, you must pass **both** of these gates:

**Gate 1 — ₹100 Expected Profit Floor:**
- Total round-trip taxes on a sell are approximately ₹25 (DP charge + STT + GST).
- Your expected profit from this trade must be **greater than ₹100** (4× the sell tax).
- Example: If you're 60% confident in a ₹200 gain → `0.60 × ₹200 = ₹120 > ₹100` ✅ Pass.

**Gate 2 — 2:1 Reward-to-Risk Ratio:**
- Your **Price Target distance** must be at least **2× your Stop-Loss distance**.
- Example: Stop-Loss is ₹30 below entry → Target must be at least ₹60 above entry.
- This ensures bad trades are cut small, good trades run large.

### 🛑 THE "FRICTION SHIELD" (EXIT/ROTATION RULES)
- **No Tiny Trimming:** Never 'trim' or 'rotate' a winning position for a gross profit less than **₹150**. Selling for tiny gains results in wasted transaction friction.
- **The Rotation Hurdle:** Only rotate from a "slow" winner to a "fast" momentum stock if the expected catalyst in the *new* stock is strong enough to recover the exit friction of the *old* stock PLUS the Gate 1 floor.
- **Stop-Loss Priority:** Emergency exits (Stop-Loss breaches) supersede the Friction Shield. If capital is at risk, exit immediately regardless of tax.

Mandatory Thinking Protocol (follow in exact order every hourly session):
1. 🔍 SCAN HOLDINGS (MANDATORY): For EVERY stock you currently hold, you MUST:
   a. Check the intraday candle table below for its current price.
   b. Calculate: (current price - your entry price) as both ₹ and %.
   c. Compare current price against your self-defined stop-loss. If breached → SELL immediately.
   d. Compare current price against your price target. If hit → take profit immediately.
   You are NOT allowed to skip this step. Use `get_price_local` only if a stock is missing from the table.

2. ⚖️ WEIGH NEW OPPORTUNITIES: Study the Intraday Price Table below.
   - Each row shows: yesterday's close → today's 9:15 open → each completed hour → current hour (open only).
   - Calculate overnight gap: (9:15 open - yesterday close) / yesterday close × 100.
   - Calculate intraday momentum: (current price - 9:15 open) / 9:15 open × 100.
   - Look for stocks where BOTH gap AND momentum are strongly positive = breakout signal.
   - High positive momentum + both Gate 1 and Gate 2 pass → consider entry.

3. ⚡ ACT: Execute your buys/sells. Use up to 30 steps.


Current information:
- Date: {date}
- Positions: {positions}

📊 INTRADAY PRICE TABLE (yesterday close → all today's candles so far):
{intraday_table}

⚠️  Current hour ({current_slot}) shows open price only — high/low/close not yet available (no lookahead).

When complete, output {STOP_SIGNAL}
"""


def get_todays_intraday_candles(
    today_date: str,
    symbols: List[str],
    market: str = "in"
) -> Dict[str, Dict[str, Dict]]:
    """
    Fetch all completed hourly candles for today up to (but not including) the current session,
    plus the open price for the current session.

    Returns a dict like:
    {
      "RELIANCE": {
        "09:15": {"open": 1418.0, "high": 1425.0, "low": 1415.0, "close": 1422.0},
        "10:15": {"open": 1422.0, "high": 1432.0, "low": 1420.0, "close": 1429.0},
        "11:15": {"open": 1429.0}   ← current hour: only open available
      },
      ...
    }
    """
    if " " not in today_date:
        return {}  # daily mode, not hourly

    date_str, time_str = today_date.split(" ", 1)
    current_slot = time_str  # e.g. "11:15:00"

    # Determine which slots are past (completed) and which is current
    past_slots = []
    for slot in NSE_HOURLY_SLOTS:
        if slot < current_slot:
            past_slots.append(slot)
        elif slot == current_slot:
            break  # current slot — stop here

    merged_file = get_merged_file_path(market)
    if not merged_file.exists():
        return {}

    # Build lookup: symbol → { "YYYY-MM-DD HH:MM:SS" → bar_dict }
    wanted = set(symbols)
    symbol_series: Dict[str, Dict] = {}

    with merged_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except Exception:
                continue
            meta = doc.get("Meta Data", {})
            sym = meta.get("2. Symbol", "")

            # Indian market: strip exchange suffix for matching
            clean_sym = sym.split(".")[0] if market == "in" else sym
            matched = None
            if clean_sym in wanted:
                matched = clean_sym
            elif sym in wanted:
                matched = sym

            if matched is None:
                continue

            for key, value in doc.items():
                if key.startswith("Time Series") and isinstance(value, dict):
                    symbol_series[matched] = value
                    break

    # Now build the result dict
    result: Dict[str, Dict[str, Dict]] = {}

    for sym in symbols:
        series = symbol_series.get(sym)
        if not series:
            continue

        sym_data: Dict[str, Dict] = {}

        # Past slots — full OHLC available
        for slot in past_slots:
            ts = f"{date_str} {slot}"
            bar = series.get(ts)
            if bar:
                entry = {}
                if bar.get("1. buy price") is not None:
                    try:
                        entry["open"] = float(str(bar["1. buy price"]).replace(",", ""))
                    except Exception:
                        pass
                if bar.get("2. high") is not None:
                    try:
                        entry["high"] = float(str(bar["2. high"]).replace(",", ""))
                    except Exception:
                        pass
                if bar.get("3. low") is not None:
                    try:
                        entry["low"] = float(str(bar["3. low"]).replace(",", ""))
                    except Exception:
                        pass
                if bar.get("4. sell price") is not None:
                    try:
                        entry["close"] = float(str(bar["4. sell price"]).replace(",", ""))
                    except Exception:
                        pass
                if entry:
                    sym_data[slot[:5]] = entry  # store as "09:15" not "09:15:00"

        # Current slot — open price only (anti-lookahead)
        cur_ts = f"{date_str} {current_slot}"
        cur_bar = series.get(cur_ts)
        if cur_bar and cur_bar.get("1. buy price") is not None:
            try:
                sym_data[current_slot[:5]] = {
                    "open": float(str(cur_bar["1. buy price"]).replace(",", ""))
                }
            except Exception:
                pass

        if sym_data:
            result[sym] = sym_data

    return result


def format_intraday_table(
    yesterday_close: Dict[str, Optional[float]],
    intraday: Dict[str, Dict[str, Dict]],
    symbols: List[str]
) -> str:
    """
    Format the intraday candles + yesterday close into a readable table string.

    Output example:
    RELIANCE  | yest_close=1423.5 | 09:15 O:1418 H:1425 L:1415 C:1422 | 10:15 O:1422 H:1432 L:1420 C:1429 | 11:15 O:1429* (current)
    """
    lines = []
    for sym in symbols:
        candles = intraday.get(sym)
        if not candles:
            continue  # skip stocks with no data today

        ykey = f"{sym}_price"
        yclose = yesterday_close.get(ykey)
        yclose_str = f"₹{yclose:.1f}" if yclose is not None else "N/A"

        parts = [f"{sym:<14} | yest_close={yclose_str}"]

        for slot_label, bar in sorted(candles.items()):
            if "close" in bar:
                # Completed candle — show OHLC
                o = f"O:{bar['open']:.1f}" if "open" in bar else ""
                h = f"H:{bar['high']:.1f}" if "high" in bar else ""
                l = f"L:{bar['low']:.1f}" if "low" in bar else ""
                c = f"C:{bar['close']:.1f}" if "close" in bar else ""
                parts.append(f"{slot_label} {o} {h} {l} {c}".strip())
            else:
                # Current candle — open only
                o = f"O:{bar['open']:.1f}" if "open" in bar else "no data"
                parts.append(f"{slot_label} {o} ← NOW")

        lines.append(" | ".join(parts))

    if not lines:
        return "(No intraday data available)"
    return "\n".join(lines)


def get_agent_system_prompt(
    today_date: str, signature: str, market: str = "us", stock_symbols: Optional[List[str]] = None
) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    print(f"market: {market}")

    # Auto-select stock symbols based on market if not provided
    if stock_symbols is None:
        stock_symbols = all_nifty_50_symbols

    # Get yesterday's close prices
    _, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, stock_symbols, market=market
    )

    today_init_position = get_today_init_position(today_date, signature)

    # Filter positions to only show non-zero holdings and CASH
    filtered_positions = {k: v for k, v in today_init_position.items() if v != 0 or k == "CASH"}

    # Determine current slot label for prompt annotation
    current_slot = "09:15"
    if " " in today_date:
        current_slot = today_date.split(" ")[1][:5]  # e.g. "11:15"

    if market == "in" and " " in today_date:
        # Build full intraday candle table
        intraday = get_todays_intraday_candles(today_date, stock_symbols, market=market)
        filtered_yesterday_close = {k: v for k, v in yesterday_sell_prices.items() if v is not None}
        intraday_table = format_intraday_table(filtered_yesterday_close, intraday, stock_symbols)
    else:
        # Daily mode or non-Indian market — fall back to just current price
        today_session_price = get_open_prices(today_date, stock_symbols, market=market)
        filtered_session_prices = {k: v for k, v in today_session_price.items() if v is not None}
        filtered_yesterday_close = {k: v for k, v in yesterday_sell_prices.items() if v is not None}
        intraday_table = (
            f"Yesterday Close: {filtered_yesterday_close}\n"
            f"Current Price:   {filtered_session_prices}"
        )

    prompt_text = agent_system_prompt
    if market == "in":
        prompt_text += "\nNote for Indian Market:"
        prompt_text += "\n- NO search/news tool available. Base decisions purely on price action shown in the intraday table above."
        prompt_text += "\n- Use the intraday candles to judge: is momentum building or fading across hours?"
        prompt_text += "\n- Small Position Friction: If buying < ₹4,000, fixed DP charges (₹16) eat a HIGH % of the trade. Adjust Gate 1 'Expected Profit' upward to compensate."

    return prompt_text.format(
        date=today_date,
        positions=filtered_positions,
        STOP_SIGNAL=STOP_SIGNAL,
        intraday_table=intraday_table,
        current_slot=current_slot,
    )


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))

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
                               get_yesterday_profit)

STOP_SIGNAL = "<FINISH_SIGNAL>"

agent_system_prompt = """
You are a professional stock trading assistant with full autonomy.

Your goals are:
### 🛡️ THE "BALANCED SNIPER" RISK FRAMEWORK
- **Position Sizing (Anti-Concentration):** Maximum investment per stock is **₹4,000** (40% of capital). You may hold 1 stock, a basket, or stay in cash — your choice based on market quality.
- **Autonomous Risk Management:**
    - **Self-Defined Exits:** For every trade, you MUST define your own **Stop-Loss** and **Price Target** based on current volatility and catalyst strength. 
    - **Dynamic Trailing:** As a stock moves in your favour, raise your mental stop-loss to protect profits.
- **Velocity Rule:** If a stock has been stagnant for **5 sessions**, reassess. If a better catalyst exists elsewhere, rotate.

### 🎯 DUAL-GATE ENTRY SYSTEM (BOTH gates must pass before any Buy)
Before entering ANY trade, you must pass **both** of these gates:

**Gate 1 — ₹44 Expected Profit Floor:**
- Total round-trip taxes on a sell are approximately ₹22 (DP charge + STT + GST).
- Your expected profit from this trade must be **greater than ₹44** (2× the sell tax).
- This accounts for a ~50-60% win rate: `Win_Rate × Expected_Gain > ₹44`.
- Example: If you're 60% confident in a ₹100 gain → `0.60 × ₹100 = ₹60 > ₹44` ✅ Pass.

**Gate 2 — 2:1 Reward-to-Risk Ratio:**
- Your **Price Target distance** must be at least **2× your Stop-Loss distance**.
- Example: Stop-Loss is ₹30 below entry → Target must be at least ₹60 above entry.
- This ensures bad trades are cut small, good trades run large.

### 🛑 THE "FRICTION SHIELD" (EXIT/ROTATION RULES)
- **No Tiny Trimming:** Never 'trim' or 'rotate' a winning position for a gross profit less than **₹60**. Selling for a ₹10-₹20 gain results in a **NET LOSS** after fixed costs (₹22 per sell session).
- **The Rotation Hurdle:** Only rotate from a "slow" winner to a "fast" momentum stock if the expected catalyst in the *new* stock is strong enough to recover the ₹22 exit tax of the *old* stock PLUS the ₹44 Gate 1 floor.
- **Stop-Loss Priority:** Emergency exits (Stop-Loss breaches) supersede the Friction Shield. If capital is at risk, exit immediately regardless of tax.

Mandatory Thinking Protocol (follow in exact order every hourly session):
1. 🔍 SCAN HOLDINGS (MANDATORY): For EVERY stock you currently hold, you MUST:
   a. Call `get_price_local` to get the current price for this hour.
   b. Calculate: (current price - your entry price) as both ₹ and %.
   c. Compare current price against your self-defined stop-loss. If breached → SELL immediately.
   d. Compare current price against your price target. If hit → take profit immediately.
   You are NOT allowed to skip this step. No tools other than `get_price_local` and `buy`/`sell` are available.

2. ⚖️ WEIGH NEW OPPORTUNITIES: Look at Today's Buying Prices (provided below).
   - Identify stocks with strong upward momentum vs yesterday's close.
   - Calculate gap: (today_buy_price - yesterday_close_price) / yesterday_close_price × 100.
   - High positive momentum + both Gate 1 and Gate 2 pass → consider entry.

3. ⚡ ACT: Execute your buys/sells. Use up to 30 steps.


Current information:
- Date: {date}
- Positions: {positions}
- Yesterday's Prices: {yesterday_close_price}
- Day Opening Prices (9:15 AM): {day_open_price}
- Today's Hourly Prices (Current): {today_buy_price}

When complete, output {STOP_SIGNAL}
"""


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
    
    # Get current session price
    today_session_price = get_open_prices(today_date, stock_symbols, market=market)
    
    # Get today's opening price (9:15 AM) for daily context
    day_open_price = {}
    if " " in today_date:
        day_str = today_date.split(" ")[0]
        opening_ts = f"{day_str} 09:15:00"
        day_open_price = get_open_prices(opening_ts, stock_symbols, market=market)
    else:
        day_open_price = today_session_price # Daily mode

    today_init_position = get_today_init_position(today_date, signature)
    
    # Filter positions to only show non-zero holdings and CASH
    filtered_positions = {k: v for k, v in today_init_position.items() if v != 0 or k == "CASH"}
    
    # Filter prices to only show stocks with data
    filtered_session_prices = {k: v for k, v in today_session_price.items() if v is not None}
    filtered_yesterday_close = {k: v for k, v in yesterday_sell_prices.items() if v is not None}
    filtered_day_open = {k: v for k, v in day_open_price.items() if v is not None}
    
    prompt_text = agent_system_prompt
    if market == "in":
        prompt_text += "\nNote for Indian Market:"
        prompt_text += "\n- NO search/news tool available. Base decisions purely on price: Yesterday Close vs Day Open (Overnight Gap) and Day Open vs Current Price (Daily Momentum)."
        prompt_text += "\n- Small Position Friction: If buying < ₹4,000, fixed DP charges (₹16) represent a HIGHER % of your trade. Adjust your Gate 1 'Expected Profit' higher to compensate for this drag."

    return prompt_text.format(
        date=today_date,
        positions=filtered_positions,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=filtered_yesterday_close,
        day_open_price=filtered_day_open,
        today_buy_price=filtered_session_prices,
    )


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))

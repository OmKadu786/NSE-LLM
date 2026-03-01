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
- If you cannot define a 2:1 setup, do NOT enter.

You may trade as often as you want — but EVERY trade must pass both gates. There is no monthly budget limit.

Mandatory Thinking Protocol (follow in exact order every hourly session):
1. 🔍 SCAN HOLDINGS (MANDATORY): For EVERY stock you currently hold, you MUST:
   a. Call `get_price_local` to get the current price for this hour.
   b. Call the search tool for latest news (e.g., "TATAMOTORS NSE news today").
   c. Compare current price against your stop-loss. If breached → SELL immediately.
   d. Check for negative catalysts. If found → reassess immediately.
   You are NOT allowed to skip this step. Use your search tool — do not say "no access."

2. ⚖️ WEIGH NEW OPPORTUNITIES: Scan 3-5 Nifty 50 stocks for high-conviction entries.
   Both Gate 1 and Gate 2 must pass before placing any buy order.

3. ⚡ ACT: Execute trades. Use up to 30 steps.


Current information:
- Date: {date}
- Positions: {positions}
- Yesterday's Prices: {yesterday_close_price}
- Today's Buying Prices: {today_buy_price}

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

    # Get yesterday's buy and sell prices
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, stock_symbols, market=market
    )
    today_buy_price = get_open_prices(today_date, stock_symbols, market=market)
    today_init_position = get_today_init_position(today_date, signature)
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    
    # Filter positions to only show non-zero holdings and CASH
    filtered_positions = {k: v for k, v in today_init_position.items() if v != 0 or k == "CASH"}
    
    # Filter today's prices to only show stocks with prices
    filtered_today_prices = {k: v for k, v in today_buy_price.items() if v is not None}
    
    # Optional: If you want to keep the prompt even shorter, you can show only top 20 or something, 
    # but the agent needs to know what stocks it CAN buy.
    # For now, let's just keep the non-zero positions simplified.
    
    prompt_text = agent_system_prompt
    if market == "in":
        prompt_text += "\nNote for Indian Market: Prioritize news from Moneycontrol, Economic Times (ET), and Mint for local stock catalysts and RBI policy updates."

    return prompt_text.format(
        date=today_date,
        positions=filtered_positions,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=filtered_today_prices,
    )


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))

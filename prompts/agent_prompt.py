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
- **Position Sizing (Anti-Concentration):** You are strictly forbidden from going "All-in" on a single stock. Maximum investment per stock is **₹4,000** (40% of your initial capital). You may choose to hold only 1 stock, a basket of 3, or stay entirely in liquid cash based on market quality.
- **Operating Fee Budget:** You have a **₹150/month "Operating Fee Budget."** Use it for strategic rotations. If a trade plan is invalidated, cut it immediately. Do not "bag-hold" just to avoid the ₹22 fee.
- **Autonomous Risk Management:**
    - **Self-Defined Exits:** For every trade, you MUST define your own **Stop-Loss** and **Price Target** based on current volatility and catalyst strength. 
    - **Profit Hurdle:** Only execute a trade if your conviction suggests a return that comfortably clears the **₹22 Indian "Exit Toll"** plus taxes.
    - **Dynamic Trailing:** Proactively protect profits by raising your mental stop-loss as a stock moves in your favor.
- **Velocity Rule:** If a stock has been stagnant for **5 trading days**, reassess. If a better opportunity exists, use your fee budget to pivot to a higher-velocity catalyst.

Your goal: Use your intelligence to set targets, manage risk through position sizing (max 40%), and use your fee budget to keep capital moving toward the best catalysts.

Thinking Standards:
1. GATHER: Pulse prices and find high-momentum news (Moneycontrol, ET, etc.).
2. WEIGH: Calculate if your target upside justifies the ₹22 exit fee and risk.
3. ACT: Execute as many steps as needed (up to 30) to reach a final decision.

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

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
You are a stock fundamental analysis trading assistant optimized for the Indian Stock Market (NSE).

Your goals are:
- Maximize total portfolio returns using 'Asymmetric Risk/Reward' logic.
- Aggressively protect capital from the "Silent Killer" (Fixed DP charges and STT).
- Think like a institutional 'Sniper' or 'Vulture'—only strike when the reward vastly outweighs the cost.

🇮🇳 INDIAN MARKET ECONOMICS (NON-NEGOTIABLE):
- DP CHARGES & TAXES: Every sell action costs ~₹18–₹22 in total fees (Fixed ₹16 DP + Variable STT/GST).
- SMALL CAPITAL RULE (₹10,000): Fixed fees are a massive percentage of small trades. Do NOT split ₹10k into more than 3-4 high-conviction stocks (~₹2.5k - ₹3.3k per position).
- OPPORTUNITY COST: A 'Win' is only a win if the profit is significantly larger than the ₹22 exit fee.

THINKING STANDARDS (ASYMMETRIC LOGIC):
1. GATHER: Pulse the Nifty 50 prices and News (Moneycontrol, ET).
2. EXPECTED VALUE (EV) CALCULATION:
   - Before executing, explicitly reason: "What is my Target Upside vs. Potential Downside?"
   - DISCARD trades where the potential gain is less than 3x the transaction cost.
3. THE EXERTION RULE: Only 'buy' if you have a fundamental thesis for a >3% move or a major trend reversal.
4. EXIT STRATEGY: Do not 'trim' small amounts. Exit the FULL position only when the fundamental thesis changes or a target is reached to minimize repeated DP charges.

Current information:
- Time: {date}
- Market: India (NSE)
- Today Init Positions: {positions}
- Yesterday Prices: {yesterday_close_price}
- Today Buying Prices: {today_buy_price}

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

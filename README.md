# NSE-LLM: Indian Market AI Trader

## 📌 Overview
This repository is an implementation of an autonomous trading agent optimized specifically for the **National Stock Exchange (NSE) of India**. It uses Large Language Models (LLMs) to make real-time trading decisions based on Nifty 50 price data, Indian financial news, and technical analysis.

This project is a fork of the [AI-Trader](https://github.com/HKUDS/AI-Trader) research, adapted for the unique dynamics of the Indian equity market.

---

## 🧠 Trading Logic & Strategy (NSE Optimized)

The agent operates on an hourly frequency using a **multi-step agentic reasoning loop**:

1.  **Data Gathering:** Pulls hourly OHLC prices for high-liquidity **Nifty 50** stocks (e.g., RELIANCE, TCS, HDFCBANK).
2.  **Local News Retrieval:** Scans Indian-specific sources like **Moneycontrol, Economic Times (ET), and Mint** for local catalysts, RBI policy updates, and corporate announcements.
3.  **Technical Analysis:** Calculates technical indicators (RSI, EMAs) tailored to Indian market volatility.
4.  **Strategic Execution:** Implements a sector-aware strategy, pivoting between high-growth IT/Banking and defensive FMCG/Pharma sectors.

---

## 🛠 Technology Stack (Indian Context)

| Feature | Technology Used | Description |
| :--- | :--- | :--- |
| **Brain** | **DeepSeek-V3 Chat** | Logic & decision engine utilizing an agentic loop. |
| **Eyes (Prices)** | **Dhan / KiteConnect** | High-precision Indian market data APIs. |
| **Ears (News)** | **Jina Search** | Targeted crawling of Indian financial news portals. |
| **Hands (MCP)** | **Model Context Protocol** | Connecting the AI to local trading tools. |
| **Storage** | **Python / JSONL** | Local log of all thinking steps and trades. |

---

## 📊 Getting Started

1.  **Configure API Keys:** Add your `DEEPSEEK_API_KEY` and `JINA_API_KEY` to the `.env` file.
2.  **Set Market:** Ensure `market` is set to `"in"` in your configuration.
3.  **Run Backtest:** Execute `python main.py` to start the simulation for the Nifty 50 period.

---

## 🛡 Disclaimer
This project is for educational and research purposes only. Algorithmic trading in India is subject to SEBI regulations. Always consult with a certified financial advisor before trading with real capital.

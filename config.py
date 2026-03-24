"""
Configuration for the trading bot.
Edit this file before running.
"""

# ==============================================================
# 1. Broker & API Settings
# ==============================================================
BROKER = "alpaca"           # 'alpaca' or 'binance' (future support)
ALPACA = {
    "API_KEY": "PKQWF4HGHSRL722BMCPRRY6OLL",
    "API_SECRET": "9XMWTHMm7KAKQUXRSxftUikR3EMuSdjk4oCFrguu6YbW",
    "BASE_URL": "https://paper-api.alpaca.markets",  # change to live URL if needed
    "TIME_ZONE": "America/New_York",
    "ACCOUNT_ID": None,  # optional: fetch from API if None
}

# ==============================================================
# 2. Strategy Parameters
# ==============================================================
STRATEGY = {
    "symbol": "AAPL",              # target symbol
    "interval": "5Min",            # candle interval
    "lookback": 365,               # days of historical data
    "entry": {
        "vwap": True,
        "ema_short": 20,
        "rsi": 30,
        "volume_sma": 50,
    },
    "exit": {
        "tp_atr_mult": 2.0,
        "sl_atr_mult": 1.0,
        "trailing_atr_mult": 1.0,
        "take_profit_pct": 0.02,    # 2%
        "stop_loss_pct": 0.01,     # 1%
    },
}

# ==============================================================
# 3. Risk Management
# ==============================================================
RISK = {
    "max_per_trade_pct": 0.02,    # 2% of equity
    "daily_loss_pct": 0.05,       # 5% of equity
    "max_trades_per_day": 10,
    "atr_period": 14,
    "slippage_pct": 0.0001,       # 0.01%
    "commission_per_share": 0.005, # $0.005 per share
}

# ==============================================================
# 4. Logging
# ==============================================================
LOGGING = {
    "level": "INFO",
    "file": "trading_bot.log",
    "max_bytes": 10 * 1024 * 1024,  # 10 MB
    "backup_count": 5,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}

# ==============================================================
# 5. Modes
# ==============================================================
# Modes: 'backtest', 'paper', 'live'
DEFAULT_MODE = "paper"

# ==============================================================
# 5. UI
# ==============================================================

"""
Alpaca credentials – put your keys here.
You can keep the paper‑account values for testing
and switch to the live ones before going live.
"""

# ---------- Alpaca – Paper ----------
ALPACA_API_KEY_PAPER = "PKQWF4HGHSRL722BMCPRRY6OLL"
ALPACA_SECRET_KEY_PAPER = "9XMWTHMm7KAKQUXRSxftUikR3EMuSdjk4oCFrguu6YbW"
ALPACA_BASE_URL_PAPER = "https://paper-api.alpaca.markets"

# ---------- Alpaca – Live ----------
ALPACA_API_KEY_LIVE = "PKQWF4HGHSRL722BMCPRRY6OLL"
ALPACA_SECRET_KEY_LIVE = "9XMWTHMm7KAKQUXRSxftUikR3EMuSdjk4oCFrguu6YbW"
ALPACA_BASE_URL_LIVE = "https://api.alpaca.markets"

# ---------- Misc ----------
REFRESH_INTERVAL_SECONDS = 5      # how often the dashboard pulls fresh data

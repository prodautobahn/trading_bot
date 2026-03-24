# alpaca_client.py
import pandas as pd
from datetime import datetime, timedelta
from alpaca_trade_api import REST, TimeFrame

class AlpacaClient:
    """
    A thin, opinionated wrapper around Alpaca REST API.
    """
    def __init__(self, base_url, api_key, secret_key):
        self.api = REST(api_key, secret_key, base_url, api_version="v2")

    # ────────────────────── Account ──────────────────────
    def get_account(self):
        """Return Alpaca account object."""
        return self.api.get_account()

    def get_account_history(self, start=None, end=None):
        """
        Return a list of dicts (date, equity, portfolio_value, cash, etc.)
        """
        return self.api.get_account_history(start=start, end=end)

    # ────────────────────── Positions ──────────────────────
    def get_positions(self):
        """Return a list of Alpaca Position objects."""
        return self.api.list_positions()

    def get_latest_price(self, symbol):
        """Return the most recent trade price."""
        return self.api.get_latest_trade(symbol).price

    # ────────────────────── Trades ──────────────────────
    def get_trades(self, limit=20):
        """
        Return the most recent trades (up to `limit`).
        """
        return self.api.list_trades(status="all", limit=limit)

    # ────────────────────── Bars ──────────────────────
    def get_latest_bars(self, symbol, timeframe="5Min", limit=20):
        """
        Return a DataFrame of recent bars.
        """
        bars = self.api.get_barset(symbol, timeframe, limit=limit).df
        return bars[symbol]  # DataFrame with columns: open, high, low, close, volume

    # ────────────────────── Orders ──────────────────────
    def place_order(self, symbol, qty, side, type="market", time_in_force="gtc"):
        """
        Submit an order. Return the Order object.
        """
        return self.api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type=type,
            time_in_force=time_in_force,
        )

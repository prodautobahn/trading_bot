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

# Replace get_account_history with this:
    def get_account_history(self, start=None, end=None, timeframe='1D'):
        """
        Return portfolio history (equity over time) for the account.
        """
        # Use ISO format if start/end provided
        start_iso = start.isoformat() if start else None
        end_iso = end.isoformat() if end else None
    
        history: 'PortfolioHistory' = self.api.get_portfolio_history(
            period='1M',          # last 1 month
            timeframe=timeframe,
            date_start=start_iso,
            date_end=end_iso,
            extended_hours=False
        )
    
        # history.equity and history.timestamp are lists
        df = pd.DataFrame({
            'equity': history.equity,
            'timestamp': pd.to_datetime(history.timestamp)
        })
        df.set_index('timestamp', inplace=True)
        return df

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
        Return the most recent filled orders (trades).
        """
        # Fetch all orders (Alpaca SDK may not support order_by/direction)
        orders = self.api.list_orders(status='all', limit=limit)
    
        # Filter only filled orders
        trades = [o for o in orders if o.filled_at is not None]
        return trades

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

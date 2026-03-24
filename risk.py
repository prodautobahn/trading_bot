# risk.py   (replace the old file)
"""
Risk‑management utilities used by the bot.

All functions are pure, so the old logic is replaced wholesale.
"""

from math import ceil

# ---------- POSITION SIZING ----------
def position_size(equity, risk_pct, atr, stop_mult=1.5):
    """
    Return number of shares to trade.
    :param equity: current account equity (USD)
    :param risk_pct: e.g. 0.02 for 2 % of equity
    :param atr: current ATR(14) value
    :param stop_mult: stop distance multiplier (default 1.5×ATR)
    """
    risk_amount = equity * risk_pct
    if atr == 0:
        return 0
    size = risk_amount / (stop_mult * atr)
    return int(ceil(size))

# ---------- STOPS ----------
def stop_loss(entry_price, atr, stop_mult=1.5):
    """Return a stop‑loss price 1.5×ATR below entry."""
    return entry_price - stop_mult * atr

def take_profit(entry_price, atr, tp_mult=2.0):
    """Return a take‑profit price 2×ATR above entry."""
    return entry_price + tp_mult * atr

# ---------- DAILY LIMIT ----------
def max_daily_loss(max_drawdown, pct=0.20):
    """Maximum loss we’ll tolerate in a single day."""
    return pct * max_drawdown

# risk.py
"""
Position sizing, stop‑loss, take‑profit, and daily limits.
"""

from math import ceil

# ------------------------------------------------------------------
# Position sizing – 1% risk per trade, stop at 1.5×ATR
# ------------------------------------------------------------------
def position_size(account_equity, risk_pct, atr, stop_mult=1.5):
    risk_amount = account_equity * risk_pct
    if atr == 0:
        return 0
    size = risk_amount / (stop_mult * atr)
    return int(ceil(size))

# ------------------------------------------------------------------
# Stop‑loss and take‑profit calculations
# ------------------------------------------------------------------
def stop_loss(entry_price, atr, stop_mult=1.5):
    return entry_price - stop_mult * atr

def take_profit(entry_price, atr, tp_mult=2.0):
    return entry_price + tp_mult * atr

# ------------------------------------------------------------------
# Daily loss limit – 20% of maximum drawdown
# ------------------------------------------------------------------
def max_daily_loss(max_drawdown):
    return 0.20 * max_drawdown

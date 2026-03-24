# risk.py

from math import ceil

# ---------- POSITION SIZING ----------
def position_size(equity, risk_pct, atr, stop_mult=1.5):
    risk_amount = equity * risk_pct
    if atr == 0:
        return 0
    size = risk_amount / (stop_mult * atr)
    return int(ceil(size))

def stop_loss(entry_price, atr, stop_mult=1.5):
    return entry_price - stop_mult * atr

def take_profit(entry_price, atr, tp_mult=2.0):
    return entry_price + tp_mult * atr

def max_daily_loss(max_drawdown, pct=0.20):
    return pct * max_drawdown

# ---------- SLIPPAGE & COMMISSION (needed by backtester) ----------
def apply_slippage(price, slippage_pct=0.02):
    """Apply slippage to a price in percent (0.02% default)."""
    return price * (1 + slippage_pct / 100)

def apply_commission(price, qty, commission_per_share=0.005):
    """Apply commission per share."""
    return price * qty * commission_per_share
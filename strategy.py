# strategy_improved.py
"""
Rule‑based day‑trading strategy – improved for robustness.

Indicators used:
    - 200‑period SMA (trend)
    - ATR(14) (volatility)
    - RSI(14) (momentum)
    - 80‑percentile volume (liquidity)
"""

import pandas as pd
import numpy as np
from collections import namedtuple

Signal = namedtuple('Signal', ['time', 'action', 'price', 'atr'])

# ------------------------------------------------------------------
# Indicator helpers
# ------------------------------------------------------------------
def calc_sma(df, period):
    return df['close'].rolling(window=period, min_periods=1).mean()

def calc_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()

def calc_rsi(df, period=14):
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ema_up = up.ewm(alpha=1/period, adjust=False).mean()
    ema_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def calc_vol_pct(df, window=30, pct=0.8):
    vol = df['volume']
    vol_threshold = vol.rolling(window=window, min_periods=1).quantile(pct)
    return vol >= vol_threshold

# ------------------------------------------------------------------
# Compute all indicators once
# ------------------------------------------------------------------
def add_indicators(df):
    df = df.copy()
    df['sma200'] = calc_sma(df, 200)
    df['atr14']  = calc_atr(df, 14)
    df['rsi14']  = calc_rsi(df, 14)
    df['vol_high'] = calc_vol_pct(df, 30, 0.8)
    return df

# ------------------------------------------------------------------
# Generate signals
# ------------------------------------------------------------------
def generate_signals(df):
    """
    Returns a list of Signal objects (time, BUY/SELL, price, atr)
    Only long positions are considered in the demo – short logic is symmetrical.
    """
    df = add_indicators(df)

    # Filter out low‑liquidity and quiet periods
    filt = (
        df['volume'] > df['volume'].rolling(30).quantile(0.8) &   # 80th percentile
        (df['atr14'] > df['atr14'].rolling(30).median() * 0.5)   # 50% of 30‑day median
    )

    # Trend & momentum
    long_cond = (
        filt &
        (df['close'] > df['sma200']) &          # price above 200‑SMA
        (df['rsi14'] > 50)                      # momentum bullish
    )

    # Avoid first/last 15 min of the day
    df['hour'] = df.index.hour
    df['minute'] = df.index.minute
    time_window = (
        (df['hour'] > 9) | (df['hour'] == 9 & df['minute'] >= 15)
    )
    time_window &= (
        (df['hour'] < 15) | (df['hour'] == 15 & df['minute'] <= 55)
    )

    long_cond &= time_window

    signals = []
    for ts, row in df[long_cond].iterrows():
        signals.append(
            Signal(time=ts, action='BUY', price=row['close'], atr=row['atr14'])
        )
    return signals

 """
Rule‑based strategy: VWAP + EMA + RSI + Volume.
Exports functions used by backtester and live engine.
"""

import pandas as pd
import numpy as np
from collections import namedtuple

# A simple namedtuple for a trade signal
Signal = namedtuple('Signal', ['time', 'action', 'price', 'atr'])

def compute_indicators(df):
    """
    Compute all strategy indicators on the OHLCV dataframe.
    Assumes df is sorted ascending by datetime.
    """
    df = df.copy()
    # VWAP
    cum_vol = df['volume'].cumsum()
    cum_vol_price = (df['close'] * df['volume']).cumsum()
    df['vwap'] = cum_vol_price / cum_vol

    # EMA
    ema_short = STRATEGY['entry']['ema_short']
    df['ema_short'] = df['close'].ewm(span=ema_short, adjust=False).mean()

    # RSI
    delta = df['close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    roll_up = up.ewm(alpha=1/STRATEGY['entry']['rsi'], adjust=False).mean()
    roll_down = down.ewm(alpha=1/STRATEGY['entry']['rsi'], adjust=False).mean()
    rs = roll_up / roll_down
    df['rsi'] = 100 - (100 / (1 + rs))

    # Volume SMA
    vol_sma = STRATEGY['entry']['volume_sma']
    df['vol_sma'] = df['volume'].rolling(window=vol_sma).mean()

    # ATR
    atr_period = RISK['atr_period']
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low']  - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = ranges.rolling(window=atr_period).mean()

    return df

def generate_signals(df):
    """
    Scan the dataframe for entry and exit points.
    Returns a list of Signal objects.
    """
    df = compute_indicators(df)
    signals = []

    # Long entry condition
    long_cond = (
        (df['close'] > df['vwap']) &
        (df['close'] > df['ema_short']) &
        (df['rsi'] < 30) &
        (df['volume'] > df['vol_sma'])
    )

    for i, row in df.iterrows():
        if long_cond.at[i]:
            signals.append(Signal(
                time=row.name,
                action='BUY',
                price=row['close'],
                atr=row['atr'],
            ))

    # Short entry condition (optional, same logic but flipped)
    short_cond = (
        (df['close'] < df['vwap']) &
        (df['close'] < df['ema_short']) &
        (df['rsi'] > 70) &
        (df['volume'] > df['vol_sma'])
    )

    for i, row in df.iterrows():
        if short_cond.at[i]:
            signals.append(Signal(
                time=row.name,
                action='SELL',
                price=row['close'],
                atr=row['atr'],
            ))

    # Sort signals chronologically
    signals.sort(key=lambda x: x.time)
    return signals

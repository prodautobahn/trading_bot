"""
Entry point. Parses CLI args, runs backtest, paper‑trade or live.
"""

import argparse
import sys
import os
import logging
import pandas as pd
import pytz
import time

from datetime import datetime, timedelta, time 
from config import *
from logger import log
from backtester import Backtester
from broker import *
from strategy import generate_signals
from risk import *
from broker import _get

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit


# Add this at the top-level of main.py, outside any other functions
def run_bot(client, logger):
    """
    Single-step iteration for the UI wrapper.
    Fetches last bar, computes signals, places orders.
    """
    import pytz
    from datetime import datetime, timedelta, time
    import pandas as pd

    symbol = STRATEGY['symbol']
    interval = STRATEGY['interval']

    # ----------------- Market hours check -----------------
    eastern = pytz.timezone('US/Eastern')
    local = pytz.timezone('Europe/Madrid')

    # Current time in Spain
    now_local = datetime.now(local)

    # Convert to US/Eastern
    now_et = now_local.astimezone(eastern)

    # Market open/close in ET (9:30-16:00)
    market_open = datetime.combine(now_et.date(), time(9, 30)).replace(tzinfo=eastern)
    market_close = datetime.combine(now_et.date(), time(16, 0)).replace(tzinfo=eastern)

    if now_et < market_open or now_et > market_close:
        logger.info(f"Market is closed. Current ET time: {now_et.time()}")
        return  # skip trading
    else:
        logger.info(f"Market is open! Current ET time: {now_et.time()}")

    # ----------------- Safe bar fetch -----------------
    # Round down to last completed 5-min bar
    minute = now_et.minute - (now_et.minute % 5)
    last_bar_end = now_et.replace(minute=minute, second=0, microsecond=0)
    last_bar_start = last_bar_end - timedelta(minutes=5*10)  # 10 bars back

    try:
        bar_resp = _get(f'/v2/stocks/{symbol}/bars', params={
            'start': last_bar_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end': last_bar_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'timeframe': interval,  # "5Min" expected
            'limit': 100
        })
    except Exception as e:
        logger.warning(f"Failed to fetch recent bars: {e}")
        return

    if not bar_resp:
        logger.info("No bars returned by API.")
        return

    # Take the latest bar
    new_bar = pd.DataFrame(bar_resp).iloc[-1]

    # ----------------- Load historical data -----------------
    df = load_historical(
        symbol,
        interval,
        (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d'),
        datetime.utcnow().strftime('%Y-%m-%d')
    )

    df = df.append(new_bar.set_index('timestamp'))

    # ----------------- Compute indicators -----------------
    df = compute_indicators(df)

    # ----------------- Generate signals -----------------
    signals = generate_signals(df)
    sigs = [s for s in signals if s.time == new_bar['timestamp']]

    for sig in sigs:
        equity = get_account()['cash']
        size = position_size(
            equity,
            RISK['max_per_trade_pct'],
            RISK['exit']['sl_atr_mult'],
            sig.atr
        )
        if size <= 0:
            logger.info("Calculated position size <= 0, skipping.")
            continue
        order_id = place_order(
            symbol,
            qty=size,
            side='buy',
            type_='market',
            time_in_force='gtc'
        )
        logger.info(f"Placed market order {order_id} for {size} shares at {sig.price}")

def parse_args():
    parser = argparse.ArgumentParser(description="Day‑Trading Bot")
    parser.add_argument('--mode', choices=['backtest', 'paper', 'live'],
                        default=DEFAULT_MODE,
                        help='Execution mode')
    parser.add_argument('--symbol', help='Ticker symbol to trade')
    parser.add_argument('--start', help='Start date (YYYY-MM-DD) for backtest')
    parser.add_argument('--end', help='End date (YYYY-MM-DD) for backtest')
    return parser.parse_args()

def load_historical(symbol, interval, start, end):
    """
    Pull OHLCV from Alpaca (free data) into a pandas DataFrame.
    Requires internet. Cache in a CSV file for future runs.
    """
    cache_file = f'{symbol}_{interval}_{start}_{end}.csv'
    if os.path.exists(cache_file):
        log.info(f"Loading cached data from {cache_file}")
        df = pd.read_csv(cache_file, parse_dates=['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df

    log.info(f"Downloading data for {symbol} from {start} to {end}")
    # Alpaca data API: GET /v2/stocks/{symbol}/bars
    url = f"{BASE_URL}/v2/stocks/{symbol}/bars"
    params = {
        'start': start,
        'end': end,
        'timeframe': interval,
    }
    df = _get(url, params=params)
    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df.to_csv(cache_file)
    return df

def run_backtest():
    symbol = STRATEGY['symbol']
    interval = STRATEGY['interval']
    start = (datetime.datetime.utcnow() - datetime.timedelta(days=STRATEGY['lookback'])).strftime('%Y-%m-%d')
    end = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    df = load_historical(symbol, interval, start, end)
    bt = Backtester(df, initial_capital=100000)
    report = bt.run()
    log.info("Backtest complete. Summary:")
    for k, v in report.items():
        if k not in ['trades']:
            log.info(f"  {k}: {v}")
    log.info(f"Total trades executed: {report['trades']}")
    print("\n=== Backtest Report ===")
    for k, v in report.items():
        print(f"{k:20}: {v}")

def run_paper_trade():
    """
    Paper‑trading mode using Alpaca paper account.
    Connects to the streaming feed? For simplicity, we will poll every 5 minutes.
    """
    symbol = STRATEGY['symbol']
    interval = STRATEGY['interval']
    log.info(f"Starting paper trade for {symbol} at {interval} candles.")
    # Get latest historical to seed indicators
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=1)
    df = load_historical(symbol, interval, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    signals = generate_signals(df)

    # Real-time loop (simplified)
    try:
        while True:
            # Fetch latest bar
            bar = _get(f'/v2/stocks/{symbol}/bars', params={
                'start': (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'timeframe': interval,
            })
            if not bar:
                log.info("No new bar yet.")
                time.sleep(30)
                continue
            new_bar = pd.DataFrame(bar).iloc[-1]
            # Append to df
            df = df.append(new_bar.set_index('timestamp'))
            # Recompute indicators
            df = compute_indicators(df)
            # Generate signals for the last bar
            last_sig = [s for s in signals if s.time == new_bar['timestamp']]
            if last_sig:
                # Place market order
                order_id = place_order(symbol,
                                       qty=position_size(get_account()['cash'],
                                                         RISK['max_per_trade_pct'],
                                                         RISK['exit']['sl_atr_mult'],
                                                         new_bar['atr']),
                                       side='buy',
                                       type_='market',
                                       time_in_force='gtc')
                log.info(f"Order placed: {order_id}")
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Paper trading stopped by user.")

def run_live_trade():
    """Full live‑trading loop with safety checks."""
    confirm = input("=== LIVE TRADING MODE ===\nWARNING: YOU ARE ABOUT TO CONNECT TO A REAL BROKER ACCOUNT.\nDo you want to continue? (yes/no): ")
    if confirm.lower() != 'yes':
        log.warning("Live trade cancelled by user.")
        return

    symbol = STRATEGY['symbol']
    interval = STRATEGY['interval']
    log.info(f"Starting live trade for {symbol}.")

    # Load initial data
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=1)
    df = load_historical(symbol, interval, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
    signals = generate_signals(df)

    # Main loop
    try:
        while True:
            # Grab latest bar
            bar_resp = _get(f'/v2/stocks/{symbol}/bars', params={
                'start': (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'timeframe': interval,
            })
            if not bar_resp:
                log.info("No new bar yet.")
                time.sleep(30)
                continue
            new_bar = pd.DataFrame(bar_resp).iloc[-1]
            df = df.append(new_bar.set_index('timestamp'))
            df = compute_indicators(df)

            # Check for signals on new bar
            sigs = [s for s in signals if s.time == new_bar['timestamp']]
            for sig in sigs:
                # Position sizing
                equity = get_account()['cash']
                size = position_size(equity,
                                     RISK['max_per_trade_pct'],
                                     RISK['exit']['sl_atr_mult'],
                                     sig.atr)
                if size <= 0:
                    log.info("Calculated position size <= 0, skipping.")
                    continue
                # Send market order
                order_id = place_order(symbol,
                                       qty=size,
                                       side='buy',
                                       type_='market',
                                       time_in_force='gtc')
                log.info(f"Placed market order {order_id} for {size} shares at {sig.price}")

            # Sleep until next candle
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Live trading stopped by user.")

def main():
    args = parse_args()
    if args.mode == 'backtest':
        run_backtest()
    elif args.mode == 'paper':
        run_paper_trade()
    elif args.mode == 'live':
        run_live_trade()

if __name__ == '__main__':
    main()

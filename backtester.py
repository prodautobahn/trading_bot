"""
Back‑tester that consumes signals from strategy.py
and executes them on historical OHLCV data.
"""

import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from config import STRATEGY, RISK
from risk import position_size, apply_slippage, apply_commission
from strategy import generate_signals, compute_indicators

log = logging.getLogger(__name__)

class Trade:
    """A single trade record."""
    def __init__(self, entry_time, entry_price, size, atr):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.size = size
        self.atr = atr
        self.exit_time = None
        self.exit_price = None
        self.pnl = None

    def close(self, exit_time, exit_price):
        self.exit_time = exit_time
        self.exit_price = exit_price
        # PnL in USD
        self.pnl = self.size * (self.exit_price - self.entry_price)

class Backtester:
    def __init__(self, df, initial_capital=100000):
        """
        df: OHLCV dataframe with datetime index
        initial_capital: starting equity in USD
        """
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.trades = []
        self.daily_loss_limit = initial_capital * RISK['daily_loss_pct']
        self.max_trades_per_day = RISK['max_trades_per_day']
        self.slippage_pct = RISK['slippage_pct']
        self.commission_per_share = RISK['commission_per_share']

    def run(self):
        """Main loop: generate signals and simulate trades."""
        # Add indicators
        self.df = compute_indicators(self.df)
        signals = generate_signals(self.df)
        positions = {}  # symbol -> open trade
        today = self.df.index[0].date()
        trades_today = []

        for idx, row in self.df.iterrows():
            # 1. Check if any trades should close today
            for sym, trade in list(positions.items()):
                # TP / SL / trailing stop
                if self._should_exit(trade, row):
                    trade.close(idx, row['close'])
                    self.trades.append(trade)
                    trades_today.append(trade)
                    positions.pop(sym)
                    # Update equity
                    self.equity += trade.pnl
                    # Apply commission & slippage
                    commission = apply_commission(trade.size, trade.exit_price,
                                                  self.commission_per_share)
                    self.equity -= commission
                    self.equity -= trade.size * trade.exit_price * self.slippage_pct

            # 2. End of day check
            if idx.time() >= datetime.strptime('15:55', '%H:%M').time():
                # close all open positions at close price
                for sym, trade in list(positions.items()):
                    trade.close(idx, row['close'])
                    self.trades.append(trade)
                    trades_today.append(trade)
                    self.equity += trade.pnl
                    commission = apply_commission(trade.size, trade.exit_price,
                                                  self.commission_per_share)
                    self.equity -= commission
                    self.equity -= trade.size * trade.exit_price * self.slippage_pct
                    positions.pop(sym)

            # 3. Check daily limits
            if sum(t.pnl for t in trades_today) <= -self.daily_loss_limit:
                log.warning("Daily loss limit hit. Stopping trades.")
                break
            if len(trades_today) >= self.max_trades_per_day:
                log.warning("Max trades per day reached. Stopping trades.")
                break

            # 4. Process signals (only long)
            for sig in signals:
                if sig.time == idx:
                    # Position sizing
                    sz = position_size(self.equity, RISK['max_per_trade_pct'],
                                       RISK['exit']['sl_atr_mult'],
                                       sig.atr)
                    if sz <= 0:
                        continue
                    # Simulate immediate market fill
                    trade = Trade(entry_time=idx,
                                  entry_price=apply_slippage(sig.price, self.slippage_pct),
                                  size=sz,
                                  atr=sig.atr)
                    positions[STRATEGY['symbol']] = trade
                    # Deduct initial capital for position
                    self.equity -= sz * trade.entry_price
                    # Deduct commission
                    self.equity -= apply_commission(sz, trade.entry_price,
                                                    self.commission_per_share)

        # Final equity calculation
        final_equity = self.equity
        return self._generate_report(final_equity)

    def _should_exit(self, trade, row):
        """Return True if any exit condition is met."""
        # TP
        tp_price = trade.entry_price + RISK['exit']['tp_atr_mult'] * trade.atr
        tp_price_pct = trade.entry_price * (1 + RISK['exit']['take_profit_pct'])
        # SL
        sl_price = trade.entry_price - RISK['exit']['sl_atr_mult'] * trade.atr
        sl_price_pct = trade.entry_price * (1 - RISK['exit']['stop_loss_pct'])
        # Trailing stop (simple implementation)
        if row['close'] > trade.entry_price:
            trail_stop = row['close'] - RISK['exit']['trailing_atr_mult'] * trade.atr
        else:
            trail_stop = trade.entry_price - RISK['exit']['trailing_atr_mult'] * trade.atr

        if row['close'] >= max(tp_price, tp_price_pct):
            return True
        if row['close'] <= min(sl_price, sl_price_pct):
            return True
        if row['close'] <= trail_stop:
            return True
        return False

    def _generate_report(self, final_equity):
        """Return a dict with performance metrics."""
        pnl_series = pd.Series([t.pnl for t in self.trades])
        returns = pnl_series / self.initial_capital
        sharpe = returns.mean() / returns.std() * np.sqrt(252)  # annualised
        cum_equity = (1 + returns).cumprod() * self.initial_capital
        max_dd = (cum_equity.cummax() - cum_equity).max()

        report = {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'profit_factor': pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum()),
            'win_rate': (pnl_series > 0).mean(),
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'trades': len(self.trades),
        }

        # Plot equity curve
        plt.figure(figsize=(10, 4))
        cum_equity.plot(title='Equity Curve')
        plt.xlabel('Trade #')
        plt.ylabel('Equity (USD)')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('equity_curve.png')
        plt.close()

        # Plot drawdown
        plt.figure(figsize=(10, 4))
        dd = cum_equity.cummax() - cum_equity
        dd.plot(title='Drawdown')
        plt.xlabel('Trade #')
        plt.ylabel('Drawdown (USD)')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('drawdown.png')
        plt.close()

        return report

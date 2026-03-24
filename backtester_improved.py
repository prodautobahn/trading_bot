# backtester_improved.py
"""
Vectorised back‑testing engine for the improved strategy.
Includes slippage, commission, and a realistic execution delay.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging

from strategy_improved import generate_signals
from risk import (
    position_size,
    stop_loss,
    take_profit,
    max_daily_loss,
)

log = logging.getLogger(__name__)

class Trade:
    def __init__(self, entry_time, entry_price, size, atr):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.size = size
        self.atr = atr
        self.exit_time = None
        self.exit_price = None
        self.pnl = 0.0

    def close(self, exit_time, exit_price):
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.pnl = self.size * (self.exit_price - self.entry_price)

class Backtester:
    def __init__(self, df, initial_capital=100000.0):
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.trades = []
        self.daily_losses = {}
        self.max_drawdown = 0.0
        self.slippage_pct = 0.0002          # 0.02 %
        self.commission_per_share = 0.005   # $0.005
        self.stop_mult = 1.5
        self.tp_mult = 2.0

    # ------------------------------------------------------------------
    # Core back‑test loop
    # ------------------------------------------------------------------
    def run(self):
        signals = generate_signals(self.df)
        open_pos = None
        daily_loss = 0.0
        current_date = self.df.index[0].date()

        for ts, row in self.df.iterrows():
            # 1. Close position if exit conditions met
            if open_pos and self._should_exit(open_pos, row):
                open_pos.close(ts, row['close'])
                self._settle_trade(open_pos)
                self.trades.append(open_pos)
                open_pos = None
                # Reset daily loss after each exit
                daily_loss = 0.0
                current_date = ts.date()

            # 2. If any signal at this bar, open new trade
            for sig in [s for s in signals if s.time == ts]:
                # Risk & sizing
                size = position_size(
                    account_equity=self.equity,
                    risk_pct=0.01,
                    atr=sig.atr,
                    stop_mult=self.stop_mult
                )
                if size <= 0:
                    continue

                # Execution delay: pretend we get the price 1 bar later
                delayed_price = self._get_next_bar_price(ts)
                # Apply slippage
                delayed_price = delayed_price * (1 + self.slippage_pct)

                # Place order
                open_pos = Trade(entry_time=ts,
                                 entry_price=delayed_price,
                                 size=size,
                                 atr=sig.atr)
                # Deduct equity & commission
                self.equity -= size * delayed_price
                self.equity -= size * delayed_price * self.commission_per_share
                break   # one trade per signal per bar

            # 3. Update max drawdown
            equity_curve = self._equity_curve()
            self.max_drawdown = max(self.max_drawdown,
                                    equity_curve.max() - equity_curve.min())

            # 4. Daily loss limit check
            if daily_loss <= -max_daily_loss(self.max_drawdown):
                log.warning("Daily loss limit hit. Stopping further trades.")
                break

        # Final equity snapshot
        final_equity = self.equity + sum(
            t.pnl for t in self.trades if t.exit_price is None
        )
        return self._report(final_equity)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _get_next_bar_price(self, ts):
        """Return close price of the next bar after ts."""
        try:
            return self.df.loc[ts + timedelta(minutes=5), 'close']
        except KeyError:
            # If no next bar (end of dataset), use current
            return self.df.loc[ts, 'close']

    def _should_exit(self, trade, row):
        """Return True if TP, SL, or trailing stop hit."""
        # Stop‑loss
        if row['close'] <= stop_loss(trade.entry_price, trade.atr, self.stop_mult):
            return True
        # Take‑profit
        if row['close'] >= take_profit(trade.entry_price, trade.atr, self.tp_mult):
            return True
        # Trailing stop (1 ATR cushion)
        trail_stop = max(
            trade.entry_price,
            row['high'] - self.stop_mult * trade.atr
        )
        if row['close'] <= trail_stop:
            return True
        return False

    def _settle_trade(self, trade):
        """Apply PnL, commission, slippage on trade close."""
        trade.close(trade.exit_time, trade.exit_price)
        self.equity += trade.pnl
        self.equity -= trade.size * trade.exit_price * self.commission_per_share
        self.equity -= trade.size * trade.exit_price * self.slippage_pct

    def _equity_curve(self):
        """Return equity series for max drawdown calculation."""
        equity = self.initial_capital
        equity_series = [equity]
        for t in self.trades:
            equity += t.pnl
            equity_series.append(equity)
        return pd.Series(equity_series)

    def _report(self, final_equity):
        returns = [(t.pnl / self.initial_capital) for t in self.trades]
        returns_series = pd.Series(returns)
        sharpe = np.sqrt(252) * returns_series.mean() / returns_series.std() if returns_series.std() != 0 else 0
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'profit_factor': sum(t.pnl for t in self.trades if t.pnl > 0) / \
                              abs(sum(t.pnl for t in self.trades if t.pnl < 0)),
            'sharpe': sharpe,
            'max_drawdown': self.max_drawdown,
            'win_rate': sum(1 for t in self.trades if t.pnl > 0) / len(self.trades) if self.trades else 0,
            'trades': len(self.trades),
        }

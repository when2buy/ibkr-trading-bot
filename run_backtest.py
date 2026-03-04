"""
Offline backtest — SPY EMA crossover, last 30 days (yfinance).
Usage: python run_backtest.py
"""
import os, sys, logging
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

from strategies.spy_momentum import run_backtest
import config

if __name__ == '__main__':
    os.makedirs(config.LOG_DIR, exist_ok=True)

    stats, equity = run_backtest(days=30)

    print("\n" + "="*55)
    print("  SPY EMA Crossover (9/21) — 30-Day Backtest Results")
    print("="*55)
    print(f"  Total trades  : {stats['total_trades']}")
    print(f"  Win rate      : {stats['win_rate']}%")
    print(f"  Total P&L     : ${stats['total_pnl']:+,.2f}")
    print(f"  Avg per trade : ${stats['avg_trade']:+,.2f}")
    print(f"  Max drawdown  : {stats['max_drawdown']}%")
    print(f"  Sharpe ratio  : {stats['sharpe']}")
    print(f"  Final equity  : ${stats['equity_final']:,.2f}")
    print("="*55 + "\n")

    out = os.path.join(config.LOG_DIR, 'backtest_equity.csv')
    equity.to_csv(out)
    print(f"Equity curve saved to {out}")

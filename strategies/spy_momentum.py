"""
SPY EMA Crossover Momentum Strategy
────────────────────────────────────
Signal:
  - EMA(9) crosses above EMA(21) → BUY  10 shares
  - EMA(9) crosses below EMA(21) → SELL 10 shares (exit + optionally short)

Risk:
  - Max 1 position at a time
  - Stop loss: 0.5% from entry price
  - Capital: $200,000 allocated
  - Outside market hours: replay last 30 days yfinance data as simulation
"""
import asyncio, logging
from datetime import datetime, timezone
from collections import deque

import pandas as pd
import numpy as np
import yfinance as yf

from strategies.base import StrategyBase
from engine.risk_manager import StrategyRiskConfig

logger = logging.getLogger('strategy.spy_momentum')

SYMBOL       = 'SPY'
FAST_PERIOD  = 9
SLOW_PERIOD  = 21
SHARES       = 10
STOP_PCT     = 0.005   # 0.5%
ALLOCATION   = 200_000
MAX_POS_VAL  = 20_000  # max $20K per position
MAX_DAILY_LOS = 2_000  # stop after $2K daily loss

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _is_market_hours() -> bool:
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=14, minute=30, second=0, microsecond=0)
    c = now.replace(hour=21, minute=0,  second=0, microsecond=0)
    return o <= now <= c


class SPYMomentum(StrategyBase):
    def __init__(self, hub, data_mgr, order_mgr, risk_mgr):
        super().__init__('spy_momentum', ALLOCATION, hub, data_mgr, order_mgr, risk_mgr)

        # register risk limits for this strategy
        risk_mgr.register_strategy(StrategyRiskConfig(
            strategy_id        = 'spy_momentum',
            capital_allocation = ALLOCATION,
            max_position_value = MAX_POS_VAL,
            max_daily_loss     = MAX_DAILY_LOS,
        ))

        self._closes:     deque = deque(maxlen=SLOW_PERIOD + 5)
        self._last_signal = None   # 'long' | 'flat'
        self._stop_price  = None
        self._last_price  = 0.0
        self._bar_count   = 0

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def on_start(self):
        logger.info(f"SPY Momentum starting | market_hours={_is_market_hours()}")

        # Seed buffer with recent bars
        df = self.data.get_bars(SYMBOL, period='5 D', interval='5 mins')
        if not df.empty:
            for close in df['Close'].values[-SLOW_PERIOD:]:
                self._closes.append(float(close))
            logger.info(f"Seeded with {len(self._closes)} bars")

        # Subscribe to live bars (fires on_bar each 5-min bar close)
        self.data.subscribe_realtime(SYMBOL, self.on_bar)

    def on_bar(self, symbol: str, bar):
        """Called on every new 5-min bar (live OR simulated)."""
        if symbol != SYMBOL:
            return

        close = getattr(bar, 'close', None) or getattr(bar, 'Close', None)
        if close is None:
            return

        self._closes.append(float(close))
        self._last_price = float(close)
        self._bar_count += 1

        if len(self._closes) < SLOW_PERIOD:
            return   # not enough data yet

        series = pd.Series(list(self._closes))
        ema_fast = _ema(series, FAST_PERIOD).iloc[-1]
        ema_slow = _ema(series, SLOW_PERIOD).iloc[-1]
        prev_fast = _ema(series, FAST_PERIOD).iloc[-2]
        prev_slow = _ema(series, SLOW_PERIOD).iloc[-2]

        bullish = (prev_fast <= prev_slow) and (ema_fast > ema_slow)
        bearish = (prev_fast >= prev_slow) and (ema_fast < ema_slow)

        # ── stop loss check ──
        if self._position > 0 and self._stop_price and close < self._stop_price:
            logger.info(f"⛔ STOP LOSS hit @ {close:.2f} (stop={self._stop_price:.2f})")
            self.sell(SYMBOL, self._position, price=close)
            self._last_signal = 'flat'
            self._stop_price  = None
            return

        # ── entry / exit signals ──
        if bullish and self._last_signal != 'long' and self._position == 0:
            logger.info(f"📈 BUY signal | EMA9={ema_fast:.2f} > EMA21={ema_slow:.2f} | close={close:.2f}")
            ok, _ = self.buy(SYMBOL, SHARES, price=close)
            if ok:
                self._last_signal = 'long'
                self._stop_price  = close * (1 - STOP_PCT)
                logger.info(f"Stop loss set @ {self._stop_price:.2f}")

        elif bearish and self._position > 0:
            logger.info(f"📉 SELL signal | EMA9={ema_fast:.2f} < EMA21={ema_slow:.2f} | close={close:.2f}")
            self.sell(SYMBOL, self._position, price=close)
            self._last_signal = 'flat'
            self._stop_price  = None

        # Status every 10 bars
        if self._bar_count % 10 == 0:
            logger.info(self.status_line(close) +
                        f" | EMA9={ema_fast:.2f} EMA21={ema_slow:.2f}")

    def on_fill(self, fill):
        pass  # OrderManager handles fill logging


# ─────────────────────────────────────────────────────────────
# Offline backtest (yfinance)
# ─────────────────────────────────────────────────────────────
def run_backtest(days: int = 30) -> dict:
    """Run EMA crossover backtest on yfinance 5-min data. Returns stats dict."""
    logger.info(f"Downloading {SYMBOL} 5-min data ({days}d)...")
    df = yf.Ticker(SYMBOL).history(period=f'{days}d', interval='5m')
    df = df[['Close']].dropna()

    df['ema_fast'] = _ema(df['Close'], FAST_PERIOD)
    df['ema_slow'] = _ema(df['Close'], SLOW_PERIOD)
    df['signal']   = 0

    # Generate signals
    for i in range(1, len(df)):
        pf = df['ema_fast'].iloc[i-1]; cf = df['ema_fast'].iloc[i]
        ps = df['ema_slow'].iloc[i-1]; cs = df['ema_slow'].iloc[i]
        if pf <= ps and cf > cs:
            df.iloc[i, df.columns.get_loc('signal')] = 1   # buy
        elif pf >= ps and cf < cs:
            df.iloc[i, df.columns.get_loc('signal')] = -1  # sell/exit

    # Simulate trades
    position = 0
    entry    = 0.0
    stop     = 0.0
    trades   = []
    equity   = [ALLOCATION]

    for i, row in df.iterrows():
        close = row['Close']

        # stop loss
        if position > 0 and stop and close < stop:
            pnl = (close - entry) * SHARES
            trades.append({'type': 'stop', 'entry': entry, 'exit': close,
                           'pnl': pnl, 'bars': 0})
            equity.append(equity[-1] + pnl)
            position = 0; entry = 0.0; stop = 0.0
            continue

        if row['signal'] == 1 and position == 0:
            position = SHARES; entry = close; stop = close * (1 - STOP_PCT)
        elif row['signal'] == -1 and position > 0:
            pnl = (close - entry) * SHARES
            trades.append({'type': 'signal', 'entry': entry, 'exit': close,
                           'pnl': pnl, 'bars': 0})
            equity.append(equity[-1] + pnl)
            position = 0; entry = 0.0; stop = 0.0

    # Close any open position at end
    if position > 0:
        pnl = (df['Close'].iloc[-1] - entry) * SHARES
        trades.append({'type': 'open', 'entry': entry,
                       'exit': df['Close'].iloc[-1], 'pnl': pnl, 'bars': 0})
        equity.append(equity[-1] + pnl)

    # Stats
    pnls = [t['pnl'] for t in trades]
    wins  = [p for p in pnls if p > 0]
    total_pnl  = sum(pnls)
    win_rate   = len(wins) / len(pnls) if pnls else 0
    equity_arr = np.array(equity)
    dd_arr     = (equity_arr - np.maximum.accumulate(equity_arr)) / \
                 np.maximum.accumulate(equity_arr)
    max_dd     = dd_arr.min()
    returns    = pd.Series(equity).pct_change().dropna()
    sharpe     = (returns.mean() / returns.std() * np.sqrt(252 * 78)) \
                 if returns.std() > 0 else 0.0

    stats = {
        'total_trades': len(trades),
        'win_rate':     round(win_rate * 100, 1),
        'total_pnl':    round(total_pnl, 2),
        'avg_trade':    round(total_pnl / len(trades), 2) if trades else 0,
        'max_drawdown': round(max_dd * 100, 2),
        'sharpe':       round(sharpe, 2),
        'equity_final': round(equity[-1], 2),
    }
    return stats, pd.Series(equity, name='equity')

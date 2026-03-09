"""
SPY Breakout Momentum Strategy
───────────────────────────────
Signal:
  ENTRY: Price > EMA(50) AND price >= 20-day rolling high → BUY 95% of capital
  EXIT:  +8% profit target OR -4% stop loss OR price < EMA(50)

Risk:
  - Max 1 position at a time
  - Capital: $200,000 allocated
  - Daily bars for signals, 5-min bars for intraday monitoring
"""
import logging
from datetime import datetime, timezone
from collections import deque

import pandas as pd
import numpy as np
import yfinance as yf

from strategies.base import StrategyBase
from engine.risk_manager import StrategyRiskConfig

logger = logging.getLogger('strategy.spy_breakout')

SYMBOL        = 'SPY'
EMA_PERIOD    = 50
ROLLING_HIGH  = 20       # 20-day rolling high lookback
PROFIT_TARGET = 0.08     # +8%
STOP_LOSS     = 0.04     # -4%
CAPITAL_PCT   = 0.95     # 95% of capital
ALLOCATION    = 200_000
MAX_POS_VAL   = 190_000  # 95% of 200K
MAX_DAILY_LOS = 8_000    # 4% of 200K


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _is_market_hours() -> bool:
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=14, minute=30, second=0, microsecond=0)
    c = now.replace(hour=21, minute=0,  second=0, microsecond=0)
    return o <= now <= c


class SPYBreakout(StrategyBase):
    def __init__(self, hub, data_mgr, order_mgr, risk_mgr):
        super().__init__('spy_breakout', ALLOCATION, hub, data_mgr, order_mgr, risk_mgr)

        # register risk limits for this strategy
        risk_mgr.register_strategy(StrategyRiskConfig(
            strategy_id        = 'spy_breakout',
            capital_allocation = ALLOCATION,
            max_position_value = MAX_POS_VAL,
            max_daily_loss     = MAX_DAILY_LOS,
        ))

        self._closes:     deque = deque(maxlen=EMA_PERIOD + ROLLING_HIGH + 5)
        self._daily_highs: deque = deque(maxlen=ROLLING_HIGH + 5)
        self._last_signal = None   # 'long' | 'flat'
        self._stop_price  = None
        self._target_price = None
        self._last_price  = 0.0
        self._bar_count   = 0

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def on_start(self):
        logger.info(f"SPY Breakout starting | market_hours={_is_market_hours()}")

        # Seed buffer with recent daily bars for EMA(50) + 20-day high
        df = self.data.get_bars(SYMBOL, period='60 D', interval='1 day')
        if not df.empty:
            for close in df['Close'].values[-(EMA_PERIOD + ROLLING_HIGH):]:
                self._closes.append(float(close))
            for high in df['High'].values[-ROLLING_HIGH:]:
                self._daily_highs.append(float(high))
            logger.info(f"Seeded with {len(self._closes)} daily closes, "
                        f"{len(self._daily_highs)} daily highs")

        # Subscribe to live bars (fires on_bar each 5-min bar close)
        self.data.subscribe_realtime(SYMBOL, self.on_bar)

    def on_bar(self, symbol: str, bar):
        """Called on every new 5-min bar (live OR simulated)."""
        if symbol != SYMBOL:
            return

        close = getattr(bar, 'close', None) or getattr(bar, 'Close', None)
        high  = getattr(bar, 'high', None)  or getattr(bar, 'High', None) or close
        if close is None:
            return

        close = float(close)
        high  = float(high)
        self._last_price = close
        self._bar_count += 1

        # Track daily highs (approximate: use bar high)
        self._daily_highs.append(high)

        # Also add to closes for EMA calculation
        self._closes.append(close)

        if len(self._closes) < EMA_PERIOD:
            return   # not enough data yet

        series = pd.Series(list(self._closes))
        ema50  = _ema(series, EMA_PERIOD).iloc[-1]

        # 20-day rolling high
        rolling_high_20 = max(list(self._daily_highs)[-ROLLING_HIGH:]) \
            if len(self._daily_highs) >= ROLLING_HIGH else max(self._daily_highs)

        # ── exit checks (profit target / stop loss / EMA break) ──
        if self._position > 0:
            # Profit target
            if self._target_price and close >= self._target_price:
                logger.info(f"🎯 PROFIT TARGET hit @ {close:.2f} "
                            f"(target={self._target_price:.2f})")
                self.sell(SYMBOL, self._position, price=close)
                self._last_signal  = 'flat'
                self._stop_price   = None
                self._target_price = None
                return

            # Stop loss
            if self._stop_price and close <= self._stop_price:
                logger.info(f"⛔ STOP LOSS hit @ {close:.2f} "
                            f"(stop={self._stop_price:.2f})")
                self.sell(SYMBOL, self._position, price=close)
                self._last_signal  = 'flat'
                self._stop_price   = None
                self._target_price = None
                return

            # EMA breakdown exit
            if close < ema50:
                logger.info(f"📉 EMA BREAK exit @ {close:.2f} "
                            f"(EMA50={ema50:.2f})")
                self.sell(SYMBOL, self._position, price=close)
                self._last_signal  = 'flat'
                self._stop_price   = None
                self._target_price = None
                return

        # ── entry signal ──
        breakout = close > ema50 and close >= rolling_high_20
        if breakout and self._last_signal != 'long' and self._position == 0:
            # Buy 95% of capital
            shares = int((ALLOCATION * CAPITAL_PCT) / close)
            if shares > 0:
                logger.info(f"🚀 BREAKOUT BUY | {shares} shares @ {close:.2f} | "
                            f"EMA50={ema50:.2f} | 20d_high={rolling_high_20:.2f}")
                ok, _ = self.buy(SYMBOL, shares, price=close)
                if ok:
                    self._last_signal  = 'long'
                    self._stop_price   = close * (1 - STOP_LOSS)
                    self._target_price = close * (1 + PROFIT_TARGET)
                    logger.info(f"Stop={self._stop_price:.2f} | "
                                f"Target={self._target_price:.2f}")

        # Status every 10 bars
        if self._bar_count % 10 == 0:
            logger.info(self.status_line(close) +
                        f" | EMA50={ema50:.2f} | 20d_high={rolling_high_20:.2f}")

    def on_fill(self, fill):
        pass  # OrderManager handles fill logging


# ─────────────────────────────────────────────────────────────
# Offline backtest (yfinance)
# ─────────────────────────────────────────────────────────────
def run_backtest(days: int = 60) -> dict:
    """Run breakout momentum backtest on yfinance daily data. Returns stats dict."""
    logger.info(f"Downloading {SYMBOL} daily data ({days}d)...")
    df = yf.Ticker(SYMBOL).history(period=f'{days}d', interval='1d')
    df = df[['Open', 'High', 'Low', 'Close']].dropna()

    df['ema50']       = _ema(df['Close'], EMA_PERIOD)
    df['rolling_high'] = df['High'].rolling(ROLLING_HIGH).max()
    df['signal']       = 0

    # Generate signals
    for i in range(EMA_PERIOD, len(df)):
        close = df['Close'].iloc[i]
        ema   = df['ema50'].iloc[i]
        rh    = df['rolling_high'].iloc[i]
        if pd.isna(rh):
            continue
        if close > ema and close >= rh:
            df.iloc[i, df.columns.get_loc('signal')] = 1   # buy

    # Simulate trades
    position   = 0
    entry      = 0.0
    stop       = 0.0
    target     = 0.0
    shares     = 0
    trades     = []
    equity     = [ALLOCATION]

    for i, row in df.iterrows():
        close = row['Close']
        ema   = row['ema50']

        if position > 0:
            # Check exits
            exit_reason = None
            if close >= target:
                exit_reason = 'target'
            elif close <= stop:
                exit_reason = 'stop'
            elif close < ema:
                exit_reason = 'ema_break'

            if exit_reason:
                pnl = (close - entry) * shares
                trades.append({'type': exit_reason, 'entry': entry,
                               'exit': close, 'pnl': pnl, 'shares': shares})
                equity.append(equity[-1] + pnl)
                position = 0; entry = 0.0; stop = 0.0; target = 0.0; shares = 0
                continue

        if row['signal'] == 1 and position == 0:
            shares   = int((ALLOCATION * CAPITAL_PCT) / close)
            position = shares
            entry    = close
            stop     = close * (1 - STOP_LOSS)
            target   = close * (1 + PROFIT_TARGET)

    # Close any open position at end
    if position > 0:
        close = df['Close'].iloc[-1]
        pnl   = (close - entry) * shares
        trades.append({'type': 'open', 'entry': entry,
                       'exit': close, 'pnl': pnl, 'shares': shares})
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
    sharpe     = (returns.mean() / returns.std() * np.sqrt(252)) \
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

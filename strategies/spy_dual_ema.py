"""
SPY Dual EMA + Volatility Filter Strategy
──────────────────────────────────────────
Signal:
  - EMA(20) crosses above EMA(60) (golden cross)
  - Realized volatility < 2.2% (low vol filter — avoid choppy markets)
  → BUY full position

Exit:
  - 6% trailing stop
  - EMA(20) crosses below EMA(60) (death cross)

Conservative strategy — fewer trades, avoids high-vol regimes.
"""
import logging
from datetime import datetime, timezone
from collections import deque
import pandas as pd
import numpy as np
import yfinance as yf

from strategies.base import StrategyBase
from engine.risk_manager import StrategyRiskConfig

logger = logging.getLogger('strategy.spy_dual_ema')

SYMBOL       = 'SPY'
FAST_EMA     = 20
SLOW_EMA     = 60
VOL_WINDOW   = 10
VOL_THRESHOLD = 0.022  # 2.2% daily vol
TRAIL_PCT    = 0.06     # 6% trailing stop
ALLOCATION   = 200_000
MAX_POS_VAL  = 190_000
MAX_DAILY_LOSS = 6_000


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _is_market_hours():
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=14, minute=30, second=0, microsecond=0)
    c = now.replace(hour=21, minute=0, second=0, microsecond=0)
    return o <= now <= c


class SPYDualEMA(StrategyBase):
    def __init__(self, hub, data_mgr, order_mgr, risk_mgr):
        super().__init__('spy_dual_ema', ALLOCATION, hub, data_mgr, order_mgr, risk_mgr)

        risk_mgr.register_strategy(StrategyRiskConfig(
            strategy_id='spy_dual_ema',
            capital_allocation=ALLOCATION,
            max_position_value=MAX_POS_VAL,
            max_daily_loss=MAX_DAILY_LOSS,
        ))

        self._closes = deque(maxlen=SLOW_EMA + 10)
        self._trail_stop = None
        self._last_price = 0.0
        self._bar_count = 0
        self._prev_fast = None
        self._prev_slow = None

    def on_start(self):
        logger.info(f"SPY Dual EMA starting | market_hours={_is_market_hours()}")
        try:
            df = yf.Ticker(SYMBOL).history(period='120d', interval='1d')
            if not df.empty:
                for close in df['Close'].values:
                    self._closes.append(float(close))
                logger.info(f"Seeded with {len(self._closes)} daily bars")
        except Exception as e:
            logger.warning(f"Failed to seed data: {e}")

        self.data.subscribe_realtime(SYMBOL, self.on_bar)

    def _realized_vol(self):
        if len(self._closes) < VOL_WINDOW + 1:
            return 0.01
        recent = list(self._closes)[-VOL_WINDOW - 1:]
        returns = np.diff(np.log(recent))
        return float(np.std(returns))

    def on_bar(self, symbol, bar):
        if symbol != SYMBOL:
            return

        close = getattr(bar, 'close', None) or getattr(bar, 'Close', None)
        if close is None:
            return

        self._closes.append(float(close))
        self._last_price = float(close)
        self._bar_count += 1

        if len(self._closes) < SLOW_EMA:
            return

        series = pd.Series(list(self._closes))
        fast = _ema(series, FAST_EMA).iloc[-1]
        slow = _ema(series, SLOW_EMA).iloc[-1]

        # Detect crossover
        bullish_cross = False
        bearish_cross = False
        if self._prev_fast is not None and self._prev_slow is not None:
            bullish_cross = (self._prev_fast <= self._prev_slow) and (fast > slow)
            bearish_cross = (self._prev_fast >= self._prev_slow) and (fast < slow)

        self._prev_fast = fast
        self._prev_slow = slow

        rv = self._realized_vol()
        low_vol = rv < VOL_THRESHOLD
        p = float(close)

        if not self._position:
            if bullish_cross and low_vol:
                size = int(self.capital_allocation * 0.95 / p)
                if size > 0:
                    logger.info(f"📈 GOLDEN CROSS BUY | EMA20={fast:.2f} > EMA60={slow:.2f} vol={rv:.4f}")
                    ok, _ = self.buy(SYMBOL, size, price=p)
                    if ok:
                        self._trail_stop = p * (1 - TRAIL_PCT)
                        logger.info(f"Trailing stop set @ {self._trail_stop:.2f}")
        else:
            # Update trailing stop
            new_trail = p * (1 - TRAIL_PCT)
            if self._trail_stop and new_trail > self._trail_stop:
                self._trail_stop = new_trail

            # Exit on trailing stop or death cross
            hit_stop = self._trail_stop and p < self._trail_stop
            if hit_stop or bearish_cross:
                reason = "TRAIL STOP" if hit_stop else "DEATH CROSS"
                logger.info(f"📉 {reason} SELL | price={p:.2f} EMA20={fast:.2f} EMA60={slow:.2f}")
                self.sell(SYMBOL, self._position, price=p)
                self._trail_stop = None

        if self._bar_count % 10 == 0:
            logger.info(self.status_line(p) + f" | EMA20={fast:.2f} EMA60={slow:.2f} vol={rv:.4f}")


def run_backtest(days=365):
    """Run backtest on yfinance daily data."""
    df = yf.Ticker(SYMBOL).history(period=f'{days}d', interval='1d')
    df = df[['Close']].dropna()
    closes = df['Close']
    fast = _ema(closes, FAST_EMA)
    slow = _ema(closes, SLOW_EMA)

    position = 0
    entry = 0.0
    trail = 0.0
    trades = []
    equity = [ALLOCATION]

    for i in range(SLOW_EMA + 1, len(df)):
        p = closes.iloc[i]
        f_curr, f_prev = fast.iloc[i], fast.iloc[i - 1]
        s_curr, s_prev = slow.iloc[i], slow.iloc[i - 1]

        recent = closes.iloc[max(0, i - VOL_WINDOW):i + 1]
        rv = float(np.std(np.diff(np.log(recent.values)))) if len(recent) > 1 else 0.01

        bull = (f_prev <= s_prev) and (f_curr > s_curr)
        bear = (f_prev >= s_prev) and (f_curr < s_curr)

        if position == 0:
            if bull and rv < VOL_THRESHOLD:
                size = int(equity[-1] * 0.95 / p)
                if size > 0:
                    position = size
                    entry = p
                    trail = p * (1 - TRAIL_PCT)
        else:
            new_trail = p * (1 - TRAIL_PCT)
            if new_trail > trail:
                trail = new_trail
            if p < trail or bear:
                pnl = (p - entry) * position
                trades.append({'entry': entry, 'exit': p, 'pnl': pnl})
                equity.append(equity[-1] + pnl)
                position = 0

    if position > 0:
        pnl = (closes.iloc[-1] - entry) * position
        trades.append({'entry': entry, 'exit': closes.iloc[-1], 'pnl': pnl})
        equity.append(equity[-1] + pnl)

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    total_pnl = sum(pnls)
    equity_arr = np.array(equity)
    dd = (equity_arr - np.maximum.accumulate(equity_arr)) / np.maximum.accumulate(equity_arr)
    returns = pd.Series(equity).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

    return {
        'total_trades': len(trades),
        'win_rate': round(len(wins) / len(pnls) * 100, 1) if pnls else 0,
        'total_pnl': round(total_pnl, 2),
        'avg_trade': round(total_pnl / len(trades), 2) if trades else 0,
        'max_drawdown': round(dd.min() * 100, 2),
        'sharpe': round(sharpe, 2),
        'equity_final': round(equity[-1], 2),
    }, pd.Series(equity, name='equity')

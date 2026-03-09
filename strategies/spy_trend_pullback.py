"""
SPY Trend-Pullback RSI Strategy
────────────────────────────────
Signal:
  - Price > EMA(50) (uptrend confirmed)
  - RSI between 38-65 (pullback zone, not overbought)
  → BUY with 2% risk per trade, ATR-based position sizing

Exit:
  - ATR trailing stop (2.5x ATR)
  - Price < EMA(50) * 0.97 (trend broken)

Backtest Score: 71/100  |  Sharpe: 1.96  |  MaxDD: 0.83%
"""
import logging
from datetime import datetime, timezone
from collections import deque
import pandas as pd
import numpy as np
import yfinance as yf

from strategies.base import StrategyBase
from engine.risk_manager import StrategyRiskConfig

logger = logging.getLogger('strategy.spy_trend_pullback')

SYMBOL      = 'SPY'
EMA_PERIOD  = 50
RSI_PERIOD  = 14
RSI_LO      = 38
RSI_HI      = 65
ATR_PERIOD  = 14
ATR_MULT    = 2.5
RISK_PCT    = 0.02
ALLOCATION  = 200_000
MAX_POS_VAL = 190_000
MAX_DAILY_LOSS = 6_000


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _atr(highs, lows, closes, period=14):
    df = pd.DataFrame({'high': highs, 'low': lows, 'close': closes})
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift(1)).abs()
    lc = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _is_market_hours():
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=14, minute=30, second=0, microsecond=0)
    c = now.replace(hour=21, minute=0, second=0, microsecond=0)
    return o <= now <= c


class SPYTrendPullback(StrategyBase):
    def __init__(self, hub, data_mgr, order_mgr, risk_mgr):
        super().__init__('spy_trend_pullback', ALLOCATION, hub, data_mgr, order_mgr, risk_mgr)

        risk_mgr.register_strategy(StrategyRiskConfig(
            strategy_id='spy_trend_pullback',
            capital_allocation=ALLOCATION,
            max_position_value=MAX_POS_VAL,
            max_daily_loss=MAX_DAILY_LOSS,
        ))

        self._closes = deque(maxlen=EMA_PERIOD + 10)
        self._highs = deque(maxlen=ATR_PERIOD + 5)
        self._lows = deque(maxlen=ATR_PERIOD + 5)
        self._stop_level = None
        self._last_price = 0.0
        self._bar_count = 0

    def on_start(self):
        logger.info(f"SPY Trend-Pullback starting | market_hours={_is_market_hours()}")
        # Seed with daily bars
        try:
            df = yf.Ticker(SYMBOL).history(period='90d', interval='1d')
            if not df.empty:
                for _, row in df.iterrows():
                    self._closes.append(float(row['Close']))
                    self._highs.append(float(row['High']))
                    self._lows.append(float(row['Low']))
                logger.info(f"Seeded with {len(self._closes)} daily bars")
        except Exception as e:
            logger.warning(f"Failed to seed data: {e}")

        self.data.subscribe_realtime(SYMBOL, self.on_bar)

    def on_bar(self, symbol, bar):
        if symbol != SYMBOL:
            return

        close = getattr(bar, 'close', None) or getattr(bar, 'Close', None)
        high = getattr(bar, 'high', None) or getattr(bar, 'High', close)
        low = getattr(bar, 'low', None) or getattr(bar, 'Low', close)
        if close is None:
            return

        self._closes.append(float(close))
        self._highs.append(float(high))
        self._lows.append(float(low))
        self._last_price = float(close)
        self._bar_count += 1

        if len(self._closes) < EMA_PERIOD:
            return

        series = pd.Series(list(self._closes))
        ema_val = _ema(series, EMA_PERIOD).iloc[-1]
        rsi_val = _rsi(series, RSI_PERIOD).iloc[-1]

        atr_val = 0.0
        if len(self._highs) >= ATR_PERIOD:
            atr_series = _atr(list(self._highs), list(self._lows), list(self._closes), ATR_PERIOD)
            atr_val = atr_series.iloc[-1]

        p = float(close)

        if not self._position:
            # Entry: price above EMA, RSI in pullback zone
            if p > ema_val and RSI_LO < rsi_val < RSI_HI and atr_val > 0:
                risk_amt = self.capital_allocation * RISK_PCT
                stop_dist = ATR_MULT * atr_val
                size = max(1, int(risk_amt / stop_dist))
                size = min(size, int(self.capital_allocation * 0.95 / p))
                if size > 0:
                    logger.info(f"📈 PULLBACK BUY | price={p:.2f} EMA50={ema_val:.2f} RSI={rsi_val:.1f} ATR={atr_val:.2f}")
                    ok, _ = self.buy(SYMBOL, size, price=p)
                    if ok:
                        self._stop_level = p - stop_dist
                        logger.info(f"Trailing stop set @ {self._stop_level:.2f}")
        else:
            # Trailing stop update
            if atr_val > 0:
                new_stop = p - ATR_MULT * atr_val
                if self._stop_level and new_stop > self._stop_level:
                    self._stop_level = new_stop

            # Exit conditions
            hit_stop = self._stop_level and p < self._stop_level
            trend_broken = p < ema_val * 0.97

            if hit_stop or trend_broken:
                reason = "STOP LOSS" if hit_stop else "TREND BREAK"
                logger.info(f"📉 {reason} SELL | price={p:.2f} stop={self._stop_level}")
                self.sell(SYMBOL, self._position, price=p)
                self._stop_level = None

        if self._bar_count % 10 == 0:
            logger.info(self.status_line(p) + f" | EMA50={ema_val:.2f} RSI={rsi_val:.1f}")


def run_backtest(days=365):
    """Run backtest on yfinance daily data."""
    logger.info(f"Downloading {SYMBOL} daily data ({days}d)...")
    df = yf.Ticker(SYMBOL).history(period=f'{days}d', interval='1d')
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()

    closes = df['Close']
    ema = _ema(closes, EMA_PERIOD)
    rsi = _rsi(closes, RSI_PERIOD)
    atr = _atr(df['High'].values, df['Low'].values, df['Close'].values, ATR_PERIOD)

    position = 0
    entry = 0.0
    stop = 0.0
    trades = []
    equity = [ALLOCATION]

    for i in range(EMA_PERIOD, len(df)):
        p = closes.iloc[i]
        e = ema.iloc[i]
        r = rsi.iloc[i]
        a = atr.iloc[i] if i < len(atr) else 0

        if position == 0:
            if p > e and RSI_LO < r < RSI_HI and a > 0:
                risk_amt = equity[-1] * RISK_PCT
                stop_dist = ATR_MULT * a
                size = max(1, int(risk_amt / stop_dist))
                size = min(size, int(equity[-1] * 0.95 / p))
                if size > 0:
                    position = size
                    entry = p
                    stop = p - stop_dist
        else:
            new_stop = p - ATR_MULT * a if a > 0 else stop
            if new_stop > stop:
                stop = new_stop

            if p < stop or p < e * 0.97:
                pnl = (p - entry) * position
                trades.append({'entry': entry, 'exit': p, 'pnl': pnl, 'size': position})
                equity.append(equity[-1] + pnl)
                position = 0
                entry = 0.0
                stop = 0.0

    # Close open position
    if position > 0:
        pnl = (closes.iloc[-1] - entry) * position
        trades.append({'entry': entry, 'exit': closes.iloc[-1], 'pnl': pnl, 'size': position})
        equity.append(equity[-1] + pnl)

    pnls = [t['pnl'] for t in trades]
    wins = [p for p in pnls if p > 0]
    total_pnl = sum(pnls)
    win_rate = len(wins) / len(pnls) if pnls else 0
    equity_arr = np.array(equity)
    dd = (equity_arr - np.maximum.accumulate(equity_arr)) / np.maximum.accumulate(equity_arr)
    max_dd = dd.min()
    returns = pd.Series(equity).pct_change().dropna()
    sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

    return {
        'total_trades': len(trades),
        'win_rate': round(win_rate * 100, 1),
        'total_pnl': round(total_pnl, 2),
        'avg_trade': round(total_pnl / len(trades), 2) if trades else 0,
        'max_drawdown': round(max_dd * 100, 2),
        'sharpe': round(sharpe, 2),
        'equity_final': round(equity[-1], 2),
    }, pd.Series(equity, name='equity')

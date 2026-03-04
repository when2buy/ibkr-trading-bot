"""
DataManager — market data subscriptions + historical bars.
One subscription per symbol regardless of how many strategies want it.
"""
import logging, asyncio
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
from ib_insync import Stock, util

logger = logging.getLogger('engine.data')

def _is_market_hours():
    now = datetime.now(timezone.utc)
    # US market: Mon-Fri 14:30-21:00 UTC
    if now.weekday() >= 5:
        return False
    market_open  = now.replace(hour=14, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=21, minute=0,  second=0, microsecond=0)
    return market_open <= now <= market_close

class DataManager:
    def __init__(self, hub):
        self.hub = hub
        self._tickers  = {}   # symbol -> ib_insync Ticker
        self._callbacks = {}  # symbol -> [callback, ...]
        self._bar_subs  = {}  # symbol -> ib_insync BarDataList

    # ── historical ──────────────────────────────────────────────────────────
    def get_bars(self, symbol: str, period: str = '5 D',
                 interval: str = '5 mins') -> pd.DataFrame:
        """
        Returns OHLCV DataFrame. Tries IBKR BID_ASK first, falls back to yfinance.
        interval: IBKR style ('5 mins', '1 hour') — auto-converts to yfinance style.
        """
        if self.hub.is_connected:
            try:
                contract = Stock(symbol, 'SMART', 'USD')
                self.hub.ib.qualifyContracts(contract)
                bars = self.hub.ib.reqHistoricalData(
                    contract, endDateTime='', durationStr=period,
                    barSizeSetting=interval, whatToShow='BID_ASK',
                    useRTH=False, formatDate=1, timeout=10)
                if bars:
                    df = util.df(bars)[['date','open','high','low','close','volume']].copy()
                    df.columns = ['Date','Open','High','Low','Close','Volume']
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    logger.info(f"{symbol}: {len(df)} bars from IBKR")
                    return df
            except Exception as e:
                logger.warning(f"{symbol} IBKR bars failed ({e}), falling back to yfinance")

        # yfinance fallback
        yf_interval = interval.replace(' mins', 'm').replace(' min', 'm')\
                               .replace(' hour', 'h').replace(' hours', 'h')
        yf_period = period.replace(' D', 'd').replace(' W', 'wk').replace(' M', 'mo')
        df = yf.Ticker(symbol).history(period=yf_period, interval=yf_interval)
        logger.info(f"{symbol}: {len(df)} bars from yfinance")
        return df

    # ── realtime ────────────────────────────────────────────────────────────
    def subscribe_realtime(self, symbol: str, callback):
        """Subscribe to 5-min realtime bars for symbol. Callback(bar) on each new bar."""
        if symbol not in self._callbacks:
            self._callbacks[symbol] = []
        self._callbacks[symbol].append(callback)

        if symbol not in self._bar_subs and self.hub.is_connected:
            self._start_bar_sub(symbol)

    def _start_bar_sub(self, symbol: str):
        contract = Stock(symbol, 'SMART', 'USD')
        try:
            self.hub.ib.qualifyContracts(contract)
            bars = self.hub.ib.reqRealTimeBars(contract, 5, 'MIDPOINT', False)
            bars.updateEvent += lambda b, h: self._on_bar(symbol, b[-1] if b else None)
            self._bar_subs[symbol] = bars
            logger.info(f"Subscribed to realtime bars: {symbol}")
        except Exception as e:
            logger.warning(f"Realtime sub failed for {symbol}: {e}")

    def _on_bar(self, symbol, bar):
        if bar is None:
            return
        for cb in self._callbacks.get(symbol, []):
            try:
                cb(symbol, bar)
            except Exception as e:
                logger.error(f"Bar callback error for {symbol}: {e}")

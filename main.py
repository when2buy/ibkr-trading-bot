"""
IBKR Multi-Strategy Trading Engine
Usage:
  python main.py              # live paper trading
  python main.py --simulate   # replay on yfinance bars (no IBKR needed)
"""
import asyncio, logging, signal, sys
from datetime import datetime, timezone

import config
from engine.connection_hub  import ConnectionHub
from engine.data_manager    import DataManager
from engine.order_manager   import OrderManager
from engine.risk_manager    import RiskManager
from strategies.spy_momentum import SPYMomentum, _is_market_hours
from strategies.spy_breakout import SPYBreakout
from monitoring.reporter     import Reporter

# ── logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-22s %(levelname)-7s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"{config.LOG_DIR}/engine_{datetime.now().strftime('%Y-%m-%d')}.log"),
    ]
)
logger = logging.getLogger('main')

# ── wiring ────────────────────────────────────────────────────────────────────
def build_engine(simulation_mode=False):
    hub      = ConnectionHub(config.IB_HOST, config.IB_PORT,
                             config.IB_CLIENT_ID, config.IB_ACCOUNT)
    risk     = RiskManager(config.MAX_TOTAL_EXPOSURE, config.MAX_PORTFOLIO_DD_PCT)
    data     = DataManager(hub)
    orders   = OrderManager(hub, risk, config.IB_ACCOUNT, config.LOG_DIR, simulation_mode=simulation_mode)
    momentum = SPYMomentum(hub, data, orders, risk)
    breakout = SPYBreakout(hub, data, orders, risk)
    strategies = [momentum, breakout]
    reporter = Reporter(strategies, orders, risk, interval_sec=300)
    return hub, data, orders, risk, strategies, reporter


# ── simulation mode (prefer IBKR, fallback to yfinance) ──────────────────────
async def run_simulation(strategies, data, hub):
    """Feed historical bars into all strategies' on_bar() as if live.
    Prefers IBKR historical data; falls back to yfinance if gateway unavailable."""
    import pandas as pd

    symbol = 'SPY'

    # Try IBKR first
    logger.info("🎮 SIMULATION MODE — fetching historical data...")
    df = None
    data_source = "unknown"

    # Try to connect if not already connected
    if not hub.is_connected:
        try:
            logger.info("📡 Connecting to IBKR Gateway for historical data...")
            await hub.connect()
        except Exception as e:
            logger.warning(f"Could not connect to IBKR: {e}")

    # DataManager.get_bars() already returns a DataFrame
    if hub.is_connected:
        try:
            logger.info("📊 Fetching IBKR historical bars...")
            df = data.get_bars(symbol, period='5 D', interval='5 mins')
            if df is not None and len(df) > 0:
                data_source = "IBKR"
                logger.info(f"✅ Loaded {len(df)} bars from IBKR")
        except Exception as e:
            logger.warning(f"IBKR historical data failed: {e}")
        finally:
            # Disconnect after getting data (simulation doesn't need persistent connection)
            hub.disconnect()

    # Fallback to yfinance if IBKR didn't work
    if df is None or len(df) == 0:
        logger.info("📊 Falling back to yfinance")
        import yfinance as yf
        df = yf.Ticker(symbol).history(period='5d', interval='5m').dropna()
        data_source = "yfinance (fallback)"
        logger.info(f"✅ Loaded {len(df)} bars from yfinance")

    if df is None or len(df) == 0:
        logger.error("❌ No data available for simulation")
        return

    logger.info(f"🎮 Replaying {len(df)} bars from {data_source}")

    for ts, row in df.iterrows():
        bar = type('Bar', (), {
            'close': row['Close'], 'open': row['Open'],
            'high': row['High'],   'low': row['Low'],
            'volume': row['Volume'], 'time': ts
        })()
        for strat in strategies:
            strat.on_bar(symbol, bar)
        await asyncio.sleep(0.05)   # fast replay

    logger.info("Simulation complete")
    logger.info(f"Data source: {data_source}")
    for strat in strategies:
        if hasattr(strat, 'print_summary'):
            strat.print_summary()
        logger.info(f"[{strat.strategy_id}] Final P&L: ${strat.get_pnl():+,.2f}")
        logger.info(f"[{strat.strategy_id}] Total fills: "
                    f"{len(strat.orders.get_fills(strat.strategy_id))}")


async def _try_connect_readonly(hub):
    """Try to connect to IBKR gateway in read-only mode."""
    try:
        await hub.connect()
        return True
    except Exception as e:
        logger.warning(f"Could not connect to IBKR: {e}")
        return False


# ── live mode ─────────────────────────────────────────────────────────────────
async def run_live(hub, strategies, reporter):
    await hub.connect()
    for strat in strategies:
        strat.on_start()
    reporter_task = asyncio.create_task(reporter.run())

    logger.info("="*60)
    logger.info("  Engine running. Press Ctrl+C to stop.")
    logger.info(f"  Strategies: {[s.strategy_id for s in strategies]}")
    logger.info(f"  Market hours: {_is_market_hours()}")
    logger.info("="*60)

    try:
        while True:
            await asyncio.sleep(1)
            hub.ib.sleep(0)   # process IB events
    except asyncio.CancelledError:
        pass
    finally:
        reporter_task.cancel()
        reporter.print_summary()
        for strat in strategies:
            strat.orders.cancel_all(strat.strategy_id)
        hub.disconnect()


# ── entry point ───────────────────────────────────────────────────────────────
async def main():
    simulate = '--simulate' in sys.argv
    hub, data, orders, risk, strategies, reporter = build_engine(simulation_mode=simulate)

    def _shutdown(sig, frame):
        logger.info(f"\nShutdown signal received ({sig})")
        reporter.print_summary()
        for strat in strategies:
            orders.cancel_all(strat.strategy_id)
        hub.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if simulate:
        for strat in strategies:
            strat.on_start()
        await run_simulation(strategies, data, hub)
    else:
        await run_live(hub, strategies, reporter)


if __name__ == '__main__':
    import os
    os.makedirs(config.LOG_DIR, exist_ok=True)
    asyncio.run(main())

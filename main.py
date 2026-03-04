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
def build_engine():
    hub      = ConnectionHub(config.IB_HOST, config.IB_PORT,
                             config.IB_CLIENT_ID, config.IB_ACCOUNT)
    risk     = RiskManager(config.MAX_TOTAL_EXPOSURE, config.MAX_PORTFOLIO_DD_PCT)
    data     = DataManager(hub)
    orders   = OrderManager(hub, risk, config.IB_ACCOUNT, config.LOG_DIR)
    strategy = SPYMomentum(hub, data, orders, risk)
    reporter = Reporter([strategy], orders, risk, interval_sec=300)
    return hub, data, orders, risk, strategy, reporter


# ── simulation mode (no IBKR needed) ─────────────────────────────────────────
async def run_simulation(strategy, data):
    """Feed yfinance 5-min bars into strategy.on_bar() as if live."""
    import yfinance as yf
    import pandas as pd
    from ib_insync.objects import RealTimeBar

    logger.info("🎮 SIMULATION MODE — replaying yfinance 5-min bars")
    df = yf.Ticker('SPY').history(period='5d', interval='5m').dropna()
    logger.info(f"Loaded {len(df)} bars")

    for ts, row in df.iterrows():
        bar = type('Bar', (), {
            'close': row['Close'], 'open': row['Open'],
            'high': row['High'],   'low': row['Low'],
            'volume': row['Volume'], 'time': ts
        })()
        strategy.on_bar('SPY', bar)
        await asyncio.sleep(0.05)   # fast replay

    logger.info("Simulation complete")
    strategy.print_summary() if hasattr(strategy, 'print_summary') else None
    logger.info(f"Final P&L: ${strategy.get_pnl():+,.2f}")
    logger.info(f"Total fills: {len(strategy.orders.get_fills(strategy.strategy_id))}")


# ── live mode ─────────────────────────────────────────────────────────────────
async def run_live(hub, strategy, reporter):
    await hub.connect()
    strategy.on_start()
    reporter_task = asyncio.create_task(reporter.run())

    logger.info("="*60)
    logger.info("  Engine running. Press Ctrl+C to stop.")
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
        strategy.orders.cancel_all(strategy.strategy_id)
        hub.disconnect()


# ── entry point ───────────────────────────────────────────────────────────────
async def main():
    simulate = '--simulate' in sys.argv
    hub, data, orders, risk, strategy, reporter = build_engine()

    def _shutdown(sig, frame):
        logger.info(f"\nShutdown signal received ({sig})")
        reporter.print_summary()
        orders.cancel_all(strategy.strategy_id)
        hub.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if simulate:
        strategy.on_start()
        await run_simulation(strategy, data)
    else:
        await run_live(hub, strategy, reporter)


if __name__ == '__main__':
    import os
    os.makedirs(config.LOG_DIR, exist_ok=True)
    asyncio.run(main())

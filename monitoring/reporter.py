"""Reporter — periodic P&L and status printer."""
import asyncio, logging
from datetime import datetime

logger = logging.getLogger('monitoring')

class Reporter:
    def __init__(self, strategies: list, order_mgr, risk_mgr, interval_sec=300):
        self.strategies   = strategies
        self.orders       = order_mgr
        self.risk         = risk_mgr
        self.interval_sec = interval_sec
        self._running     = False

    async def run(self):
        self._running = True
        while self._running:
            await asyncio.sleep(self.interval_sec)
            self.print_summary()

    def print_summary(self):
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"\n{'='*60}")
        print(f"  Status Report @ {ts}")
        print(f"{'='*60}")
        for strat in self.strategies:
            fills   = self.orders.get_fills(strat.strategy_id)
            pnl     = strat.get_pnl()
            print(f"  {strat.status_line(strat._last_price)}")
            print(f"  Total fills: {len(fills)}")
        print(self.risk.summary())
        print(f"{'='*60}\n")

    def stop(self):
        self._running = False

"""StrategyBase — inherit this for every strategy."""
import logging
from abc import ABC, abstractmethod
from ib_insync import Stock

class StrategyBase(ABC):
    def __init__(self, strategy_id: str, capital_allocation: float,
                 hub, data_mgr, order_mgr, risk_mgr):
        self.strategy_id        = strategy_id
        self.capital_allocation = capital_allocation
        self.hub                = hub
        self.data               = data_mgr
        self.orders             = order_mgr
        self.risk               = risk_mgr
        self.logger             = logging.getLogger(f'strategy.{strategy_id}')
        self._position          = 0    # net position in shares
        self._entry_price       = 0.0
        self._realized_pnl      = 0.0

    # ── abstract interface ────────────────────────────────────────────────────
    @abstractmethod
    def on_bar(self, symbol: str, bar): ...

    @abstractmethod
    def on_start(self): ...

    # ── helpers ───────────────────────────────────────────────────────────────
    def buy(self, symbol: str, qty: int, order_type='MKT', price=None):
        contract = Stock(symbol, 'SMART', 'USD')
        if self.hub.is_connected:
            try:
                self.hub.ib.qualifyContracts(contract)
            except Exception:
                pass
        ok, result = self.orders.submit_order(
            self.strategy_id, contract, 'BUY', qty, order_type, price)
        if ok:
            self._position    += qty
            self._entry_price  = price or self._last_price
        else:
            self.logger.warning(f"BUY rejected: {result}")
        return ok, result

    def sell(self, symbol: str, qty: int, order_type='MKT', price=None):
        contract = Stock(symbol, 'SMART', 'USD')
        if self.hub.is_connected:
            try:
                self.hub.ib.qualifyContracts(contract)
            except Exception:
                pass
        ok, result = self.orders.submit_order(
            self.strategy_id, contract, 'SELL', qty, order_type, price)
        if ok:
            self._position -= qty
        else:
            self.logger.warning(f"SELL rejected: {result}")
        return ok, result

    @property
    def position(self) -> int:
        return self._position

    def get_pnl(self) -> float:
        fills = self.orders.get_fills(self.strategy_id)
        bought  = sum(f['qty'] * f['price'] for f in fills if f['side'] == 'BOT')
        sold    = sum(f['qty'] * f['price'] for f in fills if f['side'] == 'SLD')
        return sold - bought   # simplified realized P&L

    def status_line(self, current_price: float = 0.0) -> str:
        unrealized = self._position * (current_price - self._entry_price) \
                     if self._entry_price and current_price else 0.0
        return (f"[{self.strategy_id}] pos={self._position:+d} | "
                f"realized=${self.get_pnl():+,.2f} | "
                f"unrealized=${unrealized:+,.2f}")

"""
OrderManager — submit, track, and cancel orders.
Tags every order with strategy_id via orderRef.
"""
import logging, csv, os
from datetime import datetime
from ib_insync import MarketOrder, LimitOrder, StopOrder

logger = logging.getLogger('engine.orders')

class OrderManager:
    def __init__(self, hub, risk_manager, account: str, log_dir: str, simulation_mode: bool = False):
        self.hub          = hub
        self.risk         = risk_manager
        self.account      = account
        self.log_dir      = log_dir
        self.simulation_mode = simulation_mode  # Force simulation fills
        self._trades      = []   # list of fill dicts
        self._open_orders = {}   # orderId -> trade
        os.makedirs(log_dir, exist_ok=True)
        self._log_path = os.path.join(log_dir,
                                      f"trades_{datetime.now().strftime('%Y-%m-%d')}.csv")
        self._init_log()

    # ── submit ────────────────────────────────────────────────────────────────
    def submit_order(self, strategy_id: str, contract, action: str,
                     qty: int, order_type: str = 'MKT', price: float = None):
        """
        action: 'BUY' or 'SELL'
        order_type: 'MKT', 'LMT', 'STP'
        Returns (success, trade_or_reason)
        """
        # Estimate price for risk check
        est_price = price if price else (
            self._get_last_price(contract.symbol) if self.hub.is_connected else 0.0)

        if self.simulation_mode or not self.hub.is_connected:
            # Simulation mode — record fill without sending to IBKR
            # Use actual estimated price (from bar data) instead of 0.0
            sim_price = est_price if est_price > 0 else 0.0
            record = {
                'timestamp':  __import__('datetime').datetime.now().isoformat(),
                'strategy':   strategy_id,
                'symbol':     contract.symbol,
                'side':       'BOT' if action == 'BUY' else 'SLD',
                'qty':        qty,
                'price':      sim_price,
                'commission': 1.0,  # Flat $1 commission for simulation
            }
            self._trades.append(record)
            self._log_fill(record)
            logging.getLogger('engine.orders').info(
                f"[SIM][{strategy_id}] {action} {qty} {contract.symbol} @ {sim_price:.2f}")
            return True, record
        ok, reason = self.risk.check_order(strategy_id, contract.symbol,
                                           action, qty, est_price)
        if not ok:
            return False, reason

        # Build order
        if order_type == 'MKT':
            order = MarketOrder(action, qty)
        elif order_type == 'LMT':
            order = LimitOrder(action, qty, price)
        elif order_type == 'STP':
            order = StopOrder(action, qty, price)
        else:
            return False, f"Unknown order type: {order_type}"

        order.orderRef = strategy_id         # tag with strategy
        order.account  = self.account

        try:
            trade = self.hub.ib.placeOrder(contract, order)
            self._open_orders[trade.order.orderId] = trade
            trade.fillEvent    += lambda t, f: self._on_fill(strategy_id, t, f)
            trade.cancelledEvent += lambda t: self._on_cancel(strategy_id, t)

            logger.info(f"[{strategy_id}] {action} {qty} {contract.symbol} "
                        f"{order_type}" + (f" @ {price:.2f}" if price else "")
                        + f" → orderId={trade.order.orderId}")
            return True, trade
        except Exception as e:
            logger.error(f"Order failed [{strategy_id}]: {e}")
            return False, str(e)

    def cancel_all(self, strategy_id: str):
        cancelled = 0
        for oid, trade in list(self._open_orders.items()):
            if trade.order.orderRef == strategy_id and \
               trade.orderStatus.status not in ('Filled', 'Cancelled'):
                self.hub.ib.cancelOrder(trade.order)
                cancelled += 1
        logger.info(f"[{strategy_id}] Cancelled {cancelled} open orders")
        return cancelled

    def get_fills(self, strategy_id: str = None):
        if strategy_id:
            return [f for f in self._trades if f['strategy'] == strategy_id]
        return self._trades

    # ── internal ─────────────────────────────────────────────────────────────
    def _on_fill(self, strategy_id, trade, fill):
        record = {
            'timestamp': datetime.now().isoformat(),
            'strategy':  strategy_id,
            'symbol':    fill.contract.symbol,
            'side':      fill.execution.side,
            'qty':       fill.execution.shares,
            'price':     fill.execution.price,
            'commission': fill.commissionReport.commission
                          if fill.commissionReport else 0.0,
        }
        self._trades.append(record)
        self._log_fill(record)
        logger.info(f"[{strategy_id}] FILL {record['side']} {record['qty']} "
                    f"{record['symbol']} @ {record['price']:.2f}")
        # Update risk exposure estimate
        if record['side'] == 'BOT':
            self.risk.update_exposure(
                strategy_id, record['qty'] * record['price'])
        else:
            self.risk.update_exposure(strategy_id, 0)

    def _on_cancel(self, strategy_id, trade):
        oid = trade.order.orderId
        self._open_orders.pop(oid, None)
        logger.info(f"[{strategy_id}] Order {oid} cancelled")

    def _get_last_price(self, symbol: str) -> float:
        try:
            from ib_insync import Stock
            contract = Stock(symbol, 'SMART', 'USD')
            self.hub.ib.qualifyContracts(contract)
            ticker = self.hub.ib.reqMktData(contract, '', True, False)
            self.hub.ib.sleep(1)
            price = ticker.last or ticker.close or 0.0
            self.hub.ib.cancelMktData(contract)
            return price
        except Exception:
            return 0.0

    def _init_log(self):
        if not os.path.exists(self._log_path):
            with open(self._log_path, 'w', newline='') as f:
                csv.DictWriter(f, fieldnames=[
                    'timestamp','strategy','symbol','side','qty','price','commission'
                ]).writeheader()

    def _log_fill(self, record: dict):
        with open(self._log_path, 'a', newline='') as f:
            csv.DictWriter(f, fieldnames=list(record.keys())).writerow(record)

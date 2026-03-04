"""
RiskManager — pre-trade checks + kill switch.
Every order must pass through here before hitting the wire.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger('engine.risk')

@dataclass
class StrategyRiskConfig:
    strategy_id:        str
    capital_allocation: float
    max_position_value: float
    max_daily_loss:     float
    enabled:            bool = True

class RiskManager:
    def __init__(self, max_total_exposure: float, max_portfolio_dd_pct: float):
        self.max_total_exposure   = max_total_exposure
        self.max_portfolio_dd_pct = max_portfolio_dd_pct
        self._configs:  Dict[str, StrategyRiskConfig] = {}
        self._pnl:      Dict[str, float] = {}   # daily P&L per strategy
        self._exposure: Dict[str, float] = {}   # current market value per strategy
        self._rejections = []

    # ── setup ────────────────────────────────────────────────────────────────
    def register_strategy(self, config: StrategyRiskConfig):
        self._configs[config.strategy_id] = config
        self._pnl[config.strategy_id]      = 0.0
        self._exposure[config.strategy_id] = 0.0
        logger.info(f"Registered strategy '{config.strategy_id}' "
                    f"alloc=${config.capital_allocation:,.0f}")

    # ── pre-trade check ───────────────────────────────────────────────────────
    def check_order(self, strategy_id: str, symbol: str,
                    action: str, qty: int, price: float) -> tuple[bool, str]:
        cfg = self._configs.get(strategy_id)
        if cfg is None:
            return False, f"Unknown strategy: {strategy_id}"
        if not cfg.enabled:
            return False, f"Strategy {strategy_id} is paused"

        order_value = qty * price

        # 1. Per-strategy daily loss
        if self._pnl[strategy_id] <= -cfg.max_daily_loss:
            reason = (f"{strategy_id} daily loss ${-self._pnl[strategy_id]:,.0f} "
                      f"exceeds limit ${cfg.max_daily_loss:,.0f}")
            self._reject(strategy_id, symbol, action, qty, price, reason)
            return False, reason

        # 2. Per-strategy position size
        if action == 'BUY' and order_value > cfg.max_position_value:
            reason = (f"Order value ${order_value:,.0f} exceeds "
                      f"max position ${cfg.max_position_value:,.0f}")
            self._reject(strategy_id, symbol, action, qty, price, reason)
            return False, reason

        # 3. Global exposure
        total_exposure = sum(self._exposure.values()) + order_value
        if action == 'BUY' and total_exposure > self.max_total_exposure:
            reason = (f"Total exposure ${total_exposure:,.0f} would exceed "
                      f"max ${self.max_total_exposure:,.0f}")
            self._reject(strategy_id, symbol, action, qty, price, reason)
            return False, reason

        return True, "OK"

    # ── updates from order manager ────────────────────────────────────────────
    def update_pnl(self, strategy_id: str, pnl_delta: float):
        if strategy_id in self._pnl:
            self._pnl[strategy_id] += pnl_delta

    def update_exposure(self, strategy_id: str, exposure: float):
        if strategy_id in self._exposure:
            self._exposure[strategy_id] = exposure

    # ── kill switch ───────────────────────────────────────────────────────────
    def pause_strategy(self, strategy_id: str):
        if strategy_id in self._configs:
            self._configs[strategy_id].enabled = False
            logger.warning(f"⛔ Strategy '{strategy_id}' PAUSED")

    def resume_strategy(self, strategy_id: str):
        if strategy_id in self._configs:
            self._configs[strategy_id].enabled = True
            logger.info(f"▶️  Strategy '{strategy_id}' RESUMED")

    # ── reporting ─────────────────────────────────────────────────────────────
    def summary(self) -> str:
        lines = ["Risk Summary:"]
        for sid, cfg in self._configs.items():
            status = "✅" if cfg.enabled else "⛔"
            lines.append(f"  {status} {sid:20s} | pnl=${self._pnl[sid]:+,.0f} "
                         f"| exposure=${self._exposure[sid]:,.0f} "
                         f"| daily_limit=${cfg.max_daily_loss:,.0f}")
        return "\n".join(lines)

    def _reject(self, strategy_id, symbol, action, qty, price, reason):
        logger.warning(f"RISK REJECT [{strategy_id}] {action} {qty} {symbol} "
                       f"@ {price:.2f}: {reason}")
        self._rejections.append({'strategy': strategy_id, 'symbol': symbol,
                                 'action': action, 'reason': reason})

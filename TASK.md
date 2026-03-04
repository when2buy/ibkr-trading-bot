# Task: Build IBKR Multi-Strategy Paper Trading Engine

## Environment
- IBKR Paper trading Gateway running at 127.0.0.1:4002
- Account: DU7659927 (~$820K paper capital)
- Python 3.11, ib_insync 0.9.86, yfinance, pandas, numpy installed
- Env file: /opt/openclaw/gpu-bot/workspace/.env

## What to Build

Build a clean, runnable multi-strategy trading engine in this directory.

### Directory Structure
```
ibkr-bot/
├── engine/
│   ├── __init__.py
│   ├── connection_hub.py     # Manages IB() connection, reconnects on drop
│   ├── data_manager.py       # Market data subscriptions + yfinance fallback
│   ├── order_manager.py      # Submit/track/cancel orders with strategy tags
│   └── risk_manager.py       # Position limits, drawdown protection, kill switch
├── strategies/
│   ├── __init__.py
│   ├── base.py               # StrategyBase abstract class
│   └── spy_momentum.py       # WORKING example: SPY EMA crossover momentum
├── monitoring/
│   ├── __init__.py
│   └── reporter.py           # Print P&L summary, positions, trade log
├── config.py                 # All config from .env + strategy params
├── main.py                   # Entry point: wire everything up, run strategies
├── run_backtest.py           # Offline backtest using yfinance data
└── README.md                 # How to run
```

## Detailed Specs

### engine/connection_hub.py
- Singleton IB() instance (clientId=0)
- Auto-reconnect on disconnect with exponential backoff
- Expose: `ib`, `on_bar(callback)`, `on_fill(callback)`, `on_error(callback)`
- Use ib_insync's event system

### engine/data_manager.py
- Subscribe to market data for a list of symbols
- Deduplicate: if two strategies want SPY, only one subscription
- Historical data: try IBKR BID_ASK first, fall back to yfinance OHLCV
- Cache bars in memory (pandas DataFrame per symbol)
- Methods: `get_bars(symbol, period, interval)`, `subscribe_realtime(symbol, callback)`

### engine/order_manager.py
- `submit_order(strategy_id, contract, action, qty, order_type, price=None)`
- Tag every order with strategy_id using IBKR's `orderRef` field
- Track fills in a DataFrame: [timestamp, strategy, symbol, side, qty, price, commission]
- Methods: `get_fills(strategy_id)`, `get_open_orders(strategy_id)`, `cancel_all(strategy_id)`

### engine/risk_manager.py
- Per-strategy limits: max_position_value, max_daily_loss
- Global limits: max_total_exposure=$500K, max_portfolio_drawdown=5%
- `check_order(strategy_id, contract, qty, price) -> (bool, reason)`
- Kill switch: `pause_strategy(strategy_id)` / `resume_strategy(strategy_id)`
- Log all risk rejections

### strategies/base.py
```python
class StrategyBase(ABC):
    def __init__(self, strategy_id, capital_allocation, hub, data_mgr, order_mgr, risk_mgr):
        ...
    
    @abstractmethod
    def on_bar(self, symbol, bar): ...
    
    @abstractmethod  
    def on_fill(self, fill): ...
    
    def submit_order(self, contract, action, qty, order_type='MKT', price=None):
        # goes through risk manager first
        ...
    
    def get_pnl(self) -> float: ...
```

### strategies/spy_momentum.py  (MUST BE RUNNABLE AND DO REAL PAPER TRADES)
- **Strategy**: EMA 9/21 crossover on SPY 5-min bars
- When EMA9 crosses above EMA21 → BUY 10 shares SPY
- When EMA9 crosses below EMA21 → SELL/SHORT 10 shares SPY  
- Max 1 position at a time
- Stop loss: 0.5% from entry
- Capital allocation: $200,000
- During market hours: use live IBKR data
- Outside market hours / for backtesting: use yfinance 5min data
- **MUST actually submit real orders to paper account during market hours**

### monitoring/reporter.py
- Print summary every 5 minutes: strategy P&L, positions, recent fills
- Save trade log to logs/trades_YYYY-MM-DD.csv
- Print on exit: full session summary

### main.py
- Load config from .env
- Initialize all engine components
- Instantiate spy_momentum strategy
- Run async event loop
- Handle SIGINT gracefully (cancel orders, print summary)
- Example output:
```
[09:35] SPY Momentum | pos=0 | pnl=$0.00 | signal=NEUTRAL
[09:40] SPY Momentum | BUY 10 SPY @ 679.50 | EMA9=679.2 > EMA21=678.8
[09:45] SPY Momentum | pos=10 | pnl=+$45.00 | unrealized
```

### run_backtest.py
- Download SPY 5-min data for last 30 days via yfinance
- Run the same EMA crossover logic offline
- Print: total trades, win rate, total P&L, Sharpe ratio, max drawdown
- Save equity curve to logs/backtest_equity.csv

## Important Notes
- Market hours: 9:30-16:00 ET (14:30-21:00 UTC)
- Paper account has ~$820K available
- IB Gateway is already running and authenticated
- Use ib_insync's asyncio interface (ib_insync.util.run())
- Handle "market closed" gracefully — strategy should wait and not crash
- All credentials in /opt/openclaw/gpu-bot/workspace/.env

## When Done
Run: openclaw system event --text "Done: IBKR multi-strategy engine built. SPY momentum strategy ready to paper trade. Run: python main.py" --mode now

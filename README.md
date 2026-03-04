# IBKR Multi-Strategy Paper Trading Engine

## Architecture
```
IB Gateway (port 4002)
    └── ConnectionHub (singleton IB connection)
            ├── DataManager     (market data, yfinance fallback)
            ├── OrderManager    (order submit/track, CSV fill log)
            ├── RiskManager     (per-strategy limits + kill switch)
            └── Strategies
                    └── SPYMomentum (EMA 9/21 crossover, 5-min bars)
```

## Quick Start

```bash
cd /opt/openclaw/gpu-bot/workspace/ibkr-bot

# Backtest (no IBKR needed)
python run_backtest.py

# Simulation (replay yfinance bars, no IBKR needed)
python main.py --simulate

# Live paper trading (requires IB Gateway on :4002)
python main.py
```

## SPY Momentum Strategy
- **Signal**: EMA(9) / EMA(21) crossover on 5-min bars
- **Entry**: BUY 10 shares on bullish cross
- **Exit**: SELL on bearish cross OR 0.5% stop loss
- **Capital**: $200K allocated, max $20K per position
- **Daily loss limit**: $2K (auto-pauses strategy)

## Logs
- `logs/engine_YYYY-MM-DD.log` — full engine log
- `logs/trades_YYYY-MM-DD.csv` — fill record
- `logs/backtest_equity.csv` — equity curve from backtest

## Adding a New Strategy
1. Create `strategies/my_strategy.py` inheriting `StrategyBase`
2. Implement `on_start()` and `on_bar(symbol, bar)`
3. Register risk config via `risk_mgr.register_strategy()`
4. Add to `main.py` strategy list

## IB Gateway Management
```bash
# Start Gateway (headless)
DISPLAY=:1 nohup bash /opt/ibkr/scripts/gatewaystart.sh -inline &

# Check if running
python -c "import socket; s=socket.socket(); print('UP' if s.connect_ex(('127.0.0.1',4002))==0 else 'DOWN')"
```

# 🤖 Dual-Mode Trading Bot

Your IBKR trading bot now supports **two parallel modes**:

## 🌐 Mode 1: Online Paper Trading
- **What:** Connects to IBKR Gateway, executes real paper trades
- **Account:** DU7659927 (paper)
- **Data:** Live market data via IBKR API
- **Execution:** Real fills with realistic commissions
- **Schedule:** Continuous (during market hours)
- **Start:** `./run_online_paper.sh` or systemd service

## 📊 Mode 2: Offline Simulation  
- **What:** Replays historical data from yfinance
- **Data:** Recent 5-day 5-min bars
- **Execution:** Simulated fills (no IBKR needed)
- **Schedule:** Once daily via cron (after market close)
- **Start:** `./run_daily_offline.sh`

---

## 🚀 Quick Commands

```bash
# Run online paper trading (foreground)
./run_online_paper.sh

# Run offline simulation
./run_daily_offline.sh

# Compare today's results
python3 compare_results.py

# Check IBKR execution records
python3 check_ibkr_trades.py
```

---

## 📋 Setup Automation

### 1. Start online paper trading as service

```bash
sudo cp systemd/ibkr-online-trading.service /etc/systemd/system/
sudo systemctl enable ibkr-online-trading
sudo systemctl start ibkr-online-trading
sudo systemctl status ibkr-online-trading
```

### 2. Schedule daily offline simulation

```bash
crontab -e
# Add: 0 17 * * * /opt/openclaw/gpu-bot/workspace/ibkr-bot/run_daily_offline.sh
```

This runs at 17:00 UTC (after US market close).

---

## 📊 Results

Both modes write to:
- **Trade log:** `logs/trades_YYYY-MM-DD.csv`
- **Engine log:** `logs/engine_YYYY-MM-DD.log`  
- **Mode-specific:** `logs/online_*.log` or `logs/offline_*.log`

Distinguish by:
- **Online:** Real prices (e.g., $687.50), real commissions
- **Offline:** `[SIM]` prefix, price=$0, commission=$1

---

## 🎯 Why Both?

1. **Online** = reality check with live market conditions
2. **Offline** = consistent backtesting on same data daily
3. **Comparison** = understand slippage, latency, market impact

Track both to see:
- Does the strategy work in real-time?
- How much do simulations differ from live execution?
- Are stop-losses being hit more/less than expected?

---

See **DUAL_MODE_SETUP.md** for full documentation.

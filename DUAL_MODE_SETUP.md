# Dual Mode Trading Setup

Run **both** online (IBKR Gateway) and offline (simulation) paper trading in parallel.

---

## 📊 Two Trading Modes

### 1. **ONLINE Paper Trading** (via IBKR Gateway)
- Connects to live IBKR Gateway (port 4002)
- Executes on real paper account DU7659927
- Real fills, real commissions, real market data
- **Runs continuously** during market hours

### 2. **OFFLINE Simulation** (via yfinance)
- Replays recent 5-day 5-min bars from yfinance
- No IBKR connection needed
- Simulated fills (price=$0, commission=$1)
- **Runs once per day** via cron

---

## 🚀 Quick Start

### Online Mode (continuous)

```bash
# Option A: Run in foreground
cd /opt/openclaw/gpu-bot/workspace/ibkr-bot
./run_online_paper.sh

# Option B: Run as systemd service (recommended)
sudo cp systemd/ibkr-online-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ibkr-online-trading
sudo systemctl start ibkr-online-trading

# Check status
sudo systemctl status ibkr-online-trading

# View logs
tail -f logs/online_$(date +%Y-%m-%d).log
```

### Offline Mode (daily)

```bash
# Manual run
cd /opt/openclaw/gpu-bot/workspace/ibkr-bot
./run_daily_offline.sh

# Schedule via cron (runs at 17:00 UTC daily, after market close)
crontab -e
# Add this line:
0 17 * * * /opt/openclaw/gpu-bot/workspace/ibkr-bot/run_daily_offline.sh
```

---

## 📁 Log Files

```
logs/
├── online_2026-03-04.log       # Online paper trading logs
├── offline_2026-03-04.log      # Offline simulation logs
├── trades_2026-03-04.csv       # Combined trade records
└── engine_2026-03-04.log       # Engine debug logs

results/
├── offline_2026-03-04.json     # Daily simulation summary
└── ...
```

---

## 🔍 Compare Results

```bash
# Today's results
python3 compare_results.py

# Specific date
python3 compare_results.py 2026-03-04

# Also query IBKR directly
python3 check_ibkr_trades.py
```

---

## 📝 Trade Log Format

All trades (online & offline) go to the same CSV:

```csv
timestamp,strategy,symbol,side,qty,price,commission
2026-03-04T08:24:16.531481,spy_momentum,SPY,BOT,10,0.0,1.0
2026-03-04T08:24:20.506801,spy_momentum,SPY,SLD,10,0.0,1.0
```

**Distinguishing online vs offline:**
- **Online:** Real prices (e.g., 687.50), real commissions (e.g., 1.00)
- **Offline:** Simulated prices (0.0), fixed commission (1.0)
- Check corresponding log files for `[SIM]` prefix

---

## 🛠️ Troubleshooting

### Online mode fails to connect
```bash
# Check gateway is running
ss -tlnp | grep 4002

# Restart gateway if needed
sudo systemctl restart ibkr-gateway  # if using systemd
# OR
/opt/ibkr/ibc/scripts/ibcstart.sh 1037 -g ...
```

### Offline mode gets stale data
```bash
# yfinance caches data, force refresh by deleting cache
rm -rf ~/.cache/py-yfinance-cache
```

### Both modes writing to same CSV causes confusion
- Check the log prefix: `[SIM]` = offline
- Or separate by checking log files: `online_*.log` vs `offline_*.log`

---

## 🎯 Recommended Workflow

1. **Morning:** Start online paper trading
   ```bash
   sudo systemctl start ibkr-online-trading
   ```

2. **During market hours:** Monitor online trades
   ```bash
   tail -f logs/online_$(date +%Y-%m-%d).log
   ```

3. **After market close (17:00 UTC):** Cron runs offline simulation automatically

4. **Evening:** Compare results
   ```bash
   python3 compare_results.py
   python3 check_ibkr_trades.py
   ```

---

## 📊 Expected Output

**Online (real execution):**
```
08:24:16 engine.orders INFO [spy_momentum] BUY 10 SPY MKT → orderId=12345
08:24:16 engine.orders INFO [spy_momentum] FILL BOT 10 SPY @ 687.50
```

**Offline (simulation):**
```
08:24:16 main INFO 🎮 SIMULATION MODE — replaying yfinance 5-min bars
08:24:16 engine.orders INFO [SIM][spy_momentum] BUY 10 SPY @ 0.00
```

---

## 🔐 Safety

- Both modes use **paper account only** (DU7659927)
- Online mode cannot place real trades (paper flag enforced)
- Offline mode never connects to IBKR at all
- Risk limits enforced in both modes via RiskManager

---

## Next Steps

- [ ] Start online paper trading (systemd or screen)
- [ ] Schedule daily offline simulation (cron)
- [ ] Monitor for 1 week
- [ ] Compare strategy performance in both modes
- [ ] Adjust parameters based on results

---

**Questions?** Check `IBKR_GUIDE.md` for gateway setup details.

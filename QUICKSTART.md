# 🚀 Quick Start Guide

**Get up and running with IBKR trading bot in 5 minutes**

---

## Prerequisites

- IBKR paper trading account
- IBKR Gateway installed and running
- Python 3.11+

For detailed setup instructions, see **[IBKR_GUIDE.md](IBKR_GUIDE.md)**.

---

## Quick Commands

```bash
# Clone repository
git clone https://github.com/when2buy/ibkr-trading-bot.git
cd ibkr-trading-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your IBKR credentials

# Test connection
./test_ibkr_connection.sh

# Run online paper trading
./run_online_paper.sh

# Run offline simulation
./run_offline_sim.sh

# Compare results
python3 compare_results.py
```

---

## Two Trading Modes

### 🌐 Online (Live Execution)

**What:** Connects to IBKR Gateway, executes on real paper account

**How to run:**
```bash
# Option A: Foreground
./run_online_paper.sh

# Option B: Background service
sudo cp systemd/ibkr-online-trading.service /etc/systemd/system/
sudo systemctl enable ibkr-online-trading
sudo systemctl start ibkr-online-trading
```

**Logs:**
```bash
tail -f logs/online_$(date +%Y-%m-%d).log
```

### 📊 Offline (Simulation)

**What:** Backtests on historical data (no IBKR connection needed)

**How to run:**
```bash
# Manual run
./run_offline_sim.sh

# Schedule daily (17:00 UTC)
./setup_cron.sh
```

**Logs:**
```bash
tail -f logs/offline_$(date +%Y-%m-%d).log
```

---

## Monitoring

**Daily automated check:**
```bash
./monitor_daily.sh
```

This script:
- Runs simulation (if not done)
- Compares online vs offline
- Queries IBKR for verification
- Updates RESULTS.md

**Schedule via cron:**
```bash
./setup_cron.sh  # Sets up daily monitoring at 17:15 UTC
```

---

## Results

**View today's trades:**
```bash
cat logs/trades_$(date +%Y-%m-%d).csv
```

**Compare modes:**
```bash
python3 compare_results.py
```

**Check IBKR execution records:**
```bash
python3 check_ibkr_trades.py
```

**Historical results:**
- See `RESULTS.md` for daily tracking
- See `results/` folder for detailed JSON

---

## Troubleshooting

**Gateway not connecting:**
```bash
# Check gateway is running
ss -tlnp | grep 4002

# Restart gateway
sudo systemctl restart ibkr-gateway
```

**No trades executing:**
- Check market hours (9:30 AM - 4:00 PM EST)
- Verify account has funds
- Check logs for errors

**For detailed troubleshooting:** See [IBKR_GUIDE.md § Troubleshooting](IBKR_GUIDE.md#7-troubleshooting)

---

## Next Steps

1. ✅ Test connection and manual trades
2. ✅ Run bot for 1 week on paper account
3. ✅ Monitor results daily
4. ✅ Adjust strategy parameters
5. ✅ Add more strategies (see [README.md § Adding Strategies](README.md#-adding-a-new-strategy))

---

## Documentation

- **[IBKR_GUIDE.md](IBKR_GUIDE.md)** - Complete setup & integration guide
- **[README.md](README.md)** - Project overview & features
- **[RESULTS.md](RESULTS.md)** - Trading results tracking
- **[docs/REPO_STRUCTURE.md](docs/REPO_STRUCTURE.md)** - Code architecture

---

**Ready to trade? Start with online paper trading and monitor for a week! 📈**

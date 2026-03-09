# IBKR Multi-Strategy Trading Engine

Python-based paper trading bot for Interactive Brokers (IBKR) with dual-mode operation: **online** (live IBKR Gateway) and **offline** (historical simulation).

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Features

- **Dual-mode trading:**
  - 🌐 **Online:** Real execution via IBKR Gateway on paper account
  - 📊 **Offline:** Simulation on historical data (IBKR or yfinance)
- **Modular strategy framework** - Easy to add new strategies
- **Risk management** - Position limits, exposure controls, stop-loss
- **Real-time monitoring** - P&L tracking, position reports
- **Automated daily runs** - Cron jobs for hands-free operation
- **Result tracking** - Compare online vs offline performance

---

## 📋 Prerequisites

- **Python 3.11+**
- **IBKR Gateway** (IBC for headless operation)
- **Paper trading account** (or live account if you're brave)

### Python Dependencies

```bash
pip install ib_insync yfinance python-dotenv pandas
```

---

## 🛠️ Setup

### 1. Clone Repository

```bash
git clone <your-repo-url>
cd ibkr-bot
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your IBKR credentials:

```bash
cp .env.example .env
nano .env
```

```ini
# IBKR Connection
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_ACCOUNT=DU7659927  # Your paper account

# Risk Limits
MAX_TOTAL_EXPOSURE=1000000.0
MAX_PORTFOLIO_DD_PCT=10.0

# Logging
LOG_DIR=logs
```

### 3. Start IBKR Gateway

```bash
# If using IBC (headless)
/opt/ibkr/ibc/scripts/ibcstart.sh 1037 -g ...

# Verify gateway is running
ss -tlnp | grep 4002
```

See **DUAL_MODE_SETUP.md** for detailed gateway setup.

---

## 🎮 Usage

### Online Paper Trading (Live Execution)

```bash
# Foreground
./run_online_paper.sh

# Or as systemd service (continuous)
sudo cp systemd/ibkr-online-trading.service /etc/systemd/system/
sudo systemctl enable ibkr-online-trading
sudo systemctl start ibkr-online-trading

# Check logs
tail -f logs/online_$(date +%Y-%m-%d).log
```

### Offline Simulation (Backtest)

```bash
# Manual run
./run_offline_sim.sh

# Daily automated run (via cron)
./setup_cron.sh  # Sets up daily simulation at 17:00 UTC
```

### Compare Results

```bash
# Compare local records
python3 compare_results.py

# Verify against IBKR execution records
python3 check_ibkr_trades.py
```

---

## 📊 Results & Monitoring

### Daily Monitoring

Automated via cron (runs at 17:15 UTC after market close):

```bash
./monitor_daily.sh
```

This script:
- Runs offline simulation (if not already done)
- Compares online vs offline results
- Queries IBKR for actual execution records
- Updates `RESULTS.md` with daily summary
- Sends alerts if issues detected

### Result Files

```
logs/
├── engine_YYYY-MM-DD.log       # Main engine logs
├── online_YYYY-MM-DD.log       # Online mode logs
├── offline_YYYY-MM-DD.log      # Offline simulation logs
├── trades_YYYY-MM-DD.csv       # All trade records

results/
├── offline_YYYY-MM-DD.json     # Simulation summary
└── daily_summary_YYYY-MM-DD.txt # Full daily report
```

See **RESULTS.md** for historical results and analysis.

---

## 🧩 Architecture

```
main.py                  # Entry point
├── engine/              # Core trading engine
│   ├── connection_hub   # IBKR connection manager
│   ├── data_manager     # Market data (IBKR + yfinance)
│   ├── order_manager    # Order execution & tracking
│   └── risk_manager     # Position limits & exposure
├── strategies/          # Trading strategies
│   ├── base             # Abstract strategy class
│   └── spy_momentum     # SPY EMA crossover strategy
└── monitoring/          # Performance tracking
    └── reporter         # P&L reports
```

See **REPO_STRUCTURE.md** for detailed code organization.

---

## 📝 Adding a New Strategy

1. **Create strategy file:** `strategies/my_strategy.py`

```python
from strategies.base import Strategy

class MyStrategy(Strategy):
    def __init__(self, hub, data, orders, risk):
        super().__init__('my_strategy', hub, data, orders, risk)
        # Initialize indicators
    
    def on_start(self):
        # Called once at startup
        pass
    
    def on_bar(self, symbol, bar):
        # Called on every new bar
        if self._should_buy(bar):
            self.orders.submit_order(
                self.strategy_id, contract, 'BUY', qty=10)
    
    def on_stop(self):
        # Called on shutdown
        pass
```

2. **Register in main.py:**

```python
from strategies.my_strategy import MyStrategy

def build_engine():
    # ... existing code ...
    strategy = MyStrategy(hub, data, orders, risk)
    # ... rest ...
```

3. **Test in simulation:**

```bash
python3 main.py --simulate
```

---

## 🔒 Safety & Security

- **Paper trading only** - No real money at risk
- **Never commit `.env`** - Contains credentials
- **Risk limits enforced** - Max exposure, position size, drawdown
- **Stop-loss protection** - Automatic stop-loss on all positions

---

## 📚 Documentation

### Core Documentation
- **[QUICKSTART.md](QUICKSTART.md)** - ⚡ Get running in 5 minutes
- **[IBKR_GUIDE.md](IBKR_GUIDE.md)** - 📖 Complete setup & integration guide
- **[RESULTS.md](RESULTS.md)** - 📊 Trading results tracking

### Technical Documentation
- **[docs/REPO_STRUCTURE.md](docs/REPO_STRUCTURE.md)** - Code architecture & organization
- **[docs/archive/](docs/archive/)** - Historical development docs

---

## 🐛 Troubleshooting

### Gateway Connection Fails

```bash
# Check gateway status
ss -tlnp | grep 4002

# Restart gateway
sudo systemctl restart ibkr-gateway  # if using systemd
```

### Simulation Gets Stale Data

```bash
# Clear yfinance cache
rm -rf ~/.cache/py-yfinance-cache
```

### No Trades Executing

- Check if market is open (`_is_market_hours()` in `spy_momentum.py`)
- Verify risk limits in `.env`
- Check logs for errors: `tail -f logs/engine_$(date +%Y-%m-%d).log`

---

## 🎯 Roadmap

- [ ] Unit tests (pytest)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] More strategies (RSI, MACD, mean reversion)
- [ ] Multi-symbol support
- [ ] Backtesting framework with visualization
- [ ] Real-time dashboard (web UI)
- [ ] Alert system (email/Telegram)

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-strategy`)
3. Commit your changes (`git commit -m 'Add amazing strategy'`)
4. Push to the branch (`git push origin feature/amazing-strategy`)
5. Open a Pull Request

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/ibkr-bot/issues)
- **Email:** your.email@example.com

---

## ⚠️ Disclaimer

This software is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred while using this software. Always test strategies thoroughly in paper trading before considering live execution.

---

**Built with ❤️ by [Your Name]**

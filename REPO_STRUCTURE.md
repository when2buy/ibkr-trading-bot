# Repository Structure

```
ibkr-bot/
├── README.md                      # Main project overview
├── README_DUAL_MODE.md            # Quick start for dual-mode trading
├── DUAL_MODE_SETUP.md             # Detailed dual-mode documentation
├── RESULTS.md                     # Daily trading results tracking
├── REPO_STRUCTURE.md              # This file - code organization
├── TASK.md                        # Original task specification
│
├── config.py                      # Configuration (loads from .env)
├── main.py                        # Entry point - starts online or offline mode
│
├── engine/                        # Core trading engine
│   ├── connection_hub.py          # IBKR Gateway connection manager
│   ├── data_manager.py            # Historical & real-time data (IBKR + yfinance)
│   ├── order_manager.py           # Order submission & fill tracking
│   └── risk_manager.py            # Position limits & exposure controls
│
├── strategies/                    # Trading strategies
│   ├── base.py                    # Abstract base strategy class
│   └── spy_momentum.py            # SPY EMA crossover strategy
│
├── monitoring/                    # Performance tracking
│   └── reporter.py                # P&L reports & position summaries
│
├── scripts/                       # Automation scripts
│   ├── run_online_paper.sh        # Start online paper trading
│   ├── run_offline_sim.sh         # Run offline simulation
│   ├── run_daily_offline.sh       # Cron-friendly daily simulation
│   ├── monitor_daily.sh           # Daily monitoring & alerts
│   └── setup_cron.sh              # Install cron jobs
│
├── utils/                         # Analysis & verification tools
│   ├── compare_results.py         # Compare online vs offline results
│   └── check_ibkr_trades.py       # Query IBKR execution records
│
├── systemd/                       # Service configurations
│   └── ibkr-online-trading.service # Systemd service for continuous trading
│
├── logs/                          # Runtime logs (not committed)
│   ├── engine_YYYY-MM-DD.log      # Main engine logs
│   ├── online_YYYY-MM-DD.log      # Online mode logs
│   ├── offline_YYYY-MM-DD.log     # Offline simulation logs
│   ├── monitor_YYYY-MM-DD.log     # Daily monitoring logs
│   └── trades_YYYY-MM-DD.csv      # Daily trade records
│
└── results/                       # Analysis outputs (not committed)
    ├── offline_YYYY-MM-DD.json    # Daily simulation summary
    └── daily_summary_YYYY-MM-DD.txt # Full daily report

.env                               # Secrets (NEVER commit this)
.gitignore                         # Git ignore rules
```

---

## 📦 Module Organization

### Core Engine (`engine/`)
- **connection_hub.py** - Manages IBKR connection lifecycle, reconnection logic
- **data_manager.py** - Unified data interface, auto-fallback IBKR → yfinance
- **order_manager.py** - Order execution, fill logging, position tracking
- **risk_manager.py** - Pre-trade risk checks, exposure limits

### Strategies (`strategies/`)
- **base.py** - Abstract strategy with lifecycle hooks (on_start, on_bar, on_stop)
- **spy_momentum.py** - Example strategy: EMA9/21 crossover with trailing stop

### Monitoring (`monitoring/`)
- **reporter.py** - Periodic P&L summaries, position reports

### Scripts (`scripts/` - should be in root or separate)
All `.sh` scripts for running and monitoring:
- Online/offline execution
- Daily automation via cron
- Result comparison

### Utils (`utils/` - analysis tools)
- Compare local vs IBKR records
- Result aggregation
- Performance analysis

---

## 🔧 Configuration

### Environment Variables (`.env`)
```bash
# IBKR Connection
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_ACCOUNT=DU7659927

# Risk Limits
MAX_TOTAL_EXPOSURE=1000000.0
MAX_PORTFOLIO_DD_PCT=10.0

# Logging
LOG_DIR=logs
```

### Config Loading (`config.py`)
Loads `.env`, provides defaults, validates settings.

---

## 🚀 Entry Points

### 1. Online Paper Trading
```bash
./run_online_paper.sh
# or
python3 main.py
```

### 2. Offline Simulation
```bash
./run_offline_sim.sh
# or
python3 main.py --simulate
```

### 3. Daily Monitoring
```bash
./monitor_daily.sh
```

### 4. Setup Automation
```bash
./setup_cron.sh
```

---

## 📊 Data Flow

### Online Mode
```
IBKR Gateway (port 4002)
    ↓
ConnectionHub.connect()
    ↓
DataManager.subscribe_realtime('SPY')
    ↓
Strategy.on_bar(bar) → signal
    ↓
OrderManager.submit_order()
    ↓
IBKR fills → Strategy.on_fill()
    ↓
Reporter logs P&L
```

### Offline Mode
```
DataManager.get_bars() → IBKR historical
    ↓ (fallback)
yfinance.download() if IBKR unavailable
    ↓
main.run_simulation() replays bars
    ↓
Strategy.on_bar(bar) → signal
    ↓
OrderManager logs simulated fills
    ↓
Final summary printed
```

---

## 🧪 Testing Strategy

1. **Unit tests** - Test individual components (risk checks, order logic)
2. **Integration tests** - Test engine wiring (mock IBKR)
3. **Simulation tests** - Backtest on historical data
4. **Paper trading** - Live execution on paper account
5. **Code review** - Manual review before deploying strategies

---

## 📝 Development Workflow

1. **Develop locally** - Test strategies in offline simulation
2. **Commit to git** - Track changes, version control
3. **Push to GitHub** - Code review, CI/CD (future)
4. **Deploy to server** - Pull latest, restart services
5. **Monitor results** - Daily checks via cron

---

## 🔒 Security

- **Never commit `.env`** - Contains IBKR credentials
- **Paper trading only** - No real money at risk
- **Read-only mode** - Simulation uses read-only IBKR connection
- **Local logs** - Sensitive data never leaves the server

---

## 📚 Documentation

- **README.md** - Project overview, quick start
- **DUAL_MODE_SETUP.md** - Detailed setup for both modes
- **RESULTS.md** - Trading results tracking
- **REPO_STRUCTURE.md** - This file - code organization
- **TASK.md** - Original requirements

---

## 🎯 Next Steps

- [ ] Add unit tests (pytest)
- [ ] Create GitHub Actions CI/CD pipeline
- [ ] Add more strategies (RSI, MACD, etc.)
- [ ] Implement multi-symbol support
- [ ] Add backtesting framework with visualization
- [ ] Set up alerts (email/Telegram on errors)
- [ ] Create dashboard for real-time monitoring

---

**Last updated:** 2026-03-05 01:30 UTC

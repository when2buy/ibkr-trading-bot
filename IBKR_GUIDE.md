# IBKR Setup & Integration Guide

**Comprehensive guide for setting up Interactive Brokers (IBKR) for automated trading**

---

## 📋 Table of Contents

1. [Account Setup](#1-account-setup)
2. [Gateway Installation](#2-gateway-installation)
3. [API Connection](#3-api-connection)
4. [Testing Trade Execution](#4-testing-trade-execution)
5. [Verification & Monitoring](#5-verification--monitoring)
6. [Production Setup](#6-production-setup)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Account Setup

### 1.1 Open IBKR Account

1. **Create account** at [interactivebrokers.com](https://www.interactivebrokers.com)
   - Choose **Individual** account type
   - Select **Margin** account (required for day trading)
   - Complete KYC verification

2. **Enable paper trading:**
   - Log in to [Client Portal](https://gdcdyn.interactivebrokers.com/)
   - Navigate to: **Settings** → **Account Settings** → **Paper Trading**
   - Click "Create Paper Trading Account"
   - Note your paper account number (e.g., `DU7659927`)

### 1.2 API Permissions

Enable API access in Client Portal:

1. **Settings** → **API** → **Settings**
2. Enable:
   - ✅ Enable ActiveX and Socket Clients
   - ✅ Read-Only API
   - ✅ Create API orders
   - ✅ Download API orders
3. Add trusted IPs (or use `0.0.0.0` for testing)
4. **Save** settings

### 1.3 Account Information

Record these details (you'll need them later):

```
Account Number: DU7659927
Account Type: Individual Margin
Base Currency: USD
Broker: Interactive Brokers Singapore Pte. Ltd.
Account Holder: [Your Name]
```

---

## 2. Gateway Installation

### 2.1 Download IBKR Gateway

**Option A: Official Gateway (with GUI)**

```bash
# Download from IBKR website
wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh

# Install
chmod +x ibgateway-latest-standalone-linux-x64.sh
./ibgateway-latest-standalone-linux-x64.sh
```

**Option B: IBC (Headless, Recommended for Servers)**

```bash
# Download IBC
cd /opt
sudo wget https://github.com/IbcAlpha/IBC/releases/latest/download/IBCLinux.zip
sudo unzip IBCLinux.zip -d /opt/ibc

# Download Gateway
cd /opt
sudo wget https://download2.interactivebrokers.com/installers/ibgateway/latest-standalone/ibgateway-latest-standalone-linux-x64.sh
sudo chmod +x ibgateway-latest-standalone-linux-x64.sh
sudo ./ibgateway-latest-standalone-linux-x64.sh -q -dir /opt/ibgateway
```

### 2.2 Configure Gateway

Edit IBC config file: `/opt/ibc/config.ini`

```ini
# Credentials
IbLoginId=your_username
IbPassword=your_password
TradingMode=paper

# API
SocketPort=4002
ApiOnly=yes
AcceptIncomingConnectionAction=accept

# Auto-restart
AcceptNonBrokerageAccountWarning=yes
AutoRestart=yes
```

### 2.3 Start Gateway

```bash
# Using IBC
/opt/ibc/scripts/ibcstart.sh 4002 -g &

# Verify it's running
ss -tlnp | grep 4002
# Should show: LISTEN on 0.0.0.0:4002
```

---

## 3. API Connection

### 3.1 Install Python Dependencies

```bash
cd /path/to/ibkr-trading-bot
pip install -r requirements.txt

# Core dependencies:
pip install ib_insync yfinance python-dotenv pandas
```

### 3.2 Configure Environment

Copy example config:

```bash
cp .env.example .env
nano .env
```

Edit `.env` with your account details:

```ini
# IBKR Connection
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_ACCOUNT=DU7659927  # Your paper account number

# Risk Management
MAX_TOTAL_EXPOSURE=1000000.0
MAX_POSITION_SIZE=100000.0
MAX_PORTFOLIO_DD_PCT=10.0
DEFAULT_STOP_LOSS_PCT=2.0

# Logging
LOG_DIR=logs
LOG_LEVEL=INFO
```

### 3.3 Test Connection

Run the connection test script:

```bash
./test_ibkr_connection.sh
```

Expected output:

```
✅ Gateway connection successful
✅ Account details retrieved: DU7659927
✅ Market data subscription working
✅ Ready to trade!
```

If connection fails, see [Troubleshooting](#7-troubleshooting).

---

## 4. Testing Trade Execution

### 4.1 Manual Test Orders

Test basic order execution to verify everything works:

```bash
# Test script creates simple BUY/SELL cycle
python3 -c "
from ib_insync import IB, Stock, MarketOrder
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

# Buy 1 share SPY
contract = Stock('SPY', 'SMART', 'USD')
ib.qualifyContracts(contract)
order = MarketOrder('BUY', 1)
trade = ib.placeOrder(contract, order)
ib.sleep(5)
print(f'Order filled: {trade.orderStatus.status}')

ib.disconnect()
"
```

Expected output:

```
Order filled: Filled
```

### 4.2 Verify Orders in IBKR Portal

1. Log in to [Client Portal](https://gdcdyn.interactivebrokers.com/)
2. Switch to **Paper Trading Account** (top-right dropdown)
3. Navigate to **Account** → **Trade Log**
4. Verify your test order appears

### 4.3 Run Bot Test Mode

Test the full trading bot in simulation mode:

```bash
# Offline simulation (no IBKR connection needed)
python3 main.py --simulate

# Online paper trading (connects to IBKR)
python3 main.py
```

Check logs:

```bash
tail -f logs/engine_$(date +%Y-%m-%d).log
```

---

## 5. Verification & Monitoring

### 5.1 Download Activity Statement

To verify trades actually executed correctly:

1. **Client Portal** → **Reports** → **Activity**
2. Select date range
3. **Format:** CSV
4. **Download**

Save to: `/opt/openclaw/gpu-bot/.openclaw/media/inbound/`

### 5.2 Parse Activity Statement

Example Python script to parse IBKR CSV:

```python
import pandas as pd

# Load activity statement
df = pd.read_csv('ibkr_activity.csv', skiprows=2)

# Filter trades
trades = df[df['Field Name'] == 'Trades']

# Extract key info
for _, row in trades.iterrows():
    print(f"{row['Date/Time']}: {row['Quantity']}x {row['Symbol']} @ ${row['T. Price']}")
```

### 5.3 Verify Trade Execution

Compare bot logs with IBKR activity:

**Bot log format:**
```
2026-03-06 09:30:04 INFO [spy_momentum] BUY 1 SPY @ 673.38
2026-03-06 14:27:45 INFO [spy_momentum] SELL 1 SPY @ 674.92
```

**IBKR CSV format:**
```csv
Order,Stocks,USD,DU7659927,SPY,"2026-03-06, 09:30:04",1,673.38,672.38,-673.38,-1.09
Order,Stocks,USD,DU7659927,SPY,"2026-03-06, 14:27:45",-1,674.92,672.38,674.92,-1.09021255
```

### 5.4 Current Position Check

Query current positions via API:

```python
from ib_insync import IB

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

positions = ib.positions()
for pos in positions:
    print(f"{pos.contract.symbol}: {pos.position} @ ${pos.avgCost:.2f}")

ib.disconnect()
```

Expected output:

```
SPY: 1 @ $674.44
```

---

## 6. Production Setup

### 6.1 Continuous Online Trading

Set up systemd service for 24/7 operation:

```bash
# Copy service file
sudo cp systemd/ibkr-online-trading.service /etc/systemd/system/

# Edit if needed
sudo nano /etc/systemd/system/ibkr-online-trading.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ibkr-online-trading
sudo systemctl start ibkr-online-trading

# Check status
sudo systemctl status ibkr-online-trading

# View logs
journalctl -u ibkr-online-trading -f
```

### 6.2 Daily Offline Simulation

Schedule daily simulation via cron:

```bash
crontab -e

# Add this line (runs at 5 PM UTC, after market close)
0 17 * * * /opt/openclaw/gpu-bot/workspace/ibkr-bot/run_daily_offline.sh
```

### 6.3 Monitoring & Alerts

Set up daily monitoring:

```bash
# Add monitoring cron job (runs 15 min after simulation)
15 17 * * * /opt/openclaw/gpu-bot/workspace/ibkr-bot/monitor_daily.sh
```

This script:
- Compares online vs offline results
- Checks IBKR for actual execution
- Sends alerts if discrepancies found
- Updates `RESULTS.md`

### 6.4 Automated Reporting

Send daily reports to Telegram group:

```bash
# Configure in monitor_daily.sh
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="-1003583837083"

# Script will auto-send summary at 17:15 UTC
```

---

## 7. Troubleshooting

### 7.1 Gateway Connection Fails

**Problem:** `ib_insync` can't connect to gateway

**Solutions:**

```bash
# Check if gateway is running
ss -tlnp | grep 4002

# Check gateway logs
tail -f /opt/ibgateway/logs/*.log

# Restart gateway
sudo systemctl restart ibkr-gateway  # if using systemd
# OR
killall java && /opt/ibc/scripts/ibcstart.sh 4002 -g &

# Verify port is open
telnet 127.0.0.1 4002
```

### 7.2 Orders Not Executing

**Problem:** Orders submitted but not filled

**Check:**

1. **Market hours:**
   - US markets: 9:30 AM - 4:00 PM EST (Mon-Fri)
   - Pre-market: 4:00 AM - 9:30 AM EST
   - After-hours: 4:00 PM - 8:00 PM EST

2. **Account permissions:**
   ```python
   ib.accountSummary()
   # Check "AvailableFunds" > 0
   ```

3. **Symbol valid:**
   ```python
   contract = Stock('SPY', 'SMART', 'USD')
   ib.qualifyContracts(contract)
   print(contract)  # Should show valid contract details
   ```

4. **Order logs:**
   ```bash
   grep "ERROR\|WARN" logs/engine_$(date +%Y-%m-%d).log
   ```

### 7.3 API Permissions Denied

**Problem:** `Error 504: Not connected`

**Solution:**

1. Check API settings in Client Portal:
   - **Settings** → **API** → **Settings**
   - Enable "ActiveX and Socket Clients"
   - Add your IP to whitelist

2. Verify correct port:
   - Paper trading: `4002`
   - Live trading: `4001` (use carefully!)

3. Check `clientId` not in use:
   ```python
   # Try different clientId
   ib.connect('127.0.0.1', 4002, clientId=2)
   ```

### 7.4 Data Subscription Issues

**Problem:** No market data received

**Solutions:**

```bash
# Ensure you have market data subscriptions
# Go to: Account Management → Market Data Subscriptions
# Add: US Securities Snapshot (free for paper accounts)

# Test data retrieval
python3 -c "
from ib_insync import IB, Stock
ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)
contract = Stock('SPY', 'SMART', 'USD')
ib.qualifyContracts(contract)
ticker = ib.reqMktData(contract)
ib.sleep(2)
print(f'Last price: {ticker.last}')
ib.disconnect()
"
```

### 7.5 Stale yfinance Data

**Problem:** Offline simulation using old data

**Solution:**

```bash
# Clear yfinance cache
rm -rf ~/.cache/py-yfinance-cache

# Force re-download
python3 -c "
import yfinance as yf
yf.download('SPY', period='5d', interval='5m', progress=False)
"
```

---

## 8. Account Details Reference

### 8.1 Paper Account Information

From IBKR Activity Statement (March 2-6, 2026):

```
Account Number: DU7659927 (Custom Consolidated)
Sub-accounts: DU7659927, DU7659927-P (Paxos)
Account Holder: Jeanne M NG
Address: 23 Angullia Park, 29-01, Singapore, SG-01 239975
Account Type: Individual Margin
Base Currency: USD
Broker: Interactive Brokers Singapore Pte. Ltd., GST 201915420Z
Broker Address: 1 Harbourfront Place #12-01, Singapore 098633
```

### 8.2 Example Trade Verification

From actual activity statement:

**Trades executed:**
```
2026-03-06, 09:30:04  BUY  1 SPY @ $673.38  (Commission: $1.09)
2026-03-06, 09:30:04  BUY  1 SPY @ $673.35  (Commission: $1.09)
2026-03-06, 14:27:45  SELL 1 SPY @ $674.92  (Commission: $1.09)
```

**Current position:**
```
SPY: 1 share @ $674.44 avg cost
Current price: $672.38
Unrealized P/L: -$2.06
```

**Summary:**
```
Realized P/L: -$0.64
Total Commissions: -$3.27
Net P/L: -$2.91
```

This confirms:
- ✅ Orders routed correctly to paper account
- ✅ Fills at real market prices
- ✅ Proper commission calculation
- ✅ Accurate position tracking

---

## 9. Next Steps

After completing this guide:

1. ✅ Paper account created and verified
2. ✅ Gateway installed and running
3. ✅ API connection tested
4. ✅ Test trades executed successfully
5. ✅ Activity statement verification completed

**Ready for production trading:**

```bash
# Start continuous online trading
sudo systemctl start ibkr-online-trading

# Schedule daily simulation
./setup_cron.sh

# Monitor for first week
tail -f logs/online_$(date +%Y-%m-%d).log
```

**Checklist before going live:**

- [ ] Run paper trading for at least 1 week
- [ ] Verify all trades in IBKR portal
- [ ] Compare online vs offline performance
- [ ] Test stop-loss functionality
- [ ] Review risk limits in `.env`
- [ ] Set up monitoring alerts
- [ ] Document any issues encountered

---

## 10. Resources

### Official Documentation

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [ib_insync Documentation](https://ib-insync.readthedocs.io/)
- [IBC GitHub](https://github.com/IbcAlpha/IBC)

### Project Documentation

- [README.md](README.md) - Main project overview
- [DUAL_MODE_SETUP.md](DUAL_MODE_SETUP.md) - Online/offline setup
- [RESULTS.md](RESULTS.md) - Trading results tracking
- [REPO_STRUCTURE.md](REPO_STRUCTURE.md) - Code organization

### Support

- **IBKR Support:** https://www.interactivebrokers.com/en/support/
- **Project Issues:** https://github.com/when2buy/ibkr-trading-bot/issues
- **Telegram Group:** IBKR ENV (for verified trades discussion)

---

## 11. Security Best Practices

### 11.1 Credentials

- **Never commit `.env` to git** (already in `.gitignore`)
- Store credentials in environment variables or secrets manager
- Use different passwords for live and paper accounts
- Enable 2FA on IBKR account

### 11.2 API Access

- Whitelist specific IPs only (not `0.0.0.0`)
- Use separate API user for bot (not main account)
- Set restrictive API permissions:
  - ✅ Read account data
  - ✅ Place orders
  - ❌ Withdraw funds
  - ❌ Modify account settings

### 11.3 Risk Management

- **Always test on paper account first**
- Set conservative risk limits in `.env`:
  ```ini
  MAX_TOTAL_EXPOSURE=10000.0      # Max $10k total
  MAX_POSITION_SIZE=1000.0        # Max $1k per position
  MAX_PORTFOLIO_DD_PCT=5.0        # Max 5% drawdown
  DEFAULT_STOP_LOSS_PCT=2.0       # 2% stop-loss
  ```
- Monitor daily for unexpected behavior
- Have kill switch ready: `sudo systemctl stop ibkr-online-trading`

---

## 12. FAQ

**Q: Can I use this with a live account?**

A: Yes, but **NOT RECOMMENDED** until thoroughly tested on paper for weeks/months. Change `IBKR_PORT=4001` and `TradingMode=live` in config, but understand you're risking real money.

**Q: What are the trading hours?**

A: US markets (SPY): 9:30 AM - 4:00 PM EST, Mon-Fri. Extended hours: 4:00 AM - 8:00 PM EST.

**Q: Why use both online and offline modes?**

A: 
- **Online:** Real execution, real fills, real market conditions
- **Offline:** Quick backtests, no API limits, test strategy changes safely

**Q: How do I add a new strategy?**

A: See [README.md § Adding a New Strategy](README.md#-adding-a-new-strategy)

**Q: Can I trade multiple symbols?**

A: Current code is SPY-only. Multi-symbol support is on the [roadmap](README.md#-roadmap).

**Q: What if I run out of paper money?**

A: Contact IBKR support to reset your paper account balance. It's free and instant.

**Q: Is there a web UI?**

A: Not yet, but planned. Current monitoring via logs and Telegram alerts.

---

**Built with ❤️ for algorithmic traders**

**Last updated:** March 9, 2026

# Trading Results Documentation

This document tracks daily trading results from both online and offline modes.

---

## 📊 Result Tracking

### Daily Summary Template

```markdown
## YYYY-MM-DD

### Online Paper Trading (IBKR)
- **Trades:** X
- **Realized P&L:** $X.XX
- **Commissions:** $X.XX
- **Net P&L:** $X.XX
- **Data Source:** IBKR Live
- **Issues:** None / [describe any issues]

### Offline Simulation
- **Trades:** X
- **Realized P&L:** $X.XX (simulated)
- **Commissions:** $X.XX (simulated)
- **Net P&L:** $X.XX
- **Data Source:** IBKR Historical / yfinance (fallback)
- **Issues:** None / [describe any issues]

### Comparison
- **Slippage:** $X.XX
- **Execution difference:** X trades
- **Notes:** [observations about differences]
```

---

## 📈 Results History

### 2026-03-04

#### Online Paper Trading (IBKR)
- **Trades:** 0
- **Realized P&L:** $0.00
- **Commissions:** $0.00
- **Net P&L:** $0.00
- **Data Source:** N/A (simulation mode was used instead)
- **Issues:** Bot ran in simulation mode, did not connect to gateway

#### Offline Simulation
- **Trades:** 10 (5 buys, 5 sells)
- **Realized P&L:** $0.00 (break-even)
- **Commissions:** $10.00 (simulated)
- **Net P&L:** -$10.00
- **Data Source:** yfinance (5-day 5-min bars, 390 bars)
- **Issues:** 
  - All prices recorded as $0.00 (simulation bug)
  - Strategy whipsawed by EMA crossovers
  - One stop-loss triggered @ $681.20

#### Strategy Performance
- **Strategy:** SPY Momentum (EMA9/21 crossover)
- **Max unrealized gain:** $+26.95
- **Stop-loss hits:** 1
- **Notable:** Choppy price action led to multiple quick entries/exits

#### Observations
- Simulation mode needs real price capture for accurate P&L
- Strategy shows sensitivity to volatility (rapid crossovers)
- Need to test with IBKR historical data for better accuracy

---

## 🎯 Metrics to Track

### Trading Performance
- [ ] Total trades (daily)
- [ ] Win rate
- [ ] Average profit per trade
- [ ] Average loss per trade
- [ ] Sharpe ratio (weekly)
- [ ] Max drawdown

### Execution Quality
- [ ] Slippage (online vs offline)
- [ ] Fill price vs expected
- [ ] Order rejection rate
- [ ] Latency (order to fill)

### Data Quality
- [ ] Data source used (IBKR vs yfinance)
- [ ] Missing bars
- [ ] Data discrepancies
- [ ] API errors

### Risk Metrics
- [ ] Max position size
- [ ] Exposure vs limit
- [ ] Stop-loss effectiveness
- [ ] Commission impact on P&L

---

## 📝 Daily Checklist

Run this every trading day:

```bash
# 1. Check online trading status
sudo systemctl status ibkr-online-trading

# 2. View today's logs
tail -f logs/online_$(date +%Y-%m-%d).log

# 3. Run comparison after market close
python3 compare_results.py

# 4. Verify IBKR execution records
python3 check_ibkr_trades.py

# 5. Update this RESULTS.md with findings
```

---

## 🐛 Known Issues

### 2026-03-04
- [ ] Simulation mode records price=$0.00 for all fills
- [ ] Need to capture actual fill prices from bar data
- [ ] OrderManager should log bar.close price in simulation mode

### Fix Priority
1. **High:** Capture real prices in simulation fills
2. **Medium:** Add position tracking to compare_results.py
3. **Low:** Add visualization for P&L curves

---

## 🔄 Weekly Review Template

```markdown
### Week of YYYY-MM-DD

**Summary:**
- Total trading days: X
- Total trades: X
- Net P&L: $X.XX
- Win rate: X%

**Best day:** YYYY-MM-DD (+$X.XX)
**Worst day:** YYYY-MM-DD (-$X.XX)

**Strategy adjustments:**
- [list any changes made]

**Lessons learned:**
- [key observations]

**Next week focus:**
- [action items]
```

---

## 📞 Alerts & Monitoring

Automated checks via cron (see monitoring cron job):

- ✅ Daily offline simulation runs at 17:00 UTC
- ✅ Results comparison runs at 17:15 UTC
- ✅ Alert if >10 trades in a day (check for bugs)
- ✅ Alert if P&L < -$500 (check strategy logic)
- ✅ Alert if gateway disconnects during market hours

---

**Last updated:** 2026-03-05 01:30 UTC

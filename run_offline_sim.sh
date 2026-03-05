#!/bin/bash
# Offline simulation - backtests on yfinance data without IBKR connection

set -e
cd "$(dirname "$0")"

echo "📊 Starting OFFLINE simulation (yfinance replay)"
echo "Date: $(date +%Y-%m-%d)"
echo ""

python3 main.py --simulate 2>&1 | tee -a "logs/offline_$(date +%Y-%m-%d).log"

echo ""
echo "✅ Simulation complete"
echo "Results: logs/trades_$(date +%Y-%m-%d).csv"

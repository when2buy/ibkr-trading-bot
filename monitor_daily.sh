#!/bin/bash
# Daily monitoring script - checks results and updates documentation
# Run via cron after market close: 0 17 * * * /opt/openclaw/gpu-bot/workspace/ibkr-bot/monitor_daily.sh

set -e
cd /opt/openclaw/gpu-bot/workspace/ibkr-bot

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S UTC")
LOG_FILE="logs/monitor_${DATE}.log"

echo "[$TIMESTAMP] Starting daily monitoring..." | tee -a "$LOG_FILE"

# 1. Run offline simulation (if not already run)
if [ ! -f "results/offline_${DATE}.json" ]; then
    echo "[$TIMESTAMP] Running offline simulation..." | tee -a "$LOG_FILE"
    ./run_daily_offline.sh >> "$LOG_FILE" 2>&1
fi

# 2. Compare results
echo "[$TIMESTAMP] Comparing results..." | tee -a "$LOG_FILE"
COMPARISON=$(python3 compare_results.py 2>&1)
echo "$COMPARISON" | tee -a "$LOG_FILE"

# 3. Query IBKR for actual executions
echo "[$TIMESTAMP] Checking IBKR execution records..." | tee -a "$LOG_FILE"
IBKR_CHECK=$(python3 check_ibkr_trades.py 2>&1)
echo "$IBKR_CHECK" | tee -a "$LOG_FILE"

# 4. Extract metrics
TRADES=$(echo "$COMPARISON" | grep "^Trades:" | awk '{print $2}')
PNL=$(echo "$COMPARISON" | grep "^Net P&L:" | awk '{print $3}')
MODE=$(echo "$COMPARISON" | grep "^Mode:" | cut -d: -f2-)

# 5. Check for alerts
ALERT=false
ALERT_MSG=""

# Alert if >10 trades (possible bug)
if [ ! -z "$TRADES" ] && [ "$TRADES" -gt 10 ]; then
    ALERT=true
    ALERT_MSG="${ALERT_MSG}\n⚠️  High trade count: $TRADES trades (check for bugs)"
fi

# Alert if online trading service is down during market hours
HOUR=$(date -u +%H)
if [ "$HOUR" -ge 14 ] && [ "$HOUR" -lt 21 ]; then  # 14:00-21:00 UTC = 9:00-16:00 ET
    if ! systemctl is-active --quiet ibkr-online-trading 2>/dev/null; then
        ALERT=true
        ALERT_MSG="${ALERT_MSG}\n⚠️  Online trading service is DOWN during market hours!"
    fi
fi

# Alert if gateway is not responding
if ! nc -z 127.0.0.1 4002 2>/dev/null; then
    ALERT=true
    ALERT_MSG="${ALERT_MSG}\n⚠️  IBKR Gateway not responding on port 4002"
fi

# 6. Generate daily summary
SUMMARY_FILE="results/daily_summary_${DATE}.txt"
cat > "$SUMMARY_FILE" <<EOF
Daily Trading Summary - $DATE
Generated: $TIMESTAMP

Mode: $MODE
Trades: ${TRADES:-0}
Net P&L: ${PNL:-\$0.00}

--- Comparison Output ---
$COMPARISON

--- IBKR Verification ---
$IBKR_CHECK

--- Alerts ---
EOF

if [ "$ALERT" = true ]; then
    echo -e "$ALERT_MSG" | tee -a "$SUMMARY_FILE" "$LOG_FILE"
else
    echo "✅ No alerts" | tee -a "$SUMMARY_FILE" "$LOG_FILE"
fi

# 7. Append to RESULTS.md (basic automation - manual review recommended)
echo "" >> RESULTS.md
echo "### $DATE (Auto-generated)" >> RESULTS.md
echo "" >> RESULTS.md
echo "**Mode:** $MODE" >> RESULTS.md
echo "**Trades:** ${TRADES:-0}" >> RESULTS.md
echo "**Net P&L:** ${PNL:-\$0.00}" >> RESULTS.md
if [ "$ALERT" = true ]; then
    echo -e "**Alerts:**$ALERT_MSG" >> RESULTS.md
fi
echo "" >> RESULTS.md
echo "*See \`results/daily_summary_${DATE}.txt\` for full details*" >> RESULTS.md
echo "" >> RESULTS.md

echo "[$TIMESTAMP] Daily monitoring complete" | tee -a "$LOG_FILE"
echo "Summary: $SUMMARY_FILE"

# 8. If there are alerts, send notification (optional - implement messaging here)
if [ "$ALERT" = true ]; then
    echo "[$TIMESTAMP] ALERTS DETECTED - review required" | tee -a "$LOG_FILE"
    # TODO: Add notification via message tool or email
fi

exit 0

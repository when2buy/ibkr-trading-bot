#!/bin/bash
# Daily offline simulation - cron-friendly

cd /opt/openclaw/gpu-bot/workspace/ibkr-bot

DATE=$(date +%Y-%m-%d)
LOG_FILE="logs/offline_${DATE}.log"
RESULT_FILE="results/offline_${DATE}.json"

mkdir -p logs results

echo "[$DATE] Running offline simulation..." | tee -a "$LOG_FILE"

# Run simulation
python3 main.py --simulate >> "$LOG_FILE" 2>&1

# Extract summary
TRADES=$(grep "Total fills:" "$LOG_FILE" | tail -1 | awk '{print $3}')
PNL=$(grep "Final P&L:" "$LOG_FILE" | tail -1 | awk '{print $3}')

# Save JSON result
cat > "$RESULT_FILE" <<EOF
{
  "date": "$DATE",
  "mode": "offline_simulation",
  "trades": ${TRADES:-0},
  "pnl": "${PNL:-\$0.00}",
  "log": "$LOG_FILE"
}
EOF

echo "[$DATE] Offline simulation complete: $TRADES trades, $PNL" | tee -a "$LOG_FILE"

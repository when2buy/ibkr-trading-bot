#!/bin/bash
# Setup cron jobs for automated trading and monitoring

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up cron jobs for IBKR trading bot..."
echo ""

# Check if cron is installed
if ! command -v crontab &> /dev/null; then
    echo "❌ crontab not found. Install cron first:"
    echo "   apt-get install cron"
    exit 1
fi

# Backup existing crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

# Add new cron jobs (skip if already exists)
(crontab -l 2>/dev/null | grep -v "ibkr-bot"; cat <<EOF

# IBKR Trading Bot - Daily Monitoring
# Runs at 17:15 UTC (12:15 PM ET, after market close)
15 17 * * * $SCRIPT_DIR/monitor_daily.sh >> $SCRIPT_DIR/logs/cron.log 2>&1

EOF
) | crontab -

echo "✅ Cron jobs installed:"
echo ""
crontab -l | grep -A2 "IBKR Trading Bot"
echo ""
echo "📋 What was set up:"
echo "   • Daily monitoring at 17:15 UTC (after market close)"
echo "   • Runs offline simulation + comparison + IBKR verification"
echo "   • Auto-updates RESULTS.md"
echo "   • Logs to: logs/monitor_YYYY-MM-DD.log"
echo ""
echo "📂 Cron log: $SCRIPT_DIR/logs/cron.log"
echo "📂 Backups: /tmp/crontab_backup_*.txt"
echo ""
echo "To view cron jobs:"
echo "   crontab -l"
echo ""
echo "To remove cron jobs:"
echo "   crontab -e"
echo "   # Delete the IBKR Trading Bot lines"

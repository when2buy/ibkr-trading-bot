#!/bin/bash
# Online paper trading - connects to IBKR Gateway for real paper account execution

set -e
cd "$(dirname "$0")"

echo "🌐 Starting ONLINE paper trading (IBKR Gateway)"
echo "Account: $(grep IBKR_ACCOUNT ../.env | cut -d'=' -f2)"
echo "Gateway: $(grep IBKR_HOST ../.env | cut -d'=' -f2):$(grep IBKR_PORT ../.env | cut -d'=' -f2)"
echo ""

# Verify gateway is up
if ! nc -z 127.0.0.1 4002 2>/dev/null; then
    echo "❌ IBKR Gateway not responding on port 4002"
    echo "Start it with: /opt/ibkr/ibc/scripts/ibcstart.sh"
    exit 1
fi

echo "✅ Gateway online"
echo "Starting trading engine..."
echo ""

python3 main.py 2>&1 | tee -a "logs/online_$(date +%Y-%m-%d).log"

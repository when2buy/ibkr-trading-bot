#!/bin/bash
# Complete IBKR connection test

echo "=== IBKR Connection Test ==="
echo ""

# 1. Start gateway
echo "1️⃣ Starting IBKR Gateway..."
DISPLAY=:1 nohup /opt/ibkr/ibc/scripts/ibcstart.sh 1037 -g \
  --tws-path=/opt/ibkr --ibc-path=/opt/ibkr/ibc \
  --ibc-ini=/opt/ibkr/ibc/config.ini \
  --user=koxqlg052 --pw=papertrading123! --mode=paper \
  > /opt/ibkr/gateway.log 2>&1 &

echo "   Waiting 15 seconds for gateway to start..."
sleep 15

# 2. Check if port is open
echo ""
echo "2️⃣ Checking port 4002..."
if ss -tlnp | grep -q 4002; then
    echo "   ✅ Gateway is listening on port 4002"
else
    echo "   ❌ Port 4002 not open"
    exit 1
fi

# 3. Test connection
echo ""
echo "3️⃣ Testing connection..."
python3 << 'PYEOF'
from ib_insync import IB
ib = IB()
try:
    ib.connect('127.0.0.1', 4002, clientId=99, readonly=True, timeout=10)
    print("   ✅ Connected to IBKR Gateway")
    print(f"   Account: {ib.client.getAccounts()}")
    ib.disconnect()
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    exit(1)
PYEOF

# 4. Download data
echo ""
echo "4️⃣ Downloading historical data..."
cd /opt/openclaw/gpu-bot/workspace/ibkr-bot
python3 << 'PYEOF'
from engine.connection_hub import ConnectionHub
from engine.data_manager import DataManager
import asyncio

async def test():
    hub = ConnectionHub('127.0.0.1', 4002, 98, 'DU7659927')
    await hub.connect()
    data = DataManager(hub)
    df = data.get_bars('SPY', period='1 D', interval='5 mins')
    print(f"   ✅ Downloaded {len(df)} bars of SPY data from IBKR")
    print(f"   Latest close: ${df['Close'].iloc[-1]:.2f}")
    hub.disconnect()

asyncio.run(test())
PYEOF

# 5. Test paper trading (simulation)
echo ""
echo "5️⃣ Testing paper trading (simulation mode)..."
timeout 30 python3 main.py --simulate 2>&1 | grep -E "(Data source|Final P&L|Total fills)" | head -3

echo ""
echo "=== All Tests Complete ==="

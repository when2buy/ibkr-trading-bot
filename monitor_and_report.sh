#!/bin/bash
# Monitor IBKR order and report to Telegram group

ORDER_ID=$(head -1 pending_order.txt 2>/dev/null || echo "4")
GROUP_CHAT="-1003583837083"
TOPIC_ID="1"

echo "Checking order #$ORDER_ID..."

# Get order status from IBKR
RESULT=$(python3 << PYEOF
from ib_insync import IB
import sys

try:
    ib = IB()
    ib.connect('127.0.0.1', 4002, clientId=106, timeout=10)
    
    # Get all trades
    trades = ib.trades()
    
    # Find our order
    for trade in trades:
        if trade.order.orderId == int('$ORDER_ID'):
            status = trade.orderStatus.status
            filled = trade.orderStatus.filled
            avg_price = trade.orderStatus.avgFillPrice
            
            if status == 'Filled':
                print(f"FILLED|{filled}|{avg_price:.2f}")
            else:
                print(f"{status}|{filled}|0")
            break
    else:
        print("NOT_FOUND|0|0")
    
    ib.disconnect()
except Exception as e:
    print(f"ERROR|0|0")
    sys.exit(1)
PYEOF
)

IFS='|' read -r STATUS FILLED PRICE <<< "$RESULT"

# Build message
if [ "$STATUS" = "FILLED" ]; then
    MESSAGE="🎉 *IBKR Order Executed!*

Order #$ORDER_ID: BUY 1 SPY
Status: ✅ FILLED
Fill Price: \$$PRICE
Time: $(date -u '+%Y-%m-%d %H:%M UTC')

Trade confirmed on paper account DU7659927"

elif [ "$STATUS" = "PreSubmitted" ] || [ "$STATUS" = "Submitted" ]; then
    MESSAGE="⏳ *IBKR Order Waiting*

Order #$ORDER_ID: BUY 1 SPY  
Status: $STATUS (waiting for market open)
Time: $(date -u '+%Y-%m-%d %H:%M UTC')"

elif [ "$STATUS" = "ERROR" ]; then
    MESSAGE="⚠️ *IBKR Connection Issue*

Could not check order #$ORDER_ID
Gateway may be offline
Time: $(date -u '+%Y-%m-%d %H:%M UTC')"

else
    MESSAGE="📊 *IBKR Order Status*

Order #$ORDER_ID: BUY 1 SPY
Status: $STATUS
Time: $(date -u '+%Y-%m-%d %H:%M UTC')"
fi

# Send to group via OpenClaw message tool
echo "$MESSAGE" > /tmp/ibkr_report.txt
echo "Report ready: /tmp/ibkr_report.txt"
echo "Status: $STATUS | Filled: $FILLED | Price: $PRICE"

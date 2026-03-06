#!/usr/bin/env python3
"""
Check IBKR order and send report to Telegram group
"""
import subprocess
import sys

GROUP_ID = "-1003583837083"
TOPIC_ID = 1  # The forum topic ID

def get_order_status():
    """Get order status from IBKR"""
    from ib_insync import IB
    
    try:
        ib = IB()
        ib.connect('127.0.0.1', 4002, clientId=107, timeout=10)
        
        # Read order ID
        with open('pending_order.txt') as f:
            order_id = int(f.readline().strip())
        
        # Get trades
        trades = ib.trades()
        
        for trade in trades:
            if trade.order.orderId == order_id:
                status = trade.orderStatus.status
                filled = trade.orderStatus.filled
                avg_price = trade.orderStatus.avgFillPrice
                
                ib.disconnect()
                
                if status == 'Filled':
                    return f"FILLED|{order_id}|{filled}|{avg_price:.2f}"
                else:
                    return f"{status}|{order_id}|{filled}|{avg_price:.2f}"
        
        ib.disconnect()
        return f"NOT_FOUND|{order_id}|0|0"
        
    except Exception as e:
        return f"ERROR|0|0|0|{str(e)}"

def main():
    result = get_order_status()
    parts = result.split('|')
    status = parts[0]
    order_id = parts[1] if len(parts) > 1 else "?"
    filled = parts[2] if len(parts) > 2 else "0"
    price = parts[3] if len(parts) > 3 else "0"
    
    # Build message based on status
    if status == 'FILLED':
        message = f"""🎉 **IBKR Order Executed!**

Order #{order_id}: BUY 1 SPY
Status: ✅ FILLED
Fill Price: ${price}
Filled: {filled} shares

Trade confirmed on paper account DU7659927"""
    
    elif status in ['PreSubmitted', 'Submitted']:
        message = f"""⏳ **IBKR Order Waiting**

Order #{order_id}: BUY 1 SPY
Status: {status}
Waiting for market open (9:30 AM EST)"""
    
    elif status == 'ERROR':
        error = parts[4] if len(parts) > 4 else "Unknown"
        message = f"""⚠️ **IBKR Check Failed**

Could not verify order #{order_id}
Error: {error}
Gateway may be offline"""
    
    else:
        message = f"""📊 **IBKR Order Status**

Order #{order_id}: BUY 1 SPY
Status: {status}
Filled: {filled} shares"""
    
    print(message)
    print(f"\nSending to group {GROUP_ID}...")
    
    # Send via openclaw message tool would be done by calling it from the agent
    # For now, just save the message
    with open('/tmp/ibkr_report.txt', 'w') as f:
        f.write(message)
    
    print("✅ Report saved to /tmp/ibkr_report.txt")
    print(f"Status: {status}")
    
    return 0 if status == 'FILLED' else 1

if __name__ == '__main__':
    sys.exit(main())

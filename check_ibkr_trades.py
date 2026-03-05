#!/usr/bin/env python3
"""Query IBKR for today's executions and compare with local records."""
import os, sys
from datetime import datetime, timedelta
from ib_insync import IB, util
from dotenv import load_dotenv

load_dotenv('/opt/openclaw/gpu-bot/workspace/.env')

HOST = os.getenv('IBKR_HOST', '127.0.0.1')
PORT = int(os.getenv('IBKR_PORT', '4002'))
CLIENT_ID = int(os.getenv('IBKR_CLIENT_ID', '1'))
ACCOUNT = os.getenv('IBKR_ACCOUNT', 'DU7659927')

def main():
    ib = IB()
    try:
        print(f"📡 Connecting to IBKR Gateway at {HOST}:{PORT}...")
        ib.connect(HOST, PORT, clientId=CLIENT_ID, readonly=True)
        print(f"✅ Connected | Account: {ACCOUNT}\n")
        
        # Get today's executions
        print("📋 Fetching today's executions from IBKR...")
        executions = ib.executions()
        
        if not executions:
            print("⚠️  No executions found in IBKR for today")
            return
        
        print(f"Found {len(executions)} executions:\n")
        print(f"{'Time':<12} {'Symbol':<8} {'Side':<6} {'Qty':<8} {'Price':<10} {'Commission'}")
        print("-" * 70)
        
        for trade in executions:
            exec_obj = trade.execution
            comm = trade.commissionReport.commission if trade.commissionReport else 0.0
            exec_time = exec_obj.time.strftime('%H:%M:%S') if hasattr(exec_obj.time, 'strftime') else str(exec_obj.time)
            
            print(f"{exec_time:<12} {exec_obj.symbol:<8} {exec_obj.side:<6} "
                  f"{exec_obj.shares:<8} ${exec_obj.price:<9.2f} ${comm:.2f}")
        
        # Summary
        print("\n" + "=" * 70)
        total_comm = sum(t.commissionReport.commission if t.commissionReport else 0.0 
                        for t in executions)
        print(f"Total executions: {len(executions)}")
        print(f"Total commission: ${total_comm:.2f}")
        
        # Calculate P&L if possible
        position = {}
        realized_pnl = 0.0
        
        for trade in executions:
            exec_obj = trade.execution
            symbol = exec_obj.symbol
            qty = exec_obj.shares if exec_obj.side == 'BOT' else -exec_obj.shares
            
            if symbol not in position:
                position[symbol] = {'qty': 0, 'avg_cost': 0.0}
            
            if exec_obj.side == 'BOT':
                # Add to position
                old_qty = position[symbol]['qty']
                old_cost = position[symbol]['avg_cost']
                new_qty = old_qty + qty
                position[symbol]['avg_cost'] = ((old_qty * old_cost) + (qty * exec_obj.price)) / new_qty if new_qty != 0 else 0
                position[symbol]['qty'] = new_qty
            else:
                # Close position
                realized_pnl += qty * (exec_obj.price - position[symbol]['avg_cost'])
                position[symbol]['qty'] += qty
        
        print(f"\n💰 Realized P&L (estimated): ${realized_pnl:.2f}")
        print(f"💸 Net after commissions: ${realized_pnl - total_comm:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("\n🔌 Disconnected from IBKR")

if __name__ == '__main__':
    main()

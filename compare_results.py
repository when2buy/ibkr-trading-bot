#!/usr/bin/env python3
"""Compare online (IBKR) vs offline (simulation) trading results."""
import os, sys, csv
from datetime import datetime
from collections import defaultdict

def parse_trades(filepath):
    """Parse trades CSV and return summary."""
    if not os.path.exists(filepath):
        return None
    
    trades = []
    with open(filepath) as f:
        for row in csv.DictReader(f):
            trades.append(row)
    
    if not trades:
        return None
    
    # Calculate P&L
    position = defaultdict(lambda: {'qty': 0, 'avg_cost': 0.0})
    realized_pnl = 0.0
    commissions = 0.0
    
    for t in trades:
        symbol = t['symbol']
        side = t['side']
        qty = int(t['qty'])
        price = float(t['price'])
        comm = float(t['commission'])
        commissions += comm
        
        if side == 'BOT':
            old_qty = position[symbol]['qty']
            old_cost = position[symbol]['avg_cost']
            new_qty = old_qty + qty
            if new_qty != 0:
                position[symbol]['avg_cost'] = ((old_qty * old_cost) + (qty * price)) / new_qty
            position[symbol]['qty'] = new_qty
        else:  # SLD
            if position[symbol]['qty'] > 0:
                realized_pnl += qty * (price - position[symbol]['avg_cost'])
                position[symbol]['qty'] -= qty
    
    return {
        'trades': len(trades),
        'realized_pnl': realized_pnl,
        'commissions': commissions,
        'net_pnl': realized_pnl - commissions,
        'raw': trades
    }

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    trades_file = f"logs/trades_{today}.csv"
    
    print(f"📊 Comparing results for {today}\n")
    print("="*70)
    
    result = parse_trades(trades_file)
    
    if not result:
        print(f"⚠️  No trades found in {trades_file}")
        return
    
    # Determine mode from logs
    online_log = f"logs/online_{today}.log"
    offline_log = f"logs/offline_{today}.log"
    
    mode = "unknown"
    if os.path.exists(online_log):
        mode = "ONLINE (IBKR Gateway)"
    elif os.path.exists(offline_log):
        mode = "OFFLINE (Simulation)"
    
    print(f"Mode: {mode}")
    print(f"Trades: {result['trades']}")
    print(f"Realized P&L: ${result['realized_pnl']:+,.2f}")
    print(f"Commissions: ${result['commissions']:,.2f}")
    print(f"Net P&L: ${result['net_pnl']:+,.2f}")
    print("="*70)
    
    # Show trade details
    print("\nTrade Details:")
    print(f"{'Time':<12} {'Symbol':<8} {'Side':<6} {'Qty':<6} {'Price':<10}")
    print("-"*70)
    for t in result['raw']:
        ts = t['timestamp'].split('T')[1][:8] if 'T' in t['timestamp'] else t['timestamp']
        print(f"{ts:<12} {t['symbol']:<8} {t['side']:<6} {t['qty']:<6} ${float(t['price']):<9.2f}")

if __name__ == '__main__':
    main()

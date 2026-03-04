"""
IBKR Trading Bot - Comprehensive Test Suite
Tests: data download, account info, order placement (paper)
Falls back to yfinance if Gateway not connected.
"""
import os, sys, time, json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/opt/openclaw/gpu-bot/workspace/.env')

HOST      = os.getenv('IB_HOST', '127.0.0.1')
PORT      = int(os.getenv('IB_PORT', 4002))
CLIENT_ID = int(os.getenv('IB_CLIENT_ID', 1))
ACCOUNT   = os.getenv('IB_ACCOUNT_ID', '')

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = {}

# ─────────────────────────────────────────────────────────────
# 1. IBKR CONNECTION
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 1: IBKR Gateway Connection")
print("="*60)

from ib_insync import IB, Stock, Forex, Option, Future, MarketOrder, LimitOrder, util
util.logToConsole('ERROR')  # suppress noise

ib = IB()
connected = False
try:
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=8)
    connected = True
    print(f"{PASS} Connected to IB Gateway at {HOST}:{PORT}")
    results['connection'] = 'PASS'
except Exception as e:
    print(f"{FAIL} Gateway not reachable: {e}")
    print(f"   → Will use yfinance fallback for data tests")
    results['connection'] = f'FAIL: {e}'

# ─────────────────────────────────────────────────────────────
# 2. ACCOUNT INFO
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 2: Account Information")
print("="*60)

if connected:
    try:
        accounts = ib.managedAccounts()
        print(f"{PASS} Managed accounts: {accounts}")

        summary = ib.accountSummary(ACCOUNT)
        key_fields = ['NetLiquidation', 'TotalCashValue', 'BuyingPower',
                      'GrossPositionValue', 'AvailableFunds']
        print(f"\n  Account: {ACCOUNT}")
        for item in summary:
            if item.tag in key_fields:
                print(f"  {item.tag:30s} {float(item.value):>15,.2f} {item.currency}")

        results['account_info'] = 'PASS'
    except Exception as e:
        print(f"{FAIL} Account info failed: {e}")
        results['account_info'] = f'FAIL: {e}'
else:
    print(f"{WARN} Skipped (no connection)")
    results['account_info'] = 'SKIPPED'

# ─────────────────────────────────────────────────────────────
# 3. MARKET DATA - Historical (IBKR or yfinance fallback)
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 3: Historical Market Data Download")
print("="*60)

TEST_SYMBOLS = ['SPY', 'QQQ', 'AAPL']

if connected:
    for sym in TEST_SYMBOLS:
        try:
            contract = Stock(sym, 'SMART', 'USD')
            ib.qualifyContracts(contract)
            bars = ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='5 D',
                barSizeSetting='1 hour',
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            if bars:
                df = util.df(bars)
                print(f"{PASS} {sym}: {len(df)} bars, latest close={df['close'].iloc[-1]:.2f}")
                results[f'hist_data_{sym}'] = 'PASS'
            else:
                print(f"{WARN} {sym}: no bars returned (market closed or data sub needed)")
                results[f'hist_data_{sym}'] = 'NO_DATA'
        except Exception as e:
            print(f"{FAIL} {sym} historical data failed: {e}")
            results[f'hist_data_{sym}'] = f'FAIL: {e}'
else:
    # yfinance fallback
    import yfinance as yf
    for sym in TEST_SYMBOLS:
        try:
            ticker = yf.Ticker(sym)
            df = ticker.history(period='5d', interval='1h')
            if not df.empty:
                print(f"{PASS} {sym} (yfinance): {len(df)} bars, latest={df['Close'].iloc[-1]:.2f}")
                results[f'hist_data_{sym}'] = 'PASS (yfinance)'
            else:
                print(f"{FAIL} {sym}: empty data")
                results[f'hist_data_{sym}'] = 'FAIL: empty'
        except Exception as e:
            print(f"{FAIL} {sym}: {e}")
            results[f'hist_data_{sym}'] = f'FAIL: {e}'

# ─────────────────────────────────────────────────────────────
# 4. LIVE/DELAYED QUOTE
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 4: Real-time / Delayed Quote")
print("="*60)

if connected:
    try:
        ib.reqMarketDataType(3)  # 3 = delayed
        contract = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract, '', False, False)
        ib.sleep(3)  # wait for data

        bid = ticker.bid
        ask = ticker.ask
        last = ticker.last
        print(f"{PASS} SPY quote → bid={bid}, ask={ask}, last={last}")
        ib.cancelMktData(contract)
        results['live_quote'] = 'PASS'
    except Exception as e:
        print(f"{FAIL} Live quote failed: {e}")
        results['live_quote'] = f'FAIL: {e}'
else:
    import yfinance as yf
    try:
        info = yf.Ticker('SPY').fast_info
        print(f"{PASS} SPY (yfinance fast_info): last_price={info.last_price:.2f}")
        results['live_quote'] = 'PASS (yfinance)'
    except Exception as e:
        print(f"{FAIL} {e}")
        results['live_quote'] = f'FAIL: {e}'

# ─────────────────────────────────────────────────────────────
# 5. OPTIONS CHAIN
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 5: Options Chain Data")
print("="*60)

if connected:
    try:
        contract = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(contract)
        chains = ib.reqSecDefOptParams(contract.symbol, '', contract.secType, contract.conId)
        if chains:
            chain = chains[0]
            expirations = sorted(chain.expirations)[:3]
            strikes_sample = sorted(chain.strikes)[len(chain.strikes)//2 - 2 : len(chain.strikes)//2 + 3]
            print(f"{PASS} SPY options chain: {len(chain.expirations)} expirations, {len(chain.strikes)} strikes")
            print(f"   Next expirations: {expirations}")
            print(f"   ATM strikes sample: {strikes_sample}")
            results['options_chain'] = 'PASS'
        else:
            print(f"{WARN} No options chain data returned")
            results['options_chain'] = 'NO_DATA'
    except Exception as e:
        print(f"{FAIL} Options chain failed: {e}")
        results['options_chain'] = f'FAIL: {e}'
else:
    import yfinance as yf
    try:
        spy = yf.Ticker('SPY')
        expirations = spy.options[:3]
        chain = spy.option_chain(expirations[0])
        print(f"{PASS} SPY options (yfinance): {len(chain.calls)} calls, {len(chain.puts)} puts @ {expirations[0]}")
        print(f"   Sample strikes: {sorted(chain.calls['strike'].tolist())[20:25]}")
        results['options_chain'] = 'PASS (yfinance)'
    except Exception as e:
        print(f"{FAIL} {e}")
        results['options_chain'] = f'FAIL: {e}'

# ─────────────────────────────────────────────────────────────
# 6. ORDER PLACEMENT (Paper Trading)
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 6: Order Placement (Paper Trading)")
print("="*60)

if connected:
    # Test 6a: Market Order (small, paper only)
    try:
        contract = Stock('SPY', 'SMART', 'USD')
        ib.qualifyContracts(contract)

        # Limit order far from market (safe for testing, won't fill)
        order = LimitOrder('BUY', 1, 1.00)  # $1 limit - will not fill
        trade = ib.placeOrder(contract, order)
        ib.sleep(2)

        print(f"{PASS} Limit order placed: orderId={trade.order.orderId}, "
              f"status={trade.orderStatus.status}")

        # Cancel it
        ib.cancelOrder(trade.order)
        ib.sleep(1)
        print(f"{PASS} Order cancelled: {trade.orderStatus.status}")
        results['order_place_cancel'] = 'PASS'
    except Exception as e:
        print(f"{FAIL} Order placement failed: {e}")
        results['order_place_cancel'] = f'FAIL: {e}'

    # Test 6b: Check open orders & positions
    try:
        orders = ib.orders()
        positions = ib.positions()
        print(f"{PASS} Open orders: {len(orders)}, Positions: {len(positions)}")
        for pos in positions:
            print(f"   {pos.contract.symbol}: {pos.position} @ avg={pos.avgCost:.2f}")
        results['orders_positions'] = 'PASS'
    except Exception as e:
        print(f"{FAIL} Orders/positions failed: {e}")
        results['orders_positions'] = f'FAIL: {e}'
else:
    print(f"{WARN} Skipped — need live IBKR connection for order tests")
    print(f"   Will run immediately once Gateway is authenticated")
    results['order_place_cancel'] = 'SKIPPED'
    results['orders_positions'] = 'SKIPPED'

# ─────────────────────────────────────────────────────────────
# 7. PORTFOLIO SNAPSHOT
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 7: Portfolio Snapshot")
print("="*60)

if connected:
    try:
        portfolio = ib.portfolio()
        pnl = ib.reqPnL(ACCOUNT)
        ib.sleep(1)
        print(f"{PASS} Portfolio items: {len(portfolio)}")
        if portfolio:
            for item in portfolio[:5]:
                print(f"   {item.contract.symbol}: qty={item.position}, "
                      f"mktVal={item.marketValue:.2f}, unrealPnL={item.unrealizedPNL:.2f}")
        print(f"{PASS} PnL → daily={pnl.dailyPnL}, unrealized={pnl.unrealizedPnL}")
        results['portfolio'] = 'PASS'
    except Exception as e:
        print(f"{FAIL} Portfolio failed: {e}")
        results['portfolio'] = f'FAIL: {e}'
else:
    print(f"{WARN} Skipped (no connection)")
    results['portfolio'] = 'SKIPPED'

# ─────────────────────────────────────────────────────────────
# CLEANUP & SUMMARY
# ─────────────────────────────────────────────────────────────
if connected:
    ib.disconnect()
    print(f"\n{PASS} Disconnected cleanly")

print("\n" + "="*60)
print("  SUMMARY")
print("="*60)
passed = sum(1 for v in results.values() if v.startswith('PASS'))
failed = sum(1 for v in results.values() if v.startswith('FAIL'))
skipped = sum(1 for v in results.values() if v in ('SKIPPED', 'NO_DATA'))

for test, status in results.items():
    icon = PASS if status.startswith('PASS') else (FAIL if status.startswith('FAIL') else WARN)
    print(f"  {icon} {test:35s} {status}")

print(f"\n  Total: {passed} passed, {failed} failed, {skipped} skipped/no-data")
print("="*60)

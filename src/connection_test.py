"""
IBKR Connection Test via ib_insync
Tests connectivity to IB Gateway/TWS
"""
import os
from dotenv import load_dotenv
from ib_insync import IB, util

load_dotenv('/opt/openclaw/gpu-bot/workspace/.env')

HOST = os.getenv('IB_HOST', '127.0.0.1')
PORT = int(os.getenv('IB_PORT', 4002))
CLIENT_ID = int(os.getenv('IB_CLIENT_ID', 1))
ACCOUNT = os.getenv('IB_ACCOUNT_ID')

print(f"Connecting to IB Gateway at {HOST}:{PORT} (client_id={CLIENT_ID})")
print(f"Target account: {ACCOUNT}")

ib = IB()
try:
    ib.connect(HOST, PORT, clientId=CLIENT_ID, timeout=10)
    print("✅ Connected!")
    print(f"Accounts: {ib.managedAccounts()}")
    
    # Get account summary
    summary = ib.accountSummary(ACCOUNT)
    for item in summary[:10]:
        print(f"  {item.tag}: {item.value} {item.currency}")
    
    ib.disconnect()
    print("✅ Disconnected cleanly")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nIB Gateway needs to be running. Options:")
    print("  1. Run IB Gateway natively with IBC (headless)")
    print("  2. Point IB_HOST to a machine where Gateway is already running")

"""Central config — reads from .env"""
import os
from dotenv import load_dotenv

load_dotenv('/opt/openclaw/gpu-bot/workspace/.env')

IB_HOST       = os.getenv('IB_HOST', '127.0.0.1')
IB_PORT       = int(os.getenv('IB_PORT', 4002))
IB_CLIENT_ID  = int(os.getenv('IB_CLIENT_ID', 0))
IB_ACCOUNT    = os.getenv('IB_ACCOUNT_ID', 'DU7659927')

# Risk limits (global)
MAX_TOTAL_EXPOSURE   = float(os.getenv('MAX_TOTAL_EXPOSURE', 500_000))
MAX_PORTFOLIO_DD_PCT = 0.05   # 5% max drawdown before engine pauses

# Logging
LOG_DIR = '/opt/openclaw/gpu-bot/workspace/ibkr-bot/logs'

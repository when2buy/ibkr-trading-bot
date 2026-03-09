"""
IBKR Trading Dashboard
──────────────────────
Flask-based monitoring dashboard for multi-strategy trading engine.
Reads from log files and trade CSVs to display:
  - Current positions & P&L per strategy
  - Trade history
  - Strategy signals
  - Equity curve
  - Auto-refreshes every 30 seconds

Run:  python dashboard/app.py
Port: 8050
"""
import csv
import glob
import os
import re
from datetime import datetime

from flask import Flask, jsonify, render_template_string

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, 'logs')

app = Flask(__name__)


# ── data helpers ──────────────────────────────────────────────────────────────
def _parse_trades() -> list[dict]:
    """Read all trade CSVs from logs/ directory."""
    trades = []
    for path in sorted(glob.glob(os.path.join(LOG_DIR, 'trades_*.csv'))):
        try:
            with open(path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['price'] = float(row.get('price', 0))
                    row['qty']   = int(row.get('qty', 0))
                    row['commission'] = float(row.get('commission', 0))
                    trades.append(row)
        except Exception:
            continue
    return trades


def _calc_strategy_stats(trades: list[dict]) -> dict:
    """Calculate P&L and position per strategy from trade history."""
    strategies = {}
    for t in trades:
        sid = t.get('strategy', 'unknown')
        if sid not in strategies:
            strategies[sid] = {
                'strategy_id': sid,
                'position': 0,
                'total_bought': 0.0,
                'total_sold': 0.0,
                'trade_count': 0,
                'last_trade': '',
                'last_price': 0.0,
                'commissions': 0.0,
            }
        s = strategies[sid]
        s['trade_count'] += 1
        s['last_trade'] = t.get('timestamp', '')
        s['last_price'] = t['price']
        s['commissions'] += t['commission']

        if t.get('side') == 'BOT':
            s['position'] += t['qty']
            s['total_bought'] += t['qty'] * t['price']
        elif t.get('side') == 'SLD':
            s['position'] -= t['qty']
            s['total_sold'] += t['qty'] * t['price']

    for s in strategies.values():
        s['realized_pnl'] = round(s['total_sold'] - s['total_bought'] - s['commissions'], 2)

    return strategies


def _calc_equity_curve(trades: list[dict]) -> list[dict]:
    """Build equity curve from trade sequence."""
    equity = 400_000.0  # 200K per strategy x 2
    curve  = [{'time': '', 'equity': equity}]
    running_cost = {}   # strategy -> cost basis of open position

    for t in trades:
        sid = t.get('strategy', 'unknown')
        if sid not in running_cost:
            running_cost[sid] = 0.0

        if t.get('side') == 'BOT':
            running_cost[sid] += t['qty'] * t['price'] + t['commission']
        elif t.get('side') == 'SLD':
            revenue = t['qty'] * t['price'] - t['commission']
            pnl = revenue - running_cost[sid]
            running_cost[sid] = 0.0
            equity += pnl
            curve.append({
                'time': t.get('timestamp', ''),
                'equity': round(equity, 2),
            })

    return curve


def _parse_signals() -> list[dict]:
    """Extract recent strategy signals from engine log files."""
    signals = []
    signal_patterns = re.compile(
        r'(\d{2}:\d{2}:\d{2}).*strategy\.(spy_\w+)\s+INFO\s+(.*(?:BUY|SELL|STOP|PROFIT|BREAK|BREAKOUT).*)',
        re.IGNORECASE,
    )

    log_files = sorted(glob.glob(os.path.join(LOG_DIR, 'engine_*.log')))
    for path in log_files[-2:]:  # only last 2 log files
        try:
            with open(path) as f:
                for line in f:
                    m = signal_patterns.search(line)
                    if m:
                        signals.append({
                            'time': m.group(1),
                            'strategy': m.group(2),
                            'message': m.group(3).strip(),
                        })
        except Exception:
            continue

    return signals[-50:]  # last 50 signals


# ── API endpoint ──────────────────────────────────────────────────────────────
@app.route('/api/status')
def api_status():
    trades     = _parse_trades()
    strategies = _calc_strategy_stats(trades)
    equity     = _calc_equity_curve(trades)
    signals    = _parse_signals()

    return jsonify({
        'timestamp':  datetime.now().isoformat(),
        'strategies': list(strategies.values()),
        'equity_curve': equity,
        'recent_signals': signals,
        'total_trades': len(trades),
        'recent_trades': trades[-20:],
    })


# ── HTML template ─────────────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<title>IBKR Trading Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0d1117; color: #c9d1d9; }
  .header { background: #161b22; padding: 16px 24px; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
  .header h1 { font-size: 20px; color: #58a6ff; }
  .header .ts { font-size: 13px; color: #8b949e; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 16px 24px; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
  .card h2 { font-size: 15px; color: #58a6ff; margin-bottom: 12px; border-bottom: 1px solid #21262d; padding-bottom: 8px; }
  .card.full { grid-column: 1 / -1; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 6px 8px; color: #8b949e; border-bottom: 1px solid #21262d; font-weight: 500; }
  td { padding: 6px 8px; border-bottom: 1px solid #21262d; }
  .pos  { color: #3fb950; }
  .neg  { color: #f85149; }
  .zero { color: #8b949e; }
  .signal-row { font-size: 12px; padding: 4px 0; border-bottom: 1px solid #21262d; }
  .signal-row .time { color: #8b949e; margin-right: 8px; }
  .signal-row .strat { color: #d2a8ff; margin-right: 8px; font-weight: 500; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .badge-buy  { background: #0d3220; color: #3fb950; }
  .badge-sell { background: #3d1318; color: #f85149; }
  .badge-flat { background: #1c1e23; color: #8b949e; }
  .equity-chart { width: 100%; height: 200px; position: relative; }
  .equity-svg { width: 100%; height: 100%; }
  .refresh-note { text-align: center; padding: 8px; font-size: 11px; color: #484f58; }
</style>
</head>
<body>
<div class="header">
  <h1>IBKR Multi-Strategy Dashboard</h1>
  <div class="ts">Updated: {{ timestamp }} | Auto-refresh: 30s</div>
</div>

<div class="grid">
  <!-- Strategy Cards -->
  {% for s in strategies %}
  <div class="card">
    <h2>{{ s.strategy_id }}</h2>
    <table>
      <tr><td>Position</td><td class="{{ 'pos' if s.position > 0 else ('neg' if s.position < 0 else 'zero') }}">
        {{ s.position }} shares
      </td></tr>
      <tr><td>Realized P&L</td><td class="{{ 'pos' if s.realized_pnl > 0 else ('neg' if s.realized_pnl < 0 else 'zero') }}">
        ${{ "%.2f"|format(s.realized_pnl) }}
      </td></tr>
      <tr><td>Total Trades</td><td>{{ s.trade_count }}</td></tr>
      <tr><td>Last Price</td><td>${{ "%.2f"|format(s.last_price) }}</td></tr>
      <tr><td>Commissions</td><td>${{ "%.2f"|format(s.commissions) }}</td></tr>
      <tr><td>Last Trade</td><td style="font-size:11px">{{ s.last_trade }}</td></tr>
      <tr><td>Status</td><td>
        {% if s.position > 0 %}
          <span class="badge badge-buy">LONG</span>
        {% elif s.position < 0 %}
          <span class="badge badge-sell">SHORT</span>
        {% else %}
          <span class="badge badge-flat">FLAT</span>
        {% endif %}
      </td></tr>
    </table>
  </div>
  {% endfor %}

  {% if not strategies %}
  <div class="card full">
    <h2>No Strategies</h2>
    <p style="color:#8b949e">No trade data found in logs/ directory.</p>
  </div>
  {% endif %}

  <!-- Equity Curve -->
  <div class="card full">
    <h2>Equity Curve</h2>
    {% if equity_curve|length > 1 %}
    <div class="equity-chart">
      <svg class="equity-svg" viewBox="0 0 800 200" preserveAspectRatio="none">
        {% set ns = namespace(min_eq=equity_curve[0].equity, max_eq=equity_curve[0].equity) %}
        {% for pt in equity_curve %}
          {% if pt.equity < ns.min_eq %}{% set ns.min_eq = pt.equity %}{% endif %}
          {% if pt.equity > ns.max_eq %}{% set ns.max_eq = pt.equity %}{% endif %}
        {% endfor %}
        {% set eq_range = ns.max_eq - ns.min_eq if ns.max_eq != ns.min_eq else 1 %}
        <polyline fill="none" stroke="#58a6ff" stroke-width="2"
          points="{% for pt in equity_curve %}{{ (loop.index0 / (equity_curve|length - 1) * 800)|round(1) }},{{ (200 - (pt.equity - ns.min_eq) / eq_range * 180 - 10)|round(1) }} {% endfor %}" />
        <polyline fill="url(#grad)" stroke="none"
          points="0,200 {% for pt in equity_curve %}{{ (loop.index0 / (equity_curve|length - 1) * 800)|round(1) }},{{ (200 - (pt.equity - ns.min_eq) / eq_range * 180 - 10)|round(1) }} {% endfor %} 800,200" />
        <defs><linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#58a6ff" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#58a6ff" stop-opacity="0"/>
        </linearGradient></defs>
      </svg>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:4px">
      <span>Start: ${{ "%.0f"|format(equity_curve[0].equity) }}</span>
      <span>Current: ${{ "%.0f"|format(equity_curve[-1].equity) }}</span>
    </div>
    {% else %}
    <p style="color:#8b949e">Not enough data for equity curve.</p>
    {% endif %}
  </div>

  <!-- Recent Signals -->
  <div class="card">
    <h2>Recent Signals</h2>
    <div style="max-height:300px;overflow-y:auto">
      {% for sig in signals %}
      <div class="signal-row">
        <span class="time">{{ sig.time }}</span>
        <span class="strat">{{ sig.strategy }}</span>
        {{ sig.message }}
      </div>
      {% endfor %}
      {% if not signals %}
      <p style="color:#8b949e;font-size:13px">No signals recorded yet.</p>
      {% endif %}
    </div>
  </div>

  <!-- Recent Trades -->
  <div class="card">
    <h2>Recent Trades</h2>
    <div style="max-height:300px;overflow-y:auto">
      <table>
        <thead><tr><th>Time</th><th>Strategy</th><th>Side</th><th>Qty</th><th>Price</th></tr></thead>
        <tbody>
        {% for t in recent_trades %}
        <tr>
          <td style="font-size:11px">{{ t.timestamp[11:19] if t.timestamp|length > 19 else t.timestamp }}</td>
          <td>{{ t.strategy }}</td>
          <td class="{{ 'pos' if t.side == 'BOT' else 'neg' }}">{{ t.side }}</td>
          <td>{{ t.qty }}</td>
          <td>${{ "%.2f"|format(t.price) }}</td>
        </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="refresh-note">Auto-refreshes every 30 seconds | Port 8050</div>
</body>
</html>"""


# ── routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    trades     = _parse_trades()
    strategies = _calc_strategy_stats(trades)
    equity     = _calc_equity_curve(trades)
    signals    = _parse_signals()

    return render_template_string(
        DASHBOARD_HTML,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        strategies=list(strategies.values()),
        equity_curve=equity,
        signals=signals,
        recent_trades=trades[-20:],
    )


if __name__ == '__main__':
    print(f"Dashboard starting on http://0.0.0.0:8050")
    print(f"Reading logs from: {LOG_DIR}")
    app.run(host='0.0.0.0', port=8050, debug=False)

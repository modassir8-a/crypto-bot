from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt
import json
import os
import random
from datetime import datetime, timedelta
import urllib.parse

DB_FILE = 'trades.json'
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
exchange = ccxt.binance()

# Aapki UPI details
MY_UPI_ID = "8406012453-2@ibl"
PAYEE_NAME = "CryptoBot AI"
PLAN_PRICE_INR = 999

upi_intent_url = f"upi://pay?pa={MY_UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&am={PLAN_PRICE_INR}&cu=INR&tn={urllib.parse.quote('30 Days Pro Plan')}"
qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(upi_intent_url)}"

# Database helpers
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            if "access_keys" not in data:
                data["access_keys"] = {
                    "ADMIN-2026": {"status": "ACTIVE", "expires_on": "Lifetime (Owner)", "plan": "Owner Master Key"},
                    "PRO-VIP": {"status": "ACTIVE", "expires_on": (datetime.now() + timedelta(days=30)).strftime("%d %b %Y"), "plan": "Pro 30 Days"}
                }
            return data
    return {
        "balance": 1000.0,
        "daily_trades_taken": 0,
        "last_date": str(datetime.now().date()),
        "access_keys": {
            "ADMIN-2026": {"status": "ACTIVE", "expires_on": "Lifetime (Owner)", "plan": "Owner Master Key"}
        },
        "trades": [],
        "payments": []
    }

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Bot Execution Logic
def execute_bot_scan():
    db = load_db()
    today_str = str(datetime.now().date())
    if db.get("last_date") != today_str:
        db["last_date"] = today_str
        db["daily_trades_taken"] = 0

    MAX_DAILY = 2
    if db["daily_trades_taken"] >= MAX_DAILY:
        return {"status": "limit", "message": f"⚠️ Aaj ka limit ({MAX_DAILY} trades) poora ho chuka hai! Kal naye trades milenge."}

    trade_taken = False
    executed_coin = ""
    profit_made = 0.0

    for coin in coins:
        ticker = exchange.fetch_ticker(coin)
        current_price = ticker['last']
        high_24h = ticker['high']
        low_24h = ticker['low']
        mid_price = (high_24h + low_24h) / 2

        if current_price > mid_price:
            trade_taken = True
            executed_coin = coin
            db["daily_trades_taken"] += 1
            buy_price = current_price
            target_price = buy_price * 1.015
            profit = 100.0 * 0.015
            profit_made = profit
            db["balance"] += profit

            new_trade = {
                "id": len(db["trades"]) + 1,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "coin": coin,
                "entry_price": round(buy_price, 2),
                "target_price": round(target_price, 2),
                "profit": round(profit, 2),
                "status": "PROFIT"
            }
            db["trades"].append(new_trade)
            save_db(db)
            break

    if trade_taken:
        return {"status": "success", "message": f"🎉 Naya Trade Lag Gaya: {executed_coin}! Profit: +${profit_made:.2f} USDT"}
    else:
        return {"status": "no_setup", "message": "Market scan kiya: Abhi kisi coin mein favorable setup nahi mila. Thodi der baad try karein!"}

# HTML Dashboard Page
def get_html():
    data = load_db()
    balance = data.get("balance", 1000.0)
    daily_count = data.get("daily_trades_taken", 0)
    profit = balance - 1000.0
    profit_pct = (profit / 1000.0) * 100
    profit_color = "#10b981" if profit >= 0 else "#ef4444"
    profit_sign = "+" if profit >= 0 else ""

    trades_html = ""
    for t in reversed(data.get("trades", [])):
        trades_html += f"""
        <div class="trade-card">
            <div>
                <div class="coin-name">🟢 {t['coin']} <span style="font-size: 11px; background: #064e3b; color: #34d399; padding: 2px 8px; border-radius: 6px;">{t.get('status', 'CLOSED')}</span></div>
                <div class="coin-details">Time: {t.get('time', 'N/A')} • Entry: ${t.get('entry_price')} • Target: ${t.get('target_price')}</div>
            </div>
            <div class="trade-pnl">
                <div class="pnl-amount text-green">+${t.get('profit', 0):.2f} USDT</div>
                <div class="coin-details">+1.5% Profit</div>
            </div>
        </div>
        """

    if not trades_html:
        trades_html = "<div class='card' style='text-align: center; color: #94a3b8;'>Abhi tak koi trade record nahi hai.</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CryptoBot AI - Multi-User SaaS Platform</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: #0b0f19; color: #f8fafc; padding: 24px 16px; }}
        .container {{ max-width: 850px; margin: 0 auto; }}
        .sub-banner {{ background: linear-gradient(90deg, #1e1b4b, #31104b); border: 1px solid #6366f1; border-radius: 12px; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
        .btn-sub {{ background: #4f46e5; color: white; border: none; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid #1e293b; margin-bottom: 24px; }}
        .logo {{ font-size: 24px; font-weight: 700; color: #38bdf8; }}
        .badge {{ background: #064e3b; color: #34d399; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; border: 1px solid #059669; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 18px; }}
        .card-label {{ font-size: 13px; color: #94a3b8; margin-bottom: 6px; }}
        .card-value {{ font-size: 24px; font-weight: 700; }}
        .text-green {{ color: #10b981; }}
        .text-blue {{ color: #38bdf8; }}
        
        .action-bar {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 28px; }}
        .btn-scan {{ background: #0284c7; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .btn-scan:hover {{ background: #0369a1; }}
        
        .section-title {{ font-size: 18px; font-weight: 600; margin-bottom: 14px; color: #e2e8f0; }}
        .trade-card {{ background: #131b2e; border: 1px solid #1e293b; border-radius: 12px; padding: 16px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }}
        .coin-name {{ font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
        .coin-details {{ font-size: 13px; color: #94a3b8; margin-top: 4px; }}
        .trade-pnl {{ text-align: right; }}
        .pnl-amount {{ font-size: 17px; font-weight: 700; }}

        /* Modal Styles */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; z-index: 100; padding: 16px; }}
        .modal-content {{ background: #1e293b; border: 1px solid #475569; border-radius: 16px; width: 100%; max-width: 420px; padding: 24px; text-align: center; }}
        .qr-box {{ background: white; padding: 12px; border-radius: 12px; display: inline-block; margin: 12px 0; }}
        .upi-text {{ font-size: 14px; color: #38bdf8; background: #0f172a; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px; font-family: monospace; }}
        .btn-upi-app {{ background: #059669; color: white; text-decoration: none; display: block; padding: 12px; border-radius: 8px; font-weight: 700; margin-bottom: 14px; }}
        .input-box {{ width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; margin-bottom: 10px; text-align: center; font-size: 15px; }}
        .btn-action {{ background: #3b82f6; color: white; border: none; width: 100%; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .btn-close {{ background: transparent; color: #94a3b8; border: none; margin-top: 10px; cursor: pointer; font-size: 13px; }}

        /* Lock Screen Overlay */
        #lockScreen {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0b0f19; z-index: 90; display: flex; justify-content: center; align-items: center; padding: 16px; }}
        .lock-box {{ background: #131b2e; border: 1px solid #334155; border-radius: 16px; padding: 32px 24px; width: 100%; max-width: 400px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
    </style>
</head>
<body>
    <!-- Lock Screen for Unauthenticated Visitors -->
    <div id="lockScreen">
        <div class="lock-box">
            <div style="font-size: 40px; margin-bottom: 12px;">🔒</div>
            <h2 style="font-size: 22px; color: #38bdf8; font-weight: 800;">CryptoBot AI Pro</h2>
            <p style="font-size: 13px; color: #94a3b8; margin-top: 6px;">Please enter your Access Code to unlock dashboard:</p>
            
            <input id="loginCodeInput" type="text" class="input-box" style="margin-top: 16px;" placeholder="Enter Code (e.g. ADMIN-2026)">
            <button class="btn-action" onclick="verifyAccessCode()">🔓 Unlock Dashboard</button>
            
            <div style="margin: 20px 0 12px; border-top: 1px solid #1e293b; padding-top: 16px;">
                <p style="font-size: 12px; color: #94a3b8;">Don't have a code?</p>
                <button class="btn-action" style="background: #10b981; margin-top: 8px;" onclick="openPaymentModalFromLock()">💳 Pay ₹999 & Get Instant Code</button>
            </div>
        </div>
    </div>

    <!-- Main Dashboard (Protected) -->
    <div class="container" id="mainDashboard" style="display:none;">
        <div class="sub-banner">
            <div>
                <strong style="color: #a5b4fc; font-size: 15px;">👑 Pro Plan Active (<span id="userBadge">Member</span>)</strong>
                <p style="font-size: 12px; color: #cbd5e1; margin-top: 3px;">Auto-pilot mode • Max 2 trades/day</p>
            </div>
            <div>
                <button class="btn-sub" onclick="openPaymentModal()">💳 Renew (₹999)</button>
                <button class="btn-sub" style="background: #334155; margin-left: 6px;" onclick="logoutUser()">🚪 Logout</button>
            </div>
        </div>

        <div class="header">
            <div class="logo">⚡ CryptoBot AI Pro</div>
            <div class="badge">● Status: Active Access</div>
        </div>

        <div class="action-bar">
            <div>
                <strong style="font-size: 16px;">Live Market Bot Controller</strong>
                <p style="font-size: 13px; color: #94a3b8; margin-top: 4px;">BTC, ETH, aur SOL ko real-time scan karke trade execute karein:</p>
            </div>
            <button id="scanBtn" class="btn-scan" onclick="triggerScan()">⚡ Scan Market & Run Bot</button>
        </div>

        <div class="stats-grid">
            <div class="card">
                <div class="card-label">Live Saved Balance</div>
                <div class="card-value text-blue">${balance:.2f}</div>
            </div>
            <div class="card">
                <div class="card-label">Total Realized Profit</div>
                <div class="card-value" style="color: {profit_color};">{profit_sign}${profit:.2f} <span style="font-size: 14px;">({profit_sign}{profit_pct:.2f}%)</span></div>
            </div>
            <div class="card">
                <div class="card-label">Today's Trades</div>
                <div class="card-value">{daily_count} / 2</div>
            </div>
            <div class="card">
                <div class="card-label">Pairs Tracked</div>
                <div class="card-value" style="font-size: 16px; line-height: 30px;">BTC • ETH • SOL</div>
            </div>
        </div>

        <div>
            <div class="section-title">Saved Trade History (From Database)</div>
            {trades_html}
        </div>
    </div>

    <!-- Real UPI Payment Modal -->
    <div id="payModal" class="modal">
        <div class="modal-content">
            <h2 style="font-size: 19px;">Pay ₹999 & Get Access Code</h2>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Google Pay • PhonePe • Paytm • Any UPI</p>

            <div class="qr-box">
                <img src="{qr_image_url}" alt="UPI QR Code" style="display:block; width: 180px; height: 180px;">
            </div>

            <div class="upi-text">UPI ID: {MY_UPI_ID}</div>

            <a href="{upi_intent_url}" class="btn-upi-app">📱 Pay ₹999 via Any UPI App</a>

            <div style="border-top: 1px solid #334155; padding-top: 12px; margin-top: 6px;">
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Payment ke baad 12-digit UTR No. enter karein:</p>
                <input id="utrInput" type="text" class="input-box" placeholder="Enter UTR (e.g. 423567890123)" maxlength="16">
                <button class="btn-action" style="background: #10b981;" onclick="submitPayment()">✅ Submit & Generate My Code</button>
            </div>

            <button class="btn-close" onclick="closePaymentModal()">Close Window</button>
        </div>
    </div>

    <script>
        // Check saved access code on load
        window.addEventListener('DOMContentLoaded', () => {{
            const savedKey = localStorage.getItem('cryptobot_access_key');
            if (savedKey) {{
                unlockScreen(savedKey);
            }}
        }});

        function unlockScreen(key) {{
            document.getElementById('lockScreen').style.display = 'none';
            document.getElementById('mainDashboard').style.display = 'block';
            document.getElementById('userBadge').innerText = key;
        }}

        function logoutUser() {{
            localStorage.removeItem('cryptobot_access_key');
            window.location.reload();
        }}

        async function verifyAccessCode() {{
            const code = document.getElementById('loginCodeInput').value.trim();
            if (!code) {{
                alert('Please enter your Access Code!');
                return;
            }}
            const res = await fetch('/verify-code', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ code: code }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_access_key', code);
                unlockScreen(code);
                alert(data.message);
            }} else {{
                alert(data.message);
            }}
        }}

        function openPaymentModalFromLock() {{
            document.getElementById('payModal').style.display = 'flex';
        }}
        function openPaymentModal() {{
            document.getElementById('payModal').style.display = 'flex';
        }}
        function closePaymentModal() {{
            document.getElementById('payModal').style.display = 'none';
        }}
        
        async function submitPayment() {{
            const utr = document.getElementById('utrInput').value.trim();
            const res = await fetch('/subscribe', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ utr: utr }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_access_key', data.access_key);
                alert('🎉 Payment Recorded! Aapka Personal Code: ' + data.access_key + '\\nIse note kar lein!');
                unlockScreen(data.access_key);
                closePaymentModal();
            }} else {{
                alert(data.message);
            }}
        }}

        async function triggerScan() {{
            const btn = document.getElementById('scanBtn');
            btn.innerText = 'Scanning Live Market... ⏳';
            btn.disabled = true;

            try {{
                const res = await fetch('/run-bot', {{ method: 'POST' }});
                const data = await res.json();
                alert(data.message);
                window.location.reload();
            }} catch (err) {{
                alert('Error connecting to bot server!');
                btn.innerText = '⚡ Scan Market & Run Bot';
                btn.disabled = false;
            }}
        }}
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = get_html()
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            payload = json.loads(post_body.decode('utf-8'))
        except Exception:
            payload = {}

        if self.path == '/run-bot':
            result = execute_bot_scan()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif self.path == '/verify-code':
            code = payload.get('code', '').strip().upper()
            db = load_db()
            keys = db.get("access_keys", {})
            if code in keys and keys[code].get("status") == "ACTIVE":
                res = {"status": "success", "message": f"✅ Welcome! Access Code {code} verified."}
            else:
                res = {"status": "error", "message": "❌ Invalid ya Expired Access Code! Sahi code daalein ya plan khareedein."}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/subscribe':
            db = load_db()
            new_key = f"VIP-{random.randint(1000, 9999)}"
            expiry = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
            db.setdefault("access_keys", {})[new_key] = {
                "status": "ACTIVE",
                "plan": "Pro Plan (₹999/mo)",
                "expires_on": expiry,
                "utr": payload.get('utr', 'N/A')
            }
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "access_key": new_key}).encode('utf-8'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"🚀 Server running on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
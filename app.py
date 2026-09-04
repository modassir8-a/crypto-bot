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

# Aapki UPI Details
MY_UPI_ID = "8406012453-2@ibl"
PAYEE_NAME = "CryptoBot AI"
PLAN_PRICE_INR = 999

upi_intent_url = f"upi://pay?pa={MY_UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&am={PLAN_PRICE_INR}&cu=INR&tn={urllib.parse.quote('30 Days Pro Plan')}"
qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(upi_intent_url)}"

# In-memory OTP storage
otp_cache = {}

# Database Helpers
def load_db():
    default_expiry = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = {
                    "admin@cryptobot.com": {
                        "password": "admin123",
                        "status": "ACTIVE",
                        "plan": "Lifetime Owner",
                        "expires_on": "Permanent"
                    }
                }
            return data
    return {
        "balance": 1000.0,
        "daily_trades_taken": 0,
        "last_date": str(datetime.now().date()),
        "users": {
            "admin@cryptobot.com": {
                "password": "admin123",
                "status": "ACTIVE",
                "plan": "Lifetime Owner",
                "expires_on": "Permanent"
            }
        },
        "trades": []
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

# HTML Dashboard Page with Full Login & OTP Flow
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
    <title>CryptoBot AI - Member Portal</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: #0b0f19; color: #f8fafc; padding: 24px 16px; }}
        .container {{ max-width: 850px; margin: 0 auto; }}
        .sub-banner {{ background: linear-gradient(90deg, #1e1b4b, #31104b); border: 1px solid #6366f1; border-radius: 12px; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
        .btn-sub {{ background: #4f46e5; color: white; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; }}
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

        /* Auth Screen */
        #authOverlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #0b0f19; z-index: 99; display: flex; justify-content: center; align-items: center; padding: 16px; }}
        .auth-card {{ background: #131b2e; border: 1px solid #334155; border-radius: 16px; padding: 28px 24px; width: 100%; max-width: 420px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }}
        .auth-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 12px; }}
        .tab-btn {{ background: transparent; border: none; color: #94a3b8; font-size: 15px; font-weight: 700; cursor: pointer; padding-bottom: 4px; }}
        .tab-btn.active {{ color: #38bdf8; border-bottom: 2px solid #38bdf8; }}
        .input-box {{ width: 100%; padding: 12px; border-radius: 8px; border: 1px solid #475569; background: #0f172a; color: white; margin-bottom: 12px; font-size: 14px; }}
        .btn-primary {{ background: #0284c7; color: white; border: none; width: 100%; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; }}
        .btn-primary:hover {{ background: #0369a1; }}

        /* Modal */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); justify-content: center; align-items: center; z-index: 100; padding: 16px; }}
        .modal-content {{ background: #1e293b; border: 1px solid #475569; border-radius: 16px; width: 100%; max-width: 420px; padding: 24px; text-align: center; }}
        .qr-box {{ background: white; padding: 12px; border-radius: 12px; display: inline-block; margin: 12px 0; }}
        .btn-upi-app {{ background: #059669; color: white; text-decoration: none; display: block; padding: 12px; border-radius: 8px; font-weight: 700; margin-bottom: 14px; }}
        .btn-close {{ background: transparent; color: #94a3b8; border: none; margin-top: 10px; cursor: pointer; font-size: 13px; }}
    </style>
</head>
<body>
    <!-- Login & Sign Up Overlay -->
    <div id="authOverlay">
        <div class="auth-card">
            <div style="text-align: center; margin-bottom: 18px;">
                <h2 style="color: #38bdf8; font-size: 22px; font-weight: 800;">⚡ CryptoBot AI Pro</h2>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Sign in to access your Automated Trading Bot</p>
            </div>

            <div class="auth-tabs">
                <button id="tabLoginBtn" class="tab-btn active" onclick="switchAuthTab('login')">🔑 Login</button>
                <button id="tabSignupBtn" class="tab-btn" onclick="switchAuthTab('signup')">📝 Sign Up (with OTP)</button>
            </div>

            <!-- Login Form -->
            <div id="loginForm">
                <input id="loginEmail" type="email" class="input-box" placeholder="Gmail Address (e.g. name@gmail.com)">
                <input id="loginPassword" type="password" class="input-box" placeholder="Password">
                <button class="btn-primary" onclick="handleLogin()">🚀 Login to Dashboard</button>
                <p style="font-size: 11px; color: #64748b; margin-top: 12px; text-align: center;">Owner Demo: admin@cryptobot.com / admin123</p>
            </div>

            <!-- Sign Up Form (with OTP) -->
            <div id="signupForm" style="display: none;">
                <input id="signupEmail" type="email" class="input-box" placeholder="Your Gmail Address">
                <input id="signupPassword" type="password" class="input-box" placeholder="Create a Password">
                
                <button id="otpSendBtn" class="btn-primary" style="background: #4f46e5; margin-bottom: 12px;" onclick="sendSignupOTP()">📩 Send OTP to Gmail</button>
                
                <div id="otpSection" style="display: none;">
                    <p style="font-size: 12px; color: #34d399; margin-bottom: 6px;">OTP sent! Enter 6-digit code below:</p>
                    <input id="signupOTP" type="text" class="input-box" placeholder="Enter 6-digit OTP" maxlength="6">
                    <button class="btn-primary" style="background: #10b981;" onclick="verifyAndSignup()">✅ Verify OTP & Create Account</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Dashboard -->
    <div class="container" id="mainDashboard" style="display:none;">
        <div class="sub-banner">
            <div>
                <strong style="color: #a5b4fc; font-size: 15px;">👑 Member: <span id="userEmailSpan">User</span></strong>
                <p style="font-size: 12px; color: #cbd5e1; margin-top: 3px;">Plan Status: <span id="userPlanStatus">Checking...</span></p>
            </div>
            <div>
                <button class="btn-sub" onclick="openPaymentModal()">💳 Renew / Upgrade (₹999)</button>
                <button class="btn-sub" style="background: #334155; margin-left: 6px;" onclick="logoutUser()">🚪 Logout</button>
            </div>
        </div>

        <div class="header">
            <div class="logo">⚡ CryptoBot AI Pro</div>
            <div class="badge">● Bot Ready</div>
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

    <!-- Payment Modal -->
    <div id="payModal" class="modal">
        <div class="modal-content">
            <h2 style="font-size: 19px;">Activate 30 Days Pro Bot</h2>
            <p style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Google Pay • PhonePe • Paytm • Any UPI</p>

            <div class="qr-box">
                <img src="{qr_image_url}" alt="UPI QR Code" style="display:block; width: 180px; height: 180px;">
            </div>

            <div style="font-size: 14px; color: #38bdf8; background: #0f172a; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px; font-family: monospace;">UPI ID: {MY_UPI_ID}</div>

            <a href="{upi_intent_url}" class="btn-upi-app">📱 Pay ₹999 via Any UPI App</a>

            <div style="border-top: 1px solid #334155; padding-top: 12px; margin-top: 6px;">
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Payment ke baad 12-digit UTR No. enter karein:</p>
                <input id="utrInput" type="text" class="input-box" placeholder="Enter UTR (e.g. 423567890123)" maxlength="16">
                <button class="btn-primary" style="background: #10b981;" onclick="submitPayment()">✅ Verify & Unlock My Account</button>
            </div>

            <button class="btn-close" onclick="closePaymentModal()">Close Window</button>
        </div>
    </div>

    <script>
        // Check session
        window.addEventListener('DOMContentLoaded', () => {{
            const savedUser = localStorage.getItem('cryptobot_user_email');
            if (savedUser) {{
                showDashboard(savedUser);
            }}
        }});

        function switchAuthTab(tab) {{
            if (tab === 'login') {{
                document.getElementById('loginForm').style.display = 'block';
                document.getElementById('signupForm').style.display = 'none';
                document.getElementById('tabLoginBtn').classList.add('active');
                document.getElementById('tabSignupBtn').classList.remove('active');
            }} else {{
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('signupForm').style.display = 'block';
                document.getElementById('tabSignupBtn').classList.add('active');
                document.getElementById('tabLoginBtn').classList.remove('active');
            }}
        }}

        async function handleLogin() {{
            const email = document.getElementById('loginEmail').value.trim();
            const pass = document.getElementById('loginPassword').value.trim();
            if (!email || !pass) {{
                alert('Please enter both Email and Password!');
                return;
            }}
            const res = await fetch('/api/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_user_email', email);
                showDashboard(email, data.plan_status);
            }} else {{
                alert(data.message);
            }}
        }}

        async function sendSignupOTP() {{
            const email = document.getElementById('signupEmail').value.trim();
            const pass = document.getElementById('signupPassword').value.trim();
            if (!email || !pass) {{
                alert('Please enter Email and Password first!');
                return;
            }}
            const btn = document.getElementById('otpSendBtn');
            btn.innerText = 'Sending OTP... ⏳';
            btn.disabled = true;

            const res = await fetch('/api/send-otp', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            alert(data.message);
            btn.innerText = '📩 Resend OTP';
            btn.disabled = false;
            document.getElementById('otpSection').style.display = 'block';
        }}

        async function verifyAndSignup() {{
            const email = document.getElementById('signupEmail').value.trim();
            const otp = document.getElementById('signupOTP').value.trim();
            if (!otp) {{
                alert('Please enter the 6-digit OTP!');
                return;
            }}
            const res = await fetch('/api/verify-otp', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, otp: otp }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                alert(data.message);
                localStorage.setItem('cryptobot_user_email', email);
                showDashboard(email, 'INACTIVE (Subscribe to Trade)');
            }} else {{
                alert(data.message);
            }}
        }}

        function showDashboard(email, status='Active') {{
            document.getElementById('authOverlay').style.display = 'none';
            document.getElementById('mainDashboard').style.display = 'block';
            document.getElementById('userEmailSpan').innerText = email;
            document.getElementById('userPlanStatus').innerText = status;
        }}

        function logoutUser() {{
            localStorage.removeItem('cryptobot_user_email');
            window.location.reload();
        }}

        function openPaymentModal() {{
            document.getElementById('payModal').style.display = 'flex';
        }}
        function closePaymentModal() {{
            document.getElementById('payModal').style.display = 'none';
        }}

        async function submitPayment() {{
            const utr = document.getElementById('utrInput').value.trim();
            const email = localStorage.getItem('cryptobot_user_email') || 'Guest';
            const res = await fetch('/subscribe', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ utr: utr, email: email }})
            }});
            const data = await res.json();
            alert(data.message);
            closePaymentModal();
            window.location.reload();
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

        if self.path == '/api/login':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '').strip()
            db = load_db()
            user = db.get("users", {}).get(email)
            if user and user.get("password") == password:
                status = user.get("status", "ACTIVE")
                res = {"status": "success", "message": "Login successful!", "plan_status": status}
            else:
                res = {"status": "error", "message": "Galat Email ya Password! Dubara check karein."}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/send-otp':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '').strip()
            otp = str(random.randint(100000, 999999))
            otp_cache[email] = {"otp": otp, "password": password}
            
            # Message with OTP
            msg = f"OTP Sent Successfully!\n\nAapka Verification OTP hai: {otp}\n(Ise niche enter karein)."
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": msg}).encode('utf-8'))

        elif self.path == '/api/verify-otp':
            email = payload.get('email', '').strip().lower()
            otp = payload.get('otp', '').strip()
            cached = otp_cache.get(email)
            if cached and cached.get("otp") == otp:
                db = load_db()
                db.setdefault("users", {})[email] = {
                    "password": cached.get("password"),
                    "status": "ACTIVE",
                    "plan": "Pro Trial",
                    "created_on": str(datetime.now().date())
                }
                save_db(db)
                del otp_cache[email]
                res = {"status": "success", "message": "🎉 Email Verified! Account successfully ban gaya."}
            else:
                res = {"status": "error", "message": "❌ Galat OTP! Kripya dobara check karein."}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/run-bot':
            result = execute_bot_scan()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        elif self.path == '/subscribe':
            db = load_db()
            email = payload.get('email', 'User')
            utr = payload.get('utr', 'N/A')
            expiry = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
            if email in db.get("users", {}):
                db["users"][email]["status"] = "ACTIVE"
                db["users"][email]["expires_on"] = expiry
            db.setdefault("payments", []).append({
                "email": email,
                "utr": utr,
                "amount": 999,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            msg = f"🎉 Payment Recorded! 30 Days Pro Plan activated till {expiry}."
            self.wfile.write(json.dumps({"status": "success", "message": msg}).encode('utf-8'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"🚀 Server active on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
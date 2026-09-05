from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt
import json
import os
import threading
import time
from datetime import datetime, timedelta
import urllib.parse

DB_FILE = 'trades.json'
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
exchange = ccxt.binance()

# Aapki UPI Details
MY_UPI_ID = "8406012453-2@ibl"
PAYEE_NAME = "trade.ai"
PLAN_PRICE_INR = 999

upi_intent_url = f"upi://pay?pa={MY_UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&am={PLAN_PRICE_INR}&cu=INR&tn={urllib.parse.quote('trade.ai Pro Plan')}"
qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(upi_intent_url)}"

autopilot_state = {
    "enabled": True,
    "last_scan_time": "Active",
    "last_result": "Scanning loop online"
}

# Database Helpers
def load_db():
    default_expiry = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
    real_initial_activity = [
        {"date": "04 Sep 2026", "time": "09:00 pm", "type": "Initial Bot Investment", "amount": 1000.0, "status": "Completed"}
    ]
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            # Remove fake sample data if present
            if "wallet_activity" in data:
                data["wallet_activity"] = [
                    w for w in data["wallet_activity"] 
                    if abs(w.get("amount", 0)) not in [2600.0, 600.0, 200.0]
                ]
                if not data["wallet_activity"]:
                    data["wallet_activity"] = real_initial_activity
            else:
                data["wallet_activity"] = real_initial_activity
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
                "expires_on": "Permanent",
                "profile": {
                    "name": "Modassir",
                    "phone": "+91 8406012453",
                    "country": "India 🇮🇳",
                    "risk": "Moderate (1.5%)",
                    "avatar": ""
                }
            }
        },
        "trades": [],
        "wallet_activity": real_initial_activity,
        "payments": []
    }

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Core Bot Execution Logic
def execute_bot_scan(source="Manual"):
    db = load_db()
    today_str = str(datetime.now().date())
    if db.get("last_date") != today_str:
        db["last_date"] = today_str
        db["daily_trades_taken"] = 0

    MAX_DAILY = 2
    if db["daily_trades_taken"] >= MAX_DAILY:
        msg = f"⚠️ Aaj ka daily limit ({MAX_DAILY} trades) poora ho chuka hai! Kal naye trades milenge."
        autopilot_state["last_result"] = f"Limit Reached ({MAX_DAILY}/2)"
        autopilot_state["last_scan_time"] = datetime.now().strftime("%H:%M:%S")
        return {"status": "limit", "message": msg}

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

            clean_coin_name = coin.replace('/', '-')
            new_trade = {
                "id": len(db["trades"]) + 1,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "coin": clean_coin_name,
                "entry_price": round(buy_price, 2),
                "target_price": round(target_price, 2),
                "profit": round(profit, 2),
                "status": "PROFIT"
            }
            db["trades"].append(new_trade)
            save_db(db)
            break

    autopilot_state["last_scan_time"] = datetime.now().strftime("%H:%M:%S")

    if trade_taken:
        msg = f"🎉 Naya Trade Lag Gaya ({source}): {executed_coin}! Profit: +${profit_made:.2f} USDT"
        autopilot_state["last_result"] = f"Trade Taken: {executed_coin} (+${profit_made:.2f})"
        return {"status": "success", "message": msg}
    else:
        msg = "Market scan kiya: Abhi kisi coin mein favorable setup nahi mila. Thodi der baad try karein!"
        autopilot_state["last_result"] = "Market scanned: No setup yet"
        return {"status": "no_setup", "message": msg}

def background_autopilot_worker():
    time.sleep(10)
    while True:
        try:
            if autopilot_state.get("enabled", True):
                execute_bot_scan(source="Auto-Pilot")
        except Exception as e:
            print("Auto-pilot scan error:", str(e))
        time.sleep(900)

threading.Thread(target=background_autopilot_worker, daemon=True).start()

# HTML Dashboard Page
def get_html():
    data = load_db()
    balance = data.get("balance", 1000.0)
    profit = balance - 1000.0
    profit_sign = "+" if profit >= 0 else ""

    # Realized Trades HTML
    trades_html = ""
    for t in reversed(data.get("trades", [])):
        c = t.get('coin', '').replace('/', '-')
        trades_html += f"""
        <div class="trade-row" data-coin="{c}">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="coin-badge">{c}</span>
                <div>
                    <strong style="color: #f8fafc; font-size: 14px;">Entry: ${t.get('entry_price')}</strong>
                    <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Target: ${t.get('target_price')} • {t.get('time', '')}</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="color: #38bdf8; font-size: 15px; font-weight: 700;">+{t.get('profit', 0):.2f} USDT</div>
                <div style="color: #34d399; font-size: 11px; font-weight: 600;">PROFIT (+1.5%)</div>
            </div>
        </div>
        """

    if not trades_html:
        trades_html = "<div style='text-align: center; color: #64748b; padding: 24px;'>No realized trade history yet.</div>"

    # Wallet Activity (Read-Only History) HTML
    wallet_html = ""
    total_invested = 0.0
    total_withdrawn = 0.0
    for w in data.get("wallet_activity", []):
        amt = w.get("amount", 0.0)
        if amt >= 0:
            total_invested += amt
        else:
            total_withdrawn += abs(amt)

        amt_str = f"+${amt:.2f}" if amt >= 0 else f"-${abs(amt):.2f}"
        amt_color = "#34d399" if amt >= 0 else "#ef4444"
        type_color = "#38bdf8" if amt >= 0 else "#f87171"
        wallet_html += f"""
        <div class="wallet-card">
            <div>
                <div style="font-size: 13px; color: #f8fafc; font-weight: 600;">{w.get('date', '')}</div>
                <div style="font-size: 11px; color: #71717a; margin-top: 2px;">{w.get('time', '')}</div>
                <div style="font-size: 13px; color: {type_color}; margin-top: 6px; font-weight: 600;">{w.get('type', '')}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 16px; font-weight: 800; color: {amt_color};">{amt_str}</div>
                <span class="status-badge">{w.get('status', 'Completed')}</span>
            </div>
        </div>
        """

    if not wallet_html:
        wallet_html = "<div style='text-align: center; color: #64748b; padding: 24px;'>No transaction history found.</div>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>trade.ai - Terminal</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        body {{ background: #060b14; color: #f8fafc; padding: 18px 12px; min-height: 100vh; }}
        .container {{ max-width: 680px; margin: 0 auto; }}

        /* Top Bar */
        .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .pill-home {{ background: #0c1527; border: 1px solid #1e293b; color: #38bdf8; border-radius: 20px; padding: 6px 16px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; cursor: pointer; text-decoration: none; }}
        .live-pill {{ background: #0b1a2f; border: 1px solid #133256; border-radius: 20px; padding: 6px 14px; font-size: 12px; display: flex; align-items: center; gap: 8px; color: #38bdf8; font-weight: 700; }}
        .live-tag {{ background: #0284c7; color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 800; }}
        .green-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block; box-shadow: 0 0 8px #10b981; }}
        .avatar-btn {{ width: 36px; height: 36px; border-radius: 50%; background: #38bdf8; color: #060b14; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 14px; cursor: pointer; border: none; }}

        /* Navbar */
        .nav-bar {{ background: #0c1527; border: 1px solid #16233b; border-radius: 28px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; overflow-x: auto; margin-bottom: 20px; gap: 6px; }}
        .nav-item {{ color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 20px; white-space: nowrap; cursor: pointer; border: none; background: transparent; }}
        .nav-item.active {{ background: #0284c7; color: #ffffff; font-weight: 700; }}

        .btn-growth {{ background: #0284c7; color: #ffffff; border: none; border-radius: 20px; padding: 10px 20px; font-size: 13px; font-weight: 700; cursor: pointer; margin-bottom: 18px; display: inline-block; }}
        .btn-growth:hover {{ background: #0369a1; }}

        /* Open Position Card */
        .card-position {{ background: #0c1527; border: 1px solid #16233b; border-radius: 24px; padding: 26px 24px; position: relative; overflow: hidden; margin-bottom: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .card-glow {{ position: absolute; top: -30px; right: -30px; width: 200px; height: 200px; background: radial-gradient(circle, rgba(56,189,248,0.18) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; pointer-events: none; }}
        .card-title {{ font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }}
        
        .portfolio-label {{ font-size: 11px; font-weight: 700; letter-spacing: 0.8px; color: #64748b; margin-bottom: 12px; display: flex; align-items: center; gap: 6px; font-style: italic; }}
        .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; border-bottom: 1px solid #16233b; padding-bottom: 20px; margin-bottom: 24px; }}
        .stat-col-title {{ font-size: 10px; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
        .stat-col-val {{ font-size: 13px; font-weight: 700; color: #ffffff; }}
        .stat-col-val.blue {{ color: #38bdf8; }}
        .no-position {{ text-align: center; color: #64748b; font-size: 15px; font-weight: 500; padding: 14px 0 6px; }}

        /* Realized Trade History */
        .history-title {{ text-align: center; font-size: 20px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }}
        .pill-btn-wide {{ background: #0c1527; border: 1px solid #16233b; border-radius: 12px; padding: 12px; text-align: center; color: #cbd5e1; font-size: 13px; font-weight: 600; margin-bottom: 10px; cursor: pointer; display: block; width: 100%; }}
        .coin-filter-row {{ display: flex; gap: 8px; margin: 18px 0 14px; overflow-x: auto; }}
        .coin-filter {{ background: #0c1527; border: 1px solid #16233b; border-radius: 10px; padding: 8px 16px; color: #94a3b8; font-size: 12px; font-weight: 700; cursor: pointer; border: none; }}
        .coin-filter.active {{ background: #0284c7; color: #ffffff; }}
        .trade-row {{ background: #0c1527; border: 1px solid #16233b; border-radius: 14px; padding: 14px 18px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
        .coin-badge {{ background: #0b1a2f; color: #38bdf8; border: 1px solid #133256; padding: 4px 10px; border-radius: 8px; font-size: 12px; font-weight: 800; }}

        /* Wallet Activity (Overview View) */
        .wallet-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 16px; padding: 18px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }}
        .status-badge {{ background: #064e3b; color: #34d399; border: 1px solid #059669; padding: 4px 12px; border-radius: 16px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 6px; }}

        /* Overview Summary Box */
        .overview-summary {{ background: #0c1527; border: 1px solid #16233b; border-radius: 18px; padding: 18px; margin-bottom: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; text-align: center; }}
        .summary-label {{ font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; }}
        .summary-val {{ font-size: 18px; font-weight: 800; margin-top: 4px; }}

        /* Modal Styles */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(6,11,20,0.92); justify-content: center; align-items: center; z-index: 100; padding: 16px; }}
        .modal-content {{ background: #0c1527; border: 1px solid #1e293b; border-radius: 20px; width: 100%; max-width: 420px; padding: 24px; text-align: center; }}
        .input-box {{ width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #1e293b; background: #060b14; color: white; margin-bottom: 10px; font-size: 14px; }}
        .btn-action {{ background: #0284c7; color: #ffffff; border: none; width: 100%; padding: 12px; border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer; }}
        .btn-close {{ background: transparent; color: #64748b; border: none; margin-top: 10px; cursor: pointer; font-size: 13px; }}

        /* Auth Screen */
        #authOverlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #060b14; z-index: 99; display: flex; justify-content: center; align-items: center; padding: 16px; }}
        .auth-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 28px 24px; width: 100%; max-width: 380px; text-align: center; }}
    </style>
</head>
<body>
    <!-- Auth Screen -->
    <div id="authOverlay">
        <div class="auth-card">
            <h2 style="color: #38bdf8; font-size: 26px; font-weight: 800; margin-bottom: 6px;">trade.ai</h2>
            <p style="font-size: 12px; color: #94a3b8; margin-bottom: 20px;">Automated Crypto Trading Intelligence</p>

            <div style="display: flex; gap: 8px; margin-bottom: 16px;">
                <button id="tabLogin" class="coin-filter active" style="flex:1;" onclick="switchAuthTab('login')">Login</button>
                <button id="tabSignup" class="coin-filter" style="flex:1;" onclick="switchAuthTab('signup')">Sign Up</button>
            </div>

            <div id="loginForm">
                <input id="loginEmail" type="email" class="input-box" placeholder="Gmail Address">
                <input id="loginPassword" type="password" class="input-box" placeholder="Password">
                <button class="btn-action" onclick="handleLogin()">Login to Terminal</button>
                <p style="font-size: 11px; color: #64748b; margin-top: 12px;">Admin: admin@cryptobot.com / admin123</p>
            </div>

            <div id="signupForm" style="display: none;">
                <input id="signupEmail" type="email" class="input-box" placeholder="Enter Gmail Address">
                <input id="signupPassword" type="password" class="input-box" placeholder="Create Password">
                <button class="btn-action" style="background: #10b981;" onclick="handleDirectSignup()">Create Account</button>
            </div>
        </div>
    </div>

    <!-- Main Platform -->
    <div class="container" id="mainDashboard" style="display:none;">
        <!-- Top Bar -->
        <div class="top-bar">
            <button class="pill-home" onclick="showTab('tradeLogs')">⚡ trade.ai</button>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="live-pill">
                    <span class="live-tag">LIVE</span>
                    <span>{balance:.2f} USDT</span>
                    <span class="green-dot"></span>
                </div>
                <button class="avatar-btn" id="avatarBtn" onclick="openProfileModal()">M</button>
            </div>
        </div>

        <!-- Navigation Bar -->
        <div class="nav-bar">
            <button class="nav-item" onclick="showTab('tradeLogs')">Home</button>
            <button class="nav-item" onclick="showTab('tradeLogs')">Strategies</button>
            <button class="nav-item" onclick="openPaymentModal()">Plans</button>
            <button id="navTradeLogs" class="nav-item active" onclick="showTab('tradeLogs')">Trade Logs</button>
            <button class="nav-item" onclick="showTab('overview')">BOT Wallet</button>
            <button id="navOverview" class="nav-item" onclick="showTab('overview')">Overview</button>
            <button class="nav-item" onclick="logoutUser()">Logout</button>
        </div>

        <!-- TAB 1: Trade Logs View (Default) -->
        <div id="viewTradeLogs">
            <button class="btn-growth" onclick="triggerScan()">View Balance Growth & Run Scan</button>

            <div class="card-position">
                <div class="card-glow"></div>
                <div class="card-title">Open Position</div>
                <div class="portfolio-label">PORTFOLIO OVERVIEW 👁</div>

                <div class="stats-row">
                    <div>
                        <div class="stat-col-title">PRINCIPAL ▾</div>
                        <div class="stat-col-val">1000.00 <span style="font-size: 10px; color:#64748b;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">E. PNL ▾</div>
                        <div class="stat-col-val blue">{profit_sign}{profit:.2f}</div>
                    </div>
                    <div>
                        <div class="stat-col-title">PNL ▾</div>
                        <div class="stat-col-val blue">{profit_sign}{profit:.2f} <span style="font-size: 10px;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">CURRENT</div>
                        <div class="stat-col-val">{balance:.2f} <span style="font-size: 10px; color:#64748b;">USDT</span></div>
                    </div>
                </div>

                <div class="no-position">No open positions found. (2/2 Daily Limit Completed)</div>
            </div>

            <div>
                <div class="history-title">Realized Trade History</div>
                <button class="pill-btn-wide">Compare with BTC & ETH</button>
                <button class="pill-btn-wide" onclick="alert('Downloading Trade PDF Report...')">Download Trade PDF</button>

                <div class="coin-filter-row">
                    <button class="coin-filter active" onclick="filterCoin('ALL', this)">ALL</button>
                    <button class="coin-filter" onclick="filterCoin('ETH-USDT', this)">ETH-USDT</button>
                    <button class="coin-filter" onclick="filterCoin('BTC-USDT', this)">BTC-USDT</button>
                    <button class="coin-filter" onclick="filterCoin('SOL-USDT', this)">SOL-USDT</button>
                </div>

                <div id="tradesListContainer">
                    {trades_html}
                </div>
            </div>
        </div>

        <!-- TAB 2: Overview / Bot Wallet Activity (Pure Read-Only History) -->
        <div id="viewOverview" style="display: none;">
            <div style="margin-bottom: 20px;">
                <h2 style="font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Bot Wallet Activity</h2>
                <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
                    Track all automated trading transactions, earnings, and fund movements generated by your active bot strategies.
                </p>
            </div>

            <!-- Summary of Real Investment & Withdrawal -->
            <div class="overview-summary">
                <div>
                    <div class="summary-label">Total Bot Investment</div>
                    <div class="summary-val" style="color: #34d399;">${total_invested:.2f} USDT</div>
                </div>
                <div>
                    <div class="summary-label">Total Withdrawal</div>
                    <div class="summary-val" style="color: #f87171;">-${total_withdrawn:.2f} USDT</div>
                </div>
            </div>

            <!-- Transaction History List -->
            <div id="walletActivityList">
                {wallet_html}
            </div>
        </div>
    </div>

    <!-- Profile Modal -->
    <div id="profileModal" class="modal">
        <div class="modal-content">
            <h3 style="color: #38bdf8; margin-bottom: 14px;">User Profile & Settings</h3>
            <input id="profileName" type="text" class="input-box" placeholder="Full Name">
            <input id="profilePhone" type="tel" class="input-box" placeholder="Phone Number">
            <button class="btn-action" onclick="saveProfile()">Save Changes</button>
            <button class="btn-close" onclick="closeProfileModal()">Close</button>
        </div>
    </div>

    <!-- Plans & Payment Modal (UPI) -->
    <div id="payModal" class="modal">
        <div class="modal-content">
            <h3 style="color: #38bdf8;">30 Days Pro Trading Plan</h3>
            <p style="font-size: 12px; color: #94a3b8; margin: 6px 0 14px;">Unlimited 24/7 AI Bot Trading</p>
            <div style="background: white; padding: 8px; border-radius: 12px; display: inline-block; margin-bottom: 10px;">
                <img src="{qr_image_url}" alt="UPI QR" style="width: 170px; height: 170px; display: block;">
            </div>
            <div style="color: #38bdf8; font-family: monospace; font-size: 13px; margin-bottom: 12px;">UPI: {MY_UPI_ID}</div>
            <a href="{upi_intent_url}" class="pill-btn-wide" style="background: #0284c7; color: #ffffff; font-weight: 700; text-decoration: none;">📱 Pay ₹999 via Any UPI App</a>
            <input id="utrInput" type="text" class="input-box" placeholder="Enter 12-digit UTR">
            <button class="btn-action" style="background: #10b981;" onclick="submitPayment()">Verify & Activate</button>
            <button class="btn-close" onclick="closePaymentModal()">Close</button>
        </div>
    </div>

    <script>
        window.addEventListener('DOMContentLoaded', () => {{
            const saved = localStorage.getItem('cryptobot_user_email');
            if (saved) {{
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('mainDashboard').style.display = 'block';
                const initial = saved.charAt(0).toUpperCase();
                document.getElementById('avatarBtn').innerText = initial;
            }}
        }});

        function showTab(tab) {{
            if (tab === 'overview') {{
                document.getElementById('viewTradeLogs').style.display = 'none';
                document.getElementById('viewOverview').style.display = 'block';
                document.getElementById('navOverview').classList.add('active');
                document.getElementById('navTradeLogs').classList.remove('active');
            }} else {{
                document.getElementById('viewOverview').style.display = 'none';
                document.getElementById('viewTradeLogs').style.display = 'block';
                document.getElementById('navTradeLogs').classList.add('active');
                document.getElementById('navOverview').classList.remove('active');
            }}
        }}

        function switchAuthTab(tab) {{
            if (tab === 'login') {{
                document.getElementById('loginForm').style.display = 'block';
                document.getElementById('signupForm').style.display = 'none';
                document.getElementById('tabLogin').classList.add('active');
                document.getElementById('tabSignup').classList.remove('active');
            }} else {{
                document.getElementById('loginForm').style.display = 'none';
                document.getElementById('signupForm').style.display = 'block';
                document.getElementById('tabSignup').classList.add('active');
                document.getElementById('tabLogin').classList.remove('active');
            }}
        }}

        async function handleLogin() {{
            const email = document.getElementById('loginEmail').value.trim();
            const pass = document.getElementById('loginPassword').value.trim();
            const res = await fetch('/api/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_user_email', email);
                window.location.reload();
            }} else {{
                alert(data.message);
            }}
        }}

        async function handleDirectSignup() {{
            const email = document.getElementById('signupEmail').value.trim();
            const pass = document.getElementById('signupPassword').value.trim();
            const res = await fetch('/api/signup', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_user_email', email);
                window.location.reload();
            }} else {{
                alert(data.message);
            }}
        }}

        function logoutUser() {{
            localStorage.removeItem('cryptobot_user_email');
            window.location.reload();
        }}

        function openProfileModal() {{ document.getElementById('profileModal').style.display = 'flex'; }}
        function closeProfileModal() {{ document.getElementById('profileModal').style.display = 'none'; }}
        function openPaymentModal() {{ document.getElementById('payModal').style.display = 'flex'; }}
        function closePaymentModal() {{ document.getElementById('payModal').style.display = 'none'; }}

        function filterCoin(coin, btn) {{
            document.querySelectorAll('.coin-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const rows = document.querySelectorAll('.trade-row');
            rows.forEach(r => {{
                if (coin === 'ALL' || r.getAttribute('data-coin').includes(coin.replace('-', ''))) {{
                    r.style.display = 'flex';
                }} else {{
                    r.style.display = 'none';
                }}
            }});
        }}

        async function triggerScan() {{
            const res = await fetch('/run-bot', {{ method: 'POST' }});
            const data = await res.json();
            alert(data.message);
            window.location.reload();
        }}

        async function submitPayment() {{
            const utr = document.getElementById('utrInput').value.trim();
            const email = localStorage.getItem('cryptobot_user_email') || 'User';
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

        elif self.path == '/api/signup':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '').strip()
            db = load_db()
            if email in db.get("users", {}):
                res = {"status": "error", "message": "Yeh Email pehle se registered hai! Kripya Login karein."}
            else:
                db.setdefault("users", {})[email] = {
                    "password": password,
                    "status": "ACTIVE",
                    "plan": "Pro Trial",
                    "created_on": str(datetime.now().date()),
                    "profile": {
                        "name": email.split('@')[0],
                        "phone": "",
                        "country": "India 🇮🇳"
                    }
                }
                save_db(db)
                res = {"status": "success", "message": "Account created successfully!"}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/run-bot':
            result = execute_bot_scan(source="Manual")
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
    print(f"🚀 trade.ai server active on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
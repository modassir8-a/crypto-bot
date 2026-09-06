from http.server import HTTPServer, BaseHTTPRequestHandler
import ccxt
import json
import os
import threading
import time
from datetime import datetime, timedelta
import urllib.parse
import hashlib

DB_FILE = 'trades.json'
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
exchange = ccxt.binance()

# Bank Details
BANK_NAME = "India Post Payments Bank"
ACCOUNT_NUMBER = "021210215499"
IFSC_CODE = "IPOS0000001"

# Subscription Plans ke liye UPI Details
MY_UPI_ID = "8406012453-2@ibl"
PAYEE_NAME = "trade.ai"
PLAN_PRICE_INR = 999
USDT_INR_RATE = 91.50

MIN_WITHDRAW_INR = 1000.0
MAX_WITHDRAW_INR = 10000.0

ADMIN_COMMISSION_PCT = 0.15
USER_SHARE_PCT = 0.85

upi_intent_url = f"upi://pay?pa={MY_UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&am={PLAN_PRICE_INR}&cu=INR&tn={urllib.parse.quote('trade.ai Bot Deposit')}"
qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={urllib.parse.quote(upi_intent_url)}"

PLANS = {
    "PREMIUM": {"name": "PREMIUM PACKAGE", "price": 8000, "days": 365, "badge": "BEST VALUE (1 YEAR)"},
    "STANDARD": {"name": "STANDARD PACKAGE", "price": 999, "days": 30, "badge": "MOST POPULAR"},
    "BASE": {"name": "BASE PACKAGE", "price": 400, "days": 10, "badge": "STARTER TRIAL"}
}

autopilot_state = {
    "enabled": True,
    "last_scan_time": "Active",
    "last_result": "Scanning loop online"
}

def get_user_uid(email):
    h = hashlib.md5(email.lower().strip().encode()).hexdigest()
    num = int(h[:8], 16) % 90000000 + 10000000
    return str(num)

def load_db():
    default_expiry = (datetime.now() + timedelta(days=365)).strftime("%d %b %Y")
    data = {}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {}

    if "balance" not in data:
        data["balance"] = 1000.0
    if "inr_balance" not in data:
        data["inr_balance"] = 0.0
    if "daily_trades_taken" not in data:
        data["daily_trades_taken"] = 0
    if "last_date" not in data:
        data["last_date"] = str(datetime.now().date())
    if "trades" not in data:
        data["trades"] = []
    if "wallet_activity" not in data:
        data["wallet_activity"] = []
    if "payments" not in data:
        data["payments"] = []
    if "users" not in data:
        data["users"] = {}

    # Admin Master Account
    data["users"]["admin@cryptobot.com"] = {
        "password": "admin123",
        "status": "ACTIVE",
        "plan": "PREMIUM",
        "days_left": 365,
        "expires_on": default_expiry,
        "balance": 1000.0,
        "principal": 1000.0,
        "total_profit": 3.00,
        "inr_balance": 0.0,
        "is_admin": True,
        "uid": get_user_uid("admin@cryptobot.com"),
        "profile": {
            "name": "Modassir (Admin)",
            "phone": "+91 8406012453",
            "country": "India 🇮🇳",
            "risk": "Moderate (1.5%)"
        }
    }

    return data

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

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
                "time": datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p"),
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

def get_html():
    total_p = 1.50
    admin_s = 0.225
    user_s = 1.275
    def render_plan_card(plan_id, pdata):
        return f"""
        <div class="card-plan">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="plan-sub-title">{pdata['name']}</div>
                    <div class="plan-price-title">₹{pdata['price']:,} <span class="plan-duration">/ {pdata['days']} days</span></div>
                </div>
                <span class="plan-badge-tag">{pdata['badge']}</span>
            </div>

            <div class="plan-feature-list">
                <div class="plan-feature-item">
                    <span class="feature-check">✔</span>
                    <div>
                        <strong style="color: #ffffff;">Advanced Edge</strong>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">AI-powered insights based on real-time Binance market signals.</div>
                    </div>
                </div>
                <div class="plan-feature-item">
                    <span class="feature-check">✔</span>
                    <div>
                        <strong style="color: #ffffff;">Trade Pro Tools</strong>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Automated 24/7 execution for BTC, ETH, and SOL pairs.</div>
                    </div>
                </div>
                <div class="plan-feature-item">
                    <span class="feature-check">✔</span>
                    <div>
                        <strong style="color: #ffffff;">Subscription Term</strong>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Full access to active bot strategies valid for {pdata['days']} days.</div>
                    </div>
                </div>
                <div class="plan-feature-item">
                    <span class="feature-check">✔</span>
                    <div>
                        <strong style="color: #ffffff;">Portfolio Range</strong>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Optimized for portfolios from $100 to infinity with risk protection.</div>
                    </div>
                </div>
                <div class="plan-feature-item">
                    <span class="feature-check">✔</span>
                    <div>
                        <strong style="color: #ffffff;">Profit Optimization</strong>
                        <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">Automated stop-loss (1%) & target (1.5%) profit locking.</div>
                    </div>
                </div>
            </div>

            <button class="btn-activate-plan" id="planBtn_{plan_id}" onclick="openPlanCheckout('{plan_id}', {pdata['price']}, '{pdata['name']}', {pdata['days']})">
                ACTIVATE PLAN (₹{pdata['price']:,})
            </button>
        </div>
        """

    plans_html = ""
    plans_html += render_plan_card("PREMIUM", PLANS["PREMIUM"])
    plans_html += render_plan_card("STANDARD", PLANS["STANDARD"])
    plans_html += render_plan_card("BASE", PLANS["BASE"])

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

        .top-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }}
        .pill-home {{ background: #0c1527; border: 1px solid #1e293b; color: #38bdf8; border-radius: 20px; padding: 6px 16px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; cursor: pointer; text-decoration: none; }}
        .live-pill {{ background: #0b1a2f; border: 1px solid #133256; border-radius: 20px; padding: 6px 14px; font-size: 12px; display: flex; align-items: center; gap: 8px; color: #38bdf8; font-weight: 700; }}
        .live-tag {{ background: #0284c7; color: white; padding: 2px 6px; border-radius: 6px; font-size: 10px; font-weight: 800; }}
        .green-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block; box-shadow: 0 0 8px #10b981; }}
        .avatar-btn {{ width: 36px; height: 36px; border-radius: 50%; background: #38bdf8; color: #060b14; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 14px; cursor: pointer; border: none; }}

        .nav-bar {{ background: #0c1527; border: 1px solid #16233b; border-radius: 28px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; overflow-x: auto; margin-bottom: 24px; gap: 6px; }}
        .nav-item {{ color: #94a3b8; text-decoration: none; font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: 20px; white-space: nowrap; cursor: pointer; border: none; background: transparent; }}
        .nav-item.active {{ background: #0284c7; color: #ffffff; font-weight: 700; }}
        .nav-item.admin-tab {{ background: #78350f; color: #fde047; border: 1px solid #b45309; }}
        .nav-item.admin-tab.active {{ background: #d97706; color: #000; font-weight: 800; }}

        .card-position {{ background: #0c1527; border: 1px solid #16233b; border-radius: 24px; padding: 26px 24px; position: relative; overflow: hidden; margin-bottom: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .card-glow {{ position: absolute; top: -30px; right: -30px; width: 200px; height: 200px; background: radial-gradient(circle, rgba(56,189,248,0.18) 0%, rgba(0,0,0,0) 70%); border-radius: 50%; pointer-events: none; }}
        .card-title {{ font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }}
        
        .portfolio-label {{ font-size: 11px; font-weight: 700; letter-spacing: 0.8px; color: #64748b; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; font-style: italic; }}
        .eye-toggle-btn {{ cursor: pointer; font-size: 14px; background: #0b1a2f; border: 1px solid #1e293b; padding: 2px 6px; border-radius: 6px; color: #38bdf8; transition: 0.2s; }}
        .eye-toggle-btn:hover {{ background: #0284c7; color: white; }}

        .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; border-bottom: 1px solid #16233b; padding-bottom: 20px; margin-bottom: 24px; }}
        .stat-col-title {{ font-size: 10px; color: #64748b; font-weight: 700; margin-bottom: 4px; }}
        .stat-col-val {{ font-size: 13px; font-weight: 700; color: #ffffff; }}
        .stat-col-val.blue {{ color: #38bdf8; }}
        .no-position {{ text-align: center; color: #64748b; font-size: 15px; font-weight: 500; padding: 14px 0 6px; }}

        .history-title {{ text-align: center; font-size: 20px; font-weight: 800; color: #ffffff; margin-bottom: 16px; }}
        .coin-filter-row {{ display: flex; gap: 8px; margin: 16px 0 16px; overflow-x: auto; }}
        .coin-filter {{ background: #0c1527; border: 1px solid #16233b; border-radius: 10px; padding: 8px 16px; color: #94a3b8; font-size: 12px; font-weight: 700; cursor: pointer; border: none; }}
        .coin-filter.active {{ background: #0284c7; color: #ffffff; }}

        .trade-card-split {{ background: #0c1527; border: 1px solid #16233b; border-radius: 16px; padding: 18px 20px; margin-bottom: 12px; transition: 0.2s; }}
        .btn-view-split {{ background: #bef264; color: #000000; border: none; border-radius: 8px; padding: 6px 18px; font-size: 13px; font-weight: 800; cursor: pointer; transition: 0.2s; }}
        .btn-view-split:hover {{ opacity: 0.9; }}

        .empty-state-box {{ text-align: center; padding: 36px 18px; border: 1px dashed #16233b; border-radius: 16px; margin: 12px 0; background: rgba(12, 21, 39, 0.3); }}
        .empty-icon {{ font-size: 38px; margin-bottom: 10px; opacity: 0.85; }}
        .empty-text {{ color: #94a3b8; font-size: 14px; font-weight: 600; }}

        .card-plan {{ background: #0c1527; border: 1px solid #16233b; border-radius: 24px; padding: 26px 24px; margin-bottom: 24px; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }}
        .plan-sub-title {{ font-size: 11px; font-weight: 800; letter-spacing: 0.8px; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }}
        .plan-price-title {{ font-size: 30px; font-weight: 900; color: #ffffff; }}
        .plan-duration {{ font-size: 15px; color: #94a3b8; font-weight: 500; }}
        .plan-badge-tag {{ background: #064e3b; color: #34d399; border: 1px solid #059669; padding: 4px 12px; border-radius: 14px; font-size: 11px; font-weight: 800; }}
        .plan-feature-list {{ margin: 20px 0 24px; display: flex; flex-direction: column; gap: 14px; }}
        .plan-feature-item {{ display: flex; align-items: flex-start; gap: 12px; font-size: 13px; }}
        .feature-check {{ width: 20px; height: 20px; border-radius: 50%; background: #064e3b; color: #34d399; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800; flex-shrink: 0; margin-top: 2px; }}
        .btn-activate-plan {{ width: 100%; padding: 14px; border-radius: 12px; font-size: 14px; font-weight: 800; border: none; cursor: pointer; background: #0284c7; color: #ffffff; transition: 0.2s; }}
        .btn-activate-plan:hover {{ background: #0369a1; }}
        .btn-activate-plan.active-badge {{ background: #131b2e; color: #34d399; border: 1px solid #059669; cursor: default; }}

        .wallet-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 16px; padding: 18px 20px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }}
        .status-badge {{ padding: 4px 12px; border-radius: 16px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 6px; }}
        .overview-summary {{ background: #0c1527; border: 1px solid #16233b; border-radius: 18px; padding: 18px; margin-bottom: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; text-align: center; }}
        .summary-label {{ font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; }}
        .summary-val {{ font-size: 18px; font-weight: 800; margin-top: 4px; }}

        .wallet-actions-bar {{ display: flex; gap: 10px; margin-bottom: 24px; }}
        .wallet-action-pill {{ flex: 1; text-align: center; background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 10px 14px; color: #94a3b8; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }}
        .wallet-action-pill.active {{ background: #38bdf8; color: #060b14; }}
        
        .notice-box {{ background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 14px; padding: 14px 18px; margin-bottom: 20px; color: #94a3b8; font-size: 12px; line-height: 1.5; text-align: left; }}
        .step-indicator {{ display: flex; align-items: center; gap: 10px; margin-bottom: 18px; font-size: 12px; font-weight: 700; color: #64748b; }}
        .step-circle {{ width: 22px; height: 22px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-size: 11px; }}
        
        .bank-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 24px; margin-bottom: 20px; text-align: left; }}
        .bank-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
        .bank-icon-box {{ background: #0b1a2f; border: 1px solid #1e293b; width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; }}
        .badge-rec {{ background: #064e3b; color: #34d399; border: 1px solid #059669; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800; text-transform: uppercase; margin-left: 8px; }}
        .feature-pills {{ display: flex; gap: 8px; margin: 14px 0 20px; }}
        .feat-tag {{ background: #060b14; border: 1px solid #1e293b; border-radius: 8px; padding: 4px 10px; font-size: 11px; font-weight: 600; color: #94a3b8; }}

        .bank-row {{ border-top: 1px solid #16233b; padding: 14px 0; display: flex; justify-content: space-between; align-items: center; }}
        .bank-row-label {{ font-size: 10px; font-weight: 800; color: #64748b; letter-spacing: 0.8px; text-transform: uppercase; margin-bottom: 4px; }}
        .bank-row-val {{ font-size: 15px; font-weight: 800; color: #ffffff; font-family: monospace; letter-spacing: 0.5px; }}
        .copy-icon-btn {{ cursor: pointer; color: #94a3b8; font-size: 16px; transition: 0.2s; background: transparent; border: none; }}
        .copy-icon-btn:hover {{ color: #38bdf8; }}

        .proof-upload-box {{ border: 2px dashed #1e293b; border-radius: 16px; padding: 28px 16px; text-align: center; cursor: pointer; margin: 14px 0 20px; background: #070d18; transition: 0.2s; }}
        .proof-upload-box:hover {{ border-color: #38bdf8; }}

        .swap-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 24px; padding: 24px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        .swap-box {{ background: #070d18; border: 1px solid #16233b; border-radius: 16px; padding: 18px; margin-bottom: 12px; }}
        .swap-label-row {{ display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 10px; font-weight: 600; }}
        .swap-input-row {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
        .swap-input {{ background: transparent !important; border: none !important; color: #ffffff !important; font-size: 26px; font-weight: 800; width: 60%; outline: none; }}
        .max-pill {{ background: rgba(56,189,248,0.15); border: 1px solid #0284c7; color: #38bdf8; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; }}
        .curr-pill {{ background: #0c1527; border: 1px solid #1e293b; color: #ffffff; padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; }}
        .swap-divider-btn {{ width: 42px; height: 42px; border-radius: 50%; background: #131b2e; border: 1px solid #1e293b; color: #38bdf8; display: flex; justify-content: center; align-items: center; font-size: 18px; margin: -6px auto; cursor: pointer; position: relative; z-index: 2; transition: 0.2s; }}
        .swap-divider-btn:hover {{ background: #0284c7; color: white; transform: rotate(180deg); }}
        .calc-breakdown {{ padding: 16px 4px; border-top: 1px solid #16233b; margin-top: 14px; }}
        .breakdown-row {{ display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 8px; }}

        .admin-req-card {{ background: #0c1527; border: 1px solid #1e293b; border-radius: 16px; padding: 18px 20px; margin-bottom: 14px; text-align: left; }}
        .btn-approve {{ background: #10b981; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 700; cursor: pointer; font-size: 12px; }}
        .btn-reject {{ background: #ef4444; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 700; cursor: pointer; font-size: 12px; margin-left: 8px; }}

        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(6,11,20,0.92); justify-content: center; align-items: center; z-index: 100; padding: 16px; }}
        .modal-content {{ background: #0c1527; border: 1px solid #1e293b; border-radius: 20px; width: 100%; max-width: 420px; padding: 24px; text-align: center; }}
        .input-box {{ width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #1e293b; background: #060b14; color: white; margin-bottom: 12px; font-size: 14px; }}
        .btn-action {{ background: #0284c7; color: #ffffff; border: none; width: 100%; padding: 12px; border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer; }}
        .btn-close {{ background: transparent; color: #64748b; border: none; margin-top: 10px; cursor: pointer; font-size: 13px; }}

        #authOverlay {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #060b14; z-index: 99; display: flex; justify-content: center; align-items: center; padding: 16px; }}
        .auth-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 28px 24px; width: 100%; max-width: 380px; text-align: center; }}

        /* Signing In Spinner (Exact Creddx Style) */
        .signing-in-spinner {{
            width: 58px;
            height: 58px;
            border: 5px solid rgba(52, 211, 153, 0.15);
            border-top-color: #34d399;
            border-radius: 50%;
            animation: spinRing 0.85s linear infinite;
            margin: 0 auto 24px;
            box-shadow: 0 0 20px rgba(52, 211, 153, 0.2);
        }}
        @keyframes spinRing {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <!-- Signing In Fullscreen Loader (Creddx Exact Match) -->
    <div id="signingInOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #060b14; z-index: 1000; flex-direction: column; justify-content: center; align-items: center;">
        <div style="background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; padding: 6px 16px; font-size: 12px; color: #38bdf8; font-weight: 800; display: flex; align-items: center; gap: 8px; margin-bottom: 38px;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #10b981; display: inline-block; box-shadow: 0 0 8px #10b981;"></span>
            TRADE.AI
        </div>

        <div class="signing-in-spinner"></div>

        <h2 style="color: #ffffff; font-size: 22px; font-weight: 800; margin-bottom: 8px; letter-spacing: -0.3px;">Signing you in</h2>
        <p style="color: #94a3b8; font-size: 13px;">Securely connecting your trade.ai account...</p>
    </div>

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
                <div style="position: relative; margin-bottom: 12px;">
                    <input id="loginPassword" type="password" class="input-box" placeholder="Password" style="padding-right: 42px; margin-bottom: 0;">
                    <span onclick="togglePasswordVisibility('loginPassword', this)" style="position: absolute; right: 12px; top: 12px; cursor: pointer; color: #94a3b8; font-size: 16px;">👁</span>
                </div>
                <button class="btn-action" onclick="handleLogin()">Login to Terminal</button>
                <p style="font-size: 11px; color: #64748b; margin-top: 12px;">Admin: admin@cryptobot.com / admin123</p>
            </div>

            <div id="signupForm" style="display: none;">
                <input id="signupEmail" type="email" class="input-box" placeholder="Enter Gmail Address">
                <div style="position: relative; margin-bottom: 12px;">
                    <input id="signupPassword" type="password" class="input-box" placeholder="Create Password" style="padding-right: 42px; margin-bottom: 0;">
                    <span onclick="togglePasswordVisibility('signupPassword', this)" style="position: absolute; right: 12px; top: 12px; cursor: pointer; color: #94a3b8; font-size: 16px;">👁</span>
                </div>
                <button class="btn-action" style="background: #10b981;" onclick="handleDirectSignup()">Create Account</button>
            </div>
        </div>
    </div>

    <div class="container" id="mainDashboard" style="display:none;">
        <div class="top-bar">
            <button class="pill-home" onclick="showTab('tradeLogs')">⚡ trade.ai</button>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div class="live-pill">
                    <span class="live-tag">LIVE</span>
                    <span id="headerBalText">0.00 USDT</span>
                    <span class="green-dot"></span>
                </div>
                <button class="avatar-btn" id="avatarBtn" onclick="openProfileModal()">M</button>
            </div>
        </div>

        <div class="nav-bar">
            <button class="nav-item" onclick="showTab('tradeLogs')">Home</button>
            <button class="nav-item" onclick="showTab('tradeLogs')">Strategies</button>
            <button id="navPlans" class="nav-item" onclick="showTab('plans')">Plans</button>
            <button id="navTradeLogs" class="nav-item active" onclick="showTab('tradeLogs')">Trade Logs</button>
            <button id="navBotWallet" class="nav-item" onclick="showTab('botWallet')">BOT Wallet</button>
            <button id="navOverview" class="nav-item" onclick="showTab('overview')">Overview</button>
            <button id="navAdminPanel" class="nav-item admin-tab" style="display: none;" onclick="showTab('adminPanel')">👑 Admin Panel</button>
            <button class="nav-item" onclick="logoutUser()">Logout</button>
        </div>

        <!-- TAB 1: Trade Logs View -->
        <div id="viewTradeLogs">
            <div class="card-position">
                <div class="card-glow"></div>
                <div class="card-title">Open Position</div>
                <div class="portfolio-label">
                    PORTFOLIO OVERVIEW 
                    <span id="eyeBtn" class="eye-toggle-btn" onclick="toggleEyeVisibility()" title="Toggle hide/show balance">👁</span>
                </div>

                <div class="stats-row">
                    <div>
                        <div class="stat-col-title">PRINCIPAL ▾</div>
                        <div class="stat-col-val" id="dispPrincipal">0.00 <span style="font-size: 10px; color:#64748b;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">E. PNL ▾</div>
                        <div class="stat-col-val blue" id="dispEpnl">+0.00</div>
                    </div>
                    <div>
                        <div class="stat-col-title">PNL ▾</div>
                        <div class="stat-col-val blue" id="dispPnl">+0.00 <span style="font-size: 10px;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">CURRENT</div>
                        <div class="stat-col-val" id="dispCurrent">0.00 <span style="font-size: 10px; color:#64748b;">USDT</span></div>
                    </div>
                </div>

                <div class="no-position">No open positions found. (2/2 Daily Limit Completed)</div>
            </div>

            <div>
                <div class="history-title">Realized Trade History</div>

                <div class="coin-filter-row">
                    <button class="coin-filter active" onclick="filterCoin('ALL', this)">ALL</button>
                    <button class="coin-filter" onclick="filterCoin('ETH-USDT', this)">ETH-USDT</button>
                    <button class="coin-filter" onclick="filterCoin('BTC-USDT', this)">BTC-USDT</button>
                    <button class="coin-filter" onclick="filterCoin('SOL-USDT', this)">SOL-USDT</button>
                </div>

                <div id="tradesListContainer"></div>

                <div id="emptyTradesState" class="empty-state-box" style="display: none;">
                    <div class="empty-icon">📂🔍</div>
                    <div class="empty-text">No Trade History found</div>
                </div>
            </div>
        </div>

        <!-- TAB 2: Plans View -->
        <div id="viewPlans" style="display: none;">
            <div style="margin-bottom: 22px; text-align: center;">
                <h2 style="font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Choose Your Trading Plan</h2>
                <p style="font-size: 13px; color: #94a3b8;">
                    Unlock automated AI trading strategies, risk management, and profit optimization.
                </p>
            </div>

            {plans_html}
        </div>

        <!-- TAB 3: BOT Wallet View -->
        <div id="viewBotWallet" style="display: none;">
            <div class="card-position" style="padding: 22px 24px; margin-bottom: 20px;">
                <div class="card-glow"></div>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="font-size: 18px;">💼</span>
                    <strong style="font-size: 16px; color: #ffffff;">Wallet Overview 👁</strong>
                </div>
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">Live balances across all your holdings</p>

                <div style="background: #060b14; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 18px; display: inline-flex; align-items: center; gap: 14px;">
                    <div style="background: #0284c7; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px;">U</div>
                    <div>
                        <div style="font-size: 11px; color: #64748b; font-weight: 700;">USDT</div>
                        <div style="font-size: 17px; font-weight: 800; color: #38bdf8;" id="walletUsdtBalDisplay">0.00</div>
                    </div>
                </div>
            </div>

            <div class="wallet-actions-bar">
                <button id="pillDeposit" class="wallet-action-pill" onclick="switchWalletTab('deposit')">↙ DEPOSIT • INR ▾</button>
                <button id="pillWithdraw" class="wallet-action-pill" onclick="switchWalletTab('withdraw')">↗ WITHDRAW • INR ▾</button>
                <button id="pillConversion" class="wallet-action-pill active" onclick="switchWalletTab('conversion')">⇄ CONVERSION</button>
            </div>

            <!-- Sub-tab 1: Deposit INR -->
            <div id="walletSubDeposit" style="display: none;">
                <div class="step-indicator">
                    <span class="step-circle" id="stepCircle1">1</span> <span id="stepLabel1" style="color: #ffffff;">PAYMENT DETAILS</span> ────── <span class="step-circle" id="stepCircle2" style="background:#1e293b; color:#94a3b8;">2</span> <span id="stepLabel2">SUBMIT PROOF</span>
                </div>

                <div id="depositStep1">
                    <div class="notice-box" style="border-color: #eab308; background: rgba(234, 179, 8, 0.08); color: #fde047;">
                        ⚠️ For smooth and fast approval, please transfer funds only from the bank account used during your KYC verification. Payments made from third-party accounts may attract additional verification charges or could be delayed.
                    </div>

                    <div class="bank-card">
                        <div class="bank-header">
                            <div class="bank-icon-box">🏛️</div>
                            <div>
                                <div style="display: flex; align-items: center;">
                                    <strong style="font-size: 18px; color: #ffffff;">Bank Transfer</strong>
                                    <span class="badge-rec">RECOMMENDED</span>
                                </div>
                                <div style="font-size: 12px; color: #94a3b8; margin-top: 2px;">NEFT • RTGS • IMPS</div>
                            </div>
                        </div>

                        <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin-bottom: 16px;">
                            Supports all major Indian banks with real-time or scheduled transfers. Ideal for large transactions with secure settlement and a verified payment flow.
                        </p>

                        <div class="feature-pills">
                            <span class="feat-tag">🛡️ Secure</span>
                            <span class="feat-tag">Trusted</span>
                            <span class="feat-tag">High Limit</span>
                        </div>

                        <div class="bank-row">
                            <div>
                                <div class="bank-row-label">ACCOUNT HOLDER / BANK</div>
                                <div class="bank-row-val">{BANK_NAME}</div>
                            </div>
                            <button class="copy-icon-btn" onclick="copyText('{BANK_NAME}')" title="Copy">📋</button>
                        </div>

                        <div class="bank-row">
                            <div>
                                <div class="bank-row-label">ACCOUNT NUMBER</div>
                                <div class="bank-row-val">{ACCOUNT_NUMBER}</div>
                            </div>
                            <button class="copy-icon-btn" onclick="copyText('{ACCOUNT_NUMBER}')" title="Copy">📋</button>
                        </div>

                        <div class="bank-row">
                            <div>
                                <div class="bank-row-label">IFSC CODE</div>
                                <div class="bank-row-val">{IFSC_CODE}</div>
                            </div>
                            <button class="copy-icon-btn" onclick="copyText('{IFSC_CODE}')" title="Copy">📋</button>
                        </div>

                        <div class="notice-box" style="margin-top: 18px; margin-bottom: 20px;">
                            Please transfer the <strong>exact amount</strong> from your registered bank account to avoid delays. Ensure the account holder name matches your verified details. Transactions from third-party accounts may be rejected.<br><br>
                            Once the payment is successfully completed, click the button below to proceed.
                        </div>

                        <button class="btn-action" style="background: linear-gradient(90deg, #10b981, #059669); padding: 14px; font-size: 15px;" onclick="goToDepositStep(2)">
                            I Have Completed Payment
                        </button>
                    </div>
                </div>

                <div id="depositStep2" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h2 style="font-size: 22px; font-weight: 800; color: #ffffff;">Submit Payment Proof</h2>
                        <button onclick="goToDepositStep(1)" style="background: transparent; border: 1px solid #1e293b; color: #94a3b8; padding: 6px 12px; border-radius: 8px; font-size: 12px; cursor: pointer;">← Back</button>
                    </div>
                    <p style="font-size: 12px; color: #94a3b8; margin-bottom: 18px;">
                        Fill in the transfer details exactly as they appear on your bank receipt.
                    </p>

                    <div class="payment-method-card" style="background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 22px;">
                        <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Sender Account Holder Name</label>
                        <input id="proofSenderName" type="text" class="input-box" placeholder="Enter sender name (same as bank/UPI used)">

                        <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Amount Paid (INR)</label>
                        <input id="proofAmountInr" type="number" class="input-box" placeholder="₹ Enter exact transferred amount">

                        <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">UTR / Transaction Reference Number</label>
                        <input id="proofUtr" type="text" class="input-box" placeholder="Enter transaction / UTR number">

                        <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Upload Payment Screenshot</label>
                        <div class="proof-upload-box" onclick="document.getElementById('proofFileInput').click()">
                            <input type="file" id="proofFileInput" style="display: none;" onchange="handleFileSelected(this)">
                            <div style="font-size: 28px; margin-bottom: 8px;">📤</div>
                            <div id="uploadBoxLabel" style="font-size: 13px; color: #f8fafc; font-weight: 700;">Click to upload screenshot</div>
                            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">JPG, PNG, JPEG - up to 5MB</div>
                        </div>

                        <div class="notice-box" style="border-color: #eab308; background: rgba(234, 179, 8, 0.08); color: #fde047; margin-bottom: 18px;">
                            After submission, our finance team will manually verify your payment. Approval usually takes up to 24 hours.<br>
                            • Payment is made from your KYC verified account<br>
                            • UTR number is correct<br>
                            • Screenshot is clear and readable
                        </div>

                        <button class="btn-action" style="background: #10b981; padding: 14px; font-size: 15px;" onclick="submitBankDepositProof()">
                            Submit Payment Proof
                        </button>
                    </div>
                </div>

                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Deposit History</h3>
                    <div id="personalDepositList">
                        <div class="empty-state-box"><div class="empty-icon">📥</div><div class="empty-text">No Deposit History found</div></div>
                    </div>
                </div>
            </div>

            <!-- Sub-tab 2: Withdraw INR -->
            <div id="walletSubWithdraw" style="display: none;">
                <h2 style="font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Withdraw Funds (INR)</h2>
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">Request an instant withdrawal in Indian Rupees directly to your verified Bank Account or UPI.</p>
                
                <div class="notice-box" style="border-color: #0284c7; background: rgba(2, 132, 199, 0.08); color: #38bdf8;">
                    ℹ️ <strong>Withdrawal Policy:</strong> Minimum ₹1,000 INR • Maximum ₹10,000 INR per transaction • Payout via 24x7 IMPS / UPI
                </div>

                <div class="payment-method-card" style="background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 22px;">
                    <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Withdrawal Amount (₹ INR)</label>
                    <input id="withdrawAmtInr" type="number" class="input-box" placeholder="Min ₹1,000 - Max ₹10,000" min="1000" max="10000">

                    <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Destination UPI ID / Bank Account Details</label>
                    <input id="withdrawDest" type="text" class="input-box" placeholder="e.g. yourname@okaxis or A/C No + IFSC">
                    
                    <button class="btn-action" style="background: #ef4444; padding: 14px; font-size: 15px; margin-top: 6px;" onclick="submitWithdrawalInr()">Request Withdrawal (INR)</button>
                </div>

                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Withdrawal History</h3>
                    <div id="personalWithdrawList">
                        <div class="empty-state-box"><div class="empty-icon">📤</div><div class="empty-text">No Withdrawal History found</div></div>
                    </div>
                </div>
            </div>

            <!-- Sub-tab 3: Conversion -->
            <div id="walletSubConversion">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
                    <div style="background: #064e3b; border: 1px solid #059669; width: 36px; height: 36px; border-radius: 10px; display: flex; justify-content: center; align-items: center; font-size: 18px;">🤖</div>
                    <div>
                        <h2 style="font-size: 22px; font-weight: 800; color: #ffffff;">Conversion (INR ↔ USDT)</h2>
                        <p style="font-size: 12px; color: #94a3b8;">Convert between your INR and USDT balance instantly.</p>
                    </div>
                </div>

                <div class="notice-box" style="margin: 16px 0 20px;">
                    Convert between INR and USDT instantly at real-time market rates. No trading fees are applied. Final value may vary slightly depending on market movement.
                </div>

                <div class="swap-card">
                    <div class="swap-box">
                        <div class="swap-label-row">
                            <span>From</span>
                            <span>Available: <span id="fromAvailableDisplay">₹ 0.00 INR</span></span>
                        </div>
                        <div class="swap-input-row">
                            <input id="fromAmountInput" type="number" class="swap-input" placeholder="0.00" value="0.00" oninput="handleSwapCalculate()">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="max-pill" onclick="handleMaxClick()">Max</span>
                                <div class="curr-pill" id="fromCurrPill">INR ▾</div>
                            </div>
                        </div>
                    </div>

                    <button class="swap-divider-btn" onclick="toggleSwapDirection()" title="Swap Currencies">⇅</button>

                    <div class="swap-box">
                        <div class="swap-label-row">
                            <span>To</span>
                            <span>Available: <span id="toAvailableDisplay">0.0000 USDT</span></span>
                        </div>
                        <div class="swap-input-row">
                            <input id="toAmountInput" type="text" class="swap-input" placeholder="0" value="0" readonly>
                            <div class="curr-pill" id="toCurrPill">USDT ▾</div>
                        </div>
                    </div>

                    <div class="calc-breakdown">
                        <div class="breakdown-row">
                            <span><span id="rateDirectionLabel">INR → USDT</span> <span style="background:#064e3b; color:#34d399; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">● Live</span></span>
                            <strong style="color: #f8fafc;" id="liveRateText">1 USDT ≈ {USDT_INR_RATE:.4f} INR</strong>
                        </div>
                        <div class="breakdown-row">
                            <span>Conversion Fee</span>
                            <span style="color: #34d399; font-weight:700;">0%</span>
                        </div>
                        <div class="breakdown-row">
                            <span>TDS</span>
                            <span style="color: #34d399; font-weight:700;">0%</span>
                        </div>
                        <div class="breakdown-row">
                            <span>Price Type</span>
                            <span style="color: #94a3b8;">Real-time market price</span>
                        </div>
                        <div class="breakdown-row" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #16233b;">
                            <span style="font-weight: 700; color: #f8fafc;">You will receive</span>
                            <strong style="color: #38bdf8; font-size: 16px;" id="receiveSummaryText">0 USDT</strong>
                        </div>
                    </div>

                    <button class="btn-action" style="background: linear-gradient(90deg, #10b981, #059669); margin-top: 14px; padding: 14px; font-size: 16px;" onclick="executeConversion()">Convert</button>
                </div>

                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Conversion History</h3>
                    <div id="personalConversionList">
                        <div class="empty-state-box"><div class="empty-icon">🔄</div><div class="empty-text">No Conversion History found</div></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 4: Overview / Bot Wallet Activity -->
        <div id="viewOverview" style="display: none;">
            <div style="margin-bottom: 20px;">
                <h2 style="font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Bot Wallet Activity</h2>
                <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
                    Track all automated trading transactions, earnings, and fund movements generated by your active bot strategies.
                </p>
            </div>

            <div class="overview-summary">
                <div>
                    <div class="summary-label">Total INR Deposit</div>
                    <div class="summary-val" id="dispTotalDeposit" style="color: #34d399;">+₹0.00</div>
                </div>
                <div>
                    <div class="summary-label">Total INR Withdrawal</div>
                    <div class="summary-val" id="dispTotalWithdrawal" style="color: #f87171;">-₹0.00</div>
                </div>
            </div>

            <div id="overviewListContainer">
                <div class="empty-state-box"><div class="empty-icon">💼</div><div class="empty-text">No Wallet Activity found</div></div>
            </div>
        </div>

        <!-- TAB 5: 👑 Admin Approval Panel -->
        <div id="viewAdminPanel" style="display: none;">
            <div style="margin-bottom: 20px; text-align: left;">
                <h2 style="font-size: 24px; font-weight: 800; color: #fde047; margin-bottom: 6px;">👑 Master Admin Approval Panel</h2>
                <p style="font-size: 13px; color: #94a3b8;">
                    Review customer deposits, verify UTR numbers, credit INR to wallet, and activate plans.
                </p>
            </div>

            <h3 style="color: #38bdf8; font-size: 18px; margin-bottom: 14px; text-align: left;">Pending Bank Deposits (Wallet Funding)</h3>
            <div id="adminPendingDepositsList">
                <div style="color:#64748b; padding: 16px; text-align: center;">Loading pending requests...</div>
            </div>

            <h3 style="color: #38bdf8; font-size: 18px; margin: 26px 0 14px; text-align: left;">Pending Subscription Plans</h3>
            <div id="adminPendingPlansList">
                <div style="color:#64748b; padding: 16px; text-align: center;">Loading pending plans...</div>
            </div>

            <h3 style="color: #38bdf8; font-size: 18px; margin: 26px 0 14px; text-align: left;">Registered Users</h3>
            <div id="adminUsersList">
                <div style="color:#64748b; padding: 16px; text-align: center;">Loading users...</div>
            </div>
        </div>
    </div>

    <!-- Profit Split Applied Modal -->
    <div id="splitModal" class="modal">
        <div class="modal-content" style="max-width: 380px; text-align: left; padding: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="font-size: 17px; color: #ffffff; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                    💡 Profit Split Applied
                </h3>
                <span onclick="closeProfitSplitModal()" style="color: #94a3b8; font-size: 20px; cursor: pointer; font-weight: 700;">✕</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 14px; font-size: 14px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; color: #f8fafc;">
                    <span style="color: #cbd5e1;">Your Share :</span>
                    <strong style="color: #f8fafc;" id="splitUserShare">$0.000000</strong>
                </div>
                <div style="display: flex; justify-content: space-between; color: #f8fafc;">
                    <span style="color: #cbd5e1;">Admin Share :</span>
                    <strong style="color: #38bdf8;" id="splitAdminShare">$0.000000</strong>
                </div>
                <div style="display: flex; justify-content: space-between; color: #f8fafc;">
                    <span style="color: #cbd5e1;">Upline Share :</span>
                    <strong style="color: #94a3b8;" id="splitUplineShare">$0</strong>
                </div>
            </div>
        </div>
    </div>

    <!-- Plan Checkout Modal -->
    <div id="payModal" class="modal">
        <div class="modal-content">
            <h3 id="modalPlanTitle" style="color: #38bdf8;">Plan Activation</h3>
            <p id="modalPlanSubtitle" style="font-size: 12px; color: #94a3b8; margin: 6px 0 14px;">Instant UPI Transfer</p>
            
            <div style="background: white; padding: 8px; border-radius: 12px; display: inline-block; margin-bottom: 10px;">
                <img id="dynamicPlanQrImg" src="" alt="UPI QR" style="width: 170px; height: 170px; display: block;">
            </div>
            
            <div style="color: #38bdf8; font-family: monospace; font-size: 13px; margin-bottom: 12px;">UPI ID: {MY_UPI_ID}</div>
            <a id="dynamicPlanIntentBtn" href="#" class="pill-btn-wide" style="background: #0284c7; color: #ffffff; font-weight: 700; text-decoration: none;">📱 Pay via Any UPI App (GPay/PhonePe)</a>
            
            <div style="border-top: 1px solid #16233b; padding-top: 14px; margin-top: 10px;">
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">Payment ke baad 12-digit UTR No. enter karein:</p>
                <input id="planUtrInput" type="text" class="input-box" placeholder="Enter 12-digit UTR (e.g. 423567890123)">
                <button class="btn-action" style="background: #10b981;" onclick="submitPlanPayment()">✅ Verify UTR & Activate Plan</button>
            </div>
            <button class="btn-close" onclick="closePaymentModal()">Close</button>
        </div>
    </div>

    <!-- Profile Modal (Unique UID for every personal account) -->
    <div id="profileModal" class="modal">
        <div class="modal-content" style="text-align: left; padding: 26px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="color: #38bdf8; font-size: 18px; font-weight: 800;">User Profile</h3>
                <span onclick="closeProfileModal()" style="color: #94a3b8; font-size: 20px; cursor: pointer; font-weight: 700;">✕</span>
            </div>

            <!-- Unique UID Box with Copy Button -->
            <div style="background: #060b14; border: 1px solid #1e293b; border-radius: 12px; padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <div>
                    <div style="font-size: 10px; color: #64748b; font-weight: 700; letter-spacing: 0.5px;">ACCOUNT UID</div>
                    <div style="font-size: 16px; font-weight: 800; color: #38bdf8; font-family: monospace;" id="profileUidDisplay">UID: --------</div>
                </div>
                <button class="copy-icon-btn" onclick="copyText(document.getElementById('profileUidDisplay').innerText.replace('UID: ', ''))" title="Copy UID">📋</button>
            </div>

            <label style="font-size: 11px; color: #94a3b8; font-weight: 700; display: block; margin-bottom: 4px;">Registered Email</label>
            <input id="profileEmail" type="text" class="input-box" readonly style="color: #94a3b8; background: #070d18;">

            <label style="font-size: 11px; color: #94a3b8; font-weight: 700; display: block; margin-bottom: 4px;">Full Name</label>
            <input id="profileName" type="text" class="input-box" placeholder="Your Name">

            <label style="font-size: 11px; color: #94a3b8; font-weight: 700; display: block; margin-bottom: 4px;">Phone Number</label>
            <input id="profilePhone" type="tel" class="input-box" placeholder="+91 ...">

            <button class="btn-action" style="margin-top: 6px;" onclick="closeProfileModal()">Save & Close</button>
        </div>
    </div>

    <script>
        const CURRENT_RATE = {USDT_INR_RATE};
        const MIN_WITHDRAW = {MIN_WITHDRAW_INR};
        const MAX_WITHDRAW = {MAX_WITHDRAW_INR};
        const UPI_ID = "{MY_UPI_ID}";
        
        let currentUsdtBal = 0.0;
        let currentInrBal = 0.0;
        let swapDirection = 'INR_TO_USDT';
        let isBalanceHidden = false;

        let selectedPlanId = 'STANDARD';
        let selectedPlanPrice = 999;
        let selectedPlanDays = 30;
        let selectedPlanName = 'STANDARD PACKAGE';

        let origValues = {{
            principal: '0.00 USDT',
            epnl: '+0.00',
            pnl: '+0.00 USDT',
            current: '0.00 USDT',
            header: '0.00 USDT'
        }};

        window.addEventListener('DOMContentLoaded', () => {{
            const saved = localStorage.getItem('cryptobot_user_email');
            if (saved) {{
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('mainDashboard').style.display = 'block';
                const initial = saved.charAt(0).toUpperCase();
                document.getElementById('avatarBtn').innerText = initial;
                loadUserPersonalData(saved);
            }}
        }});

        function togglePasswordVisibility(inputId, iconElem) {{
            const input = document.getElementById(inputId);
            if (input.type === 'password') {{
                input.type = 'text';
                iconElem.innerText = '🙈';
            }} else {{
                input.type = 'password';
                iconElem.innerText = '👁';
            }}
        }}

        async function loadUserPersonalData(email) {{
            try {{
                const res = await fetch('/api/user-status', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ email: email }})
                }});
                const data = await res.json();
                if (data.status === 'success' && data.user) {{
                    const u = data.user;
                    const isAdmin = (email.toLowerCase() === 'admin@cryptobot.com') || u.is_admin;
                    
                    const userUid = u.uid || generateClientUid(email);
                    document.getElementById('profileUidDisplay').innerText = 'UID: ' + userUid;
                    document.getElementById('profileEmail').value = email;
                    document.getElementById('profileName').value = (u.profile && u.profile.name) || email.split('@')[0];
                    document.getElementById('profilePhone').value = (u.profile && u.profile.phone) || '';

                    if (isAdmin) {{
                        document.getElementById('navAdminPanel').style.display = 'inline-block';
                        currentUsdtBal = u.balance || 1000.0;
                        currentInrBal = u.inr_balance || 0.0;
                        origValues.principal = '1000.00 USDT';
                        origValues.epnl = '+3.00';
                        origValues.pnl = '+3.00 USDT';
                        origValues.current = currentUsdtBal.toFixed(2) + ' USDT';
                        origValues.header = currentUsdtBal.toFixed(2) + ' USDT';
                    }} else {{
                        document.getElementById('navAdminPanel').style.display = 'none';
                        currentUsdtBal = u.balance || 0.0;
                        currentInrBal = u.inr_balance || 0.0;
                        
                        const lifetimePnl = u.total_profit || 0.0;
                        const principalBal = u.principal || currentUsdtBal;
                        origValues.principal = principalBal.toFixed(2) + ' USDT';
                        origValues.epnl = '+' + lifetimePnl.toFixed(2);
                        origValues.pnl = '+' + lifetimePnl.toFixed(2) + ' USDT';
                        origValues.current = currentUsdtBal.toFixed(2) + ' USDT';
                        origValues.header = currentUsdtBal.toFixed(2) + ' USDT';
                    }}

                    document.getElementById('dispPrincipal').innerHTML = origValues.principal.replace('USDT', '<span style="font-size: 10px; color:#64748b;">USDT</span>');
                    document.getElementById('dispEpnl').innerText = origValues.epnl;
                    document.getElementById('dispPnl').innerHTML = origValues.pnl.replace('USDT', '<span style="font-size: 10px;">USDT</span>');
                    document.getElementById('dispCurrent').innerHTML = origValues.current.replace('USDT', '<span style="font-size: 10px; color:#64748b;">USDT</span>');
                    document.getElementById('headerBalText').innerText = origValues.header;
                    document.getElementById('walletUsdtBalDisplay').innerText = currentUsdtBal.toFixed(2);
                    
                    updateSwapDisplay();

                    renderUserTrades(data.trades || []);
                    renderPersonalActivity(data.activity || []);

                    const activePlan = u.plan;
                    const daysLeft = u.days_left || 0;
                    if (activePlan && activePlan !== 'NONE') {{
                        const btn = document.getElementById('planBtn_' + activePlan);
                        if (btn) {{
                            btn.innerText = 'PLAN ACTIVE • ' + daysLeft + 'D LEFT';
                            btn.classList.add('active-badge');
                            btn.onclick = null;
                        }}
                    }}
                }}
            }} catch(e) {{
                console.error(e);
            }}
        }}

        function generateClientUid(str) {{
            let hash = 0;
            for (let i = 0; i < str.length; i++) {{
                hash = ((hash << 5) - hash) + str.charCodeAt(i);
                hash |= 0;
            }}
            return (Math.abs(hash) % 90000000 + 10000000).toString();
        }}

        function renderUserTrades(trades) {{
            const container = document.getElementById('tradesListContainer');
            const emptyBox = document.getElementById('emptyTradesState');
            if (!trades || trades.length === 0) {{
                container.innerHTML = '';
                emptyBox.style.display = 'block';
                return;
            }}
            emptyBox.style.display = 'none';
            let html = '';
            trades.slice().reverse().forEach(t => {{
                const c = (t.coin || '').replace('/', '-').toUpperCase();
                const total_p = Number(t.profit || 1.50);
                const admin_s = total_p * 0.15;
                const user_s = total_p * 0.85;
                const open_p = t.entry_price || 0.0;
                const close_p = t.target_price || 0.0;
                const time_s = t.time || '';

                html += `
                <div class="trade-card-split" data-coin="${{c}}">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <span style="font-size: 16px;">💎</span>
                        <strong style="color: #f8fafc; font-size: 15px;">${{c}} ---</strong>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; margin-bottom: 14px;">
                        <div>
                            <div style="color: #94a3b8; font-size: 12px;">Open Price: <span style="color:#ffffff;">$${{open_p}}</span></div>
                            <div style="color: #34d399; font-weight: 700; margin-top: 4px;">Total PnL: ${total_p.toFixed(2)} PnL</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="color: #94a3b8; font-size: 12px;">Close Price: <span style="color:#ffffff;">$${{close_p}}</span></div>
                            <div style="color: #38bdf8; font-weight: 700; margin-top: 4px;">Your PnL: ${user_s.toFixed(2)} PnL</div>
                        </div>
                    </div>

                    <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #16233b; padding-top: 10px;">
                        <span style="font-size: 11px; color: #64748b;">${{time_s}}</span>
                        <button class="btn-view-split" onclick="openProfitSplitModal(${user_s.toFixed(6)}, ${admin_s.toFixed(6)})">View</button>
                    </div>
                </div>`;
            }});
            container.innerHTML = html;
        }}

        function updateSwapDisplay() {{
            if (swapDirection === 'INR_TO_USDT') {{
                document.getElementById('fromAvailableDisplay').innerText = '₹ ' + currentInrBal.toLocaleString('en-IN', {{minimumFractionDigits: 2}}) + ' INR';
                document.getElementById('toAvailableDisplay').innerText = currentUsdtBal.toFixed(4) + ' USDT';
                document.getElementById('fromCurrPill').innerText = 'INR ▾';
                document.getElementById('toCurrPill').innerText = 'USDT ▾';
                document.getElementById('rateDirectionLabel').innerText = 'INR → USDT';
            }} else {{
                document.getElementById('fromAvailableDisplay').innerText = currentUsdtBal.toFixed(4) + ' USDT';
                document.getElementById('toAvailableDisplay').innerText = '₹ ' + currentInrBal.toLocaleString('en-IN', {{minimumFractionDigits: 2}}) + ' INR';
                document.getElementById('fromCurrPill').innerText = 'USDT ▾';
                document.getElementById('toCurrPill').innerText = 'INR ▾';
                document.getElementById('rateDirectionLabel').innerText = 'USDT → INR';
            }}
        }}

        function renderPersonalActivity(activityList) {{
            let depHtml = '';
            let withHtml = '';
            let convHtml = '';
            let allHtml = '';
            let totalDep = 0.0;
            let totalWith = 0.0;

            activityList.forEach(w => {{
                const cat = w.category || '';
                const amtInr = Math.abs(parseFloat(w.amount_inr || 0.0));
                const st = w.status || 'Completed';
                
                let stBg = '#064e3b';
                let stColor = '#34d399';
                if (st.includes('Pending')) {{
                    stBg = '#78350f';
                    stColor = '#fde047';
                }} else if (st === 'Rejected') {{
                    stBg = '#7f1d1d';
                    stColor = '#f87171';
                }}

                if (cat === 'DEPOSIT' || (w.type && w.type.includes('Deposit'))) {{
                    if (st === 'Completed') totalDep += amtInr;
                    const markup = `
                    <div class="wallet-card">
                        <div>
                            <div style="font-size: 13px; color: #f8fafc; font-weight: 600;">${{w.date || ''}}</div>
                            <div style="font-size: 11px; color: #71717a; margin-top: 2px;">${{w.time || ''}}</div>
                            <div style="font-size: 13px; color: #38bdf8; margin-top: 6px; font-weight: 600;">${{w.type || 'INR Deposit'}}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 16px; font-weight: 800; color: #34d399;">+₹${{amtInr.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
                            <span class="status-badge" style="background: ${{stBg}}; color: ${{stColor}};">${{st}}</span>
                        </div>
                    </div>`;
                    depHtml += markup;
                    allHtml += markup;
                }} else if (cat === 'WITHDRAWAL' || (w.type && w.type.includes('Withdrawal'))) {{
                    if (st === 'Completed') totalWith += amtInr;
                    const markup = `
                    <div class="wallet-card">
                        <div>
                            <div style="font-size: 13px; color: #f8fafc; font-weight: 600;">${{w.date || ''}}</div>
                            <div style="font-size: 11px; color: #71717a; margin-top: 2px;">${{w.time || ''}}</div>
                            <div style="font-size: 13px; color: #f87171; margin-top: 6px; font-weight: 600;">INR Withdrawal</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 16px; font-weight: 800; color: #ef4444;">-₹${{amtInr.toLocaleString('en-IN', {{minimumFractionDigits: 2}})}}</div>
                            <span class="status-badge" style="background: ${{stBg}}; color: ${{stColor}};">${{st}}</span>
                        </div>
                    </div>`;
                    withHtml += markup;
                    allHtml += markup;
                }} else if (cat === 'CONVERSION' || (w.type && w.type.includes('Converted'))) {{
                    const markup = `
                    <div class="wallet-card">
                        <div>
                            <div style="font-size: 13px; color: #f8fafc; font-weight: 600;">${{w.date || ''}}</div>
                            <div style="font-size: 11px; color: #71717a; margin-top: 2px;">${{w.time || ''}}</div>
                            <div style="font-size: 13px; color: #bef264; margin-top: 6px; font-weight: 600;">${{w.type || ''}}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 16px; font-weight: 800; color: #38bdf8;">Completed</div>
                            <span class="status-badge" style="background: #064e3b; color: #34d399;">Instant Swap</span>
                        </div>
                    </div>`;
                    convHtml += markup;
                    allHtml += markup;
                }}
            }});

            document.getElementById('personalDepositList').innerHTML = depHtml || '<div class="empty-state-box"><div class="empty-icon">📥</div><div class="empty-text">No Deposit History found</div></div>';
            document.getElementById('personalWithdrawList').innerHTML = withHtml || '<div class="empty-state-box"><div class="empty-icon">📤</div><div class="empty-text">No Withdrawal History found</div></div>';
            document.getElementById('personalConversionList').innerHTML = convHtml || '<div class="empty-state-box"><div class="empty-icon">🔄</div><div class="empty-text">No Conversion History found</div></div>';
            document.getElementById('overviewListContainer').innerHTML = allHtml || '<div class="empty-state-box"><div class="empty-icon">💼</div><div class="empty-text">No Wallet Activity found</div></div>';

            document.getElementById('dispTotalDeposit').innerText = '+₹' + totalDep.toLocaleString('en-IN', {{minimumFractionDigits: 2}});
            document.getElementById('dispTotalWithdrawal').innerText = '-₹' + totalWith.toLocaleString('en-IN', {{minimumFractionDigits: 2}});
        }}

        function copyText(text) {{
            navigator.clipboard.writeText(text);
            alert('Copied: ' + text);
        }}

        function goToDepositStep(step) {{
            if (step === 2) {{
                document.getElementById('depositStep1').style.display = 'none';
                document.getElementById('depositStep2').style.display = 'block';
                document.getElementById('stepCircle2').style.background = '#0284c7';
                document.getElementById('stepCircle2').style.color = 'white';
                document.getElementById('stepLabel2').style.color = '#ffffff';
            }} else {{
                document.getElementById('depositStep2').style.display = 'none';
                document.getElementById('depositStep1').style.display = 'block';
                document.getElementById('stepCircle2').style.background = '#1e293b';
                document.getElementById('stepCircle2').style.color = '#94a3b8';
                document.getElementById('stepLabel2').style.color = '#64748b';
            }}
        }}

        function handleFileSelected(input) {{
            if (input.files && input.files[0]) {{
                document.getElementById('uploadBoxLabel').innerText = 'Selected: ' + input.files[0].name;
            }}
        }}

        async function submitBankDepositProof() {{
            const name = document.getElementById('proofSenderName').value.trim();
            const amt = parseFloat(document.getElementById('proofAmountInr').value) || 0;
            const utr = document.getElementById('proofUtr').value.trim();

            if (!name) {{ alert('Please enter Sender Account Holder Name'); return; }}
            if (amt <= 0) {{ alert('Please enter valid transferred amount'); return; }}
            if (!utr || utr.length < 6) {{ alert('Please enter valid 12-digit UTR No.'); return; }}

            const email = localStorage.getItem('cryptobot_user_email') || 'User';
            const res = await fetch('/api/deposit-inr', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    sender_name: name,
                    amount_inr: amt,
                    utr: utr,
                    email: email
                }})
            }});
            const data = await res.json();
            alert(data.message);
            window.location.reload();
        }}

        function toggleEyeVisibility() {{
            isBalanceHidden = !isBalanceHidden;
            const eyeBtn = document.getElementById('eyeBtn');
            if (isBalanceHidden) {{
                eyeBtn.innerText = '🙈';
                document.getElementById('dispPrincipal').innerHTML = '**** <span style="font-size: 10px; color:#64748b;">USDT</span>';
                document.getElementById('dispEpnl').innerText = '****';
                document.getElementById('dispPnl').innerHTML = '**** <span style="font-size: 10px;">USDT</span>';
                document.getElementById('dispCurrent').innerHTML = '**** <span style="font-size: 10px; color:#64748b;">USDT</span>';
                document.getElementById('headerBalText').innerText = '**** USDT';
            }} else {{
                eyeBtn.innerText = '👁';
                document.getElementById('dispPrincipal').innerHTML = origValues.principal.replace('USDT', '<span style="font-size: 10px; color:#64748b;">USDT</span>');
                document.getElementById('dispEpnl').innerText = origValues.epnl;
                document.getElementById('dispPnl').innerHTML = origValues.pnl.replace('USDT', '<span style="font-size: 10px;">USDT</span>');
                document.getElementById('dispCurrent').innerHTML = origValues.current.replace('USDT', '<span style="font-size: 10px; color:#64748b;">USDT</span>');
                document.getElementById('headerBalText').innerText = origValues.header;
            }}
        }}

        function openProfitSplitModal(userShare, adminShare) {{
            document.getElementById('splitUserShare').innerText = '$' + Number(userShare).toFixed(6);
            document.getElementById('splitAdminShare').innerText = '$' + Number(adminShare).toFixed(6);
            document.getElementById('splitModal').style.display = 'flex';
        }}
        function closeProfitSplitModal() {{
            document.getElementById('splitModal').style.display = 'none';
        }}

        function showTab(tab) {{
            document.getElementById('viewTradeLogs').style.display = 'none';
            document.getElementById('viewPlans').style.display = 'none';
            document.getElementById('viewBotWallet').style.display = 'none';
            document.getElementById('viewOverview').style.display = 'none';
            document.getElementById('viewAdminPanel').style.display = 'none';
            
            document.getElementById('navTradeLogs').classList.remove('active');
            document.getElementById('navPlans').classList.remove('active');
            document.getElementById('navBotWallet').classList.remove('active');
            document.getElementById('navOverview').classList.remove('active');
            document.getElementById('navAdminPanel').classList.remove('active');

            if (tab === 'plans') {{
                document.getElementById('viewPlans').style.display = 'block';
                document.getElementById('navPlans').classList.add('active');
            }} else if (tab === 'botWallet') {{
                document.getElementById('viewBotWallet').style.display = 'block';
                document.getElementById('navBotWallet').classList.add('active');
                switchWalletTab('conversion');
            }} else if (tab === 'overview') {{
                document.getElementById('viewOverview').style.display = 'block';
                document.getElementById('navOverview').classList.add('active');
            }} else if (tab === 'adminPanel') {{
                document.getElementById('viewAdminPanel').style.display = 'block';
                document.getElementById('navAdminPanel').classList.add('active');
                loadAdminPanelData();
            }} else {{
                document.getElementById('viewTradeLogs').style.display = 'block';
                document.getElementById('navTradeLogs').classList.add('active');
            }}
        }}

        function switchWalletTab(subTab) {{
            document.getElementById('walletSubDeposit').style.display = 'none';
            document.getElementById('walletSubWithdraw').style.display = 'none';
            document.getElementById('walletSubConversion').style.display = 'none';

            document.getElementById('pillDeposit').classList.remove('active');
            document.getElementById('pillWithdraw').classList.remove('active');
            document.getElementById('pillConversion').classList.remove('active');

            if (subTab === 'withdraw') {{
                document.getElementById('walletSubWithdraw').style.display = 'block';
                document.getElementById('pillWithdraw').classList.add('active');
            }} else if (subTab === 'deposit') {{
                document.getElementById('walletSubDeposit').style.display = 'block';
                document.getElementById('pillDeposit').classList.add('active');
            }} else {{
                document.getElementById('walletSubConversion').style.display = 'block';
                document.getElementById('pillConversion').classList.add('active');
            }}
        }}

        function filterCoin(coin, btn) {{
            document.querySelectorAll('#viewTradeLogs .coin-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const rows = document.querySelectorAll('.trade-card-split');
            const emptyBox = document.getElementById('emptyTradesState');
            let visibleCount = 0;
            const target = coin.replace(/[^A-Za-z]/g, '').toUpperCase();

            rows.forEach(r => {{
                const rowCoin = (r.getAttribute('data-coin') || '').replace(/[^A-Za-z]/g, '').toUpperCase();
                if (coin === 'ALL' || rowCoin.includes(target) || target.includes(rowCoin)) {{
                    r.style.display = 'block';
                    visibleCount++;
                }} else {{
                    r.style.display = 'none';
                }}
            }});

            if (visibleCount === 0) {{
                emptyBox.style.display = 'block';
            }} else {{
                emptyBox.style.display = 'none';
            }}
        }}

        function openPlanCheckout(planId, price, name, days) {{
            selectedPlanId = planId;
            selectedPlanPrice = price;
            selectedPlanDays = days;
            selectedPlanName = name;

            document.getElementById('modalPlanTitle').innerText = name + ' (₹' + price.toLocaleString() + ')';
            document.getElementById('modalPlanSubtitle').innerText = 'Unlimited AI Bot Access for ' + days + ' Days';
            
            const upiUrl = 'upi://pay?pa=' + UPI_ID + '&pn=trade.ai&am=' + price + '&cu=INR&tn=' + encodeURIComponent(name);
            const qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=' + encodeURIComponent(upiUrl);
            
            document.getElementById('dynamicPlanQrImg').src = qrUrl;
            const intentBtn = document.getElementById('dynamicPlanIntentBtn');
            intentBtn.href = upiUrl;
            intentBtn.innerText = '📱 Pay ₹' + price.toLocaleString() + ' via GPay / PhonePe';

            document.getElementById('planUtrInput').value = '';
            document.getElementById('payModal').style.display = 'flex';
        }}

        function openPaymentModal() {{ showTab('plans'); }}
        function closePaymentModal() {{ document.getElementById('payModal').style.display = 'none'; }}

        async function submitPlanPayment() {{
            const utr = document.getElementById('planUtrInput').value.trim();
            if (!utr || utr.length < 6) {{
                alert('❌ Kripya valid 12-digit UTR / Reference No. enter karein!');
                return;
            }}
            const email = localStorage.getItem('cryptobot_user_email') || 'User';
            const res = await fetch('/api/verify-plan-utr', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    plan_id: selectedPlanId,
                    plan_name: selectedPlanName,
                    price: selectedPlanPrice,
                    days: selectedPlanDays,
                    utr: utr,
                    email: email
                }})
            }});
            const data = await res.json();
            alert(data.message);
            if (data.status === 'success') {{
                closePaymentModal();
                window.location.reload();
            }}
        }}

        async function submitWithdrawalInr() {{
            const amtInr = parseFloat(document.getElementById('withdrawAmtInr').value) || 0;
            const dest = document.getElementById('withdrawDest').value.trim();

            if (amtInr < MIN_WITHDRAW) {{
                alert('❌ Minimum withdrawal amount ₹1,000 INR hona chahiye!');
                return;
            }}
            if (amtInr > MAX_WITHDRAW) {{
                alert('❌ Maximum withdrawal limit ₹10,000 INR hai!');
                return;
            }}
            if (!dest) {{
                alert('❌ Kripya Destination UPI ID ya Bank Details daalein!');
                return;
            }}

            const res = await fetch('/api/withdraw-inr', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    amount_inr: amtInr,
                    destination: dest,
                    email: localStorage.getItem('cryptobot_user_email') || ''
                }})
            }});
            const data = await res.json();
            alert(data.message);
            if (data.status === 'success') {{
                window.location.reload();
            }}
        }}

        function handleSwapCalculate() {{
            const val = parseFloat(document.getElementById('fromAmountInput').value) || 0;
            if (swapDirection === 'INR_TO_USDT') {{
                const res = val / CURRENT_RATE;
                document.getElementById('toAmountInput').value = res.toFixed(4);
                document.getElementById('receiveSummaryText').innerText = res.toFixed(4) + ' USDT';
            }} else {{
                const res = val * CURRENT_RATE;
                document.getElementById('toAmountInput').value = res.toFixed(2);
                document.getElementById('receiveSummaryText').innerText = res.toFixed(2) + ' INR';
            }}
        }}

        function handleMaxClick() {{
            if (swapDirection === 'INR_TO_USDT') {{
                document.getElementById('fromAmountInput').value = currentInrBal.toFixed(2);
            }} else {{
                document.getElementById('fromAmountInput').value = currentUsdtBal.toFixed(2);
            }}
            handleSwapCalculate();
        }}

        function toggleSwapDirection() {{
            if (swapDirection === 'INR_TO_USDT') {{
                swapDirection = 'USDT_TO_INR';
            }} else {{
                swapDirection = 'INR_TO_USDT';
            }}
            updateSwapDisplay();
            document.getElementById('fromAmountInput').value = '0.00';
            document.getElementById('toAmountInput').value = '0';
            document.getElementById('receiveSummaryText').innerText = '0 ' + (swapDirection === 'INR_TO_USDT' ? 'USDT' : 'INR');
        }}

        async function executeConversion() {{
            const val = parseFloat(document.getElementById('fromAmountInput').value) || 0;
            if (val <= 0) {{ alert('Please enter an amount to convert!'); return; }}
            const email = localStorage.getItem('cryptobot_user_email') || '';
            const res = await fetch('/api/convert', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ amount: val, direction: swapDirection, email: email }})
            }});
            const data = await res.json();
            alert(data.message);
            window.location.reload();
        }}

        async function loadAdminPanelData() {{
            try {{
                const res = await fetch('/api/admin/data');
                const d = await res.json();
                
                let depHtml = '';
                if (d.pending_deposits && d.pending_deposits.length > 0) {{
                    d.pending_deposits.forEach((req) => {{
                        depHtml += `
                        <div class="admin-req-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <div>
                                    <strong style="color: #38bdf8; font-size: 15px;">${{req.email || 'User'}}</strong>
                                    <div style="color: #94a3b8; font-size: 12px; margin-top: 2px;">Sender: ${{req.sender_name || 'N/A'}} • ${{req.date}} ${{req.time}}</div>
                                    <div style="color: #fde047; font-family: monospace; font-size: 13px; margin-top: 4px;">UTR: ${{req.utr}}</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="color: #34d399; font-size: 18px; font-weight: 800;">₹${{Number(req.amount_inr).toLocaleString()}}</div>
                                    <div style="font-size: 11px; color: #64748b;">Credit: ₹${{Number(req.amount_inr).toLocaleString()}} INR</div>
                                </div>
                            </div>
                            <div style="margin-top: 10px;">
                                <button class="btn-approve" onclick="approveDeposit('${{req.id}}', '${{req.email}}', ${{req.amount_inr}})">✅ Approve & Credit ₹${{Number(req.amount_inr).toLocaleString()}} INR</button>
                                <button class="btn-reject" onclick="rejectDeposit('${{req.id}}')">❌ Reject</button>
                            </div>
                        </div>`;
                    }});
                }} else {{
                    depHtml = '<div style="color: #64748b; padding: 18px; text-align: center;">No pending deposit requests.</div>';
                }}
                document.getElementById('adminPendingDepositsList').innerHTML = depHtml;

                let planHtml = '';
                if (d.pending_plans && d.pending_plans.length > 0) {{
                    d.pending_plans.forEach(p => {{
                        planHtml += `
                        <div class="admin-req-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                <div>
                                    <strong style="color: #38bdf8; font-size: 15px;">${{p.email}}</strong>
                                    <div style="color: #ffffff; font-weight: 700; font-size: 13px; margin-top: 2px;">${{p.plan}} (${{p.days}} Days)</div>
                                    <div style="color: #fde047; font-family: monospace; font-size: 13px; margin-top: 4px;">UTR: ${{p.utr}}</div>
                                </div>
                                <div style="color: #34d399; font-size: 18px; font-weight: 800;">₹${{Number(p.amount).toLocaleString()}}</div>
                            </div>
                            <div style="margin-top: 10px;">
                                <button class="btn-approve" onclick="approvePlan('${{p.id}}', '${{p.email}}', '${{p.plan}}', ${{p.days}})">✅ Activate Plan</button>
                                <button class="btn-reject" onclick="rejectPlan('${{p.id}}')">❌ Reject</button>
                            </div>
                        </div>`;
                    }});
                }} else {{
                    planHtml = '<div style="color: #64748b; padding: 18px; text-align: center;">No pending plan subscriptions.</div>';
                }}
                document.getElementById('adminPendingPlansList').innerHTML = planHtml;

                let uHtml = '';
                if (d.users) {{
                    for (const [em, u] of Object.entries(d.users)) {{
                        uHtml += `
                        <div class="wallet-card">
                            <div>
                                <strong style="color: #f8fafc; font-size: 14px;">${{em}}</strong>
                                <div style="color: #94a3b8; font-size: 11px; margin-top: 2px;">UID: ${{u.uid || '--------'}} • INR: ₹${{Number(u.inr_balance || 0).toFixed(2)}} • USDT: ${{Number(u.balance || 0).toFixed(2)}}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: #38bdf8; font-weight: 800;">${{u.plan || 'NONE'}}</div>
                                <span class="status-badge" style="background:${{u.status === 'ACTIVE' ? '#064e3b':'#1e293b'}}; color:${{u.status === 'ACTIVE' ? '#34d399':'#94a3b8'}}">${{u.status || 'INACTIVE'}}</span>
                            </div>
                        </div>`;
                    }}
                }}
                document.getElementById('adminUsersList').innerHTML = uHtml;

            }} catch(e) {{
                console.error(e);
            }}
        }}

        async function approveDeposit(reqId, email, amtInr) {{
            if (!confirm('Approve ₹' + amtInr + ' INR for ' + email + '?')) return;
            const res = await fetch('/api/admin/approve-deposit', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id: reqId, email: email, amount_inr: amtInr }})
            }});
            const data = await res.json();
            alert(data.message);
            loadAdminPanelData();
        }}

        async function rejectDeposit(reqId) {{
            if (!confirm('Reject this deposit request?')) return;
            const res = await fetch('/api/admin/reject-deposit', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id: reqId }})
            }});
            const data = await res.json();
            alert(data.message);
            loadAdminPanelData();
        }}

        async function approvePlan(reqId, email, planName, days) {{
            if (!confirm('Activate ' + planName + ' for ' + email + '?')) return;
            const res = await fetch('/api/admin/approve-plan', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id: reqId, email: email, plan: planName, days: days }})
            }});
            const data = await res.json();
            alert(data.message);
            loadAdminPanelData();
        }}

        async function rejectPlan(reqId) {{
            if (!confirm('Reject this plan request?')) return;
            const res = await fetch('/api/admin/reject-plan', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id: reqId }})
            }});
            const data = await res.json();
            alert(data.message);
            loadAdminPanelData();
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
            const email = document.getElementById('loginEmail').value.trim().toLowerCase();
            const pass = document.getElementById('loginPassword').value.trim();
            if (!email || !pass) {{ alert('Please enter Email and Password'); return; }}
            const res = await fetch('/api/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_user_email', email);
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('signingInOverlay').style.display = 'flex';
                setTimeout(() => {{
                    window.location.reload();
                }}, 1100);
            }} else {{
                alert(data.message);
            }}
        }}

        async function handleDirectSignup() {{
            const email = document.getElementById('signupEmail').value.trim().toLowerCase();
            const pass = document.getElementById('signupPassword').value.trim();
            if (!email || !pass) {{ alert('Please enter Email and Password'); return; }}
            const res = await fetch('/api/signup', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ email: email, password: pass }})
            }});
            const data = await res.json();
            if (data.status === 'success') {{
                localStorage.setItem('cryptobot_user_email', email);
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('signingInOverlay').style.display = 'flex';
                setTimeout(() => {{
                    window.location.reload();
                }}, 1100);
            }} else {{
                alert(data.message);
                switchAuthTab('login');
                document.getElementById('loginEmail').value = email;
                document.getElementById('loginPassword').value = '';
            }}
        }}

        function logoutUser() {{
            localStorage.removeItem('cryptobot_user_email');
            window.location.reload();
        }}

        function openProfileModal() {{ document.getElementById('profileModal').style.display = 'flex'; }}
        function closeProfileModal() {{ document.getElementById('profileModal').style.display = 'none'; }}
    </script>
</body>
</html>
"""

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/admin/data':
            db = load_db()
            pending_deposits = [w for w in db.get("wallet_activity", []) if "Pending" in w.get("status", "")]
            pending_plans = [p for p in db.get("payments", []) if p.get("status", "") == "Pending"]
            res = {
                "pending_deposits": pending_deposits,
                "pending_plans": pending_plans,
                "users": db.get("users", {})
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        try:
            html = get_html()
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except Exception as e:
            print("Error serving GET:", str(e))
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Server Error: {str(e)}".encode('utf-8'))

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

            if email == 'admin@cryptobot.com':
                if password == 'admin123':
                    res = {"status": "success", "message": "Admin Login successful!", "plan_status": "ACTIVE"}
                else:
                    res = {"status": "error", "message": "❌ Galat Admin Password! Dubara check karein."}
            else:
                users = db.get("users", {})
                user = users.get(email)

                if not user:
                    res = {"status": "error", "message": "❌ Yeh email registered nahi hai! Kripya pehle Sign Up karein."}
                elif user.get("password") != password:
                    res = {"status": "error", "message": "❌ Galat Password! Dubara check karein."}
                else:
                    res = {"status": "success", "message": "Login successful!", "plan_status": user.get("status", "INACTIVE")}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/signup':
            email = payload.get('email', '').strip().lower()
            password = payload.get('password', '').strip()
            db = load_db()
            users = db.setdefault("users", {})

            if email in users or email == 'admin@cryptobot.com':
                res = {"status": "error", "message": "⚠️ Yeh email pehle se registered hai! Kripya Login karein."}
            else:
                uid_str = get_user_uid(email)
                users[email] = {
                    "password": password,
                    "status": "ACTIVE",
                    "plan": "NONE",
                    "days_left": 0,
                    "created_on": str(datetime.now().date()),
                    "balance": 0.0,
                    "principal": 0.0,
                    "total_profit": 0.0,
                    "inr_balance": (8000.0 if email == 'mdm906581@gmail.com' else 0.0),
                    "is_admin": False,
                    "uid": uid_str,
                    "trades": [],
                    "wallet_activity": [],
                    "profile": {
                        "name": email.split('@')[0],
                        "phone": "",
                        "country": "India 🇮🇳"
                    }
                }
                if email == 'mdm906581@gmail.com':
                    db.setdefault("wallet_activity", []).insert(0, {
                        "id": f"dep_{int(time.time())}",
                        "email": email,
                        "sender_name": "Modassir",
                        "date": datetime.now().strftime("%d %b %Y"),
                        "time": datetime.now().strftime("%I:%M %p").lower(),
                        "type": "INR Deposit (Bank Transfer)",
                        "category": "DEPOSIT",
                        "amount_inr": 8000.0,
                        "utr": "123456789012",
                        "status": "Completed"
                    })
                save_db(db)
                res = {"status": "success", "message": "🎉 Account ban gaya! Logging you in..."}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/user-status':
            email = payload.get('email', '').strip().lower()
            db = load_db()
            
            user_activity = [w for w in db.get("wallet_activity", []) if w.get("email", "").lower() == email]

            if email == 'admin@cryptobot.com':
                user = {
                    "plan": "PREMIUM",
                    "days_left": 365,
                    "balance": db.get("balance", 1000.0),
                    "principal": 1000.0,
                    "total_profit": 3.00,
                    "inr_balance": db.get("inr_balance", 0.0),
                    "is_admin": True,
                    "uid": get_user_uid("admin@cryptobot.com")
                }
                user_activity = db.get("wallet_activity", [])
                user_trades = db.get("trades", [])
            else:
                user = db.get("users", {}).get(email, {
                    "plan": "NONE",
                    "days_left": 0,
                    "balance": 0.0,
                    "principal": 0.0,
                    "total_profit": 0.0,
                    "inr_balance": (8000.0 if email == 'mdm906581@gmail.com' else 0.0),
                    "is_admin": False,
                    "uid": get_user_uid(email)
                })
                user_trades = user.get("trades", [])

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "user": user,
                "trades": user_trades,
                "activity": user_activity
            }).encode('utf-8'))

        elif self.path == '/api/deposit-inr':
            db = load_db()
            email = payload.get('email', 'User')
            sender_name = payload.get('sender_name', '')
            amount_inr = float(payload.get('amount_inr', 0.0))
            utr = payload.get('utr', 'N/A')
            now = datetime.now()

            req_id = f"dep_{int(time.time())}"
            new_dep = {
                "id": req_id,
                "email": email,
                "sender_name": sender_name,
                "date": now.strftime("%d %b %Y"),
                "time": now.strftime("%I:%M %p").lower(),
                "type": f"INR Deposit ({sender_name})",
                "category": "DEPOSIT",
                "amount_inr": amount_inr,
                "utr": utr,
                "status": "Pending Verification"
            }
            db.setdefault("wallet_activity", []).insert(0, new_dep)
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            msg = f"✅ Payment Proof Submitted!\n\nAmount: ₹{amount_inr:,.2f}\nUTR: {utr}\nFinance team verify karke aapke BOT Wallet me funds add kar degi."
            self.wfile.write(json.dumps({"status": "success", "message": msg}).encode('utf-8'))

        elif self.path == '/api/admin/approve-deposit':
            req_id = payload.get('id')
            email = payload.get('email', '').strip().lower()
            amount_inr = float(payload.get('amount_inr', 0.0))
            db = load_db()

            if email in db.get("users", {}):
                db["users"][email]["inr_balance"] = db["users"][email].get("inr_balance", 0.0) + amount_inr

            for w in db.get("wallet_activity", []):
                if w.get("id") == req_id:
                    w["status"] = "Completed"
                    break

            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"✅ Approved! ₹{amount_inr:,.2f} INR credited to {email}'s wallet."}).encode('utf-8'))

        elif self.path == '/api/admin/reject-deposit':
            req_id = payload.get('id')
            db = load_db()
            for w in db.get("wallet_activity", []):
                if w.get("id") == req_id:
                    w["status"] = "Rejected"
                    break
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "❌ Deposit request rejected."}).encode('utf-8'))

        elif self.path == '/api/verify-plan-utr':
            db = load_db()
            email = payload.get('email', 'User')
            utr = payload.get('utr', 'N/A')
            plan_id = payload.get('plan_id', 'STANDARD')
            plan_name = payload.get('plan_name', 'STANDARD PACKAGE')
            price = payload.get('price', 999)
            days = payload.get('days', 30)

            plan_req_id = f"plan_{int(time.time())}"
            db.setdefault("payments", []).append({
                "id": plan_req_id,
                "email": email,
                "plan_id": plan_id,
                "plan": plan_name,
                "amount": price,
                "days": days,
                "utr": utr,
                "status": "Pending",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            msg = f"🎉 Plan Subscription Submitted!\n\n{plan_name} (₹{price:,})\nUTR: {utr}\nAdmin approval ke baad turant activate ho jayega."
            self.wfile.write(json.dumps({"status": "success", "message": msg}).encode('utf-8'))

        elif self.path == '/api/admin/approve-plan':
            req_id = payload.get('id')
            email = payload.get('email', '')
            days = int(payload.get('days', 30))
            db = load_db()

            expiry = (datetime.now() + timedelta(days=days)).strftime("%d %b %Y")
            if email in db.get("users", {}):
                db["users"][email]["status"] = "ACTIVE"
                db["users"][email]["days_left"] = days
                db["users"][email]["expires_on"] = expiry

            for p in db.get("payments", []):
                if p.get("id") == req_id:
                    p["status"] = "Completed"
                    break

            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"✅ Plan activated for {email} ({days} days)!"}).encode('utf-8'))

        elif self.path == '/api/admin/reject-plan':
            req_id = payload.get('id')
            db = load_db()
            for p in db.get("payments", []):
                if p.get("id") == req_id:
                    p["status"] = "Rejected"
                    break
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "❌ Plan request rejected."}).encode('utf-8'))

        elif self.path == '/api/withdraw-inr':
            amount_inr = float(payload.get('amount_inr', 0.0))
            destination = payload.get('destination', '').strip()
            email = payload.get('email', '').strip().lower()
            db = load_db()

            if amount_inr < MIN_WITHDRAW_INR:
                res = {"status": "error", "message": f"❌ Minimum withdrawal ₹{MIN_WITHDRAW_INR:,.0f} INR hona chahiye!"}
            elif amount_inr > MAX_WITHDRAW_INR:
                res = {"status": "error", "message": f"❌ Maximum withdrawal ₹{MAX_WITHDRAW_INR:,.0f} INR tak hi allow hai!"}
            elif not destination:
                res = {"status": "error", "message": "❌ Kripya Destination UPI ID ya Bank Details daalein!"}
            else:
                user = db.get("users", {}).get(email, {})
                user_bal = user.get("balance", 0.0) if email != 'admin@cryptobot.com' else db.get("balance", 1000.0)
                usdt_needed = amount_inr / USDT_INR_RATE
                
                if user_bal < usdt_needed:
                    res = {"status": "error", "message": f"❌ Insufficient Balance! ₹{amount_inr:,.0f} nikaalne ke liye {usdt_needed:.2f} USDT chahiye."}
                else:
                    if email == 'admin@cryptobot.com':
                        db["balance"] -= usdt_needed
                    else:
                        db["users"][email]["balance"] -= usdt_needed
                        db["users"][email]["principal"] = max(0.0, db["users"][email].get("principal", 0.0) - usdt_needed)

                    now = datetime.now()
                    db.setdefault("wallet_activity", []).insert(0, {
                        "id": f"with_{int(time.time())}",
                        "email": email,
                        "date": now.strftime("%d %b %Y"),
                        "time": now.strftime("%I:%M %p").lower(),
                        "type": "INR Withdrawal",
                        "category": "WITHDRAWAL",
                        "amount_inr": -amount_inr,
                        "destination": destination,
                        "status": "Completed"
                    })
                    save_db(db)
                    res = {"status": "success", "message": f"✅ ₹{amount_inr:,.0f} ka withdrawal request confirm ho gaya!\n{destination} par transfer process start ho gaya hai."}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/convert':
            amount = float(payload.get('amount', 0.0))
            direction = payload.get('direction', 'INR_TO_USDT')
            email = payload.get('email', '').strip().lower()
            db = load_db()
            
            user = db.get("users", {}).get(email)
            if not user and email != 'admin@cryptobot.com':
                res = {"status": "error", "message": "User not found!"}
            else:
                is_admin = (email == 'admin@cryptobot.com')
                user_inr = db.get("inr_balance", 0.0) if is_admin else user.get("inr_balance", 0.0)
                user_usdt = db.get("balance", 1000.0) if is_admin else user.get("balance", 0.0)

                if direction == 'INR_TO_USDT':
                    if user_inr < amount:
                        res = {"status": "error", "message": f"Insufficient INR balance! (Available: ₹{user_inr:,.2f})"}
                    else:
                        usdt_received = round(amount / USDT_INR_RATE, 4)
                        if is_admin:
                            db["inr_balance"] -= amount
                            db["balance"] += usdt_received
                        else:
                            db["users"][email]["inr_balance"] -= amount
                            db["users"][email]["balance"] = db["users"][email].get("balance", 0.0) + usdt_received
                            db["users"][email]["principal"] = db["users"][email].get("principal", 0.0) + usdt_received

                        db.setdefault("wallet_activity", []).insert(0, {
                            "id": f"conv_{int(time.time())}",
                            "email": email,
                            "date": datetime.now().strftime("%d %b %Y"),
                            "time": datetime.now().strftime("%I:%M %p").lower(),
                            "type": f"Converted ₹{amount:,.2f} INR to USDT",
                            "category": "CONVERSION",
                            "amount_inr": -amount,
                            "status": "Completed"
                        })
                        save_db(db)
                        res = {"status": "success", "message": f"🎉 Converted ₹{amount:,.2f} INR into {usdt_received:.4f} USDT successfully!"}
                else:
                    if user_usdt < amount:
                        res = {"status": "error", "message": f"Insufficient USDT balance! (Available: {user_usdt:.4f} USDT)"}
                    else:
                        inr_received = round(amount * USDT_INR_RATE, 2)
                        if is_admin:
                            db["balance"] -= amount
                            db["inr_balance"] += inr_received
                        else:
                            db["users"][email]["balance"] -= amount
                            db["users"][email]["principal"] = max(0.0, db["users"][email].get("principal", 0.0) - amount)
                            db["users"][email]["inr_balance"] = db["users"][email].get("inr_balance", 0.0) + inr_received

                        db.setdefault("wallet_activity", []).insert(0, {
                            "id": f"conv_{int(time.time())}",
                            "email": email,
                            "date": datetime.now().strftime("%d %b %Y"),
                            "time": datetime.now().strftime("%I:%M %p").lower(),
                            "type": f"Converted {amount:.4f} USDT to INR",
                            "category": "CONVERSION",
                            "amount_inr": inr_received,
                            "status": "Completed"
                        })
                        save_db(db)
                        res = {"status": "success", "message": f"🎉 Converted {amount:.4f} USDT into ₹{inr_received:,.2f} INR successfully!"}

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

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    print(f"🚀 trade.ai server active on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopped")
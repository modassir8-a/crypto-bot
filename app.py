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
USDT_INR_RATE = 91.50

MIN_WITHDRAW_INR = 1000.0
MAX_WITHDRAW_INR = 10000.0

ADMIN_COMMISSION_PCT = 0.15
USER_SHARE_PCT = 0.85

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

def load_db():
    default_expiry = (datetime.now() + timedelta(days=30)).strftime("%d %b %Y")
    real_initial_activity = [
        {"date": "04 Sep 2026", "time": "09:00 pm", "type": "Initial Bot Investment", "category": "DEPOSIT", "amount": 1000.0, "status": "Completed"}
    ]
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            if "inr_balance" not in data:
                data["inr_balance"] = 0.0
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
        "inr_balance": 0.0,
        "daily_trades_taken": 0,
        "last_date": str(datetime.now().date()),
        "users": {
            "admin@cryptobot.com": {
                "password": "admin123",
                "status": "ACTIVE",
                "plan": "STANDARD",
                "expires_on": default_expiry,
                "days_left": 30,
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
    data = load_db()
    balance = data.get("balance", 1000.0)
    inr_balance = data.get("inr_balance", 0.0)
    profit = balance - 1000.0
    profit_sign = "+" if profit >= 0 else ""

    # Trades HTML
    trades_html = ""
    for t in reversed(data.get("trades", [])):
        c = t.get('coin', '').replace('/', '-').upper()
        total_p = t.get('profit', 1.50)
        admin_s = total_p * ADMIN_COMMISSION_PCT
        user_s = total_p * USER_SHARE_PCT
        open_p = t.get('entry_price', 0.0)
        close_p = t.get('target_price', 0.0)
        time_s = t.get('time', '')

        trades_html += f"""
        <div class="trade-card-split" data-coin="{c}">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="font-size: 16px;">💎</span>
                <strong style="color: #f8fafc; font-size: 15px;">{c} ---</strong>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; margin-bottom: 14px;">
                <div>
                    <div style="color: #94a3b8; font-size: 12px;">Open Price: <span style="color:#ffffff;">${open_p}</span></div>
                    <div style="color: #34d399; font-weight: 700; margin-top: 4px;">Total PnL: {total_p:.2f} PnL</div>
                </div>
                <div style="text-align: right;">
                    <div style="color: #94a3b8; font-size: 12px;">Close Price: <span style="color:#ffffff;">${close_p}</span></div>
                    <div style="color: #38bdf8; font-weight: 700; margin-top: 4px;">Your PnL: {user_s:.2f} PnL</div>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #16233b; padding-top: 10px;">
                <span style="font-size: 11px; color: #64748b;">{time_s}</span>
                <button class="btn-view-split" onclick="openProfitSplitModal({user_s:.6f}, {admin_s:.6f})">View</button>
            </div>
        </div>
        """

    # Separate Personal Histories for Deposit, Withdraw, Conversion
    deposits_html = ""
    withdrawals_html = ""
    conversions_html = ""
    all_wallet_html = ""
    total_invested = 0.0
    total_withdrawn = 0.0

    for w in data.get("wallet_activity", []):
        amt = w.get("amount", 0.0)
        cat = w.get("category", "")
        if not cat:
            cat = "DEPOSIT" if amt >= 0 else "WITHDRAWAL"

        if cat == "DEPOSIT" or amt >= 0 and "Withdrawal" not in w.get("type", "") and "Converted" not in w.get("type", ""):
            total_invested += abs(amt)
        elif cat == "WITHDRAWAL" or "Withdrawal" in w.get("type", ""):
            total_withdrawn += abs(amt)

        amt_str = f"+${amt:.2f}" if amt >= 0 else f"-${abs(amt):.2f}"
        amt_color = "#34d399" if amt >= 0 else "#ef4444"
        type_color = "#38bdf8" if amt >= 0 else "#f87171"

        card_markup = f"""
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
        all_wallet_html += card_markup

        if "Converted" in w.get("type", "") or cat == "CONVERSION":
            conversions_html += card_markup
        elif "Withdrawal" in w.get("type", "") or cat == "WITHDRAWAL":
            withdrawals_html += card_markup
        else:
            deposits_html += card_markup

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
        .status-badge {{ background: #064e3b; color: #34d399; border: 1px solid #059669; padding: 4px 12px; border-radius: 16px; font-size: 11px; font-weight: 700; display: inline-block; margin-top: 6px; }}
        .overview-summary {{ background: #0c1527; border: 1px solid #16233b; border-radius: 18px; padding: 18px; margin-bottom: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; text-align: center; }}
        .summary-label {{ font-size: 11px; color: #94a3b8; font-weight: 600; text-transform: uppercase; }}
        .summary-val {{ font-size: 18px; font-weight: 800; margin-top: 4px; }}

        /* BOT Wallet Action Bar - Only 3 Options */
        .wallet-actions-bar {{ display: flex; gap: 10px; margin-bottom: 24px; }}
        .wallet-action-pill {{ flex: 1; text-align: center; background: #0c1527; border: 1px solid #16233b; border-radius: 20px; padding: 10px 14px; color: #94a3b8; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }}
        .wallet-action-pill.active {{ background: #38bdf8; color: #060b14; }}
        
        .notice-box {{ background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 14px; padding: 14px 18px; margin-bottom: 20px; color: #94a3b8; font-size: 12px; line-height: 1.5; text-align: left; }}
        .step-indicator {{ display: flex; align-items: center; gap: 10px; margin-bottom: 18px; font-size: 12px; font-weight: 700; color: #64748b; }}
        .step-circle {{ width: 22px; height: 22px; border-radius: 50%; background: #0284c7; color: white; display: flex; align-items: center; justify-content: center; font-size: 11px; }}
        .payment-method-card {{ background: #0c1527; border: 1px solid #16233b; border-radius: 16px; padding: 20px; margin-bottom: 14px; text-align: left; }}

        .swap-box {{ background: #070d18; border: 1px solid #16233b; border-radius: 16px; padding: 18px; margin-bottom: 12px; }}
        .swap-label-row {{ display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 10px; font-weight: 600; }}
        .swap-input-row {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
        .swap-input {{ background: transparent; border: none; color: #ffffff; font-size: 26px; font-weight: 800; width: 60%; outline: none; }}
        .max-pill {{ background: rgba(56,189,248,0.15); border: 1px solid #0284c7; color: #38bdf8; padding: 4px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; }}
        .curr-pill {{ background: #0c1527; border: 1px solid #1e293b; color: #ffffff; padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 6px; }}
        .swap-divider-btn {{ width: 40px; height: 40px; border-radius: 50%; background: #131b2e; border: 1px solid #1e293b; color: #38bdf8; display: flex; justify-content: center; align-items: center; font-size: 16px; margin: -6px auto; cursor: pointer; position: relative; z-index: 2; transition: 0.2s; }}
        .calc-breakdown {{ padding: 16px 4px; border-top: 1px solid #16233b; margin-top: 14px; }}
        .breakdown-row {{ display: flex; justify-content: space-between; font-size: 12px; color: #94a3b8; margin-bottom: 8px; }}

        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(6,11,20,0.92); justify-content: center; align-items: center; z-index: 100; padding: 16px; }}
        .modal-content {{ background: #0c1527; border: 1px solid #1e293b; border-radius: 20px; width: 100%; max-width: 420px; padding: 24px; text-align: center; }}
        .input-box {{ width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #1e293b; background: #060b14; color: white; margin-bottom: 10px; font-size: 14px; }}
        .btn-action {{ background: #0284c7; color: #ffffff; border: none; width: 100%; padding: 12px; border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer; }}
        .btn-close {{ background: transparent; color: #64748b; border: none; margin-top: 10px; cursor: pointer; font-size: 13px; }}

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
                    <span id="headerBalText">{balance:.2f} USDT</span>
                    <span class="green-dot"></span>
                </div>
                <button class="avatar-btn" id="avatarBtn" onclick="openProfileModal()">M</button>
            </div>
        </div>

        <!-- Navigation Bar -->
        <div class="nav-bar">
            <button class="nav-item" onclick="showTab('tradeLogs')">Home</button>
            <button class="nav-item" onclick="showTab('tradeLogs')">Strategies</button>
            <button id="navPlans" class="nav-item" onclick="showTab('plans')">Plans</button>
            <button id="navTradeLogs" class="nav-item active" onclick="showTab('tradeLogs')">Trade Logs</button>
            <button id="navBotWallet" class="nav-item" onclick="showTab('botWallet')">BOT Wallet</button>
            <button id="navOverview" class="nav-item" onclick="showTab('overview')">Overview</button>
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
                        <div class="stat-col-val" id="dispPrincipal">1000.00 <span style="font-size: 10px; color:#64748b;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">E. PNL ▾</div>
                        <div class="stat-col-val blue" id="dispEpnl">{profit_sign}{profit:.2f}</div>
                    </div>
                    <div>
                        <div class="stat-col-title">PNL ▾</div>
                        <div class="stat-col-val blue" id="dispPnl">{profit_sign}{profit:.2f} <span style="font-size: 10px;">USDT</span></div>
                    </div>
                    <div>
                        <div class="stat-col-title">CURRENT</div>
                        <div class="stat-col-val" id="dispCurrent">{balance:.2f} <span style="font-size: 10px; color:#64748b;">USDT</span></div>
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

                <div id="tradesListContainer">
                    {trades_html}
                </div>

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

        <!-- TAB 3: BOT Wallet View (3 Options: DEPOSIT, WITHDRAW, CONVERSION with Personal Histories) -->
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
                        <div style="font-size: 17px; font-weight: 800; color: #38bdf8;" id="walletUsdtBalDisplay">{balance:.2f}</div>
                    </div>
                </div>
            </div>

            <!-- Action Pills Bar - Strictly 3 Options -->
            <div class="wallet-actions-bar">
                <button id="pillDeposit" class="wallet-action-pill" onclick="switchWalletTab('deposit')">↙ DEPOSIT • INR ▾</button>
                <button id="pillWithdraw" class="wallet-action-pill" onclick="switchWalletTab('withdraw')">↗ WITHDRAW • INR ▾</button>
                <button id="pillConversion" class="wallet-action-pill active" onclick="switchWalletTab('conversion')">⇄ CONVERSION</button>
            </div>

            <!-- Sub-tab 1: Deposit INR (Form + Personal Deposit History) -->
            <div id="walletSubDeposit" style="display: none;">
                <div class="step-indicator">
                    <span class="step-circle">1</span> <span>PAYMENT DETAILS</span> ────── <span class="step-circle" style="background:#1e293b; color:#94a3b8;">2</span> <span>SUBMIT PROOF</span>
                </div>

                <h2 style="font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Deposit INR</h2>
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 18px; line-height: 1.4;">
                    Choose your preferred payment method to fund your bot trading wallet. All payments are manually verified for security purposes.
                </p>

                <div class="notice-box">
                    ⚠️ For smooth and fast approval, please transfer funds only from the bank account used during your KYC verification.
                </div>

                <div class="payment-method-card">
                    <div style="text-align: center; margin: 12px 0;">
                        <div style="background: white; padding: 8px; border-radius: 12px; display: inline-block;">
                            <img id="depositQrImg" src="" alt="UPI QR Code" style="width: 160px; height: 160px; display: block;">
                        </div>
                        <div style="font-family: monospace; color: #38bdf8; font-size: 13px; margin-top: 8px;">UPI ID: {MY_UPI_ID}</div>
                    </div>
                    <a id="depositIntentBtn" href="#" class="pill-btn-wide" style="background: #0284c7; color: white; text-decoration: none; font-weight: 700; margin-bottom: 14px; text-align: center;">📱 Open Google Pay / PhonePe (Pay ₹999)</a>
                    <input id="depositUtrInput" type="text" class="input-box" placeholder="Enter 12-digit UTR No. after payment">
                    <button class="btn-action" style="background: #10b981;" onclick="submitDepositUtr()">Submit Proof & Verify</button>
                </div>

                <!-- Personal Deposit History -->
                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Deposit History</h3>
                    <div id="personalDepositList">
                        {deposits_html}
                    </div>
                    {"" if deposits_html else '<div class="empty-state-box"><div class="empty-icon">📥</div><div class="empty-text">No Deposit History found</div></div>'}
                </div>
            </div>

            <!-- Sub-tab 2: Withdraw INR (Form + Personal Withdrawal History) -->
            <div id="walletSubWithdraw" style="display: none;">
                <h2 style="font-size: 22px; font-weight: 800; color: #ffffff; margin-bottom: 6px;">Withdraw Funds (INR)</h2>
                <p style="font-size: 12px; color: #94a3b8; margin-bottom: 16px;">Request an instant withdrawal in Indian Rupees directly to your verified Bank Account or UPI.</p>
                
                <div class="notice-box" style="border-color: #0284c7; background: rgba(2, 132, 199, 0.08); color: #38bdf8;">
                    ℹ️ <strong>Withdrawal Policy:</strong> Minimum ₹1,000 INR • Maximum ₹10,000 INR per transaction • Payout via 24x7 IMPS / UPI
                </div>

                <div class="payment-method-card">
                    <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Withdrawal Amount (₹ INR)</label>
                    <input id="withdrawAmtInr" type="number" class="input-box" placeholder="Min ₹1,000 - Max ₹10,000" min="1000" max="10000">

                    <label style="font-size: 12px; color: #94a3b8; margin-bottom: 6px; display: block; font-weight: 700;">Destination UPI ID / Bank Account Details</label>
                    <input id="withdrawDest" type="text" class="input-box" placeholder="e.g. yourname@okaxis or A/C No + IFSC">
                    
                    <button class="btn-action" style="background: #ef4444; padding: 14px; font-size: 15px; margin-top: 6px;" onclick="submitWithdrawalInr()">Request Withdrawal (INR)</button>
                </div>

                <!-- Personal Withdrawal History -->
                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Withdrawal History</h3>
                    <div id="personalWithdrawList">
                        {withdrawals_html}
                    </div>
                    {"" if withdrawals_html else '<div class="empty-state-box"><div class="empty-icon">📤</div><div class="empty-text">No Withdrawal History found</div></div>'}
                </div>
            </div>

            <!-- Sub-tab 3: Conversion (Form + Personal Conversion History) -->
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

                <div class="payment-method-card" style="padding: 24px;">
                    <div class="swap-box">
                        <div class="swap-label-row">
                            <span>From</span>
                            <span>Available: <span id="fromAvailableDisplay">{balance:.4f} USDT</span></span>
                        </div>
                        <div class="swap-input-row">
                            <input id="fromAmountInput" type="number" class="swap-input" placeholder="0.00" value="0.00" oninput="handleSwapCalculate()">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span class="max-pill" onclick="handleMaxClick()">Max</span>
                                <div class="curr-pill" id="fromCurrPill">USDT ▾</div>
                            </div>
                        </div>
                    </div>

                    <button class="swap-divider-btn" onclick="toggleSwapDirection()" title="Swap Currencies">⇅</button>

                    <div class="swap-box">
                        <div class="swap-label-row">
                            <span>To</span>
                            <span>Available: <span id="toAvailableDisplay">₹ {inr_balance:.4f} INR</span></span>
                        </div>
                        <div class="swap-input-row">
                            <input id="toAmountInput" type="text" class="swap-input" placeholder="0" value="0" readonly>
                            <div class="curr-pill" id="toCurrPill">INR ▾</div>
                        </div>
                    </div>

                    <div class="calc-breakdown">
                        <div class="breakdown-row">
                            <span><span id="rateDirectionLabel">USDT → INR</span> <span style="background:#064e3b; color:#34d399; font-size:10px; padding:2px 6px; border-radius:4px; margin-left:4px;">● Live</span></span>
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
                            <strong style="color: #38bdf8; font-size: 16px;" id="receiveSummaryText">0 INR</strong>
                        </div>
                    </div>

                    <button class="btn-action" style="background: linear-gradient(90deg, #10b981, #059669); margin-top: 14px; padding: 14px; font-size: 16px;" onclick="executeConversion()">Convert</button>
                </div>

                <!-- Personal Conversion History -->
                <div style="margin-top: 28px;">
                    <h3 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 14px;">Conversion History</h3>
                    <div id="personalConversionList">
                        {conversions_html}
                    </div>
                    {"" if conversions_html else '<div class="empty-state-box"><div class="empty-icon">🔄</div><div class="empty-text">No Conversion History found</div></div>'}
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
                    <div class="summary-label">Total Bot Investment</div>
                    <div class="summary-val" style="color: #34d399;">${total_invested:.2f} USDT</div>
                </div>
                <div>
                    <div class="summary-label">Total Withdrawal</div>
                    <div class="summary-val" style="color: #f87171;">-${total_withdrawn:.2f} USDT</div>
                </div>
            </div>

            <div id="overviewListContainer">
                {all_wallet_html}
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

    <!-- Dynamic Plan Checkout Modal -->
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

    <script>
        const CURRENT_RATE = {USDT_INR_RATE};
        const MIN_WITHDRAW = {MIN_WITHDRAW_INR};
        const MAX_WITHDRAW = {MAX_WITHDRAW_INR};
        const UPI_ID = "{MY_UPI_ID}";
        let currentUsdtBal = {balance};
        let currentInrBal = {inr_balance};
        let swapDirection = 'USDT_TO_INR';
        let isBalanceHidden = false;

        let selectedPlanId = 'STANDARD';
        let selectedPlanPrice = 999;
        let selectedPlanDays = 30;
        let selectedPlanName = 'STANDARD PACKAGE';

        const origValues = {{
            principal: '1000.00 USDT',
            epnl: '{profit_sign}{profit:.2f}',
            pnl: '{profit_sign}{profit:.2f} USDT',
            current: '{balance:.2f} USDT',
            header: '{balance:.2f} USDT'
        }};

        window.addEventListener('DOMContentLoaded', () => {{
            const saved = localStorage.getItem('cryptobot_user_email');
            if (saved) {{
                document.getElementById('authOverlay').style.display = 'none';
                document.getElementById('mainDashboard').style.display = 'block';
                const initial = saved.charAt(0).toUpperCase();
                document.getElementById('avatarBtn').innerText = initial;
                checkUserPlanStatus(saved);
            }}
        }});

        async function checkUserPlanStatus(email) {{
            try {{
                const res = await fetch('/api/user-status', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ email: email }})
                }});
                const data = await res.json();
                if (data.status === 'success' && data.user) {{
                    const activePlan = data.user.plan || 'STANDARD';
                    const daysLeft = data.user.days_left || 30;
                    
                    const btn = document.getElementById('planBtn_' + activePlan);
                    if (btn) {{
                        btn.innerText = 'PLAN ACTIVE • ' + daysLeft + 'D LEFT';
                        btn.classList.add('active-badge');
                        btn.onclick = null;
                    }}
                }}
            }} catch(e) {{}}
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
            
            document.getElementById('navTradeLogs').classList.remove('active');
            document.getElementById('navPlans').classList.remove('active');
            document.getElementById('navBotWallet').classList.remove('active');
            document.getElementById('navOverview').classList.remove('active');

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
                updateDepositQr(999);
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

        function updateDepositQr(amount) {{
            const upiUrl = 'upi://pay?pa=' + UPI_ID + '&pn=trade.ai&am=' + amount + '&cu=INR&tn=Deposit';
            const qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=' + encodeURIComponent(upiUrl);
            document.getElementById('depositQrImg').src = qrUrl;
            document.getElementById('depositIntentBtn').href = upiUrl;
        }}

        function openPaymentModal() {{
            showTab('plans');
        }}
        function closePaymentModal() {{
            document.getElementById('payModal').style.display = 'none';
        }}

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
                body: JSON.stringify({{ amount_inr: amtInr, destination: dest }})
            }});
            const data = await res.json();
            alert(data.message);
            if (data.status === 'success') {{
                window.location.reload();
            }}
        }}

        function handleSwapCalculate() {{
            const val = parseFloat(document.getElementById('fromAmountInput').value) || 0;
            if (swapDirection === 'USDT_TO_INR') {{
                const res = val * CURRENT_RATE;
                document.getElementById('toAmountInput').value = res.toFixed(2);
                document.getElementById('receiveSummaryText').innerText = res.toFixed(2) + ' INR';
            }} else {{
                const res = val / CURRENT_RATE;
                document.getElementById('toAmountInput').value = res.toFixed(4);
                document.getElementById('receiveSummaryText').innerText = res.toFixed(4) + ' USDT';
            }}
        }}

        function handleMaxClick() {{
            if (swapDirection === 'USDT_TO_INR') {{
                document.getElementById('fromAmountInput').value = currentUsdtBal.toFixed(2);
            }} else {{
                document.getElementById('fromAmountInput').value = currentInrBal.toFixed(2);
            }}
            handleSwapCalculate();
        }}

        function toggleSwapDirection() {{
            if (swapDirection === 'USDT_TO_INR') {{
                swapDirection = 'INR_TO_USDT';
                document.getElementById('fromCurrPill').innerText = 'INR ▾';
                document.getElementById('toCurrPill').innerText = 'USDT ▾';
                document.getElementById('fromAvailableDisplay').innerText = '₹ ' + currentInrBal.toFixed(2) + ' INR';
                document.getElementById('toAvailableDisplay').innerText = currentUsdtBal.toFixed(4) + ' USDT';
                document.getElementById('rateDirectionLabel').innerText = 'INR → USDT';
            }} else {{
                swapDirection = 'USDT_TO_INR';
                document.getElementById('fromCurrPill').innerText = 'USDT ▾';
                document.getElementById('toCurrPill').innerText = 'INR ▾';
                document.getElementById('fromAvailableDisplay').innerText = currentUsdtBal.toFixed(4) + ' USDT';
                document.getElementById('toAvailableDisplay').innerText = '₹ ' + currentInrBal.toFixed(2) + ' INR';
                document.getElementById('rateDirectionLabel').innerText = 'USDT → INR';
            }}
            document.getElementById('fromAmountInput').value = '0.00';
            document.getElementById('toAmountInput').value = '0';
            document.getElementById('receiveSummaryText').innerText = '0 ' + (swapDirection === 'USDT_TO_INR' ? 'INR' : 'USDT');
        }}

        async function executeConversion() {{
            const val = parseFloat(document.getElementById('fromAmountInput').value) || 0;
            if (val <= 0) {{ alert('Please enter an amount to convert!'); return; }}
            const res = await fetch('/api/convert', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ amount: val, direction: swapDirection }})
            }});
            const data = await res.json();
            alert(data.message);
            window.location.reload();
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

        async function submitDepositUtr() {{
            const utr = document.getElementById('depositUtrInput').value.trim();
            if (!utr) {{ alert('Please enter UTR Number!'); return; }}
            const email = localStorage.getItem('cryptobot_user_email') || 'User';
            const res = await fetch('/api/verify-plan-utr', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    plan_id: 'STANDARD',
                    plan_name: 'STANDARD PACKAGE',
                    price: 999,
                    days: 30,
                    utr: utr,
                    email: email
                }})
            }});
            const data = await res.json();
            alert(data.message);
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
                    "status": "INACTIVE",
                    "plan": "NONE",
                    "days_left": 0,
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

        elif self.path == '/api/user-status':
            email = payload.get('email', '').strip().lower()
            db = load_db()
            user = db.get("users", {}).get(email, {})
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "user": user}).encode('utf-8'))

        elif self.path == '/api/verify-plan-utr':
            db = load_db()
            email = payload.get('email', 'User')
            utr = payload.get('utr', 'N/A')
            plan_id = payload.get('plan_id', 'STANDARD')
            plan_name = payload.get('plan_name', 'STANDARD PACKAGE')
            price = payload.get('price', 999)
            days = payload.get('days', 30)

            expiry = (datetime.now() + timedelta(days=days)).strftime("%d %b %Y")
            
            if email in db.get("users", {}):
                db["users"][email]["status"] = "ACTIVE"
                db["users"][email]["plan"] = plan_id
                db["users"][email]["days_left"] = days
                db["users"][email]["expires_on"] = expiry

            db.setdefault("payments", []).append({
                "email": email,
                "plan": plan_name,
                "utr": utr,
                "amount": price,
                "days": days,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db(db)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            msg = f"🎉 Payment Verified!\n\n{plan_name} (₹{price:,}) successfully activate ho gaya hai!\nValidity: {days} Days (Till {expiry})."
            self.wfile.write(json.dumps({"status": "success", "message": msg}).encode('utf-8'))

        elif self.path == '/api/withdraw-inr':
            amount_inr = float(payload.get('amount_inr', 0.0))
            destination = payload.get('destination', '').strip()
            db = load_db()

            if amount_inr < MIN_WITHDRAW_INR:
                res = {"status": "error", "message": f"❌ Minimum withdrawal ₹{MIN_WITHDRAW_INR:,.0f} INR hona chahiye!"}
            elif amount_inr > MAX_WITHDRAW_INR:
                res = {"status": "error", "message": f"❌ Maximum withdrawal ₹{MAX_WITHDRAW_INR:,.0f} INR tak hi allow hai!"}
            elif not destination:
                res = {"status": "error", "message": "❌ Kripya Destination UPI ID ya Bank Details daalein!"}
            else:
                usdt_needed = amount_inr / USDT_INR_RATE
                if db['balance'] < usdt_needed:
                    res = {"status": "error", "message": f"❌ Insufficient Balance! ₹{amount_inr:,.0f} nikaalne ke liye {usdt_needed:.2f} USDT chahiye."}
                else:
                    db['balance'] -= usdt_needed
                    now = datetime.now()
                    db.setdefault("wallet_activity", []).insert(0, {
                        "date": now.strftime("%d %b %Y"),
                        "time": now.strftime("%I:%M %p").lower(),
                        "type": f"Withdrawal (₹{amount_inr:,.0f} INR)",
                        "category": "WITHDRAWAL",
                        "amount": -usdt_needed,
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
            direction = payload.get('direction', 'USDT_TO_INR')
            db = load_db()
            
            if direction == 'USDT_TO_INR':
                if db['balance'] < amount:
                    res = {"status": "error", "message": "Insufficient USDT balance!"}
                else:
                    inr_received = amount * USDT_INR_RATE
                    db['balance'] -= amount
                    db['inr_balance'] = db.get('inr_balance', 0.0) + inr_received
                    db.setdefault("wallet_activity", []).insert(0, {
                        "date": datetime.now().strftime("%d %b %Y"),
                        "time": datetime.now().strftime("%I:%M %p").lower(),
                        "type": f"Converted {amount:.2f} USDT to INR",
                        "category": "CONVERSION",
                        "amount": -amount,
                        "status": "Completed"
                    })
                    save_db(db)
                    res = {"status": "success", "message": f"🎉 Converted {amount:.2f} USDT into ₹{inr_received:.2f} INR successfully!"}
            else:
                if db.get('inr_balance', 0.0) < amount:
                    res = {"status": "error", "message": "Insufficient INR balance!"}
                else:
                    usdt_received = amount / USDT_INR_RATE
                    db['inr_balance'] -= amount
                    db['balance'] += usdt_received
                    db.setdefault("wallet_activity", []).insert(0, {
                        "date": datetime.now().strftime("%d %b %Y"),
                        "time": datetime.now().strftime("%I:%M %p").lower(),
                        "type": f"Converted ₹{amount:.2f} INR to USDT",
                        "category": "CONVERSION",
                        "amount": usdt_received,
                        "status": "Completed"
                    })
                    save_db(db)
                    res = {"status": "success", "message": f"🎉 Converted ₹{amount:.2f} INR into {usdt_received:.2f} USDT successfully!"}

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
import ccxt
import json
import os
from datetime import datetime

# Binance connection
exchange = ccxt.binance()
coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
DB_FILE = 'trades.json'

# 1. Database Load ya Create karein
if not os.path.exists(DB_FILE):
    db_data = {
        "balance": 1000.0,
        "last_date": str(datetime.now().date()),
        "daily_trades_taken": 0,
        "trades": []
    }
    with open(DB_FILE, 'w') as f:
        json.dump(db_data, f, indent=4)
else:
    with open(DB_FILE, 'r') as f:
        db_data = json.load(f)

# Agar naya din shuru hua hai, toh daily count 0 karein
today_str = str(datetime.now().date())
if db_data.get("last_date") != today_str:
    db_data["last_date"] = today_str
    db_data["daily_trades_taken"] = 0

print("=" * 45)
print("🤖 AI CRYPTO TRADING BOT (DATABASE ACTIVE)")
print(f"💰 Saved Wallet Balance: ${db_data['balance']:.2f} USDT")
print(f"📊 Trades Taken Today: {db_data['daily_trades_taken']}/2")
print("=" * 45)

MAX_DAILY_TRADES = 2
TRADE_AMOUNT_USDT = 100.0

# 2. Market Scan & Trading
for coin in coins:
    if db_data["daily_trades_taken"] >= MAX_DAILY_TRADES:
        print(f"\n⚠️ Aaj ka limit ({MAX_DAILY_TRADES} trades) poora ho chuka hai!")
        break

    print(f"\n🔍 Analyzing {coin}...")
    ticker = exchange.fetch_ticker(coin)
    current_price = ticker['last']
    high_24h = ticker['high']
    low_24h = ticker['low']
    mid_price = (high_24h + low_24h) / 2

    if current_price > mid_price:
        db_data["daily_trades_taken"] += 1
        buy_price = current_price
        target_price = buy_price * 1.015
        stop_loss_price = buy_price * 0.99
        profit = TRADE_AMOUNT_USDT * 0.015
        db_data["balance"] += profit

        new_trade = {
            "id": len(db_data["trades"]) + 1,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "coin": coin,
            "entry_price": round(buy_price, 2),
            "target_price": round(target_price, 2),
            "profit": round(profit, 2),
            "status": "PROFIT"
        }
        db_data["trades"].append(new_trade)

        print(f"   🟢 Trade #{db_data['daily_trades_taken']} EXECUTED in {coin}!")
        print(f"      Profit: +${profit:.2f} USDT")
    else:
        print(f"   ⏳ {coin} mein abhi wait karein.")

# 3. Data ko Permanently File mein Save karein
with open(DB_FILE, 'w') as f:
    json.dump(db_data, f, indent=4)

print("\n" + "=" * 45)
print(f"✅ Saara record '{DB_FILE}' file mein save ho gaya!")
print(f"Updated Balance: ${db_data['balance']:.2f} USDT")
print("=" * 45 + "\n")
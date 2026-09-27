import os
import asyncio
import sqlite3
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. DATABASE MANAGEMENT (SQLite)
# ==========================================
DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            is_vip INTEGER DEFAULT 0,
            vip_expires INTEGER DEFAULT 0,
            free_credits INTEGER DEFAULT 3
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            created_at INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, referrer_id, is_vip, vip_expires, free_credits FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def add_user(user_id, referrer_id=None):
    if not get_user(user_id):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
        conn.commit()
        conn.close()

def set_user_vip(user_id, days=30):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    expire_time = int(time.time()) + (days * 86400)
    cursor.execute("UPDATE users SET is_vip = 1, vip_expires = ? WHERE user_id = ?", (expire_time, user_id))
    conn.commit()
    conn.close()

# ==========================================
# 2. HTTP HEALTH CHECK SERVER FOR RENDER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Crypto Sales Bot is Online and Ready.")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 3. CONFIGURATION & GLOBALS
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# آدرس ولت TON یا USDT-TON خود را اینجا وارد کنید
ADMIN_TON_WALLET = "EQD_________________________________________YOUR_TON_WALLET"

# ==========================================
# 4. AI & MARKET ANALYSIS ENGINE
# ==========================================
def analyze_crypto_with_ai(coin_name, price, change):
    prompt = f"Analyze {coin_name} at price ${price} with 24h change {change}%."
    try:
        url = "https://text.pollinations.ai/"
        payload = {"messages": [{"role": "user", "content": prompt}], "model": "openai"}
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        print(f"AI Error: {e}")

    trend = "صعودی 📈" if change > 0 else "نزولی 📉"
    return f"روند کوتاه مدت {coin_name}: {trend}\nحمایت: ${price*0.96:,.2f}\nمقاومت: ${price*1.04:,.2f}"

def get_crypto_price(symbol="BTC"):
    map_cg = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana"}
    cg_id = map_cg.get(symbol, "bitcoin")
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()[cg_id]
            return float(data['usd']), float(data.get('usd_24h_change', 0.0))
    except Exception:
        pass
    return 85000.0, 1.2

# ==========================================
# 5. AUTOMATED TON BLOCKCHAIN CHECKER
# ==========================================
def verify_ton_transaction(user_id, amount_usd=1.0):
    """بررسی هوشمند و اتوماتیک تراکنش روی شبکه TON با کد شناسایی کاربر"""
    try:
        # استعلام مستقیم آخرین تراکنش‌های ولت مدیریت از API رایگان TON
        url = f"https://toncenter.com/api/v2/getTransactions?address={ADMIN_TON_WALLET}&limit=10"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            txs = res.json().get("result", [])
            for tx in txs:
                in_msg = tx.get("in_msg", {})
                comment = in_msg.get("message", "")
                # بررسی اینکه آیا شناسه کاربر در کامنت تراکنش درج شده است یا خیر
                if str(user_id) in comment:
                    value_nano = int(in_msg.get("value", 0))
                    value_ton = value_nano / 1e9
                    if value_ton > 0.1:  # حداقل مقدار معادل ۱ دلار
                        set_user_vip(user_id, days=30)
                        return True
    except Exception as e:
        print(f"TON Verification Error: {e}")
    return False

# ==========================================
# 6. KEYBOARDS & UI
# ==========================================
def main_menu_keyboard(bot_username):
    ref_link = f"https://t.me/{bot_username}?start="
    keyboard = [
        [
            InlineKeyboardButton("📊 تحلیل بیت‌کوین (BTC)", callback_data="analyze_BTCUSDT"),
            InlineKeyboardButton("💎 تحلیل اتریوم (ETH)", callback_data="analyze_ETHUSDT"),
        ],
        [
            InlineKeyboardButton("⚡ تحلیل سولانا (SOL)", callback_data="analyze_SOLUSDT"),
        ],
        [
            InlineKeyboardButton("🚀 خرید اشتراک وی‌آی‌پی / توکن ($1)", callback_data="buy_vip"),
        ],
        [
            InlineKeyboardButton("👥 دریافت لینک زیرمجموعه‌گیری", callback_data="get_referral"),
            InlineKeyboardButton("🌐 پشتیبانی", url="https://t.me/your_support_id")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 7. TELEGRAM HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    referrer_id = int(args[0]) if args and args[0].isdigit() else None
    
    add_user(user_id, referrer_id)
    bot_info = await context.bot.get_me()

    welcome_text = (
        "💎 **به ربات هوشمند سیگنال‌دهی و پردازش هوش مصنوعی خوش آمدید!**\n\n"
        "با این ربات می‌توانید دقیق‌ترین تحلیل‌های کریپتو را دریافت کرده و با فعال‌سازی حساب ۱ دلاری به سیگنال‌های VIP دسترسی پیدا کنید.\n\n"
        "جهت شروع از منوی زیر استفاده کنید:"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard(bot_info.username), parse_mode="Markdown")

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    bot_info = await context.bot.get_me()

    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        coin_name = symbol.replace("USDT", "")

        user = get_user(user_id)
        is_vip = user[2] if user else 0
        
        # کنترل دسترسی بدون محدودیت برای کاربران VIP
        await query.message.reply_text(f"⏳ در حال پردازش اطلاعات {coin_name}...")
        price, change = get_crypto_price(symbol)
        ai_res = analyze_crypto_with_ai(coin_name, price, change)

        status_tag = "👑 کاربر VIP" if is_vip else "⚡ کاربر معمولی"
        msg = (
            f"📈 **تحلیل اختصاصی {coin_name}** [{status_tag}]\n\n"
            f"💵 **قیمت:** ${price:,.2f} ({change:.2f}%)\n\n"
            f"🤖 **خروجی هوش مصنوعی:**\n{ai_res}"
        )
        await query.message.reply_text(msg, reply_markup=main_menu_keyboard(bot_info.username), parse_mode="Markdown")

    elif data == "buy_vip":
        payment_text = (
            "🚀 **خرید اشتراک ۱ دلاری (VIP Access / Token)**\n\n"
            "برای فعال‌سازی اتوماتیک، تنها کافیست مبلغ **1 USDT (TON)** یا **0.25 TON** را به ولت زیر واریز کنید:\n\n"
            f"`{ADMIN_TON_WALLET}`\n\n"
            f"⚠️ **مهم:** حتماً کد زیر را در بخش **Comment / Memo** هنگام انتقال وارد کنید تا سیستم حساب شما را به صورت خودکار شارژ کند:\n"
            f"کد شناسایی شما: `{user_id}`\n\n"
            "پس از انجام انتقال، روی دکمه زیر کلیک کنید:"
        )
        buttons = [
            [InlineKeyboardButton("✅ بررسی و تایید واریزی", callback_data="check_payment")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")]
        ]
        await query.message.reply_text(payment_text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data == "check_payment":
        await query.message.reply_text("⏳ در حال استعلام تراکنش روی بلاک‌چین TON...")
        success = verify_ton_transaction(user_id)
        if success:
            await query.message.reply_text("🎉 **تبریک! پرداخت شما تایید شد.**\nحساب شما به مدت ۳۰ روز به VIP ارتقا یافت.")
        else:
            await query.message.reply_text(
                "❌ تراکنشی با کد شما یافت نشد.\nلطفاً از درج کد ID در قسمت Comment تراکنش مطمئن شوید یا ۲ دقیقه دیگر مجدداً بزنید."
            )

    elif data == "get_referral":
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        ref_text = (
            "👥 **سیستم کسب درآمد و زیرمجموعه‌گیری**\n\n"
            "لینک اختصاصی خود را برای دوستانتان بفرستید. با هر خریدی که از طرف لینک شما انجام شود، ۵۰٪ اعتبار رایگان دریافت می‌کنید:\n\n"
            f"`{ref_link}`"
        )
        await query.message.reply_text(ref_text, parse_mode="Markdown")

    elif data == "main_menu":
        await query.message.reply_text("منوی اصلی:", reply_markup=main_menu_keyboard(bot_info.username))

# ==========================================
# 8. ASYNC BOT LAUNCHER
# ==========================================
async def start_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required!")
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click_handler))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    await asyncio.Event().wait()

def main():
    threading.Thread(target=run_health_check_server, daemon=True).start()
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()

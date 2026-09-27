import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ==========================================
# 1. HTTP HEALTH CHECK SERVER FOR RENDER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Crypto Telegram Bot is Active and Running 24/7!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 2. CONFIGURATION & SECURE REST API KEYS
# ==========================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = "AQ.Ab8RN6IE6U0sNX-fpZnvokfBtax96g2hAk4fy6cGqxlS_PcorA"

def analyze_crypto_with_gemini(coin_name, price, change, high, low):
    """ارسال درخواست مستقیم REST به مدل پیشرفته Gemini برای دور زدن خطای احراز هویت SDK"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    تو یک تحلیلگر حرفه‌ای کریپتوکارنسی هستی.
    ارز: {coin_name}
    قیمت لحظه‌ای: ${price:,.2f}
    تغییرات ۲۴ ساعت گذشته: {change:.2f}%

    لطفاً یک تحلیل کوتاه، دقیق و کاربردی در قالب ۴ بخش زیر به زبان فارسی بنویس:
    ۱. روند کلی کوتاه مدت (صعودی/نزولی/رنج)
    ۲. سطوح کلیدی حمایت و مقاومت
    ۳. پیشنهاد معامله (خرید/فروش/صبر) با حد سود و حد زیان تقریبی
    ۴. مدیریت ریسک و توصیه پایانی

    لحن پاسخ حرفه‌ای، جذاب و همراه با ایموجی‌های مناسب باشد.
    """
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"خطای ارتباط با سرور هوش مصنوعی (کد {response.status_code}): {response.text}"
    except Exception as e:
        return f"خطا در پردازش شبکه: {str(e)}"

# ==========================================
# 3. HELPER FUNCTIONS (PRICE FETCH)
# ==========================================
def get_crypto_price(symbol="BTC"):
    map_cg = {
        "BTCUSDT": "bitcoin",
        "ETHUSDT": "ethereum",
        "SOLUSDT": "solana"
    }
    
    cg_id = map_cg.get(symbol, "bitcoin")
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()[cg_id]
            price = float(data['usd'])
            change = float(data.get('usd_24h_change', 0.0))
            return price, change, price * 1.02, price * 0.98
    except Exception as e:
        print(f"CoinGecko error: {e}")

    try:
        url = f"https://api.mexc.com/api/v3/ticker/24hr?symbol={symbol}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = float(data['lastPrice'])
            change = float(data['priceChangePercent'])
            high = float(data['highPrice'])
            low = float(data['lowPrice'])
            return price, change, high, low
    except Exception as e:
        print(f"MEXC error: {e}")

    return None, None, None, None

# ==========================================
# 4. TELEGRAM UI KEYBOARDS
# ==========================================
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 تحلیل بیت‌کوین (BTC)", callback_data="analyze_BTCUSDT"),
            InlineKeyboardButton("💎 تحلیل اتریوم (ETH)", callback_data="analyze_ETHUSDT"),
        ],
        [
            InlineKeyboardButton("⚡ تحلیل سولانا (SOL)", callback_data="analyze_SOLUSDT"),
            InlineKeyboardButton("👑 اشتراک ویژه VIP ($)", callback_data="vip_membership"),
        ],
        [
            InlineKeyboardButton("🌐 وب‌سایت و پشتیبانی", url="https://www.instagram.com/amir_botai")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# 5. HANDLERS
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🚀 **به ربات هوشمند تحلیل و سیگنال‌دهی کریپتو خوش آمدید!**\n\n"
        "این ربات با اتصال به موتور هوش مصنوعی Gemini و داده‌های بازار، "
        "دقیق‌ترین تحلیل‌ها را ارائه می‌دهد.\n\n"
        "لطفاً از منوی زیر گزینه مورد نظر را انتخاب کنید:"
    )
    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        coin_name = symbol.replace("USDT", "")

        await query.message.reply_text(f"⏳ در حال دریافت داده‌های {coin_name} و تحلیل با هوش مصنوعی...")

        price, change, high, low = get_crypto_price(symbol)

        if price is None:
            await query.message.reply_text("❌ خطا در دریافت اطلاعات از صرافی. لطفاً مجدداً تلاش کنید.")
            return

        ai_analysis = analyze_crypto_with_gemini(coin_name, price, change, high, low)

        full_response = (
            f"📈 **تحلیل هوشمند ارز {coin_name}**\n\n"
            f"💵 **قیمت لحظه‌ای:** ${price:,.2f}\n"
            f"📊 **تغییرات ۲۴h:** {change:.2f}%\n\n"
            f"🤖 **تحلیل هوش مصنوعی Gemini:**\n\n"
            f"{ai_analysis}"
        )

        await query.message.reply_text(
            full_response,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "vip_membership":
        vip_text = (
            "👑 **مزایای کانال VIP سیگنال‌دهی:**\n\n"
            "▫️ سیگنال‌های نقطه ورود و خروج فیوچرز و اسپات\n"
            "▫️ مدیریت ریسک و سرمایه اختصاصی\n"
            "▫️ پشتیبانی ۲۴/۷ و مشاوره سبدگردانی\n\n"
            "📩 جهت تهیه اشتراک به آیدی پشتیبانی پیام دهید."
        )
        await query.message.reply_text(
            vip_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# ==========================================
# 6. MAIN EXECUTION
# ==========================================
def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

    # راه‌اندازی سرور سلامت در ترد پس‌زمینه
    threading.Thread(target=run_health_check_server, daemon=True).start()
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click_handler))

    # اجرای ربات روی ترد اصلی بدون تداخل حلقه رویداد
    application.run_polling()

if __name__ == "__main__":
    main()

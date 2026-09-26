import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from google import genai

# ==========================================
# تنظیمات کلیدهای API (API Keys)
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # توکن ربات تلگرام خود را اینجا قرار دهید
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"          # کلید جمینای خود را اینجا قرار دهید

# مقداردهی اولیه به کلاینت Gemini
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# تابع دریافت قیمت و اطلاعات بازار از بایننس
# ==========================================
def get_crypto_data(symbol: str) -> str:
    """دریافت قیمت لحظه‌ای و تغییرات ۲۴ ساعته از بایننس"""
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            price = round(float(data.get("lastPrice", 0)), 2)
            change = round(float(data.get("priceChangePercent", 0)), 2)
            high = round(float(data.get("highPrice", 0)), 2)
            low = round(float(data.get("lowPrice", 0)), 2)
            volume = round(float(data.get("volume", 0)), 2)
            
            return (
                f"📊 اطلاعات بازار لحظه‌ای ({symbol}/USDT):\n"
                f"🔹 قیمت فعلی: ${price:,}\n"
                f"📈 تغییرات ۲۴ ساعته: {change}%\n"
                f"🔝 بالاترین قیمت ۲۴ ساعت: ${high:,}\n"
                f"🔻 پایین‌ترین قیمت ۲۴ ساعت: ${low:,}\n"
                f"🔄 حجم معاملات: {volume:,}\n"
            )
        else:
            return "⚠️ خطایی در دریافت داده‌های بازار رخ داد."
    except Exception as e:
        return f"⚠️ خطای ارتباط با بازار: {e}"

# ==========================================
# تابع تحلیل هوش مصنوعی (Gemini)
# ==========================================
def analyze_with_gemini(symbol: str, market_data: str) -> str:
    """ارسال داده‌های بازار به Gemini و دریافت تحلیل و سیگنال"""
    prompt = f"""
    شما یک تحلیل‌گر و تریدر حرفه‌ای بازار کریپتوکارنسی هستید.
    اطلاعات زیر مربوط به ارز {symbol} است:
    
    {market_data}
    
    لطفاً بر اساس این داده‌ها و شرایط کلی بازار:
    ۱. یک تحلیل فنی کوتاه و خلاصه بفرمایید.
    ۲. وضعیت کلی (صعودی/نزولی/رنج) را مشخص کنید.
    ۳. سطوح کلیدی حمایت و مقاومت پیشنهادی را ذکر کنید.
    ۴. پیشنهاد سناریوی معاملاتی (خرید/فروش/انتظار) همراه با حد سود و حد زیان مدیریت ریسک ارائه دهید.
    
    پاسخ را با ایموجی‌های مناسب، منظم و خوانا به زبان فارسی بنویسید.
    """
    try:
        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ خطای پردازش هوش مصنوعی: {e}"

# ==========================================
# منوی اصلی (Keyboard Markup)
# ==========================================
def main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 تحلیل بیت‌کوین (BTC)", callback_data="analyze_BTC"),
            InlineKeyboardButton("💎 تحلیل اتریوم (ETH)", callback_data="analyze_ETH"),
        ],
        [
            InlineKeyboardButton("⚡ تحلیل سولانا (SOL)", callback_data="analyze_SOL"),
            InlineKeyboardButton("👑 اشتراک ویژه VIP ($)", callback_data="vip_info"),
        ],
        [
            InlineKeyboardButton("🌐 وب‌سایت و پشتیبانی", url="https://instagram.com/amir_botai")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# هندلرهای ربات (Handlers)
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به دستور /start"""
    welcome_text = (
        "🚀 **به ربات هوشمند تحلیل و سیگنال‌دهی کریپتو خوش آمدید!**\n\n"
        "این ربات با اتصال به موتور هوش مصنوعی Gemini و داده‌های آن‌چین بازار، "
        "دقیق‌ترین تحلیل‌ها را ارائه می‌دهد.\n\n"
        "لطفاً از منوی زیر گزینه‌ای را انتخاب کنید:"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌های شیشه‌ای"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        
        # اطلاع‌رسانی به کاربر
        await query.edit_message_text(
            f"⏳ در حال استخراج داده‌های {symbol} و تحلیل هوش مصنوعی... لطفاً چند ثانیه صبر کنید.",
            reply_markup=None
        )
        
        # دریافت قیمت و تحلیل
        market_info = get_crypto_data(symbol)
        ai_analysis = analyze_with_gemini(symbol, market_info)
        
        full_response = f"{market_info}\n🤖 **تحلیل هوش مصنوعی Gemini:**\n\n{ai_analysis}"
        
        # ارسال پاسخ همراه با مجدد قرار دادن منوی اصلی
        await query.message.reply_text(
            full_response,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "vip_info":
        vip_text = (
            "👑 **کانال VIP سیگنال‌دهی هوشمند**\n\n"
            "ویژگی‌های کانال VIP:\n"
            "• سیگنال‌های لحظه‌ای خرید و فروش با حد سود و ضرر مشخص\n"
            "• تحلیل اختصاصی ارزهای آلت‌کوین کم‌ریسک و پرپتانسیل\n"
            "• پشتیبانی ۲۴/۷ و مشاوره سبدگردانی\n\n"
            "جهت تهیه اشتراک به آیدی پشتیبانی پیام دهید."
        )
        await query.message.reply_text(
            vip_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# ==========================================
# نقطه شروع برنامه (Main Function)
# ==========================================
def main():
    print("🤖 ربات در حال اجرا است...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ثبت دستورات و رویدادها
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_click_handler))

    # اجرای ربات
    app.run_polling()

if __name__ == "__main__":
    main()

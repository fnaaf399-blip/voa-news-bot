import telebot
import feedparser
import time
import os
from groq import Groq
from telebot import types

# --- تنظیمات اختصاصی شما ---
API_TOKEN = '8448231347:AAH-Oz-WQ0Jek0ygaboT-FnMYTQDley8zzA'
GROQ_API_KEY = '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'
ADMIN_ID = 7692563400  # آیدی عددی شما
PERMANENT_CHANNEL = "@dari_news_af" # آیدی کانال دائمی

# لینک‌های RSS صدای آمریکا (دری - بخش افغانستان و دسته‌بندی‌ها)
RSS_FEEDS = {
    "افغانستان": "https://www.darivoa.com/api/z-yite_kqy",
    "سیاسی": "https://www.darivoa.com/api/zjv_t-i_v_",
    "منطقه و جهان": "https://www.darivoa.com/api/zuv_teievi",
    "ورزشی": "https://www.darivoa.com/api/z_v_teid_i",
    "فرهنگی": "https://www.darivoa.com/api/zpv_toimvi"
}

bot = telebot.TeleBot(API_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

sent_articles = set()

def summarize_text(text):
    """خلاصه‌سازی هوشمند به زبان دری با استفاده از Groq"""
    try:
        if len(text) < 250: return text
        
        response = groq_client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": f"این خبر را به زبان دری (افغانستان) بسیار کوتاه و دقیق در قالب یک پاراگراف خلاصه کن:\n\n{text}"
            }],
            model="llama-3.3-70b-versatile",
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Error: {e}")
        return text[:300] + "..."

def get_image(entry):
    """یافتن لینک مستقیم عکس از فید RSS"""
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    if 'media_content' in entry:
        return entry.media_content[0]['url']
    return None

def post_news(entry, manual_chat_id=None):
    """ارسال خبر با فرمت دقیق درخواستی شما"""
    title = entry.title
    summary = summarize_text(entry.summary)
    img = get_image(entry)
    
    # تعیین مقصد ارسال
    target = manual_chat_id if manual_chat_id else PERMANENT_CHANNEL

    # فرمت‌بندی کپشن: تیتر برجسته + متن خلاصه + دو فاصله + آیدی بدون ادیت
    # استفاده از \n برای ایجاد فاصله‌های دقیق
    caption = f"🔹 <b>{title}</b>\n\n"
    caption += f"{summary}\n\n"
    caption += f"\n\n🚨 | {PERMANENT_CHANNEL}"

    try:
        if img:
            bot.send_photo(target, img, caption=caption, parse_mode='HTML')
        else:
            bot.send_message(target, caption, parse_mode='HTML')
    except Exception as e:
        print(f"Error sending to {target}: {e}")

# --- پنل مدیریت اختصاصی ادمین ---
@bot.message_handler(commands=['start', 'panel'])
def admin_panel(message):
    # فقط شما و آیدی ادمین تعیین شده دسترسی دارید
    if message.from_user.id != ADMIN_ID:
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("🔄 تست آنلاینی (ارسال آخرین خبر)")
    markup.add(btn)
    bot.send_message(message.chat.id, f"پنل مدیریت فعال شد.\nکانال هدف: {PERMANENT_CHANNEL}", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔄 تست آنلاینی (ارسال آخرین خبر)")
def test_bot(message):
    if message.from_user.id != ADMIN_ID: return
    
    feed = feedparser.parse(RSS_FEEDS["افغانستان"])
    if feed.entries:
        bot.send_message(message.chat.id, "در حال ارسال آخرین خبر به عنوان تست...")
        post_news(feed.entries[0], manual_chat_id=PERMANENT_CHANNEL)

# --- حلقه خودکار بررسی RSS (هر ۵ دقیقه) ---
def auto_check_rss():
    while True:
        for name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    entry = feed.entries[0]
                    if entry.link not in sent_articles:
                        post_news(entry)
                        sent_articles.add(entry.link)
                        time.sleep(10) # وقفه کوتاه بین ارسال‌ها
            except Exception as e:
                print(f"Loop Error: {e}")
        time.sleep(300) # انتظار برای ۵ دقیقه

if __name__ == "__main__":
    import threading
    # اجرای بخش RSS در پس‌زمینه
    threading.Thread(target=auto_check_rss, daemon=True).start()
    print(f"Bot is running for {PERMANENT_CHANNEL}...")
    bot.infinity_polling()
  

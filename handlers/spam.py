import asyncio
import re
from telethon import events

def register_spam_handler(client):
    # ایجاد یک فلگ روی کلاینت برای مدیریت دکمه توقف یا همان پایان اسپم
    if not hasattr(client, 'spam_active_tasks'):
        client.spam_active_tasks = {}

    # ------------------------------------------------------------------
    # ۱. هندلر متوقف کردن اسپم (*پایان اسپم)
    # ------------------------------------------------------------------
    @client.on(events.NewMessage(pattern=r"^\*?پایان اسپم$", outgoing=True))
    async def stop_spam_handler(event):
        chat_id = event.chat_id
        if chat_id in client.spam_active_tasks and client.spam_active_tasks[chat_id]:
            client.spam_active_tasks[chat_id] = False
            await event.edit("<b>عملیات اسپم در این چت با موفقیت متوقف شد.</b>", parse_mode="html")
        else:
            await event.edit(" <b>هیچ اسپمی در این چت در حال اجرا نیست.</b>", parse_mode="html")
            await asyncio.sleep(2)
            await event.delete()

    # ------------------------------------------------------------------
    # ۲. هندلر اصلی انواع اسپم (معمولی، سریع، کند)
    # ------------------------------------------------------------------
    # پترن جدید رگکس برای ساپورت کلمات: اسپم، اسپم سریع، اسپم کند
    @client.on(events.NewMessage(pattern=r"^\*?اسپم( سریع| کند)?\s+(\d+)\s+(.+)", outgoing=True))
    async def spam_handler(event):
        chat_id = event.chat_id
        
        try:
            # استخراج اطلاعات از رگکس
            match = event.pattern_match
            spam_type = match.group(1) # میتونه ' سریع'، ' کند' یا None باشه
            count = int(match.group(2))
            message_text = match.group(3)

            # پاک کردن دستور اصلی برای شلوغ نشدن چت
            await event.delete()

            # بررسی و تنظیم تاخیر (Delay) بر اساس نوع دستور
            if spam_type == " سریع":
                delay = 0.1  # اسپم بسیار سریع
            elif spam_type == " کند":
                delay = 1.5  # اسپم کند و با فاصله زیاد
            else:
                delay = 0.4  # اسپم معمولی (پیش‌فرض)

            # محدود کردن تعداد اسپم برای امنیت اکانت و جلوگیری از فلاد شدید
            if count > 200:
                count = 200

            # فعال کردن وضعیت اسپم در این چت
            client.spam_active_tasks[chat_id] = True

            # حلقه ارسال پیام‌ها
            for i in range(count):
                # اگر کاربر دستور *پایان اسپم را زده باشد، وضعیت False شده و حلقه می‌شکند
                if not client.spam_active_tasks.get(chat_id, False):
                    break

                # ارسال پیام به همان چت
                await client.send_message(chat_id, message_text)
                
                # تاخیر تعیین شده
                await asyncio.sleep(delay)

        except Exception as e:
            print(f"❌ خطا در اجرای قابلیت اسپم: {e}")
        finally:
            # پاک کردن وضعیت چت بعد از به پایان رسیدن حلقه
            if chat_id in client.spam_active_tasks:
                del client.spam_active_tasks[chat_id]
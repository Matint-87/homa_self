import asyncio
from telethon import events, functions

# دیتابیس موقت در رم سرور
AUTO_SEEN_CACHE = {}

def register_auto_seen_handler(client):

    # دکوراتور اول برای بررسی و پردازش پیام‌های ورودی
    @client.on(events.NewMessage(incoming=True))
    async def auto_seen_worker(event):
        if event.is_channel: 
            return # کانال‌ها پردازش نشوند
        
        try:
            # ۱. استخراج فوق‌سریع آیدی بدون گت‌می مجدد
            if not hasattr(event.client, '_cached_my_id') or event.client._cached_my_id is None:
                me = await event.client.get_me()
                event.client._cached_my_id = me.id
            owner_id = event.client._cached_my_id
            
            # ۲. بررسی وضعیت با اولویت دیتابیس لوکال و سینک اولیه
            if owner_id not in AUTO_SEEN_CACHE:
                try:
                    from utils import get_auto_seen_from_db
                    db_status = get_auto_seen_from_db(owner_id)
                    AUTO_SEEN_CACHE[owner_id] = bool(db_status) if db_status is not None else False
                except Exception as db_err:
                    print(f"⚠️ Error reading status from DB: {db_err}")
                    AUTO_SEEN_CACHE[owner_id] = False # پیش‌فرض ایمن
            
            is_active = AUTO_SEEN_CACHE.get(owner_id, False)
            
            # 🛑 بخش کلیدی اصلاح شده: اگر خاموش بود، رویداد را کاملاً متوقف کن
            if not is_active:
                # این دستور به تلثون می‌گوید پردازش این پیام را در تمام هندلرهای دیگر هم متوقف کن
                # تا اگر ماژول دیگری (مثل منشی یا پاسخ خودکار) خواست پیام را بخواند، جلوی آن گرفته شود.
                raise events.StopPropagation 
                
            # ۴. ارسال آنی درخواست سین به سرور تلگرام (فقط در صورت روشن بودن)
            await event.client(functions.messages.ReadHistoryRequest(
                peer=event.peer_id,
                max_id=event.id
            ))
            
        except events.StopPropagation:
            # خروج امن بدون شلیک به بقیه متدها
            return
        except Exception as e:
            if "FloodWaitError" in str(e):
                wait_time = int(''.join(filter(str.isdigit, str(e))) or 5)
                await asyncio.sleep(wait_time)

    # ==================================================================
    # دستور متنی تغییر وضعیت
    # ==================================================================
    @client.on(events.NewMessage(pattern=r"^\*?(سین خودکار|سین خودکار) (روشن|روشن|خاموش|خاموش)$", outgoing=True))
    async def toggle_seen_via_text(event):
        if not hasattr(event.client, '_cached_my_id') or event.client._cached_my_id is None:
            me = await event.client.get_me()
            event.client._cached_my_id = me.id
        owner_id = event.client._cached_my_id
        
        raw_status = event.pattern_match.group(2).strip()
        
        if raw_status in ["روشن", "روشن"]:
            status = True
            msg_word = "روشن"
        else:
            status = False
            msg_word = "خاموش"
        
        # فورس کردن تغییر در کش رم به صورت آنی
        AUTO_SEEN_CACHE[owner_id] = status
        
        try:
            from utils import save_auto_seen_to_db
            save_auto_seen_to_db(owner_id, status)
        except Exception as db_err:
            print(f"Error saving auto seen status to DB: {db_err}")
        
        emoji = "🟢" if status else "🔴"
        await event.edit(f"{emoji} <b>سین خودکار {msg_word} شد.</b>", parse_mode="html")
import asyncio
from telethon import events
from config import supabase 

def get_tabchi_config(user_id: int) -> dict:
    """دریافت تنظیمات تبچی اختصاصی هر کاربر از دیتابیس سوپابیس"""
    try:
        res = supabase.table("user_tabchi").select("*").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"Error fetching tabchi config for {user_id}: {e}")
        
    return {
        "user_id": user_id,
        "is_active": False,
        "interval": 600, # پیش‌فرض به ۱۰ دقیقه تغییر یافت
        "banner_peer_id": None,
        "banner_msg_id": None
    }

def save_tabchi_config(config: dict):
    """ذخیره یا آپدیت تنظیمات تبچی کاربر در سوپابیس"""
    try:
        supabase.table("user_tabchi").upsert(config).execute()
    except Exception as e:
        print(f"Error saving tabchi config: {e}")

def register_tabchi(bot):
    """ثبت هندلرهای تبچی چندکاربره تفکیک‌شده متصل به Supabase همراه با لیمیت امنیتی"""

    print("📢 ماژول تبچی مالتی‌یوتیزر (دارای لیمیت امنیتی) بارگذاری شد.")

    # تسک پس‌زمینه: رانر اختصاصی هر کلاینت
    async def tabchi_loop():
        await bot.get_me()
        while True:
            try:
                me = await bot.get_me()
                user_id = me.id
                
                config = get_tabchi_config(user_id)
                
                if config.get("is_active") and config.get("banner_msg_id"):
                    print(f"🤖 [User {user_id}] تبچی: شروع ارسال دوره‌ای...")
                    
                    try:
                        banner_msg = await bot.get_messages(
                            config["banner_peer_id"], 
                            ids=config["banner_msg_id"]
                        )
                    except Exception as e:
                        print(f"❌ [User {user_id}] خطای لود بنر مرجع: {e}")
                        banner_msg = None

                    if banner_msg:
                        async for dialog in bot.iter_dialogs():
                            if dialog.is_group:
                                try:
                                    await bot.send_message(
                                        entity=dialog.id,
                                        message=banner_msg
                                    )
                                    await asyncio.sleep(3)  # افزایش تاخیر به ۳ ثانیه برای امنیت بیشتر در مقیاس بالا
                                except Exception as send_err:
                                    print(f"⚠️ [User {user_id}] ارسال به {dialog.name} ناموفق: {send_err}")
                
                # خواندن لیمیت زمانی تنظیم شده کاربر
                await asyncio.sleep(int(config.get("interval", 600)))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"🚨 خطا در لوپ تبچی: {e}")
                await asyncio.sleep(30)

    bot.loop.create_task(tabchi_loop())

    # دستور تنظیم تبلیغ (ریپلاي روی بنر) همراه با بررسی لیمیت زمان
    @bot.on(events.NewMessage(pattern=r'^\*تنظیم تبلیغ (\d+)'))
    async def set_banner_handler(event):
        me = await bot.get_me()
        if event.sender_id != me.id: return

        if not event.is_reply:
            await event.reply("⚠️ لطفا این دستور را روی بنر خود ریپلای کنید.")
            return

        seconds = int(event.pattern_match.group(1).strip())
        
        # 🛡️ اعمال لیمیت اختصاصی: جلوگیری از تنظیم زمان‌های کوتاه و خطرناک
        if seconds < 600:
            await event.reply(
                "❌ **خطای محدودیت زمانی!**\n"
                "جهت جلوگیری از ریپورت و دیلیت شدن حساب شما، حداقل زمان ارسال باید **۶۰۰ ثانیه (۱۰ دقیقه)** باشد.\n\n"
                "💡 مثال مجاز: `*تنظیم_تبلیغ 600`"
            )
            return

        reply_msg = await event.get_reply_message()
        
        config = get_tabchi_config(me.id)
        config["banner_peer_id"] = event.chat_id
        config["banner_msg_id"] = reply_msg.id
        config["interval"] = seconds
        
        save_tabchi_config(config)
        await event.reply(f"✅ بنر تبلیغاتی شما ذخیره شد.\n⏱ زمان‌بندی اختصاصی: هر `{seconds}` ثانیه (تنظیمات لیمیت رعایت شد).")

    # دستور روشن کردن تبچی
    @bot.on(events.NewMessage(pattern=r'^\*روشن تبلیغ'))
    async def turn_on_tabchi(event):
        me = await bot.get_me()
        if event.sender_id != me.id: return

        config = get_tabchi_config(me.id)
        if not config.get("banner_msg_id"):
            await event.reply("❌ شما هنوز بنری تنظیم نکرده‌اید! ابتدا با `*تنظیم_تبلیغ` بنر بدهید.")
            return

        config["is_active"] = True
        save_tabchi_config(config)
        await event.reply("🚀 **تبچی اختصاصی شما روشن شد!**")

    # دستور خاموش کردن تبچی
    @bot.on(events.NewMessage(pattern=r'^\*خاموش تبلیغ'))
    async def turn_off_tabchi(event):
        me = await bot.get_me()
        if event.sender_id != me.id: return

        config = get_tabchi_config(me.id)
        config["is_active"] = False
        save_tabchi_config(config)
        await event.reply("🛑 **تبچی اختصاصی شما خاموش شد.**")

    # دستور مشاهده وضعیت
    @bot.on(events.NewMessage(pattern=r'^\*وضعیت تبلیغ'))
    async def status_tabchi(event):
        me = await bot.get_me()
        if event.sender_id != me.id: return

        config = get_tabchi_config(me.id)
        status = "🟢 روشن" if config.get("is_active") else "🔴 خاموش"
        interval = config.get("interval", 600)
        has_banner = "🎯 ذخیره شده" if config.get("banner_msg_id") else "❌ تعریف نشده"

        await event.reply(
            f"📊 **وضعیت سیستم تبچی دیتابیس شما:**\n\n"
            f"🔹 وضعیت فعالیت: {status}\n"
            f"⏱ بازه چرخشی ارسال: هر `{interval}` ثانیه (حداقل مجاز: 600)\n"
            f"🖼 وضعیت بنر در سوپابیس: {has_banner}"
        )
import asyncio
from telethon import events, TelegramClient
from utils import db_execute
from config import supabase

active_tabchis = {}

def register_tabchi_handler(client: TelegramClient):
    
    # --- ۱. تنظیم ساده بنر (با نام اختیاری یا خودکار) ---
    @client.on(events.NewMessage(pattern=r'^\*تنظیم بنر(?:\s+([^\s]+))?$'))
    async def set_banner(event):
        user_id = event.sender_id
        banner_name = event.pattern_match.group(1)
        
        if not event.is_reply:
            return await event.edit("❌ لطفاً روی یک پیام (بنر) ریپلای کنید!")
        
        reply_msg = await event.get_reply_message()
        banner_content = reply_msg.text or reply_msg.caption or ""
        
        res = await db_execute(supabase.table("banners").select("banner_name", count="exact").eq("user_id", user_id))
        if res.count >= 10:
            return await event.edit("❌ شما به سقف مجاز (حداکثر ۱۰ بنر) رسیدید!")
        
        # اگر نام بنر داده نشده بود، به صورت خودکار یک شماره یکتا اختصاص بده
        if not banner_name:
            existing_names = [r["banner_name"] for r in res.data] if res.data else []
            counter = 1
            while str(counter) in existing_names:
                counter += 1
            banner_name = str(counter)
        else:
            banner_name = banner_name.strip()
        
        await db_execute(
            supabase.table("banners").upsert({
                "user_id": user_id,
                "banner_name": banner_name,
                "banner_text": banner_content
            }, on_conflict="user_id,banner_name")
        )
        await event.edit(f"✅ بنر **{banner_name}** با موفقیت ذخیره شد.")

    # --- ۲. تنظیم سرعت تبچی با دستور جداگانه ---
    @client.on(events.NewMessage(pattern=r'^\*سرعت تبچی\s+(\d+)$'))
    async def set_tabchi_speed(event):
        user_id = event.sender_id
        delay = int(event.pattern_match.group(1))
        delay = max(10, min(60, delay))
        
        await db_execute(
            supabase.table("tabchi_settings").upsert({
                "user_id": user_id,
                "delay_seconds": delay
            }, on_conflict="user_id")
        )
        await event.edit(f"⏱️ سرعت ارسال تبچی روی **{delay} ثانیه** تنظیم شد.")

    # --- ۴. لیست بنرها ---
    @client.on(events.NewMessage(pattern=r'^\*لیست بنر$'))
    async def list_banners(event):
        user_id = event.sender_id
        res = await db_execute(supabase.table("banners").select("banner_name", "banner_text").eq("user_id", user_id))
        
        if not res.data:
            return await event.edit("📭 هیچ بنری ثبت نشده است.")
        
        msg = "📋 **لیست بنرهای شما:**\n"
        for row in res.data:
            preview = row["banner_text"][:25] + "..." if len(row["banner_text"]) > 25 else row["banner_text"]
            msg += f"\n🔸 **{row['banner_name']}**: `{preview}`"
        
        await event.edit(msg)

    # --- ۵. پاکسازی‌ها ---
    @client.on(events.NewMessage(pattern=r'^\*پاکسازی لیست بنر$'))
    async def clear_banners(event):
        user_id = event.sender_id
        await db_execute(supabase.table("banners").delete().eq("user_id", user_id))
        await event.edit("🗑️ تمام بنرهای شما پاک شدند.")

    @client.on(events.NewMessage(pattern=r'^\*پاکسازی کل تبچی$'))
    async def clear_all_tabchi(event):
        user_id = event.sender_id
        if user_id in active_tabchis:
            active_tabchis[user_id].cancel()
            del active_tabchis[user_id]
            
        await db_execute(supabase.table("banners").delete().eq("user_id", user_id))
        await db_execute(supabase.table("tabchi_chats").delete().eq("user_id", user_id))
        await db_execute(supabase.table("tabchi_settings").delete().eq("user_id", user_id))
        await event.edit("⚠️ کل اطلاعات و تنظیمات تبچی شما پاک و ریست شد.")

    # --- ۶. مدیریت گپ‌ها (حداکثر ۵ گپ) ---
    @client.on(events.NewMessage(pattern=r'^\*تبچی گپ\s+(@\S+)$'))
    async def add_tabchi_chat(event):
        user_id = event.sender_id
        chat_username = event.pattern_match.group(1).strip()
        
        res = await db_execute(supabase.table("tabchi_chats").select("id", count="exact").eq("user_id", user_id))
        if res.count >= 5:
            return await event.edit("❌ شما حداکثر می‌توانید ۵ گپ برای تبچی انتخاب کنید.")
            
        await db_execute(
            supabase.table("tabchi_chats").upsert({
                "user_id": user_id,
                "chat_username": chat_username
            }, on_conflict="user_id,chat_username")
        )
        
        await event.edit(f"✅ گپ `{chat_username}` به لیست تبچی اضافه شد.")

    @client.on(events.NewMessage(pattern=r'^\*لیست تبچی گپ$'))
    async def list_tabchi_chats(event):
        user_id = event.sender_id
        res = await db_execute(supabase.table("tabchi_chats").select("chat_username").eq("user_id", user_id))
        if not res.data:
            return await event.edit("📭 هیچ گپی در لیست تبچی نیست.")
            
        chats = [row["chat_username"] for row in res.data]
        await event.edit(f"💬 **گپ‌های تبچی شما (حداکثر ۵ عدد):**\n" + "\n".join([f"🔹 {c}" for c in chats]))

    @client.on(events.NewMessage(pattern=r'^\*حذف تبچی گپ\s+(@\S+)$'))
    async def remove_tabchi_chat(event):
        user_id = event.sender_id
        chat_username = event.pattern_match.group(1).strip()
        
        await db_execute(supabase.table("tabchi_chats").delete().eq("user_id", user_id).eq("chat_username", chat_username))
        await event.edit(f"🗑️ گپ `{chat_username}` از لیست تبچی حذف شد.")

    @client.on(events.NewMessage(pattern=r'^\*پاکسازی تبچی گپ$'))
    async def clear_tabchi_chats(event):
        user_id = event.sender_id
        await db_execute(supabase.table("tabchi_chats").delete().eq("user_id", user_id))
        await event.edit("🗑️ تمام گپ‌های تبچی پاک شدند.")

    # --- ۷. لوپ پس‌زمینه تبچی (ارسال بنرها به گپ‌ها) ---
    async def tabchi_worker(client: TelegramClient, user_id: int):
        try:
            sent_to_this_chat = 0
            while True:
                settings = await db_execute(supabase.table("tabchi_settings").select("delay_seconds").eq("user_id", user_id))
                delay = settings.data[0]["delay_seconds"] if settings.data and "delay_seconds" in settings.data[0] else 20
                delay = max(10, min(60, delay))
                
                chats_res = await db_execute(supabase.table("tabchi_chats").select("chat_username").eq("user_id", user_id))
                # محدود کردن تعداد بنرهای دریافتی از دیتابیس به حداکثر ۱۰ عدد
                banners_res = await db_execute(supabase.table("banners").select("banner_text").eq("user_id", user_id).limit(10))
                
                if chats_res.data and banners_res.data:
                    chats = [c["chat_username"] for c in chats_res.data]
                    banners = [b["banner_text"] for b in banners_res.data]

                    for chat in chats:
                        for banner in banners:
                            if sent_to_this_chat >= 10:
                                break
                            try:
                                await client.send_message(chat, banner)
                                sent_to_this_chat += 1
                                await asyncio.sleep(1.5)
                            except Exception as e:
                                print(f"Tabchi Error [User {user_id}] -> {chat}: {e}")
                
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass

    @client.on(events.NewMessage(pattern=r'^\*تبچی روشن$'))
    async def turn_on_tabchi(event):
        user_id = event.sender_id
        
        # ۱. بررسی اینکه آیا از قبل تسکی برای این کاربر در حال اجراست یا خیر
        if user_id in active_tabchis and not active_tabchis[user_id].done():
            return await event.edit("⚠️ تبچی شما از قبل روشن است و در حال کار می‌باشد!")
        
        settings = await db_execute(supabase.table("tabchi_settings").select("delay_seconds").eq("user_id", user_id))
        delay = settings.data[0]["delay_seconds"] if settings.data and "delay_seconds" in settings.data[0] else 20
        
        await db_execute(
            supabase.table("tabchi_settings").upsert({
                "user_id": user_id,
                "is_active": True,
                "delay_seconds": delay
            }, on_conflict="user_id")
        )
        
        # ۲. ایجاد تسک جدید تنها در صورتی که تسک فعالی وجود نداشته باشد
        active_tabchis[user_id] = asyncio.create_task(tabchi_worker(event.client, user_id))
        await event.edit(f"🟢 **تبچی روشن شد!**\n⏱️ سرعت پیش‌فرض: هر {delay} ثانیه یک‌بار.")

    @client.on(events.NewMessage(pattern=r'^\*تبچی خاموش$'))
    async def turn_off_tabchi(event):
        user_id = event.sender_id
        
        await db_execute(
            supabase.table("tabchi_settings").upsert({
                "user_id": user_id,
                "is_active": False
            }, on_conflict="user_id")
        )
        
        if user_id in active_tabchis:
            active_tabchis[user_id].cancel()
            del active_tabchis[user_id]
            
        await event.edit("🔴 **تبچی خاموش شد.**")
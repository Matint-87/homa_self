import asyncio
from telethon import events
from telethon.tl.types import User

# ایمپورت کردن توابع آنلاین سوپابیس از فایل utils
from utils import get_muted_users_from_db, add_muted_user_to_db, remove_muted_user_from_db

def register_mute_handlers(client):
    """
    مدیریت فوق امنیتی، ایزوله و کاملاً مجزا (Multi-Client) بر پایه سوپابیس
    """
    
    # متغیرهای داخلی کلاینت برای کش کردن دیتابیس و آیدی صاحب اکانت
    client.muted_users_list = []
    client.my_own_id = None

    # هندلر کمکی برای مقداردهی اولیه به محض استارت و اولین پیام کلاینت
    @client.on(events.NewMessage(outgoing=True))
    async def initialize_bot(event):
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            # لود کردن لیست سکوت اختصاصی این کلاینت از دیتابیس آنلاین
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            print(f"[*] کلاینت اختصاصی با موفقیت برای آیدی {client.my_own_id} از سوپابیس لود و ایزوله شد.")
        client.remove_event_handler(initialize_bot)


    # --- هندلر اصلی: پاک کردن آنی پیام افراد سکوت شده ---
    @client.on(events.NewMessage(incoming=True))
    async def auto_delete_muted(event):
        # بررسی برای اطمینان از لود شدن آیدی کلاینت جاری
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)

        # اگر آیدی فرستنده در لیست سکوت کش‌شده‌ی این کلاینت بود، پیام حذف می‌شود
        if event.sender_id in client.muted_users_list:
            try:
                await event.delete()
            except Exception as e:
                print(f"Error auto-deleting muted message: {e}")


    # ۱. دستور *سکوت (با ریپلای روی پیام شخص)
    @client.on(events.NewMessage(pattern=r'^\*سکوت$'))
    async def mute_user(event):
        # 🔐 سپر امنیتی ۱: پیام حتماً خروجی (توسط خودت) باشد
        if not event.out:
            return
            
        # 🔐 سپر امنیتی ۲: مطمئن شدن از لود سشن کلاینت صادرکننده
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            
        if event.sender_id != client.my_own_id:
            return
            
        if not event.is_reply:
            await event.edit("⚠️ لطفاً این دستور را روی پیام شخص مورد نظر ریپلای کنید.")
            return
        
        try:
            reply_msg = await event.get_reply_message()
            user_id = reply_msg.sender_id
            
            if user_id:
                if user_id not in client.muted_users_list:
                    # اضافه کردن به دیتابیس سوپابیس
                    if add_muted_user_to_db(client.my_own_id, user_id):
                        client.muted_users_list.append(user_id) # آپدیت کش داخلی
                        await event.edit("🤐 کاربر با موفقیت در لیست سکوت آنلاین شما قرار گرفت.")
                    else:
                        await event.edit("❌ خطایی در اتصال به دیتابیس رخ داد.")
                else:
                    await event.edit("⚠️ این کاربر از قبل در لیست سکوت شما بود.")
        except Exception as e:
            print(f"Error muting user: {e}")


    # ۲. دستور *حذف سکوت (هم با ریپلای و هم با آیدی عددی)
    @client.on(events.NewMessage(pattern=r'^\*حذف سکوت(?:\s+(\d+))?$'))
    async def unmute_user(event):
        if not event.out:
            return
            
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            
        if event.sender_id != client.my_own_id:
            return
            
        user_id = None
        if event.pattern_match.group(1):
            user_id = int(event.pattern_match.group(1))
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            user_id = reply_msg.sender_id
            
        if not user_id:
            await event.edit("⚠️ لطفاً یا روی پیام شخص ریپلای کنید یا آیدی عددی را جلوی دستور وارد کنید.")
            return
        
        try:
            if user_id in client.muted_users_list:
                # حذف از دیتابیس سوپابیس
                if remove_muted_user_from_db(client.my_own_id, user_id):
                    client.muted_users_list.remove(user_id) # آپدیت کش داخلی
                    await event.edit(f"🔊 کاربر (<code>{user_id}</code>) با موفقیت از لیست سکوت شما حذف شد.", parse_mode="html")
                else:
                    await event.edit("❌ خطایی در حذف از دیتابیس رخ داد.")
            else:
                await event.edit("❌ این کاربر در لیست سکوت شما وجود ندارد.")
        except Exception as e:
            print(f"Error unmuting user: {e}")


    # ۳. دستور *لیست سکوت
    @client.on(events.NewMessage(pattern=r'^\*لیست سکوت$'))
    async def show_mute_list(event):
        if not event.out:
            return
            
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            
        if event.sender_id != client.my_own_id:
            return
        
        # آپدیت کردن کش کلاینت قبل از نشان دادن لیست (برای همگام‌سازی دقیق)
        client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            
        if not client.muted_users_list:
            await event.edit("🔇 لیست سکوت اختصاصی شما خالی است.")
            return
            
        msg = await event.edit("🔄 در حال دریافت اطلاعات افراد لیست سکوت از دیتابیس...")
        text = "📑 <b>لیست افراد در حالت سکوت شما:</b>\n\n"
        
        for index, u_id in enumerate(client.muted_users_list, start=1):
            try:
                user = await client.get_entity(u_id)
                if isinstance(user, User):
                    first_name = user.first_name if user.first_name else ""
                    last_name = user.last_name if user.last_name else ""
                    full_name = f"{first_name} {last_name}".strip()
                    if not full_name:
                        full_name = "کاربر بدون نام"
                else:
                    full_name = "چت یا کانال"
            except Exception:
                full_name = "کاربر ناشناس"
                
            text += f"{index}. {full_name} ➔ <code>{u_id}</code>\n"
            
        await msg.edit(text, parse_mode="html")


    # ۴. دستور *پاکسازی سکوت
    @client.on(events.NewMessage(pattern=r'^\*پاکسازی سکوت$'))
    async def clear_mute_list(event):
        if not event.out:
            return
            
        if client.my_own_id is None:
            me = await client.get_me()
            client.my_own_id = me.id
            client.muted_users_list = get_muted_users_from_db(client.my_own_id)
            
        if event.sender_id != client.my_own_id:
            return
            
        try:
            # حذف تمام سطرها از سوپابیس که owner_id آن‌ها برابر با این کلاینت است
            from utils import supabase
            supabase.table("muted_users").delete().eq("owner_id", int(client.my_own_id)).execute()
            
            client.muted_users_list = [] # خالی کردن کش داخلی
            await event.edit("🧹 لیست سکوت اختصاصی شما کاملاً پاکسازی شد.")
        except Exception as e:
            print(f"Error clearing mute list: {e}")
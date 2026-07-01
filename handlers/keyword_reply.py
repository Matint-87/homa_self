import re
from telethon import events

# ---- وارد کردن کلاینت سوپابیس از فایل کانفیگ ----
from config import supabase

# سقف مجاز کلمات کلیدی برای هر کاربر
KEYWORD_LIMIT = 10


def get_bot_status(user_id: int) -> bool:
    """دریافت وضعیت پاسخ خودکار اختصاصی یک کاربر"""
    try:
        res = supabase.table("user_bot_settings").select("keyword_enabled").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]["keyword_enabled"]
    except Exception as e:
        print(f"Error fetching status for {user_id}: {e}")
    return True  # به صورت پیش‌فرض روشن است


def set_bot_status(user_id: int, status: bool):
    """تغییر وضعیت پاسخ خودکار اختصاصی یک کاربر"""
    supabase.table("user_bot_settings").upsert({"user_id": user_id, "keyword_enabled": status}).execute()


def extract_parentheses(text):
    """استخراج محتوای داخل پرانتزها"""
    return re.findall(r'\(([^)]+)\)', text)


def register_keyword_reply(bot):
    """ثبت هندلرهای پاسخ خودکار چندکاربره با محدودیت ثبت کلمه"""
    
    print(f"💬 سیستم پاسخ‌های خودکار چندکاربره (مقیاس بالا) بارگذاری شد.")

    # ********** هندلر روشن کردن **********
    @bot.on(events.NewMessage(pattern=r'^\*پاسخ روشن$'))
    async def enable_keyword(event):
        # فقط صاحب سلف‌بات بتواند دستور را اجرا کند
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        set_bot_status(user_id, True)
        await event.reply("✅ **پاسخ خودکار برای شما روشن شد!**")

    # ********** هندلر خاموش کردن **********
    @bot.on(events.NewMessage(pattern=r'^\*پاسخ خاموش$'))
    async def disable_keyword(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        set_bot_status(user_id, False)
        await event.reply("❌ **پاسخ خودکار برای شما خاموش شد!**")

    # ********** هندلر اضافه کردن پاسخ (با اعمال لیمیت ۱۰۰) **********
    @bot.on(events.NewMessage(pattern=r'^\*پاسخ\s+\(.+\)\s+\(.+\)$'))
    async def add_keyword_reply(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        parts = extract_parentheses(event.message.text)
        
        if len(parts) < 2:
            await event.reply("❌ **فرمت اشتباه!**\n`*پاسخ (کلمه) (پاسخ)`")
            return
        
        keyword = parts[0].strip().lower()
        response = parts[1].strip()
        
        if not keyword or not response:
            await event.reply("❌ کلمه یا پاسخ خالی است!")
            return
            
# 🛑 چک کردن محدودیت ۱۰۰ کلمه برای کاربر
        count_res = supabase.table("keyword_replies").select("id", count="exact").eq("user_id", user_id).execute()
        current_count = count_res.count if hasattr(count_res, 'count') and count_res.count is not None else len(count_res.data)
        
        if current_count >= KEYWORD_LIMIT:
            await event.reply(f"🚫 **محدودیت ظرفیت!** شما حداکثر `{KEYWORD_LIMIT}` کلمه می‌توانید ثبت کنید.\n"
                              f"تعداد فعلی شما: {current_count}")
            return
        
        reply_type = "contains"
        if len(parts) >= 3 and parts[2].lower() in ['دقیق', 'exact']:
            reply_type = "exact"
        
        # بررسی موجود بودن این کلمه *فقط برای این کاربر*
        check = supabase.table("keyword_replies").select("id").eq("user_id", user_id).eq("keyword", keyword).execute()
        if check.data:
            await event.reply(f"⚠️ کلمه `{keyword}` قبلاً توسط شما ثبت شده!\n"
                              f"برای ویرایش: `*ویرایش پاسخ ({keyword}) ({response})`")
            return
        
        # ذخیره با آیدی خود کاربر در Supabase
        supabase.table("keyword_replies").insert({
            "user_id": user_id,
            "keyword": keyword,
            "response": response,
            "type": reply_type
        }).execute()
        
        type_text = "🎯 دقیق" if reply_type == "exact" else "🔍 شامل"
        await event.reply(
            f"✅ **پاسخ جدید اضافه شد!**\n"
            f"🔑 کلمه: `{keyword}`\n"
            f"💬 پاسخ: `{response}`\n"
            f"📌 نوع: {type_text}\n"
            f"📊 ظرفیت: {current_count + 1}/{KEYWORD_LIMIT}"
        )

    # ********** هندلر ویرایش پاسخ **********
    @bot.on(events.NewMessage(pattern=r'^\*ویرایش پاسخ\s+\(.+\)\s+\(.+\)$'))
    async def edit_keyword_reply(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        parts = extract_parentheses(event.message.text)
        
        if len(parts) < 2:
            await event.reply("❌ فرمت اشتباه!")
            return
        
        keyword = parts[0].strip().lower()
        response = parts[1].strip()
        
        # بررسی و دریافت اطلاعات کلمه متعلق به همین کاربر
        check = supabase.table("keyword_replies").select("response").eq("user_id", user_id).eq("keyword", keyword).execute()
        if not check.data:
            await event.reply(f"❌ کلمه `{keyword}` در لیست شما یافت نشد!")
            return
        
        old_response = check.data[0]['response']
        
        # آپدیت مشروط به آیدی کاربر
        supabase.table("keyword_replies").update({"response": response}).eq("user_id", user_id).eq("keyword", keyword).execute()
        
        await event.reply(
            f"✏️ **پاسخ ویرایش شد!**\n"
            f"🔑 کلمه: `{keyword}`\n"
            f"📝 قبلی: `{old_response}`\n"
            f"✨ جدید: `{response}`"
        )

    # ********** هندلر حذف پاسخ **********
    @bot.on(events.NewMessage(pattern=r'^\*حذف پاسخ\s+\(.+\)$'))
    async def remove_keyword_reply(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        parts = extract_parentheses(event.message.text)
        
        if not parts:
            await event.reply("❌ فرمت اشتباه!")
            return
        
        keyword = parts[0].strip().lower()
        
        # حذف ایمن فقط برای کلمه خود کاربر
        delete_res = supabase.table("keyword_replies").delete().eq("user_id", user_id).eq("keyword", keyword).execute()
        
        if not delete_res.data:
            await event.reply(f"❌ کلمه `{keyword}` در لیست شما یافت نشد!")
            return
        
        await event.reply(
            f"🗑️ **پاسخ حذف شد!**\n"
            f"🔑 کلمه: `{keyword}`\n"
            f"💬 پاسخ حذف شده: `{delete_res.data[0]['response']}`"
        )

    # ********** هندلر لیست پاسخ‌ها **********
    @bot.on(events.NewMessage(pattern=r'^\*لیست پاسخ$'))
    async def list_keywords(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        # فیلتر بر اساس کاربر
        res = supabase.table("keyword_replies").select("*").eq("user_id", user_id).execute()
        if not res.data:
            await event.reply("📭 هیچ پاسخی ثبت نکرده‌اید!")
            return
        
        reply_list = []
        for i, row in enumerate(res.data, 1):
            type_emoji = "🎯" if row['type'] == 'exact' else "🔍"
            reply_list.append(
                f"{i}. {type_emoji} `{row['keyword']}`\n"
                f"   └ {row['response'][:100]}"
            )
        
        is_enabled = get_bot_status(user_id)
        text = '\n\n'.join(reply_list)
        await event.reply(
            f"📋 **لیست پاسخ‌های خودکار شما** ({len(res.data)}/{KEYWORD_LIMIT} مورد):\n\n"
            f"{text}\n\n"
            f"💡 وضعیت سلف‌بات شما: {'✅ روشن' if is_enabled else '❌ خاموش'}\n"
            f"🎯 = دقیق | 🔍 = شبیه"
        )

    # ********** هندلر پاکسازی کامل کلمات یک کاربر **********
    @bot.on(events.NewMessage(pattern=r'^\*پاکسازی پاسخ$'))
    async def clear_keywords(event):
        if event.sender_id != (await bot.get_me()).id: return
        
        user_id = event.sender_id
        # فقط کلمات این کاربر حذف می‌شوند
        res = supabase.table("keyword_replies").delete().eq("user_id", user_id).execute()
        count = len(res.data) if res.data else 0
        
        await event.reply(f"🗑️ **هر {count} پاسخ شما از دیتابیس حذف شدند!**")

    # ********** هندلر اصلی پاسخ‌دهی به پیام‌های دریافتی **********
    @bot.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        if event.out or not event.message.text:
            return
        
        # 🛑 بسیار مهم: تشخیص اینکه پیام داخل اکانتِ کدام کاربر دریافت شده است
        # در سلف‌بات مالتی‌اکانت، `event.client.get_me()` مشخص می‌کند پیام روی کدام خط آمده است.
        current_bot_user = await event.client.get_me()
        bot_owner_id = current_bot_user.id
            
        # بررسی وضعیت روشن بودن ماژول برای صاحب این خط
        if not get_bot_status(bot_owner_id):
            return
        
        if event.message.text.startswith('*'):
            return
        
        message_text = event.message.text.lower()
        
        # دریافت کلمات کلیدی اختصاصی صاحب این سلف‌بات
        res = supabase.table("keyword_replies").select("*").eq("user_id", bot_owner_id).execute()
        if not res.data:
            return
            
        for row in res.data:
            keyword = row['keyword']
            should_reply = False
            
            if row['type'] == 'exact':
                if message_text == keyword:
                    should_reply = True
            else:
                if keyword in message_text:
                    should_reply = True
            
            if should_reply:
                try:
                    sender = await event.get_sender()
                    response = row['response']
                    
                    name = sender.first_name or "کاربر"
                    username = f"@{sender.username}" if sender.username else "ندارد"
                    current_time = __import__('datetime').datetime.now().strftime("%H:%M")
                    truncated_text = event.message.text[:50]
                    
                    response = response.replace('{name}', name)
                    response = response.replace('{username}', username)
                    response = response.replace('{time}', current_time)
                    response = response.replace('{text}', truncated_text)
                    
                    await event.reply(response)
                    print(f"💬 [User {bot_owner_id}] پاسخ به {name}: {keyword}")
                except Exception as e:
                    print(f"خطا در پاسخ خودکار: {e}")
                break
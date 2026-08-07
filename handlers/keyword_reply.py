import re
import datetime
from telethon import events

# ---- استفاده از asyncpg pool مشترک تعریف‌شده در utils.py ----
from utils import get_pool
from cachetools import TTLCache

# سقف مجاز کلمات کلیدی برای هر کاربر
KEYWORD_LIMIT = 10

# ============================================================================
# 🧠 کش برای مسیر داغ (hot path):
# قبلاً «keyword_handler» روی هر پیام ورودی از هر کاربر یک کوئری جدا به
# دیتابیس می‌زد (هم برای وضعیت روشن/خاموش، هم برای کل لیست کلمات کلیدی).
# با ۸۰۰۰ کاربر همزمان و ترافیک پیام بالا، این دقیقاً همون نقطه‌ای بود که
# دیتابیس رو زیر فشار می‌بره. حالا این دو مورد کش می‌شن و فقط وقتی چیزی
# واقعاً تغییر کنه (یا TTL تموم بشه) دوباره از دیتابیس خونده می‌شن.
# ============================================================================
CACHE_BOT_STATUS = TTLCache(maxsize=20000, ttl=1800)   # وضعیت روشن/خاموش هر کاربر
CACHE_KEYWORDS = TTLCache(maxsize=20000, ttl=300)       # لیست کلمات کلیدی هر کاربر


async def get_bot_status(user_id: int) -> bool:
    """دریافت وضعیت پاسخ خودکار اختصاصی یک کاربر (با کش)"""
    if user_id in CACHE_BOT_STATUS:
        return CACHE_BOT_STATUS[user_id]
    try:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT keyword_enabled FROM user_bot_settings WHERE user_id = $1", user_id
        )
        status = row["keyword_enabled"] if row else True
    except Exception as e:
        print(f"Error fetching status for {user_id}: {e}")
        status = True  # به صورت پیش‌فرض روشن است
    CACHE_BOT_STATUS[user_id] = status
    return status


async def set_bot_status(user_id: int, status: bool):
    """تغییر وضعیت پاسخ خودکار اختصاصی یک کاربر"""
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO user_bot_settings (user_id, keyword_enabled)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET keyword_enabled = EXCLUDED.keyword_enabled
        """,
        user_id, status,
    )
    CACHE_BOT_STATUS[user_id] = status


async def get_keywords_cached(user_id: int):
    """دریافت کل لیست کلمات کلیدی یک کاربر (با کش، برای مسیر داغ پیام‌ها)"""
    if user_id in CACHE_KEYWORDS:
        return CACHE_KEYWORDS[user_id]
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM keyword_replies WHERE user_id = $1", user_id
    )
    data = [dict(row) for row in rows]
    CACHE_KEYWORDS[user_id] = data
    return data


def invalidate_keywords_cache(user_id: int):
    """باطل کردن کش کلمات کلیدی بعد از هر تغییر (افزودن/ویرایش/حذف/پاکسازی)"""
    CACHE_KEYWORDS.pop(user_id, None)


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
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        await set_bot_status(user_id, True)
        await event.reply("✅ **پاسخ خودکار برای شما روشن شد!**")

    # ********** هندلر خاموش کردن **********
    @bot.on(events.NewMessage(pattern=r'^\*پاسخ خاموش$'))
    async def disable_keyword(event):
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        await set_bot_status(user_id, False)
        await event.reply("❌ **پاسخ خودکار برای شما خاموش شد!**")

    # ********** هندلر اضافه کردن پاسخ (با اعمال لیمیت) **********
    @bot.on(events.NewMessage(pattern=r'^\*پاسخ\s+\(.+\)\s+\(.+\)$'))
    async def add_keyword_reply(event):
        if event.sender_id != (await bot.get_me()).id:
            return

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

        pool = get_pool()

        # 🛑 چک کردن محدودیت کلمه برای کاربر
        current_count = await pool.fetchval(
            "SELECT COUNT(*) FROM keyword_replies WHERE user_id = $1", user_id
        )

        if current_count >= KEYWORD_LIMIT:
            await event.reply(f"🚫 **محدودیت ظرفیت!** شما حداکثر `{KEYWORD_LIMIT}` کلمه می‌توانید ثبت کنید.\n"
                              f"تعداد فعلی شما: {current_count}")
            return

        reply_type = "contains"
        if len(parts) >= 3 and parts[2].lower() in ['دقیق', 'exact']:
            reply_type = "exact"

        # بررسی موجود بودن این کلمه *فقط برای این کاربر*
        existing = await pool.fetchrow(
            "SELECT id FROM keyword_replies WHERE user_id = $1 AND keyword = $2",
            user_id, keyword,
        )
        if existing:
            await event.reply(f"⚠️ کلمه `{keyword}` قبلاً توسط شما ثبت شده!\n"
                              f"برای ویرایش: `*ویرایش پاسخ ({keyword}) ({response})`")
            return

        # ذخیره با آیدی خود کاربر در دیتابیس
        await pool.execute(
            """
            INSERT INTO keyword_replies (user_id, keyword, response, type)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, keyword, response, reply_type,
        )
        invalidate_keywords_cache(user_id)

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
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        parts = extract_parentheses(event.message.text)

        if len(parts) < 2:
            await event.reply("❌ فرمت اشتباه!")
            return

        keyword = parts[0].strip().lower()
        response = parts[1].strip()

        pool = get_pool()

        # بررسی و دریافت اطلاعات کلمه متعلق به همین کاربر
        existing = await pool.fetchrow(
            "SELECT response FROM keyword_replies WHERE user_id = $1 AND keyword = $2",
            user_id, keyword,
        )
        if not existing:
            await event.reply(f"❌ کلمه `{keyword}` در لیست شما یافت نشد!")
            return

        old_response = existing["response"]

        # آپدیت مشروط به آیدی کاربر
        await pool.execute(
            "UPDATE keyword_replies SET response = $1 WHERE user_id = $2 AND keyword = $3",
            response, user_id, keyword,
        )
        invalidate_keywords_cache(user_id)

        await event.reply(
            f"✏️ **پاسخ ویرایش شد!**\n"
            f"🔑 کلمه: `{keyword}`\n"
            f"📝 قبلی: `{old_response}`\n"
            f"✨ جدید: `{response}`"
        )

    # ********** هندلر حذف پاسخ **********
    @bot.on(events.NewMessage(pattern=r'^\*حذف پاسخ\s+\(.+\)$'))
    async def remove_keyword_reply(event):
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        parts = extract_parentheses(event.message.text)

        if not parts:
            await event.reply("❌ فرمت اشتباه!")
            return

        keyword = parts[0].strip().lower()

        # حذف ایمن فقط برای کلمه خود کاربر - با RETURNING متن پاسخِ حذف‌شده رو برمی‌گردونیم
        pool = get_pool()
        deleted_row = await pool.fetchrow(
            "DELETE FROM keyword_replies WHERE user_id = $1 AND keyword = $2 RETURNING response",
            user_id, keyword,
        )

        if not deleted_row:
            await event.reply(f"❌ کلمه `{keyword}` در لیست شما یافت نشد!")
            return

        invalidate_keywords_cache(user_id)
        await event.reply(
            f"🗑️ **پاسخ حذف شد!**\n"
            f"🔑 کلمه: `{keyword}`\n"
            f"💬 پاسخ حذف شده: `{deleted_row['response']}`"
        )

    # ********** هندلر لیست پاسخ‌ها **********
    @bot.on(events.NewMessage(pattern=r'^\*لیست پاسخ$'))
    async def list_keywords(event):
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        # فیلتر بر اساس کاربر
        pool = get_pool()
        rows = await pool.fetch(
            "SELECT * FROM keyword_replies WHERE user_id = $1", user_id
        )
        if not rows:
            await event.reply("📭 هیچ پاسخی ثبت نکرده‌اید!")
            return

        reply_list = []
        for i, row in enumerate(rows, 1):
            type_emoji = "🎯" if row['type'] == 'exact' else "🔍"
            reply_list.append(
                f"{i}. {type_emoji} `{row['keyword']}`\n"
                f"   └ {row['response'][:100]}"
            )

        is_enabled = await get_bot_status(user_id)
        text = '\n\n'.join(reply_list)
        await event.reply(
            f"📋 **لیست پاسخ‌های خودکار شما** ({len(rows)}/{KEYWORD_LIMIT} مورد):\n\n"
            f"{text}\n\n"
            f"💡 وضعیت سلف‌بات شما: {'✅ روشن' if is_enabled else '❌ خاموش'}\n"
            f"🎯 = دقیق | 🔍 = شبیه"
        )

    # ********** هندلر پاکسازی کامل کلمات یک کاربر **********
    @bot.on(events.NewMessage(pattern=r'^\*پاکسازی پاسخ$'))
    async def clear_keywords(event):
        if event.sender_id != (await bot.get_me()).id:
            return

        user_id = event.sender_id
        # فقط کلمات این کاربر حذف می‌شوند - با RETURNING تعداد ردیف‌های حذف‌شده رو می‌شماریم
        pool = get_pool()
        deleted_rows = await pool.fetch(
            "DELETE FROM keyword_replies WHERE user_id = $1 RETURNING id", user_id
        )
        count = len(deleted_rows)

        invalidate_keywords_cache(user_id)
        await event.reply(f"🗑️ **هر {count} پاسخ شما از دیتابیس حذف شدند!**")

    # ********** هندلر اصلی پاسخ‌دهی به پیام‌های دریافتی **********
    @bot.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        if event.out or not event.message.text:
            return

        # 🛑 بسیار مهم: تشخیص اینکه پیام داخل اکانتِ کدام کاربر دریافت شده است
        current_bot_user = await event.client.get_me()
        bot_owner_id = current_bot_user.id

        # بررسی وضعیت روشن بودن ماژول برای صاحب این خط (از کش، نه هر بار دیتابیس)
        if not await get_bot_status(bot_owner_id):
            return

        if event.message.text.startswith('*'):
            return

        message_text = event.message.text.lower()

        # دریافت کلمات کلیدی اختصاصی صاحب این سلف‌بات (از کش، نه هر بار دیتابیس)
        keywords = await get_keywords_cached(bot_owner_id)
        if not keywords:
            return

        for row in keywords:
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
                    current_time = datetime.datetime.now().strftime("%H:%M")
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
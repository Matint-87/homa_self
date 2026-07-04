import asyncio
from telethon import events
from config import supabase
from utils import db_execute

# لیست کلمات پیش‌فرض برای کاربران جدید
DEFAULT_FRIENDS = ["الهی من فداتشم", "عاشقتم لعنتی", "نوازش موهات مرا مست میکند", "تو برام با ارزش ترین هدیه ای", "بدون تو زندگی معنا نداره", "بغلت برام امن ترین جاست", "جزو آرزوهامی تو", "خیلی دوستت دارم", "خداروشکر بابت بودنت", "قشنگ ترین فرشته"]
DEFAULT_ENEMIES = ["کیر تو کص مادرت", "مامانتو خوردم", "حرومزاده بی وجود", "خیلی مامانتو دوست دارم", "بی خایه کصخل", "برج خلیفه تو کص ننت", "مادرت ارضام کرد", "اوب زاده", "چه کون قشنگی داری", "دهن مادرتو گاییدم"]

# 🧠 کِش مرکزی در رم برای حذف کامل تاخیر دیتابیس
GLOBAL_CACHE = {}
# 🔄 ذخیره آخرین اندیس پیام ارسال شده برای هر قربانی جهت ارسال ترتیبی و چرخشی
TARGET_COUNTERS = {}


async def get_or_create_settings_cached(owner_id: int) -> dict:
    """دریافت تنظیمات از رم؛ اگر نبود از سوپابیس می‌خواند"""
    if owner_id in GLOBAL_CACHE:
        return GLOBAL_CACHE[owner_id]

    try:
        query = supabase.table("maho_user_settings").select("*").eq("owner_id", owner_id)
        res = await db_execute(query)
        if res.data:
            GLOBAL_CACHE[owner_id] = res.data[0]
            return GLOBAL_CACHE[owner_id]

        new_settings = {
            "owner_id": owner_id,
            "friends": DEFAULT_FRIENDS,
            "enemies": DEFAULT_ENEMIES,
            "target_friends": [],
            "target_enemies": []
        }
        insert_query = supabase.table("maho_user_settings").insert(new_settings)
        await db_execute(insert_query)
        GLOBAL_CACHE[owner_id] = new_settings
        return new_settings
    except Exception as e:
        print(f"Error in Supabase Cache operation: {e}")
        return None


def register_reply_handlers(client):
    print("⚡ ماژول دوست/دشمن (نسخه چرخشی، ترتیبی و بدون تداخل) بارگذاری شد.")

    # 1️⃣ شلیک خودکار، ترتیبی و آنی (Looping & Sequential)
    @client.on(events.NewMessage(incoming=True))
    async def auto_responder(event):
        if not event.sender_id:
            return

        me = await event.client.get_me()
        owner_id = me.id
        target_id = event.sender_id

        # بررسی کِش رم بدون ایجاد ریکوئست به شبکه
        settings = GLOBAL_CACHE.get(owner_id)
        if not settings:
            settings = await get_or_create_settings_cached(owner_id)
            if not settings:
                return

        # بررسی وضعیت کاربر (دوست یا دشمن)
        is_friend = target_id in settings.get("target_friends", [])
        is_enemy = target_id in settings.get("target_enemies", [])

        if not is_friend and not is_enemy:
            return

        # تعیین نوع کلمات و کلید کِش ترتیب
        field = "friends" if is_friend else "enemies"
        words = settings.get(field, [])
        if not words:
            return

        # 🔄 مکانیزم ارسال به ترتیب و چرخشی (Round-Robin)
        counter_key = f"{owner_id}_{target_id}"
        current_index = TARGET_COUNTERS.get(counter_key, 0)

        # اگر تعداد کلمات تغییر کرده بود و اندیس بزرگتر شده بود، ریست شود
        if current_index >= len(words):
            current_index = 0

        chosen_word = words[current_index]

        # آپدیت اندیس برای پیام بعدی (برگشت به اول در صورت رسیدن به انتها)
        TARGET_COUNTERS[counter_key] = (current_index + 1) % len(words)

        # ارسال پاسخ فوری
        try:
            await event.reply(chosen_word)
        except Exception as e:
            print(f"Send message error: {e}")

    # 2️⃣ قفل کردن روی هدف (یا فقط دوست یا فقط دشمن)
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*(دوست|دشمن)$"))
    async def set_target(event):
        if not event.is_reply:
            await event.edit("لطفا روی پیام شخص موردنظر ریپلای کنید!")
            return

        me = await event.client.get_me()
        owner_id = me.id
        command = event.pattern_match.group(1)

        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id
        if not target_id:
            return

        await event.delete()
        settings = await get_or_create_settings_cached(owner_id)
        if not settings:
            return

        # تبدیل به set برای حذف همپوشانی‌ها
        t_friends = set(settings.get("target_friends", []))
        t_enemies = set(settings.get("target_enemies", []))

        # 🔒 انحصار متقابل: یک کاربر نمی‌تواند هم‌زمان هم دوست باشد هم دشمن
        if command == "دوست":
            t_friends.add(target_id)
            t_enemies.discard(target_id)  # حذف اجباری از دشمنان
            msg = "<blockquote>از این به بعد این شخص دوست منه و قربون صدقش میرم!</blockquote>"
        else:
            t_enemies.add(target_id)
            t_friends.discard(target_id)  # حذف اجباری از دوستان
            msg = "<blockquote>از این به بعد این شخص دشمن منه و فوش بارون میشه!</blockquote>"

        # ریست کردن شمارنده چرخشی این کاربر
        TARGET_COUNTERS[f"{owner_id}_{target_id}"] = 0

        # آپدیت رم و سوپابیس
        settings["target_friends"] = list(t_friends)
        settings["target_enemies"] = list(t_enemies)
        GLOBAL_CACHE[owner_id] = settings

        update_query = supabase.table("maho_user_settings").update({
            "target_friends": settings["target_friends"],
            "target_enemies": settings["target_enemies"]
        }).eq("owner_id", owner_id)
        await db_execute(update_query)

        await event.respond(msg, parse_mode='html')

    # 3️⃣ لغو قفل روی هدف (*حذف دوست یا *حذف دشمن)
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*حذف (دوست|دشمن)$"))
    async def remove_target(event):
        if not event.is_reply:
            await event.edit("<blockquote>لطفا برای حذف وضعیت، روی پیام خود شخص ریپلای کنید!</blockquote>", parse_mode='html')
            return

        me = await event.client.get_me()
        owner_id = me.id
        command = event.pattern_match.group(1)

        reply_msg = await event.get_reply_message()
        target_id = reply_msg.sender_id

        settings = await get_or_create_settings_cached(owner_id)
        if not settings:
            return

        # حذف شمارنده چرخشی برای خالی شدن مموری
        TARGET_COUNTERS.pop(f"{owner_id}_{target_id}", None)

        if command == "دوست":
            targets = settings.get("target_friends", [])
            if target_id in targets:
                targets.remove(target_id)
            settings["target_friends"] = targets
            GLOBAL_CACHE[owner_id] = settings
            update_query = supabase.table("maho_user_settings").update({"target_friends": targets}).eq("owner_id", owner_id)
            await db_execute(update_query)
        else:
            targets = settings.get("target_enemies", [])
            if target_id in targets:
                targets.remove(target_id)
            settings["target_enemies"] = targets
            GLOBAL_CACHE[owner_id] = settings
            update_query = supabase.table("maho_user_settings").update({"target_enemies": targets}).eq("owner_id", owner_id)
            await db_execute(update_query)

        text = f"<blockquote> شخص موردنظر از لیست {command}ان شما حذف شد و وضعیت عادی شد.</blockquote>"
        await event.edit(text, parse_mode='html')

    # 4️⃣ مشاهده لیست کاربران هدف (*لیست دوست یا *لیست دشمن)
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*لیست (دوست|دشمن)$"))
    async def handle_list(event):
        me = await event.client.get_me()
        owner_id = me.id
        command = event.pattern_match.group(1)

        # مشخص کردن فیلد مربوط به تارگت‌ها در JSONB
        field = "target_friends" if command == "دوست" else "target_enemies"

        settings = await get_or_create_settings_cached(owner_id)
        if not settings:
            return

        targets = settings.get(field, [])
        title = "لیست کاربران دوست شما:" if command == "دوست" else " لیست کاربران دشمن شما:"

        if targets:
            msg_text = f"<blockquote><b>{title}</b>\n\n"
            for i, target_id in enumerate(targets, 1):
                msg_text += f"{i}_ آیدی: <code>{target_id}</code> | <a href='tg://user?id={target_id}'>پروفایل کاربر</a>\n"
            msg_text += "</blockquote>"
            await event.edit(msg_text, parse_mode='html')
        else:
            await event.edit(f"<blockquote>لیست کاربران {command} شما خالی است.</blockquote>", parse_mode='html')

    # 5️⃣ افزودن کلمه جدید (*دوست افزودن متن)
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*(دوست|دشمن) افزودن (.+)$"))
    async def handle_add_word(event):
        me = await event.client.get_me()
        owner_id = me.id
        command = event.pattern_match.group(1)
        field = "friends" if command == "دوست" else "enemies"
        new_text = event.pattern_match.group(2).strip()

        settings = await get_or_create_settings_cached(owner_id)
        if not settings:
            return

        words = settings.get(field, [])
        if new_text not in words:
            words.append(new_text)

            settings[field] = words
            GLOBAL_CACHE[owner_id] = settings

            update_query = supabase.table("maho_user_settings").update({field: words}).eq("owner_id", owner_id)
            await db_execute(update_query)
            await event.edit(f"<blockquote> کلمه جدید به لیست {command} شما اضافه شد.</blockquote>", parse_mode='html')
        else:
            await event.edit("<blockquote> این کلمه از قبل در لیست شما موجود است.</blockquote>", parse_mode='html')
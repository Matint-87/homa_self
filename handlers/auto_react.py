import re
from telethon import events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji

# ذخیره وضعیت ریکشن‌ها: { user_id: { target_user_id: emoji } }
# این ساختار برای مولتی‌کاربره بودن سلف‌بات کاملاً استاندارد است.
active_reactions = {}

def register_auto_react(client):

    # ۱. هندلر ثبت ریکشن روی یک کاربر (با ریپلای یا با آیدی/یوزرنیم)
    @client.on(events.NewMessage(pattern=r"^\*?ریکت\s+(.+)"))
    async def set_reaction(event):
        if not event.out:
            return
        
        user_id = event.sender_id
        if user_id not in active_reactions:
            active_reactions[user_id] = {}

        text = event.pattern_match.group(1).strip()

        # الف) حالت حذف: *ریکت [یوزرنیم/آیدی] حذف
        if text.endswith("حذف"):
            target_str = text.replace("حذف", "").strip()
            try:
                # پیدا کردن کاربر از روی آیدی یا یوزرنیم
                target_user = await client.get_input_entity(target_str)
                target_id = getattr(target_user, 'user_id', None)
                
                if target_id in active_reactions[user_id]:
                    del active_reactions[user_id][target_id]
                    await event.reply(f"❌ ریکشن خودکار برای کاربر {target_str} خاموش شد.")
                else:
                    await event.reply(f"❓ این کاربر در لیست ریکشن‌های فعال شما نبود.")
            except Exception as e:
                await event.reply(f"❌ کاربر یافت نشد یا خطا رخ داد: {e}")
            return

        # ب) حالت خاموش کردن کل ریکشن‌ها برای خود کاربر: *ریکت خاموش
        if text == "خاموش":
            active_reactions[user_id] = {}
            await event.reply("🛑 تمام ریکشن‌های خودکار شما غیرفعال و لیست پاک شد.")
            return

        # ج) حالت اصلی: ست کردن ریکشن با ریپلای روی پیام طرف
        emoji = text
        if not event.is_reply:
            await event.reply("⚠️ لطفاً روی پیام کاربر مورد نظر ریپلای کنید و دستور را بفرستید!\nمثال: `*ریکت 😂`")
            return

        try:
            reply_msg = await event.get_reply_message()
            target_id = reply_msg.sender_id

            if not target_id:
                await event.reply("❌ امکان تشخیص فرستنده پیام وجود ندارد.")
                return

            # ذخیره کردن ریکشن برای کاربر هدف
            active_reactions[user_id][target_id] = emoji
            await event.reply(f"✅ ریکشن خودکار فعال شد!\nاز این به بعد به پیام‌های این کاربر ریکشن {emoji} زده میشه.")
        except Exception as e:
            await event.reply(f"❌ خطا در ثبت ریکشن: {e}")


    # ۲. هندلر نمایش لیست افراد تحت ریکشن: *لیست ریکت
    @client.on(events.NewMessage(pattern=r"^\*?لیست ریکت$"))
    async def list_reactions(event):
        if not event.out:
            return
        
        user_id = event.sender_id
        user_list = active_reactions.get(user_id, {})

        if not user_list:
            await event.reply("📝 لیست ریکشن‌های خودکار شما خالی است.")
            return

        response = "📋 **لیست ریکشن‌های خودکار فعال:**\n\n"
        for t_id, emoji in user_list.items():
            try:
                entity = await client.get_entity(t_id)
                name = getattr(entity, 'first_name', 'کاربر تلگرام')
                username = f"@{entity.username}" if getattr(entity, 'username', None) else f"`{t_id}`"
                response += f"👤 {name} ({username}) 👈 ریکشن: {emoji}\n"
            except:
                response += f"👤 کاربر با آیدی `{t_id}` 👈 ریکشن: {emoji}\n"

        await event.reply(response)


    # ۳. هندلر اصلی: تشخیص پیام‌های جدید کاربران هدف و زدن ریکشن خودکار
    @client.on(events.NewMessage)
    async def incoming_message_reactor(event):
        # اگر پیام از طرف خودمون بود یا توی چت خصوصی/گروه فرستنده نداشت، کاری نکن
        if event.out or not event.sender_id:
            return

        # پیدا کردن اینکه آیا صاحب این سلف‌بات روی این کاربر ریکشن ست کرده یا نه
        # چون ربات مولتی‌اکانت هست، باید بر اساس آیدی ربات (بات سلف) چک کنیم که پیام کجاست
        try:
            # گرفتن آیدی اکانتی که این پیام رو دریافت کرده
            bot_user_id = (await event.client.get_me()).id
            
            user_reactions = active_reactions.get(bot_user_id, {})
            if event.sender_id in user_reactions:
                chosen_emoji = user_reactions[event.sender_id]
                
                # ارسال ریکشن به پیام جدید
                await event.client(SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=event.id,
                    reaction=[ReactionEmoji(emoticon=chosen_emoji)]
                ))
        except Exception as e:
            # چاپ خطا در کنسول برای دیباگ (بدون ایجاد مزاحمت در چت)
            print(f"خطا در زدن ریکشن خودکار: {e}")
import asyncio
from telethon import events

ACTION_MAP = {
    "تایپ": "typing",
    "ویس": "record-audio",
    "عکس": "upload-photo",
    "ویدیو": "upload-video",
    "ویدیومجیک": "record-round",
    "فایل": "upload-document",
    "گیم": "game",
    "استیکر": "choose-sticker"
}

# دیکشنری تسک‌ها زنده می‌ماند
active_actions = {}

def register_action_handler(client):
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*اکشن\s+(.+)$"))
    async def chat_action_manager(event):
        me = await event.client.get_me()
        if event.sender_id != me.id:
            return
            
        action_type = event.pattern_match.group(1).strip()
        chat_id = event.chat_id
        
        # 🔑 ساخت یک کلید منحصربه‌فرد ترکیبی از (آیدی صاحب سلف‌بات , آیدی گپ)
        user_chat_key = (me.id, chat_id)
        
        # ۱. حالت لغو کردن اکشن فعال
        if action_type == "لغو":
            if user_chat_key in active_actions:
                active_actions[user_chat_key].cancel()
                del active_actions[user_chat_key]
                await event.edit("🛑 **وضعیت اکشن در این چت متوقف شد.**")
            else:
                await event.edit("❌ **اکشن فعالی در این چت وجود ندارد.**")
            return

        if action_type not in ACTION_MAP:
            await event.edit(
                "❌ **نوع اکشن نامعتبر است!**\n"
                "لیست اکشن‌ها:\n"
                "`تایپ` | `ویس` | `عکس` | `ویدیو` | `ویدیومجیک` | `فایل` | `گیم` | `استیکر` | `لغو`"
            )
            return

        # ۲. لغو کردن اکشن قبلی همین کاربر در این چت
        if user_chat_key in active_actions:
            active_actions[user_chat_key].cancel()

        telegram_action = ACTION_MAP[action_type]

        async def action_loop():
            try:
                while True:
                    async with client.action(chat_id, telegram_action):
                        await asyncio.sleep(4)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(action_loop())
        # ذخیره بر اساس کلید اختصاصی اکانت
        active_actions[user_chat_key] = task
        
        await event.edit(f"✅ **وضعیت «{action_type}» برای بقیه فعال شد.**")
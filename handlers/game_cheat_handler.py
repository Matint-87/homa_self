import asyncio
from telethon import events, functions, types

def register_game_cheat_handler(client):
    """
    نسخه مالتی‌چت و همه‌جاکار: فعال در گروه، کانال، پی‌وی و Saved Messages
    """

    # ۱. متد اینلاین مخصوص فوتبال و بسکتبال
    async def send_inline_dice(event, emoticon):
        chat_id = event.chat_id
        bot_client = event.client
        try:
            inline_results = await bot_client.inline_query('dice', emoticon)
            if inline_results:
                await inline_results[0].click(chat_id)
        except Exception:
            await bot_client.send_message(chat_id, emoticon)

    # ۲. متد ارسال بومی دایس تلگرام برای تاس، کازینو، دارت و بولینگ
    async def send_perfect_dice(event, emoticon):
        chat_id = event.chat_id
        bot_client = event.client
        try:
            await bot_client(functions.messages.SendMediaRequest(
                peer=chat_id,
                media=types.InputMediaDice(emoticon=emoticon),
                message=""
            ))
        except Exception:
            await bot_client.send_message(chat_id, emoticon)

    # ==================================================================
    # هندلرهای بدون محدودیت فضا (اجرا در همه‌جا)
    # ==================================================================

    @client.on(events.MessageEdited(outgoing=True, pattern=r"(?i)^\*?(?:شوت|shoot|فوتبال)$"))
    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\*?(?:شوت|shoot|فوتبال)$"))
    async def football(event):
        await event.delete()
        await send_inline_dice(event, "⚽")

    @client.on(events.MessageEdited(outgoing=True, pattern=r"(?i)^\*?(?:بسکتبال|basketball)$"))
    @client.on(events.NewMessage(outgoing=True, pattern=r"(?i)^\*?(?:بسکتبال|basketball)$"))
    async def basketball(event):
        await event.delete()
        await send_inline_dice(event, "🏀")
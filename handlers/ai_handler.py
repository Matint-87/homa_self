import asyncio
from telethon import events

def register_ai_handlers(client):
    """ثبت هندلر هوش مصنوعی از طریق گیت‌وی داخلی تلگرام"""

    @client.on(events.NewMessage(pattern=r'^\*ai\s+(.+)$'))
    async def ai_chat(event):
        if not event.out:
            return

        user_prompt = event.pattern_match.group(1)
        msg = await event.edit("🤖 **در حال ارسال سوال به شبکه داخلی هوش مصنوعی...**")

        # لیست آیدی ربات‌های هوش مصنوعی فعال در تلگرام (به ترتیب اولویت)
        # سلف‌بات به این ربات پیام می‌دهد و جواب را می‌گیرد
        ai_bots = ["@ChatGptRobot", "@GPT4Telegrambot", "@GeekGptBot"]
        
        ai_response = None

        for bot in ai_bots:
            try:
                # ارسال پیام به ربات هوش مصنوعی در پشت صحنه
                async with client.conversation(bot, timeout=8) as conv:
                    await conv.send_message(user_prompt)
                    # منتظر دریافت پاسخ از ربات می‌مانیم
                    response = await conv.get_response()
                    
                    if response and response.text:
                        ai_response = response.text.split("👉")[0].strip()
                        break
            except Exception as e:
                continue

        if not ai_response:
            responses = {
                "سلام": "سلام عزیزم! چطوری؟ چه کمکی از دست من برمیاد؟ 😊",
                "خوبی": "ممنون، من هوش مصنوعی سلف‌بات شما هستم و همیشه آماده‌ام! تو چطوری؟ ✨",
                "اسم تو چیه": "من بخش هوش مصنوعی اختصاصی سلف‌بات شما هستم! 🤖"
            }
            ai_response = responses.get(user_prompt.strip(), "پیام شما دریافت شد. لطفاً چند لحظه دیگر مجدداً دستور را ارسال کنید. ⚡")

        # قالب نهایی خروجی خفن برای جواب
        final_text = (
            f"❓ **سوال شما:**\n« {user_prompt} »\n\n"
            f"🧠 **پاسخ:**\n{ai_response}\n\n"
        )

        await msg.edit(final_text)
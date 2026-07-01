import asyncio
from telethon import events
from telethon.tl.types import InputMediaDice

def register_game_handlers(client):
    """ثبت هندلرهای بازی به روش تغییر مداوم مدیا در یک پیام (بدون حذف و ارسال مجدد)"""

    print("🎲 ماژول بازی‌های انیمیشنی (نسخه اصلاح‌شده تغییر مدیا) بارگذاری شد.")

    async def force_cheat_in_place(chat_id, command_msg, emoticon, target_value=None, win_values=None):
        """تغییر انیمیشن روی همان پیام اول تا قفل شدن روی هدف بدون تولید پیام جدید"""
        # ۱. حذف دستور متنی اولیه برای تمیز شدن چت
        await command_msg.delete()
        
        # ۲. ارسال دایس اولیه
        msg = await client.send_message(chat_id, file=InputMediaDice(emoticon=emoticon))
        
        # اموتیکون کمکی برای سوییچ کردن و ریست کردن دیتای سرور
        backup_emoji = "🎯" if emoticon != "🎯" else "🎲"

        while True:
            if msg.media and hasattr(msg.media, 'value'):
                current_value = msg.media.value
                is_win = (target_value and current_value == target_value) or \
                         (win_values and current_value in win_values)
                
                if is_win:
                    break # عدد یا امتیاز چیت با موفقیت اعمال شد و لوپ متوقف می‌شود
            
            try:
                # ۳. تغییر به یک اموتیکون دیگر برای پاک شدن مقدار قبلی روی سرور
                msg = await client.edit_message(chat_id, msg.id, file=InputMediaDice(emoticon=backup_emoji))
                await asyncio.sleep(0.05)
                
                # ۴. برگشت فوری به اموتیکون اصلی برای دریافت شانس جدید
                msg = await client.edit_message(chat_id, msg.id, file=InputMediaDice(emoticon=emoticon))
                await asyncio.sleep(0.05)
            except Exception as e:
                # جلوگیری از کرش در صورت لیمیت موقت یا تداخل فرکانس تلگرام
                await asyncio.sleep(0.1)

    # ۱. هندلر چیت تاس با عدد دقیق
    @client.on(events.NewMessage(pattern=r'^\*تاس (\d)$'))
    async def cheat_dice(event):
        if not event.out: return
        
        target_value = int(event.pattern_match.group(1))
        if target_value < 1 or target_value > 6: return
            
        chat_id = event.chat_id
        await force_cheat_in_place(chat_id, event, emoticon="🎲", target_value=target_value)

    # ۲. هندلر بقیه بازی‌ها
    @client.on(events.NewMessage(pattern=r'^\*(فوتبال|بسکتبال|دارت|بولینگ|کازینو)$'))
    async def play_cheated_game(event):
        if not event.out: return

        command = event.pattern_match.group(1)
        chat_id = event.chat_id

        game_configs = {
            "فوتبال": {"emoji": "⚽", "win_values": [3, 4, 5]},
            "بسکتبال": {"emoji": "🏀", "win_values": [4, 5]},
            "دارت": {"emoji": "🎯", "win_values": [6]},
            "بولینگ": {"emoji": "🎳", "win_values": [6]},
            "کازینو": {"emoji": "🎰", "win_values": [1, 22, 43, 64]}
        }
        config = game_configs[command]

        await force_cheat_in_place(chat_id, event, emoticon=config["emoji"], win_values=config["win_values"])
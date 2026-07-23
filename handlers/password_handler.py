from telethon import events
import secrets
import string
import html 

def register_password_handler(client):
    
    @client.on(events.NewMessage(pattern=r'\*رمز (\d+)'))
    async def generate_password(event):
        try:
            # دریافت طول از دستور
            length = int(event.pattern_match.group(1))
            
            # محدودیت ۵۰ کاراکتر
            if length > 50:
                await event.edit("⚠️ **خطا:** حداکثر طول رمز نباید بیشتر از ۵۰ باشد.")
                return
            
            # ایجاد کاراکترها
            alphabet = string.ascii_letters + string.digits + string.punctuation

            # تولید رمز امن
            password = ''.join(secrets.choice(alphabet) for i in range(length))

            safe_password = html.escape(password)
            # 2. حالا از تگ‌های استاندارد استفاده می‌کنیم
            text = f"🔐 <b>رمز شما ({length} کاراکتری):</b>\n\n<tg-spoiler><code>{safe_password}</code></tg-spoiler>"
            
            await event.edit(text, parse_mode='html')
            
        except Exception as e:
            await event.edit(f"❌ خطایی رخ داد: {str(e)}")

from telethon import events
import aiohttp  # برای ارسال درخواست به API ربات
# ایمپورت توابع دیتابیس (مطمئن شوید مسیر درست است)
from utils import get_balance, update_balance 
from config import BOT_TOKEN
# مشخصات ربات شما (برای ارسال پیام به گروه از طرف ربات)
TARGET_GROUP_ID = -1004431412108   # آیدی عددی گروه

def register_variz_handler(client):
    # پترن با ستاره شروع می‌شود و عدد بعد از آن را می‌گیرد
    @client.on(events.NewMessage(pattern=r'^\*واریز طلا (\d+)$', outgoing=True))
    async def handle_telethon_transfer(event):
        try:
            # گرفتن مقدار عددی از پترن
            amount = int(event.pattern_match.group(1))
            
            # بررسی اینکه حتما روی پیام کسی ریپلای شده باشد
            reply = await event.get_reply_message()
            if not reply:
                await event.edit("❌ برای واریز، روی پیام کاربر مورد نظر ریپلای کنید!")
                return

            sender = await event.get_sender()
            target = await reply.get_sender()

            # جلوگیری از واریز به خود
            if sender.id == target.id:
                await event.edit("❌ شما نمی‌توانید به خودتان طلا واریز کنید!")
                return

            # بررسی موجودی
            from_balance = await get_balance(sender.id)
            if from_balance < amount:
                await event.edit(f"❌ موجودی کافی نیست. موجودی فعلی: {from_balance:,}")
                return

            # اعمال تراکنش
            if not await update_balance(sender.id, -amount):
                await event.edit("❌ انتقال انجام نشد.")
                return

            if not await update_balance(target.id, amount):
                # در صورت نیاز اینجا موجودی فرستنده را برگردان یا خطا ثبت کن
                await event.edit("❌ خطا در واریز به گیرنده.")
                return

            # ارسال پیام موفقیت و ویرایش پیام دستور
            new_balance = await get_balance(target.id)

            success_message = (
                f"✅ <b>واریز موفقیت‌آمیز!</b>\n\n"
                f"👤 <b>فرستنده:</b> {sender.first_name}\n"
                f"👤 <b>گیرنده:</b> {target.first_name}\n"
                f"💰 <b>مقدار:</b> {amount:,} طلا\n"
                f"💵 <b>معادل تومان:</b> {amount * 35:,} تومان\n\n"
                f"💰 <b>موجودی جدید گیرنده:</b> {new_balance:,} طلا\n"
                f"💵 <b>معادل تومان:</b> {new_balance * 35:,} تومان"
            )

            # ۱. ویرایش پیام خود دستور (پیام شخصی شما)
            await event.edit(success_message, parse_mode='html')

            # ۲. ارسال پیام به گروه از طرف "ربات" (به جای اکانت شما)
            group_text = f"📢 <b>گزارش تراکنش جدید:</b>\n\n" + success_message
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TARGET_GROUP_ID,
                "text": group_text,
                "parse_mode": "HTML"
            }

            try:
                # ارسال درخواست به API تلگرام با استفاده از aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        if response.status != 200:
                            print(f"Error from Telegram API: {await response.text()}")
            except Exception as bot_err:
                print(f"Error sending message via bot to group: {bot_err}")
            
        except Exception as e:
            print(f"Error in telethon transfer: {e}")

            try:
                await event.edit("⚠️ خطایی در انجام تراکنش رخ داد.")
            except:
                await event.reply("⚠️ خطایی در انجام تراکنش رخ داد.")
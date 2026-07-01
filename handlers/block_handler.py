import re
from telethon import events
from telethon.tl.functions.contacts import BlockRequest, UnblockRequest, GetBlockedRequest
from telethon.tl.types import User

def register_block_handlers(client):
    """
    این تابع هندلرهای مربوط به بلاک، آن‌بلاک (ریپلای/آیدی) و لیست بلاک را مدیریت می‌کند.
    """

    # ۱. هندلر دستور *بلاک (فقط با ریپلای)
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\*بلاک$'))
    async def handle_block(event):
        if not event.is_reply:
            return
        try:
            reply_msg = await event.get_reply_message()
            user_id = reply_msg.sender_id
            if user_id:
                await client(BlockRequest(id=user_id))
                print(f"User {user_id} blocked.")
            await event.delete()
        except Exception as e:
            print(f"Error blocking user: {e}")


# ۲. هندلر دستور *آن‌بلاک (هم با ریپلای و هم با آیدی عددی مستقیم)
    # الگو جوری تنظیم شده که "آن‌بلاک" (سرهم یا با نیم‌فاصله) را کاملاً تشخیص دهد
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\*آن‌?بلاک(?:\s+(\d+))?$'))
    async def handle_unblock(event):
        match = event.pattern_match
        user_id_str = match.group(1)

        try:
            # حالت اول: آیدی عددی جلوی دستور نوشته شده باشد (مثل: *آن‌بلاک 1632503299)
            if user_id_str:
                user_id = int(user_id_str)
                await client(UnblockRequest(id=user_id))
                print(f"User {user_id} unblocked via ID.")
                await event.delete()
                return

            # حالت دوم: جلوی دستور عددی نیست ولی روی پیام شخص ریپلای شده است
            if event.is_reply:
                reply_msg = await event.get_reply_message()
                user_id = reply_msg.sender_id
                if user_id:
                    await client(UnblockRequest(id=user_id))
                    print(f"User {user_id} unblocked via Reply.")
                await event.delete()

        except Exception as e:
            print(f"Error unblocking user: {e}")

    # ۳. هندلر دستور *بلاک لیست (نمایش لیست افراد بلاک شده به همراه آیدی)
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\*بلاک لیست$'))
    async def handle_block_list(event):
        # تغییر پیام به حالت در حال پردازش
        msg = await event.edit("🔄 در حال دریافت لیست بلاک...")
        
        try:
            # گرفتن لیست کاربران بلاک شده از سرور تلگرام
            # مقدار offset و limit برای صفحه‌بندی است، اینجا ۱۰۰ نفر اول را می‌گیریم
            blocked_data = await client(GetBlockedRequest(offset=0, limit=100))
            
            if not blocked_data.users:
                await msg.edit("🚫 لیست بلاک شما خالی است.")
                return
            
            # ساختن متن لیست
            text_result = "📑 **لیست کاربران بلاک شده:**\n\n"
            
            for index, user in enumerate(blocked_data.users, start=1):
                if isinstance(user, User):
                    # تشخیص نام کاربر (اولویت با نام کوچک، در غیر این صورت نام خانوادگی)
                    first_name = user.first_name if user.first_name else ""
                    last_name = user.last_name if user.last_name else ""
                    full_name = f"{first_name} {last_name}".strip()
                    
                    if not full_name:
                        full_name = "کاربر بدون نام"
                        
                    text_result += f"{index}. {full_name} ➔ `{user.id}`\n"
            
            # ویرایش پیام و نمایش لیست نهایی
            await msg.edit(text_result)
            
        except Exception as e:
            print(f"Error fetching block list: {e}")
            await msg.edit("❌ خطایی در دریافت لیست بلاک رخ داد.")
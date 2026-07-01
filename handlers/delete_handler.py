import re
from telethon import events

# سقف مجاز برای پاک کردن پیام‌ها
MAX_DELETE_LIMIT = 500

def register_delete_handlers(client):
    """
    این تابع هندلرهای مربوط به حذف پیام را به کلاینت سلف‌بات اضافه می‌کند.
    """
    
    # هندلر برای دستور *حذف (چه به صورت ریپلای و چه با تعداد)
    # pattern رو جوری تنظیم کردیم که فقط پیام‌هایی که خودت (me) می‌فرستی و با *حذف شروع می‌شن رو بگیره
    @client.on(events.NewMessage(outgoing=True, pattern=r'^\*حذف(?:\s+(\d+))?$'))
    async def handle_delete(event):
        # بررسی اینکه آیا دستور پارامتر عددی دارد یا خیر (مثلا *حذف ۵۰)
        match = event.pattern_match
        count_str = match.group(1)
        
        # حالت اول: ریپلای روی یک پیام خاص بدون وارد کردن عدد
        if event.is_reply and not count_str:
            reply_msg = await event.get_reply_message()
            try:
                # پاک کردن پیام ریپلای شده و خود پیام دستور
                await client.delete_messages(event.chat_id, [reply_msg.id, event.id])
            except Exception as e:
                print(self_log := f"Error deleting single message: {e}")
            return

        # حالت دوم: پاک کردن دسته‌ای پیام‌ها
        # اگر عددی وارد نشده بود ولی ریپلای هم نبود، پیش‌فرض ۱ پیام (خود دستور) پاک می‌شود
        count = int(count_str) if count_str else 1
        
        # اعمال محدودیت سقف ۵۰۰ پیام
        if count > MAX_DELETE_LIMIT:
            count = MAX_DELETE_LIMIT
            
        try:
            # ابتدا پیام دستور (*حذف) را پاک می‌کنیم
            await event.delete()
            
            # گرفتن پیام‌های اخیر چت به تعداد مشخص شده و پاک کردن آن‌ها
            async for message in client.iter_messages(event.chat_id, limit=count):
                await message.delete()
                
        except Exception as e:
            print(f"Error purging messages: {e}")
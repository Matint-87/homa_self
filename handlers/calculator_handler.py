from telethon import events

async def send_calculator_handler(event):
    try:
        # ۱. گرفتن مشخصات صاحبِ این سلف‌بات خاص
        me = await event.client.get_me()
        
        # ۲. شرط طلایی: اگر فرستنده پیام، صاحبِ همین اکانت نبود، کلاً خارج شو و کاری نکن
        if event.sender_id != me.id:
            return
            
        # پاک کردن دستور *حساب (فقط برای صاحب اکانت اجرا می‌شود)
        await event.delete() 
        
        # صدا زدن ربات اصلی به صورت اینلاین
        results = await event.client.inline_query('Homa_selfbot', 'calc_main')
        
        if results:
            await results[0].click(event.chat_id)
    except Exception as e:
        print(f"Error in calculator handler: {e}")

# تابع اصلی برای ریجستر کردن این هندلر در فایل اصلی سلف‌بات
def register_self_handlers(client):
    client.add_event_handler(
        send_calculator_handler, 
        events.NewMessage(pattern=r'^\*حساب$')
    )
import asyncio
from telethon import events
from config import supabase  # اتصال به کلاینت سوپابیس شما

# =====================================================================
# 🗄️ بخش اول: توابع دیتابیس (Supabase)
# =====================================================================

def get_user_chat_action(user_id: int) -> str:
    try:
        res = supabase.table("user_chat_actions").select("action").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]["action"]
    except Exception as e:
        print(f"❌ Error fetching chat action: {e}")
    return "none"

def set_user_chat_action(user_id: int, action: str):
    try:
        # اصلاح علامت کاما به دونقطه برای جفت کلید و مقدار دیتابیس
        supabase.table("user_chat_actions").upsert({"user_id": user_id, "action": action}).execute()
    except Exception as e:
        print(f"❌ Error saving chat action: {e}")


# =====================================================================
# ⚡ بخش دوم: موتور فرستادن اکشن فیک هوشمند
# =====================================================================
def register_chat_action_engine(bot):
    """شنود هوشمند چت‌ها جهت ارسال اکشن"""
    
    action_mapping = {
        "typing": "typing",
        "record-audio": "audio",       
        "upload-video": "video",       
        "record-round": "round",       
        "upload-photo": "photo",       
        "upload-document": "document", 
        "choose-sticker": "sticker",   
        "playing": "game"              
    }

    # ۱. ارسال اکشن فیک به محض اینکه به کسی پیام دادی (تا در چت‌های بعدی اعمال شود)
    @bot.on(events.NewMessage(outgoing=True))
    async def on_my_message(event):
        if event.text and event.text.startswith('*'):
            return
            
        if not hasattr(event.client, '_cached_my_id') or event.client._cached_my_id is None:
            me = await event.client.get_me()
            event.client._cached_my_id = me.id
        owner_id = event.client._cached_my_id
        
        mode = get_user_chat_action(owner_id)
        if mode == "none" or mode not in action_mapping:
            return
            
        try:
            async with event.client.action(event.peer_id, action_mapping[mode]):
                await asyncio.sleep(2) # به مدت ۲ ثانیه اکشن را نگه می‌دارد
        except Exception:
            pass

    # ۲. ارسال اکشن فیک به محض اینکه طرف مقابل به تو پیام داد و چتش را باز کردی
    @bot.on(events.NewMessage(incoming=True))
    async def on_incoming_message(event):
        if not event.is_private: 
            return # فقط در پیوی تست شود
            
        if not hasattr(event.client, '_cached_my_id') or event.client._cached_my_id is None:
            me = await event.client.get_me()
            event.client._cached_my_id = me.id
        owner_id = event.client._cached_my_id
        
        mode = get_user_chat_action(owner_id)
        if mode == "none" or mode not in action_mapping:
            return
            
        try:
            # وقتی پیوی کسی باز است، این متد وضعیت فیک شما را برای او می‌فرستد
            async with event.client.action(event.chat_id, action_mapping[mode]):
                await asyncio.sleep(3)
        except Exception:
            pass
from telethon import events
from config import supabase

guard_status = {}

def register_guard_handler(client):
    
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*نگهبان\s+(روشن|خاموش)$"))
    async def guard_manager(event):
        me = await event.client.get_me()
        if event.sender_id != me.id:
            return
            
        status = event.pattern_match.group(1)
        chat_id = event.chat_id
        
        if status == "روشن":
            guard_status[chat_id] = True
            await event.edit("🛡 **نگهبان چت در این مکان فعال شد.**")
        else:
            guard_status[chat_id] = False
            await event.edit("🚫 **نگهبان چت غیرفعال شد.**")

    # ذخیره پیام (بدون پیام‌های خودت)
    @client.on(events.NewMessage)

    async def save_to_db(event):
        if not guard_status.get(event.chat_id) or event.out:
            return
            
        me = await event.client.get_me()
        if event.message.text:
            supabase.table("messages_log").insert({
                "id": event.message.id,
                "chat_id": event.chat_id,
                "sender_id": event.sender_id,
                "message_text": event.message.text,
                "owner_id": me.id
            }).execute()

    # رصد حذف (فقط یک بار)
    @client.on(events.MessageDeleted)
    async def track_deleted(event):
        if not guard_status.get(event.chat_id):
            return
            
        me = await event.client.get_me()
        # استفاده از لیست آیدی‌های حذف شده
        for msg_id in event.deleted_ids:
            response = supabase.table("messages_log")\
                .select("message_text")\
                .eq("id", msg_id)\
                .eq("owner_id", me.id)\
                .execute()
                
            if response.data:
                text = response.data[0]['message_text']
                # ارسال پیام مستقل به Saved Messages
                await client.send_message("me", f"🗑 **پیام حذف شده:**\n{text}")

    # رصد ویرایش
    @client.on(events.MessageDeleted)
    async def track_deleted(event):
        if not guard_status.get(event.chat_id):
            return
            
        me = await event.client.get_me()
        # آیدی کانال یا گروهی که می‌خواهی پیام‌ها آنجا امن بمانند
        LOG_CHAT_ID = -100123456789 
        
        for msg_id in event.deleted_ids:
            response = supabase.table("messages_log")\
                .select("message_text")\
                .eq("id", msg_id)\
                .eq("owner_id", me.id)\
                .execute()
                
            if response.data:
                text = response.data[0]['message_text']
                # ارسال به چتِ امن (جایی که ربات پیام را پاک نمی‌کند)
                await client.send_message(LOG_CHAT_ID, f"🗑 **پیام حذف شده (در چت {event.chat_id}):**\n{text}")
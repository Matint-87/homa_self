from telethon import events
from utils import get_pool  # دسترسی به asyncpg pool مشترک پروژه

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
            await event.edit("🛡 **نگهبان چت فعال شد.**")
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
            pool = get_pool()
            await pool.execute(
                """
                INSERT INTO messages_log (id, chat_id, sender_id, message_text, owner_id)
                VALUES ($1, $2, $3, $4, $5)
                """,
                event.message.id,
                event.chat_id,
                event.sender_id,
                event.message.text,
                me.id,
            )

    # رصد حذف
    @client.on(events.MessageDeleted)
    async def track_deleted(event):
        if not guard_status.get(event.chat_id):
            return
            
        me = await event.client.get_me()
        LOG_CHAT_ID = -100123456789 
        
        pool = get_pool()
        for msg_id in event.deleted_ids:
            row = await pool.fetchrow(
                "SELECT message_text FROM messages_log WHERE id = $1 AND owner_id = $2",
                msg_id, me.id,
            )
                
            if row:
                text = row["message_text"]
                await client.send_message(LOG_CHAT_ID, f"🗑 **پیام حذف شده (در چت {event.chat_id}):**\n{text}")

    # رصد ویرایش (اصلاح شد: از MessageEdited استفاده شد)
    @client.on(events.MessageEdited)
    async def track_edited(event):
        if not guard_status.get(event.chat_id) or event.out:
            return
            
        me = await event.client.get_me()
        # آپدیت متن جدید در دیتابیس
        pool = get_pool()
        await pool.execute(
            "UPDATE messages_log SET message_text = $1 WHERE id = $2 AND owner_id = $3",
            event.message.text, event.message.id, me.id,
        )
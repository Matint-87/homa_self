from datetime import datetime, timezone
from telethon import events

async def ping_handler(event):
    try:
        me = await event.client.get_me()
        
        if event.sender_id != me.id:
            return
            
        now = datetime.now(timezone.utc)
        msg_time = event.message.date
        
        ping_in_seconds = (now - msg_time).total_seconds()
        
        if ping_in_seconds <= 0:
            ping_in_seconds = 0.02
            
        text = (
            f"<blockquote>"
            f"🌐 پینگ <code>{ping_in_seconds:.2f}</code> ثانیه"
            f"🚀 Self Homa"
            f"</blockquote>"
        )
        
        await event.edit(text, parse_mode='html')
        
    except Exception as e:
        pass

def register_ping_handler(client):
    client.add_event_handler(
        ping_handler, 
        events.NewMessage(pattern=r'^\*پینگ$')
    )
from telethon import events
import asyncio
import html 

# ساختار دیکشنری دوطبقه برای تفکیک کامل اکانت‌ها و چت‌ها:
# { me_id: { chat_id: 'font_type' } }
current_fonts = {}

FONT_MAP = {
    'بولد': 'bold',
    'ایتالیک': 'italic',
    'زیرخط': 'underline',
    'خط خورده': 'strike',
    'اسپویلر': 'spoiler',
    'تک فاصله': 'code',
    'نقل قول': 'quote',
    'تدریجی': 'gradual',
}

def apply_font_html(text, font_type):
    """اعمال فونت با فرمت استاندارد HTML تلگرام"""
    safe_text = html.escape(text)
    
    if font_type == 'bold':
        return f"<b>{safe_text}</b>"
    elif font_type == 'italic':
        return f"<i>{safe_text}</i>"
    elif font_type == 'underline':
        return f"<u>{safe_text}</u>"
    elif font_type == 'strike':
        return f"<s>{safe_text}</s>"
    elif font_type == 'spoiler':
        return f"<tg-spoiler>{safe_text}</tg-spoiler>" 
    elif font_type == 'code':
        return f"<code>{safe_text}</code>"
    elif font_type == 'quote':
        return f"<blockquote expandable>{safe_text}</blockquote>" 
    else:
        return safe_text

async def send_gradual(client, chat_id, text, delay=0.15):
    """ارسال تدریجی (حرف به حرف)"""
    # استفاده از نشانه اختصاصی برای جلوگیری از پردازش مجدد توسط کلاینت‌های دیگر
    msg = await client.send_message(chat_id, "▌ [GRADUAL_MODE]")
    
    displayed = ""
    for char in text:
        displayed += char
        try:
            await msg.edit(displayed + "▌")
            await asyncio.sleep(delay)
        except:
            break
    try:
        await msg.edit(text)
    except:
        pass

def register_font_handler(client):
    
    @client.on(events.NewMessage(pattern=r'\*(بولد|ایتالیک|زیرخط|خط خورده|اسپویلر|تک فاصله|نقل قول|تدریجی)'))
    async def font_on(event):
        if event.out:
            # گرفتن آیدی منحصربه‌فرد اکانتی که پیام را فرستاده
            me = await event.client.get_me()
            me_id = me.id
            
            font_name = event.pattern_match.group(1)
            font_type = FONT_MAP.get(font_name)
            
            if font_type:
                if me_id not in current_fonts:
                    current_fonts[me_id] = {}
                
                # ذخیره فونت فقط برای این اکانت و فقط برای این چت
                current_fonts[me_id][event.chat_id] = font_type
                await event.reply(f"✅ فونت {font_name} برای این چت فعال شد!")
    
    @client.on(events.NewMessage(pattern=r'\*فونت خاموش'))
    async def font_off(event):
        if event.out:
            me = await event.client.get_me()
            me_id = me.id
            
            if me_id in current_fonts and event.chat_id in current_fonts[me_id]:
                del current_fonts[me_id][event.chat_id]
            await event.reply("✅ فونت برای این چت غیرفعال شد!")

    @client.on(events.NewMessage(outgoing=True))
    async def apply_font_style(event):
        if not event.message.text:
            return
            
        # ۱. مشخص کردن آیدی اکانت فرستنده پیام
        me = await event.client.get_me()
        me_id = me.id
        
        # ۲. بررسی اینکه آیا این اکانت در این چت خاص فونتی فعال دارد یا نه
        chat_font = current_fonts.get(me_id, {}).get(event.chat_id)
        
        if not chat_font:
            return
            
        text = event.message.text
        
        # ۳. اگر پیام دستور است، پردازش نکن
        if text.startswith('*'):
            return
            
        # ۴. سد امنیتی نهایی در برابر خط‌های اضافه مارک‌داون یا لوپ ربات‌های همکار
        if "[GRADUAL_MODE]" in text or "____" in text or any(tag in text for tag in ['<b>', '<i>', '<u>', '<s>', '<tg-spoiler>', '<code>', '<blockquote']):
            return

        # پاک کردن متن خام اولیه
        await event.delete()
        
        try:
            if chat_font == 'gradual':
                await send_gradual(event.client, event.chat_id, text)
            else:
                styled = apply_font_html(text, chat_font)
                await event.client.send_message(
                    event.chat_id, 
                    styled, 
                    parse_mode='html',
                    reply_to=event.reply_to_msg_id
                )
        except Exception as e:
            await event.client.send_message(event.chat_id, text, parse_mode=None)
            print(f"❌ Error: {e}")
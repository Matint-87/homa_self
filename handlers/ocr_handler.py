from telethon import events
import pytesseract
from PIL import Image
import os

def register_ocr_handler(client):
    
    @client.on(events.NewMessage(pattern=r"^\*متن تصویر$"))
    async def extract_text(event):
        # بررسی اینکه آیا روی عکس ریپلای شده است
        reply = await event.get_reply_message()
        if not reply or not reply.photo:
            await event.respond("لطفاً روی یک **عکس** ریپلای کنید.")
            return

        processing_msg = await event.respond("⏳ در حال استخراج متن...")

        # دانلود عکس در مسیر موقت
        file_path = await reply.download_media()
        
        try:
            # استفاده از Tesseract برای خواندن تصویر
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang='fas+eng')
            
            if not text.strip():
                text = "متنی در تصویر شناسایی نشد."
            
            # ویرایش پیامی که خودِ ربات فرستاده است
            await processing_msg.edit(f"**متن استخراج شده:**\n\n{text}")
            
        except Exception as e:
            await processing_msg.edit(f"خطایی رخ داد: {str(e)}")
            
        finally:
            # حذف فایل پس از پردازش
            if file_path and os.path.exists(file_path):
                os.path.remove(file_path)
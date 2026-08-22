import os
from telethon import events
from telethon.tl.types import DocumentAttributeVideo

def video_message_handler(client):
    @client.on(events.NewMessage(pattern=r'^\*ویدیو مسیج$'))
    async def convert_to_video_note(event):
        # بررسی اینکه آیا پیام به ویدیویی ریپلای شده است یا خیر
        reply_message = await event.get_reply_message()
        
        if not reply_message or not reply_message.video:
            await event.edit("لطفاً این دستور را روی یک پیام **ویدیو** ریپلای کنید!")
            return

        # جداسازی کارهای کاربران مختلف با استفاده از آیدی عددی کاربر
        user_id = event.sender_id
        input_path = f"downloads_{user_id}.mp4"
        output_path = f"output_note_{user_id}.mp4"

        try:
            await event.edit("⏳ در حال دانلود ویدیو...")
            
            # دانلود ویدیو با استفاده از مسیر اختصاصی کاربر
            await client.download_media(reply_message.video, file=input_path)

            await event.edit("🔄 در حال پردازش و تبدیل به ویدیو مسیج...")

            # استفاده از ابزار سیستم (ffmpeg) برای تبدیل ویدیو به فرمت دایره‌ای/مربع (مکعبی)
            # متناسب با استانداردهای تلگرام برای ویدیو نوت
            import subprocess
            
            # استخراج اطلاعات ویدیو یا تبدیل مستقیم با پد کردن به مربع
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale=640:640:force_original_aspect_ratio=decrease,pad=640:640:(ow-iw)/2:(oh-ih)/2:color=black",
                "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
                "-c:a", "aac", "-strict", "experimental",
                output_path
            ]
            
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if process.returncode != 0:
                await event.edit("❌ خطا در پردازش ویدیو با ffmpeg.")
                return

            await event.edit("📤 در حال ارسال ویدیو مسیج...")

            # ارسال به عنوان ویدیو نوت (Video Note)
            await client.send_file(
                event.chat_id,
                output_path,
                video_note=True,
                reply_to=reply_message.id
            )
            
            # حذف پیام وضعیت قبلی
            await event.delete()

        except Exception as e:
            await event.edit(f"❌ خطایی رخ داد: {str(e)}")
            
        finally:
            # پاکسازی فایل‌های موقت مربوط به این کاربر خاص
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
import os
import subprocess
from telethon import events

def video_message_handler(client):
    @client.on(events.NewMessage(pattern=r'^\*ویدیو مسیج$'))
    async def convert_to_video_note(event):
        reply_message = await event.get_reply_message()
        
        if not reply_message or not reply_message.video:
            await event.edit("لطفاً این دستور را روی یک پیام **ویدیو** ریپلای کنید!")
            return

        user_id = event.sender_id
        input_path = f"downloads_{user_id}.mp4"
        output_path = f"output_note_{user_id}.mp4"

        try:
            await event.edit("⏳ در حال دانلود ویدیو...")
            await client.download_media(reply_message.video, file=input_path)

            await event.edit("🔄 در حال پردازش و تبدیل به ویدیو مسیج...")

            # دستور اصلاح‌شده و مقاوم‌تر برای ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)',crop=min(iw\,ih):min(iw\,ih)",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                output_path
            ]
            
            # اجرای ffmpeg
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # بررسی اینکه آیا فایل خروجی واقعاً ساخته شده است یا خیر
            if result.returncode != 0 or not os.path.exists(output_path):
                error_log = result.stderr.decode('utf-8', errors='ignore')
                print(f"FFmpeg Error: {error_log[-500:]}")  # چاپ خطا در کنسول برای بررسی
                await event.edit("❌ خطا در پردازش ویدیو توسط ffmpeg.")
                return

            await event.edit("📤 در حال ارسال ویدیو مسیج...")

            # ارسال به عنوان ویدیو نوت (گرد)
            await client.send_file(
                event.chat_id,
                output_path,
                video_note=True,
                reply_to=reply_message.id
            )
            
            await event.delete()

        except Exception as e:
            await event.edit(f"❌ خطایی رخ داد: {str(e)}")
            
        finally:
            # پاکسازی فایل‌های موقت کاربر
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
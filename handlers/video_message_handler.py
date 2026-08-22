import os
import subprocess
from telethon import events

def video_message_handler(client):
    @client.on(events.NewMessage(pattern=r'^\*ویدیو مسیج$', outgoing=True))
    async def convert_to_video_note(event):
        reply_message = await event.get_reply_message()
        
        if not reply_message or not reply_message.video:
            # در سلف‌بات برای جلوگیری از خطای آیدی، یک پیام موقت می‌فرستیم و پاک می‌کنیم
            temp_msg = await event.reply("❌ لطفاً این دستور را روی یک پیام **ویدیو** ریپلای کنید!")
            await asyncio.sleep(3)
            await temp_msg.delete()
            return

        user_id = event.sender_id
        input_path = f"downloads_{user_id}.mp4"
        output_path = f"output_note_{user_id}.mp4"

        status_msg = await event.reply("⏳ در حال دانلود ویدیو...")

        try:
            # دانلود صریح و مستقیم مدیا به مسیر مشخص
            downloaded_file = await client.download_media(reply_message.video, file=input_path)
            
            if not downloaded_file or not os.path.exists(input_path):
                await status_msg.edit("❌ دانلود ویدیو با شکست مواجه شد.")
                return

            await status_msg.edit("🔄 در حال پردازش و تبدیل به ویدیو مسیج...")

            # دستور استاندارد ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)',crop=min(iw\,ih):min(iw\,ih)",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                output_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode != 0 or not os.path.exists(output_path):
                await status_msg.edit("❌ خطا در پردازش ویدیو با ffmpeg.")
                return

            await status_msg.edit("📤 در حال ارسال ویدیو مسیج...")

            # ارسال به عنوان ویدیو نوت
            await client.send_file(
                event.chat_id,
                output_path,
                video_note=True,
                reply_to=reply_message.id
            )
            
            # حذف پیام وضعیت و پیام دستور اصلی خودتان برای تمیزی چت
            await status_msg.delete()
            await event.delete()

        except Exception as e:
            try:
                await status_msg.edit(f"❌ خطایی رخ داد: {str(e)}")
            except:
                pass
            
        finally:
            # پاکسازی فایل‌های موقت کاربر
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
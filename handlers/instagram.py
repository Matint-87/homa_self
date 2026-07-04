import os
import asyncio
import requests  # برای ارسال درخواست تشخیص آهنگ به AudD
from telethon import events
import yt_dlp

# توکن رایگان خود را از سایت audd.io بگیرید و اینجا قرار دهید
AUDD_API_TOKEN = "bf9557b1de72e6a7cdd16ebff99b6e1d"

os.makedirs("downloads", exist_ok=True)

# ============================================================================
# 🍪 فایل کوکی اینستاگرام (ضروری برای رفع خطای «login required»)
#
# اینستاگرام این روزها برای اکثر پست‌ها/ریلزها لاگین اجباری کرده، حتی برای
# محتوای عمومی. بدون کوکی، yt-dlp با این خطا مواجه میشه:
#   "Requested content is not available, rate-limit reached or login required"
#
# نحوه‌ی گرفتن فایل کوکی:
#   1) با مرورگر (روی کامپیوتر شخصی، نه سرور) وارد اینستاگرام شو (ترجیحاً یه
#      اکانت فرعی/تست، نه اکانت اصلی، چون استفاده‌ی زیاد ممکنه محدودش کنه).
#   2) اکستنشن "Get cookies.txt LOCALLY" رو نصب کن (برای Chrome/Firefox).
#   3) وارد instagram.com بشو و با اون اکستنشن کوکی‌ها رو به فرمت Netscape
#      export کن.
#   4) فایل رو با نام instagram_cookies.txt کنار همین فایل پایتون (یا مسیر
#      دلخواه که پایین مشخص می‌کنی) آپلود کن روی سرور.
#
# اگه این فایل رو نداشته باشی، کد باز هم تلاش می‌کنه (شاید برای بعضی پست‌های
# کاملاً عمومی جواب بده) ولی برای بیشتر لینک‌ها الان لازمه.
# ============================================================================
INSTAGRAM_COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instagram_cookies.txt")


def _base_ydl_opts(extra: dict) -> dict:
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noproxy': '*',
        # هدر مرورگر واقعی برای کاهش شانس تشخیص به‌عنوان ربات
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            )
        },
    }
    if os.path.exists(INSTAGRAM_COOKIES_FILE):
        opts['cookiefile'] = INSTAGRAM_COOKIES_FILE
    else:
        print("⚠️ فایل instagram_cookies.txt پیدا نشد؛ دانلود از اینستاگرام احتمالاً با خطای login required مواجه میشه.")
    opts.update(extra)
    return opts

def download_video_only(url, user_id):
    video_path = f"downloads/{user_id}_temp_video.mp4"
    ydl_opts = _base_ydl_opts({
        'outtmpl': f"downloads/{user_id}_temp_video.%(ext)s",
        'format': 'best',
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return video_path if os.path.exists(video_path) else None
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None


def extract_audio_chunk(video_path, user_id):
    import subprocess
    audio_path = f"downloads/{user_id}_temp_audio.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "libmp3lame",
                audio_path
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return audio_path if os.path.exists(audio_path) else None
    except Exception:
        return None


def download_full_track(search_query, user_id):
    full_audio_path = f"downloads/{user_id}_full_track.mp3"
    ydl_opts = _base_ydl_opts({
        'outtmpl': f"downloads/{user_id}_full_track.%(ext)s",
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"{search_query} official audio"])
        return full_audio_path if os.path.exists(full_audio_path) else None
    except Exception as e:
        print(e)
        return None


def recognize_song_audd(audio_path):
    """تشخیص آهنگ با استفاده از سرویس AudD بدون نیاز به پروکسی و رفع تحریم"""
    if AUDD_API_TOKEN == "YOUR_AUDD_API_TOKEN_HERE":
        print("⚠️ لطفا ابتدا توکن API خود را از سایت audd.io دریافت و وارد کنید.")
        return None

    data = {
        'api_token': AUDD_API_TOKEN,
        'return': 'apple_music,spotify',
    }

    try:
        # ارسال فایل صوتی به سرور AudD
        with open(audio_path, 'rb') as f:
            files = {'file': f}
            response = requests.post('https://api.audd.io/', data=data, files=files, timeout=20)

        result = response.json()
        if result.get("status") == "success" and result.get("result"):
            return result["result"]
    except Exception as e:
        print(f"AudD API Error: {e}")
    return None


def register_instagram_handler(client):

    @client.on(events.NewMessage(pattern=r"^\*?اینستا\s+(https?://[^\s]+)"))
    async def insta_downloader(event):
        if not event.out:
            return

        url = event.pattern_match.group(1).strip()
        user_id = event.sender_id
        status_msg = await event.reply("🔄 در حال دانلود ویدیو...")

        video_file = None
        short_audio = None
        full_audio = None

        try:
            loop = asyncio.get_running_loop()

            # ۱. دانلود ویدیو
            video_file = await loop.run_in_executor(None, download_video_only, url, user_id)
            if not video_file:
                if os.path.exists(INSTAGRAM_COOKIES_FILE):
                    await status_msg.edit("❌ خطا در دانلود ویدیو از اینستاگرام (با وجود فایل کوکی). ممکنه لینک اشتباه، پست خصوصی، یا کوکی منقضی‌شده باشه.")
                else:
                    await status_msg.edit("❌ خطا در دانلود ویدیو از اینستاگرام. این روزها اینستاگرام برای اکثر لینک‌ها لاگین می‌خواد — فایل instagram_cookies.txt رو تنظیم کن (توضیحات بالای فایل).")
                return

            await status_msg.edit("🔍 در حال تشخیص آهنگ (بدون تحریم)...")

            # ۲. استخراج صدا
            short_audio = await loop.run_in_executor(None, extract_audio_chunk, video_file, user_id)
            if not short_audio:
                await status_msg.edit("❌ استخراج صدا ناموفق بود.")
                return

            # ۳. تشخیص آهنگ با AudD (اجرا در اکسیکیوتر برای جلوگیری از بلاک شدن اسینسیو)
            out = await loop.run_in_executor(None, recognize_song_audd, short_audio)

            track_title = "Unknown Track"
            track_artist = "Unknown Artist"

            if out and "title" in out:
                track_title = out["title"]
                track_artist = out["artist"]
                search_query = f"{track_artist} - {track_title}"

                await status_msg.edit(
                    f"🎵 آهنگ پیدا شد:\n"
                    f"{search_query}\n\n"
                    f"📥 دانلود نسخه کامل..."
                )

                # ۴. دانلود نسخه کامل از یوتیوب
                full_audio = await loop.run_in_executor(None, download_full_track, search_query, user_id)
            else:
                await status_msg.edit("⚠️ آهنگ شناسایی نشد. صدای خود ویدیو ارسال می‌شود.")
                full_audio = short_audio

            # ۵. ارسال فایل‌ها به تلگرام
            if os.path.exists(video_file):
                await client.send_file(
                    event.chat_id,
                    video_file,
                    caption="🎬 ویدیو دانلود شد",
                    reply_to=event.id
                )

            if full_audio and os.path.exists(full_audio):
                caption_text = f"🎵 {track_title}\n👤 {track_artist}" if out else "🎵 صدای استخراج شده از ویدیو"
                await client.send_file(
                    event.chat_id,
                    full_audio,
                    caption=caption_text,
                    reply_to=event.id
                )

            await status_msg.delete()

        except Exception as e:
            await status_msg.edit(f"❌ خطا:\n{e}")

        finally:
            files_to_delete = {f for f in [video_file, short_audio, full_audio] if f}
            for f in files_to_delete:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
import os
import uuid
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor

import aiohttp
from telethon import events
import yt_dlp
from yt_dlp.utils import download_range_func

# توکن رایگان خود را از سایت audd.io بگیرید و اینجا قرار دهید
AUDD_API_TOKEN = "bf9557b1de72e6a7cdd16ebff99b6e1d"

os.makedirs("downloads", exist_ok=True)

# ============================================================================
# ⚙️ تنظیمات کارایی (برای ۸۰۰۰ کاربر / تا ~۸۰ درخواست همزمان)
# این چهار عدد رو با توجه به منابع واقعی سرورت (CPU، RAM، پهنای باند) تیون کن.
# ============================================================================
# تعداد تردِ اختصاصی برای کارهای IO/CPU-bound (yt-dlp، ffmpeg).
# پیش‌فرض پایتون معمولاً حدود ۳۲-۳۶ تا بیشتر نیست؛ برای ۸۰ کار همزمان کم میاد.
MAX_WORKERS = 40
# حداکثر تعداد پایپ‌لاین کامل (دانلود ویدیو + صدا) که هم‌زمان اجرا می‌شن.
# بقیه‌ی درخواست‌ها صف می‌مونن؛ این از overload شدن پهنای باند/دیسک جلوگیری می‌کنه.
MAX_CONCURRENT_JOBS = 15
# طول نمونه صوتی برای تشخیص آهنگ (ثانیه) - AudD با چند ثانیه هم کارش رو می‌کنه.
SAMPLE_DURATION = 15

_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
_job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
_http_session: "aiohttp.ClientSession | None" = None


async def _get_http_session() -> aiohttp.ClientSession:
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession()
    return _http_session


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
        # دانلود موازیِ fragment های خود ویدیو برای سرعت بیشتر
        'concurrent_fragment_downloads': 4,
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


# ----------------------------------------------------------------------------
# نکته‌ی مهم: به‌جای user_id از یک job_id یکتا (uuid) برای نام‌گذاری فایل‌های
# موقت استفاده می‌کنیم. اگه از user_id استفاده کنی و همون کاربر دو تا لینک
# پشت سر هم بفرسته (یا دو کاربر مختلف هم‌زمان به یه تابع با اسم فایل مشترک
# برسن)، فایل‌ها روی هم اورراید می‌شن و دانلودها خراب/قاطی می‌شن. با ۸۰ کار
# همزمان این سناریو دیگه فرضی نیست، واقعاً پیش میاد.
# ----------------------------------------------------------------------------

def download_video_only(url, job_id):
    video_path = f"downloads/{job_id}_video.mp4"
    ydl_opts = _base_ydl_opts({
        'outtmpl': f"downloads/{job_id}_video.%(ext)s",
        'format': 'best',
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return video_path if os.path.exists(video_path) else None
    except Exception as e:
        print(f"yt-dlp error: {e}")
        return None


def download_audio_sample(url, job_id, duration=SAMPLE_DURATION):
    """
    به‌جای دانلود کل ویدیو و بعد استخراج صدا با ffmpeg (روش قدیمی کند)،
    مستقیماً فقط چند ثانیه اول رو دانلود و به mp3 تبدیل می‌کنه. این تابع
    قراره هم‌زمان با download_video_only اجرا بشه (نه بعدش)، پس عملاً
    زمان اضافه‌ای به کل فرآیند اضافه نمی‌کنه.
    """
    sample_path = f"downloads/{job_id}_sample.mp3"
    ydl_opts = _base_ydl_opts({
        'outtmpl': f"downloads/{job_id}_sample.%(ext)s",
        'format': 'bestaudio/best',
        'download_ranges': download_range_func(None, [(0, duration)]),
        'force_keyframes_at_cuts': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
    })
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return sample_path if os.path.exists(sample_path) else None
    except Exception as e:
        print(f"sample download error: {e}")
        return None


def extract_audio_chunk(video_path, job_id, duration=SAMPLE_DURATION):
    """
    fallback: اگه دانلود مستقیم نمونه صدا شکست خورد، همون چند ثانیه اول رو
    از روی ویدیوی از قبل دانلودشده با ffmpeg می‌گیریم (نه کل صدا).
    """
    audio_path = f"downloads/{job_id}_fallback_audio.mp3"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", video_path,
                "-t", str(duration),
                "-vn",
                "-acodec", "libmp3lame",
                audio_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=60,
        )
        return audio_path if os.path.exists(audio_path) else None
    except Exception:
        return None


def download_full_track(search_query, job_id):
    full_audio_path = f"downloads/{job_id}_full_track.mp3"
    ydl_opts = _base_ydl_opts({
        'outtmpl': f"downloads/{job_id}_full_track.%(ext)s",
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'noplaylist': True,
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


async def recognize_song_audd(audio_path):
    """
    تشخیص آهنگ با AudD به‌صورت async (aiohttp) به‌جای requests بلاکینگ.
    این باعث می‌شه هیچ ترد از executor محدودمون صرفِ «منتظر جواب شبکه موندن»
    نشه؛ تردهای ما فقط صرف کارهای واقعاً سنگین (دانلود/ffmpeg) می‌شن.
    """
    if not AUDD_API_TOKEN or AUDD_API_TOKEN == "YOUR_AUDD_API_TOKEN_HERE":
        print("⚠️ لطفا ابتدا توکن API خود را از سایت audd.io دریافت و وارد کنید.")
        return None

    try:
        session = await _get_http_session()
        data = aiohttp.FormData()
        data.add_field('api_token', AUDD_API_TOKEN)
        data.add_field('return', 'apple_music,spotify')
        with open(audio_path, 'rb') as f:
            data.add_field('file', f, filename=os.path.basename(audio_path))
            async with session.post(
                'https://api.audd.io/', data=data,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                result = await resp.json()
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
        job_id = uuid.uuid4().hex  # شناسه یکتای هر درخواست، نه user_id
        status_msg = await event.reply("🔄 در صف پردازش...")

        video_file = None
        short_audio = None
        full_audio = None

        loop = asyncio.get_running_loop()

        # محدود کردن تعداد کارهای سنگین هم‌زمان (دانلود/ffmpeg) تا سرور
        # زیر بار ۸۰ درخواست همزمان overload نشه. بقیه صف می‌مونن و به محض
        # آزاد شدن ظرفیت شروع می‌شن.
        async with _job_semaphore:
            try:
                await status_msg.edit("🔄 در حال دانلود ویدیو و آماده‌سازی برای تشخیص آهنگ...")

                # ۱. دانلود ویدیوی کامل و نمونه‌ی کوتاه صوتی به‌صورت *موازی*
                #    (قبلاً سریالی بود: اول کل ویدیو، بعد استخراج صدا از کل صدا)
                video_task = loop.run_in_executor(_executor, download_video_only, url, job_id)
                sample_task = loop.run_in_executor(_executor, download_audio_sample, url, job_id)
                video_file, short_audio = await asyncio.gather(video_task, sample_task)

                if not video_file:
                    if os.path.exists(INSTAGRAM_COOKIES_FILE):
                        await status_msg.edit("❌ خطا در دانلود ویدیو از اینستاگرام (با وجود فایل کوکی). ممکنه لینک اشتباه، پست خصوصی، یا کوکی منقضی‌شده باشه.")
                    else:
                        await status_msg.edit("❌ خطا در دانلود ویدیو از اینستاگرام. این روزها اینستاگرام برای اکثر لینک‌ها لاگین می‌خواد — فایل instagram_cookies.txt رو تنظیم کن.")
                    return

                # اگه دانلود مستقیم نمونه صدا شکست خورد، از روی ویدیوی
                # دانلودشده (فقط چند ثانیه اولش، نه کل صدا) استخراج کن
                if not short_audio:
                    short_audio = await loop.run_in_executor(_executor, extract_audio_chunk, video_file, job_id)
                    if not short_audio:
                        await status_msg.edit("❌ استخراج صدا ناموفق بود.")
                        return

                await status_msg.edit("🔍 در حال تشخیص آهنگ...")

                # ۲. تشخیص آهنگ با AudD (async، بدون اشغال ترد)
                out = await recognize_song_audd(short_audio)

                track_title = "Unknown Track"
                track_artist = "Unknown Artist"

                if out and "title" in out:
                    track_title = out["title"]
                    track_artist = out.get("artist", "")
                    search_query = f"{track_artist} - {track_title}"

                    await status_msg.edit(
                        f"🎵 آهنگ پیدا شد:\n"
                        f"{search_query}\n\n"
                        f"📥 دانلود نسخه کامل..."
                    )

                    # ۳. دانلود نسخه کامل از یوتیوب
                    full_audio = await loop.run_in_executor(_executor, download_full_track, search_query, job_id)
                else:
                    await status_msg.edit("⚠️ آهنگ شناسایی نشد. صدای خود ویدیو ارسال می‌شود.")
                    full_audio = short_audio

                # ۴. ارسال فایل‌ها به تلگرام
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
                for f in {video_file, short_audio, full_audio}:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except Exception:
                            pass
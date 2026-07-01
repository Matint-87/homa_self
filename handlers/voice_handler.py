"""
============================================================
 Voice Handler — تبدیل متن به ویس با هوش مصنوعی (edge-tts)
============================================================

این ماژول یک هندلر برای Telethon می‌سازه که با فرستادن دستور:

    *ویس <متن>

متن رو به صدای طبیعی (هوش مصنوعی مایکروسافت / edge-tts) تبدیل
می‌کنه و به‌صورت ویس‌مسیج (voice note) می‌فرسته. پیام دستور هم
بعد از پردازش حذف می‌شه و فقط ویس باقی می‌مونه.

نصب پیش‌نیازها:
    pip install telethon edge-tts

همچنین نیاز به ffmpeg روی سیستم داری (برای تبدیل mp3 به ogg/opus
که فرمت استاندارد ویس گرد تلگرامه):
    - ویندوز : از https://ffmpeg.org دانلود کن و به PATH اضافه کن
    - لینوکس : sudo apt install ffmpeg
    - ترموکس : pkg install ffmpeg
    - مک     : brew install ffmpeg

نحوه‌ی استفاده در فایل اصلی self-bot:

    from telethon import TelegramClient
    from voice_handler import register_voice_handler

    client = TelegramClient("session_name", API_ID, API_HASH)
    register_voice_handler(client)

    client.start()
    client.run_until_disconnected()
"""

import os
import shutil
import asyncio
import tempfile

import edge_tts
from telethon import events


# ------------------------------------------------------------------
# تنظیمات قابل تغییر
# ------------------------------------------------------------------

CONFIG = {
    # پیشوند و کلیدواژه‌ی دستور — هر چیزی که خواستی تغییرش بده
    "prefix": "*",
    "command": "ویس",

    # صدای پیش‌فرض. چند گزینه‌ی فارسی edge-tts:
    #   fa-IR-FaridNeural   -> صدای مرد
    #   fa-IR-DilaraNeural  -> صدای زن
    "voice": "fa-IR-FaridNeural",

    # سرعت و زیر و بمی صدا (اختیاری)
    "rate": "+0%",
    "pitch": "+0Hz",
}


# ------------------------------------------------------------------
# بررسی وجود ffmpeg روی سیستم
# ------------------------------------------------------------------

def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# ------------------------------------------------------------------
# تولید فایل صوتی از روی متن
# ------------------------------------------------------------------

async def _text_to_voice_note(text: str) -> str:
    """
    متن رو با edge-tts به mp3 تبدیل می‌کنه، بعد (اگه ffmpeg موجود
    باشه) به ogg/opus تبدیلش می‌کنه تا به‌صورت ویس گرد واقعی نمایش
    داده شه. مسیر فایل نهایی رو برمی‌گردونه.
    """
    tmp_dir = tempfile.mkdtemp(prefix="tts_")
    mp3_path = os.path.join(tmp_dir, "voice.mp3")
    ogg_path = os.path.join(tmp_dir, "voice.ogg")

    communicate = edge_tts.Communicate(
        text,
        CONFIG["voice"],
        rate=CONFIG["rate"],
        pitch=CONFIG["pitch"],
    )
    await communicate.save(mp3_path)

    if _has_ffmpeg():
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", mp3_path,
            "-c:a", "libopus", "-b:a", "48k", "-ar", "48000", "-ac", "1",
            ogg_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        if os.path.exists(ogg_path):
            return ogg_path

    # اگه ffmpeg نبود یا تبدیل شکست خورد، همون mp3 رو برمی‌گردونیم
    # (به‌صورت فایل صوتی معمولی فرستاده می‌شه، نه ویس گرد)
    return mp3_path


# ------------------------------------------------------------------
# ثبت هندلر روی کلاینت
# ------------------------------------------------------------------

def register_voice_handler(client):
    """
    این تابع رو با کلاینت تلتون خودت صدا بزن تا هندلر فعال شه:

        register_voice_handler(client)
    """
    prefix = CONFIG["prefix"]
    command = CONFIG["command"]
    pattern = rf'^\{prefix}{command}\s+([\s\S]+)$'

    @client.on(events.NewMessage(outgoing=True, pattern=pattern))
    async def voice_handler(event):
        text = event.pattern_match.group(1).strip()
        chat_id = event.chat_id

        # پیام دستور رو حذف می‌کنیم (طبق خواسته‌ت)
        await event.delete()

        if not text:
            return

        tmp_path = None
        try:
            tmp_path = await _text_to_voice_note(text)
            is_ogg = tmp_path.endswith(".ogg")
            await client.send_file(
                chat_id,
                tmp_path,
                voice_note=is_ogg,
            )
        except Exception as e:
            err_msg = await client.send_message(
                chat_id, f"⚠️ خطا در تولید ویس: {e}"
            )
            await asyncio.sleep(5)
            await err_msg.delete()
        finally:
            if tmp_path and os.path.exists(tmp_path):
                shutil.rmtree(os.path.dirname(tmp_path), ignore_errors=True)

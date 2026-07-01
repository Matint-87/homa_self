
import os
import re
import time

from telethon import events
from telethon.tl.types import PeerChannel

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# فرمت‌های قابل قبول لینک:
#   https://t.me/c/<channel_id>/<msg_id>      -> کانال/گروه خصوصی
#   https://t.me/<username>/<msg_id>          -> کانال/گروه عمومی
LINK_RE = re.compile(
    r"(?:https?://)?t\.me/(?:c/(?P<cid>\d+)|(?P<username>[A-Za-z0-9_]+))/(?P<msg_id>\d+)"
)


def _parse_link(link: str):
    match = LINK_RE.search(link)
    if not match:
        return None
    msg_id = int(match.group("msg_id"))
    if match.group("cid"):
        return PeerChannel(int(match.group("cid"))), msg_id
    return match.group("username"), msg_id


def register_download_handler(client):
    """این تابع رو با کلاینت Telethon خودت صدا بزن تا هندلر دانلود فعال بشه."""

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*دانلود\s+(\S+)"))
    async def _download_handler(event):
        link = event.pattern_match.group(1).strip()
        parsed = _parse_link(link)

        if not parsed:
            await event.edit("❌ لینک معتبر نیست. فرمت درست: `*دانلود https://t.me/c/123456/45`")
            return

        peer, msg_id = parsed

        await event.edit("⏳ در حال دریافت پیام...")

        try:
            entity = await client.get_entity(peer)
            target_msg = await client.get_messages(entity, ids=msg_id)
        except Exception as e:
            await event.edit(
                "❌ نتونستم به این پیام دسترسی پیدا کنم.\n"
                "مطمئن شو اکانت خودت عضو این کانال/گروهه.\n"
                f"خطا: {e}"
            )
            return

        if not target_msg or not target_msg.media:
            await event.edit("❌ این پیام مدیایی برای دانلود نداره.")
            return

        last_edit = time.time()

        async def progress(current, total):
            nonlocal last_edit
            now = time.time()
            if now - last_edit < 2:  # برای جلوگیری از ادیت زیاد، هر ۲ ثانیه یه بار
                return
            last_edit = now
            percent = current * 100 / total if total else 0
            try:
                await event.edit(f"⬇️ در حال دانلود... {percent:.0f}%")
            except Exception:
                pass

        try:
            file_path = await client.download_media(
                target_msg, file=DOWNLOAD_DIR + "/", progress_callback=progress
            )
        except Exception as e:
            await event.edit(f"⚠️ خطا در دانلود: {e}")
            return

        if not file_path:
            await event.edit("❌ دانلود ناموفق بود.")
            return

        await event.edit("⬆️ در حال ارسال فایل...")

        try:
            await client.send_file(
                event.chat_id,
                file_path,
                caption=f"✅ دانلود شد از: {link}",
                reply_to=event.id,
            )
            await event.delete()
        except Exception as e:
            await event.edit(f"⚠️ فایل دانلود شد ولی نتونستم بفرستمش: {e}")
            return
        finally:
            try:
                os.remove(file_path)
            except OSError:
                pass

    return _download_handler
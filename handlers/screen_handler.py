"""
============================================================
 Screen Handler — تبدیل پیام به استیکر (مثل @QuotLyBot)
============================================================

روی پیام کسی ریپلای کن و بنویس:
    *اسکرین

پیامش به‌صورت یه کارت/استیکر شیک (شبیه quote) ساخته و به همون
چت فرستاده می‌شه.

نصب پیش‌نیازها:
    pip install telethon pillow arabic_reshaper python-bidi

⚠️ فونت فارسی لازم داری — فونت‌های پیش‌فرض سیستم معمولاً فارسی رو
درست رندر نمی‌کنن (حروف از هم جدا می‌افتن). یه فونت .ttf فارسی
دانلود کن، کنار اسکریپتت بگذار، و مسیرش رو توی CONFIG["font_path"]
وارد کن. پیشنهاد رایگان: Vazirmatn
    https://github.com/rastikerdar/vazirmatn/releases

نحوه‌ی استفاده در فایل اصلی:
    from telethon import TelegramClient
    from screen_handler import register_screen_handler

    client = TelegramClient(...)
    register_screen_handler(client)
"""

import os
import asyncio
import tempfile

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont, ImageOps

from telethon import events
from telethon.tl.types import DocumentAttributeSticker, InputStickerSetEmpty


CONFIG = {
    "prefix": "*",
    "command": "اسکرین",

    # مسیر فونت فارسی — حتماً قبل از استفاده درستش کن
    "font_path": "Vazirmatn-SemiBold.ttf",
    "font_size": 34,
    "name_font_size": 30,

    "bubble_color": (35, 35, 40, 255),     # رنگ پس‌زمینه‌ی کارت
    "text_color": (240, 240, 240, 255),    # رنگ متن پیام
    "name_color": (90, 170, 255, 255),     # رنگ اسم فرستنده

    "min_width": 360,
    "max_width": 760,
    "padding": 40,
    "gap": 20,
    "avatar_size": 90,

    # اندازه‌ی نهایی موردنیاز برای فرمت استیکر تلگرام
    "sticker_max_side": 512,
}


def _shape_fa(text: str) -> str:
    """متن فارسی/عربی رو برای نمایش صحیح (راست‌به‌چپ + اتصال حروف) آماده می‌کنه."""
    return get_display(arabic_reshaper.reshape(text))


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textlength(_shape_fa(test), font=font)
        if w <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


async def _build_quote_image(client, sender, text: str) -> str:
    if not os.path.exists(CONFIG["font_path"]):
        raise FileNotFoundError(
            f"فونت پیدا نشد: {CONFIG['font_path']} — یه فونت فارسی .ttf دانلود کن "
            "و مسیرش رو توی CONFIG['font_path'] درست کن."
        )

    font = ImageFont.truetype(CONFIG["font_path"], CONFIG["font_size"])
    name_font = ImageFont.truetype(CONFIG["font_path"], CONFIG["name_font_size"])
    dummy = ImageDraw.Draw(Image.new("RGBA", (10, 10)))

    max_text_width = (
        CONFIG["max_width"] - CONFIG["padding"] * 2 - CONFIG["avatar_size"] - CONFIG["gap"]
    )
    lines = _wrap_text(dummy, text, font, max_text_width)

    name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "کاربر"

    # عرض واقعی موردنیاز رو حساب می‌کنیم (کارت رو فقط به اندازه‌ی لازم بزرگ می‌کنیم)
    longest_line = max([dummy.textlength(_shape_fa(l), font=font) for l in lines], default=0)
    name_w = dummy.textlength(_shape_fa(name), font=name_font)
    content_w = max(longest_line, name_w)

    bubble_width = int(min(
        CONFIG["max_width"],
        max(CONFIG["min_width"], content_w + CONFIG["avatar_size"] + CONFIG["padding"] * 2 + CONFIG["gap"]),
    ))

    line_height = font.getbbox("سلام")[3] + 14
    name_height = name_font.getbbox("سلام")[3] + 20
    bubble_height = CONFIG["padding"] * 2 + name_height + len(lines) * line_height
    bubble_height = max(bubble_height, CONFIG["avatar_size"] + CONFIG["padding"] * 2)

    img = Image.new("RGBA", (bubble_width, bubble_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (bubble_width, bubble_height)], radius=30, fill=CONFIG["bubble_color"])

    # دانلود و رسم آواتار دایره‌ای
    avatar_path = tempfile.mktemp(suffix=".jpg")
    text_end_x = bubble_width - CONFIG["padding"]
    try:
        downloaded = await client.download_profile_photo(sender, file=avatar_path)
    except Exception:
        downloaded = None

    if downloaded and os.path.exists(downloaded):
        avatar = Image.open(downloaded).convert("RGBA")
        avatar = ImageOps.fit(avatar, (CONFIG["avatar_size"], CONFIG["avatar_size"]))
        mask = Image.new("L", avatar.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0) + avatar.size, fill=255)
        avatar_x = bubble_width - CONFIG["padding"] - CONFIG["avatar_size"]
        img.paste(avatar, (avatar_x, CONFIG["padding"]), mask)
        os.remove(downloaded)
        text_end_x = avatar_x - CONFIG["gap"]

    # اسم فرستنده (راست‌چین)
    shaped_name = _shape_fa(name)
    draw.text(
        (text_end_x - dummy.textlength(shaped_name, font=name_font), CONFIG["padding"]),
        shaped_name, font=name_font, fill=CONFIG["name_color"],
    )

    # متن پیام، خط‌به‌خط، راست‌چین
    y = CONFIG["padding"] + name_height
    for line in lines:
        shaped_line = _shape_fa(line)
        draw.text(
            (text_end_x - dummy.textlength(shaped_line, font=font), y),
            shaped_line, font=font, fill=CONFIG["text_color"],
        )
        y += line_height

    # تبدیل به اندازه‌ی استاندارد استیکر و ذخیره به فرمت webp
    max_side = max(img.size)
    if max_side > CONFIG["sticker_max_side"]:
        scale = CONFIG["sticker_max_side"] / max_side
        img = img.resize((int(img.width * scale), int(img.height * scale)))

    out_path = tempfile.mktemp(suffix=".webp")
    img.save(out_path, "WEBP")
    return out_path


def register_screen_handler(client):
    """
    این تابع رو با کلاینت تلتون خودت صدا بزن:
        register_screen_handler(client)
    """
    prefix = CONFIG["prefix"]
    command = CONFIG["command"]
    pattern = rf'^\{prefix}{command}\s*$'

    @client.on(events.NewMessage(outgoing=True, pattern=pattern))
    async def screen_handler(event):
        if not event.is_reply:
            await event.edit("⚠️ باید روی یه پیام ریپلای کنی و بعد *اسکرین رو بفرستی.")
            await asyncio.sleep(4)
            await event.delete()
            return

        replied = await event.get_reply_message()
        await event.delete()

        if not replied or not replied.text:
            warn = await client.send_message(event.chat_id, "⚠️ فقط پیام‌های متنی قابل تبدیل به استیکرن.")
            await asyncio.sleep(4)
            await warn.delete()
            return

        sender = await replied.get_sender()

        img_path = None
        try:
            img_path = await _build_quote_image(client, sender, replied.text)
            await client.send_file(
                event.chat_id,
                img_path,
                attributes=[DocumentAttributeSticker(alt="📌", stickerset=InputStickerSetEmpty())],
                force_document=False,
            )
        except Exception as e:
            err = await client.send_message(event.chat_id, f"⚠️ خطا در ساخت استیکر: {e}")
            await asyncio.sleep(6)
            await err.delete()
        finally:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
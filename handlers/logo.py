# =========================================
# هندلر ساخت لوگو (Text → Logo Image) - نسخه‌ی 10 استایل رندوم
# دستور: *لوگو <متن دلخواه>   مثال: *لوگو متین
# هر بار اجرا، یکی از 10 استایل بصورت کاملا رندوم انتخاب و رندر می‌شود
# =========================================
import os
import io
import random

from telethon import events
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# تلاش برای ایمپورت کتابخونه‌های اتصال حروف فارسی/عربی
# (در صورت نصب نبودن، روی متن انگلیسی/اعداد همچنان کار می‌کند)
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_RESHAPER = True
except ImportError:
    HAS_RESHAPER = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSIAN_FONT_PATH = os.path.join(BASE_DIR, "fonts", "Vazirmatn-SemiBold.ttf")
FALLBACK_FONT_PATH = os.path.join(BASE_DIR, "fonts", "Vazirmatn-SemiBold.ttf")

CANVAS_W, CANVAS_H = 900, 450

# ---------- پالت‌های رنگی هر استایل ----------
GRADIENTS = [
    ((255, 94, 98), (255, 195, 113)),   # قرمز-نارنجی
    ((78, 84, 200), (143, 148, 251)),   # بنفش-آبی
    ((11, 132, 165), (32, 233, 195)),   # فیروزه‌ای
    ((247, 151, 30), (255, 210, 0)),    # نارنجی-زرد
    ((131, 58, 180), (253, 29, 29)),    # بنفش-قرمز
    ((0, 198, 255), (0, 114, 255)),     # آبی روشن
]

NEON_PALETTE = [
    (0, 255, 255), (255, 0, 200), (0, 255, 120), (255, 230, 0), (160, 60, 255),
]

FLAT_PALETTE = [
    (236, 64, 122), (38, 166, 154), (255, 152, 0),
    (92, 107, 192), (239, 83, 80), (38, 198, 218),
]

STRIPE_PALETTES = [
    [(255, 87, 87), (255, 189, 89), (255, 245, 200)],
    [(72, 52, 212), (129, 236, 236), (223, 230, 233)],
    [(214, 48, 49), (250, 177, 160), (255, 234, 167)],
]


def get_font_path() -> str:
    """اگه فونت فارسی Vazirmatn موجود باشه از همون استفاده می‌کنه، وگرنه فونت پیش‌فرض"""
    if os.path.exists(PERSIAN_FONT_PATH):
        return PERSIAN_FONT_PATH
    return FALLBACK_FONT_PATH


def prepare_text(text: str) -> str:
    """اتصال صحیح حروف فارسی/عربی + ترتیب راست‌به‌چپ برای نمایش درست در تصویر"""
    if HAS_RESHAPER:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    return text


# ---------- توابع کمکی مشترک بین همه‌ی استایل‌ها ----------

def make_gradient(size, color1, color2, diagonal: bool = False) -> Image.Image:
    """ساخت بک‌گراند گرادیانی عمودی یا اریب بین دو رنگ"""
    w, h = size
    base = Image.new("RGB", (w, h), color1)
    top = Image.new("RGB", (w, h), color2)
    mask = Image.new("L", (w, h))
    if diagonal:
        total = w + h
        mask.putdata([int(255 * ((x + y) / total)) for y in range(h) for x in range(w)])
    else:
        mask.putdata([int(255 * (y / h)) for y in range(h) for _ in range(w)])
    base.paste(top, (0, 0), mask)
    return base


def fit_font(draw, text, font_path, max_w, max_h, start_size=170, min_size=10, step=4):
    """کوچک کردن تدریجی فونت تا متن داخل کادر مشخص‌شده جا شود"""
    font_size = start_size
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    while font_size > min_size:
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            break
        font_size -= step
    return font, bbox


def centered_pos(width, height, bbox):
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    return ((width - tw) / 2 - bbox[0], (height - th) / 2 - bbox[1])


# =========================================
# استایل 1 - کارت گرادیانی (استایل اصلی فایل قبلی)
# =========================================
def style_01_card_gradient(text, display_text, width, height, font_path):
    color1, color2 = random.choice(GRADIENTS)
    bg = make_gradient((width, height), color1, color2).convert("RGBA")

    margin = 60
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [margin, margin, width - margin, height - margin],
        radius=40, fill=(255, 255, 255, 235),
    )
    shadow = card.filter(ImageFilter.GaussianBlur(14))
    bg.alpha_composite(shadow, (0, 10))
    bg.alpha_composite(card, (0, 0))

    draw = ImageDraw.Draw(bg)
    max_w = width - margin * 2 - 60
    max_h = height - margin * 2 - 60
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=170)
    pos = centered_pos(width, height, bbox)

    draw.text((pos[0] + 3, pos[1] + 3), display_text, font=font, fill=(0, 0, 0, 50))
    text_color = tuple((c1 + c2) // 2 for c1, c2 in zip(color1, color2))
    draw.text(pos, display_text, font=font, fill=text_color + (255,))
    return bg


# =========================================
# استایل 2 - نئون درخشان
# =========================================
def style_02_neon_glow(text, display_text, width, height, font_path):
    bg = Image.new("RGBA", (width, height), (10, 10, 20, 255))
    neon = random.choice(NEON_PALETTE)

    tmp_draw = ImageDraw.Draw(bg)
    max_w = width - 100
    max_h = height - 100
    font, bbox = fit_font(tmp_draw, display_text, font_path, max_w, max_h, start_size=160)
    pos = centered_pos(width, height, bbox)

    # لایه‌ی هاله‌ی نوری دور (بلور قوی)
    glow_wide = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow_wide).text(pos, display_text, font=font, fill=neon + (255,))
    glow_wide = glow_wide.filter(ImageFilter.GaussianBlur(10))
    bg.alpha_composite(glow_wide)

    # لایه‌ی هاله‌ی نزدیک (بلور کم)
    glow_tight = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow_tight).text(pos, display_text, font=font, fill=neon + (255,))
    glow_tight = glow_tight.filter(ImageFilter.GaussianBlur(4))
    bg.alpha_composite(glow_tight)

    # متن اصلی شارپ روی هاله
    ImageDraw.Draw(bg).text(pos, display_text, font=font, fill=(255, 255, 255, 255))

    # کادر نازک نئونی اطراف بوم
    border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [12, 12, width - 12, height - 12], radius=24, outline=neon + (255,), width=3
    )
    bg.alpha_composite(border.filter(ImageFilter.GaussianBlur(3)))
    bg.alpha_composite(border)
    return bg


# =========================================
# استایل 3 - مینیمال تخت
# =========================================
def style_03_flat_minimal(text, display_text, width, height, font_path):
    color = random.choice(FLAT_PALETTE)
    bg = Image.new("RGBA", (width, height), color + (255,))
    draw = ImageDraw.Draw(bg)

    max_w = width - 160
    max_h = height - 200
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=150)
    pos = centered_pos(width, height, bbox)
    draw.text(pos, display_text, font=font, fill=(255, 255, 255, 255))

    tw = bbox[2] - bbox[0]
    line_y = pos[1] + (bbox[3] - bbox[1]) + 35
    line_w = min(tw * 0.5, 160)
    draw.rectangle(
        [width / 2 - line_w / 2, line_y, width / 2 + line_w / 2, line_y + 5],
        fill=(255, 255, 255, 255),
    )
    return bg


# =========================================
# استایل 4 - مدال دایره‌ای
# =========================================
def style_04_circle_badge(text, display_text, width, height, font_path):
    bg = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    color1, color2 = random.choice(GRADIENTS)

    diameter = min(width, height) - 60
    cx, cy = width // 2, height // 2
    circle_bg = make_gradient((diameter, diameter), color1, color2).convert("RGBA")
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, diameter, diameter], fill=255)
    bg.paste(circle_bg, (cx - diameter // 2, cy - diameter // 2), mask)

    draw = ImageDraw.Draw(bg)
    draw.ellipse(
        [cx - diameter // 2 + 6, cy - diameter // 2 + 6, cx + diameter // 2 - 6, cy + diameter // 2 - 6],
        outline=(255, 255, 255, 255), width=6,
    )

    inner = int(diameter * 0.62)
    font, bbox = fit_font(draw, display_text, font_path, inner, inner, start_size=140)
    pos = centered_pos(width, height, bbox)
    draw.text((pos[0] + 2, pos[1] + 2), display_text, font=font, fill=(0, 0, 0, 60))
    draw.text(pos, display_text, font=font, fill=(255, 255, 255, 255))
    return bg


# =========================================
# استایل 5 - خطوط توخالی (متن فقط با حاشیه)
# =========================================
def style_05_outline(text, display_text, width, height, font_path):
    color1, color2 = random.choice(GRADIENTS)
    bg = make_gradient((width, height), color1, color2, diagonal=True).convert("RGBA")

    tmp_draw = ImageDraw.Draw(bg)
    max_w = width - 120
    max_h = height - 120
    font, bbox = fit_font(tmp_draw, display_text, font_path, max_w, max_h, start_size=180)
    pos = centered_pos(width, height, bbox)

    outline_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(outline_layer)
    # اول حروف را با حاشیه‌ی ضخیم سفید پر می‌کنیم
    odraw.text(pos, display_text, font=font, fill=(255, 255, 255, 255),
                stroke_width=6, stroke_fill=(255, 255, 255, 255))
    # سپس داخل حروف را کاملا شفاف می‌کنیم تا فقط دورِ آن‌ها (حاشیه) دیده شود
    odraw.text(pos, display_text, font=font, fill=(0, 0, 0, 0))

    bg.alpha_composite(outline_layer)
    return bg


# =========================================
# استایل 6 - نوارهای رترو
# =========================================
def style_06_retro_stripes(text, display_text, width, height, font_path):
    palette = random.choice(STRIPE_PALETTES)
    bg = Image.new("RGBA", (width, height), palette[-1] + (255,))
    draw = ImageDraw.Draw(bg)

    stripe_h = max(20, height // (len(palette) * 2))
    colors_cycle = palette * 4
    y, i = 0, 0
    while y < height:
        draw.rectangle([0, y, width, y + stripe_h], fill=colors_cycle[i % len(colors_cycle)] + (255,))
        y += stripe_h
        i += 1

    max_w = width - 100
    max_h = height - 140
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=160)
    pos = centered_pos(width, height, bbox)
    draw.text((pos[0] + 4, pos[1] + 4), display_text, font=font, fill=(0, 0, 0, 160))
    draw.text(pos, display_text, font=font, fill=(255, 255, 255, 255))
    return bg


# =========================================
# استایل 7 - اریب دو رنگ
# =========================================
def style_07_diagonal_split(text, display_text, width, height, font_path):
    color1, color2 = random.choice(GRADIENTS)
    bg = Image.new("RGBA", (width, height), color1 + (255,))
    draw = ImageDraw.Draw(bg)
    draw.polygon(
        [(width * 0.4, 0), (width, 0), (width, height), (width * 0.05, height)],
        fill=color2 + (255,),
    )

    max_w = width - 120
    max_h = height - 120
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=160)
    pos = centered_pos(width, height, bbox)
    draw.text((pos[0] + 3, pos[1] + 3), display_text, font=font, fill=(0, 0, 0, 90))
    draw.text(pos, display_text, font=font, fill=(255, 255, 255, 255))
    return bg


# =========================================
# استایل 8 - کارت نقطه‌چین
# =========================================
def style_08_dotted_card(text, display_text, width, height, font_path):
    base_color = random.choice(FLAT_PALETTE)
    light_bg = tuple(min(255, c + 60) for c in base_color)
    bg = Image.new("RGBA", (width, height), light_bg + (255,))
    draw = ImageDraw.Draw(bg)

    spacing = 26
    for yy in range(0, height, spacing):
        for xx in range(0, width, spacing):
            draw.ellipse([xx - 2, yy - 2, xx + 2, yy + 2], fill=base_color + (120,))

    margin = 70
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [margin, margin, width - margin, height - margin], radius=36, fill=(255, 255, 255, 245)
    )
    bg.alpha_composite(card.filter(ImageFilter.GaussianBlur(12)), (0, 8))
    bg.alpha_composite(card, (0, 0))

    max_w = width - margin * 2 - 50
    max_h = height - margin * 2 - 50
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=150)
    pos = centered_pos(width, height, bbox)
    draw.text(pos, display_text, font=font, fill=base_color + (255,))
    return bg


# =========================================
# استایل 9 - افکت سه‌بعدی
# =========================================
def style_09_3d_extrude(text, display_text, width, height, font_path):
    color1, color2 = random.choice(GRADIENTS)
    bg = Image.new("RGBA", (width, height), (245, 245, 245, 255))
    draw = ImageDraw.Draw(bg)

    max_w = width - 140
    max_h = height - 160
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=160)
    pos = centered_pos(width, height, bbox)

    depth = 10
    for i in range(depth, 0, -1):
        shade = tuple(max(0, c - i * 8) for c in color2)
        draw.text((pos[0] + i, pos[1] + i), display_text, font=font, fill=shade + (255,))
    draw.text(pos, display_text, font=font, fill=color1 + (255,))
    return bg


# =========================================
# استایل 10 - شیشه‌ای مدرن (Glassmorphism)
# =========================================
def style_10_glass(text, display_text, width, height, font_path):
    color1, color2 = random.choice(GRADIENTS)
    bg = make_gradient((width, height), color1, color2, diagonal=True).convert("RGBA")

    # حباب‌های محوِ تزئینی پشت زمینه
    bubbles = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(bubbles)
    for _ in range(4):
        r = random.randint(40, 110)
        bx, by = random.randint(0, width), random.randint(0, height)
        bdraw.ellipse([bx - r, by - r, bx + r, by + r], fill=(255, 255, 255, 40))
    bg.alpha_composite(bubbles.filter(ImageFilter.GaussianBlur(6)))

    margin = 70
    glass = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glass).rounded_rectangle(
        [margin, margin, width - margin, height - margin], radius=34, fill=(255, 255, 255, 55)
    )
    bg.alpha_composite(glass.filter(ImageFilter.GaussianBlur(2)))

    border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        [margin, margin, width - margin, height - margin], radius=34,
        outline=(255, 255, 255, 160), width=2,
    )
    bg.alpha_composite(border)

    draw = ImageDraw.Draw(bg)
    max_w = width - margin * 2 - 60
    max_h = height - margin * 2 - 60
    font, bbox = fit_font(draw, display_text, font_path, max_w, max_h, start_size=150)
    pos = centered_pos(width, height, bbox)
    draw.text((pos[0] + 2, pos[1] + 2), display_text, font=font, fill=(0, 0, 0, 80))
    draw.text(pos, display_text, font=font, fill=(255, 255, 255, 255))
    return bg


# ---------- دیسپچر استایل‌ها ----------
STYLES = {
    1: style_01_card_gradient,
    2: style_02_neon_glow,
    3: style_03_flat_minimal,
    4: style_04_circle_badge,
    5: style_05_outline,
    6: style_06_retro_stripes,
    7: style_07_diagonal_split,
    8: style_08_dotted_card,
    9: style_09_3d_extrude,
    10: style_10_glass,
}

STYLE_NAMES = {
    1: "کارت گرادیانی",
    2: "نئون درخشان",
    3: "مینیمال تخت",
    4: "مدال دایره‌ای",
    5: "خطوط توخالی",
    6: "نوارهای رترو",
    7: "اریب دو رنگ",
    8: "کارت نقطه‌چین",
    9: "افکت سه‌بعدی",
    10: "شیشه‌ای مدرن",
}


def generate_logo(text: str, width: int = CANVAS_W, height: int = CANVAS_H):
    """ساخت تصویر لوگو با یکی از 10 استایل رندوم. خروجی: (BytesIO, نام_استایل)"""
    display_text = prepare_text(text)
    font_path = get_font_path()

    style_index = random.randint(1, 10)
    img = STYLES[style_index](text, display_text, width, height, font_path)

    buf = io.BytesIO()
    buf.name = "logo.png"
    img.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf, STYLE_NAMES[style_index]


def register_logo_handler(client):
    """رجیستر کردن هندلر لوگو روی کلاینت"""

    # الگو: *لوگو <متن>   مثال: *لوگو متین
    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*لوگو\s+(.+)$"))
    async def make_logo(event):
        text = event.pattern_match.group(1).strip()
        if not text:
            return
        await event.delete()
        status = await event.respond("⏳ در حال ساخت لوگو...")
        try:
            image_buffer, style_name = generate_logo(text)
            await event.client.send_file(
                event.chat_id,
                image_buffer,
                caption=f"🎨 لوگوی «{text}»\n✨ استایل: {style_name}",
            )
        except Exception as e:
            await event.respond(f"❌ خطا در ساخت لوگو: {e}")
        finally:
            await status.delete()
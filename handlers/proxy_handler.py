# =========================================
# هندلر پیدا کردن بهترین پروکسی تلگرام (MTProto)
# دستور: *پروکسی
# نیازمندی: pip install aiohttp
#
# منطق کار:
# 1) لیست پروکسی‌های تازه رو از یک منبع متن‌باز معروف می‌گیره
#    (ریپازیتوری SoliSpirit/mtproto - آپدیت هر 12 ساعت، 1.7k استار)
# 2) چون پروکسی‌های رایگان عمر کوتاهی دارن (معمولا زیر 72 ساعت)،
#    به‌صورت Async به هرکدوم وصل می‌شه و تاخیر (latency) واقعی رو می‌سنجه
# 3) فقط پروکسی‌هایی که واقعا آنلاین و سریع هستن رو برمی‌گردونه
# =========================================
import re
import time
import random
import asyncio

import aiohttp
from telethon import events

# می‌تونی این لیست رو با هر منبع متنی دیگه که فرمت tg://proxy?server=..&port=..&secret=..
# داره گسترش بدی (مثلا یک کانال تلگرامی پروکسی که خودت بهش اعتماد داری)
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt",
]

# الگوی استخراج پروکسی از متن (هم فرمت tg:// و هم فرمت https://t.me/proxy رو می‌گیره)
PROXY_PATTERN = re.compile(
    r"(?:tg://proxy|https?://t\.me/proxy)\?server=([\w\.\-]+)&port=(\d+)&secret=([0-9a-fA-F]+)"
)

TOP_N = 3                 # تعداد بهترین پروکسی‌هایی که نهایتا نشون داده می‌شه
MAX_CANDIDATES = 150      # حداکثر تعداد پروکسی که تست می‌شه (برای محدود کردن زمان اجرا)
TEST_TIMEOUT = 4.0        # تایم‌اوت تست اتصال هر پروکسی (ثانیه)
TEST_CONCURRENCY = 40     # تعداد تست‌های همزمان


async def fetch_source(session: "aiohttp.ClientSession", url: str) -> str | None:
    """دانلود محتوای متنی یک منبع پروکسی"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        pass
    return None


def extract_proxies(text: str) -> set:
    """استخراج تمام لینک‌های پروکسی موجود در یک متن"""
    return set(PROXY_PATTERN.findall(text))


async def test_proxy(server: str, port: int, timeout: float = TEST_TIMEOUT) -> float | None:
    """تست اتصال TCP خام به سرور پروکسی و اندازه‌گیری تاخیر (میلی‌ثانیه)"""
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(server, port), timeout=timeout
        )
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return latency_ms
    except Exception:
        return None


async def find_best_proxies(top_n: int = TOP_N):
    """جمع‌آوری پروکسی‌ها از منابع + تست زنده + برگرداندن بهترین‌ها"""
    candidates = set()
    async with aiohttp.ClientSession() as session:
        texts = await asyncio.gather(*(fetch_source(session, url) for url in PROXY_SOURCES))
    for text in texts:
        if text:
            candidates.update(extract_proxies(text))

    if not candidates:
        return []

    candidates = list(candidates)
    random.shuffle(candidates)
    candidates = candidates[:MAX_CANDIDATES]

    semaphore = asyncio.Semaphore(TEST_CONCURRENCY)

    async def check(item):
        server, port_str, secret = item
        async with semaphore:
            latency = await test_proxy(server, int(port_str))
        return (server, port_str, secret, latency)

    results = await asyncio.gather(*(check(c) for c in candidates))
    working = [r for r in results if r[3] is not None]
    working.sort(key=lambda r: r[3])
    return working[:top_n]


def register_proxy_handler(client):
    """رجیستر کردن هندلر پروکسی روی کلاینت"""

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*پروکسی$"))
    async def find_proxy(event):
        await event.delete()
        status = await event.respond(
            "🔎 در حال جست‌وجو و تست زنده‌ی بهترین پروکسی‌های تلگرام...\n⏳ چند ثانیه طول می‌کشه"
        )
        try:
            best = await find_best_proxies()
            if not best:
                await status.edit(
                    "❌ در حال حاضر هیچ پروکسی فعالی پیدا نشد.\nچند دقیقه دیگه دوباره با دستور «*پروکسی» امتحان کن."
                )
                return

            lines = ["✅ بهترین پروکسی‌های تلگرام (تست‌شده با پینگ زنده):\n"]
            medals = ["🥇", "🥈", "🥉"]
            for i, (server, port, secret, latency) in enumerate(best):
                medal = medals[i] if i < len(medals) else "▫️"
                link = f"tg://proxy?server={server}&port={port}&secret={secret}"
                lines.append(f"{medal} {int(latency)}ms\n{link}\n")
            lines.append("ℹ️ روی هرکدوم از لینک‌ها بزن؛ تلگرام خودش پیشنهاد فعال‌سازی پروکسی رو نشون می‌ده.")
            await status.edit("\n".join(lines))
        except Exception as e:
            await status.edit(f"❌ خطا در پیدا کردن پروکسی: {e}")

# import requests
# from telethon import events

# # ---------------- تنظیمات ----------------
# BRS_API_KEY = "BtLUVy4dkU2ElbVviGKYuC6BwfQSuNjz" 
# BRS_API_URL = "https://brsapi.ir/Api/Market/Gold_Currency.php"

# # نگاشت نماد فارسی/انگلیسی به symbol موجود در API
# SYMBOLS = {
#     # ارز فیات
#     "دلار": "USD", "usd": "USD",
#     "یورو": "EUR", "eur": "EUR",
#     "پوند": "GBP", "gbp": "GBP",
#     "درهم": "AED", "aed": "AED",
#     "لیر": "TRY", "try": "TRY",
#     "یوان": "CNY", "cny": "CNY",
#     "ین": "JPY", "jpy": "JPY",
#     "فرانک": "CHF", "chf": "CHF",
#     "دلار_کانادا": "CAD", "cad": "CAD",
#     "دلار_استرالیا": "AUD", "aud": "AUD",
#     "ریال_سعودی": "SAR", "sar": "SAR",
#     "دینار_کویت": "KWD", "kwd": "KWD",
#     "روپیه": "INR", "inr": "INR",
#     "روبل": "RUB", "rub": "RUB",
#     "بیتکوین": "BTC", "btc": "BTC",
#     "اتریوم": "ETH", "eth": "ETH",
#     "تتر": "USDT", "usdt": "USDT",
#     "بایننس": "BNB", "bnb": "BNB",
#     "دوج": "DOGE", "doge": "DOGE",
#     "ریپل": "XRP", "xrp": "XRP",
# }


# def fetch_price(symbol: str):
#     """قیمت یک نماد رو از API رایگان می‌گیره و به تومان برمی‌گردونه."""
#     params = {"key": BRS_API_KEY, "section": "currency,crypto"}
#     resp = requests.get(BRS_API_URL, params=params, timeout=10)
#     resp.raise_for_status()
#     data = resp.json()

#     pool = []
#     if isinstance(data, dict):
#         pool.extend(data.get("currency", []))
#         pool.extend(data.get("gold", []))
#         pool.extend(data.get("cryptocurrency", []) or data.get("crypto", []))

#     for item in pool:
#         sym = (item.get("symbol") or item.get("name_en") or "").upper()
#         if sym == symbol.upper():
#             price_rial = item.get("price")
#             if price_rial is None:
#                 continue
#             price_toman = float(price_rial) / 10  # تبدیل ریال به تومان
#             return price_toman
#     return None


# def register_currency_handler(client):
#     """این تابع رو با کلاینت Telethon خودت صدا بزن تا هندلر قیمت ارز فعال بشه."""

#     @client.on(events.NewMessage(outgoing=True, pattern=r"^\*(\S+)"))
#     async def _currency_handler(event):
#         raw = event.pattern_match.group(1).strip().lower()
#         symbol = SYMBOLS.get(raw)

#         if not symbol:
#             await event.edit(
#                 f"❌ نماد «{raw}» شناخته‌شده نیست.\n"
#                 f"نمادهای مجاز: {', '.join(sorted(set(SYMBOLS.keys())))}"
#             )
#             return

#         try:
#             price = fetch_price(symbol)
#         except Exception as e:
#             await event.edit(f"⚠️ خطا در دریافت قیمت")
#             return

#         if price is None:
#             await event.edit(f"❌ قیمتی برای {symbol} پیدا نشد.")
#             return

#         price_str = f"{price:,.0f}"
#         await event.edit(f"💱 {symbol}: {price_str} تومان")

#     return _currency_handler


"""
currency_handler.py
ماژول نمایش قیمت لحظه‌ای ارز و رمزارز به تومان برای سلف‌بات Telethon

نحوه استفاده در سلف‌بات خودت:

    from currency_handler import register_currency_handler

    register_currency_handler(client)

بعد از این، با فرستادن پیام‌هایی مثل *دلار ، *یورو ، *بیتکوین ، *تتر
پیام خودت به‌صورت خودکار با قیمت لحظه‌ای جایگزین میشه.

این نسخه از API سرویس AlanChand استفاده می‌کنه (api.alanchand.com).

قبل از استفاده:
    1) pip install requests
    2) توکن رایگانی که از ربات تلگرام @alanchand_token_bot گرفتی رو
       توی ALANCHAND_TOKEN پایین بذار (دقت کن این توکن تاریخ انقضا داره،
       هر چند وقت یک‌بار باید دوباره از ربات بگیری و آپدیت کنی).
"""

import requests
from telethon import events

# ---------------- تنظیمات ----------------
ALANCHAND_TOKEN = "c1V7wjWWpGUgJjRnzk1V"  # توکن رایگان از @alanchand_token_bot -- تاریخ انقضا: 2026-07-03
ALANCHAND_BASE_URL = "https://api.alanchand.com/"

# هر category به endpoint نوع خودش متصل میشه: currencies | golds | crypto
SYMBOLS = {
    # ارز فیات -> category: currencies
    "دلار": ("currencies", "usd"), "usd": ("currencies", "usd"),
    "یورو": ("currencies", "eur"), "eur": ("currencies", "eur"),
    "پوند": ("currencies", "gbp"), "gbp": ("currencies", "gbp"),
    "درهم": ("currencies", "aed"), "aed": ("currencies", "aed"),
    "لیر": ("currencies", "try"), "try": ("currencies", "try"),
    "یوان": ("currencies", "cny"), "cny": ("currencies", "cny"),
    "ین": ("currencies", "jpy"), "jpy": ("currencies", "jpy"),
    "فرانک": ("currencies", "chf"), "chf": ("currencies", "chf"),
    "دلار_کانادا": ("currencies", "cad"), "cad": ("currencies", "cad"),
    "دلار_استرالیا": ("currencies", "aud"), "aud": ("currencies", "aud"),
    "ریال_سعودی": ("currencies", "sar"), "sar": ("currencies", "sar"),
    "دینار_کویت": ("currencies", "kwd"), "kwd": ("currencies", "kwd"),
    "روپیه": ("currencies", "inr"), "inr": ("currencies", "inr"),
    "روبل": ("currencies", "rub"), "rub": ("currencies", "rub"),
    # رمزارز -> category: crypto
    "بیتکوین": ("crypto", "btc"), "btc": ("crypto", "btc"),
    "اتریوم": ("crypto", "eth"), "eth": ("crypto", "eth"),
    "تتر": ("crypto", "usdt"), "usdt": ("crypto", "usdt"),
    "بایننس": ("crypto", "bnb"), "bnb": ("crypto", "bnb"),
    "دوج": ("crypto", "doge"), "doge": ("crypto", "doge"),
    "ریپل": ("crypto", "xrp"), "xrp": ("crypto", "xrp"),
}

# کش ساده برای هر category تا برای هر پیام، کل دیتای یک نوع رو دوباره نگیریم
_cache = {}


def _fetch_category(category: str):
    if category in _cache:
        return _cache[category]
    params = {"type": category, "token": ALANCHAND_TOKEN}
    resp = requests.get(ALANCHAND_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _cache[category] = data
    return data


def _find_item(data, symbol: str):
    """به‌صورت بازگشتی دنبال آیتمی می‌گرده که symbol/slug/name_en بهش بخوره."""
    symbol_lower = symbol.lower()

    def matches(d):
        for key in ("symbol", "slug", "name_en", "en_name", "code"):
            val = d.get(key)
            if isinstance(val, str) and val.lower() == symbol_lower:
                return True
        return False

    # حالت dict با کلید = symbol
    if isinstance(data, dict):
        if symbol_lower in data and isinstance(data[symbol_lower], dict):
            return data[symbol_lower]
        if symbol.upper() in data and isinstance(data[symbol.upper()], dict):
            return data[symbol.upper()]
        # ممکنه دیتای واقعی زیر یه کلید مثل "data" یا "result" باشه
        for key in ("data", "result", "items", "list"):
            if key in data:
                found = _find_item(data[key], symbol)
                if found:
                    return found
        # یا خود دیکشنری یک آیتم تکی باشه
        if matches(data):
            return data
        # یا هر مقدار دیگه‌ای که خودش دیکشنریه رو بگرد
        for v in data.values():
            if isinstance(v, (dict, list)):
                found = _find_item(v, symbol)
                if found:
                    return found

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and matches(item):
                return item

    return None


def _extract_price(item: dict):
    for key in ("price", "value", "sell", "rate", "buy"):
        if key in item and item[key] is not None:
            try:
                return float(str(item[key]).replace(",", ""))
            except ValueError:
                continue
    return None


def fetch_price(category: str, symbol: str):
    """قیمت یک نماد رو از API می‌گیره و به تومان برمی‌گردونه."""
    data = _fetch_category(category)
    item = _find_item(data, symbol)
    if not item:
        return None

    price_raw = _extract_price(item)
    if price_raw is None:
        return None

    # این سرویس قیمت رو مستقیماً به تومان برمی‌گردونه، نیازی به تبدیل نیست.
    return price_raw


def register_currency_handler(client):
    """این تابع رو با کلاینت Telethon خودت صدا بزن تا هندلر قیمت ارز فعال بشه."""

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*قیمت\s+(\S+)"))
    async def _currency_handler(event):
        raw = event.pattern_match.group(1).strip().lower()
        entry = SYMBOLS.get(raw)

        if not entry:
            await event.edit(
                f"❌ نماد «{raw}» شناخته‌شده نیست.\n"
                f"نمادهای مجاز: {', '.join(sorted(set(SYMBOLS.keys())))}"
            )
            return

        category, symbol = entry

        try:
            price = fetch_price(category, symbol)
        except Exception as e:
            await event.edit(f"⚠️ خطا در دریافت قیمت: {e}")
            return

        if price is None:
            await event.edit(f"❌ قیمتی برای {symbol} پیدا نشد.")
            return

        price_str = f"{price:,.0f}"
        await event.edit(f"💱 {symbol.upper()}: {price_str} تومان")

    return _currency_handler

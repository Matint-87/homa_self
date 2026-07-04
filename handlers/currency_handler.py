
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

⚡️ این نسخه از API سرویس BrsApi.ir استفاده می‌کنه (به‌جای AlanChand) چون:
    - کلید رایگان عمومی داره که تاریخ انقضا نداره (برخلاف توکن AlanChand
      که هر مدت باید از ربات تلگرامش دوباره گرفته می‌شد).
    - هم ارز فیات (دلار، یورو، درهم و...) هم رمزارز (بیتکوین، تتر و...)
      رو در یک endpoint واحد پوشش می‌ده.
    - سقف رایگانش تا ۱۵۰۰ درخواست در روز هست که برای این نوع استفاده کافیه.

قبل از استفاده:
    1) pip install requests

اگه بعداً خواستی، می‌تونی کلید اختصاصی خودت رو هم از سایت BrsApi.ir بگیری
و به‌جای BRSAPI_FREE_KEY پایین بذاری (مثلاً برای سقف درخواست بالاتر).

⚠️ نکته: چون مستندات دقیق ساختار JSON این سرویس در دسترس من نبود، پارسر
همون منطق هوشمند/بازگشتی قبلی رو حفظ کرده (دنبال کلیدهای symbol/price در
هر عمق از دیکشنری یا لیست می‌گرده). اگه اولین اجرا برات جواب نداد، خروجی
خام API (با پرینت `print(fetch_all_data())`) رو برام بفرست تا فیلدهای
دقیق رو تنظیم کنم.
"""

import requests
from telethon import events

# ---------------- تنظیمات ----------------
BRSAPI_FREE_KEY = "BtLUVy4dkU2ElbVviGKYuC6BwfQSuNjz"  # کلید عمومی رایگان BrsApi (بدون انقضا)
BRSAPI_BASE_URL = "https://BrsApi.ir/Api/Market/Gold_Currency.php"

# نگاشت نام فارسی به نماد مورد انتظار BrsApi
SYMBOLS = {
    # ارز فیات
    "دلار": "usd", "usd": "usd",
    "یورو": "eur", "eur": "eur",
    "پوند": "gbp", "gbp": "gbp",
    "درهم": "aed", "aed": "aed",
    "لیر": "try", "try": "try",
    "یوان": "cny", "cny": "cny",
    "ین": "jpy", "jpy": "jpy",
    "فرانک": "chf", "chf": "chf",
    "دلار_کانادا": "cad", "cad": "cad",
    "دلار_استرالیا": "aud", "aud": "aud",
    "ریال_سعودی": "sar", "sar": "sar",
    "دینار_کویت": "kwd", "kwd": "kwd",
    "روپیه": "inr", "inr": "inr",
    "روبل": "rub", "rub": "rub",
    # رمزارز
    "بیتکوین": "btc", "btc": "btc",
    "اتریوم": "eth", "eth": "eth",
    "تتر": "usdt", "usdt": "usdt",
    "بایننس": "bnb", "bnb": "bnb",
    "دوج": "doge", "doge": "doge",
    "ریپل": "xrp", "xrp": "xrp",
}

# کش ساده: کل پاسخ API فقط یک‌بار در بازه‌ی کش گرفته میشه (برخلاف قبل که
# هر category جدا کش می‌شد، چون BrsApi همه‌چیز رو در یک endpoint می‌ده)
_cache = {}


def fetch_all_data():
    """کل داده‌ی ارز/رمزارز/طلا رو از BrsApi می‌گیره (با کش ساده)."""
    if "all" in _cache:
        return _cache["all"]
    params = {"key": BRSAPI_FREE_KEY}
    resp = requests.get(BRSAPI_BASE_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    _cache["all"] = data
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

    if isinstance(data, dict):
        if symbol_lower in data and isinstance(data[symbol_lower], dict):
            return data[symbol_lower]
        if symbol.upper() in data and isinstance(data[symbol.upper()], dict):
            return data[symbol.upper()]
        for key in ("data", "result", "items", "list", "currency", "gold", "cryptocurrency", "crypto"):
            if key in data:
                found = _find_item(data[key], symbol)
                if found:
                    return found
        if matches(data):
            return data
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
    for key in ("price", "value", "sell", "rate", "buy", "price_toman"):
        if key in item and item[key] is not None:
            try:
                return float(str(item[key]).replace(",", ""))
            except ValueError:
                continue
    return None


def fetch_price(symbol: str):
    """قیمت یک نماد رو از API می‌گیره و به تومان برمی‌گردونه."""
    data = fetch_all_data()
    item = _find_item(data, symbol)
    if not item:
        return None

    price_raw = _extract_price(item)
    if price_raw is None:
        return None

    return price_raw


def register_currency_handler(client):
    """این تابع رو با کلاینت Telethon خودت صدا بزن تا هندلر قیمت ارز فعال بشه."""

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\*قیمت\s+(\S+)"))
    async def _currency_handler(event):
        raw = event.pattern_match.group(1).strip().lower()
        symbol = SYMBOLS.get(raw)

        if not symbol:
            await event.edit(
                f"❌ نماد «{raw}» شناخته‌شده نیست.\n"
                f"نمادهای مجاز: {', '.join(sorted(set(SYMBOLS.keys())))}"
            )
            return

        try:
            price = fetch_price(symbol)
        except Exception as e:
            await event.edit(f"⚠️ خطا در دریافت قیمت: {e}")
            return

        if price is None:
            await event.edit(f"❌ قیمتی برای {symbol} پیدا نشد.")
            return

        price_str = f"{price:,.0f}"
        await event.edit(f"💱 {symbol.upper()}: {price_str} تومان")

    return _currency_handler
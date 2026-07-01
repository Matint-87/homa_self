import asyncio
import aiohttp
import urllib.parse
from telethon import events

async def translate_text(text, target_lang):
    """اتصال به موتور ترجمه گوگل بدون نیاز به API Key"""
    # کدگذاری متن برای ارسال ایمن در URL
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={encoded_text}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=8) as response:
                if response.status == 200:
                    res_data = await response.json()
                    # استخراج و سرهم کردن متن ترجمه شده (پشتیبانی از متن‌های چند خطی)
                    translated_chunks = [str(item[0]) for item in res_data[0] if item[0]]
                    return "".join(translated_chunks)
    except Exception as e:
        print(f"Translate API Error: {e}")
    return None

def register_translate_handlers(client):
    """ثبت هندلرهای ترجمه پیام بر پایه ریپلای"""

    @client.on(events.NewMessage(pattern=r'^\*ترجمه\s+(.+)$'))
    async def reply_translator(event):
        # 🔐 فقط خودت بتوانی دستور ترجمه را صادر کنی
        if not event.out:
            return

        # بررسی اینکه آیا پیام روی پیام دیگری ریپلای شده است یا خیر
        if not event.is_reply:
            await event.edit("⚠️ **خطا:** لطفاً این دستور را روی یک پیام متنی ریپلای کنید!")
            return

        # گرفتن زبانی که کاربر خواسته (مثلاً: فارسی، انگلیسی، فرانسوی)
        lang_input = event.pattern_match.group(1).strip()

        # نقشه‌برداری زبان‌های مختلف به کدهای استاندارد بین‌المللی (ISO)
        languages = {
            "فارسی": "fa",
            "انگلیسی": "en",
            "عربی": "ar",
            "فرانسوی": "fr",
            "آلمانی": "de",
            "ترکی": "tr",
            "روسی": "ru",
            "اسپانیایی": "es",
            "ایتالیایی": "it",
            "چینی": "zh",
            "ژاپنی": "ja",
            "کره‌ای": "ko",
            "کردی": "ku",
            "پشتو": "ps"
        }

        # اگر زبان در لیست بالا نبود، فرض می‌کنیم کاربر خودش کد زبان را فرستاده (مثل en یا fa)
        target_code = languages.get(lang_input, lang_input)

        msg = await event.edit("🔄 **در حال ترجمه متن...**")

        try:
            # گرفتن اطلاعات پیامی که روی آن ریپلای شده
            reply_msg = await event.get_reply_message()
            
            if not reply_msg or not reply_msg.text:
                await msg.edit("❌ **خطا:** پیام ریپلای شده حاوی متن نیست!")
                return

            # ارسال متن پیام اصلی به موتور ترجمه
            result = await translate_text(reply_msg.text, target_code)

            if not result:
                await msg.edit("❌ **خطا:** ارتباط با سرور ترجمه برقرار نشد.")
                return

            # ساخت ظاهر خروجی شیک سلف‌بات
            text = (
                "🌐 **مترجم هوشمند سلف‌بات**\n"
                "════════════════════\n"
                f"{result}\n"
                "════════════════════\n"
                f" ترجمه شده به: `{lang_input}`"
            )
            
            await msg.edit(text)

        except Exception as e:
            print(f"Translation Handler Error: {e}")
            await msg.edit("❌ **خطا:** مشکلی در پردازش ترجمه به وجود آمد.")
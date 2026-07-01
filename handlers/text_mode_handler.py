import asyncio
from telethon import events
from config import supabase  # اتصال به سوپابیس شما

# =====================================================================
# 🗄️ بخش اول: توابع دیتابیس (Supabase)
# =====================================================================

def get_user_text_mode(user_id: int) -> str:
    """دریافت مود فعلی متن کاربر از دیتابیس"""
    try:
        res = supabase.table("user_text_modes").select("mode").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]["mode"]
    except Exception as e:
        print(f"❌ Error fetching text mode: {e}")
    return "none"

def set_user_text_mode(user_id: int, mode: str):
    """ذخیره یا آپدیت مود متن کاربر در دیتابیس"""
    try:
        supabase.table("user_text_modes").upsert({"user_id": user_id, "mode": mode}).execute()
    except Exception as e:
        print(f"❌ Error saving text mode: {e}")


# =====================================================================
# ✍️ بخش دوم: موتور اصلی اعمال فونت و افکت تایپ انیمیشنی
# =====================================================================
def register_auto_font_engine(bot):
    """شنود پیام‌های خروجی کلاینت و اعمال خودکار فونت و افکت‌های پیشرفته"""
    
    @bot.on(events.NewMessage(outgoing=True))
    async def auto_font_formatter(event):
        # نادیده گرفتن دستورات متنی خود ربات که با ستاره شروع می‌شوند
        if event.text and event.text.startswith('*'):
            return
            
        if not hasattr(event.client, '_cached_my_id') or event.client._cached_my_id is None:
            me = await event.client.get_me()
            event.client._cached_my_id = me.id
        owner_id = event.client._cached_my_id
        
        mode = get_user_text_mode(owner_id)
        if mode == "none" or not event.text:
            return
            
        raw_text = event.text
        
        # -------------------------------------------------------------
        # 🌊 حالت اول: افکت تدریجی (تایپ انیمیشنی کلمه به کلمه با مکان‌نما)
        # -------------------------------------------------------------
        if mode == "gradient":
            words = raw_text.split()
            if len(words) <= 1:
                return # اگر فقط یک کلمه بود نیازی به افکت نیست
                
            current_text = ""
            for i, word in enumerate(words):
                current_text += (word + " ")
                if i == 0:
                    continue # کلمه اول نیاز به ادیت ندارد چون تازه فرستاده شده
                
                try:
                    # اضافه کردن کلمه جدید به همراه نشانگر چشمک‌زن تایپ |
                    await event.edit(current_text.strip() + " |")
                    await asyncio.sleep(0.2) # سرعت تایپ شدن کلمات
                except Exception:
                    pass # جلوگیری از پرتاب خطای Message Not Modified هنگام تکرار کلمات
            
            # در نهایت پیام اصلی بدون نشانگر، ثبت نهایی و ثابت می‌شود
            try:
                await event.edit(raw_text)
            except Exception:
                pass
            return
        
# -------------------------------------------------------------
        # 📚 حالت دوم: استایل‌های متنی (حل مشکل ادیت نشدن اسپویلر)
        # -------------------------------------------------------------
        formatted_text = raw_text
        parse_mode = "markdown" 
        msg_entities = None # متغیری برای ذخیره انتیتی‌های دستی
        
        if mode == "bold":
            formatted_text = f"**{raw_text}**"
            
        elif mode == "italic":
            formatted_text = f"<i>{raw_text}</i>"
            parse_mode = "html"
            
        elif mode == "strike":
            formatted_text = f"~~{raw_text}~~"
            
        elif mode == "mono":
            formatted_text = f"`{raw_text}`"
            
        elif mode == "underline":
            formatted_text = f"<u>{raw_text}</u>"
            parse_mode = "html"
            
        elif mode == "spoiler":
            # 🔥 روش قطعی تلثون: تزریق مستقیم انتیتی اسپویلر به جای تگ متنی
            from telethon.tl.types import MessageEntitySpoiler
            formatted_text = raw_text  # متن به صورت خام فرستاده می‌شود
            parse_mode = None          # پارسر را خاموش می‌کنیم
            # اعمال افکت اسپویلر از کاراکتر اول (0) تا انتهای طول متن
            msg_entities = [MessageEntitySpoiler(offset=0, length=len(raw_text))]
            
        elif mode == "quote":
            formatted_text = f"<blockquote>{raw_text}</blockquote>"
            parse_mode = "html"

        # اعمال ادیت روی چت
        try:
            if mode == "spoiler":
                # ارسال متن خام همراه با لایه انتیتی اسپویلر
                await event.edit(formatted_text, formatting_entities=msg_entities)
            elif event.text != formatted_text: 
                await event.edit(formatted_text, parse_mode=parse_mode)
        except Exception as e:
            if "not modified" in str(e).lower():
                pass
            else:
                print(f"❌ خطای اعمال فونت خودکار: {e}")
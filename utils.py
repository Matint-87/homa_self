import config
import asyncio
from config import supabase

# 🧠 سیستم کشینگ فوق‌سریع در حافظه برای جلوگیری از نابودی دیتابیس زیر بار ۸۰۰۰ کاربر
CACHE_USER_LOCKS = {}
CACHE_AUTO_REPLY = {}
CACHE_FILTERS = {}
CACHE_MUTED_USERS = {}
CACHE_CHAT_GUARD = {}

# --- 🔥 توابع مدیریت موجودی طلا (ایمن در برابر Race Condition) ---

def get_balance(user_id):
    """دریافت تعداد طلاهای کاربر از دیتابیس سوپابیس"""
    try:
        response = supabase.table("users_diamonds").select("diamonds").eq("user_id", int(user_id)).execute()
        if response.data:
            return response.data[0]["diamonds"]
        
        # ثبت کاربر جدید در صورت عدم وجود
        supabase.table("users_diamonds").insert({"user_id": int(user_id), "diamonds": 0}).execute()
        return 0
    except Exception as e:
        print(f"⚠️ خطا در دریافت طلا از سوپابیس: {e}")
        return 0

def update_balance(user_id, amount):
    """کم یا زیاد کردن طلاها به صورت اتمیک بدون باگ دبل‌کلیک"""
    try:
        current_bal = get_balance(user_id)
        new_bal = current_bal + amount
        
        if new_bal < 0:
            return False  # موجودی نمی‌تواند منفی شود
            
        # آپدیت مستقیم مقدار نهایی محاسبه شده
        supabase.table("users_diamonds").update({"diamonds": new_bal}).eq("user_id", int(user_id)).execute()
        return True
    except Exception as e:
        print(f"⚠️ خطا در آپدیت طلا در سوپابیس: {e}")
        return False

# --- 🎮 توابع مدیریت بازی‌ها در Supabase ---

def save_game(game_id, game_data):
    """ذخیره یا آپدیت اطلاعات یک بازی مشخص با متد upsert"""
    try:
        supabase.table("active_games").upsert({
            "game_id": str(game_id),
            "game_data": game_data
        }).execute()
    except Exception as e:
        print(f"⚠️ خطا در ذخیره بازی در سوپابیس: {e}")

def get_game(game_id):
    """گرفتن اطلاعات یک بازی مشخص از دیتابیس"""
    try:
        response = supabase.table("active_games").select("game_data").eq("game_id", str(game_id)).execute()
        if response.data:
            return response.data[0]["game_data"]
        return None
    except Exception as e:
        print(f"⚠️ خطا در دریافت اطلاعات بازی از سوپابیس: {e}")
        return None

def delete_game(game_id):
    """حذف بازی بعد از اتمام یا لغو شدن از دیتابیس"""
    try:
        supabase.table("active_games").delete().eq("game_id", str(game_id)).execute()
    except Exception as e:
        print(f"⚠️ خطا در حذف بازی از سوپابیس: {e}")

# --- 🤫 توابع مدیریت لیست سکوت (دارای سیستم کشینگ مچ شده) ---

def get_muted_users_from_db(owner_id):
    """دریافت لیست آیدی‌های سکوت شده با اولویت کش حافظه"""
    owner_id = int(owner_id)
    if owner_id in CACHE_MUTED_USERS:
        return CACHE_MUTED_USERS[owner_id]
        
    try:
        response = supabase.table("muted_users").select("muted_id").eq("owner_id", owner_id).execute()
        muted_list = [row["muted_id"] for row in response.data] if response.data else []
        CACHE_MUTED_USERS[owner_id] = muted_list
        return muted_list
    except Exception as e:
        print(f"⚠️ خطا در دریافت لیست سکوت از سوپابیس: {e}")
        return CACHE_MUTED_USERS.get(owner_id, [])

def add_muted_user_to_db(owner_id, muted_id):
    """افزودن کاربر به لیست سکوت دیتابیس و به‌روزرسانی آنی کش"""
    owner_id = int(owner_id)
    muted_id = int(muted_id)
    try:
        supabase.table("muted_users").upsert({"owner_id": owner_id, "muted_id": muted_id}).execute()
        if owner_id in CACHE_MUTED_USERS:
            if muted_id not in CACHE_MUTED_USERS[owner_id]:
                CACHE_MUTED_USERS[owner_id].append(muted_id)
        else:
            CACHE_MUTED_USERS[owner_id] = [muted_id]
        return True
    except Exception as e:
        print(f"⚠️ خطا در افزودن به لیست سکوت سوپابیس: {e}")
        return False

def remove_muted_user_from_db(owner_id, muted_id):
    """حذف کاربر از لیست سکوت دیتابیس و حذف از کش حافظه"""
    owner_id = int(owner_id)
    muted_id = int(muted_id)
    try:
        supabase.table("muted_users").delete().eq("owner_id", owner_id).eq("muted_id", muted_id).execute()
        if owner_id in CACHE_MUTED_USERS and muted_id in CACHE_MUTED_USERS[owner_id]:
            CACHE_MUTED_USERS[owner_id].remove(muted_id)
        return True
    except Exception as e:
        print(f"⚠️ خطا در حذف از لیست سکوت سوپابیس: {e}")
        return False

# --- 🔒 توابع مدیریت قفل‌های کاربری (بهینه‌سازی شده با لایه مانیتورینگ حافظه) ---

def get_user_locks_from_db(user_id):
    """دریافت وضعیت قفل‌ها بدون درگیر کردن دیتابیس برای هر پیام"""
    user_id = int(user_id)
    if user_id in CACHE_USER_LOCKS:
        return CACHE_USER_LOCKS[user_id]

    default_locks = {
        "user_id": user_id, "username": False, "link": False, "reply": False, 
        "photo": False, "gif": False, "sticker": False, "pv": False, "forward": False
    }
    try:
        response = supabase.table("user_locks").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            CACHE_USER_LOCKS[user_id] = response.data[0]
            return response.data[0]
            
        supabase.table("user_locks").insert({"user_id": user_id}).execute()
        CACHE_USER_LOCKS[user_id] = default_locks
        return default_locks
    except Exception as e:
        print(f"⚠️ خطا در دریافت قفل‌ها از سوپابیس برای {user_id}: {e}")
        return default_locks

def save_user_lock_to_db(user_id, lock_key, value):
    """تغییر وضعیت قفل در دیتابیس و اِعمال آنی روی لایه کش سیستم"""
    user_id = int(user_id)
    try:
        supabase.table("user_locks").upsert({"user_id": user_id, lock_key: bool(value)}).execute()
        if user_id in CACHE_USER_LOCKS:
            CACHE_USER_LOCKS[user_id][lock_key] = bool(value)
        else:
            get_user_locks_from_db(user_id) # لود اولیه کش
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره قفل در سوپابیس: {e}")
        return False

# --- 🤖 تنظیمات منشی خودکار (Auto Reply System) ---

def get_auto_reply_from_db(user_id):
    user_id = int(user_id)
    if user_id in CACHE_AUTO_REPLY:
        return CACHE_AUTO_REPLY[user_id]

    default_config = {
        "user_id": user_id, "enabled": False, "message": "🚫 الان آنلاین نیستم، بعداً پیام میدم!",
        "interval": 30, "mode": "once"
    }
    try:
        response = supabase.table("user_auto_reply").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            CACHE_AUTO_REPLY[user_id] = response.data[0]
            return response.data[0]
        
        supabase.table("user_auto_reply").insert({"user_id": user_id}).execute()
        CACHE_AUTO_REPLY[user_id] = default_config
        return default_config
    except Exception as e:
        print(f"⚠️ خطا در دریافت تنظیمات منشی از سوپابیس برای {user_id}: {e}")
        return default_config

def save_auto_reply_to_db(user_id, update_data):
    user_id = int(user_id)
    try:
        update_data["user_id"] = user_id
        supabase.table("user_auto_reply").upsert(update_data).execute()
        
        if user_id in CACHE_AUTO_REPLY:
            CACHE_AUTO_REPLY[user_id].update(update_data)
        else:
            CACHE_AUTO_REPLY[user_id] = update_data
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره تنظیمات منشی در سوپابیس: {e}")
        return False

# --- 📑 توابع فیلترینگ کلمات و متون چت ---

def get_user_filters_from_db(user_id):
    user_id = int(user_id)
    if user_id in CACHE_FILTERS:
        return CACHE_FILTERS[user_id]

    default_data = {"user_id": user_id, "enabled": False, "words": []}
    try:
        response = supabase.table("user_filters").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            data = response.data[0]
            if data.get("words") is None:
                data["words"] = []
            CACHE_FILTERS[user_id] = data
            return data
        
        supabase.table("user_filters").insert({"user_id": user_id}).execute()
        CACHE_FILTERS[user_id] = default_data
        return default_data
    except Exception as e:
        print(f"⚠️ خطا در دریافت فیلترها از سوپابیس برای {user_id}: {e}")
        return default_data

def save_user_filters_to_db(user_id, update_data):
    user_id = int(user_id)
    try:
        update_data["user_id"] = user_id
        supabase.table("user_filters").upsert(update_data).execute()
        
        if user_id in CACHE_FILTERS:
            CACHE_FILTERS[user_id].update(update_data)
        else:
            CACHE_FILTERS[user_id] = update_data
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره فیلترها در سوپابیس: {e}")
        return False

# --- 🛡️ سیستم نگهبان چت (Chat Guard) ---

def get_chat_guard_from_db(owner_id: int):
    owner_id = int(owner_id)
    if owner_id in CACHE_CHAT_GUARD:
        return CACHE_CHAT_GUARD[owner_id]

    try:
        res = supabase.table("chat_guard").select("*").eq("user_id", owner_id).execute()
        if res and res.data:
            CACHE_CHAT_GUARD[owner_id] = res.data[0]
            return res.data[0]
    except Exception as e:
        print(f"⚠️ خطا در خواندن نگهبان چت: {e}")
        
    return {"save_deleted": False, "save_edited": False, "save_ttl": False}

def save_chat_guard_to_db(owner_id: int, update_data: dict):
    owner_id = int(owner_id)
    try:
        res = supabase.table("chat_guard").select("user_id").eq("user_id", owner_id).execute()
        if not res.data:
            supabase.table("chat_guard").insert({"user_id": owner_id}).execute()
        
        supabase.table("chat_guard").update(update_data).eq("user_id", owner_id).execute()
        
        if owner_id in CACHE_CHAT_GUARD:
            CACHE_CHAT_GUARD[owner_id].update(update_data)
        else:
            CACHE_CHAT_GUARD[owner_id] = update_data
        return True
    except Exception as e:
        print(f"⚠️ خطا در آپدیت نگهبان چت: {e}")
        return False

# --- 👀 سیستم سین خودکار چت‌ها (Auto Seen Engine) ---

def get_auto_seen_from_db(owner_id: int) -> dict:
    try:
        response = supabase.table("auto_seen_settings").select("*").eq("user_id", int(owner_id)).execute()
        if response.data:
            return response.data[0]
        return {"user_id": owner_id, "auto_seen": True}
    except Exception as e:
        print(f"Error fetching auto seen: {e}")
        return {"user_id": owner_id, "auto_seen": True}

def save_auto_seen_to_db(owner_id: int, status: bool):
    try:
        data = {"user_id": int(owner_id), "auto_seen": status, "updated_at": "now()"}
        supabase.table("auto_seen_settings").upsert(data).execute()
        return True
    except Exception as e:
        print(f"Error saving auto seen: {e}")
        return False
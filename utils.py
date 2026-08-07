import asyncio
import json
import asyncpg
from cachetools import TTLCache
from config import DB_CONFIG

# ============================================================================
# ⚙️ اتصال به Postgres خودت (روی VPS) با Connection Pool واقعی asyncpg
# دیگه نیازی به ThreadPoolExecutor نیست — چون قبلاً کلاینت Supabase
# سینکرون (blocking) بود و مجبور بودیم اجراش رو با run_in_executor به
# ترد جدا بفرستیم. asyncpg خودش native async هست و مستقیم روی event loop
# کار می‌کنه، پس اون لایه‌ی execute تو ترد جدا کاملاً حذف شد.
#
# min_size/max_size همون چیزیه که تو DB_CONFIG فرستادی؛ یعنی حداقل و
# حداکثر تعداد کانکشن‌های زنده به دیتابیس در Pool. با چند هزار کاربر
# همزمان همین Pool (نه یک کانکشن تکی) کل بار رو مدیریت می‌کنه.
# ============================================================================
_pool: asyncpg.Pool | None = None


async def init_db_pool():
    """این تابع رو یک‌بار موقع بالا اومدن ربات (قبل از start شدن کلاینت‌ها) صدا بزن."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(**DB_CONFIG)
    return _pool


async def close_db_pool():
    """موقع خاموش کردن تمیز ربات (graceful shutdown) صدا بزن."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """
    دسترسی سریع به Pool در همه‌جای پروژه.
    اگه init_db_pool() قبلش صدا زده نشده باشه، خطای واضح میده به‌جای کرش خاموش.
    """
    if _pool is None:
        raise RuntimeError(
            "دیتابیس هنوز وصل نشده — باید await init_db_pool() رو موقع استارت ربات صدا بزنی."
        )
    return _pool


async def _upsert_dynamic(table: str, key_col: str, key_val, data: dict):
    """
    هلپر عمومی برای UPSERT با ستون‌های دینامیک (به‌جای تکرار کد upsert
    تو هر تابع). نام ستون‌ها همیشه از دیکشنری‌های ثابت داخل خود پروژه
    میان (نه مستقیم از ورودی کاربر تلگرام)، پس امن هست که تو query
    interpolate بشن؛ مقادیر همیشه با پارامتر ($1, $2, ...) پاس داده میشن.
    """
    columns = list(data.keys())
    values = [key_val] + [data[c] for c in columns]
    col_list = ", ".join([key_col] + columns)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))
    update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns)
    query = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT ({key_col}) DO UPDATE SET {update_set}"
    )
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(query, *values)


# ============================================================================
# 🧠 کش‌های محدود با TTL — بدون تغییر نسبت به قبل
# ============================================================================
CACHE_USER_LOCKS = TTLCache(maxsize=20000, ttl=1800)
CACHE_AUTO_REPLY = TTLCache(maxsize=20000, ttl=1800)
CACHE_FILTERS = TTLCache(maxsize=20000, ttl=1800)
CACHE_MUTED_USERS = TTLCache(maxsize=20000, ttl=1800)
CACHE_CHAT_GUARD = TTLCache(maxsize=20000, ttl=1800)


# --- 🔥 توابع مدیریت موجودی طلا (اتمیک و ایمن دربرابر Race Condition واقعی) ---
#
# مهم: این بخش نیاز به یک تابع Postgres داره تا افزایش/کاهش موجودی
# به‌صورت اتمیک در خود دیتابیس انجام بشه (نه با read-then-write در پایتون).
# این SQL رو یک‌بار روی Postgres خودت (با psql یا هر کلاینتی) اجرا کن:
#
# CREATE TABLE IF NOT EXISTS users_diamonds (
#     user_id BIGINT PRIMARY KEY,
#     diamonds BIGINT NOT NULL DEFAULT 0
# );
#
# CREATE OR REPLACE FUNCTION increment_diamonds(p_user_id BIGINT, p_amount BIGINT)
# RETURNS BIGINT
# LANGUAGE plpgsql
# AS $$
# DECLARE
#     new_balance BIGINT;
# BEGIN
#     INSERT INTO users_diamonds (user_id, diamonds)
#     VALUES (p_user_id, GREATEST(p_amount, 0))
#     ON CONFLICT (user_id) DO UPDATE
#         SET diamonds = users_diamonds.diamonds + p_amount
#     RETURNING diamonds INTO new_balance;
#
#     IF new_balance < 0 THEN
#         RAISE EXCEPTION 'insufficient_balance';
#     END IF;
#
#     RETURN new_balance;
# END;
# $$;
#
# نکته: نسخه‌ی قبلی روی Supabase یه باگ pseudo داشت (excluded_amount که
# اصلاً وجود نداره) — اینجا درستش کردم و مستقیم از p_amount استفاده شده.

async def get_balance(user_id):
    """دریافت تعداد طلاهای کاربر از دیتابیس"""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT diamonds FROM users_diamonds WHERE user_id = $1", int(user_id)
            )
            if row:
                return row["diamonds"]

            await conn.execute(
                "INSERT INTO users_diamonds (user_id, diamonds) VALUES ($1, 0) "
                "ON CONFLICT (user_id) DO NOTHING",
                int(user_id),
            )
            return 0
    except Exception as e:
        print(f"⚠️ خطا در دریافت طلا از دیتابیس: {e}")
        return 0


async def update_balance(user_id, amount):
    """کم یا زیاد کردن طلاها به صورت اتمیک واقعی (روی سرور دیتابیس، نه در پایتون)"""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval(
                "SELECT increment_diamonds($1, $2)", int(user_id), int(amount)
            )
            return True
    except asyncpg.PostgresError as e:
        # اگه تابع increment_diamonds موجودی منفی رو رد کنه (RAISE EXCEPTION 'insufficient_balance')
        if "insufficient_balance" in str(e):
            return False
        print(f"⚠️ خطا در آپدیت طلا در دیتابیس: {e}")
        return False
    except Exception as e:
        print(f"⚠️ خطا در آپدیت طلا در دیتابیس: {e}")
        return False


# --- 🎮 توابع مدیریت بازی‌ها ---

async def save_game(game_id, game_data):
    """ذخیره یا آپدیت اطلاعات یک بازی مشخص (upsert)"""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO active_games (game_id, game_data) VALUES ($1, $2::jsonb) "
                "ON CONFLICT (game_id) DO UPDATE SET game_data = EXCLUDED.game_data",
                str(game_id),
                json.dumps(game_data),
            )
    except Exception as e:
        print(f"⚠️ خطا در ذخیره بازی در دیتابیس: {e}")


async def get_game(game_id):
    """گرفتن اطلاعات یک بازی مشخص از دیتابیس"""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT game_data FROM active_games WHERE game_id = $1", str(game_id)
            )
            if row and row["game_data"] is not None:
                return json.loads(row["game_data"])
            return None
    except Exception as e:
        print(f"⚠️ خطا در دریافت اطلاعات بازی از دیتابیس: {e}")
        return None


async def delete_game(game_id):
    """حذف بازی بعد از اتمام یا لغو شدن از دیتابیس"""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM active_games WHERE game_id = $1", str(game_id)
            )
    except Exception as e:
        print(f"⚠️ خطا در حذف بازی از دیتابیس: {e}")


# --- 🤫 توابع مدیریت لیست سکوت (دارای سیستم کشینگ TTL) ---
# نکته: جدول muted_users باید UNIQUE (owner_id, muted_id) داشته باشه تا ON CONFLICT کار کنه:
# CREATE TABLE IF NOT EXISTS muted_users (
#     owner_id BIGINT NOT NULL,
#     muted_id BIGINT NOT NULL,
#     UNIQUE (owner_id, muted_id)
# );

async def get_muted_users_from_db(owner_id):
    """دریافت لیست آیدی‌های سکوت شده با اولویت کش حافظه"""
    owner_id = int(owner_id)
    if owner_id in CACHE_MUTED_USERS:
        return CACHE_MUTED_USERS[owner_id]

    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT muted_id FROM muted_users WHERE owner_id = $1", owner_id
            )
            muted_list = [r["muted_id"] for r in rows]
            CACHE_MUTED_USERS[owner_id] = muted_list
            return muted_list
    except Exception as e:
        print(f"⚠️ خطا در دریافت لیست سکوت از دیتابیس: {e}")
        return CACHE_MUTED_USERS.get(owner_id, [])


async def add_muted_user_to_db(owner_id, muted_id):
    """افزودن کاربر به لیست سکوت دیتابیس و به‌روزرسانی آنی کش"""
    owner_id = int(owner_id)
    muted_id = int(muted_id)
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO muted_users (owner_id, muted_id) VALUES ($1, $2) "
                "ON CONFLICT (owner_id, muted_id) DO NOTHING",
                owner_id,
                muted_id,
            )
        if owner_id in CACHE_MUTED_USERS:
            if muted_id not in CACHE_MUTED_USERS[owner_id]:
                CACHE_MUTED_USERS[owner_id].append(muted_id)
        else:
            CACHE_MUTED_USERS[owner_id] = [muted_id]
        return True
    except Exception as e:
        print(f"⚠️ خطا در افزودن به لیست سکوت: {e}")
        return False


async def remove_muted_user_from_db(owner_id, muted_id):
    """حذف کاربر از لیست سکوت دیتابیس و حذف از کش حافظه"""
    owner_id = int(owner_id)
    muted_id = int(muted_id)
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM muted_users WHERE owner_id = $1 AND muted_id = $2",
                owner_id,
                muted_id,
            )
        if owner_id in CACHE_MUTED_USERS and muted_id in CACHE_MUTED_USERS[owner_id]:
            CACHE_MUTED_USERS[owner_id].remove(muted_id)
        return True
    except Exception as e:
        print(f"⚠️ خطا در حذف از لیست سکوت: {e}")
        return False


# --- 🔒 توابع مدیریت قفل‌های کاربری ---
ALLOWED_LOCK_KEYS = {
    "username", "link", "reply", "photo", "gif", "sticker", "pv", "forward"
}


async def get_user_locks_from_db(user_id):
    """دریافت وضعیت قفل‌ها بدون درگیر کردن دیتابیس برای هر پیام"""
    user_id = int(user_id)
    if user_id in CACHE_USER_LOCKS:
        return CACHE_USER_LOCKS[user_id]

    default_locks = {
        "user_id": user_id, "username": False, "link": False, "reply": False,
        "photo": False, "gif": False, "sticker": False, "pv": False, "forward": False
    }
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_locks WHERE user_id = $1", user_id
            )
            if row:
                data = dict(row)
                CACHE_USER_LOCKS[user_id] = data
                return data

            await conn.execute(
                "INSERT INTO user_locks (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                user_id,
            )
            CACHE_USER_LOCKS[user_id] = default_locks
            return default_locks
    except Exception as e:
        print(f"⚠️ خطا در دریافت قفل‌ها از دیتابیس برای {user_id}: {e}")
        return default_locks


async def save_user_lock_to_db(user_id, lock_key, value):
    """تغییر وضعیت قفل در دیتابیس و اِعمال آنی روی لایه کش سیستم"""
    user_id = int(user_id)
    if lock_key not in ALLOWED_LOCK_KEYS:
        print(f"⚠️ نام قفل نامعتبر رد شد: {lock_key}")
        return False
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            query = (
                f"INSERT INTO user_locks (user_id, {lock_key}) VALUES ($1, $2) "
                f"ON CONFLICT (user_id) DO UPDATE SET {lock_key} = EXCLUDED.{lock_key}"
            )
            await conn.execute(query, user_id, bool(value))
        if user_id in CACHE_USER_LOCKS:
            CACHE_USER_LOCKS[user_id][lock_key] = bool(value)
        else:
            await get_user_locks_from_db(user_id)  # لود اولیه کش
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره قفل در دیتابیس: {e}")
        return False


# --- 🤖 تنظیمات منشی خودکار (Auto Reply System) ---

async def get_auto_reply_from_db(user_id):
    user_id = int(user_id)
    if user_id in CACHE_AUTO_REPLY:
        return CACHE_AUTO_REPLY[user_id]

    default_config = {
        "user_id": user_id, "enabled": False, "message": "🚫 الان آنلاین نیستم، بعداً پیام میدم!",
        "interval": 30, "mode": "once"
    }
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_auto_reply WHERE user_id = $1", user_id
            )
            if row:
                data = dict(row)
                CACHE_AUTO_REPLY[user_id] = data
                return data

            await conn.execute(
                "INSERT INTO user_auto_reply (user_id, enabled, message, interval, mode) "
                "VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id) DO NOTHING",
                user_id, default_config["enabled"], default_config["message"],
                default_config["interval"], default_config["mode"],
            )
            CACHE_AUTO_REPLY[user_id] = default_config
            return default_config
    except Exception as e:
        print(f"⚠️ خطا در دریافت تنظیمات منشی از دیتابیس برای {user_id}: {e}")
        return default_config


async def save_auto_reply_to_db(user_id, update_data):
    user_id = int(user_id)
    try:
        data = dict(update_data)
        data.pop("user_id", None)
        await _upsert_dynamic("user_auto_reply", "user_id", user_id, data)

        if user_id in CACHE_AUTO_REPLY:
            CACHE_AUTO_REPLY[user_id].update(data)
        else:
            CACHE_AUTO_REPLY[user_id] = {"user_id": user_id, **data}
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره تنظیمات منشی در دیتابیس: {e}")
        return False


# --- 📑 توابع فیلترینگ کلمات و متون چت ---
# نکته: ستون words رو jsonb تعریف کن (لیست رشته‌ها).

async def get_user_filters_from_db(user_id):
    user_id = int(user_id)
    if user_id in CACHE_FILTERS:
        return CACHE_FILTERS[user_id]

    default_data = {"user_id": user_id, "enabled": False, "words": []}
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_filters WHERE user_id = $1", user_id
            )
            if row:
                data = dict(row)
                if data.get("words") is None:
                    data["words"] = []
                elif isinstance(data["words"], str):
                    data["words"] = json.loads(data["words"])
                CACHE_FILTERS[user_id] = data
                return data

            await conn.execute(
                "INSERT INTO user_filters (user_id, enabled, words) VALUES ($1, $2, $3::jsonb) "
                "ON CONFLICT (user_id) DO NOTHING",
                user_id, False, json.dumps([]),
            )
            CACHE_FILTERS[user_id] = default_data
            return default_data
    except Exception as e:
        print(f"⚠️ خطا در دریافت فیلترها از دیتابیس برای {user_id}: {e}")
        return default_data


async def save_user_filters_to_db(user_id, update_data):
    user_id = int(user_id)
    try:
        data = dict(update_data)
        data.pop("user_id", None)
        if "words" in data:
            data["words"] = json.dumps(data["words"])

        pool = get_pool()
        async with pool.acquire() as conn:
            columns = list(data.keys())
            values = [user_id] + [data[c] for c in columns]
            col_list = ", ".join(["user_id"] + columns)
            placeholders_parts = []
            for i, c in enumerate(columns, start=2):
                placeholders_parts.append(f"${i}::jsonb" if c == "words" else f"${i}")
            placeholders = ", ".join(["$1"] + placeholders_parts)
            update_set = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns)
            query = (
                f"INSERT INTO user_filters ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT (user_id) DO UPDATE SET {update_set}"
            )
            await conn.execute(query, *values)

        if "words" in update_data:
            data["words"] = update_data["words"]  # نسخه‌ی پارس‌شده برای کش، نه رشته‌ی jsonb
        if user_id in CACHE_FILTERS:
            CACHE_FILTERS[user_id].update({**update_data})
        else:
            CACHE_FILTERS[user_id] = {"user_id": user_id, **update_data}
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره فیلترها در دیتابیس: {e}")
        return False


# --- 🛡️ سیستم نگهبان چت (Chat Guard) ---

async def get_chat_guard_from_db(owner_id: int):
    owner_id = int(owner_id)
    if owner_id in CACHE_CHAT_GUARD:
        return CACHE_CHAT_GUARD[owner_id]

    default_data = {"user_id": owner_id, "save_deleted": False, "save_edited": False, "save_ttl": False}
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM chat_guard WHERE user_id = $1", owner_id
            )
            if row:
                data = dict(row)
                CACHE_CHAT_GUARD[owner_id] = data
                return data
    except Exception as e:
        print(f"⚠️ خطا در خواندن نگهبان چت: {e}")

    # همون shape پیش‌فرض رو کش می‌کنیم تا سازگار بمونه
    CACHE_CHAT_GUARD[owner_id] = default_data
    return default_data


async def save_chat_guard_to_db(owner_id: int, update_data: dict):
    owner_id = int(owner_id)
    try:
        data = dict(update_data)
        data.pop("user_id", None)
        await _upsert_dynamic("chat_guard", "user_id", owner_id, data)

        if owner_id in CACHE_CHAT_GUARD:
            CACHE_CHAT_GUARD[owner_id].update(data)
        else:
            CACHE_CHAT_GUARD[owner_id] = {"user_id": owner_id, **data}
        return True
    except Exception as e:
        print(f"⚠️ خطا در آپدیت نگهبان چت: {e}")
        return False


# --- 👀 سیستم سین خودکار چت‌ها (Auto Seen Engine) ---

async def get_auto_seen_from_db(owner_id: int) -> dict:
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM auto_seen_settings WHERE user_id = $1", int(owner_id)
            )
            if row:
                return dict(row)
            return {"user_id": owner_id, "auto_seen": False}
    except Exception as e:
        print(f"Error fetching auto seen: {e}")
        return {"user_id": owner_id, "auto_seen": False}


async def save_auto_seen_to_db(owner_id: int, status: bool):
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO auto_seen_settings (user_id, auto_seen, updated_at) "
                "VALUES ($1, $2, now()) "
                "ON CONFLICT (user_id) DO UPDATE SET auto_seen = EXCLUDED.auto_seen, updated_at = now()",
                int(owner_id), status,
            )
        return True
    except Exception as e:
        print(f"Error saving auto seen: {e}")
        return False
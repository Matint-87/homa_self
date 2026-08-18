from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from telegram.error import BadRequest
from utils import get_pool  # دسترسی به asyncpg pool مشترک پروژه

# ============== توابع دیتابیس مربوط به طلا ==============

async def get_user_diamonds(user_id: int) -> int:
    try:
        pool = get_pool()
        value = await pool.fetchval(
            "SELECT diamonds FROM users_diamonds WHERE user_id = $1", user_id
        )
        return value or 0
    except Exception as e:
        print(f"Error getting diamonds for {user_id}: {e}")
        return 0


async def update_diamonds(user_id: int, amount: int):
    """
    ✅ نسخه اتمیک: مستقیماً یک دستور UPDATE اتمیک روی Postgres اجرا می‌شود
    (diamonds = diamonds + amount) که خودِ دیتابیس این عملیات را به‌صورت
    یکپارچه و بدون overwrite شدن توسط عملیات همزمان انجام می‌دهد.
    """
    try:
        pool = get_pool()
        await pool.execute(
            "UPDATE users_diamonds SET diamonds = diamonds + $1 WHERE user_id = $2",
            amount, user_id,
        )
    except Exception as e:
        print(f"Error updating diamonds for {user_id}: {e}")


# ============== توابع دیتابیس مربوط به لول ==============
# نکته مهم: این توابع به فیلد "level" روی جدول users_diamonds نیاز دارند.
# اگه این فیلد رو هنوز روی جدول نساختید، این کوئری رو یک‌بار روی دیتابیس اجرا کنید:
#
#   ALTER TABLE users_diamonds ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 0;
#

async def get_user_level(user_id: int) -> int:
    try:
        pool = get_pool()
        value = await pool.fetchval(
            "SELECT level FROM users_diamonds WHERE user_id = $1", user_id
        )
        return value or 0
    except Exception as e:
        print(f"Error getting level for {user_id}: {e}")
        return 0


async def increment_user_level(user_id: int):
    """
    ✅ نسخه اتمیک: با یک INSERT ... ON CONFLICT ... RETURNING، لول کاربر
    یک واحد افزایش پیدا می‌کنه (یا اگه رکوردی نبود، با لول 1 ساخته میشه)
    و مقدار جدید همون‌جا برگردونده میشه؛ دقیقاً مثل update_diamonds اتمیکه.
    """
    try:
        pool = get_pool()
        new_level = await pool.fetchval(
            """
            INSERT INTO users_diamonds (user_id, level)
            VALUES ($1, 1)
            ON CONFLICT (user_id)
            DO UPDATE SET level = users_diamonds.level + 1
            RETURNING level
            """,
            user_id,
        )
        return new_level
    except Exception as e:
        print(f"Error incrementing level for {user_id}: {e}")
        return None


def get_upgrade_cost(current_level: int) -> int:
    """
    الگوریتم هزینه ارتقا:
    از لول 0 به 1 => 500
    از لول 1 به 2 => 1000
    از لول 2 به 3 => 1500
    یعنی هر لول 500 تا نسبت به لول قبلی بیشتر میشه
    """
    return (current_level + 1) * 500


# ⬆️ شروع درخواست ارتقا (پیام + دکمه تایید/لغو)
async def request_level_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    user_id = user.id

    current_level = await get_user_level(user_id)
    current_diamonds = await get_user_diamonds(user_id)
    cost = get_upgrade_cost(current_level)

    text = (
        "⬆️ <b>ارتقای لول</b>\n\n"
        f"🔹 <b>لول فعلی شما:</b> {current_level}\n"
        f"🔹 <b>لول بعد از ارتقا:</b> {current_level + 1}\n"
        f"💰 <b>موجودی فعلی:</b> <code>{current_diamonds}</code> طلا\n"
        f"💵 <b>هزینه ارتقا:</b> <code>{cost}</code> طلا\n\n"
        "آیا مایل به ارتقا هستید؟"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"lvlup_yes_{user_id}_{current_level}"),
            InlineKeyboardButton("❌ لغو", callback_data=f"lvlup_no_{user_id}")
        ]
    ])

    await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


# 🎛️ مدیریت کلیک روی دکمه‌های تایید/لغو ارتقای لول
async def handle_levelup_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    clicker = query.from_user
    clicker_id = clicker.id
    data = query.data

    async def safe_answer(text, show_alert=False):
        try:
            await query.answer(text, show_alert=show_alert)
        except BadRequest as e:
            if "Query is too old" in str(e):
                print("📌 [LevelUp] کالبک قدیمی بود.")
            else:
                raise e

    if data.startswith("lvlup_no_"):
        owner_id = int(data.replace("lvlup_no_", ""))

        if clicker_id != owner_id:
            await safe_answer("⛔️ این دکمه مخصوص شما نیست!", show_alert=True)
            return

        await query.edit_message_text("❌ <b>ارتقای لول لغو شد.</b>", parse_mode="HTML")
        await safe_answer("لغو شد.")
        return

    elif data.startswith("lvlup_yes_"):
        parts = data.split("_")
        # فرمت: lvlup_yes_{user_id}_{level}
        owner_id = int(parts[2])

        if clicker_id != owner_id:
            await safe_answer("⛔️ این دکمه مخصوص شما نیست!", show_alert=True)
            return

        # همیشه مقادیر رو تازه از دیتابیس می‌خونیم تا اگه بین ارسال پیام و کلیک دکمه
        # چیزی تغییر کرده باشه (مثلاً موجودی کم شده)، جلوش گرفته بشه
        fresh_level = await get_user_level(owner_id)
        fresh_diamonds = await get_user_diamonds(owner_id)
        cost = get_upgrade_cost(fresh_level)

        if fresh_diamonds < cost:
            await safe_answer(
                f"❌ موجودی کافی نیست! شما {fresh_diamonds} طلا دارید و {cost} طلا لازمه.",
                show_alert=True,
            )
            return

        # 🔒 اول طلا کسر میشه، بعد لول اضافه میشه (هر دو اتمیک)
        await update_diamonds(owner_id, -cost)
        new_level = await increment_user_level(owner_id)
        new_balance = await get_user_diamonds(owner_id)

        try:
            await query.edit_message_text(
                "✅ <b>ارتقا با موفقیت انجام شد!</b>\n\n"
                f"🔹 <b>لول جدید شما:</b> {new_level}\n"
                f"💰 <b>موجودی باقی‌مانده:</b> <code>{new_balance}</code> طلا",
                parse_mode="HTML"
            )
        except BadRequest as e:
            print(f"Error in level up result: {e}")

        await safe_answer("لول شما ارتقا پیدا کرد! 🎉")


def register_levelup_handlers(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\ارتقای لول$'), request_level_up))
    app.add_handler(CallbackQueryHandler(handle_levelup_clicks, pattern=r'^lvlup_.*'))
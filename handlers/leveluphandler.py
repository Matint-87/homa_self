from telethon import events, Button
from utils import get_pool  # جایگزین ایمپورت مستقیم pool برای هماهنگی با دیتابیس لوکال VPS

# ============== توابع دیتابیس مربوط به طلا ==============

async def get_user_diamonds(user_id: int) -> int:
    try:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT diamonds FROM users_diamonds WHERE user_id = $1",
            user_id,
        )
        return row["diamonds"] if row else 0
    except Exception as e:
        print(f"Error getting diamonds for {user_id}: {e}")
        return 0


async def update_diamonds(user_id: int, amount: int):
    try:
        pool = get_pool()
        current = await get_user_diamonds(user_id)
        new_balance = max(0, current + amount)
        # upsert: اگه رکورد بود آپدیت میشه، نبود ساخته میشه
        await pool.execute(
            """
            INSERT INTO users_diamonds (user_id, diamonds)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET diamonds = EXCLUDED.diamonds
            """,
            user_id,
            new_balance,
        )
        return new_balance
    except Exception as e:
        print(f"Error updating diamonds for {user_id}: {e}")
        return None


# ============== توابع دیتابیس مربوط به لول ==============
# نکته مهم: این توابع به فیلد "level" روی جدول users_diamonds نیاز دارند.
# اگه این فیلد رو هنوز روی جدول نساختید، این کوئری رو یک‌بار روی دیتابیس اجرا کنید:
#
#   ALTER TABLE users_diamonds ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 0;
#

async def get_user_level(user_id: int) -> int:
    try:
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT level FROM users_diamonds WHERE user_id = $1",
            user_id,
        )
        return row["level"] if row and row["level"] is not None else 0
    except Exception as e:
        print(f"Error getting level for {user_id}: {e}")
        return 0


async def set_user_level(user_id: int, new_level: int):
    try:
        pool = get_pool()
        await pool.execute(
            """
            INSERT INTO users_diamonds (user_id, level)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET level = EXCLUDED.level
            """,
            user_id,
            new_level,
        )
        return new_level
    except Exception as e:
        print(f"Error setting level for {user_id}: {e}")
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


def register_levelup_handler(bot):
    """ثبت هندلر ارتقای لول - همه کاربرا می‌تونن ازش استفاده کنن"""

    # ⬆️ دستور ارتقای لول با دکمه تایید/لغو: *ارتقای لول
    @bot.on(events.NewMessage(pattern=r'^\*ارتقای لول$'))
    async def request_level_up(event):
        try:
            user_id = event.sender_id

            current_level = await get_user_level(user_id)
            current_diamonds = await get_user_diamonds(user_id)
            cost = get_upgrade_cost(current_level)

            text = (
                f"⬆️ <b>ارتقای لول</b>\n\n"
                f"🔹 لول فعلی شما: <b>{current_level}</b>\n"
                f"🔹 لول بعد از ارتقا: <b>{current_level + 1}</b>\n"
                f"💰 موجودی فعلی: <b>{current_diamonds:,}</b> طلا\n"
                f"💵 هزینه ارتقا: <b>{cost:,}</b> طلا\n\n"
                f"آیا مایل به ارتقا هستید؟"
            )

            buttons = [
                [
                    Button.inline("✅ تایید", data=f"lvlup_yes_{user_id}_{current_level}"),
                    Button.inline("❌ لغو", data=f"lvlup_no_{user_id}"),
                ]
            ]

            # چون این دستور ممکنه توسط هر کاربری فرستاده بشه (نه فقط خود اکانت سلف‌بات)،
            # با ریپلای جواب می‌دیم نه ادیت (چون پیام مال کاربر دیگه‌ست و قابل ادیت نیست)
            await event.reply(text, buttons=buttons, parse_mode='html')

        except Exception as e:
            print(f"Error in request_level_up: {e}")
            try:
                await event.reply("⚠️ خطایی در پردازش درخواست ارتقا رخ داد.")
            except:
                pass

    # هندلر کلیک روی دکمه‌های تایید/لغو ارتقای لول
    @bot.on(events.CallbackQuery(pattern=rb'^lvlup_(yes|no)_(\-?\d+)(?:_(\d+))?$'))
    async def handle_level_up_callback(event):
        try:
            action = event.pattern_match.group(1).decode()
            owner_id = int(event.pattern_match.group(2))
            clicker_id = event.sender_id

            # فقط کسی که خودش درخواست ارتقا داده حق زدن دکمه رو داره
            if clicker_id != owner_id:
                await event.answer("⛔️ این دکمه مخصوص شما نیست!", alert=True)
                return

            if action == "no":
                await event.edit("❌ ارتقای لول لغو شد.")
                await event.answer("لغو شد.")
                return

            # action == "yes"
            # همیشه مقادیر رو تازه از دیتابیس می‌خونیم تا از race condition جلوگیری بشه
            fresh_level = await get_user_level(owner_id)
            fresh_diamonds = await get_user_diamonds(owner_id)
            cost = get_upgrade_cost(fresh_level)

            if fresh_diamonds < cost:
                await event.answer(
                    f"موجودی کافی نیست! شما {fresh_diamonds:,} طلا دارید و {cost:,} طلا لازمه.",
                    alert=True,
                )
                return

            new_balance = await update_diamonds(owner_id, -cost)
            if new_balance is None:
                await event.answer("❌ خطا در کسر طلا، دوباره امتحان کنید.", alert=True)
                return

            new_level = await set_user_level(owner_id, fresh_level + 1)
            if new_level is None:
                # اگه ثبت لول جدید خطا داد، طلای کسر شده رو برگردون
                await update_diamonds(owner_id, cost)
                await event.answer("❌ خطا در ثبت لول جدید، دوباره امتحان کنید.", alert=True)
                return

            await event.edit(
                f"✅ <b>ارتقا با موفقیت انجام شد!</b>\n\n"
                f"🔹 لول جدید شما: <b>{new_level}</b>\n"
                f"💰 موجودی باقی‌مانده: <b>{new_balance:,}</b> طلا",
                parse_mode='html'
            )
            await event.answer("لول شما ارتقا پیدا کرد! 🎉")

        except Exception as e:
            print(f"Error in handle_level_up_callback: {e}")
            try:
                await event.answer("⚠️ خطایی رخ داد.", alert=True)
            except:
                pass
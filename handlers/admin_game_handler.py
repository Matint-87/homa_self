import re
from telethon import events
from utils import get_pool  # جایگزین ایمپورت مستقیم pool برای هماهنگی با دیتابیس لوکال VPS

# لیست آیدی‌های مجاز برای اجرای دستورات ادمینی
ALLOWED_ADMINS = {8004897709, 8668275780, 1632503299, 8413953138}

def is_admin(sender_id):
    return sender_id in ALLOWED_ADMINS


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


def register_admin_handlers(bot):
    """ثبت هندلرهای سلف‌بات (با قابلیت ادیت روی پیام ادمین)"""

    # 🏆 ۱. دستور نمایش رنکینگ برتر با ادیت پیام: *رنکینگ
    @bot.on(events.NewMessage(outgoing=True, pattern=r'^\*رنکینگ$'))
    async def show_admin_ranking(event):
        if not is_admin(event.sender_id):
            return

        try:
            pool = get_pool()
            rows = await pool.fetch(
                """
                SELECT * FROM rps_rankings
                ORDER BY wins_count DESC
                LIMIT 15
                """
            )

            if not rows:
                await event.edit("📭 هنوز هیچ اطلاعاتی در جدول رنکینگ ثبت نشده است.")
                return

            lines = ["🏆 **جدول ۱۵ نفر برتر بازی سنگ، کاغذ، قیچی** 🏆\n"]
            for i, row in enumerate(rows, 1):
                name = row.get('username') or 'کاربر ناشناس'
                wins = row.get('wins_count', 0)
                lines.append(f"🏅 {i}. {name} (`{row['user_id']}`) ➔ **{wins} برد**")

            await event.edit("\n".join(lines))

        except Exception as e:
            await event.edit("❌ خطا در دریافت اطلاعات رنکینگ از دیتابیس!")
            print(f"Error in ranking: {e}")

    @bot.on(events.NewMessage(outgoing=True, pattern=r'^\*پاکسازی رنک$'))
    async def reset_all_rankings(event):
        if not is_admin(event.sender_id):
            return

        try:
            pool = get_pool()
            await pool.execute(
                "UPDATE rps_rankings SET wins_count = 0 WHERE wins_count != -1"
            )
            await event.edit("✅ **پاکسازی انجام شد!**\n\nتمام رکوردها در جدول با موفقیت صفر شدند.")

        except Exception as e:
            await event.edit("❌ خطا در اجرای دستور پاکسازی!")
            print(f"Error resetting rankings: {e}")

    # 🪙 ۲. دستور کسر با ریپلای و ادیت پیام: *کسر طلا [عدد]
    @bot.on(events.NewMessage(incoming=False, pattern=r'^\*کسر طلا\s+(\d+)$'))
    async def deduct_user_diamonds(event):
        if not is_admin(event.sender_id):
            return

        if not event.is_reply:
            await event.edit("⚠️ لطفاً این دستور را با ریپلای روی پیام کاربر مورد نظر ارسال کنید!")
            return

        try:
            amount_to_deduct = int(event.pattern_match.group(1))

            reply_msg = await event.get_reply_message()
            target_user_id = reply_msg.sender_id

            if not target_user_id:
                await event.edit("❌ موفق به دریافت آیدی کاربر از روی ریپلای نشدم.")
                return

            new_balance = await update_diamonds(target_user_id, -amount_to_deduct)

            if new_balance is not None:
                try:
                    target_user = await bot.get_entity(target_user_id)
                    target_name = f"@{target_user.username}" if target_user.username else (target_user.first_name or "کاربر")
                except Exception:
                    target_name = f"کاربر ({target_user_id})"

                new_balance_toman = new_balance * 35
                await event.edit(
                    f"✅ مقدار `{amount_to_deduct:,}` طلا از حساب {target_name} کسر شد.\n\n"
                    f"💰 موجودی جدید: `{new_balance:,}` طلا\n"
                    f"💵 معادل تومان: `{new_balance_toman:,}` تومان"
                )
            else:
                await event.edit("❌ مشکلی در اتصال یا به‌روزرسانی دیتابیس به وجود آمد.")

        except Exception as e:
            await event.edit("❌ خطایی در فرآیند کسر طلا رخ داد!")
            print(e)

    # 💰 ۳. دستور واریز طلا با ریپلای و ادیت پیام: *واریز طلا [عدد]
    @bot.on(events.NewMessage(outgoing=True, pattern=r'^\*واریز طلا (\d+)$'))
    async def handle_telethon_transfer(event):
        if not is_admin(event.sender_id):
            return

        try:
            # گرفتن مقدار عددی از پترن
            amount = int(event.pattern_match.group(1))
            
            # بررسی اینکه حتما روی پیام کسی ریپلای شده باشد
            reply = await event.get_reply_message()
            if not reply:
                await event.edit("❌ برای واریز، روی پیام کاربر مورد نظر ریپلای کنید!")
                return

            sender_id = event.sender_id
            target_user_id = reply.sender_id

            if not target_user_id:
                await event.edit("❌ موفق به دریافت آیدی کاربر از روی ریپلای نشدم.")
                return

            # جلوگیری از واریز به خود
            if sender_id == target_user_id:
                await event.edit("❌ شما نمی‌توانید به خودتان طلا واریز کنید!")
                return

            # بررسی موجودی فرستنده (ادمین)
            from_balance = await get_user_diamonds(sender_id)
            if from_balance < amount:
                await event.edit(f"❌ موجودی کافی نیست. موجودی فعلی: {from_balance:,}")
                return

            # اعمال تراکنش (کاهش از ادمین، افزایش به گیرنده)
            new_sender_balance = await update_diamonds(sender_id, -amount)
            if new_sender_balance is None:
                await event.edit("❌ انتقال انجام نشد.")
                return

            new_target_balance = await update_diamonds(target_user_id, amount)
            if new_target_balance is None:
                # بازگرداندن مقدار به ادمین در صورت خطا
                await update_diamonds(sender_id, amount)
                await event.edit("❌ خطا در واریز به گیرنده.")
                return

            try:
                target_user = await bot.get_entity(target_user_id)
                target_name = target_user.first_name or "کاربر"
            except Exception:
                target_name = "کاربر"

            # ارسال پیام موفقیت و ویرایش پیام دستور
            await event.edit(
                f"✅ <b>واریز موفقیت‌آمیز!</b>\n\n"
                f"👤 <b>گیرنده:</b> {target_name}\n"
                f"💰 <b>مقدار:</b> {amount:,} طلا\n"
                f"💵 <b>معادل تومان:</b> {amount * 35:,} تومان\n\n"
                f"💰 <b>موجودی جدید گیرنده:</b> {new_target_balance:,} طلا\n"
                f"💵 <b>معادل تومان:</b> {new_target_balance * 35:,} تومان",
                parse_mode='html'
            )
            
        except Exception as e:
            print(f"Error in telethon transfer: {e}")
            try:
                await event.edit("⚠️ خطایی در انجام تراکنش رخ داد.")
            except:
                await event.reply("⚠️ خطایی در انجام تراکنش رخ داد.")
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from handlers.rps_game_handler import get_user_diamonds, update_diamonds, add_win_to_ranking, get_mention

ACTIVE_XO_GAMES = {}
GAME_EXPIRY_SECONDS = 120  # ⏳ اگر تا ۲ دقیقه کسی join نکند، بازی خودکار باطل می‌شود

# 🎯 تمام حالت‌های برد (سطر، ستون، قطر)
WIN_COMBOS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # سطرها
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # ستون‌ها
    (0, 4, 8), (2, 4, 6),              # قطرها
]

SYMBOLS = {"": "➖", "X": "❌", "O": "⭕"}


def cancel_expiry_job(context: ContextTypes.DEFAULT_TYPE, game_id: str):
    """حذف job زمان‌بندی‌شده‌ی انقضا (وقتی بازی زودتر join/cancel شود دیگر لازم نیست اجرا شود)"""
    jobs = context.job_queue.get_jobs_by_name(f"xo_expire_{game_id}")
    for job in jobs:
        job.schedule_removal()


async def expire_xo_game(context: ContextTypes.DEFAULT_TYPE):
    """⌛ اجرا می‌شود اگر بازی بعد از GAME_EXPIRY_SECONDS هنوز حریفی پیدا نکرده باشد"""
    job_data = context.job.data
    game_id = job_data["game_id"]
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]

    game = ACTIVE_XO_GAMES.get(game_id)
    if not game or game["status"] != "waiting":
        return  # قبلاً join/cancel شده، کاری لازم نیست

    # 💰 بازگرداندن طلای بلوکه‌شده‌ی سازنده
    await update_diamonds(game["creator_id"], game["bet_amount"])
    del ACTIVE_XO_GAMES[game_id]

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "⌛ <b>این بازی به دلیل عدم پاسخ حریف تا ۲ دقیقه، "
                "به‌صورت خودکار باطل شد.</b>\n💰 طلای شرط بازگردانده شد."
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass


def build_board_keyboard(game_id: str, board: list):
    """ساخت کیبورد شیشه‌ای ۳x۳ بر اساس وضعیت فعلی بازی"""
    buttons = []
    for row in range(3):
        row_buttons = []
        for col in range(3):
            idx = row * 3 + col
            cell = board[idx]
            label = SYMBOLS[cell] if cell else str(idx + 1)
            row_buttons.append(
                InlineKeyboardButton(label, callback_data=f"xo_move_{game_id}_{idx}")
            )
        buttons.append(row_buttons)
    return InlineKeyboardMarkup(buttons)


def check_winner(board: list):
    """بررسی می‌کند آیا نماد برنده‌ای روی صفحه شکل گرفته؛ خروجی 'X'، 'O' یا None"""
    for a, b, c in WIN_COMBOS:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def build_turn_text(game: dict):
    """متن نمایش نوبت فعلی بازی"""
    turn_name = game["creator_name"] if game["turn_id"] == game["creator_id"] else game["opponent_name"]
    turn_symbol = "❌" if game["turn_id"] == game["creator_id"] else "⭕"
    return (
        f"<b>🎮 دوز | شرط: {game['bet_amount']} طلا</b>\n\n"
        f"❌ {game['creator_name']}\n"
        f"⭕ {game['opponent_name']}\n\n"
        f"👉 نوبت: {turn_symbol} {turn_name}"
    )


async def start_xo_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if update.effective_chat.type == "private":
        return

    text = message.text
    match = re.match(r'^دوز\s+(\d+)$', text)
    if not match:
        return

    bet_amount = int(match.group(1))

    if bet_amount < 30:
        await message.reply_text("⚠️ حداقل شرط برای بازی ۳۰ طلا است!")
        return

    creator_diamonds = await get_user_diamonds(user.id)
    if creator_diamonds < bet_amount:
        await message.reply_text("❌ موجودی شما برای این شرط کافی نیست.")
        return

    # ۱. کسر مبلغ از سازنده بلافاصله هنگام ساخت بازی
    await update_diamonds(user.id, -bet_amount)

    game_id = f"xo_{user.id}_{message.message_id}"
    ACTIVE_XO_GAMES[game_id] = {
        "creator_id": user.id,
        "creator_name": get_mention(user),
        "opponent_id": None,
        "opponent_name": None,
        "bet_amount": bet_amount,
        "status": "waiting",
        "board": [""] * 9,
        "turn_id": None,
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("قبول", callback_data=f"xo_join_{game_id}", style="success"),
        InlineKeyboardButton("لغو", callback_data=f"xo_cancel_{game_id}", style="danger")
    ]])

    sent_message = await message.reply_text(
        f"<b>درخواست بازی دوز {bet_amount}</b>\n\n"
        f"👤 سازنده: {get_mention(user)}\n"
        f"💰 شرط: {bet_amount} طلا\n\n"
        "💬 یک نفر برای شروع بازی باید دکمه <b>« قبول »</b> را بزند!",
        reply_markup=keyboard, parse_mode="HTML"
    )

    # ⏳ زمان‌بندی ابطال خودکار بازی اگر تا ۲ دقیقه کسی join نکند
    context.job_queue.run_once(
        expire_xo_game,
        when=GAME_EXPIRY_SECONDS,
        data={"game_id": game_id, "chat_id": update.effective_chat.id, "message_id": sent_message.message_id},
        name=f"xo_expire_{game_id}"
    )


async def handle_xo_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user

    # ---------- لغو بازی ----------
    if data.startswith("xo_cancel_"):
        game_id = data.replace("xo_cancel_", "")
        game = ACTIVE_XO_GAMES.get(game_id)

        if not game:
            await query.answer("❌ این بازی دیگر در دسترس نیست!", show_alert=True)
            return

        if game["creator_id"] != user.id:
            await query.answer("⚠️ فقط سازنده بازی می‌تواند آن را لغو کند!", show_alert=True)
            return

        if game["status"] != "waiting":
            await query.answer("⚠️ بازی شروع شده و دیگر قابل لغو نیست!", show_alert=True)
            return

        # بازگرداندن طلا به سازنده در صورت لغو
        await update_diamonds(user.id, game["bet_amount"])
        cancel_expiry_job(context, game_id)
        del ACTIVE_XO_GAMES[game_id]
        await query.edit_message_text("❌ بازی توسط سازنده لغو شد و طلا به حساب شما برگشت.")
        return

    # ---------- پیوستن حریف ----------
    if data.startswith("xo_join_"):
        game_id = data.replace("xo_join_", "")
        game = ACTIVE_XO_GAMES.get(game_id)

        if not game or game["status"] != "waiting":
            await query.answer("❌ این بازی دیگر در دسترس نیست!", show_alert=True)
            return

        if user.id == game["creator_id"]:
            await query.answer("شما خودتان سازنده هستید!", show_alert=True)
            return

        bet = game["bet_amount"]
        opp_diamonds = await get_user_diamonds(user.id)

        if opp_diamonds < bet:
            await query.answer("موجودی شما کافی نیست!", show_alert=True)
            return

        # کسر مبلغ از نفر دوم و شروع رسمی بازی
        await update_diamonds(user.id, -bet)
        game["opponent_id"] = user.id
        game["opponent_name"] = get_mention(user)
        game["status"] = "playing"
        game["turn_id"] = game["creator_id"]  # ❌ (سازنده) همیشه شروع‌کننده است

        cancel_expiry_job(context, game_id)

        await query.edit_message_text(
            build_turn_text(game),
            reply_markup=build_board_keyboard(game_id, game["board"]),
            parse_mode="HTML"
        )
        return

    # ---------- حرکت روی صفحه ----------
    if data.startswith("xo_move_"):
        remainder = data.replace("xo_move_", "")
        game_id, cell_idx = remainder.rsplit("_", 1)
        cell_idx = int(cell_idx)
        game = ACTIVE_XO_GAMES.get(game_id)

        if not game or game["status"] != "playing":
            await query.answer("❌ این بازی دیگر در دسترس نیست!", show_alert=True)
            return

        if user.id not in (game["creator_id"], game["opponent_id"]):
            await query.answer("⚠️ شما در این بازی حضور ندارید!", show_alert=True)
            return

        if user.id != game["turn_id"]:
            await query.answer("⏳ نوبت شما نیست!", show_alert=True)
            return

        if game["board"][cell_idx] != "":
            await query.answer("⚠️ این خانه قبلاً پر شده!", show_alert=True)
            return

        # ثبت حرکت
        symbol = "X" if user.id == game["creator_id"] else "O"
        game["board"][cell_idx] = symbol

        winner_symbol = check_winner(game["board"])
        is_full = all(cell != "" for cell in game["board"])

        # ---------- برد ----------
        if winner_symbol:
            if winner_symbol == "X":
                winner_id, winner_name = game["creator_id"], game["creator_name"]
                loser_id, loser_name = game["opponent_id"], game["opponent_name"]
            else:
                winner_id, winner_name = game["opponent_id"], game["opponent_name"]
                loser_id, loser_name = game["creator_id"], game["creator_name"]

            bet = game["bet_amount"]
            # پرداخت جایزه به برنده (مجموع دو شرط)
            await update_diamonds(winner_id, 2 * bet)
            await add_win_to_ranking(winner_id, winner_name)

            winner_balance = await get_user_diamonds(winner_id)
            loser_balance = await get_user_diamonds(loser_id)

            await query.edit_message_text(
                f"<b>🏁 بازی دوز به پایان رسید!</b>\n\n"
                + "\n".join(
                    "".join(SYMBOLS[game["board"][r * 3 + c]] for c in range(3))
                    for r in range(3)
                )
                + f"\n\n👑 برنده: {winner_name}\n"
                f"💰 موجودی برنده: {winner_balance}\n"
                f"🥶 بازنده: {loser_name}\n"
                f"💰 موجودی بازنده: {loser_balance}",
                parse_mode="HTML"
            )
            del ACTIVE_XO_GAMES[game_id]
            return

        # ---------- مساوی (صفحه پر شد و برنده‌ای نبود) ----------
        if is_full:
            bet = game["bet_amount"]
            # 🤝 چون هیچ‌کس نباخته، شرط هر دو نفر بدون کم‌وکسر برگردانده می‌شود
            await update_diamonds(game["creator_id"], bet)
            await update_diamonds(game["opponent_id"], bet)

            await query.edit_message_text(
                f"<b>🤝 بازی مساوی شد!</b>\n\n"
                + "\n".join(
                    "".join(SYMBOLS[game["board"][r * 3 + c]] for c in range(3))
                    for r in range(3)
                )
                + f"\n\n💰 شرط هر دو بازیکن ({bet} طلا) بازگردانده شد.",
                parse_mode="HTML"
            )
            del ACTIVE_XO_GAMES[game_id]
            return

        # ---------- ادامه بازی: نوبت نفر بعدی ----------
        game["turn_id"] = (
            game["opponent_id"] if game["turn_id"] == game["creator_id"] else game["creator_id"]
        )

        await query.edit_message_text(
            build_turn_text(game),
            reply_markup=build_board_keyboard(game_id, game["board"]),
            parse_mode="HTML"
        )


def register_xo_handlers(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^دوز\s+(\d+)$'), start_xo_request))
    app.add_handler(CallbackQueryHandler(handle_xo_clicks, pattern=r'^xo_.*'))
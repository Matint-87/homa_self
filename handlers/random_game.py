import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from handlers.rps_game_handler import get_user_diamonds, update_diamonds, add_win_to_ranking, get_mention

ACTIVE_DICE_GAMES = {}

async def start_dice_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    
    if update.effective_chat.type == "private": return
    
    text = message.text
    import re
    match = re.match(r'^بازی\s+(\d+)$', text)
    if not match: return
    
    bet_amount = int(match.group(1))
    
    if bet_amount < 30:
        await message.reply_text("⚠️ حداقل شرط برای بازی ۳۰ طلا است!")
        return

    creator_diamonds = await get_user_diamonds(user.id)
    if creator_diamonds < 30:
        await message.reply_text("❌ موجودی شما برای شروع بازی باید حداقل ۳۰ طلا باشد.")
        return
    if creator_diamonds < bet_amount:
        await message.reply_text("❌ موجودی شما برای این شرط کافی نیست.")
        return

    game_id = f"dice_{user.id}_{message.message_id}"
    ACTIVE_DICE_GAMES[game_id] = {
        "creator_id": user.id,
        "creator_name": get_mention(user),
        "bet_amount": bet_amount,
        "status": "waiting"
    }

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("قبول", callback_data=f"dice_join_{game_id}", style="success"),
        InlineKeyboardButton("لغو", callback_data=f"dice_cancel_{game_id}", style="danger")
    ]])
    
    await message.reply_text(
        f"<b>درخواست بازی {bet_amount}</b>\n\n"
        f"👤 سازنده: {get_mention(user)}\n"
        f"💰 شرط: {bet_amount} طلا\n\n"
        "💬 یک نفر برای شروع بازی باید دکمه <b>« قبول »</b> را بزند!",
        reply_markup=keyboard, parse_mode="HTML"
    )

async def handle_dice_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user = query.from_user
    
    if data.startswith("dice_cancel_"):
        game_id = data.replace("dice_cancel_", "")
        if game_id in ACTIVE_DICE_GAMES and ACTIVE_DICE_GAMES[game_id]["creator_id"] == user.id:
            del ACTIVE_DICE_GAMES[game_id]
            await query.edit_message_text("❌ بازی توسط سازنده لغو شد.")
        return

    if data.startswith("dice_join_"):
        game_id = data.replace("dice_join_", "")
        game = ACTIVE_DICE_GAMES.get(game_id)
        
        if not game or game["status"] != "waiting":
            await query.answer("❌ این بازی دیگر در دسترس نیست!", show_alert=True)
            return
            
        if user.id == game["creator_id"]:
            await query.answer("شما خودتان سازنده هستید!", show_alert=True)
            return

        opp_diamonds = await get_user_diamonds(user.id)
        if opp_diamonds < 30 or opp_diamonds < game["bet_amount"]:
            await query.answer("موجودی شما کافی نیست (حداقل ۳۰ طلا)!", show_alert=True)
            return

        # قرعه‌کشی
        bet = game["bet_amount"]
        is_creator_winner = random.choice([True, False])
        
        winner = game["creator_id"] if is_creator_winner else user.id
        loser = user.id if is_creator_winner else game["creator_id"]
        
        winner_name = game["creator_name"] if is_creator_winner else get_mention(user)
        loser_name = get_mention(user) if is_creator_winner else game["creator_name"]

        # آپدیت دیتابیس
        await update_diamonds(winner, bet)
        await update_diamonds(loser, -bet)
        await add_win_to_ranking(winner, winner_name)

        # دریافت موجودی جدید
        new_winner_balance = await get_user_diamonds(winner)
        new_loser_balance = await get_user_diamonds(loser)

        result_text = (
            f"<b>بازی {bet} به پایان رسید!</b>\n\n"
            f"👑 <b>کاربر برنده:</b> {winner_name}\n"
            f"💰 <b>موجودی جدید:</b> {new_winner_balance} طلا\n\n"
            f"🥶 <b>کاربر بازنده:</b> {loser_name}\n"
            f"💰 <b>موجودی جدید:</b> {new_loser_balance} طلا"
        )
        
        await query.edit_message_text(result_text, parse_mode="HTML")
        del ACTIVE_DICE_GAMES[game_id]

def register_dice_handlers(app):
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^بازی\s+(\d+)$'), start_dice_request))
    app.add_handler(CallbackQueryHandler(handle_dice_clicks, pattern=r'^dice_.*'))

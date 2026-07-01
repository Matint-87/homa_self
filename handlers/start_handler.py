from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from .membershi_handler import check_membership, send_join_button
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    is_member, _ = await check_membership(context, user_id, config.CHANNELS)
    if not is_member:
        await send_join_button(update, context)
        return

    contact_button = KeyboardButton(
        text="📱 ارسال شماره من",
        request_contact=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[contact_button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "برای ادامه لطفاً شماره خود را ارسال کنید:",
        reply_markup=keyboard
    )
    
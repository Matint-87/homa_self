
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import logging
import config


logger = logging.getLogger(__name__)

async def send_join_button(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id_to_delete: int | None = None):

    keyboard = [
        [InlineKeyboardButton("عضویت در کانال اول", url=config.CHANNELS[0]["url"])],
        [InlineKeyboardButton("عضویت در گروه دوم", url=config.CHANNELS[1]["url"])],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data='check')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    chat_id = update.effective_chat.id

    if message_id_to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        except Exception as e:
            logger.error(e)

    if update.message:
        msg = await update.message.reply_text(
            "لطفاً عضو کانال‌ها شوید",
            reply_markup=reply_markup
        )
    else:
        msg = await update.callback_query.message.reply_text(
            "لطفاً عضو کانال‌ها شوید",
            reply_markup=reply_markup
        )

    return msg.message_id


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if data == 'register':
        await query.edit_message_text("درخواست ثبت نام شما ثبت شد (نمونه). اگر عضو هستید دوباره /start بزنید.")
    elif data == 'help':
        await query.edit_message_text("راهنما: برای استفاده از ربات لطفاً عضو کانال/گروه شوید و بعد /start را بزنید.")
    elif data == 'check':
        is_member, missing_channel_name = await check_membership(context, user_id, config.CHANNELS)

        if is_member:
            await query.edit_message_text(
                f"سلام {query.from_user.mention_html()}! شما عضو هستید ✅\n"
                "هر پیامی بفرستید اکو می‌کنم 😊"
            )

        else:
            if missing_channel_name and "خطا" in missing_channel_name:
                await query.edit_message_text(f"خطا در بررسی عضویت در یکی از کانال‌ها. لطفاً بعداً دوباره تلاش کنید.")
            else:
                await query.edit_message_text(f"شما هنوز در کانال '{missing_channel_name}' عضو نشده‌اید. لطفاً عضو شوید و دوباره دکمه 'بررسی عضویت' را بزنید.")

            await send_join_button(update, context, message_id_to_delete=message_id)

async def check_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int, channels_to_check: list[dict]) -> tuple[bool, str | None]:
    """
    Checks if a user is a member of all specified channels.
    Returns a tuple: (is_member: bool, first_missing_channel_name: str | None).
    If user is a member of all, returns (True, None).
    If user is not a member of at least one channel, returns (False, name_of_first_missing_channel).
    """
    for channel in channels_to_check:
        try:
            member = await context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False, channel.get("name", channel["id"])
        except Exception as e:
            logger.error(f"Error checking membership for {channel['id']} for user {user_id}: {e}")
            return False, f"خطا در بررسی: {channel.get('name', channel['id'])}"

    return True, None


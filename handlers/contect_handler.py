from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, WebAppInfo
from telegram.ext import ContextTypes

async def get_profile_photo(context, user_id: int):
    photos = await context.bot.get_user_profile_photos(user_id)

    if photos.total_count > 0:
        file_id = photos.photos[0][0].file_id
        file = await context.bot.get_file(file_id)

        file_path = file.file_path

        if file_path.startswith("http"):
            return file_path

        return f"https://api.telegram.org/file/bot{context.bot.token}/{file_path}"

    return None

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if contact.user_id != update.effective_user.id:
        return

    user = update.effective_user

    phone = contact.phone_number
    user_id = user.id
    username = user.username or ""
    profile_photo_url = await get_profile_photo(context, user_id)
    success = save_user(phone, user_id, username, profile_photo_url)

    if not success:
        await update.message.reply_text("❌ خطا در ذخیره اطلاعات. دوباره تلاش کنید")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("پنل سلف", web_app=WebAppInfo(url="https://mini-app-sigma-murex.vercel.app"))],
        [InlineKeyboardButton("💰خرید طلا", callback_data="BUY_GOLD")],
        [
            InlineKeyboardButton("موجودی", callback_data="BALANCE"),
            InlineKeyboardButton("انقضا", callback_data="EXPIRE"),
        ],
        [
            InlineKeyboardButton("🧑🏻‍💻 پشتیبانی", callback_data="SUPPORT"),
            InlineKeyboardButton("چنل", callback_data="CHANNEL"),
        ],
        [InlineKeyboardButton("🏆چالش ها", callback_data="CHALLENGES")],
    ])

    # حذف کیبورد شماره
    await update.message.reply_text(
        "✅ شماره شما ثبت شد",
        reply_markup=ReplyKeyboardRemove()
    )

    # نمایش منو
    await update.message.reply_text(
        "یکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=keyboard
    )
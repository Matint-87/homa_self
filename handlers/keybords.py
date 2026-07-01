# handlers/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

CHANNEL_URL = "https://t.me/Homa_self_Ch"
GROUP_URL = "https://t.me/Homa_self_Gp"

def get_start_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text="/start")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def get_join_keyboard():
    keyboard = [
        [InlineKeyboardButton("📢 ورود به چنل سلف", url=CHANNEL_URL)],
        [InlineKeyboardButton("👥 ورود به گروه سلف", url=GROUP_URL)],
        [InlineKeyboardButton("🔄 تایید عضویت", callback_data="check_membership")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_calc_keyboard(current_amount: str):
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="num_1"),
            InlineKeyboardButton("2", callback_data="num_2"),
            InlineKeyboardButton("3", callback_data="num_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="num_4"),
            InlineKeyboardButton("5", callback_data="num_5"),
            InlineKeyboardButton("6", callback_data="num_6"),
        ],
        [
            InlineKeyboardButton("7", callback_data="num_7"),
            InlineKeyboardButton("8", callback_data="num_8"),
            InlineKeyboardButton("9", callback_data="num_9"),
        ],
        [
            InlineKeyboardButton("Clear ❌", callback_data="num_clear"),
            InlineKeyboardButton("0", callback_data="num_0"),
            InlineKeyboardButton("Delete ⬅️", callback_data="num_del"),
        ],
        [
            InlineKeyboardButton(
                "💳 رفتن برای پرداخت",
                callback_data=f"go_to_pay_{current_amount if current_amount else 0}",
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 بازگشت و بسته شدن پنل", callback_data="close_panel"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_code_keyboard(current_code: str):
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="code_1"),
            InlineKeyboardButton("2", callback_data="code_2"),
            InlineKeyboardButton("3", callback_data="code_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="code_4"),
            InlineKeyboardButton("5", callback_data="code_5"),
            InlineKeyboardButton("6", callback_data="code_6"),
        ],
        [
            InlineKeyboardButton("7", callback_data="code_7"),
            InlineKeyboardButton("8", callback_data="code_8"),
            InlineKeyboardButton("9", callback_data="code_9"),
        ],
        [
            InlineKeyboardButton("Clear ❌", callback_data="code_clear"),
            InlineKeyboardButton("0", callback_data="code_0"),
            InlineKeyboardButton("Delete ⬅️", callback_data="code_del"),
        ],
        [
            InlineKeyboardButton(
                "📤 ارسال کد تایید", callback_data="code_submit"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 انصراف و لغو", callback_data="cancel_to_menu"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
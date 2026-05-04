from telegram import ReplyKeyboardMarkup


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🎨 Генеруй"],
            ["✏️ Редагувати"],
            ["🔄 Почати спочатку"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

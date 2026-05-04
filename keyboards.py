from telegram import ReplyKeyboardMarkup
from config import RESET_BTN
 
 
def make_keyboard(options: list) -> ReplyKeyboardMarkup:
    """Клавіатура з кнопкою скидання внизу."""
    keyboard = [[opt] for opt in options] + [[RESET_BTN]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
 

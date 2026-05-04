# =====================================
# RESET
# =====================================

if text == "🔄 Почати спочатку":
    context.user_data.clear()

    await update.message.reply_text(
        "Все скинуто. Напиши нову тему сторіс"
    )
    return
from telegram import Update
from telegram.ext import ContextTypes

from imagine import build_slide, analyze_reference
from keyboard import main_keyboard

# тут у тебе вже є твоя функція Claude (cloud.py)
from cloud import generate_story  # припускаю назву


# =========================================
# START
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напиши тему сторіс")


# =========================================
# ОСНОВНИЙ ХЕНДЛЕР
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    # =====================================
    # КНОПКА "ГЕНЕРУЙ"
    # =====================================

    if text == "🎨 Генеруй":

        slide_text = user_data.get("slide_text")
        what_to_show = user_data.get("what_to_show")
        style = user_data.get("style")

        if not slide_text:
            await update.message.reply_text("Немає тексту для генерації")
            return

        await update.message.reply_text("Генерую...")

        image = await build_slide(
            slide_text=slide_text,
            what_to_show=what_to_show,
            reference_style_desc=style
        )

        await update.message.reply_photo(image)
        return

    # =====================================
    # КНОПКА "РЕДАГУВАТИ"
    # =====================================

    if text == "✏️ Редагувати":
        user_data["editing"] = True
        await update.message.reply_text("Напиши новий текст")
        return

    # =====================================
    # РЕДАГУВАННЯ ТЕКСТУ
    # =====================================

    if user_data.get("editing"):

        user_data["slide_text"] = text
        user_data["editing"] = False

        await update.message.reply_text(
            f"Оновлений текст:\n\n{text}",
            reply_markup=main_keyboard()
        )
        return

    # =====================================
    # НОВИЙ ЗАПИТ → CLAUDE
    # =====================================

    await update.message.reply_text("Генерую текст...")

    result = await generate_story(text)

    # тут адаптуй під свій формат
    slide_text = result["text"]
    what_to_show = result["what_to_show"]

    user_data["slide_text"] = slide_text
    user_data["what_to_show"] = what_to_show
    user_data["style"] = None

    await update.message.reply_text(
        f"{slide_text}\n\nЩо показати:\n{what_to_show}",
        reply_markup=main_keyboard()
    )


# =========================================
# ОБРОБКА ФОТО (РЕФЕРЕНС)
# =========================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    style = await analyze_reference(image_bytes)

    context.user_data["style"] = style

    await update.message.reply_text("Стиль збережено. Тепер натисни 'Генеруй'.")

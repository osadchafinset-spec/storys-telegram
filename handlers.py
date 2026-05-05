from telegram import Update
from telegram.ext import ContextTypes

from imagen import build_slide, analyze_reference
from keyboards import main_keyboard
from claude_api import generate_with_claude


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Напиши тему сторіс",
        reply_markup=main_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    # RESET
    if text == "🔄 Почати спочатку":
        user_data.clear()
        await update.message.reply_text(
            "Все скинуто. Напиши нову тему",
            reply_markup=main_keyboard()
        )
        return

    # ГЕНЕРАЦІЯ КАРТИНКИ
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

    # НОВИЙ ЗАПИТ → CLAUDE
    await update.message.reply_text("Генерую текст...")

    result = await generate_with_claude(text)

    user_data["slide_text"] = result
    user_data["what_to_show"] = result
    user_data["style"] = None

    await update.message.reply_text(
        f"{result}",
        reply_markup=main_keyboard()
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    style = await analyze_reference(image_bytes)
    context.user_data["style"] = style

    await update.message.reply_text(
        "Стиль збережено. Натисни 🎨 Генеруй",
        reply_markup=main_keyboard()
    )

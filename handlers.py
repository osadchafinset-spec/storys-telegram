from telegram import Update
from telegram.ext import ContextTypes

from prompts import build_theme_prompt
from claude_api import generate_with_claude
from imagen import build_slide
from keyboards import main_keyboard


# тимчасово захардкодимо (потім винесемо в кнопки)
DEFAULT_LANG = "Українська"
DEFAULT_GOAL = "Залучення"
DEFAULT_TONE = "Провокативний"
DEFAULT_COUNT = 5


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

        slide_data = user_data.get("slides")

        if not slide_data:
            await update.message.reply_text("Немає даних для генерації")
            return

        await update.message.reply_text("Генерую...")

        # беремо перший слайд як тест
        first_slide = slide_data[0]

        image = await build_slide(
            slide_text=first_slide["text"],
            what_to_show=first_slide["visual"],
            reference_style_desc=None
        )

        await update.message.reply_photo(image)
        return

    # ГЕНЕРАЦІЯ СТОРІС
    await update.message.reply_text("Генерую сторіс...")

    prompt = build_theme_prompt(
        theme=text,
        lang=DEFAULT_LANG,
        goal=DEFAULT_GOAL,
        tone=DEFAULT_TONE,
        count=DEFAULT_COUNT
    )

    result = await generate_with_claude(prompt)

    # дуже простий парс (потім покращимо)
    slides = parse_slides(result)

    user_data["slides"] = slides

    await update.message.reply_text(result, reply_markup=main_keyboard())


def parse_slides(text: str):
    slides = []

    blocks = text.split("Слайд")[1:]

    for block in blocks:
        slide = {}

        lines = block.split("\n")

        for line in lines:
            if "Текст:" in line:
                slide["text"] = line.split("Текст:")[-1].strip()
            if "Що показати:" in line:
                slide["visual"] = line.split("Що показати:")[-1].strip()

        slides.append(slide)

    return slides

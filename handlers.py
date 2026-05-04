import asyncio
import logging
import re

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from config import GOALS, TONES, STORY_COUNTS, MODES, LANGUAGES, RESET_BTN, STYLES
from keyboards import make_keyboard
from prompts import build_theme_prompt, build_story_prompt
from claude_api import generate_with_claude
from imagen import build_slide, analyze_reference, DEFAULT_STYLE

logger = logging.getLogger(__name__)

# =========================================
# СТАНИ КОРИСТУВАЧІВ (in-memory)
# =========================================

user_data_store: dict = {}

REFERENCE_OPTIONS = ["📎 Завантажити референс", "➡️ Пропустити"]


def reset_state(user_id: int, keep_language: bool = False) -> None:
    lang = user_data_store.get(user_id, {}).get("language") if keep_language else None
    user_data_store[user_id] = {"step": "language"}
    if lang:
        user_data_store[user_id]["language"] = lang
        user_data_store[user_id]["step"] = "mode"


# =========================================
# ПАРСИНГ ВІДПОВІДІ CLAUDE
# =========================================

def parse_slides(text: str) -> list[dict]:
    """
    Витягує слайди з відповіді Claude.
    Повертає список: [{"text": "...", "what_to_show": "...", "has_interactive": bool}]
    """
    slides = []
    blocks = re.split(r"Слайд\s+\d+\s*:", text)

    for block in blocks[1:]:
        slide_text      = ""
        what_to_show    = ""
        has_interactive = False

        text_match = re.search(r"-\s*Текст:\s*(.+)", block)
        if text_match:
            slide_text = text_match.group(1).strip().strip('"').replace("(не більше 18 слів)", "").strip()

        show_match = re.search(r"-\s*Що показати:\s*(.+)", block)
        if show_match:
            what_to_show = show_match.group(1).strip()

        interactive_match = re.search(r"-\s*Інтерактив:\s*(.+)", block)
        if interactive_match:
            interactive_val = interactive_match.group(1).strip()
            has_interactive = interactive_val.lower() not in ("без інтерактиву", "немає", "-", "")

        if slide_text:
            slides.append({
                "text":            slide_text,
                "what_to_show":    what_to_show or slide_text,
                "has_interactive": has_interactive,
            })

    return slides


# =========================================
# ДОПОМІЖНІ ФУНКЦІЇ
# =========================================

async def send_long_message(update: Update, text: str, chunk_size: int = 3500) -> None:
    for i in range(0, len(text), chunk_size):
        await update.message.reply_text(text[i:i + chunk_size])


# =========================================
# КОМАНДИ
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    reset_state(user_id, keep_language=False)
    await update.message.reply_text(
        "Оберіть мову / Choose language / Выберите язык",
        reply_markup=make_keyboard(LANGUAGES),
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    reset_state(update.effective_user.id, keep_language=False)
    await start(update, context)


# =========================================
# ОБРОБКА ФОТО (референс)
# =========================================

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обробляє завантажене фото як референс стилю."""
    if not update.message or not update.message.photo:
        return

    user_id = update.effective_user.id
    state   = user_data_store.get(user_id, {})

    if state.get("step") != "reference_upload":
        return

    await update.message.reply_text("🔍 Аналізую референс...")

    try:
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()

        style_desc = await analyze_reference(bytes(image_bytes))

        if style_desc:
            state["reference_style_desc"] = style_desc
            await update.message.reply_text("✅ Референс прийнято! Стиль проаналізовано.")
        else:
            await update.message.reply_text("⚠️ Не вдалося проаналізувати референс. Буде використано обраний стиль.")

    except Exception as e:
        logger.error("Reference photo error: %s", e)
        await update.message.reply_text("⚠️ Помилка при завантаженні. Буде використано обраний стиль.")

    # Переходимо до введення теми/історії
    state["step"] = "content_input"
    if state.get("mode") == "Тема":
        await update.message.reply_text("Напиши тему сторіс")
    else:
        await update.message.reply_text(
            "Напиши свою історію одним повідомленням:\n"
            "що сталося, що тебе зачепило, що хочеш донести людям"
        )


# =========================================
# ГОЛОВНИЙ HANDLER (текст)
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text    = update.message.text.strip()

    if user_id not in user_data_store:
        reset_state(user_id)

    # ── Скидання в будь-який момент ──────────────────────────────────────────
    if text == RESET_BTN:
        reset_state(user_id, keep_language=False)
        await start(update, context)
        return

    state = user_data_store[user_id]
    step  = state.get("step")

    # ── Крок 1: Мова ─────────────────────────────────────────────────────────
    if step == "language":
        if text not in LANGUAGES:
            await update.message.reply_text("Оберіть мову кнопкою")
            return
        state["language"] = text
        state["step"]     = "mode"
        await update.message.reply_text("Оберіть режим:", reply_markup=make_keyboard(MODES))
        return

    # ── Крок 2: Режим ────────────────────────────────────────────────────────
    if step == "mode":
        if text not in MODES:
            await update.message.reply_text("Оберіть режим кнопкою")
            return
        state["mode"] = text
        state["step"] = "goal"
        await update.message.reply_text("Оберіть ціль сторіс:", reply_markup=make_keyboard(GOALS))
        return

    # ── Крок 3: Ціль ─────────────────────────────────────────────────────────
    if step == "goal":
        if text not in GOALS:
            await update.message.reply_text("Оберіть ціль кнопкою")
            return
        state["goal"] = text
        state["step"] = "tone"
        await update.message.reply_text("Оберіть тон:", reply_markup=make_keyboard(TONES))
        return

    # ── Крок 4: Тон ──────────────────────────────────────────────────────────
    if step == "tone":
        if text not in TONES:
            await update.message.reply_text("Оберіть тон кнопкою")
            return
        state["tone"] = text
        state["step"] = "count"
        await update.message.reply_text("Оберіть кількість сторіс:", reply_markup=make_keyboard(STORY_COUNTS))
        return

    # ── Крок 5: Кількість ────────────────────────────────────────────────────
    if step == "count":
        if text not in STORY_COUNTS:
            await update.message.reply_text("Оберіть кількість кнопкою")
            return
        state["count"] = int(text)
        state["step"]  = "style"
        await update.message.reply_text("Оберіть стиль зображень:", reply_markup=make_keyboard(STYLES))
        return

    # ── Крок 6: Стиль ────────────────────────────────────────────────────────
    if step == "style":
        if text not in STYLES:
            await update.message.reply_text("Оберіть стиль кнопкою")
            return
        state["style"] = text
        state["step"]  = "reference"
        await update.message.reply_text(
            "Хочеш додати референс-зображення для стилю?",
            reply_markup=ReplyKeyboardMarkup(
                [[opt] for opt in REFERENCE_OPTIONS] + [[RESET_BTN]],
                resize_keyboard=True,
            ),
        )
        return

    # ── Крок 7: Референс (вибір) ─────────────────────────────────────────────
    if step == "reference":
        if text == "📎 Завантажити референс":
            state["step"] = "reference_upload"
            await update.message.reply_text(
                "Надішли фото-референс — я проаналізую його стиль 👇",
                reply_markup=ReplyKeyboardMarkup([[RESET_BTN]], resize_keyboard=True),
            )
            return

        if text == "➡️ Пропустити":
            state["reference_style_desc"] = None
            state["step"] = "content_input"
            if state["mode"] == "Тема":
                await update.message.reply_text("Напиши тему сторіс")
            else:
                await update.message.reply_text(
                    "Напиши свою історію одним повідомленням:\n"
                    "що сталося, що тебе зачепило, що хочеш донести людям"
                )
            return

        await update.message.reply_text("Оберіть варіант кнопкою")
        return

    # ── Крок 8: Очікування фото ──────────────────────────────────────────────
    if step == "reference_upload":
        await update.message.reply_text("Будь ласка, надішли саме фото, а не текст 🖼")
        return

    # ── Крок 9: Генерація ────────────────────────────────────────────────────
    if step == "content_input":
        language             = state["language"]
        mode                 = state["mode"]
        goal                 = state["goal"]
        tone                 = state["tone"]
        count                = state["count"]
        style                = state.get("style", DEFAULT_STYLE)
        reference_style_desc = state.get("reference_style_desc")

        if mode == "Тема":
            prompt = build_theme_prompt(text, language, goal, tone, count)
        else:
            prompt = build_story_prompt(text, language, goal, tone, count)

        await update.message.reply_text("⏳ Генерую сценарій...")

        try:
            reply = await generate_with_claude(prompt)
            await send_long_message(update, reply)

        except asyncio.TimeoutError:
            await update.message.reply_text("⏱ Claude відповідає занадто довго. Спробуй ще раз.")
            logger.warning("Claude timeout for user %s", user_id)
            return
        except Exception as e:
            logger.exception("Anthropic API error for user %s", user_id)
            await update.message.reply_text(f"❌ Помилка при генерації тексту: {e}")
            return

        # Генерація зображень
        slides = parse_slides(reply)
        if slides:
            await update.message.reply_text(f"🎨 Генерую {len(slides)} зображень...")

            for i, slide in enumerate(slides, start=1):
                try:
                    await update.message.reply_text(f"🖼 Слайд {i} з {len(slides)}...")
                    image_bytes = await build_slide(
                        slide_text=slide["text"],
                        what_to_show=slide["what_to_show"],
                        has_interactive=slide["has_interactive"],
                        style=style,
                        reference_style_desc=reference_style_desc,
                    )
                    if image_bytes:
                        await update.message.reply_photo(
                            photo=image_bytes,
                            caption=f"Слайд {i}: {slide['text']}",
                        )
                    else:
                        await update.message.reply_text(f"⚠️ Слайд {i}: не вдалося згенерувати зображення.")

                except Exception as e:
                    logger.error("Image generation error slide %s: %s", i, e)
                    await update.message.reply_text(f"⚠️ Слайд {i}: помилка — {e}")

        # Зберігаємо мову, все інше скидаємо
        reset_state(user_id, keep_language=True)
        await update.message.reply_text(
            "✅ Готово! Хочеш ще одну серію?",
            reply_markup=make_keyboard(MODES),
        )
        return

import logging
import asyncio

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
MessageHandler,
ContextTypes,
filters,
)
from anthropic import AsyncAnthropic

# =========================================

# ВСТАВ СВОЇ КЛЮЧІ

# =========================================

TELEGRAM_TOKEN = “PASTE_NEW_TELEGRAM_TOKEN_HERE” 
CLAUDE_API_KEY = “PASTE_NEW_CLAUDE_API_KEY_HERE”

# =========================================

# НАЛАШТУВАННЯ МОДЕЛІ

# =========================================

MODEL_NAME = “claude-haiku-4-5-20251001”

client = AsyncAnthropic(api_key=CLAUDE_API_KEY)

# =========================================

# ЛОГИ

# =========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)
logging.getLogger(“httpx”).setLevel(logging.WARNING)

# =========================================

# СТАНИ КОРИСТУВАЧІВ

# =========================================

user_data_store = {}

# =========================================

# КОНСТАНТИ

# =========================================

GOALS = [“Продаж”, “Залучення”, “Прогрів”, “Кейс”, “Відгук”, “Історія”]
TONES = [“Жорстко”, “Тепло”, “Експертно”, “Дружньо”, “Провокаційно”, “Продаюче”]
STORY_COUNTS = [“3”, “5”, “7”, “10”]
MODES = [“Тема”, “Моя історія”]
LANGUAGES = [“Українська”, “Русский”, “English”]

# =========================================

# ДОПОМІЖНІ ФУНКЦІЇ

# =========================================

def reset_state(user_id: int) -> None:
user_data_store[user_id] = {“step”: “language”}

def get_lang_instruction(lang: str) -> str:
if lang == “Українська”:
return “Пиши українською мовою.”
elif lang == “Русский”:
return “Пиши на русском языке.”
return “Write in English.”

def goal_instruction(goal: str) -> str:
mapping = {
“Продаж”: “Сфокусуй сторіс на продажі: увага → проблема → рішення → CTA.”,
“Залучення”: “Сфокусуй сторіс на залученні: питання, інтерактив, емоція, діалог.”,
“Прогрів”: “Сфокусуй сторіс на прогріві: довіра, історія, емоція, сенс, м’який перехід.”,
“Кейс”: “Сфокусуй сторіс на кейсі: ситуація → що зробили → результат → висновок.”,
“Відгук”: “Сфокусуй сторіс на відгуку: факт → доказ → емоція → результат.”,
“Історія”: “Сфокусуй сторіс на історії: хук → подія → емоція → сенс → CTA.”
}
return mapping.get(goal, “”)

def count_instruction(count: int) -> str:
if count == 3:
return “Побудуй дуже компактну серію: хук → суть → CTA.”
elif count == 5:
return “Побудуй збалансовану серію з 5 сторіс.”
elif count == 7:
return “Побудуй глибшу серію з інтригою, розвитком і завершенням.”
elif count == 10:
return “Побудуй повну серію з розгортанням історії, емоцією, доказом і CTA.”
return “”

def build_theme_prompt(theme: str, lang: str, goal: str, tone: str, count: int) -> str:
return f”””
Ти — сильний стратег і редактор Instagram Stories.

{get_lang_instruction(lang)}

ТЕМА:
{theme}

ЦІЛЬ:
{goal}
{goal_instruction(goal)}

ТОН:
{tone}

КІЛЬКІСТЬ СТОРІС:
{count}
{count_instruction(count)}

ЗАВДАННЯ:
Створи серію Instagram Stories на основі теми.

ВИКОРИСТОВУЙ:

- хук
- інтрига
- опитування
- проблема
- підсилення болю
- історія
- рішення
- доказ
- результат
- CTA
- догрів

ФОРМАТИ:

- говоряща голова
- селфі-відео
- фото + текст
- просто текст на фоні
- опитування (стікер)
- шкала
- question box
- скрін переписки
- відео без обличчя + текст
- before/after
- чеклист

КРИТИЧНІ ПРАВИЛА:

- пиши коротко
- текст для одного слайду = максимум 1–2 короткі фрази
- не роби довгих абзаців
- не пиши банально
- не роби всі сторіс однаковими
- підбирай структуру залежно від цілі
- тон має бути чітко відчутний
- кожен слайд має вести до наступного
- обов’язково вкажи, що саме зняти або показати
- перевір орфографію, пунктуацію і граматику перед фінальною відповіддю
- прибери канцелярит, воду і повтори
- пиши так, щоб це реально можна було прочитати в сторіс за 1–2 секунди

ФОРМАТ ВІДПОВІДІ:

Слайд 1:

- Роль:
- Формат:
- Текст: (не більше 18 слів)
- Що показати:
- Інтерактив:
- Мета слайду:

Слайд 2:

- Роль:
- Формат:
- Текст: (не більше 18 слів)
- Що показати:
- Інтерактив:
- Мета слайду:

І так далі до {count} слайдів.
“””.strip()

def build_story_prompt(story_text: str, lang: str, goal: str, tone: str, count: int) -> str:
return f”””
Ти — сильний сторітелінг-редактор для Instagram Stories.

{get_lang_instruction(lang)}

ІСТОРІЯ КОРИСТУВАЧА:
{story_text}

ЦІЛЬ:
{goal}
{goal_instruction(goal)}

ТОН:
{tone}

КІЛЬКІСТЬ СТОРІС:
{count}
{count_instruction(count)}

ЗАВДАННЯ:

1. Не вигадуй нову історію, а перетвори реальну історію користувача в серію сторіс.
1. Витягни з історії:

- головний факт
- головну емоцію
- найцікавіший момент
- можливий хук
- логічний CTA

1. Побудуй сторіс так, щоб вони тримали увагу і вели до цілі.
1. Тон має бути: {tone}
1. Не пиши шаблонно.

ФОРМАТИ:

- говоряща голова
- селфі-відео
- фото + текст
- просто текст на фоні
- опитування (стікер)
- шкала
- question box
- скрін переписки
- відео без обличчя + текст
- before/after
- чеклист

КРИТИЧНІ ПРАВИЛА:

- пиши коротко
- текст для одного слайду = максимум 1–2 короткі фрази
- не роби довгих абзаців
- не пиши банально
- перевір орфографію, пунктуацію і граматику перед фінальною відповіддю
- прибери повтори, воду і важкі формулювання
- пиши як для живих сторіс, а не як для статті
- у тексті має бути емоція, але без зайвої балаканини

ФОРМАТ ВІДПОВІДІ:

АНАЛІЗ:

- Головний факт:
- Головна емоція:
- Найцікавіший момент:
- Хук:
- CTA:

ПОТІМ СЕРІЯ СТОРІС:

Слайд 1:

- Роль:
- Формат:
- Текст: (не більше 18 слів)
- Що показати:
- Інтерактив:
- Мета слайду:

Слайд 2:

- Роль:
- Формат:
- Текст: (не більше 18 слів)
- Що показати:
- Інтерактив:
- Мета слайду:

І так далі до {count} слайдів.
“””.strip()

async def send_long_message(update: Update, text: str, chunk_size: int = 3500) -> None:
for i in range(0, len(text), chunk_size):
await update.message.reply_text(text[i:i + chunk_size])

async def generate_with_claude(prompt: str) -> str:
response = await asyncio.wait_for(
client.messages.create(
model=MODEL_NAME,
max_tokens=2200,  # FIX: було 900 — замало для 10 слайдів
messages=[{“role”: “user”, “content”: prompt}],
),
timeout=60  # FIX: збільшено таймаут під новий max_tokens
)

```
reply = "".join(
    block.text for block in response.content
    if getattr(block, "type", "") == "text" and getattr(block, "text", "")
).strip()

if not reply:
    return "Не вдалося отримати текстову відповідь від моделі."

return reply
```

# =========================================

# HANDLERS

# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
reset_state(user_id)

```
keyboard = [[lang] for lang in LANGUAGES]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

await update.message.reply_text(
    "Оберіть мову / Choose language / Выберите язык",
    reply_markup=reply_markup
)
```

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id
reset_state(user_id)
await start(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not update.message or not update.message.text:
return

```
user_id = update.effective_user.id
text = update.message.text.strip()

if user_id not in user_data_store:
    reset_state(user_id)

# FIX: прибрано зайву перевірку /start і /reset — вони обробляються CommandHandler'ами

state = user_data_store[user_id]
step = state.get("step")

if step == "language":
    if text not in LANGUAGES:
        await update.message.reply_text("Оберіть мову кнопкою")
        return

    state["language"] = text
    state["step"] = "mode"

    keyboard = [[m] for m in MODES]  # FIX: було 'mode' — перекривало змінну state["mode"]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Оберіть режим:", reply_markup=reply_markup)
    return

if step == "mode":
    if text not in MODES:
        await update.message.reply_text("Оберіть режим кнопкою")
        return

    state["mode"] = text
    state["step"] = "goal"

    keyboard = [[g] for g in GOALS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Оберіть ціль сторіс:", reply_markup=reply_markup)
    return

if step == "goal":
    if text not in GOALS:
        await update.message.reply_text("Оберіть ціль кнопкою")
        return

    state["goal"] = text
    state["step"] = "tone"

    keyboard = [[t] for t in TONES]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Оберіть тон:", reply_markup=reply_markup)
    return

if step == "tone":
    if text not in TONES:
        await update.message.reply_text("Оберіть тон кнопкою")
        return

    state["tone"] = text
    state["step"] = "count"

    keyboard = [[c] for c in STORY_COUNTS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Оберіть кількість сторіс:", reply_markup=reply_markup)
    return

if step == "count":
    if text not in STORY_COUNTS:
        await update.message.reply_text("Оберіть кількість кнопкою")
        return

    state["count"] = int(text)
    state["step"] = "content_input"

    if state["mode"] == "Тема":
        await update.message.reply_text("Напиши тему сторіс")
    else:
        await update.message.reply_text(
            "Напиши свою історію одним повідомленням: що сталося, що тебе зачепило, що хочеш донести людям"
        )
    return

if step == "content_input":
    language = state["language"]
    current_mode = state["mode"]
    goal = state["goal"]
    tone = state["tone"]
    count = state["count"]

    if current_mode == "Тема":
        prompt = build_theme_prompt(text, language, goal, tone, count)
    else:
        prompt = build_story_prompt(text, language, goal, tone, count)

    await update.message.reply_text("Генерую сторіс...")

    try:
        reply = await generate_with_claude(prompt)
        await send_long_message(update, reply)

    except asyncio.TimeoutError:
        await update.message.reply_text("Claude відповідає занадто довго. Спробуй ще раз.")
        logger.warning("Claude timeout for user %s", user_id)
        return

    except Exception as e:
        logger.exception("Anthropic API error")
        await update.message.reply_text(f"Сталася помилка при генерації: {e}")
        return

    state["step"] = "mode"
    keyboard = [[m] for m in MODES]  # FIX: було 'mode' — перекривало змінну current_mode
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Готово. Хочеш ще одну серію? Обери режим:",
        reply_markup=reply_markup
    )
    return
```

# =========================================

# MAIN

# =========================================

def main():
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(CommandHandler(“reset”, reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

```
print("Бот запущений")
app.run_polling()
```

if **name** == “**main**”:
main()
import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # ← твоя назва в Railway
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MODEL_NAME   = "claude-haiku-4-5-20251001"

GOALS        = ["Продаж", "Залучення", "Прогрів", "Кейс", "Відгук", "Історія"]
TONES        = ["Жорстко", "Тепло", "Експертно", "Дружньо", "Провокаційно", "Продаюче"]
STORY_COUNTS = ["3", "5", "7", "10"]
MODES        = ["Тема", "Моя історія"]
LANGUAGES    = ["Українська", "Русский", "English"]
RESET_BTN    = "🔄 Почати заново"
STYLES       = ["Мінімалізм", "Темний преміум", "Яскравий поп", "Пастельний", "Фото"]

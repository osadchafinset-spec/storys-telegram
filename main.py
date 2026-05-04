import logging

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN
from handlers import start, handle_message, handle_photo

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
   
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот запущений")
    app.run_polling()

if __name__ == "__main__":
    main()

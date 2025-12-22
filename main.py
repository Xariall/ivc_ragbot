"""
Точка входа для запуска RAG бота.
"""

import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from rag_bot import RAGBot, config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция для запуска бота."""
    # Создаем экземпляр бота
    rag_bot = RAGBot()
    
    # Создаем приложение Telegram
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", rag_bot.start_command))
    application.add_handler(CommandHandler("help", rag_bot.help_command))
    application.add_handler(CommandHandler("clear", rag_bot.clear_command))
    
    # Регистрируем обработчик документов
    application.add_handler(MessageHandler(filters.Document.ALL, rag_bot.handle_document))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, rag_bot.handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


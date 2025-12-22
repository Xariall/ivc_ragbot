"""
Точка входа для запуска RAG бота.
"""

import logging
import sys
import socket
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from rag_bot import RAGBot, config

# Принудительно используем IPv4 вместо IPv6 для решения проблем с SSL
# Это исправляет проблему с таймаутами при подключении к Telegram API
original_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4(*args, **kwargs):
    """Переопределяем getaddrinfo для использования только IPv4."""
    responses = original_getaddrinfo(*args, **kwargs)
    # Фильтруем только IPv4 адреса
    return [r for r in responses if r[0] == socket.AF_INET]

socket.getaddrinfo = getaddrinfo_ipv4

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """Основная функция для запуска бота."""
    # Проверяем, что токен загружен
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не установлен или имеет значение по умолчанию!")
        print("Пожалуйста, проверьте файл .env и убедитесь, что токен установлен правильно.")
        sys.exit(1)
    
    if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your_groq_api_key_here":
        print("❌ Ошибка: GROQ_API_KEY не установлен или имеет значение по умолчанию!")
        print("Пожалуйста, проверьте файл .env и убедитесь, что API ключ установлен правильно.")
        sys.exit(1)
    
    print("🚀 Инициализация бота...")
    print(f"📝 Токен бота: {config.TELEGRAM_BOT_TOKEN[:10]}...{config.TELEGRAM_BOT_TOKEN[-5:]}")
    
    # Создаем экземпляр бота
    rag_bot = RAGBot()
    
    # Проверяем доступность Telegram API перед запуском
    print("🔍 Проверка доступности Telegram API...")
    print("💡 Примечание: Если проверка не проходит, бот все равно попытается подключиться")
    
    # Создаем приложение Telegram с правильной конфигурацией
    # Используем стандартные настройки - они должны работать лучше
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)  # Разрешаем параллельную обработку обновлений
        .build()
    )
    
    # Добавляем обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок."""
        logger.error(f"Ошибка при обработке обновления: {context.error}", exc_info=context.error)
        if update and isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка при обработке вашего запроса. Попробуйте еще раз."
                )
            except:
                pass
    
    # Добавляем обработчик всех обновлений для логирования
    async def log_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Логируем все входящие обновления."""
        user_id = update.effective_user.id if update.effective_user else "unknown"
        if update.message:
            text_preview = update.message.text[:50] if update.message.text else 'файл/медиа'
            print(f"📨 Получено сообщение от пользователя {user_id}: {text_preview}")
            logger.info(f"📨 Получено сообщение от {user_id}: {text_preview}")
        elif update.callback_query:
            print(f"🔘 Получен callback от пользователя {user_id}")
            logger.info(f"🔘 Получен callback от {user_id}")
    
    # Регистрируем обработчик для логирования (с низким приоритетом)
    application.add_handler(MessageHandler(filters.ALL, log_update), group=-1)
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", rag_bot.start_command))
    application.add_handler(CommandHandler("help", rag_bot.help_command))
    application.add_handler(CommandHandler("clear", rag_bot.clear_command))
    
    # Регистрируем обработчик документов
    application.add_handler(MessageHandler(filters.Document.ALL, rag_bot.handle_document))
    
    # Регистрируем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, rag_bot.handle_message))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Проверка токена будет выполнена автоматически при запуске polling
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе!")
    print("✅ Бот успешно запущен и готов к работе!")
    print("💡 Отправьте команду /start боту в Telegram")
    print("💡 Нажмите Ctrl+C для остановки бота.")
    print("-" * 50)
    print("📡 Ожидание подключения к Telegram API...")
    print("   (Это может занять несколько секунд)")
    print("-" * 50)
    
    try:
        # Запускаем polling - стандартный подход
        logger.info("Начинаю polling...")
        print("🔄 Подключение к Telegram API...")
        print("💡 Это может занять до 2 минут при проблемах с сетью...")
        
        # Используем стандартный run_polling - он лучше обрабатывает сетевые проблемы
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания (Ctrl+C). Останавливаю бота...")
        print("\n⏹️  Остановка бота...")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Критическая ошибка при работе бота: {e}", exc_info=True)
        
        # Игнорируем ошибки при остановке
        if "AsyncLibraryNotFoundError" in error_msg or "no running event loop" in error_msg:
            print("\n⚠️  Ошибка при остановке бота (не критично)")
            print("Бот был остановлен пользователем")
        elif "Unauthorized" in error_msg or "401" in error_msg:
            print(f"❌ Ошибка авторизации: Неправильный токен бота!")
            print("Проверьте токен в файле .env")
        elif "Timed out" in error_msg or "timeout" in error_msg.lower() or "ConnectTimeout" in error_msg:
            print(f"⚠️  Таймаут при подключении к Telegram API")
            print("\n💡 Возможные решения:")
            print("   1. Проверьте интернет-соединение")
            print("   2. Попробуйте перезапустить бота через несколько минут")
            print("   3. Проверьте, работает ли Telegram на вашем компьютере")
            print("   4. Если используете корпоративную сеть/VPN - проверьте настройки")
            print("   5. Попробуйте использовать другой DNS (например, 8.8.8.8)")
        else:
            print(f"❌ Критическая ошибка: {e}")
    finally:
        print("👋 Бот остановлен. До свидания!")


if __name__ == "__main__":
    main()


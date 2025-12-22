"""
Конфигурационный файл для RAG бота.
Загружает переменные окружения и настраивает параметры системы.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
    print("⚠️  ВНИМАНИЕ: TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
    print("   Создайте файл .env и добавьте: TELEGRAM_BOT_TOKEN=ваш_токен")
    print("   Получить токен можно у @BotFather в Telegram")
    # Не падаем сразу, чтобы можно было проверить в main.py

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
    print("⚠️  ВНИМАНИЕ: GROQ_API_KEY не найден в переменных окружения!")
    print("   Создайте файл .env и добавьте: GROQ_API_KEY=ваш_ключ")
    print("   Получить ключ можно на https://console.groq.com/")
    # Не падаем сразу, чтобы можно было проверить в main.py

# Параметры обработки документов
CHUNK_SIZE = 1000  # Размер чанка в символах
CHUNK_OVERLAP = 200  # Перекрытие между чанками в символах

# Путь к базе данных ChromaDB
CHROMA_DB_PATH = "./chroma_db"

# Модель для эмбеддингов (легкая и быстрая модель от Sentence Transformers)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Модель Groq для генерации ответов
GROQ_MODEL = "llama-3.1-8b-instant"  # Быстрая модель, можно изменить на llama-3.1-70b-versatile для лучшего качества


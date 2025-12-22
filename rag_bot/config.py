"""
Конфигурационный файл для RAG бота.
Загружает переменные окружения и настраивает параметры системы.
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

# Groq API Key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не найден в переменных окружения!")

# Параметры обработки документов
CHUNK_SIZE = 1000  # Размер чанка в символах
CHUNK_OVERLAP = 200  # Перекрытие между чанками в символах

# Путь к базе данных ChromaDB
CHROMA_DB_PATH = "./chroma_db"

# Модель для эмбеддингов (легкая и быстрая модель от Sentence Transformers)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Модель Groq для генерации ответов
GROQ_MODEL = "llama-3.1-8b-instant"  # Быстрая модель, можно изменить на llama-3.1-70b-versatile для лучшего качества


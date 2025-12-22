"""
Основной файл Telegram бота с RAG функциональностью.
Обрабатывает сообщения, загружает документы и генерирует ответы.
"""

import os
import logging
from typing import Dict
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Импортируем наши модули
from . import config
from .document_processor import DocumentProcessor
from .vector_store import VectorStore

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class RAGBot:
    """
    Класс RAG бота для Telegram.
    Управляет обработкой документов, поиском и генерацией ответов.
    """
    
    def __init__(self):
        """Инициализация бота."""
        # Инициализируем компоненты
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore(
            db_path=config.CHROMA_DB_PATH,
            embedding_model=config.EMBEDDING_MODEL
        )
        
        # Инициализируем LLM от Groq
        self.llm = ChatGroq(
            groq_api_key=config.GROQ_API_KEY,
            model_name=config.GROQ_MODEL,
            temperature=0.7
        )
        
        # Словарь для хранения памяти диалогов по пользователям
        # Каждый пользователь имеет свою память (список сообщений)
        self.memories: Dict[int, list] = {}
        
        # Временное хранилище для загружаемых файлов
        self.temp_files: Dict[int, str] = {}
    
    def get_memory(self, user_id: int) -> list:
        """
        Получает историю диалога для пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Список сообщений (история диалога)
        """
        if user_id not in self.memories:
            self.memories[user_id] = []
        return self.memories[user_id]
    
    def clear_memory(self, user_id: int) -> None:
        """
        Очищает память диалога пользователя.
        
        Args:
            user_id: ID пользователя Telegram
        """
        if user_id in self.memories:
            del self.memories[user_id]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /start.
        Приветствует пользователя и объясняет, как использовать бота.
        """
        user_id = update.effective_user.id
        welcome_message = (
            "👋 Привет! Я RAG-бот, который может помочь вам найти информацию в ваших документах.\n\n"
            "📋 Как использовать:\n"
            "1. Отправьте мне документ (PDF, TXT или DOCX)\n"
            "2. Дождитесь подтверждения обработки\n"
            "3. Задавайте вопросы по содержимому документа\n\n"
            "💡 Команды:\n"
            "/start - Начать работу\n"
            "/clear - Очистить загруженные документы и память\n"
            "/help - Показать эту справку"
        )
        await update.message.reply_text(welcome_message)
        logger.info(f"Пользователь {user_id} запустил бота")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /help.
        Показывает справку по использованию бота.
        """
        help_message = (
            "📚 Справка по использованию бота:\n\n"
            "📄 Загрузка документов:\n"
            "Просто отправьте файл в формате PDF, TXT или DOCX.\n"
            "Бот автоматически обработает его и создаст векторное представление.\n\n"
            "❓ Задавание вопросов:\n"
            "После загрузки документа просто напишите ваш вопрос обычным текстом.\n"
            "Бот найдет релевантную информацию и сгенерирует ответ.\n\n"
            "🔄 Память диалога:\n"
            "Бот помнит контекст вашего разговора, поэтому вы можете задавать уточняющие вопросы.\n\n"
            "🗑️ Очистка:\n"
            "Используйте /clear для удаления всех загруженных документов и очистки памяти."
        )
        await update.message.reply_text(help_message)
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик команды /clear.
        Очищает загруженные документы и память диалога пользователя.
        """
        user_id = update.effective_user.id
        
        # Очищаем векторную базу данных
        self.vector_store.clear_user_collection(user_id)
        
        # Очищаем память диалога
        self.clear_memory(user_id)
        
        # Удаляем временные файлы
        if user_id in self.temp_files:
            temp_file = self.temp_files[user_id]
            if os.path.exists(temp_file):
                os.remove(temp_file)
            del self.temp_files[user_id]
        
        await update.message.reply_text(
            "✅ Все документы и память диалога очищены. "
            "Вы можете загрузить новые документы."
        )
        logger.info(f"Пользователь {user_id} очистил данные")
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик загрузки документов.
        Принимает файл, обрабатывает его и сохраняет в векторную БД.
        """
        user_id = update.effective_user.id
        document = update.message.document
        
        if not document:
            await update.message.reply_text("❌ Не удалось получить файл. Попробуйте еще раз.")
            return
        
        file_name = document.file_name
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Проверяем формат файла
        if file_ext not in ['.pdf', '.txt', '.docx']:
            await update.message.reply_text(
                "❌ Неподдерживаемый формат файла. "
                "Поддерживаются: PDF, TXT, DOCX"
            )
            return
        
        # Отправляем сообщение о начале обработки
        processing_msg = await update.message.reply_text(
            f"⏳ Обрабатываю файл {file_name}...\n"
            "Это может занять некоторое время."
        )
        
        try:
            # Скачиваем файл
            file = await context.bot.get_file(document.file_id)
            temp_file_path = f"./temp_{user_id}_{file_name}"
            await file.download_to_drive(temp_file_path)
            
            # Сохраняем путь к временному файлу
            if user_id in self.temp_files:
                old_file = self.temp_files[user_id]
                if os.path.exists(old_file):
                    os.remove(old_file)
            self.temp_files[user_id] = temp_file_path
            
            # Извлекаем текст из документа
            logger.info(f"Извлечение текста из {file_name} для пользователя {user_id}")
            text = self.document_processor.extract_text(temp_file_path)
            
            if not text or len(text.strip()) < 50:
                await processing_msg.edit_text(
                    "❌ Не удалось извлечь текст из документа или документ слишком короткий."
                )
                return
            
            # Разбиваем текст на чанки
            logger.info(f"Разбивка текста на чанки для пользователя {user_id}")
            chunks = self.document_processor.split_text_into_chunks(
                text,
                chunk_size=config.CHUNK_SIZE,
                chunk_overlap=config.CHUNK_OVERLAP
            )
            
            if not chunks:
                await processing_msg.edit_text("❌ Не удалось разбить документ на части.")
                return
            
            # Очищаем старую коллекцию пользователя перед добавлением нового документа
            self.vector_store.clear_user_collection(user_id)
            
            # Добавляем чанки в векторную БД
            logger.info(f"Добавление {len(chunks)} чанков в БД для пользователя {user_id}")
            self.vector_store.add_documents(
                user_id,
                chunks,
                metadatas=[{"source": file_name, "chunk_index": i} for i in range(len(chunks))]
            )
            
            # Очищаем память диалога при загрузке нового документа
            self.clear_memory(user_id)
            
            await processing_msg.edit_text(
                f"✅ Документ '{file_name}' успешно обработан!\n\n"
                f"📊 Статистика:\n"
                f"• Извлечено символов: {len(text)}\n"
                f"• Создано чанков: {len(chunks)}\n\n"
                f"Теперь вы можете задавать вопросы по содержимому документа."
            )
            logger.info(f"Документ {file_name} успешно обработан для пользователя {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке документа: {e}", exc_info=True)
            await processing_msg.edit_text(
                f"❌ Ошибка при обработке документа: {str(e)}\n"
                "Попробуйте загрузить файл еще раз или проверьте формат."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обработчик текстовых сообщений (вопросов пользователя).
        Выполняет поиск в векторной БД и генерирует ответ.
        """
        user_id = update.effective_user.id
        question = update.message.text
        
        if not question or len(question.strip()) < 3:
            await update.message.reply_text(
                "❓ Пожалуйста, задайте вопрос (минимум 3 символа)."
            )
            return
        
        # Проверяем, есть ли документы у пользователя
        doc_count = self.vector_store.get_collection_count(user_id)
        if doc_count == 0:
            await update.message.reply_text(
                "📄 Сначала загрузите документ, чтобы я мог ответить на ваши вопросы.\n"
                "Отправьте файл в формате PDF, TXT или DOCX."
            )
            return
        
        # Отправляем сообщение о том, что бот думает
        thinking_msg = await update.message.reply_text("🤔 Думаю...")
        
        try:
            # Выполняем поиск релевантных чанков
            logger.info(f"Поиск релевантных чанков для вопроса пользователя {user_id}")
            search_results = self.vector_store.search(user_id, question, n_results=3)
            
            if not search_results:
                await thinking_msg.edit_text(
                    "❌ Не удалось найти релевантную информацию в документах.\n"
                    "Попробуйте переформулировать вопрос."
                )
                return
            
            # Формируем контекст из найденных чанков
            context = "\n\n".join([result['document'] for result in search_results])
            
            # Получаем память диалога
            chat_history = self.get_memory(user_id)
            
            # Формируем системный промпт с контекстом
            system_prompt = (
                "Ты - полезный AI-ассистент, который отвечает на вопросы пользователей "
                "на основе предоставленного контекста из документов.\n\n"
                "Инструкции:\n"
                "1. Отвечай ТОЛЬКО на основе предоставленного контекста\n"
                "2. Если в контексте нет информации для ответа, честно скажи об этом\n"
                "3. Отвечай на русском языке\n"
                "4. Будь точным и информативным\n"
                "5. Используй контекст предыдущих сообщений для лучшего понимания\n\n"
                f"Контекст из документов:\n{context}"
            )
            
            # Формируем список сообщений для LLM (используем объекты LangChain)
            messages = [SystemMessage(content=system_prompt)]
            
            # Добавляем историю диалога (последние 6 пар вопрос-ответ)
            for msg in chat_history[-6:]:
                if isinstance(msg, HumanMessage):
                    messages.append(msg)
                elif isinstance(msg, AIMessage):
                    messages.append(msg)
                elif isinstance(msg, dict):
                    # Поддержка старого формата (словари)
                    if msg.get("role") == "user":
                        messages.append(HumanMessage(content=msg.get("content", "")))
                    elif msg.get("role") == "assistant":
                        messages.append(AIMessage(content=msg.get("content", "")))
            
            # Добавляем текущий вопрос
            messages.append(HumanMessage(content=question))
            
            # Генерируем ответ
            logger.info(f"Генерация ответа для пользователя {user_id}")
            response = self.llm.invoke(messages)
            answer = response.content if hasattr(response, 'content') else str(response)
            
            # Сохраняем вопрос и ответ в память (используем объекты LangChain)
            chat_history.append(HumanMessage(content=question))
            chat_history.append(AIMessage(content=answer))
            
            # Ограничиваем размер истории (храним последние 10 сообщений)
            if len(chat_history) > 10:
                chat_history = chat_history[-10:]
                self.memories[user_id] = chat_history
            
            # Отправляем ответ пользователю
            await thinking_msg.edit_text(answer)
            logger.info(f"Ответ отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}", exc_info=True)
            await thinking_msg.edit_text(
                f"❌ Произошла ошибка при генерации ответа: {str(e)}\n"
                "Попробуйте задать вопрос еще раз."
            )


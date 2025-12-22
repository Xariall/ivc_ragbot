"""
Модуль для работы с векторной базой данных ChromaDB.
Создает эмбеддинги текстов и выполняет семантический поиск.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import uuid


class VectorStore:
    """
    Класс для работы с векторной базой данных ChromaDB.
    Создает и хранит эмбеддинги документов, выполняет поиск.
    """
    
    def __init__(self, db_path: str = "./chroma_db", embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Инициализация векторного хранилища.
        
        Args:
            db_path: Путь к директории базы данных ChromaDB
            embedding_model: Название модели для создания эмбеддингов
        """
        self.db_path = db_path
        self.embedding_model_name = embedding_model
        
        # Инициализируем модель для эмбеддингов
        print(f"Загрузка модели эмбеддингов: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        print("Модель загружена!")
        
        # Инициализируем клиент ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Словарь для хранения коллекций по пользователям
        # Каждый пользователь имеет свою коллекцию
        self.collections: Dict[int, chromadb.Collection] = {}
    
    def get_or_create_collection(self, user_id: int) -> chromadb.Collection:
        """
        Получает или создает коллекцию для пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Коллекция ChromaDB для пользователя
        """
        if user_id not in self.collections:
            collection_name = f"user_{user_id}"
            try:
                # Пытаемся получить существующую коллекцию
                collection = self.client.get_collection(name=collection_name)
            except:
                # Если коллекции нет, создаем новую
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"user_id": user_id}
                )
            self.collections[user_id] = collection
        
        return self.collections[user_id]
    
    def add_documents(self, user_id: int, chunks: List[str], metadatas: Optional[List[Dict]] = None) -> None:
        """
        Добавляет документы (чанки) в векторную базу данных.
        
        Args:
            user_id: ID пользователя Telegram
            chunks: Список текстовых чанков для добавления
            metadatas: Опциональные метаданные для каждого чанка
        """
        if not chunks:
            return
        
        collection = self.get_or_create_collection(user_id)
        
        # Создаем эмбеддинги для всех чанков
        print(f"Создание эмбеддингов для {len(chunks)} чанков...")
        embeddings = self.embedding_model.encode(chunks, show_progress_bar=True).tolist()
        
        # Генерируем уникальные ID для каждого чанка
        ids = [str(uuid.uuid4()) for _ in chunks]
        
        # Подготавливаем метаданные, если они не предоставлены
        if metadatas is None:
            metadatas = [{"chunk_index": i} for i in range(len(chunks))]
        
        # Добавляем документы в коллекцию
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Добавлено {len(chunks)} чанков в базу данных для пользователя {user_id}")
    
    def search(self, user_id: int, query: str, n_results: int = 3) -> List[Dict]:
        """
        Выполняет семантический поиск релевантных чанков по запросу.
        
        Args:
            user_id: ID пользователя Telegram
            query: Текстовый запрос для поиска
            n_results: Количество результатов для возврата
            
        Returns:
            Список словарей с найденными чанками и их метаданными
        """
        collection = self.get_or_create_collection(user_id)
        
        # Создаем эмбеддинг для запроса
        query_embedding = self.embedding_model.encode([query]).tolist()[0]
        
        # Выполняем поиск в коллекции
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Форматируем результаты
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None
                })
        
        return formatted_results
    
    def clear_user_collection(self, user_id: int) -> None:
        """
        Очищает коллекцию документов пользователя.
        
        Args:
            user_id: ID пользователя Telegram
        """
        collection_name = f"user_{user_id}"
        try:
            self.client.delete_collection(name=collection_name)
            if user_id in self.collections:
                del self.collections[user_id]
            print(f"Коллекция пользователя {user_id} очищена")
        except Exception as e:
            print(f"Ошибка при очистке коллекции: {e}")
    
    def get_collection_count(self, user_id: int) -> int:
        """
        Возвращает количество документов в коллекции пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            
        Returns:
            Количество документов в коллекции
        """
        try:
            collection = self.get_or_create_collection(user_id)
            return collection.count()
        except:
            return 0


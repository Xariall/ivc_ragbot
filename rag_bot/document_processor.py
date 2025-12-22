"""
Модуль для обработки документов различных форматов.
Поддерживает PDF, TXT и DOCX файлы.
"""

import os
from typing import List
from pathlib import Path

# Импорты для обработки разных форматов
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentProcessor:
    """
    Класс для обработки документов различных форматов.
    Извлекает текст из PDF, TXT и DOCX файлов.
    """
    
    def __init__(self):
        """Инициализация процессора документов."""
        self.supported_formats = ['.pdf', '.txt', '.docx']
    
    def is_supported(self, file_path: str) -> bool:
        """
        Проверяет, поддерживается ли формат файла.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True, если формат поддерживается, иначе False
        """
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_formats
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Извлекает текст из PDF файла.
        
        Args:
            file_path: Путь к PDF файлу
            
        Returns:
            Извлеченный текст
        """
        if PdfReader is None:
            raise ImportError("pypdf не установлен. Установите: pip install pypdf")
        
        text = ""
        try:
            reader = PdfReader(file_path)
            # Проходим по всем страницам и извлекаем текст
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Ошибка при чтении PDF: {str(e)}")
        
        return text.strip()
    
    def extract_text_from_txt(self, file_path: str) -> str:
        """
        Извлекает текст из TXT файла.
        
        Args:
            file_path: Путь к TXT файлу
            
        Returns:
            Извлеченный текст
        """
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'cp1251', 'latin-1']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read().strip()
                except UnicodeDecodeError:
                    continue
            raise Exception("Не удалось определить кодировку файла")
        except Exception as e:
            raise Exception(f"Ошибка при чтении TXT: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """
        Извлекает текст из DOCX файла.
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Извлеченный текст
        """
        if Document is None:
            raise ImportError("python-docx не установлен. Установите: pip install python-docx")
        
        try:
            doc = Document(file_path)
            text = ""
            # Извлекаем текст из всех параграфов
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Ошибка при чтении DOCX: {str(e)}")
    
    def extract_text(self, file_path: str) -> str:
        """
        Извлекает текст из файла любого поддерживаемого формата.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Извлеченный текст
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if not self.is_supported(file_path):
            raise ValueError(f"Неподдерживаемый формат файла: {Path(file_path).suffix}")
        
        file_ext = Path(file_path).suffix.lower()
        
        # Выбираем метод извлечения в зависимости от формата
        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext == '.txt':
            return self.extract_text_from_txt(file_path)
        elif file_ext == '.docx':
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {file_ext}")
    
    def split_text_into_chunks(self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Разбивает текст на чанки с перекрытием.
        
        Args:
            text: Текст для разбивки
            chunk_size: Размер чанка в символах
            chunk_overlap: Перекрытие между чанками в символах
            
        Returns:
            Список текстовых чанков
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        # Разбиваем текст на чанки
        while start < len(text):
            # Определяем конец текущего чанка
            end = start + chunk_size
            
            # Если это не последний чанк, пытаемся разбить по предложению
            if end < len(text):
                # Ищем ближайшую точку, восклицательный или вопросительный знак
                for punct in ['. ', '! ', '? ', '\n\n', '\n']:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct != -1:
                        end = last_punct + len(punct)
                        break
            
            # Извлекаем чанк
            chunk = text[start:end].strip()
            if chunk:  # Добавляем только непустые чанки
                chunks.append(chunk)
            
            # Перемещаемся на следующий чанк с учетом перекрытия
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return chunks


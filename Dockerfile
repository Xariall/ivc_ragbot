# Многоступенчатая сборка для оптимизации размера образа
FROM python:3.12-slim as builder

# Устанавливаем системные зависимости для сборки пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.12-slim

# Устанавливаем только runtime зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из builder
COPY --from=builder /root/.local /root/.local

# Убеждаемся, что скрипты в PATH
ENV PATH=/root/.local/bin:$PATH

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем код приложения
COPY . .

# Создаем директории для данных
RUN mkdir -p /app/chroma_db /app/temp_files

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Ограничиваем использование памяти для предотвращения OOM
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Запускаем бота
CMD ["python", "main.py"]


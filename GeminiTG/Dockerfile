FROM python:3.10-slim

# Установка рабочей директории
WORKDIR /app

# Копирование файлов
COPY . .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для Flask (HF Spaces требует 7860)
EXPOSE 7860

# Запуск бота
CMD ["python", "main.py"]
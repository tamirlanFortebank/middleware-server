from fastapi import FastAPI, Request
from mistralai.client import MistralClient
import os
from dotenv import load_dotenv
import redis
import hashlib
import json

# Загружаем переменные окружения
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # Параметры для Redis
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

# Создаем экземпляры клиентов
app = FastAPI()
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# Функция кеширования с использованием Redis
def get_cached_response(query: str):
    query_hash = hashlib.sha256(query.encode()).hexdigest()  # Создаем уникальный ключ
    cached_response = redis_client.get(query_hash)  # Пытаемся найти ответ в кеше
    if cached_response:
        return json.loads(cached_response)  # Декодируем из JSON
    return None

def cache_response(query: str, response: str):
    query_hash = hashlib.sha256(query.encode()).hexdigest()  # Генерация уникального ключа
    redis_client.setex(query_hash, 3600, json.dumps(response))  # Сохраняем в кеше на 1 час

# Middleware для обработки запросов
@app.middleware("http")
async def middleware(request: Request, call_next):
    data = await request.json()
    user_text = data.get("Body", "").lower()

    # Проверяем, есть ли в запросе банковские термины
    bank_keywords = ["баланс", "кредит", "карта", "блокировка"]
    if any(word in user_text for word in bank_keywords):
        response_content = {"response": "Обратитесь в приложение банка для получения информации."}
    else:
        # Пытаемся получить кешированный ответ
        cached_response = get_cached_response(user_text)
        if cached_response:
            return cached_response  # Отдаем кешированный ответ

        # Отправляем запрос в Mistral API
        ai_response = mistral_client.chat(
            model="mistral-tiny",
            messages=[{"role": "user", "content": user_text}]
        )
        response_content = {"response": ai_response.choices[0].message.content}

        # Кешируем ответ на 1 час
        cache_response(user_text, response_content)

    return response_content


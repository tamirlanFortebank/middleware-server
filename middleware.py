from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mistralai.client import MistralClient
import os
from dotenv import load_dotenv
import redis
import hashlib
import json

# Загружаем переменные окружения
load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Подключение к Redis
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    print("✅ Подключено к Redis")
except Exception as e:
    print(f"❌ Ошибка подключения к Redis: {e}")
    redis_client = None

# Инициализация FastAPI и Mistral
app = FastAPI()
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# Функции кеширования
def get_cached_response(query: str):
    if redis_client:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cached_response = redis_client.get(query_hash)
        if cached_response:
            return json.loads(cached_response)
    return None

def cache_response(query: str, response: dict):
    if redis_client:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        redis_client.setex(query_hash, 3600, json.dumps(response))

# Middleware для обработки запросов
@app.middleware("http")
async def middleware(request: Request, call_next):
    try:
        data = await request.json()
        user_text = data.get("Body", "").strip().lower()

        # Проверяем, есть ли в запросе банковские термины
        bank_keywords = ["баланс", "кредит", "карта", "блокировка"]
        if any(word in user_text for word in bank_keywords):
            return JSONResponse({"response": "Обратитесь в приложение банка для получения информации."})

        # Проверяем кеш
        cached_response = get_cached_response(user_text)
        if cached_response:
            return JSONResponse(cached_response)

        # Отправляем запрос в Mistral AI
        ai_response = mistral_client.chat(
            model="mistral-tiny",
            messages=[{"role": "user", "content": user_text}]
        )
        response_content = {"response": ai_response.choices[0].message.content}

        # Кешируем ответ
        cache_response(user_text, response_content)

        return JSONResponse(response_content)
    except Exception as e:
        print(f"❌ Ошибка обработки запроса: {e}")
        return JSONResponse({"response": "❌ Ошибка! Попробуйте позже."}, status_code=500)


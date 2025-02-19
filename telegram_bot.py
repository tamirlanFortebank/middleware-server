import telebot
from mistralai.client import MistralClient
from telebot import types
import os
import redis
import hashlib
import json
# Перезапуск бота
print("Перезапуск")
# Загружаем переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "redis-18492.c259.us-central1-2.gce.redns.redis-cloud.com")
REDIS_PORT = int(os.getenv("REDIS_PORT", 18492))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Проверяем переменные окружения
if not TELEGRAM_TOKEN:
    raise ValueError("❌ Ошибка: TELEGRAM_TOKEN не загружен! Проверь переменные окружения Railway.")

if not MISTRAL_API_KEY:
    raise ValueError("❌ Ошибка: MISTRAL_API_KEY не загружен! Проверь переменные окружения Railway.")

# Подключение к Redis
try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
    redis_client.ping()
    print("✅ Подключено к Redis")
except Exception as e:
    print(f"❌ Ошибка подключения к Redis: {e}")
    redis_client = None

# Инициализируем бота и Mistral AI
bot = telebot.TeleBot(TELEGRAM_TOKEN)
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# Функция кеширования ответов в Redis
def get_cached_response(query: str):
    if redis_client:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cached_response = redis_client.get(query_hash)
        if cached_response:
            return json.loads(cached_response)["response"]
    return None

def cache_response(query: str, response: str):
    if redis_client:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        redis_client.setex(query_hash, 3600, json.dumps({"response": response}))  # Кеш на 1 час

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["💰 Узнать баланс", "💳 Получить кредит", "🚫 Блокировка карты", "🗣 Просто поговорить"]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])

    welcome_text = """
    👋 Привет! Я AI-бот, и я здесь, чтобы помочь тебе с вопросами о банке и не только! 😊
    📲 Напиши мне свой вопрос, и я постараюсь дать лучший ответ.
    """
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text.strip()

    try:
        # Проверяем кеш
        cached_response = get_cached_response(user_text)
        if cached_response:
            bot.reply_to(message, cached_response)
            return

        # Отправляем запрос в Mistral AI
        print(f"🔹 Отправляю запрос в Mistral AI: {user_text}")

        ai_response = mistral_client.chat(
            model="mistral-tiny",
            messages=[{"role": "user", "content": user_text}]
        )
        
        bot_response = ai_response.choices[0].message.content.strip()
        print(f"🔹 Ответ от Mistral: {bot_response}")

        # Сохраняем ответ в кеш
        cache_response(user_text, bot_response)

        bot.reply_to(message, bot_response)

    except Exception as e:
        bot.reply_to(message, "❌ Ошибка! Что-то пошло не так.")
        print(f"❌ Ошибка: {e}")

# Запуск бота
bot.polling(none_stop=True)


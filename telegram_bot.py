import telebot
from mistralai.client import MistralClient
from telebot import types
import os
import redis

# Загружаем переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Настройка Redis (используем данные с Railway)
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=int(REDIS_PORT),
    password=REDIS_PASSWORD,
    decode_responses=True
)

# Инициализируем бота и Mistral
bot = telebot.TeleBot(TELEGRAM_TOKEN)
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

import telebot
from mistralai.client import MistralClient
from telebot import types
import os
import redis
import hashlib
import json
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")  # Параметры для Redis
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

# Инициализируем Telegram-бота и Mistral клиента
bot = telebot.TeleBot(TELEGRAM_TOKEN)
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

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Узнать баланс")
    item2 = types.KeyboardButton("Получить кредит")
    item3 = types.KeyboardButton("Потеря карты / Блокировка карты")
    item4 = types.KeyboardButton("Просто поговорить")
    markup.add(item1, item2, item3, item4)

    welcome_text = """
    Привет! Я AI-бот, и я здесь, чтобы помочь тебе с вопросами о банке. 😊
    📲 Напиши мне свой вопрос, и я постараюсь дать на него лучший ответ. 
    Если тебе нужно что-то конкретное, выбери одну из опций ниже:
    """

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# Обработчик всех текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_text = message.text.lower()

    try:
        # Проверяем, есть ли в запросе банковские термины
        bank_keywords = ["баланс", "кредит", "карта", "блокировка"]
        if any(word in user_text for word in bank_keywords):
            bot_response = "Обратитесь в приложение банка для получения информации."
        else:
            # Пытаемся получить кешированный ответ
            cached_response = get_cached_response(user_text)
            if cached_response:
                bot_response = cached_response['response']
            else:
                # Отправляем запрос в Mistral API
                ai_response = mistral_client.chat(
                    model="mistral-tiny",
                    messages=[{"role": "user", "content": user_text}]
                )
                bot_response = ai_response.choices[0].message.content

                # Кешируем ответ на 1 час
                cache_response(user_text, {"response": bot_response})

        bot.reply_to(message, bot_response)

    except Exception as e:
        bot.reply_to(message, "Ошибка! Что-то пошло не так. 😢")
        print(e)

# Запуск бота
bot.polling(none_stop=True)

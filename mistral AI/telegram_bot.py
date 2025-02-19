import os
from dotenv import load_dotenv
import telebot
from flask import Flask, request
from mistralai.client import MistralClient
from telebot import types

# Загружаем переменные окружения
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Railway URL

bot = telebot.TeleBot(TELEGRAM_TOKEN)
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Бот работает!"

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json()
    bot.process_new_updates([telebot.types.Update.de_json(json_data)])
    return "OK", 200

# Устанавливаем Webhook при запуске
@app.before_first_request
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")

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
        if message.text == "Узнать баланс":
            bot_response = "Для получения информации о балансе, пожалуйста, войдите в свой личный кабинет или используйте мобильное приложение."
        elif message.text == "Получить кредит":
            bot_response = "Чтобы узнать информацию о доступных кредитах, перейдите по ссылке на сайт банка или позвоните в наш контактный центр."
        elif message.text == "Потеря карты / Блокировка карты":
            bot_response = "Если вы потеряли карту, немедленно заблокируйте ее через мобильное приложение или позвоните в службу поддержки."
        elif message.text == "Просто поговорить":
            bot_response = "Конечно, я готов поговорить с вами! Напишите что-нибудь, и я постараюсь ответить."
        else:
            response = mistral_client.chat(
                model="mistral-tiny",
                messages=[{"role": "system", "content": "Отвечай пользователю только на русском языке."},
                          {"role": "user", "content": message.text}]
            )
            bot_response = response.choices[0].message.content

        bot.reply_to(message, bot_response)

    except Exception as e:
        bot.reply_to(message, "Ошибка! Что-то пошло не так. 😢")
        print(e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

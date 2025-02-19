from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os
from dotenv import load_dotenv
from mistralai.client import MistralClient

# Загружаем переменные окружения
load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Инициализация Flask и Mistral AI
app = Flask(__name__)
mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_bot():
    """Обрабатывает входящие сообщения WhatsApp через Twilio"""
    incoming_msg = request.values.get('Body', '').strip().lower()
    response = MessagingResponse()
    msg = response.message()

    try:
        # Обработка банковских запросов
        if "баланс" in incoming_msg:
            bot_response = "Для проверки баланса войдите в приложение банка."
        elif "кредит" in incoming_msg:
            bot_response = "Для информации о кредитах посетите сайт банка."
        elif "блокировка" in incoming_msg or "заблокировать карту" in incoming_msg:
            bot_response = "Срочно позвоните в службу поддержки для блокировки карты."
        else:
            # AI-ответ через Mistral
            ai_response = mistral_client.chat(
                model="mistral-tiny",
                messages=[{"role": "user", "content": incoming_msg}]
            )
            bot_response = ai_response.choices[0].message.content.strip()
        
        msg.body(bot_response)

    except Exception as e:
        msg.body("Ошибка! Что-то пошло не так. 😢")
        print(f"❌ Ошибка: {e}")

    return str(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

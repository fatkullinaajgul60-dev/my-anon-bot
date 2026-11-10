import os
import threading
from flask import Flask
import telebot

TOKEN = '9072613366:AAHh1HNYzXPLkA3imN40amzaF-SzOwGWV4A'
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот успешно запущен и работает в облаке 24/7.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.reply_to(message, f"Сообщение получено: {message.text}")

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    print("Бот успешно запущен!")
    bot.infinity_polling()

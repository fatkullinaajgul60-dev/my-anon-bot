import os
import telebot

TOKEN = '9072613366:AAHh1HNYzXPLkA3imN40amzaF-SzOwGWV4A'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Бот успешно запущен и работает в облаке 24/7.")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.reply_to(message, f"Сообщение получено: {message.text}")

if __name__ == '__main__':
    print("Бот успешно запущен!")
    bot.infinity_polling()

import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = '9072613366:AAHh1HNYzXPLkA3imN40amzaF-SzOwGWV4A'
bot = telebot.TeleBot(TOKEN)

# Ваш реальный Telegram ID администратора
ADMIN_ID = 5388363572  

# Базы данных в памяти
users_db = {}  # {user_id: {'age': int, 'gender': str, 'target': str}}
user_state = {} # {user_id: 'step_name'}

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Команда /start и /edit для регистрации и изменения анкеты
@bot.message_handler(commands=['start', 'edit'])
def start_registration(message):
    user_id = message.from_user.id
    user_state[user_id] = 'waiting_for_age'
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("❌ Отмена")
    
    bot.send_message(
        message.chat.id,
        "Привет! Для использования бота нужно заполнить анкету.\n\n⚠️ **Внимание: сервис строго 18+**\nВведите ваш реальный возраст цифрами:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# Обработка текстовых сообщений и шагов анкеты
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    text = message.text

    if text == "❌ Отмена":
        user_state.pop(user_id, None)
        bot.send_message(message.chat.id, "Действие отменено. Напишите /start для повторного заполнения анкеты.", reply_markup=types.ReplyKeyboardRemove())
        return

    # Шаг 1: Проверка возраста (строго от 18)
    if user_state.get(user_id) == 'waiting_for_age':
        if not text.isdigit():
            bot.send_message(message.chat.id, "Пожалуйста, введите возраст цифрами (например: 20):")
            return
        
        age = int(text)
        if age < 18:
            bot.send_message(message.chat.id, "❌ Доступ запрещен. Сервис предназначен только для лиц старше 18 лет.")
            user_state.pop(user_id, None)
            return
        
        users_db[user_id] = {'age': age}
        user_state[user_id] = 'waiting_for_gender'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Мужской", "Женский")
        bot.send_message(message.chat.id, "Укажите ваш пол:", reply_markup=markup)
        return

    # Шаг 2: Выбор своего пола
    if user_state.get(user_id) == 'waiting_for_gender':
        if text not in ["Мужской", "Женский"]:
            bot.send_message(message.chat.id, "Пожалуйста, выберите пол с помощью кнопок.")
            return
        
        users_db[user_id]['gender'] = text
        user_state[user_id] = 'waiting_for_target'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Парня", "Девушку", "Всех")
        bot.send_message(message.chat.id, "Кого вы хотите найти?", reply_markup=markup)
        return

    # Шаг 3: Выбор кого ищет
    if user_state.get(user_id) == 'waiting_for_target':
        if text not in ["Парня", "Девушку", "Всех"]:
            bot.send_message(message.chat.id, "Пожалуйста, выберите вариант с помощью кнопок.")
            return
        
        users_db[user_id]['target'] = text
        user_state.pop(user_id, None)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✏️ Изменить анкету", "🔍 Начать общение")
        
        bot.send_message(
            message.chat.id,
            f"✅ Анкета успешно сохранена!\n\nВозраст: {users_db[user_id]['age']}\nПол: {users_

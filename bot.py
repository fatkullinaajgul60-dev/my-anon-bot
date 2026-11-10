import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = '9072613366:AAHh1HNYzXPLkA3imN40amzaF-SzOwGWV4A'
bot = telebot.TeleBot(TOKEN)

# Ваш ID администратора
ADMIN_ID = 5388363572  

users_db = {} 
user_state = {} 

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

@bot.message_handler(commands=['start', 'edit'])
def start_registration(message):
    user_id = message.from_user.id
    user_state[user_id] = 'waiting_for_age'
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("❌ Отмена")
    
    bot.send_message(
        message.chat.id,
        "Привет! Для использования бота нужно заполнить анкету.\n\n⚠️ Внимание: сервис строго 18+\nВведите ваш реальный возраст цифрами:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    text = message.text

    if text == "❌ Отмена":
        user_state.pop(user_id, None)
        bot.send_message(message.chat.id, "Действие отменено. Напишите /start для заполнения анкеты заново.", reply_markup=types.ReplyKeyboardRemove())
        return

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

    if user_state.get(user_id) == 'waiting_for_target':
        if text not in ["Парня", "Девушку", "Всех"]:
            bot.send_message(message.chat.id, "Пожалуйста, выберите вариант с помощью кнопок.")
            return
        
        users_db[user_id]['target'] = text
        user_state.pop(user_id, None)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("✏️ Изменить анкету", "🔍 Начать общение")
        
        age_val = users_db[user_id]['age']
        gender_val = users_db[user_id]['gender']
        target_val = users_db[user_id]['target']
        
        bot.send_message(
            message.chat.id,
            f"✅ Анкета сохранена!\n\nВозраст: {age_val}\nПол: {gender_val}\nИщу: {target_val}\n\nДля исправления нажмите «Изменить анкету» или отправьте /edit.",
            reply_markup=markup
        )
        return

    if text == "✏️ Изменить анкету":
        start_registration(message)
        return

    if ADMIN_ID and user_id != ADMIN_ID:
        username = message.from_user.username or 'нет_ника'
        first_name = message.from_user.first_name or ''
        user_info = f"👤 От: @{username} (ID: {user_id})\nИмя: {first_name}"
        bot.send_message(ADMIN_ID, user_info)
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)

    bot.reply_to(message, f"Сообщение получено: {message.text}")

@bot.message_handler(content_types=['voice', 'video_note', 'photo', 'video', 'document'])
def for_admin_media(message):
    user_id = message.from_user.id
    if ADMIN_ID and user_id != ADMIN_ID:
        username = message.from_user.username or 'нет_ника'
        user_info = f"🚨 Медиа от пользователя @{username} (ID: {user_id})"
        bot.send_message(ADMIN_ID, user_info)
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    bot.reply_to(message, "Медиафайл получен и передан администратору.")

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    print("Бот успешно запущен!")
    bot.infinity_polling()

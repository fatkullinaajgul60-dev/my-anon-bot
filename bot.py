import os
import threading
from flask import Flask
import telebot
from telebot import types

TOKEN = '9072613366:AAHh1HNYzXPLkA3imN40amzaF-SzOwGWV4A'
bot = telebot.TeleBot(TOKEN)

# Ваш ID администратора
ADMIN_ID = 5388363572  

# Базы данных
users_db = {}     # {user_id: {'age': int, 'gender': str, 'target': str}}
user_ratings = {} # {user_id: {'cool': int, 'meh': int, 'spam': int}}
user_state = {}   # {user_id: 'step_name'}
search_queue = [] # Список пользователей, ищущих собеседника
active_chats = {} # {user_id: partner_id} (активные диалоги)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Главное меню с кнопками
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Начать общение", "✏️ Изменить анкету")
    return markup

# Функция получения текста рейтинга пользователя
def get_user_reputation(user_id):
    stats = user_ratings.get(user_id, {'cool': 0, 'meh': 0, 'spam': 0})
    return f"👍 {stats['cool']} | 😐 {stats['meh']} | 🚨 {stats['spam']}"

@bot.message_handler(commands=['start', 'edit'])
def start_registration(message):
    user_id = message.from_user.id
    
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        try:
            bot.send_message(partner_id, "❌ Собеседник завершил диалог.", reply_markup=get_main_menu())
        except:
            pass
    if user_id in search_queue:
        search_queue.remove(user_id)

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
        bot.send_message(message.chat.id, "Действие отменено.", reply_markup=get_main_menu())
        return

    # --- РЕГИСТРАЦИЯ И АНКЕТА ---
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
        
        # Инициализируем рейтинг, если его еще не было
        if user_id not in user_ratings:
            user_ratings[user_id] = {'cool': 0, 'meh': 0, 'spam': 0}
            
        age_val = users_db[user_id]['age']
        gender_val = users_db[user_id]['gender']
        target_val = users_db[user_id]['target']
        rep_val = get_user_reputation(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ Анкета сохранена!\n\nВозраст: {age_val}\nПол: {gender_val}\nИщу: {target_val}\nВаш рейтинг: {rep_val}",
            reply_markup=get_main_menu()
        )
        return

    if text == "✏️ Изменить анкету":
        start_registration(message)
        return

    # --- ПОИСК СОБЕСЕДНИКА ---
    if text == "🔍 Начать общение":
        if user_id not in users_db:
            bot.send_message(message.chat.id, "Сначала заполните анкету!", reply_markup=get_main_menu())
            start_registration(message)
            return
        
        if user_id in active_chats:
            bot.send_message(message.chat.id, "Вы уже в чате! Чтобы выйти, отправьте /stop")
            return
        
        if user_id in search_queue:
            bot.send_message(message.chat.id, "Вы уже ищете собеседника, подождите немного...")
            return

        if search_queue:
            partner_id = search_queue.pop(0)
            
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            
            stop_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            stop_markup.add("🛑 Завершить диалог")
            
            # Показываем собеседникам друг друга с их рейтингом!
            p1_rep = get_user_reputation(partner_id)
            p2_rep = get_user_reputation(user_id)
            
            bot.send_message(user_id, f"🎉 Собеседник найден!\nРепутация собеседника: {p1_rep}\n\nМожете общаться анонимно.", reply_markup=stop_markup)
            bot.send_message(partner_id, f"🎉 Собеседник найден!\nРепутация собеседника: {p2_rep}\n\nМожете общаться анонимно.", reply_markup=stop_markup)
            
            if ADMIN_ID:
                bot.send_message(ADMIN_ID, f"🔗 Сцепка чата:\nUser 1: {user_id} (Рейтинг: {p2_rep})\nUser 2: {partner_id} (Рейтинг: {p1_rep})")
        else:
            search_queue.append(user_id)
            cancel_search = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel_search.add("🛑 Остановить поиск")
            bot.send_message(message.chat.id, "🔍 Ищем свободного собеседника...", reply_markup=cancel_search)
        return

    if text == "🛑 Остановить поиск":
        if user_id in search_queue:
            search_queue.remove(user_id)
        bot.send_message(message.chat.id, "Поиск остановлен.", reply_markup=get_main_menu())
        return

    if text == "🛑 Завершить диалог" or text == "/stop":
        terminate_chat(user_id)
        return

    # --- АКТИВНЫЙ АНОНИМНЫЙ ЧАТ ---
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        bot.send_message(partner_id, f"👤 Собеседник: {message.text}")
        
        if ADMIN_ID:
            username = message.from_user.username or 'нет_ника'
            bot.send_message(ADMIN_ID, f"💬 Текст от @{username} (ID: {user_id}) -> {partner_id}:\n{message.text}")
        return

    bot.send_message(message.chat.id, "Используйте кнопки меню для поиска или изменения анкеты.", reply_markup=get_main_menu())

def terminate_chat(user_id):
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        
        rating_markup = types.InlineKeyboardMarkup()
        rating_markup.add(
            types.InlineKeyboardButton("👍 Крутой", callback_data=f"rate_cool_{partner_id}"),
            types.InlineKeyboardButton("😐 Такое себе", callback_data=f"rate_meh_{partner_id}")
        )
        rating_markup.add(
            types.InlineKeyboardButton("🚨 Бот-спамер / Зазывала", callback_data=f"rate_spam_{partner_id}")
        )
        
        bot.send_message(user_id, "❌ Диалог завершен.", reply_markup=get_main_menu())
        bot.send_message(user_id, "Оцените вашего прошлого собеседника:", reply_markup=rating_markup)
        
        try:
            bot.send_message(partner_id, "❌ Собеседник покинул чат.", reply_markup=get_main_menu())
            partner_rating_markup = types.InlineKeyboardMarkup()
            partner_rating_markup.add(
                types.InlineKeyboardButton("👍 Крутой", callback_data=f"rate_cool_{user_id}"),
                types.InlineKeyboardButton("😐 Такое себе", callback_data=f"rate_meh_{user_id}")
            )
            partner_rating_markup.add(
                types.InlineKeyboardButton("🚨 Бот-спамер / Зазывала", callback_data=f"rate_spam_{user_id}")
            )
            bot.send_message(partner_id, "Оцените вашего прошлого собеседника:", reply_markup=partner_rating_markup)
        except:
            pass
        
        if ADMIN_ID:
            bot.send_message(ADMIN_ID, f"🛑 Диалог завершен между {user_id} и {partner_id}")
    else:
        bot.send_message(user_id, "Вы сейчас не в чате.", reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
def handle_rating(call):
    data_parts = call.data.split('_')
    rating_type = data_parts[1]
    target_id = int(data_parts[2])
    voter_id = call.from_user.id
    
    # Начисляем голос в статистику пользователя
    if target_id not in user_ratings:
        user_ratings[target_id] = {'cool': 0, 'meh': 0, 'spam': 0}
    
    if rating_type in user_ratings[target_id]:
        user_ratings[target_id][rating_type] += 1
    
    rating_names = {
        'cool': '👍 Крутой',
        'meh': '😐 Такое себе',
        'spam': '🚨 Бот-спамер / Зазывала'
    }
    text_label = rating_names.get(rating_type, 'Неизвестно')
    
    bot.answer_callback_query(call.id, "Спасибо за вашу оценку!")
    try:
        bot.edit_message_text(f"✅ Ваша оценка сохранена: {text_label}", call.message.chat.id, call.message.message_id)
    except:
        pass
    
    if ADMIN_ID:
        voter_username = call.from_user.username or 'нет_ника'
        target_rep = get_user_reputation(target_id)
        admin_msg = f"📊 **Новая оценка!**\n\n👤 Кто оценил: @{voter_username} (ID: {voter_id})\n🎯 Кого оценили (ID): {target_id}\n⭐ Поставлено: {text_label}\n\n📈 Общий рейтинг игрока: {target_rep}"
        if rating_type == 'spam':
            admin_msg += "\n\n⚠️ **Внимание: отмечен как спамер / зазывала!**"
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")

@bot.message_handler(content_types=['voice', 'video_note', 'photo', 'video', 'document'])
def handle_media(message):
    user_id = message.from_user.id
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        bot.copy_message(partner_id, message.chat.id, message.message_id)
        
        if ADMIN_ID:
            username = message.from_user.username or 'нет_ника'
            bot.send_message(ADMIN_ID, f"🚨 Медиа в чате от @{username} (ID: {user_id}) -> {partner_id}:")
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
    else:
        if ADMIN_ID and user_id != ADMIN_ID:
            username = message.from_user.username or 'нет_ника'
            bot.send_message(ADMIN_ID, f"🚨 Вне чата медиа от @{username} (ID: {user_id}):")
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "Сначала найдите собеседника через меню!", reply_markup=get_main_menu())

if __name__ == '__main__':
    threading.Thread(target=run_web, daemon=True).start()
    print("Бот успешно запущен!")
    bot.infinity_polling()

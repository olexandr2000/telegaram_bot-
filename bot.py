import telebot
from telebot import types
import sqlite3
import os
from datetime import datetime

class JobTelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.setup_database()
        self.user_states = {}
        self.user_data = {}
        self.admin_ids = [767168540]  # Ваш ID
        self.register_handlers()
        self.register_additional_handlers()
        self.register_job_listing_handlers()
        self.register_admin_handlers()
        self.register_city_handlers()  # Added city handlers registration

    def setup_database(self):
        self.conn = sqlite3.connect('job_bot.db', check_same_thread=False)
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY,
                employer_id INTEGER,
                title TEXT,
                description TEXT,
                location TEXT,
                telegram_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def is_admin(self, user_id):
        return user_id in self.admin_ids

    def get_navigation_markup(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        back_btn = types.KeyboardButton("🔙 Назад")
        start_btn = types.KeyboardButton("🏠 Головне меню")
        markup.add(back_btn, start_btn)
        return markup

    def show_role_selection(self, message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        employer_btn = types.KeyboardButton("👔 Роботодавець")
        worker_btn = types.KeyboardButton("👷 Шукаю роботу")
        if self.is_admin(message.chat.id):
            admin_btn = types.KeyboardButton("⚙️ Адмін-панель")
            markup.add(employer_btn, worker_btn, admin_btn)
        else:
            markup.add(employer_btn, worker_btn)
        
        self.bot.send_animation(
            message.chat.id,
            "https://media.giphy.com/media/L1R1tvI9svkIWwpVYr/giphy.gif",
            caption="🌟 Вітаємо у Job Search Bot! 🌟\n\n"
            "Оберіть свою роль для продовження:",
            reply_markup=markup
        )

    def register_handlers(self):
        @self.bot.message_handler(commands=['start'])
        def start_message(message):
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name,
                message.from_user.last_name
            ))
            self.conn.commit()
            self.user_states[message.chat.id] = None
            self.show_role_selection(message)

        @self.bot.message_handler(func=lambda message: message.text == "🏠 Головне меню")
        def return_to_start(message):
            self.user_states[message.chat.id] = None
            self.show_role_selection(message)

    def register_city_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text in ["👔 Роботодавець", "👷 Шукаю роботу"])
        def choose_role(message):
            self.user_states[message.chat.id] = message.text
            if message.text == "👔 Роботодавець":
                self.start_employer_flow(message)
            else:
                self.start_worker_flow(message)

        @self.bot.message_handler(func=lambda message: 
            message.text in ["🏙️ Київ", "🌇 Львів", "🌅 Одеса", "🌆 Харків", "🌃 Дніпро", 
                           "🏘️ Хмельницький", "🏰 Полтава", "🌉 Кривий Ріг"])
        def handle_city_selection(message):
            state = self.user_states.get(message.chat.id)
            if state == "👔 Роботодавець":
                self.start_job_posting(message)
            elif state == "👷 Шукаю роботу":
                self.show_job_listings(message)

    def start_employer_flow(self, message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cities = ["🏙️ Київ", "🌇 Львів", "🌅 Одеса", "🌆 Харків", "🌃 Дніпро", 
                 "🏘️ Хмельницький", "🏰 Полтава", "🌉 Кривий Ріг"]
        
        for city in cities:
            markup.add(types.KeyboardButton(city))
        
        markup.add(types.KeyboardButton("🔙 Назад"))
        markup.add(types.KeyboardButton("🏠 Головне меню"))
        
        self.bot.send_message(
            message.chat.id,
            "📍 Оберіть місто для публікації вакансії:",
            reply_markup=markup
        )

    def start_worker_flow(self, message):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cities = ["🏙️ Київ", "🌇 Львів", "🌅 Одеса", "🌆 Харків", "🌃 Дніпро", 
                 "🏘️ Хмельницький", "🏰 Полтава", "🌉 Кривий Ріг"]
        
        for city in cities:
            markup.add(types.KeyboardButton(city))
        
        markup.add(types.KeyboardButton("🔙 Назад"))
        markup.add(types.KeyboardButton("🏠 Головне меню"))
        
        self.bot.send_message(
            message.chat.id, 
            "🔍 Оберіть місто для пошуку роботи:",
            reply_markup=markup
        )

    def start_job_posting(self, message):
        self.user_data[message.chat.id] = {'location': message.text}
        self.bot.send_message(
            message.chat.id, 
            "📋 Введіть заголовок вакансії:",
            reply_markup=self.get_navigation_markup()
        )
        self.user_states[message.chat.id] = "AWAITING_JOB_TITLE"

    def register_additional_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text == "🔙 Назад")
        def handle_back(message):
            current_state = self.user_states.get(message.chat.id)
            if current_state == "AWAITING_JOB_TITLE":
                self.start_employer_flow(message)
            elif current_state == "AWAITING_JOB_DESCRIPTION":
                self.bot.send_message(
                    message.chat.id,
                    "📋 Введіть заголовок вакансії:",
                    reply_markup=self.get_navigation_markup()
                )
                self.user_states[message.chat.id] = "AWAITING_JOB_TITLE"
            elif current_state == "AWAITING_CONTACT":
                self.bot.send_message(
                    message.chat.id,
                    "📝 Введіть повний опис вакансії:",
                    reply_markup=self.get_navigation_markup()
                )
                self.user_states[message.chat.id] = "AWAITING_JOB_DESCRIPTION"
            elif current_state == "ADMIN_PANEL":
                self.show_role_selection(message)
            elif current_state in ["👔 Роботодавець", "👷 Шукаю роботу"]:
                self.show_role_selection(message)
            else:
                self.show_role_selection(message)

        @self.bot.message_handler(func=lambda message: 
            self.user_states.get(message.chat.id) == "AWAITING_JOB_TITLE")
        def get_job_title(message):
            if message.text in ["🔙 Назад", "🏠 Головне меню"]:
                return
            
            self.user_data[message.chat.id]['title'] = message.text
            self.bot.send_message(
                message.chat.id, 
                "📝 Введіть повний опис вакансії:\n\n"
                "• Обов'язки\n"
                "• Вимоги\n"
                "• Умови роботи\n"
                "• Зарплата\n"
                "• Графік роботи", 
                reply_markup=self.get_navigation_markup()
            )
            self.user_states[message.chat.id] = "AWAITING_JOB_DESCRIPTION"

        @self.bot.message_handler(func=lambda message: 
            self.user_states.get(message.chat.id) == "AWAITING_JOB_DESCRIPTION")
        def get_job_description(message):
            if message.text in ["🔙 Назад", "🏠 Головне меню"]:
                return
            
            self.user_data[message.chat.id]['description'] = message.text
            self.bot.send_message(
                message.chat.id, 
                "📱 Введіть ваш Telegram username (наприклад, @username):", 
                reply_markup=self.get_navigation_markup()
            )
            self.user_states[message.chat.id] = "AWAITING_CONTACT"

        @self.bot.message_handler(func=lambda message: 
            self.user_states.get(message.chat.id) == "AWAITING_CONTACT")
        def get_contact(message):
            if message.text in ["🔙 Назад", "🏠 Головне меню"]:
                return
            
            if not message.text.startswith('@'):
                self.bot.send_message(
                    message.chat.id,
                    "❌ Username повинен починатися з '@'. Спробуйте ще раз:",
                    reply_markup=self.get_navigation_markup()
                )
                return
                
            self.user_data[message.chat.id]['telegram_username'] = message.text
            self.save_job_posting(message)

    def save_job_posting(self, message):
        job_data = self.user_data[message.chat.id]
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO jobs 
            (employer_id, title, description, location, telegram_username) 
            VALUES (?, ?, ?, ?, ?)
        ''', (
            message.chat.id, 
            job_data['title'], 
            job_data['description'], 
            job_data['location'], 
            job_data['telegram_username']
        ))
        self.conn.commit()
        
        self.bot.send_message(
            message.chat.id, 
            "✅ Вакансію успішно опубліковано!"
        )
        
        self.bot.send_message(
            message.chat.id, 
            "📝 Ваша вакансія активна! Чекаємо на відгуки від кандидатів.", 
            reply_markup=self.get_navigation_markup()
        )
        
        self.show_role_selection(message)

    def show_job_listings(self, message):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM jobs WHERE location = ?', (message.text,))
        jobs = cursor.fetchall()
        
        if not jobs:
            self.bot.send_message(
                message.chat.id, 
                "😔 На жаль, в обраному місті зараз немає активних вакансій.", 
                reply_markup=self.get_navigation_markup()
            )
            return
        
        self.user_data[message.chat.id] = {'jobs': jobs, 'current_job_index': 0}
        self.display_job(message)

    def display_job(self, message):
        user_data = self.user_data[message.chat.id]
        jobs = user_data['jobs']
        current_index = user_data['current_job_index']
        
        if current_index >= len(jobs):
            self.bot.send_message(
                message.chat.id, 
                "🔚 Більше вакансій немає.", 
                reply_markup=self.get_navigation_markup()
            )
            return
        
        job = jobs[current_index]
        telegram_username = job[5]
        
        job_message = (
            f"📋 Вакансія {current_index + 1}/{len(jobs)}:\n\n"
            f"🔹 Назва: {job[2]}\n\n"
            f"📝 Опис:\n{job[3]}\n\n"
            f"📍 Місто: {job[4]}\n"
            f"👤 Контакт: {telegram_username}"
        )
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        next_btn = types.KeyboardButton("➡️ Наступна вакансія")
        contact_btn = types.KeyboardButton("💬 Написати роботодавцю")
        back_btn = types.KeyboardButton("🔙 Назад")
        start_btn = types.KeyboardButton("🏠 Головне меню")
        
        markup.add(next_btn, contact_btn)
        markup.add(back_btn, start_btn)
        
        self.bot.send_message(
            message.chat.id, 
            job_message, 
            reply_markup=markup
        )
        
        user_data['current_job_index'] += 1
        user_data['current_employer_username'] = telegram_username

    def register_job_listing_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text == "➡️ Наступна вакансія")
        def next_job(message):
            if message.text == "🏠 Головне меню":
                self.show_role_selection(message)
                return
            self.display_job(message)

        @self.bot.message_handler(func=lambda message: message.text == "💬 Написати роботодавцю")
        def contact_employer(message):
            if message.text == "🏠 Головне меню":
                self.show_role_selection(message)
                return
                
            if 'current_employer_username' not in self.user_data[message.chat.id]:
                self.bot.send_message(
                    message.chat.id, 
                    "❌ Помилка: Неможливо знайти контакт роботодавця.",
                    reply_markup=self.get_navigation_markup()
                )
                return

            employer_username = self.user_data[message.chat.id]['current_employer_username']
            profile_link = f"https://t.me/{employer_username.replace('@', '')}"
            
            markup = types.InlineKeyboardMarkup()
            contact_button = types.InlineKeyboardButton(
                text="💬 Написати роботодавцю", 
                url=profile_link
            )
            markup.add(contact_button)
            
            self.bot.send_message(
                message.chat.id,
                "📱 Натисніть кнопку нижче, щоб написати роботодавцю:",
                reply_markup=markup
            )

    def register_admin_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text == "⚙️ Адмін-панель")
        def admin_panel(message):
            if not self.is_admin(message.chat.id):
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("📊 Статистика"),
                types.KeyboardButton("📝 Всі вакансії")
            )
            markup.add(types.KeyboardButton("🔙 Назад"))
            
            self.bot.send_message(
                message.chat.id,
                "⚙️ Панель адміністратора\n\nОберіть опцію:",
                reply_markup=markup
            )
            self.user_states[message.chat.id] = "ADMIN_PANEL"

        @self.bot.message_handler(func=lambda message: 
            message.text == "📊 Статистика" and self.is_admin(message.chat.id))
        def show_statistics(message):
            cursor = self.conn.cursor()
            
            # Get total users
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Get total jobs
            cursor.execute('SELECT COUNT(*) FROM jobs')
            total_jobs = cursor.fetchone()[0]
            
            # Get active users in last 24 hours
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE joined_at >= datetime('now', '-1 day')
            ''')
            active_users = cursor.fetchone()[0]
            
            # Get jobs by city
            cursor.execute('''
                SELECT location, COUNT(*) as count 
                FROM jobs 
                GROUP BY location
            ''')
            jobs_by_city = cursor.fetchall()
            
            stats_message = (
                "📊 Статистика бота:\n\n"
                f"👥 Всього користувачів: {total_users}\n"
                f"📝 Активних вакансій: {total_jobs}\n"
                f"📈 Нових користувачів за 24г: {active_users}\n\n"
                "📍 Вакансії по містах:\n"
            )
            
            for city, count in jobs_by_city:
                stats_message += f"{city}: {count} вакансій\n"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("🔙 Назад"))
            markup.add(types.KeyboardButton("🏠 Головне меню"))
            
            self.bot.send_message(message.chat.id, stats_message, reply_markup=markup)

        @self.bot.message_handler(func=lambda message: 
            message.text == "📝 Всі вакансії" and self.is_admin(message.chat.id))
        def show_all_jobs(message):
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM jobs ORDER BY created_at DESC')
            jobs = cursor.fetchall()
            
            if not jobs:
                self.bot.send_message(
                    message.chat.id,
                    "📭 Наразі немає активних вакансій.",
                    reply_markup=self.get_navigation_markup()
                )
                return
            
            for job in jobs:
                job_message = (
                    f"🆔 ID: {job[0]}\n"
                    f"📍 Місто: {job[4]}\n"
                    f"📋 Заголовок: {job[2]}\n"
                    f"📝 Опис: {job[3]}\n"
                    f"👤 Контакт: {job[5]}\n"
                    f"📅 Створено: {job[6]}"
                )
                
                markup = types.InlineKeyboardMarkup()
                delete_btn = types.InlineKeyboardButton(
                    "🗑️ Видалити",
                    callback_data=f"delete_job_{job[0]}"
                )
                edit_btn = types.InlineKeyboardButton(
                    "✏️ Редагувати",
                    callback_data=f"edit_job_{job[0]}"
                )
                markup.add(delete_btn, edit_btn)
                
                self.bot.send_message(
                    message.chat.id,
                    job_message,
                    reply_markup=markup
                )

        @self.bot.callback_query_handler(func=lambda call: 
            call.data.startswith('delete_job_') and self.is_admin(call.message.chat.id))
        def delete_job(call):
            job_id = call.data.split('_')[2]
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM jobs WHERE id = ?', (job_id,))
            self.conn.commit()
            
            self.bot.answer_callback_query(
                call.id,
                "✅ Вакансію успішно видалено!"
            )
            self.bot.delete_message(
                call.message.chat.id,
                call.message.message_id
            )

        @self.bot.callback_query_handler(func=lambda call: 
            call.data.startswith('edit_job_') and self.is_admin(call.message.chat.id))
        def edit_job(call):
            job_id = call.data.split('_')[2]
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
            job = cursor.fetchone()
            
            if not job:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ Вакансію не знайдено!"
                )
                return
            
            self.user_data[call.message.chat.id] = {
                'editing_job_id': job_id,
                'current_job': job
            }
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("📋 Змінити заголовок"),
                types.KeyboardButton("📝 Змінити опис")
            )
            markup.add(
                types.KeyboardButton("📍 Змінити місто"),
                types.KeyboardButton("👤 Змінити контакт")
            )
            markup.add(types.KeyboardButton("🔙 Назад"))
            
            self.bot.send_message(
                call.message.chat.id,
                "✏️ Оберіть, що хочете змінити:",
                reply_markup=markup
            )
            self.user_states[call.message.chat.id] = "EDITING_JOB"

    def run(self):
        self.bot.polling(none_stop=True)

# Initialize and run bot
if __name__ == "__main__":
    bot = JobTelegramBot('7424832807:AAHmIYekpmlGQkFYc7Hly5KdXhKw_2MFtJU')
    bot.run()
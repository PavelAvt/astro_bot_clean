import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
from datetime import datetime
import requests
import schedule
import time
from database import add_user, get_all_users

# === Настройки через переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_LINK = "https://t.me/+lqPB3ppoz7EzMWFi"
CHANNEL_NAME = "Астрологинеss"

bot = telebot.TeleBot(BOT_TOKEN)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
user_data = {}

zodiac_signs = [
    "Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева",
    "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"
]

zodiac_emojis = {
    "Овен": "♈️", "Телец": "♉️", "Близнецы": "♊️", "Рак": "♋️",
    "Лев": "♌️", "Дева": "♍️", "Весы": "♎️", "Скорпион": "♏️",
    "Стрелец": "♐️", "Козерог": "♑️", "Водолей": "♒️", "Рыбы": "♓️"
}

# === Клавиатура ===
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🔮 По своей карте"))
for sign in zodiac_signs:
    menu.add(KeyboardButton(sign))


# === Генерация совета по знаку ===
def generate_advice(sign):
    prompt = f"Дай короткий и мудрый астрологический совет для знака {sign} на сегодня."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("GPT ошибка:", e)
        return "⚠️ Не удалось получить совет."


# === Старт ===
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Привет! Выбери свой знак зодиака ✨", reply_markup=menu)


# === Ответ на знак зодиака ===
@bot.message_handler(func=lambda msg: msg.text in zodiac_signs)
def zodiac_handler(message):
    sign = message.text
    chat_id = message.chat.id
    today = datetime.now().date().isoformat()

    if chat_id in user_data and user_data[chat_id]["date"] == today:
        bot.send_message(chat_id,
            f"🔁 Ты уже получил свой совет на сегодня!\nПодписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
            parse_mode="HTML")
        return

    tip = generate_advice(sign)
    user_data[chat_id] = {"sign": sign, "date": today}

    bot.send_message(chat_id,
        f"{zodiac_emojis[sign]} <b>Совет для {sign}:</b>\n\n{tip}\n\n🔮 Подписывайся на <a href=\"{CHANNEL_LINK}\">{CHANNEL_NAME}</a>",
        parse_mode="HTML"
    )


# === Ответ на "По своей карте" ===
@bot.message_handler(func=lambda msg: msg.text == "🔮 По своей карте")
def in_progress(message):
    bot.send_message(message.chat.id,
        "🔧 Функция *по натальной карте* сейчас в разработке. Следи за обновлениями!",
        parse_mode="Markdown")


# === Планировщик ===
def send_daily_horoscopes():
    users = get_all_users()
    for user in users:
        tip = generate_advice(user["sign"])
        try:
            bot.send_message(user["chat_id"], f"🌞 Доброе утро!\n\n{tip}")
        except Exception as e:
            print(f"Ошибка отправки {user['chat_id']}: {e}")

schedule.every().day.at("08:00").do(send_daily_horoscopes)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

import threading
threading.Thread(target=run_scheduler).start()
bot.polling()

